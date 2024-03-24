import logging, argparse
from datetime import datetime, timezone, timedelta
from tortoise import Tortoise, run_async
import discord
from discord import ButtonStyle, Forbidden, HTTPException, SelectOption, Option, Interaction, InputTextStyle
from discord.ext import commands
from discord.ui import Button, Select, View, Modal, InputText, button, string_select

from db import DB, VoteMode, VoteStatus

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
    logger.info("Start resuming votes...")
    for vote in await user.getALLmovingVote():
        if vote.message_id is not None:
            view=voteSelect(vote.id, vote.mode, vote.indexes)
            bot.add_view(view, message_id=vote.message_id)
    logger.info("Resuming votes completed!")


""" command """
# mkvote
@bot.slash_command(name="mkvote", description="Make Voting.", default_permission=False)
async def mkvote(ctx):
    id=await user.mkvote(ctx.guild.id, [ usr.id for usr in ctx.channel.members if not usr.bot], ctx.author.id)
    await ctx.respond("投票の種類を選んで設定を行ってください。", view=mkvoteView(id), ephemeral=True)

class mkvoteView(View):
    def __init__(self, id):
        super().__init__(timeout=None)
        self.vote_id = id
    
    @string_select(min_values=1, max_values=1, placeholder="選択してください...", options=[
            SelectOption(label="一つを選ぶ", value="0", description="選択肢の中から1つのみを選択できるようにします。"),
            SelectOption(label="一つを選ぶ(変更可)", value="1", description="「一つを選ぶ」に加えて変更することができるようにします。"),
            SelectOption(label="複数選ぶ", value="2", description="選択肢の中から複数個を選択できるようにします。"),
            SelectOption(label="複数選ぶ(変更可)", value="3", description="「複数選ぶ」に加えて変更することができるようにします。"),])
    async def callback(self, select:Select, interaction: Interaction):
        mode = int(select.values[0])
        await interaction.response.send_modal(setupModal(self.vote_id, mode))


class setupModal(Modal):
    def __init__(self, id, mode):
        super().__init__(title="投票の設定")
        self.vote_id = id
        self.vote_mode = mode
        self.add_item(InputText(style=InputTextStyle.singleline,
                      label="投票の名前(必須):", required=True))
        self.add_item(InputText(style=InputTextStyle.singleline, label="有効期限:",
                      placeholder="yyyy-mm-dd hh:mm:ss+zz:zz(ISOフォーマットで入力。部分省略可能)", required=False))
        self.add_item(InputText(style=InputTextStyle.multiline,
                      label="選択肢(必須):", placeholder="1行に一つずつ入力してください。", required=True))

    async def callback(self, interaction: Interaction):
        try:
            if self.children[1].value == "":
                date=None
            else:
                date=datetime.fromisoformat(self.children[1].value)
                if not "+" in self.children[1].value:
                    date.astimezone(timezone(timedelta(hours=9)))
        except ValueError:
            logger.warning(f"Invalid date format(input={self.children[1].value}, guild_id={interaction.guild_id})")
            return
        await user.setvote(server_id=interaction.guild_id, id=self.vote_id, users=[mem.id for mem in interaction.guild.members], mode=self.vote_mode, name=self.children[0].value,
                            datetime=date, index=self.children[2].value.split("\n"))
        await interaction.response.send_message(f"設定が完了しました! \n/start_voteコマンドで投票を開始してください。もしくはボタンを押すと今すぐ開始できます。", ephemeral=True, view=startVoteView(self.vote_id))


# start_vote
async def start_vote(gid, vote_id, msg=None):
    vote = await user.loadvote(gid, vote_id)
    if msg is not None:
        vote.message_id=msg.id
        await vote.save()
    view=voteSelect(vote.id, vote.mode, vote.indexes)
    await user.addmovingVote(gid, vote_id)
    return vote.name, view


@bot.command(name="start_vote", aliases=["stvote"])
async def stvote(ctx, id: str = None, show_closed:bool=False):
    if id != None and type(id) == str:
        if hasattr(ctx, "respond"):
            msg=await ctx.respond('投票を準備しています...')
        else:
            msg=await ctx.send('投票を準備しています...')
        name, view = await start_vote(ctx.guild.id, id, msg)
        await msg.edit(f"投票:{name}", view=view)
    else:
        view = View(timeout=None)
        try:
            view.add_item(await selectVote.init("start", ctx.guild.id, show_closed=show_closed))
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
async def stvote_sl(ctx, id: Option(str, description="Vote ID", required=False, default=None),
                    show_closed: Option(bool, description="Show closed vote", required=False, default=False)):
    await stvote(ctx, id, show_closed)


class startVoteView(View):
    def __init__(self, vote_id):
        super().__init__(timeout=None)
        self.vote_id = vote_id
    
    @button(style=ButtonStyle.green, label="投票を開始する")
    async def callback(self, btn:Button, interaction: Interaction):
        await interaction.response.defer()
        msg=await interaction.channel.send('投票を準備しています...')
        name, view = await start_vote(interaction.guild.id, self.vote_id, msg)
        await msg.edit(f"投票:{name}", view=view)
        self.stop()
        await interaction.edit_original_response(view=None)


