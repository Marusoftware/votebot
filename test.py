import discord
from discord.ui import Button, View, Select
from discord import ButtonStyle, SelectOption
from discord.ext.commands import Bot

intents = discord.Intents.default()
intents.typing=False
intents.members=True
intents.webhooks=False

bot=Bot("!", intents=intents)

@bot.command()
async def test(ctx):
    llist=list()
    for i in range(25):
        llist.append(SelectOption(label=str(i)))
    view=View(timeout=None)
    view.add_item(select("test", llist))
    view.add_item(select("test", llist))
    await ctx.send("test",view=view)

class select(Select):
    def __init__(self, custom_id, llist):
        super().__init__(custom_id=custom_id, options=llist)
    async def callback(self, interaction):
        print(self.values, self.custom_id, interaction.user.name)
        view=View(timeout=None)
        rdict=dict()
        rdict.update(value=self.values,custom_id=self.custom_id,user=interaction.user.name)
        view.add_item(button(True, rdict))
        view.add_item(button(False, rdict))
        await interaction.response.send_message("Is it OK?\n"+str(self.values), view=view,ephemeral=True)

class button(Button):
    def __init__(self, ok, response_dict):
        super().__init__(style=ButtonStyle.primary, label=str(ok))
        self.ok=ok
        self.response_dict=response_dict
    async def callback(self, interaction: discord.Interaction):
        if self.ok:
            await interaction.response.edit_message(content="done"+str(self.response_dict), view=None)
        else:
            await interaction.response.edit_message(content="cancel", view=None)

bot.run("ODY5MDA0MjMzMzY4ODI1OTM5.YP35Qg.Zxpak4b0vPmNJekZRGeRuhX5qFs")