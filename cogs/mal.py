import configparser
import spice_api
import urllib.request
import urllib.parse
import urllib.error
import json
from bs4 import BeautifulSoup
import discord
from discord.ext import commands

tscore = ["(Appalling)", "(Horrible)", "(Very Bad)", "(Bad)", "(Average)",
          "(Fine)", "(Good)", "(Very Good)", "(Great)", "(Masterpiece)"]

config = configparser.ConfigParser()
config.read('config.ini')


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


class MAL:

    def __init__(self, bot):
        self.bot = bot
        self.loggedin = False
        # by default, senpai is the configured MAL user
        self.senpai = config['MAL']['user']
        self.api = 'https://myanimelist.net/includes/ajax-no-auth.inc.php?t=6'

        try:
            self.creds = spice_api.init_auth(
                config['MAL']['user'], config['MAL']['pass'])
        except ValueError:
            print("MAL: Failed to log into MAL")
        else:
            print("MAL: Logged into MAL as {}.".format(self.senpai))
            self.loggedin = True

        self._update_cookie()

    def _update_cookie(self):
        req = urllib.request.urlopen(
            "https://myanimelist.net/animelist/" + self.senpai)
        self.cookies = req.getheader('Set-Cookie')

        html = req.read()
        parsed = BeautifulSoup(html, "lxml")
        self.csrf = parsed.head.find(
            "meta", attrs={"name": "csrf_token"})['content']
        self.memid = parsed.body.attrs['data-owner-id']

    async def _search_entry(self, ctx, *, medium, title: str):
        if not self.loggedin:
            await ctx.send('Senpai has not configured MAL yet!')
            return None

        def entry_check(m):
            return m.content.isdigit() and m.channel == ctx.channel and m.author == ctx.author

        entry = None
        results = spice_api.search(title, medium, self.creds)
        if len(results) == 0:
            await ctx.send('No search results found!')
            return None
        elif len(results) > 1:
            reslist = '\n'.join('[{}] {.title}'.format(*k)
                                for k in enumerate(results, 1))
            res_embed = discord.Embed(
                title='Which one are you talking about?', description=reslist)
            res_msg = await ctx.send(embed=res_embed)
            reply = await self.bot.wait_for('message', check=entry_check)
            entry = results[int(reply.content) - 1]
            await reply.delete()
            await res_msg.delete()
        else:
            entry = results[0]

        return entry

    async def _build_message(self, ctx, *, medium, entry):
        if not entry:
            return

        url = 'https://myanimelist.net/'
        url += 'manga/' if medium == spice_api.tokens.Medium.MANGA else 'anime/'
        url += '{.id}/'.format(entry)

        embed = discord.Embed(title=entry.title, url=url)

        if medium == spice_api.tokens.Medium.MANGA:
            embed.add_field(name='Type', value=entry.manga_type)
            embed.add_field(name='Chapters', value=entry.chapters)
            embed.add_field(name='Volumes', value=entry.volume)
        else:
            embed.add_field(name='Type', value=entry.anime_type)
            embed.add_field(name='Episodes', value=entry.episodes)

        embed.add_field(name='MAL Score', value=':star: ' + entry.score)
        embed.add_field(name='Status', value=entry.status)
        embed.add_field(name='Start Date', value=entry.dates[0])
        if entry.dates[1] and entry.dates[1] != '0000-00-00':
            embed.add_field(name='End Date', value=entry.dates[1])

        synopsis = (
            entry.synopsis[:1021] + '..') if len(entry.synopsis) > 1024 else entry.synopsis
        synopsis = BeautifulSoup(synopsis, "lxml").text
        embed.add_field(name='Synopsis', value=synopsis)
        embed.set_image(url=entry.image_url)
        return await ctx.send(embed=embed)

    @commands.command(name='anime', aliases=['a'])
    async def search_anime(self, ctx, *, title: str):
        medium = spice_api.get_medium('a')
        entry = await self._search_entry(ctx, medium=medium, title=title)
        return await self._build_message(ctx, medium=medium, entry=entry)

    @commands.command(name='manga', aliases=['m'])
    async def search_manga(self, ctx, *, title: str):
        medium = spice_api.get_medium('m')
        entry = await self._search_entry(ctx, medium=medium, title=title)
        return await self._build_message(ctx, medium=medium, entry=entry)

    @commands.command(name='review', aliases=['r'])
    async def get_review(self, ctx, *, title: str):
        medium = spice_api.get_medium('a')
        entry = await self._search_entry(ctx, medium=medium, title=title)
        if entry:
            slist = spice_api.get_list(medium, self.senpai, self.creds)
            fullist = slist.medium_list['completed'] + \
                slist.medium_list['dropped']
            match = next((x for x in fullist if x.id == entry.id), None)
            if not match:
                return await ctx.send("Senpai hasn't watched this anime yet!")

            resp = None
            while not resp:
                try:
                    data = urllib.parse.urlencode(
                        {"color": "1", "type": "anime", "memId": self.memid, "csrf_token": self.csrf, "id": entry.id}).encode()
                    req = urllib.request.Request(self.api, data=data, headers={
                                                 "Cookie": self.cookies})
                    resp = urllib.request.urlopen(req)
                except urllib.error.HTTPError:
                    self._update_cookie()

            rstr = resp.read().decode()
            rmsg = json.loads(rstr)
            chtml = rmsg['html']
            comments = find_between(chtml, "Comments: ", "&nbsp;<br>")
            comments = BeautifulSoup(comments, "lxml").text

            if len(comments) == 0:
                return await ctx.send("Senpai hasn't reviewed this anime!")

            # flip status because of spice api bug
            status = int(match.status)
            if status == 4:
                status = 3
            elif status == 3:
                status = 4

            title = "Senpai's Review of {.title}".format(match)
            url = 'https://myanimelist.net/anime/' + '{.id}/'.format(match)

            split = False
            while len(comments) > 2044:
                part = (comments[:2044] + '...')
                comments = '...' + comments[2044:]
                pembed = discord.Embed(title=title, url=url, description=part)
                await ctx.send(embed=pembed)
                if not split:
                    title = title + ' (cont)'
                    split = True

            embed = discord.Embed(title=title, url=url, description=comments)
            embed.add_field(name='Type', value=entry.anime_type)
            embed.add_field(name='Episodes Watched', value=match.episodes)
            embed.add_field(name='Final Score',
                            value=':star: ' + match.score + '/10 ' + tscore[int(match.score) - 1])
            embed.add_field(name='Status', value=spice_api.get_status(status))
            embed.set_image(url=entry.image_url)
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(MAL(bot))
