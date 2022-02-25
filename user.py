import pickle, os

class User():
    def __init__(self, data_path):
        self.data_dir=data_path
    def mkvote(self, server_id, id,users):
        temp={}
        temp.update(users=users)
        temp.update(status="not set")
        pickle.dump(temp,open(self.data_dir+str(server_id)+"_"+id,"wb"))
    def loadvote(self, server_id, id):
        with open(self.data_dir+str(server_id)+"_"+id,"rb") as f:
            return pickle.load(f)
    def dumpvote(self, server_id, id, obj):
        with open(self.data_dir+str(server_id)+"_"+id,"wb") as f:
            pickle.dump(obj,f)
    def setvote(self, server_id, id, users, mode, name, datetime, index):
        temp={}
        temp.update(status="set")
        temp.update(users=users,mode=int(mode),name=name,datetime=datetime,index=index)
        self.dumpvote(server_id, id, temp)
    def isexist(self, server_id, id):
        return str(server_id)+"_"+id in os.listdir(self.data_dir)
    def listvote(self, server_id):
        return [i.split("_")[1] for i in os.listdir(self.data_dir) if str(server_id) in i]
    def addmovingVote(self, server_id, id):
        dct={}
        temp=self.loadvote(server_id, id)
        if os.path.exists(self.data_dir+str(server_id)+"_moving"):
            dct=pickle.load(open(self.data_dir+str(server_id)+"_"+"moving","rb"))
        dct[id]=temp["name"]
        pickle.dump(dct,open(self.data_dir+str(server_id)+"_moving","wb"))
        temp.update(status="running")
        temp.update(vote={})
        temp.update(voted={})
        self.dumpvote(server_id, id, temp)
    def getmovingVote(self, server_id):
        try:
            return list(pickle.load(open(self.data_dir+str(server_id)+"_moving","rb")).keys())
        except FileNotFoundError:
            return []
    def getmovingVotename(self, server_id):
        try:
            return list(pickle.load(open(self.data_dir+str(server_id)+"_moving","rb")).values())
        except FileNotFoundError:
            return []
    def getmovingVotedict(self, server_id):
        try:
            return pickle.load(open(self.data_dir+str(server_id)+"_"+"moving","rb"))
        except FileNotFoundError:
            return {}
    def closeVote(self, server_id, id):
        dct=pickle.load(open(self.data_dir+str(server_id)+"_"+"moving","rb"))
        dct.pop(id)
        pickle.dump(dct,open(self.data_dir+str(server_id)+"_"+"moving","wb"))
        temp=self.loadvote(server_id, id)
        temp.update(status="closed")
        self.dumpvote(server_id, id, temp)
    def vote(self, server_id, id, user, index):
        temp=self.loadvote(server_id, id)
        if not user in temp["users"]:
            return False
        if temp["mode"] == 0 and user in temp["voted"] and temp["voted"][user]:
            return False
        elif temp["mode"] == 1:
            pass
        if index in temp["vote"]:
            temp["vote"][index]+=1
        else:
            temp["vote"][index]=1
        temp["voted"][user]=True
        self.dumpvote(server_id, id, temp)
        return temp["name"]
    def make_token(self, server_id, id, user, token):
        dct={"id":id,"token":token,"user":user,"server_id":server_id}
        pickle.dump(dct,open(self.data_dir+"token"+token,"wb"))
    def loadvote_token(self, token):
        dct=pickle.load(open(self.data_dir+"token"+token,"rb"))
        return self.loadvote(dct["server_id"], dct["id"])
    def vote_token(self, token, index):
        dct=pickle.load(open(self.data_dir+"token"+token,"rb"))
        return self.vote(dct["server_id"], dct["id"], dct["user"], index)
#    def token2id(self, token):
#        return pickle.load(open(self.data_dir+"token"+token,"rb"))["id"]