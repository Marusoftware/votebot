from discord.ext import commands
from discord_buttons_plugin.types import ButtonType
from discord_components import DiscordComponents, Button, ButtonStyle, Select, SelectOption
from user import User
import logging, argparse, discord, random, string

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
#backend
user=User()
#intents
intents=discord.Intents.default()
intents.typing=False
intents.members=True
#bot
bot = commands.Bot(command_prefix="!", intents=intents)

#event_on_connect
@bot.event
async def on_ready():
    DiscordComponents(bot)
    logger.info("Login")

#event_on_test_command
@bot.command(name="test")
async def test(ctx):
    await ctx.send('正常に動作しているようです...')

#event_on_mkvote_command
@bot.command(name="mkvote")
async def mkvote(ctx, args=None):
    id=randomstr(10)
    user.mkvote(id, [(usr.nick if not usr.nick is None else usr.name) for usr in ctx.channel.members if not usr.bot])#, ctx.channel.members)
    await ctx.send('このボットは無能なので、以下のリンクを使って投票を作成できるようにしました。',components=[Button(style=ButtonStyle.URL,label="Link",url="https://marusoftware.net/service/vote?id="+id)])

@bot.command(name="start_vote")
async def stvote(ctx, args=None):
    buttons=[]
    if args != None and type(args) == str:
        usr=user.loadvote(args)
        for i in range(len(usr["index"])//5):
            for j in range(5):
                buttons.append(Button(label=usr["index"][i*5+j], style=1))
            await ctx.send(f'{usr["name"]}の{i}枚目',components=buttons)
            buttons=[]
        for k in range(len(usr["index"])%4):
            try:
                n=(i+1)*5+k
            except:
                n=k
            buttons.append(Button(label=usr["index"][n], style=1))
        try:
            await ctx.send(f'{usr["name"]}の{i+1}枚目',components=buttons)
        except:
            await ctx.send(f'{usr["name"]}の1枚目',components=buttons)
        user.addmovingVote(args)
    else:
        await ctx.send("投票idが入力されていないようです。")

@bot.listen("on_button_click")
async def btclick(ctx):
    id=ctx.message.content.split("の")[0]
    if id in user.getmovingVotename():
        member=ctx.guild.get_member(ctx.user.id)
        member= member.name if member.nick is None else member.nick
        out= user.vote(id, member, ctx.component.label)
        if out:
            await ctx.respond(content = f'{id}における{member}さんの{ctx.component.label}への投票を受け付けました。')
        else:
            await ctx.respond(content="何らかの問題により、投票に失敗しました。")
    else:
        await ctx.respond(content="この投票は締め切られているか、開始されていない可能性があります。")

@bot.command(name="close_vote")
async def close(ctx, args=None):
    if not args is None and type(args) == str:
        if args in user.getmovingVote():
            user.closeVote(args)
            temp=user.loadvote(args)
            txt=""
            for index in temp["index"]:
                txt+=f'{index}: {(temp["vote"][index] if index in temp["vote"] else 0) }票\n'
            await ctx.send(f'投票"{temp["name"]}"を締め切りました。\n結果は次のようになりました:\n{txt}')
        else: print(user.getmovingVote())
    else:
        await ctx.send('投票idが入力されていないか、そのような投票が存在しない可能性があります。')

@bot.command(name="getOpening")
async def getOpen(ctx, args=None):
    temp=user.getmovingVotedict()
    await ctx.send('\n'.join([f'{vote}:{temp[vote]}' for vote in temp]))
#@bot.command(name="help")
#async def help(ctx):
#    await ctx.send("～VoteBotの使い方～ \
#\n!test 生存確認 \
#\n!mkvote 投票設定URL発行 \
#\n!start_vote [ID] 設定後に渡されるIDを引数にして入力すると、投票ボタンが現れる。\
#\n!close_vote [ID] 終了して結果を表示 \
#\n!getOpening 進行中の投票を表示 \
#\n!help このヘルプを表示")

bot.run("ODY5MDA0MjMzMzY4ODI1OTM5.YP35Qg.Zxpak4b0vPmNJekZRGeRuhX5qFs")