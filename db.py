from enum import IntEnum
from tortoise.fields import BigIntField, ReverseRelation, UUIDField, IntEnumField, CharField, DatetimeField, ManyToManyField, ForeignKeyField, IntField, ManyToManyRelation
from tortoise.models import Model
from tortoise import fields
from datetime import datetime, timezone, timedelta

class VoteStatus(IntEnum):
    not_set=0
    set=1
    running=2
    closed=3

class VoteMode(IntEnum):
    one_select_once=0
    one_select_editable=1
    multi_select_once=2
    multi_select_editable=3

class Vote(Model):
    id=UUIDField(pk=True, description="Vote ID")
    guild_id=BigIntField(description="Discord Guild ID")
    owner_id=BigIntField(description="Owner of this vote")
    users:ManyToManyRelation["User"]
    indexes:ReverseRelation["Index"]
    status=IntEnumField(VoteStatus, description="Vote status", default=VoteStatus.not_set)
    mode=IntEnumField(VoteMode, description="Vote Mode", default=VoteMode.one_select_once)
    name=CharField(max_length=1024, description="Vote name", default="")
    end_time=DatetimeField(description="Vote end time", null=True)

class User(Model):
    id=BigIntField(pk=True, description="Discord User ID")
    votes:ManyToManyRelation[Vote]=ManyToManyField("models.Vote", related_name="users", on_delete=fields.CASCADE)
    indexes:ReverseRelation["Index"]

class Index(Model):
    id=UUIDField(pk=True, description="Index ID")
    vote=ForeignKeyField("models.Vote", related_name="indexes", on_delete=fields.CASCADE)
    name=CharField(max_length=1024, description="Index name")
    users=ManyToManyField("models.User", related_name="indexes", on_delete=fields.CASCADE)
    point=IntField(description="Point")

class DB():
    async def loadvote(self, server_id, id):
        return await Vote.get(guild_id=server_id, id=id).prefetch_related("users", "indexes")
    async def mkvote(self, server_id, users, owner_id):
        vote=await Vote.create(guild_id=server_id, owner_id=owner_id)
        return vote.id
    async def setvote(self, server_id, id, users, mode, name, datetime, index):
        vote=await Vote.get(guild_id=server_id, id=id)
        vote=vote.update_from_dict(data={"status":VoteStatus.set,
                    "mode":VoteMode(int(mode)), "name":name, "end_time":datetime})
        for uid in users:
            user, res=await User.get_or_create(id=uid)
            await user.votes.add(vote)
        for i in index:
            await Index.create(name=i, point=0, vote=vote)
        await vote.save()
    async def isexist(self, server_id, id):
        return await Vote.exists(guild_id=server_id, id=id)
    async def listvote(self, server_id):
        votes=await Vote.filter(guild_id=server_id).prefetch_related("users", "indexes")
        return [] if votes is None else votes
    async def addmovingVote(self, server_id, id):
        vote=await self.loadvote(server_id, id)
        vote.status=VoteStatus.running
        await vote.save()
    async def getmovingVote(self, server_id):
        return await Vote.filter(guild_id=server_id, status=VoteStatus.running)
    async def closeVote(self, server_id, id):
        vote=await self.loadvote(server_id, id)
        vote.status=VoteStatus.closed
        await vote.save()
    async def vote(self, server_id, id, user, index, tzinfo=timezone(timedelta(hours=9))):
        temp=await self.loadvote(server_id, id)
        if not user in [user.id for user in temp.users]:
            return False
        user=await User.get(id=user)
        if temp.end_time is not None:
            if temp.end_time > datetime.now(tz=tzinfo):
                return False
        if temp.mode == VoteMode.one_select_once and (await user.indexes.filter(vote=temp).exists() or not await user.votes.filter(id=temp.id).exists()):
            return False
        index=await temp.indexes.filter(name=index).first()
        index.point+=1
        await index.save()
        await index.users.add(user)
        return temp.name