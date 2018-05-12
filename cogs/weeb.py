import configparser
import os
import random
import asyncio
from pixivpy3 import *
import discord
from discord.ext import commands

config = configparser.ConfigParser()
config.read('config.ini')

class Weeb:
    def __init__(self, bot):
        self.bot = bot
        self.pixiv = None
        self.autotasks = {}

        if config['pixiv']['user']:
            self.pixiv = AppPixivAPI(timeout=10)
            try:
                self.pixiv.login(config['pixiv']['user'], config['pixiv']['pass'])
            except Exception as e:
                print("pixiv: Failed to login")
                print(f"{e}")
                self.pixiv = None
            else:
                print(f"pixiv: Logged into pixiv as {config['pixiv']['user']}.")
        else:
            print("pixiv: Unavailable")

    async def _autoimg_task(self, channel, *, timeout=30, nsfw=False):
        while True:
            await asyncio.sleep(timeout * 60)
            print(f"Sending image to channel {channel.name}")
            await self._random_pixiv(channel, nsfw=nsfw)

    @commands.command()
    async def image(self, ctx):
        """Posts a random illustration from pixiv"""
        if not self.pixiv:
            await ctx.send('Senpai has not configured pixiv yet!')
            return

        await self._random_pixiv(ctx.channel)

    @commands.command()
    async def autoimage(self, ctx, *, delay: int):
        """Posts a random illustration from pixiv every X minutes (min. 1, 0 to cancel)"""
        if delay <= 0:
            if ctx.channel.id in self.autotasks:
                self.autotasks[ctx.channel.id].cancel()
                del self.autotasks[ctx.channel.id]
                await ctx.send("No longer posting images in this channel!")
            else:
                await ctx.send("This channel is not setup to post images!")
        else:
            if ctx.channel.id in self.autotasks:
                self.autotasks[ctx.channel.id].cancel()
                del self.autotasks[ctx.channel.id]

            self.autotasks[ctx.channel.id] = asyncio.get_event_loop().create_task(self._autoimg_task(ctx.channel, timeout=delay, nsfw=False))
            await ctx.send(f"I will post images in this channel every {delay} minute(s)!")

    @commands.command()
    @commands.is_nsfw()
    async def nsfw(self, ctx):
        """Posts a random NSFW illustration from pixiv"""
        if not self.pixiv:
            await ctx.send('Senpai has not configured pixiv yet!')
            return

        await self._random_pixiv(ctx.channel, nsfw=True)

    async def _random_pixiv(self, channel, *, nsfw=False):
        ranking_modes = ['day', 'week', 'month']
        json_result = None

        if nsfw:
            ranking_modes = ['day_r18', 'week_r18']

        if not nsfw and random.getrandbits(1):
            json_result = self.pixiv.illust_recommended('illust')
        else:
            json_result = self.pixiv.illust_ranking(random.choice(ranking_modes))

        if not json_result:
            print("pixiv: no illustration results")
            return

        illust = random.choice(json_result.illusts)
        await self._post_pixiv(channel, illust)

    async def _post_pixiv(self, channel, illust, download=False):
        if download:
            response = self.pixiv.requests_call('GET', illust.image_urls['large'], headers={ 'Referer': 'https://app-api.pixiv.net/' }, stream=True)
            print(illust)
            img = discord.File(response.raw, os.path.basename(illust.image_urls['large']))
            await channel.send(f"https://pixiv.net/i/{illust.id}", file=img)
            del response
        else:
            await channel.send(f"https://pixiv.net/i/{illust.id}")

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        if "this is my fight" in message.content:
            await message.channel.send('No, Senpai. This is our fight!')

def setup(bot):
    bot.add_cog(Weeb(bot))
