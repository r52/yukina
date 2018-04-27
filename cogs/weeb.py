import discord
from discord.ext import commands

class Weeb:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='fight')
    async def fight(self, ctx):
        await ctx.send('No, Senpai. This is our fight!')

    @commands.command(name='senpai')
    async def senpai(self, ctx):
        senpai = ctx.guild.role_hierarchy[0].members[0]
        if senpai:
            await ctx.send('Senpai is {.name}!'.format(senpai))
        else:
            await ctx.send('There are no Senpais in this server!')

    @client.event
    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        if "this is my fight" in message.content:
            await message.channel.send('No, Senpai. This is our fight!')

def setup(bot):
    bot.add_cog(Weeb(bot))
