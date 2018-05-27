import configparser
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
import json
from bs4 import BeautifulSoup
import asyncio
import discord
from discord.ext import commands

tscore = ["(Garbage)", "(Appalling)", "(Horrible)", "(Very Bad)", "(Bad)", "(Average)",
          "(Fine)", "(Good)", "(Very Good)", "(Great)", "(Masterpiece)"]

config = configparser.ConfigParser()
config.read('config.ini')

class Anime:
    def __init__(self, bot):
        self.bot = bot
        self.senpai = False

        # configure gql transport
        authtoken = config['Anime']['token']
        headers = {}

        if authtoken:
            # anilist userid
            self.senpai = True
            headers = {'Authorization': 'Bearer ' + authtoken}

        transport = RequestsHTTPTransport(
            url='https://graphql.anilist.co',
            use_json=True,
            headers=headers
        )

        self.client = Client(
            retries=0,
            transport=transport,
            fetch_schema_from_transport=True,
        )

    async def _search_media(self, ctx, *, medium, title: str):
        querystring = """
        query {{
            Page (page: {page}, perPage: 15) {{
                pageInfo {{
                    total
                    currentPage
                    lastPage
                    hasNextPage
                    perPage
                }}
                media (search: {search}, type: {medium}) {{
                    id
                    title {{
                        english
                        romaji
                    }}
                    type
                    format
                    status
                    description(asHtml: false)
                    startDate {{
                        year
                        month
                        day
                    }}
                    endDate {{
                        year
                        month
                        day
                    }}
                    episodes
                    chapters
                    volumes
                    meanScore
                    siteUrl
                    coverImage {{
                        large
                    }}
                    mediaListEntry {{
                        id
                        userId
                        status
                        score(format: POINT_100)
                        progress
                        notes
                        completedAt {{
                            year
                            month
                            day
                        }}
                    }}
                }}
            }}
        }}
        """

        def entry_check(m):
            return (m.content.isdigit() or m.content == '..' or m.content == '...') and m.channel == ctx.channel and m.author == ctx.author

        curpage = 1
        srchstr = json.dumps(title)

        ql = gql(querystring.format(page=curpage, search=srchstr, medium=medium))
        results = self.client.execute(ql)
        pageinfo = results['Page']['pageInfo']

        entry = None
        if 0 == pageinfo['total']:
            await ctx.send("I couldn't find anything with that name!")
            return None
        elif pageinfo['total'] > 1:
            media = results['Page']['media']
            page = '\n'.join('[{0}] {1}'.format(i, k['title']['english'] if k['title']['english'] else k['title']['romaji']) for i,k in enumerate(media, 1))

            if pageinfo['hasNextPage']:
                page += '\n[...] Next Page'

            page_embed = discord.Embed(
                title='Which one are you talking about?', description=page)
            page_msg = await ctx.send(embed=page_embed)

            while not entry:
                try:
                    reply = await self.bot.wait_for('message', check=entry_check, timeout=30.0)
                    if reply.content == '..':
                        if curpage > 0:
                            curpage -= 1
                    elif reply.content == '...':
                        if pageinfo['hasNextPage']:
                            curpage += 1
                    else:
                        entry = media[int(reply.content) - 1]
                        await page_msg.delete()

                    await reply.delete()
                except asyncio.TimeoutError:
                    await page_msg.delete()
                    break

                if not entry:
                    ql = gql(querystring.format(page=curpage, search=srchstr, medium=medium))
                    results = self.client.execute(ql)
                    pageinfo = results['Page']['pageInfo']
                    media = results['Page']['media']

                    page = '\n'.join('[{0}] {1}'.format(i, k['title']['english'] if k['title']['english'] else k['title']['romaji']) for i,k in enumerate(media, 1))

                    if curpage > 0:
                        page += '\n[..] Previous Page'

                    if pageinfo['hasNextPage']:
                        page += '\n[...] Next Page'

                    page_embed.description = page
                    await page_msg.edit(embed=page_embed)
        else:
            entry = results['Page']['media'][0]

        return entry

    async def _build_message(self, ctx, *, medium, entry):
        if not entry:
            return

        title = entry['title']['english'] if entry['title']['english'] else entry['title']['romaji']
        embed = discord.Embed(title=title, url=entry['siteUrl'])
        embed.add_field(name='Type', value=entry['format'])

        if medium == "MANGA":
            embed.add_field(name='Chapters', value=entry['chapters'])
            embed.add_field(name='Volumes', value=entry['volumes'])
        else:
            embed.add_field(name='Episodes', value=entry['episodes'])

        embed.add_field(name='Mean Score', value=':star: ' + str(entry['meanScore']) + '/100')
        embed.add_field(name='Status', value=entry['status'])
        sd = entry['startDate']
        ed = entry['endDate']
        embed.add_field(name='Start Date', value=str(sd['year'])+'-'+str(sd['month'])+'-'+str(sd['day']))
        if ed['year'] is not None:
            embed.add_field(name='End Date', value=str(ed['year'])+'-'+str(ed['month'])+'-'+str(ed['day']))

        synopsis = (
            entry['description'][:1021] + '..') if len(entry['description']) > 1024 else entry['description']
        synopsis = BeautifulSoup(synopsis, "lxml").text
        embed.add_field(name='Synopsis', value=synopsis)
        embed.set_image(url=entry['coverImage']['large'])
        return await ctx.send(embed=embed)

    @commands.command(aliases=['a'])
    async def anime(self, ctx, *, title: str):
        """Searches for an anime on AniList"""
        entry = await self._search_media(ctx, medium="ANIME", title=title)
        return await self._build_message(ctx, medium="ANIME", entry=entry)

    @commands.command(aliases=['m'])
    async def manga(self, ctx, *, title: str):
        """Searches for a manga on AniList"""
        entry = await self._search_media(ctx, medium="MANGA", title=title)
        return await self._build_message(ctx, medium="MANGA", entry=entry)

    @commands.command()
    async def review(self, ctx, *, title: str):
        """Senpai's anime reviews"""
        if not self.senpai:
            return await ctx.send('Senpai has not configured reviews yet!')

        medium = "ANIME"
        entry = await self._search_media(ctx, medium=medium, title=title)

        if entry is not None:
            entryTitle = entry['title']['english'] if entry['title']['english'] else entry['title']['romaji']
            listEntry = entry['mediaListEntry']
            if not listEntry:
                return await ctx.send(f"Senpai hasn't watched {entryTitle} yet!")

            review = listEntry['notes']

            if not review:
                # if review not in notes, try to find the actual review
                query = """
                query {{
                    Review (mediaId: {mediaId}, userId: {userId}, mediaType: {medium}) {{
                        body(asHtml: false)
                    }}
                }}
                """
                ql = gql(query.format(mediaId=entry['id'], userId=listEntry['userId'], medium=medium))
                results = self.client.execute(ql)
                if results['Review'] is None:
                    review = "Senpai hasn't reviewed this anime!"
                else:
                    review = results['Review']['body']

            review = BeautifulSoup(review, "lxml").text
            title = f"Senpai's Review of {entryTitle}"

            split = False
            while len(review) > 2044:
                part = (review[:2044] + '...')
                review = '...' + review[2044:]
                pembed = discord.Embed(title=title, url=entry['siteUrl'], description=part)
                await ctx.send(embed=pembed)
                if not split:
                    title = title + ' (cont)'
                    split = True

            embed = discord.Embed(title=title, url=entry['siteUrl'], description=review)
            embed.add_field(name='Type', value=entry['format'])
            embed.add_field(name='Episodes Watched', value=listEntry['progress'])
            embed.add_field(name='Final Score',
                            value=':star: ' + str(listEntry['score']) + '/100 ' + tscore[round(listEntry['score']/10)])
            embed.add_field(name='Status', value=listEntry['status'])
            if listEntry['completedAt']['year'] is not None:
                embed.add_field(name='Completed On', value=str(listEntry['completedAt']['year'])+'-'+str(listEntry['completedAt']['month'])+'-'+str(listEntry['completedAt']['day']))
            embed.set_image(url=entry['coverImage']['large'])
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Anime(bot))
