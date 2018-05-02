import asyncio

import discord
import youtube_dl

from discord.ext import commands

# Suppress noise about console usage from errors
youtube_dl.utils.bug_reports_message = lambda: ''


ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

ffmpeg_options = {
    'before_options': '-nostdin',
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)


class Music:
    def __init__(self, bot):
        self.bot = bot

    async def timeout_check(self, ctx):
        """Disconnects from voice channel on inactivity"""
        await asyncio.sleep(60)

        if not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()

    @commands.command()
    async def play(self, ctx, *, url):
        """Streams from a URL"""

        def finalize(e):
            print('Player error: %s' % e) if e else None
            ctx.voice_client.loop.create_task(self.timeout_check(ctx))

        async with ctx.typing():
            player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
            ctx.voice_client.play(player, after=finalize)

        await ctx.send('Now playing: {}'.format(player.title))

    @commands.command()
    async def stop(self, ctx):
        """Stops and disconnects from voice"""

        await ctx.voice_client.disconnect()

    @commands.command()
    async def airhorn(self, ctx):
        """Airhorn"""
        await self.clip(ctx, url="https://www.youtube.com/watch?v=MAFGdHvHxpU")

    @commands.command()
    async def hello(self, ctx):
        """Hello :)"""
        await self.file(ctx, query="clips/hello.ogg")

    @commands.command()
    async def nani(self, ctx):
        """NANI?!?!?!?"""
        await self.file(ctx, query="clips/nani.ogg")

    @commands.command()
    async def senpai(self, ctx):
        """Senpai!"""
        await self.clip(ctx, url="https://www.youtube.com/watch?v=PnHi8cjulI0")

    @commands.command()
    async def fight(self, ctx):
        """No Senpai, this is our fight!"""
        await self.clip(ctx, url="https://www.youtube.com/watch?v=wimSoRKKepc")

    async def file(self, ctx, *, query):
        """Plays a file from the local filesystem then immediately disconnect"""

        def finalize(e):
            print('Player error: %s' % e) if e else None
            asyncio.run_coroutine_threadsafe(
                ctx.voice_client.disconnect(), ctx.voice_client.loop)

        source = discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(query))
        ctx.voice_client.play(source, after=finalize)

    async def clip(self, ctx, *, url):
        """Play a short clip then immediately disconnect"""

        def finalize(e):
            print('Player error: %s' % e) if e else None
            asyncio.run_coroutine_threadsafe(
                ctx.voice_client.disconnect(), ctx.voice_client.loop)

        player = await YTDLSource.from_url(url, loop=self.bot.loop, stream=True)
        ctx.voice_client.play(player, after=finalize)

    @play.before_invoke
    @hello.before_invoke
    @senpai.before_invoke
    @fight.before_invoke
    @airhorn.before_invoke
    @nani.before_invoke
    async def ensure_voice(self, ctx):
        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("You are not connected to a voice channel.")
                raise commands.CommandError(
                    "Author not connected to a voice channel.")
        elif ctx.voice_client.is_playing():
            ctx.voice_client.stop()


def setup(bot):
    bot.add_cog(Music(bot))
