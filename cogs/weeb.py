import configparser
import os
import random
import asyncio
import json
import datetime
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
        self.cfg = config['pixiv']
        self.dupes = deque(maxlen=100)

        if 'dupes' in self.cfg:
            self.dupes = deque(json.loads(self.cfg['dupes']), maxlen=100)

        self.autotasks = {}

        self._pixiv_login()

    def __del__(self):
        for k, t in self.autotasks.items():
            t.cancel()
            del t

    def log(self, msg):
        st = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{st}] {msg}")

    def _pixiv_login(self):
        if not self.pixiv:
            self.pixiv = AppPixivAPI(timeout=10)

        token = None
        # First try to refresh
        if 'refresh_token' in self.cfg and 'access_token' in self.cfg:
            # refresh login instead of generating new one
            self.pixiv.set_auth(
                self.cfg['access_token'], self.cfg['refresh_token'])
            try:
                token = self.pixiv.auth()
            except Exception as e:
                self.log("pixiv: Failed to refresh login.")
                self.log(f"{e}")
            else:
                self.log(f"pixiv: Login to pixiv refreshed.")

        # Otherwise try new login
        if token is None and self.cfg['user']:
            self.log(f"pixiv: Logging in as {self.cfg['user']}...")
            try:
                token = self.pixiv.login(self.cfg['user'],
                                         self.cfg['pass'])
            except Exception as e:
                self.log("pixiv: Failed to login")
                self.log(f"{e}")
            else:
                self.log(f"pixiv: Logged into pixiv as {self.cfg['user']}.")

        # Save tokens if successful
        if token is not None:
            self.cfg['access_token'] = token.response.access_token
            self.cfg['refresh_token'] = token.response.refresh_token
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
        else:
            # If everything failed, kill it
            self.pixiv = None
            self.log("pixiv: Unavailable")

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

        def get_illust(nsfw, offset=None):
            json_result = None
            ranking_modes = ['day', 'week']

            if nsfw:
                ranking_modes = ['day_r18', 'week_r18']

            while True:
                try:
                    if not nsfw and random.getrandbits(1):
                        json_result = self.pixiv.illust_recommended('illust', offset=offset)
                    else:
                        json_result = self.pixiv.illust_ranking(random.choice(ranking_modes), offset=offset)
                except Exception as e:
                    self.log(f"pixiv: polling failed: {e}")
                    break

                if 'error' in json_result:
                    # Refresh oauth
                    self._pixiv_login()
                    continue

                if 'illusts' in json_result:
                    break

            return json_result

        il_results = get_illust(nsfw)
        if il_results is None:
            self.log("pixiv: No results, something went wrong")
            # polling failed, internet probably dead, kill this attempt
            return

        illust = random.choice(il_results.illusts)

        def is_manga_or_dupe(il):
            if self.dupes.count(illust.id) > 0:
                return True

            for tag in il.tags:
                if tag['name'] == '漫画':
                    return True
            return False

        # skip manga panels
        numdupes = 0
        offset = 0
        while is_manga_or_dupe(illust):
            numdupes += 1
            if numdupes % 20 is 0:
                offset += len(il_results)

            if numdupes % 10 is 0:
                il_results = get_illust(nsfw, offset)

            illust = random.choice(il_results.illusts)

        self.dupes.append(illust.id)
        # write cfg
        self.cfg['dupes'] = json.dumps(list(self.dupes))
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

        url = None
        if len(illust.meta_pages) > 0:
            # this is a collection/album
            # select a random image from the collection
            pg = random.choice(illust.meta_pages)
            url = pg.image_urls['original']
        else:
            # single image
            url = illust.meta_single_page['original_image_url']

        if url is None:
            self.log(f"Illust {illust.id} has no url. Wtf?")
            return

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
