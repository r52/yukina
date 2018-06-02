import configparser
import os
import random
import asyncio
from collections import deque
from pixivpy3 import *
import discord
from discord.ext import commands

config = configparser.ConfigParser()
config.read('config.ini')


class Weeb:
    def __init__(self, bot):
        self.bot = bot
        self.pixiv = None
        self.dupes = deque(maxlen=100)
        self.autotasks = {}

        self._pixiv_login()

    def _pixiv_login(self):
        if not self.pixiv:
            self.pixiv = AppPixivAPI(timeout=10)

        token = None
        # First try to refresh
        if 'refresh_token' in config['pixiv'] and 'access_token' in config['pixiv']:
            # refresh login instead of generating new one
            self.pixiv.set_auth(
                config['pixiv']['access_token'], config['pixiv']['refresh_token'])
            try:
                token = self.pixiv.auth()
            except Exception as e:
                print("pixiv: Failed to refresh login.")
                print(f"{e}")
            else:
                print(f"pixiv: Login to pixiv refreshed.")

        # Otherwise try new login
        if token is None and config['pixiv']['user']:
            print(f"pixiv: Logging in as {config['pixiv']['user']}...")
            try:
                token = self.pixiv.login(config['pixiv']['user'],
                                         config['pixiv']['pass'])
            except Exception as e:
                print("pixiv: Failed to login")
                print(f"{e}")
            else:
                print(
                    f"pixiv: Logged into pixiv as {config['pixiv']['user']}.")

        # Save tokens if successful
        if token is not None:
            config['pixiv']['access_token'] = token.response.access_token
            config['pixiv']['refresh_token'] = token.response.refresh_token
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
        else:
            # If everything failed, kill it
            self.pixiv = None
            print("pixiv: Unavailable")

    async def _autoimg_task(self, channel, *, timeout=30, nsfw=False):
        while True:
            await asyncio.sleep(timeout * 60)

            async with channel.typing():
                await self._random_pixiv(channel, nsfw=nsfw)

    @commands.command()
    async def image(self, ctx):
        """Posts a random illustration from pixiv"""
        if not self.pixiv:
            await ctx.send('Senpai has not configured pixiv yet!')
            return

        async with ctx.channel.typing():
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

            self.autotasks[ctx.channel.id] = asyncio.get_event_loop().create_task(
                self._autoimg_task(ctx.channel, timeout=delay, nsfw=False))
            await ctx.send(f"I will post images in this channel every {delay} minute(s)!")

    @commands.command()
    @commands.is_nsfw()
    async def nsfw(self, ctx):
        """Posts a random NSFW illustration from pixiv"""
        if not self.pixiv:
            await ctx.send('Senpai has not configured pixiv yet!')
            return

        async with ctx.channel.typing():
            await self._random_pixiv(ctx.channel, nsfw=True)

    async def _random_pixiv(self, channel, *, nsfw=False):
        ranking_modes = ['day', 'week']
        json_result = None

        if nsfw:
            ranking_modes = ['day_r18', 'week_r18']

        while True:
            try:
                if not nsfw and random.getrandbits(1):
                    json_result = self.pixiv.illust_recommended('illust')
                else:
                    json_result = self.pixiv.illust_ranking(
                        random.choice(ranking_modes))
            except Exception as e:
                print(f"pixiv: polling failed: {e}")
                return

            if 'error' in json_result:
                # Refresh oauth
                self._pixiv_login()
                continue

            if 'illusts' in json_result:
                break

        illust = random.choice(json_result.illusts)

        def is_manga_or_dupe(il):
            if self.dupes.count(illust.id) > 0:
                return True

            for tag in il.tags:
                if tag['name'] == '漫画':
                    return True
            return False

        # skip manga panels
        while is_manga_or_dupe(illust):
            illust = random.choice(json_result.illusts)

        self.dupes.append(illust.id)
        url = None
        if len(illust.meta_pages) > 0:
            # this is a collection/album
            # select a random image from the collection
            pg = random.choice(illust.meta_pages)
            url = pg.image_urls['original']
        else:
            # single image
            url = illust.meta_single_page['original_image_url']

        await self._post_pixiv(channel, illust.id, url)

    async def _post_pixiv(self, channel, id, url, download=True):
        if download:
            response = self.pixiv.requests_call('GET', url, headers={
                'Referer': 'https://app-api.pixiv.net/'}, stream=True)
            img = discord.File(response.raw, os.path.basename(url))
            await channel.send(f"<https://pixiv.net/i/{id}>", file=img)
            del response
        else:
            await channel.send(f"https://pixiv.net/i/{id}")

    async def on_message(self, message):
        if message.author.id == self.bot.user.id:
            return

        if "this is my fight" in message.content:
            await message.channel.send('No, Senpai. This is our fight!')


def setup(bot):
    bot.add_cog(Weeb(bot))
