#! /usr/bin/python3

import argparse, sys, datetime
sys.path.append("/home/web/discord/")
from user import User
import cgi, cgitb
print("Content-type:text/html\n\n")
cgitb.enable()

form = cgi.FieldStorage()
if "id" in form:
    id = form["id"].value
else:
    if not form["mode"].value == "vote":
        print("No id presented...")
        sys.exit()
step = 0 if not "step" in form else int(form["step"].value)

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
if not "mode" in form or form["mode"].value == "set":
    if user.loadvote(id)["status"] != "not set":
        print("既に設定されています。再設定するには選挙管理委員権限をもつメンバーに解除してもらってください。")
        sys.exit()
    if step == 0:
        output=f'<form method="post" action="./" enctype="application/x-www-form-urlencoded"> <input type="hidden" name="id" value={id}><input type="hidden" name="mode" value="set"><input type="hidden" name="step" value="1">'
        output+='<label>投票の名前:<input type="text" name="name" /></label><br />'
        output+='<label>投票の形式:<div><input type="radio" name="vote_mode" value="1">投票(1個のみ)</input><input type="radio" name="vote_mode" value="2">信任投票</input><input type="radio" name="vote_mode" value="3">差額選挙</input></div></label><br />'
        output+='<label>有効期限:<input type="date" name="date" /><input type="time" name="time" /></label><br />'
        output+='<label>投票項目(カンマ区切りで入力, 投票以外の時は省略):<textarea name="index" ></textarea></label><br />'
        output+='<label>投票者:<br />'
        for usr in user.loadvote(id)["users"]:
            output+=f'<input type="checkbox" name="users" value="{usr}">{usr}</input><br />'
        output+='</label><br />'
        output+='一度設定すると取り消すには選挙管理委員権限が必要です。<br /><input type="submit" /></form>'
    else:
        if require(["name","date","time","vote_mode", "users", "index"],form):
            name=form["name"].value
            date=form["date"].value.split("-")
            time=form["time"].value.split(":")
            dt=datetime.datetime(year=int(date[0]),month=int(date[1]),day=int(date[2]),hour=int(time[0]),minute=int(time[1]))
            vote_mode=int(form["vote_mode"].value)
            users=form.getlist("users")
            if vote_mode==1:
                index=form["index"].value.split(",")
            user.setvote(id,users,vote_mode,name,dt,index)
            output=f'正常に操作が完了しました。<br />この投票のidは"{id}"です。'
        else:
            output="何か問題が起きたようです。設定に必要なデータが足りません。<br />"
            output+=str(require(["name","date","time"],form,rt_losts=True))
elif form["mode"].value == "vote":
    print(type(step))
    if step == 0:
        output='<form method="post" action="./" enctype="application/x-www-form-urlencoded"><input type="hidden" name="mode" value="vote"><input type="hidden" name="step" value="1">'
        output+='<label>投票トークン:<input type="text" name="token"/></label><br /><input type="submit" /></form>'
    elif step == 1:
        if require(["token"],form):
            token=form["token"].value
            id = user.token2id(token)
            temp = user.loadvote(id)
            output=f'<form method="post" action="./" enctype="application/x-www-form-urlencoded"><input type="hidden" name="mode" value="vote" /><input type="hidden" name="token" value="{token}" /><input type="hidden" name="step" value="2">'
            if temp["mode"] == 1:
                for index in temp["index"]:
                    output+=f'<label><input type="radio" name="vote" value="{index}"/>{index}</label><br />'
            output+='<input type="submit" /></form>'
        else:
            output="何か問題が起きたようです。投票に必要なデータが足りません。<br />"
            output+=str(require(["token"],form,rt_losts=True))
    else:
        if require(["token","step","vote"],form):
            token=form["token"].value
            id = user.token2id(token)
            temp = user.loadvote(id)
            #output=f'<form method="post" action="./" enctype="application/x-www-form-urlencoded"><input type="hidden" n$            if temp["mode"] == 0:
                #for index in temp["index"]:
                #output+=f'<label><input type="radio" name="vote" value="{index}"/>{index}</label><br />'
            if user.vote_token(id, token, form["vote"].value):
                output="投票完了"
            else:
                output="error"
        else:
            output="何か問題が起きたようです。投票に必要なデータが足りません。<br />"
            output+=str(require(["token","vote"],form,rt_losts=True))

else:
    output="申し訳ございません。未実装です。"
print(output)