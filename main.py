from discord.ext import commands
from discord.mentions import A
from discord.ui import Button, Select, View
from user import User
import logging, argparse, discord, random, string
from discord import ButtonStyle, SelectOption
def randomstr(n):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=n))

#parse argv
argparser = argparse.ArgumentParser("VoteBot", description="VotingBot")
argparser.add_argument("-log_level", action="store", type=int, dest="log_level", default=20 ,help="set Log level.(0-50)")
##argparser.add_argument("--daemon", dest="daemon", help="Start in daemon mode.", action="store_true")
argv=argparser.parse_args()
#setting logging
logging.basicConfig(level=argv.log_level)
logger = logging.getLogger("Main")
#intents
intents=discord.Intents.default()
intents.typing=False
intents.members=True
#bot
bot = commands.Bot(command_prefix="!", intents=intents)
#backend
user=User()

#event_on_connect
@bot.event
async def on_ready():
    logger.info("Login")

""" command """
#TODO: permition, help, server
#test
@bot.command(name="test")
async def test(ctx):
    await ctx.send('正常に動作しているようです...')

#mkvote
@bot.command(name="mkvote")
async def mkvote(ctx, args=None):
    id=randomstr(10)
    user.mkvote(ctx.guild.id, id, [(usr.nick if not usr.nick is None else usr.name) for usr in ctx.channel.members if not usr.bot])#, ctx.channel.members)
    view=View()
    view.add_item(Button(style=ButtonStyle.link,label="Link",url="https://marusoftware.net/service/vote?id="+id+"&srv_id="+str(ctx.guild.id)))
    await ctx.send("以下のURLを使って投票を設定してください。",view=view)

#strt_vote
@bot.command(name="start_vote")
async def stvote(ctx, args=None):
    if args != None and type(args) == str:
        usr=user.loadvote(ctx.guild.id, args)
        border=25
        llist=[]
        view=View(timeout=None)
        for i in range(len(usr["index"])//border):
            for j in range(border):
                llist.append(SelectOption(label=usr["index"][i*border+j]))
            view.add_item(select(args+"_"+str(i), llist=llist, id=args))
            llist=[]
        try:
            i=i+1
        except:
            i=0
        for k in range(len(usr["index"])%border):
            n=i*border+k
            llist.append(SelectOption(label=usr["index"][n]))
        view.add_item(select(args+"_"+str(i), llist=llist, id=args))
        await ctx.send(f'{usr["name"]}',view=view)
        user.addmovingVote(ctx.guild.id, args)
    else:
        await ctx.send("投票idが入力されていないようです。")

#close_vote
@bot.command(name="close_vote")
async def close(ctx, args=None):
    if not args is None and type(args) == str:
        if args in user.getmovingVote(ctx.guild.id):
            user.closeVote(ctx.guild.id, args)
            temp=user.loadvote(ctx.guild.id, args)
            txt=""
            for index in temp["index"]:
                txt+=f'{index}: {(temp["vote"][index] if index in temp["vote"] else 0) }票\n'
            await ctx.send(f'投票"{temp["name"]}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else: print(user.getmovingVote(ctx.guild.id))
    else:
        await ctx.send('投票idが入力されていないか、そのような投票が存在しない可能性があります。')

#getOpening
@bot.command(name="getOpening")
async def getOpen(ctx, args=None):
    temp=user.getmovingVotedict(ctx.guild.id)
    await ctx.send('\n'.join([f'{vote}:{temp[vote]}' for vote in temp]))

#getwtoken
@bot.command(name="getwtoken")
async def gtoken(ctx, id=None, user=None):
    if not id is None and not user is None:
        token=randomstr(15)
        user.make_token(ctx.guild.id, id, user, token)
        await ctx.send(f'このトークンを以下のページで入力し、投票を行ってください。\n{token}\n',components=[Button(style=ButtonStyle.URL,label="Link",url="https://marusoftware.net/service/vote?mode=vote")])

class select(Select):#TODO: other vote mode
    def __init__(self, custom_id, llist, id):
        super().__init__(custom_id=custom_id, options=llist)
        self.id=id
    async def callback(self, interaction):
        view=View(timeout=None)
        rdict=dict()
        rdict.update(value=self.values,id=self.id,user=(interaction.user.name if interaction.user.nick is None else interaction.user.nick))
        view.add_item(button(True, rdict))
        view.add_item(button(False, rdict))
        await interaction.response.send_message("これでよろしいですか?\n(複数の選択肢ウィジェットがある場合は、一つにつき1回この手続きが必要です。)\n"+",".join(self.values), view=view,ephemeral=True)

class button(Button):
    def __init__(self, ok, response_dict):
        super().__init__(style=ButtonStyle.primary, label=("はい" if ok else "いいえ"), emoji=(bot.get_emoji(871402454527410267) if ok else bot.get_emoji(871402621657821215)))
        self.ok=ok
        self.response_dict=response_dict
    async def callback(self, interaction: discord.Interaction):
        id=self.response_dict["id"]
        member=self.response_dict["user"]
        index=self.response_dict["value"]
        server=interaction.guild.id
        if self.ok:
            if id in user.getmovingVote(server):
                out= user.vote(server, id, member, index[0])#TODO: other vote mode
                if out:
                    await interaction.response.edit_message(content=f'{id}における{member}さんの{",".join(index)}への投票を受け付けました。', view=None)
                else:
                    await interaction.response.edit_message(content="何らかの問題により、投票に失敗しました。", view=None)
            else:
                await interaction.response.edit_message(content="この投票は締め切られているか、開始されていない可能性があります。", view=None)
        else:
            await interaction.response.edit_message(content="キャンセルしました。", view=None)


bot.run("ODY5MDA0MjMzMzY4ODI1OTM5.YP35Qg.Zxpak4b0vPmNJekZRGeRuhX5qFs")