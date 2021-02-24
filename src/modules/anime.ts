import Discord from 'discord.js';
import Conf from 'conf';
import config from 'config';
import { stripHtml } from 'string-strip-html';
import { GraphQLClient, gql } from 'graphql-request';

import { Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';
import { Media, MediaType, Query } from '../types/anilist';

const query = gql`
  query($page: Int!, $search: String!, $medium: MediaType!) {
    Page(page: $page, perPage: 10) {
      pageInfo {
        total
        currentPage
        lastPage
        hasNextPage
        perPage
      }
      media(search: $search, type: $medium) {
        id
        title {
          english
          romaji
        }
        type
        format
        status
        description(asHtml: false)
        startDate {
          year
          month
          day
        }
        endDate {
          year
          month
          day
        }
        episodes
        chapters
        volumes
        meanScore
        siteUrl
        coverImage {
          large
        }
        mediaListEntry {
          id
          userId
          status
          score(format: POINT_10_DECIMAL)
          progress
          notes
          completedAt {
            year
            month
            day
          }
        }
      }
    }
  }
`;

export class Anime extends Module {
  private gqlClient: GraphQLClient | null = null;

  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    super(regCmd, client, store);

    const token = config.get<string>('anilist.token');

    if (token) {
      this.gqlClient = new GraphQLClient('https://graphql.anilist.co', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
      });

      console.log('Anilist gql client initialized');
    } else {
      console.log('Anilist gql client inactive: no token configured');
    }

    console.log('Anime module loaded');
  }

  load(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>): void {
    regCmd('anime', async (msg: Discord.Message, args: string[]) => {
      await this.anime(msg, args);
    });

    regCmd('manga', async (msg: Discord.Message, args: string[]) => {
      await this.manga(msg, args);
    });
  }

  private async search(msg: Discord.Message, type: MediaType, arg: string) {
    if (!msg.guild) return;
    if (!arg) return;
    if (!(msg.channel.type === 'text')) return;

    if (this.gqlClient) {
      let curpage = 1;

      let data = await this.gqlClient.request<Query>(query, {
        page: curpage,
        search: arg,
        medium: type,
      });

      let pageinfo = data.Page?.pageInfo;

      if (!pageinfo) {
        await msg.reply('Error querying Anilist! Please try again later.');
        return null;
      }

      let entry = null;

      if (pageinfo?.total == 0) {
        await msg.reply("I couldn't find anything with that name!");
        return null;
      }

      if (pageinfo.total && pageinfo.total > 1) {
        let media = data.Page?.media;
        let pages: string[] = [];

        if (Array.isArray(media)) {
          media.forEach((entry, idx) => {
            const line = `[${idx + 1}] ${
              entry?.title?.english ?? entry?.title?.romaji
            }`;
            pages.push(line);
          });
        }

        let page = pages.join('\n');

        if (pageinfo['hasNextPage']) {
          page += '\n[...] Next Page';
        }

        let pageEmbed = new Discord.MessageEmbed()
          .setTitle('Which one are you talking about?')
          .setDescription(page);

        const pageSelect = await msg.channel.send(pageEmbed);

        while (!entry) {
          const filter = (m: Discord.Message) =>
            (Number.isInteger(parseInt(m.content)) ||
              m.content == '..' ||
              m.content == '...') &&
            m.channel == msg.channel &&
            m.author == msg.author;

          await msg.channel
            .awaitMessages(filter, { max: 1, time: 30000, errors: ['time'] })
            .then(async (replies) => {
              if (media && replies.size) {
                const reply = replies.first() as Discord.Message;

                if (reply.content == '..') {
                  if (curpage > 0) curpage -= 1;
                } else if (reply.content == '...') {
                  if (pageinfo?.hasNextPage) curpage += 1;
                } else {
                  entry = media[parseInt(reply.content) - 1];
                  await pageSelect.delete();
                }
                await reply.delete();
              }
            })
            .catch(async () => {
              await pageSelect.delete();
            });

          if (!entry) {
            data = await this.gqlClient.request<Query>(query, {
              page: curpage,
              search: arg,
              medium: type,
            });

            pageinfo = data.Page?.pageInfo;
            media = data.Page?.media;
            pages = [];

            if (Array.isArray(media)) {
              media.forEach((entry, idx) => {
                const line = `[${idx + 1}] ${
                  entry?.title?.english ?? entry?.title?.romaji
                }`;
                pages.push(line);
              });
            }

            let page = pages.join('\n');

            if (curpage > 0) {
              page += '\n[..] Previous Page';
            }

            if (pageinfo?.hasNextPage) {
              page += '\n[...] Next Page';
            }

            pageEmbed.setDescription(page);
            await pageSelect.edit(pageEmbed);
          }
        }
      } else if (data.Page?.media) {
        entry = data.Page?.media[0];
      }

      return entry;
    }

    return null;
  }

  private async buildEmbed(
    msg: Discord.Message,
    type: MediaType,
    entry: Media | null | undefined
  ) {
    if (!entry) return;

    let title = entry.title?.english ?? entry.title?.romaji;
    let embed = new Discord.MessageEmbed()
      .setTitle(title)
      .addField('Type', entry.format, true);

    if (entry.siteUrl) {
      embed.setURL(entry.siteUrl);
    }

    if (type == MediaType.Manga) {
      embed
        .addField('Chapters', entry.chapters, true)
        .addField('Volumes', entry.volumes, true);
    } else {
      embed.addField('Episodes', entry.episodes, true);
    }

    embed
      .addField('Mean Score', ':star: ' + entry.meanScore + '/100', true)
      .addField('Status', entry.status, true);

    let sd = entry.startDate;
    let ed = entry.endDate;

    embed.addField(
      'Start Date',
      sd?.year + '-' + sd?.month + '-' + sd?.day,
      true
    );

    if (ed?.year) {
      embed.addField('End Date', ed.year + '-' + ed.month + '-' + ed.day, true);
    }

    let synopsis = stripHtml(entry.description as string).result;

    if (synopsis.length > 1024) {
      synopsis = synopsis.slice(0, 1021) + '..';
    }

    embed.addField('Synopsis', synopsis);
    embed.setImage(entry.coverImage?.large as string);
    await msg.channel.send(embed);
  }

  private async anime(msg: Discord.Message, args: string[]) {
    const arg = args.join(' ');
    const entry = await this.search(msg, MediaType.Anime, arg);
    await this.buildEmbed(msg, MediaType.Anime, entry);
  }

  private async manga(msg: Discord.Message, args: string[]) {
    const arg = args.join(' ');
    const entry = await this.search(msg, MediaType.Manga, arg);
    await this.buildEmbed(msg, MediaType.Manga, entry);
  }
}
