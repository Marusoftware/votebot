#! /usr/bin/python3
votebot_mainDir=""
import sys, datetime
sys.path.append(votebot_mainDir)
from user import User
import cgi, cgitb
print("Content-type:text/html\n\n")
cgitb.enable(display=False)

form = cgi.FieldStorage()
id = form.getvalue("id", None)
mode=form.getvalue("mode", "set")
if id is None and mode != "vote":
    print("No id presented...")
    sys.exit()
try:
    step = int(form.getvalue("step", 0))
except:
    print("step is not an number.")
    sys.exit()

def require(lst, obj, rt_losts=False):
    lost=[]
    for index in lst:
        if not index in obj:
            lost.append(index)
    if len(lost) == 0:
        return True
    else:
        if rt_losts:
            return lost
        else:
            return False

user=User()
if mode == "set":
    import re
    if not re.fullmatch("[0-9A-Za-z]+", id):
        print("Server attack was detected.")
        sys.exit()
    srv_id=form.getvalue("srv_id", None)
    if srv_id is None:
        print("サーバーidが指定されていません。")
        sys.exit()
    if user.loadvote(srv_id, id)["status"] != "not set":
        print("既に設定されています。再設定するには選挙管理委員権限をもつメンバーに解除してもらってください。")
        sys.exit()
    if step == 0:
        output=f'<form method="post" action="" enctype="application/x-www-form-urlencoded"> <input type="hidden" name="id" value={id}><input type="hidden" name="mode" value="set"><input type="hidden" name="step" value="1"><input type="hidden" name="srv_id" value="{srv_id}">'
        output+='<label>投票の名前:<input type="text" name="name" /></label><br />'
        output+='<label>投票の形式:<div><input type="radio" name="vote_mode" value="1">投票(1個のみ)</input><input type="radio" name="vote_mode" value="2">信任投票</input><input type="radio" name="vote_mode" value="3">差額選挙</input></div></label><br />'
        output+='<label>有効期限:<input type="date" name="date" /><input type="time" name="time" /></label><br />'
        output+='<label>投票項目(カンマ区切りで入力, 投票以外の時は省略):<textarea name="index" ></textarea></label><br />'
        output+='<label>投票者:<br />'
        for usr in user.loadvote(srv_id, id)["users"]:
            output+=f'<input type="checkbox" name="users" value="{usr}">{usr}</input><br />'
        output+='</label><br />'
        output+='一度設定すると取り消すには選挙管理委員権限が必要です。<br /><input type="submit" /></form>'
    else:
        if require(["name","date","time","vote_mode", "users", "index"],form):
            name=form.getvalue("name")
            date=form.getvalue("date").split("-")
            time=form.getvalue("time").split(":")
            dt=datetime.datetime(year=int(date[0]),month=int(date[1]),day=int(date[2]),hour=int(time[0]),minute=int(time[1]))
            vote_mode=int(form.getvalue("vote_mode"))
            users=form.getlist("users")
            if vote_mode==1:
                index=form.getvalue("index").split(",")
            user.setvote(srv_id, id,users,vote_mode,name,dt,index)
            output=f'正常に投票を作成できました。<br />この投票のidは"{id}"です。<br />"!start_vote {id}"で投票を開始してください。'
        else:
            output="何か問題が起きたようです。設定に必要なデータが足りません。<br />"
            output+=str(require(["name","date","time"],form,rt_losts=True))
elif mode == "vote":
    if step == 0:
        output='<form method="post" action="" enctype="application/x-www-form-urlencoded"><input type="hidden" name="mode" value="vote"><input type="hidden" name="step" value="1">'
        output+='<label>投票トークン:<input type="text" name="token"/></label><br /><input type="submit" /></form>'
    elif step == 1:
        token=form.getvalue("token", None)
        if token is None:
            print("投票トークンが指定されていません")
            sys.exit()
        #id = user.token2id(token)
        #temp = user.loadvote(id)
        temp=user.loadvote_token(token)
        output=f'<form method="post" action="" enctype="application/x-www-form-urlencoded"><input type="hidden" name="mode" value="vote" /><input type="hidden" name="token" value="{token}" /><input type="hidden" name="step" value="2">'
        if temp["mode"] == 1:
            for index in temp["index"]:
                output+=f'<label><input type="radio" name="vote" value="{index}"/>{index}</label><br />'
        else:
            print("未実装です。")
            sys.exit()
        output+='<input type="submit" /></form>'
    else:
        if require(["token","step","vote"],form):
            if user.vote_token(form["token"].value, form["vote"].value):
                output="投票完了"
            else:
                output="error"
        else:
            output="何か問題が起きたようです。投票に必要なデータが足りません。<br />"
            output+=str(require(["token","vote"],form,rt_losts=True))

else:
    output="申し訳ございません。未実装です。"
print(output)