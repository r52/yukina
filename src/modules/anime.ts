import Discord, { User } from 'discord.js';
import Conf from 'conf';
import config from 'config';
import { stripHtml } from 'string-strip-html';
import { GraphQLClient, gql } from 'graphql-request';

import { CommandInfo, Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';
import { Media, MediaType, Query } from '../types/anilist';

const emoteUCTable = [
  '0️⃣',
  '1️⃣',
  '2️⃣',
  '3️⃣',
  '4️⃣',
  '5️⃣',
  '6️⃣',
  '7️⃣',
  '8️⃣',
  '9️⃣',
  '🔟',
  '⬅️',
  '➡️',
];

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

export class Anime implements Module {
  name = 'Anime';

  private gqlClient: GraphQLClient | null = null;

  private commands = new Discord.Collection<string, CommandInfo>([
    [
      'anime',
      {
        name: 'anime',
        description: 'Searches anilist.co for the specified anime',
        permissions: 'SEND_MESSAGES',
        usage: '<name of the anime to search for>',
      },
    ],
    [
      'manga',
      {
        name: 'manga',
        description: 'Searches anilist.co for the specified manga',
        permissions: 'SEND_MESSAGES',
        usage: '<name of the manga to search for>',
      },
    ],
  ]);

  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    const token = config.get<string>('anilist.token');

    if (token) {
      this.gqlClient = new GraphQLClient('https://graphql.anilist.co', {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
      });

      regCmd(
        this.commands.get('anime') as CommandInfo,
        async (msg: Discord.Message, args: string[]) => {
          await this.anime(msg, args);
        }
      );

      regCmd(
        this.commands.get('manga') as CommandInfo,
        async (msg: Discord.Message, args: string[]) => {
          await this.manga(msg, args);
        }
      );

      console.log('Anilist gql client initialized');
    } else {
      console.log('Anilist gql client inactive: no token configured');
    }

    console.log(`${this.name} module loaded`);
  }

  private buildSelector(
    medialist: Media[],
    embed: Discord.MessageEmbed,
    isFirstPage: boolean,
    hasNextPage: boolean
  ) {
    const sec1: string[] = [],
      sec2: string[] = [];

    medialist.forEach((entry, idx) => {
      const line = `${emoteUCTable[idx + 1]} ${
        entry?.title?.english ?? entry?.title?.romaji
      }`;

      if (idx < 5) {
        sec1.push(line);
      } else {
        sec2.push(line);
      }
    });

    let pec1 = sec1.join('\n');
    let pec2 = sec2.join('\n');

    if (!isFirstPage) {
      pec1 += '\n[..] Previous Page';
    }

    if (hasNextPage) {
      pec2 += '\n[...] Next Page';
    }

    embed.fields.length = 0;
    embed.addField('Select:', pec1, true);

    if (pec2) {
      embed.addField('cont', pec2, true);
    }
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
        let media = data.Page?.media as Media[];

        let pageEmbed = new Discord.MessageEmbed()
          .setTitle('Which one are you talking about?')
          .setColor(0x2ecc71);

        this.buildSelector(
          media,
          pageEmbed,
          true,
          pageinfo.hasNextPage as boolean
        );

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
              if (replies.size) {
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
            media = data.Page?.media as Media[];

            this.buildSelector(
              media,
              pageEmbed,
              curpage == 0,
              pageinfo?.hasNextPage as boolean
            );

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
      .addField('Type', entry.format, true)
      .setColor(0x2ecc71);

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

    embed
      .addField('Synopsis', synopsis)
      .setImage(entry.coverImage?.large as string);

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

  public getHelp(prefix: string): [string, string] {
    let cmds: string[] = [];

    this.commands.forEach((cmd) => {
      cmds.push(`${prefix}${cmd.name}`);
    });

    const desc = cmds.join('\n');

    return [this.name, desc];
  }
}