class selectVote(Select):
    @classmethod
    async def init(cls, action, gid, show_user=False, show_closed=False):
        options = []
        moving = await user.getmovingVote(gid)
        if action == "close":
            for vote in moving:
                options.append(SelectOption(label=vote.name, value=str(vote.id)))
        else:
            votes = await user.listvote(gid)
            for vote in votes:
                if vote.status == VoteStatus.set or (vote.status == VoteStatus.closed and show_closed):
                    options.append(SelectOption(label=vote.name, value=str(vote.id)))
        if len(options) == 0:
            raise
        obj=cls(placeholder="選択してください...",
                         options=options, disabled=len(options) == 0)
        obj.action = action
        obj.show_user=show_user
        return obj

    async def callback(self, interaction: Interaction):
        if self.action == "close":
            vote = await user.loadvote(interaction.guild.id, self.values[0])
            await user.closeVote(interaction.guild.id, self.values[0])
            txt = "```"
            for index in vote.indexes:
                txt += f'{index.name}: {index.point}票\n'
                if self.show_user:
                    txt+=', '.join([(await bot.fetch_user(user.id)).display_name for user in await index.users.all()])+"\n"
            txt+="```"
            await interaction.response.send_message(f'投票"{vote.name}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else:
            msg=await interaction.channel.send('投票を準備しています...')
            name, view = await start_vote(interaction.guild.id, self.values[0], msg)
            await interaction.response.defer()
            await msg.edit(f"投票:{name}", view=view)


# close_vote
@bot.command(name="close_vote")
async def close(ctx, id: str = None, show_user: bool=False):
    if id is not None:
        vote=await user.loadvote(ctx.guild.id, id)
        msg=bot.get_message(vote.message_id)
        if msg is not None: await msg.delete()
        await user.closeVote(ctx.guild.id, id)
        txt = "```"
        for index in vote.indexes:
            txt += f'{index.name}: {index.point}票\n'
            if show_user:
                txt+=', '.join([(await bot.fetch_user(user.id)).display_name for user in await index.users.all()])+"\n"
        txt+="```"
        if hasattr(ctx, "respond"):
            await ctx.respond(f'投票"{vote.name}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else:
            await ctx.send(f'投票"{vote.name}"を締め切りました。\n結果は次のようになりました:\n{txt}')
    else:
        view = View(timeout=None)
        try:
            view.add_item(await selectVote.init("close", ctx.guild.id, show_user))
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
async def close_sl(ctx, vote_id: Option(str, "Vote ID", required=False, default=None), show_user: Option(bool, "Show user name?", required=False, default=False)):
    await close(ctx, vote_id, show_user)


# getOpening
@bot.slash_command(name="getopening", description="Get opening Vote.", default_permission=False)
async def getOpen(ctx):
    votes = await user.getmovingVote(ctx.guild.id)
    if len(votes) ==0:
        await ctx.respond('現在実施されている投票はありません。', ephemeral=True)
    else:
        await ctx.respond('\n'.join([f'{vote.id}:{vote.name}' for vote in votes]), ephemeral=True)


class voteSelect(View):
    def __init__(self, id, mode, indexes):
        border = 25
        llist = []
        super().__init__(timeout=None)
        for i in range(len(indexes)//border):
            for j in range(border):
                llist.append(SelectOption(label=indexes[i*border+j]))
            sl=_voteSelect(options=llist, custom_id=str(id), max_values=len(llist) if mode>=VoteMode.multi_select_once else 1 )
            sl.callback=self.callback
            self.add_item(sl)
            llist = []
        try:
            i = i+1
        except:
            i = 0
        for k in range(len(indexes) % border):
            n = i*border+k
            llist.append(SelectOption(label=indexes[n].name))
        sl=_voteSelect(options=llist, custom_id=str(id), max_values=len(llist) if mode>=VoteMode.multi_select_once else 1 )
        self.add_item(sl)

class _voteSelect(Select):
    async def callback(self, interaction):
        view = View(timeout=None)
        rdict = {"value":self.values, "id":self.custom_id, "user":interaction.user.display_name, "user_id":interaction.user.id}
        view.add_item(voteButton(True, rdict))
        view.add_item(voteButton(False, rdict))
        await interaction.response.send_message("これでよろしいですか?\n(複数の選択肢ウィジェットがある場合は、一つにつき1回この手続きが必要です。)\n"+",".join(self.values), view=view, ephemeral=True)


locale2tz={
    "ja": 9,
}

class voteButton(Button):
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
                out = await user.vote(server, id, member_id, index, tzinfo=timezone(timedelta(hours=locale2tz.get(interaction.locale, 9))))
                if out:
                    await interaction.edit_original_response(content=f'投票{out}における{member}さんの{",".join(index)}への投票を受け付けました。', view=None)
                else:
                    await interaction.edit_original_response(content="何らかの問題により、投票に失敗しました。"
                                                                    "``` "
                                                                    "以下のような原因が考えられます:"
                                                                    "- すでに回答済みである "
                                                                    "- 締切時刻を過ぎている "
                                                                    "- 回答権限がない "
                                                                    "```", view=None)
            else:
                await interaction.edit_original_response(content="この投票は締め切られているか、開始されていない可能性があります。", view=None)
        else:
            await interaction.edit_original_response(content="キャンセルしました。", view=None)

async def db_init():
    await Tortoise.init(db_url=argv.path, modules={'models': ['db']})
    await Tortoise.generate_schemas()

run_async(db_init())
bot.run(argv.token)
