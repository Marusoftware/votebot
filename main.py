from datetime import datetime
from discord.ext import commands
from discord.ui import Button, Select, View, Modal, InputText
from user import User
import logging, argparse, discord, random, string
from discord import ButtonStyle, SelectOption, Option, Interaction, InputTextStyle
def randomstr(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

#parse argv
argparser = argparse.ArgumentParser("VoteBot", description="VotingBot")
argparser.add_argument("-log_level", action="store", type=int, dest="log_level", default=20 ,help="set Log level.(0-50)")
argparser.add_argument("-path", action="store", type=str, dest="path", required=False ,help="data path", default="./")
argparser.add_argument("-logfile", action="store", type=str, dest="logfile", required=False ,help="log file path", default=None)
argparser.add_argument("token", action="store", type=str, help="discord bot token")
argv=argparser.parse_args()
#setting logging
logger_options={}
if argv.logfile is not None: logger_options["filename"]=argv.logfile
logging.basicConfig(level=argv.log_level, **logger_options)
logger = logging.getLogger("Main")
#intents
intents=discord.Intents.default()
intents.typing=False
intents.members=True
intents.message_content=True
#bot
bot = commands.Bot(command_prefix="!", intents=intents)
#backend
user=User(argv.path)

#event_on_connect
@bot.event
async def on_ready():
    logger.info("Login")

""" command """
#test
@bot.slash_command(name="test")
async def test(ctx):
    await ctx.respond('正常に動作しているようです...')

class mkvoteSelect(Select):
    def __init__(self, id):
        super().__init__(min_values=1, max_values=1, placeholder="選択してください...", options=[SelectOption(label="一つを選ぶ", value="0", description="選択肢の中から1つのみを選択できるようにします。")])
        self.vote_id=id
    async def callback(self, interaction: Interaction):
        mode=int(self.values[0])
        await interaction.response.send_modal(setupModal(self.vote_id, mode))

class setupModal(Modal):
    def __init__(self, id, mode):
        super().__init__(title="投票の設定")
        self.vote_id=id
        self.vote_mode=mode
        self.add_item(InputText(style=InputTextStyle.singleline, label="投票の名前(必須):", required=True))
        self.add_item(InputText(style=InputTextStyle.singleline, label="有効期限:", placeholder="yyyy-mm-dd hh:mm:ss(部分的も可, 入力がない場合は期限なし)", required=False))
        self.add_item(InputText(style=InputTextStyle.multiline, label="選択肢(必須):", placeholder="1行に一つずつ入力してください。", required=True))
    async def callback(self, interaction: Interaction):
        user.setvote(server_id=interaction.guild_id, id=self.vote_id, users=[mem.id for mem in interaction.guild.members], mode=self.vote_mode, name=self.children[0].value, datetime=None if self.children[1].value == "" else datetime.fromisoformat(self.children[1].value), index=self.children[2].value.split("\n"))
        view=View(timeout=None)
        view.add_item(startVoteBtn(self.vote_id))
        await interaction.response.send_message(f"設定が完了しました! \nstart_voteコマンドで投票を開始してください。ボタンを押すと今すぐ開始できます。", ephemeral=True, view=view)

class startVoteBtn(Button):
    def __init__(self, vote_id):
        super().__init__(style=ButtonStyle.green, label="投票を開始する")
        self.vote_id=vote_id
    async def callback(self, interaction: Interaction):
        name, view=await start_vote(interaction.guild.id, self.vote_id)
        await interaction.response.defer()
        await interaction.channel.send(f"投票:{name}", view=view)
        await interaction.edit_original_response(view=None)

class selectVote(Select):
    def __init__(self, action, gid):
        options=[]
        moving=user.getmovingVotedict(gid)
        if action == "close":
            for vote_id, vote_name in moving.items():
                options.append(SelectOption(label=vote_name, value=vote_id))
        else:
            votes=user.listvote(gid)
            for vote_id in votes:
                if not vote_id in moving:
                    vote=user.loadvote(server_id=gid, id=vote_id)
                    if not "name" in vote: continue
                    options.append(SelectOption(label=vote["name"], value=vote_id))
        if len(options) == 0:
            raise
        super().__init__(placeholder="選択してください...", options=options, disabled=len(options)==0)
        self.action=action
    async def callback(self, interaction: Interaction):
        if self.action == "close":
            user.closeVote(interaction.guild.id, self.values[0])
            temp=user.loadvote(interaction.guild.id, self.values[0])
            txt=""
            for index in temp["index"]:
                txt+=f'{index}: {(temp["vote"][index] if index in temp["vote"] else 0) }票\n'
            await interaction.response.send_message(f'投票"{temp["name"]}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else:
            name, view=await start_vote(interaction.guild.id, self.values[0])
            await interaction.response.defer()
            await interaction.channel.send(f"投票:{name}", view=view)

#mkvote
@bot.slash_command(name="mkvote", description="Make Voting.", default_permission=False)
async def mkvote(ctx):
    id=randomstr(10)
    user.mkvote(ctx.guild.id, id, [(usr.nick if not usr.nick is None else usr.name) for usr in ctx.channel.members if not usr.bot])
    view=View()
    view.add_item(mkvoteSelect(id))
    await ctx.respond("投票の種類を選んで設定を行ってください。", view=view, ephemeral=True)

async def start_vote(gid, vote_id):
    usr=user.loadvote(gid, vote_id)
    border=25
    llist=[]
    view=View(timeout=None)
    for i in range(len(usr["index"])//border):
        for j in range(border):
            llist.append(SelectOption(label=usr["index"][i*border+j]))
        view.add_item(select(vote_id+"_"+str(i), llist=llist, id=vote_id))
        llist=[]
    try:
        i=i+1
    except:
        i=0
    for k in range(len(usr["index"])%border):
        n=i*border+k
        llist.append(SelectOption(label=usr["index"][n]))
    view.add_item(select(vote_id+"_"+str(i), llist=llist, id=vote_id))
    user.addmovingVote(gid, vote_id)
    return usr["name"], view

#start_vote
@bot.command(name="start_vote", aliases=["stvote"])
async def stvote(ctx, id:str=None):
    if id != None and type(id) == str:
        name, view=await start_vote(ctx.guild.id, id)
        if hasattr(ctx, "respond"): await ctx.respond(f"投票:{name}", view=view)
        else: await ctx.send(f'投票:{name}',view=view)
    else:
        view=View(timeout=None)
        try:
            view.add_item(selectVote("start", ctx.guild.id))
        except:
            if hasattr(ctx, "respond"): await ctx.respond("開始できる投票がありません", ephemeral=True)
            else: await ctx.send("開始できる投票がありません")
        else:
            if hasattr(ctx, "respond"): await ctx.respond("投票を選択してください。", view=view, ephemeral=True)
            else: await ctx.send("投票を選択してください。", view=view)
@bot.slash_command(name="start_vote", description="Start Voting", default_permission=False)
async def stvote_sl(ctx, id:Option(str, description="Vote ID", required=False, default=None)):
    await stvote(ctx, id)

#close_vote
@bot.command(name="close_vote")
async def close(ctx, id:str=None):
    args=id
    if not args is None and type(args) == str:
        if args in user.getmovingVote(ctx.guild.id):
            user.closeVote(ctx.guild.id, args)
            temp=user.loadvote(ctx.guild.id, args)
            txt=""
            for index in temp["index"]:
                txt+=f'{index}: {(temp["vote"][index] if index in temp["vote"] else 0) }票\n'
            if hasattr(ctx, "respond"): await ctx.respond(f'投票"{temp["name"]}"を締め切りました。\n結果は次のようになりました:\n{txt}')
            else: await ctx.send(f'投票"{temp["name"]}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else: print(user.getmovingVote(ctx.guild.id))
    else:
        view=View(timeout=None)
        try:
            view.add_item(selectVote("close", ctx.guild.id))
        except:
            if hasattr(ctx, "respond"): await ctx.respond("終了できる投票がありません", ephemeral=True)
            else: await ctx.send("終了できる投票がありません")
        else:
            if hasattr(ctx, "respond"): await ctx.respond("投票を選択してください。", view=view, ephemeral=True)
            else: await ctx.send("投票を選択してください。", view=view)
@bot.slash_command(name="close_vote", description="Close Voting.", default_permission=False)
async def close_sl(ctx, vote_id:Option(str, "Vote ID", required=False, default=None)):
    await close(ctx, vote_id)

#getOpening
@bot.slash_command(name="getopening", description="Get opening Vote.", default_permission=False)
async def getOpen(ctx):
    temp=user.getmovingVotedict(ctx.guild.id)
    await ctx.respond('\n'.join([f'{vote}:{temp[vote]}' for vote in temp]), ephemeral=True)

class select(Select):#TODO: other vote mode
    def __init__(self, custom_id, llist, id):
        super().__init__(custom_id=custom_id, options=llist)
        self.id=id
    async def callback(self, interaction):
        view=View(timeout=None)
        rdict=dict()
        rdict.update(value=self.values,id=self.id,user=(interaction.user.name if interaction.user.nick is None else interaction.user.nick), user_id=interaction.user.id)
        view.add_item(button(True, rdict))
        view.add_item(button(False, rdict))
        await interaction.response.send_message("これでよろしいですか?\n(複数の選択肢ウィジェットがある場合は、一つにつき1回この手続きが必要です。)\n"+",".join(self.values), view=view,ephemeral=True)

class button(Button):
    def __init__(self, ok, response_dict):
        super().__init__(style=(ButtonStyle.green if ok else ButtonStyle.red), label=("はい" if ok else "いいえ"), emoji=(bot.get_emoji(871402454527410267) if ok else bot.get_emoji(871402621657821215)))
        self.ok=ok
        self.response_dict=response_dict
    async def callback(self, interaction: discord.Interaction):
        id=self.response_dict["id"]
        member=self.response_dict["user"]
        member_id=self.response_dict["user_id"]
        index=self.response_dict["value"]
        server=interaction.guild.id
        if self.ok:
            if id in user.getmovingVote(server):
                out= user.vote(server, id, member_id, index[0])#TODO: other vote mode
                if out:
                    await interaction.edit_original_response(content=f'投票{out}における{member}さんの{",".join(index)}への投票を受け付けました。', view=None)
                else:
                    await interaction.edit_original_response(content="何らかの問題により、投票に失敗しました。", view=None)
            else:
                await interaction.edit_original_response(content="この投票は締め切られているか、開始されていない可能性があります。", view=None)
        else:
            await interaction.edit_original_response(content="キャンセルしました。", view=None)

#run
bot.run(argv.token)
