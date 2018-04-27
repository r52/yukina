import discord
from discord.ext import commands

class Weeb:
    def __init__(self, bot):
        self.bot = bot

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        if "this is my fight" in message.content:
            await message.channel.send('No, Senpai. This is our fight!')

def setup(bot):
    bot.add_cog(Weeb(bot))
