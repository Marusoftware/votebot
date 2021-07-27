import pickle, os

class User():
    def __init__(self):
        self.conf_dir="/mnt/hdd_linuxfs_ext4/WEB/DATA/vote/"
    def mkvote(self,id,users):
        temp={}
        temp.update(users=users)
        temp.update(status="not set")
        pickle.dump(temp,open(self.conf_dir+id,"wb"))
    def loadvote(self, id):
        return pickle.load(open(self.conf_dir+id,"rb"))
    def setvote(self,id,users,mode,name,datetime,index):
        temp={}
        temp.update(status="set")
        temp.update(users=users,mode=mode,name=name,datetime=datetime,index=index)
        pickle.dump(temp,open(self.conf_dir+id,"wb"))
    def isexist(id):
        return id in os.listdir(self.conf_dir)
    def addmovingVote(self,id):
        dct={}
        temp=self.loadvote(id)
        if os.path.exists(self.conf_dir+"moving"):
            dct=pickle.load(open(self.conf_dir+"moving","rb"))
        dct[id]=temp["name"]
        pickle.dump(dct,open(self.conf_dir+"moving","wb"))
        temp.update(status="running")
        temp.update(vote={})
        temp.update(voted={})
        pickle.dump(temp,open(self.conf_dir+id,"wb"))
    def getmovingVote(self):
        return list(pickle.load(open(self.conf_dir+"moving","rb")).keys())
    def getmovingVotename(self):
        return list(pickle.load(open(self.conf_dir+"moving","rb")).values())
    def getmovingVotedict(self):
        return pickle.load(open(self.conf_dir+"moving","rb"))
    def closeVote(self,id):
        dct=pickle.load(open(self.conf_dir+"moving","rb"))
        dct.pop(id)
        pickle.dump(dct,open(self.conf_dir+"moving","wb"))
        temp=self.loadvote(id)
        temp.update(status="running")
        pickle.dump(temp,open(self.conf_dir+id,"wb"))
    def vote(self, vote_name, user, index):
        dct=pickle.load(open(self.conf_dir+"moving","rb"))
        for id in dct:
            if dct[id] == vote_name:
                break
        temp=self.loadvote(id)
        if temp["mode"] == 1:
            if not user in temp["users"]:
                return False
            if user in temp["voted"]:
                return False
            if index in temp["vote"]:
                temp["vote"][index]+=1
            else:
                temp["vote"].update([(index,1)])
            temp["voted"][user]=True
            pickle.dump(temp,open(self.conf_dir+id,"wb"))
            return True
        else:
            print("未実装1")
            return False
    def make_token(self, id, user, token):
        dct={"id":id,"token":token,"user":user}
        pickle.dump(dct,open(self.conf_dir+"token"+token,"wb"))
    def vote_token(self, id, token, index):
        #return self.vote(self.loadvote(id)["name"],pickle.load(open(self.conf_dir+"token"+token,"rb"))["user"],index)
        temp=self.loadvote(id)
        user=pickle.load(open(self.conf_dir+"token"+token,"rb"))["user"]
        id=self.token2id(token)
        if temp["mode"] == 1:
            if not user in temp["users"]:
                return False
            if user in temp["voted"]:
                return False
            if index in temp["vote"]:
                temp["vote"][index]+=1
            else:
                temp["vote"].update([(index,1)])
            temp["voted"][user]=True
            pickle.dump(temp,open(self.conf_dir+id,"wb"))
            os.remove(self.conf_dir+"token"+token)
            return True
    def token2id(self, token):
        return pickle.load(open(self.conf_dir+"token"+token,"rb"))["id"]