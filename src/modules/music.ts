import Discord from 'discord.js';
import Conf from 'conf';
import ytdl from 'ytdl-core';
import ytsr from 'ytsr';

import { Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';

type QueueEntry = {
  info: ytdl.videoInfo;
  msg: Discord.Message;
};

export class Music implements Module {
  private connection: Discord.VoiceConnection | null = null;
  private dispatcher: Discord.StreamDispatcher | null = null;
  private timeout: NodeJS.Timeout | null = null;

  private queue: QueueEntry[] = [];

  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    // join
    regCmd(
      {
        name: 'join',
        description: 'Joins the voice channel',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.join(msg, args);
      }
    );

    // leave
    regCmd(
      {
        name: 'leave',
        description: 'Leaves the voice channel',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.leave(msg, args);
      }
    );

    // play
    regCmd(
      {
        name: 'play',
        description: 'Plays a track from Youtube',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.play(msg, args);
      }
    );

    // stop
    regCmd(
      {
        name: 'stop',
        description: 'Stops currently playing tracks',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.stop(msg, args);
      }
    );

    // skip
    regCmd(
      {
        name: 'skip',
        description: 'Skips currently playing track',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.skip(msg, args);
      }
    );

    // clear queue
    regCmd(
      {
        name: 'clearqueue',
        description: 'Clears the track queue',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.clear(msg, args);
      }
    );

    // check queue
    regCmd(
      {
        name: 'checkqueue',
        description: 'List all tracks in the queue',
        permissions: ['SEND_MESSAGES', 'CONNECT', 'SPEAK'],
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.checkqueue(msg, args);
      }
    );

    console.log('Music module loaded');
  }

  private async timeoutCheck() {
    if (this.connection && !this.dispatcher) {
      await this.connection.disconnect();

      this.connection = null;
      this.dispatcher = null;
      this.queue.length = 0;
    }

    this.timeout = null;
  }

  private async search(key: string) {
    const results = await ytsr(key, { limit: 10 });
    const first = results.items.find((element) => {
      return element.type == 'video' && element.url;
    });

    if (first && first.type == 'video') {
      return first.url;
    }

    return null;
  }

  private async startPlaying(info: ytdl.videoInfo, msg: Discord.Message) {
    if (!this.connection && msg.member?.voice.channel) {
      try {
        this.connection = await msg.member.voice.channel.join();
      } catch (e) {
        msg.reply('I do not have permission to join your channel!');
      }
    }

    if (this.connection) {
      if (this.timeout) {
        clearTimeout(this.timeout);
        this.timeout = null;
      }

      this.dispatcher = this.connection.play(
        ytdl.downloadFromInfo(info, {
          filter: 'audioonly',
          quality: 'highestaudio',
        }),
        { volume: 0.1 }
      );

      this.dispatcher.on('start', async () => {
        const embed = new Discord.MessageEmbed()
          .setTitle('🎶 Now Playing: ' + info.videoDetails.title)
          .setColor(0xff0000)
          .setDescription('Queued by ' + msg.author.toString())
          .setImage(
            info.videoDetails.thumbnails[
              info.videoDetails.thumbnails.length - 2
            ].url
          )
          .setURL(info.videoDetails.video_url);
        await msg.channel.send(embed);
      });

      this.dispatcher.on('finish', async () => {
        this.dispatcher?.destroy();
        this.dispatcher = null;

        if (!this.queue.length) {
          this.timeout = setTimeout(async () => {
            await this.timeoutCheck();
          }, 60000);
        } else {
          // pop the queue
          const next = this.queue.shift() as QueueEntry;
          await this.startPlaying(next?.info, next?.msg);
        }
      });
    }
  }

  private async join(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;

    if (!msg.member?.voice.channel) {
      msg.reply('You need to join a voice channel first!');
      return;
    }

    try {
      this.connection = await msg.member.voice.channel.join();
    } catch (e) {
      msg.reply('I do not have permission to join your channel!');
    }
  }

  private async leave(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!msg.member) return;

    // if same channel
    if (
      this.connection &&
      msg.member?.voice.channel &&
      msg.member.voice.channel == this.connection.channel
    ) {
      await this.connection.disconnect();

      // these are destroyed
      this.connection = null;
      this.dispatcher = null;
      this.queue.length = 0;
    }
  }

  private async play(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!msg.member) return;

    if (!msg.member.voice.channel) {
      msg.reply('You need to join a voice channel first!');
      return;
    }

    if (
      this.connection &&
      msg.member.voice.channel != this.connection.channel
    ) {
      msg.reply('You need to be in the same voice channel!');
      return;
    }

    let url = args[0];

    if (!url) {
      msg.reply('Error: Invalid URL');
      return;
    } else if (!url.startsWith('http')) {
      // do a search
      const search = args.join(' ');
      const found = await this.search(search);

      if (!found) {
        msg.reply('No video results found!');
        return;
      }

      url = found;
    }

    // Handled msg
    await msg.delete();

    ytdl
      .getInfo(url)
      .then(async (info) => {
        if (this.dispatcher || this.queue.length) {
          // add to queue
          this.queue.push({ info, msg });

          const embed = new Discord.MessageEmbed()
            .setColor(0xff0000)
            .setDescription(
              `Queued [${info.videoDetails.title}](${
                info.videoDetails.video_url
              }) from ${msg.author.toString()}`
            );

          await msg.channel.send(embed);
          return;
        }

        await this.startPlaying(info, msg);
      })
      .catch((err) => {
        msg.reply('Error: URL is not a YouTube domain!');
      });
  }

  private async stop(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!msg.member) return;

    // if same channel
    if (
      this.dispatcher &&
      this.connection &&
      msg.member.voice.channel &&
      msg.member.voice.channel == this.connection.channel
    ) {
      msg.react('🛑');

      this.dispatcher.destroy();
      this.dispatcher = null;
      this.queue.length = 0;

      this.timeout = setTimeout(async () => {
        await this.timeoutCheck();
      }, 60000);
    }
  }

  private async skip(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!msg.member) return;

    // if same channel
    if (
      this.dispatcher &&
      this.connection &&
      msg.member.voice.channel &&
      msg.member.voice.channel == this.connection.channel
    ) {
      if (!this.queue.length) {
        msg.reply('No tracks queued!');
        return;
      }

      msg.react('👌');

      this.dispatcher.destroy();
      this.dispatcher = null;

      // pop the queue
      const next = this.queue.shift() as QueueEntry;
      await this.startPlaying(next?.info, next?.msg);
    }
  }

  private async clear(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!msg.member) return;

    // if same channel
    if (
      this.connection &&
      msg.member.voice.channel &&
      msg.member.voice.channel == this.connection.channel
    ) {
      if (!this.queue.length) {
        msg.reply('No tracks queued!');
        return;
      }

      this.queue.length = 0;

      const embed = new Discord.MessageEmbed()
        .setColor(0x00ff00)
        .setDescription(`Queued cleared by ${msg.author.toString()}`);

      await msg.channel.send(embed);
    }
  }

  private async checkqueue(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!msg.member) return;

    if (this.connection) {
      if (!this.queue.length) {
        msg.reply('No tracks queued!');
        return;
      }

      let list = '';

      this.queue.forEach((entry) => {
        list += `[${entry.info.videoDetails.title}](${
          entry.info.videoDetails.video_url
        }) from ${entry.msg.author.toString()}\n`;
      });

      const embed = new Discord.MessageEmbed()
        .setTitle('🎶 Next Up')
        .setColor(0x00ff00)
        .setDescription(list);

      await msg.channel.send(embed);
    }
  }
}
