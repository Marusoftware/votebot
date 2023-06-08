import logging, argparse, pytz
from datetime import datetime, timezone, timedelta
from tortoise import Tortoise, run_async
import discord
from discord import ButtonStyle, SelectOption, Option, Interaction, InputTextStyle
from discord.ext import commands
from discord.ui import Button, Select, View, Modal, InputText

from db import DB, VoteStatus

# parse argv
argparser = argparse.ArgumentParser("VoteBot", description="VotingBot")
argparser.add_argument("-log_level", action="store", type=int,
                       dest="log_level", default=20, help="set Log level.(0-50)")
argparser.add_argument("-path", action="store", type=str,
                       dest="path", required=False, help="data path(tortoise-orm format)", default="sqlite://./test.db")
argparser.add_argument("-logfile", action="store", type=str,
                       dest="logfile", required=False, help="log file path", default=None)
argparser.add_argument("token", action="store",
                       type=str, help="discord bot token")
argv = argparser.parse_args()
# setting logging
logger_options = {}
if argv.logfile is not None:
    logger_options["filename"] = argv.logfile
logging.basicConfig(level=argv.log_level, **logger_options)
logger = logging.getLogger("Main")
logger_db_client = logging.getLogger("db_client")
logger_tortoise = logging.getLogger("tortoise")

# intents
intents = discord.Intents.default()
intents.typing = False
intents.members = True
intents.message_content = True
# bot

bot = commands.Bot(command_prefix="!", intents=intents)
# backend
user = DB()

# event_on_connect
@bot.event
async def on_ready():
    logger.info("Login")

""" command """

# test
@bot.slash_command(name="test")
async def test(ctx):
    await ctx.respond('正常に動作しているようです...')


class mkvoteSelect(Select):
    def __init__(self, id):
        super().__init__(min_values=1, max_values=1, placeholder="選択してください...", options=[
            SelectOption(label="一つを選ぶ", value="0", description="選択肢の中から1つのみを選択できるようにします。")])
        self.vote_id = id

    async def callback(self, interaction: Interaction):
        mode = int(self.values[0])
        await interaction.response.send_modal(setupModal(self.vote_id, mode))


class setupModal(Modal):
    def __init__(self, id, mode):
        super().__init__(title="投票の設定")
        self.vote_id = id
        self.vote_mode = mode
        self.add_item(InputText(style=InputTextStyle.singleline,
                      label="投票の名前(必須):", required=True))
        self.add_item(InputText(style=InputTextStyle.singleline, label="有効期限:",
                      placeholder="yyyy-mm-dd hh:mm:ss+zz:zz(ISOフォーマットで入力。省略可能)", required=False))
        self.add_item(InputText(style=InputTextStyle.multiline,
                      label="選択肢(必須):", placeholder="1行に一つずつ入力してください。", required=True))

    async def callback(self, interaction: Interaction):
        await user.setvote(server_id=interaction.guild_id, id=self.vote_id, users=[mem.id for mem in interaction.guild.members], mode=self.vote_mode, name=self.children[0].value,
                            datetime=None if self.children[1].value == "" else (datetime.fromisoformat(self.children[1].value) if "+" in self.children[1].value else datetime.fromisoformat(self.children[1].value).astimezone(timezone(timedelta(hours=9)))), index=self.children[2].value.split("\n"))
        view = View(timeout=None)
        view.add_item(startVoteBtn(self.vote_id))
        await interaction.response.send_message(f"設定が完了しました! \n/start_voteコマンドで投票を開始してください。もしくはボタンを押すと今すぐ開始できます。", ephemeral=True, view=view)


class startVoteBtn(Button):
    def __init__(self, vote_id):
        super().__init__(style=ButtonStyle.green, label="投票を開始する")
        self.vote_id = vote_id

    async def callback(self, interaction: Interaction):
        name, view = await start_vote(interaction.guild.id, self.vote_id)
        await interaction.response.defer()
        await interaction.channel.send(f"投票:{name}", view=view)
        await interaction.edit_original_response(view=None)


class selectVote(Select):
    @classmethod
    async def init(cls, action, gid):
        options = []
        moving = await user.getmovingVote(gid)
        if action == "close":
            for vote in moving:
                options.append(SelectOption(label=vote.name, value=str(vote.id)))
        else:
            votes = await user.listvote(gid)
            for vote in votes:
                if vote.status != VoteStatus.running:
                    options.append(SelectOption(label=vote.name, value=str(vote.id)))
        if len(options) == 0:
            raise
        obj=cls(placeholder="選択してください...",
                         options=options, disabled=len(options) == 0)
        obj.action = action
        return obj

    async def callback(self, interaction: Interaction):
        if self.action == "close":
            await user.closeVote(interaction.guild.id, self.values[0])
            vote = await user.loadvote(interaction.guild.id, self.values[0])
            txt = ""
            for index in vote.indexes:
                txt += f'{index.name}: {index.point}票\n'
            await interaction.response.send_message(f'投票"{vote.name}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else:
            name, view = await start_vote(interaction.guild.id, self.values[0])
            await interaction.response.defer()
            await interaction.channel.send(f"投票:{name}", view=view)

# mkvote
@bot.slash_command(name="mkvote", description="Make Voting.", default_permission=False)
async def mkvote(ctx):
    id=await user.mkvote(ctx.guild.id, [(usr.nick if not usr.nick is None else usr.name)
                for usr in ctx.channel.members if not usr.bot])
    view = View(timeout=None)
    view.add_item(mkvoteSelect(id))
    await ctx.respond("投票の種類を選んで設定を行ってください。", view=view, ephemeral=True)


async def start_vote(gid, vote_id):
    vote = await user.loadvote(gid, vote_id)
    border = 25
    llist = []
    view = View(timeout=None)
    for i in range(len(vote.indexes)//border):
        for j in range(border):
            llist.append(SelectOption(label=vote.indexes[i*border+j]))
        view.add_item(select(vote_id+"_"+str(i), llist=llist, id=vote_id))
        llist = []
    try:
        i = i+1
    except:
        i = 0
    for k in range(len(vote.indexes) % border):
        n = i*border+k
        llist.append(SelectOption(label=vote.indexes[n].name))
    view.add_item(select(str(vote_id)+"_"+str(i), llist=llist, id=vote_id))
    await user.addmovingVote(gid, vote_id)
    return vote.name, view

# start_vote
@bot.command(name="start_vote", aliases=["stvote"])
async def stvote(ctx, id: str = None):
    if id != None and type(id) == str:
        name, view = await start_vote(ctx.guild.id, id)
        if hasattr(ctx, "respond"):
            await ctx.respond(f"投票:{name}", view=view)
        else:
            await ctx.send(f'投票:{name}', view=view)
    else:
        view = View(timeout=None)
        try:
            view.add_item(await selectVote.init("start", ctx.guild.id))
        except:
            if hasattr(ctx, "respond"):
                await ctx.respond("開始できる投票がありません", ephemeral=True)
            else:
                await ctx.send("開始できる投票がありません")
        else:
            if hasattr(ctx, "respond"):
                await ctx.respond("投票を選択してください。", view=view, ephemeral=True)
            else:
                await ctx.send("投票を選択してください。", view=view)


@bot.slash_command(name="start_vote", description="Start Voting", default_permission=False)
async def stvote_sl(ctx, id: Option(str, description="Vote ID", required=False, default=None)):
    await stvote(ctx, id)

# close_vote
@bot.command(name="close_vote")
async def close(ctx, id: str = None):
    if id is not None:
        vote=await user.loadvote(ctx.guild.id, id)
        await user.closeVote(ctx.guild.id, id)
        txt = ""
        for index in vote.indexes:
            txt += f'{index.name}: {index.point}票\n'
        if hasattr(ctx, "respond"):
            await ctx.respond(f'投票"{vote.name}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else:
            await ctx.send(f'投票"{vote.name}"を締め切りました。\n結果は次のようになりました:\n{txt}')
    else:
        view = View(timeout=None)
        try:
            view.add_item(await selectVote.init("close", ctx.guild.id))
        except:
            if hasattr(ctx, "respond"):
                await ctx.respond("終了できる投票がありません", ephemeral=True)
            else:
                await ctx.send("終了できる投票がありません")
        else:
            if hasattr(ctx, "respond"):
                await ctx.respond("投票を選択してください。", view=view, ephemeral=True)
            else:
                await ctx.send("投票を選択してください。", view=view)


@bot.slash_command(name="close_vote", description="Close Voting.", default_permission=False)
async def close_sl(ctx, vote_id: Option(str, "Vote ID", required=False, default=None)):
    await close(ctx, vote_id)

# getOpening
@bot.slash_command(name="getopening", description="Get opening Vote.", default_permission=False)
async def getOpen(ctx):
    votes = await user.getmovingVote(ctx.guild.id)
    await ctx.respond('\n'.join([f'{vote.id}:{vote.name}' for vote in votes]), ephemeral=True)


class select(Select):  # TODO: other vote mode
    def __init__(self, custom_id, llist, id):
        super().__init__(custom_id=custom_id, options=llist)
        self.id = id

    async def callback(self, interaction):
        view = View(timeout=None)
        rdict = dict()
        rdict.update(value=self.values, id=self.id, user=(
            interaction.user.name if interaction.user.nick is None else interaction.user.nick), user_id=interaction.user.id)
        view.add_item(button(True, rdict))
        view.add_item(button(False, rdict))
        await interaction.response.send_message("これでよろしいですか?\n(複数の選択肢ウィジェットがある場合は、一つにつき1回この手続きが必要です。)\n"+",".join(self.values), view=view, ephemeral=True)


locale2tz={
    "ja": 9,
}

class button(Button):
    def __init__(self, ok, response_dict):
        super().__init__(style=(ButtonStyle.green if ok else ButtonStyle.red), label=("はい" if ok else "いいえ"),
                         emoji=(bot.get_emoji(871402454527410267) if ok else bot.get_emoji(871402621657821215)))
        self.ok = ok
        self.response_dict = response_dict

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        id = self.response_dict["id"]
        member = self.response_dict["user"]
        member_id = self.response_dict["user_id"]
        index = self.response_dict["value"]
        server = interaction.guild.id
        if self.ok:
            vote=await user.loadvote(server, id)
            if vote.status==VoteStatus.running:
                # TODO: other vote mode
                out = await user.vote(server, id, member_id, index[0], tzinfo=timezone(timedelta(hours=locale2tz.get(interaction.locale, 9))))
                if out:
                    await interaction.edit_original_response(content=f'投票{out}における{member}さんの{",".join(index)}への投票を受け付けました。', view=None)
                else:
                    await interaction.edit_original_response(content="何らかの問題により、投票に失敗しました。", view=None)
            else:
                await interaction.edit_original_response(content="この投票は締め切られているか、開始されていない可能性があります。", view=None)
        else:
            await interaction.edit_original_response(content="キャンセルしました。", view=None)

async def db_init():
    await Tortoise.init(db_url=argv.path, modules={'models': ['db']})
    await Tortoise.generate_schemas()

run_async(db_init())
bot.run(argv.token)
