import Discord from 'discord.js';
import Conf from 'conf';
import ytdl from 'ytdl-core';

import { Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';

export class Music extends Module {
  private connection: Discord.VoiceConnection | null = null;
  private dispatcher: Discord.StreamDispatcher | null = null;
  private timeout: NodeJS.Timeout | null = null;

  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    super(regCmd, client, store);

    console.log('Music module loaded');
  }

  load(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>): void {
    // join
    regCmd('join', async (msg: Discord.Message, args: string[]) => {
      await this.join(msg, args);
    });

    // leave
    regCmd('leave', async (msg: Discord.Message, args: string[]) => {
      await this.leave(msg, args);
    });

    // play
    regCmd('play', async (msg: Discord.Message, args: string[]) => {
      await this.play(msg, args);
    });

    // stop
    regCmd('stop', async (msg: Discord.Message, args: string[]) => {
      await this.stop(msg, args);
    });
  }

  private async timeoutCheck() {
    if (this.connection && !this.dispatcher) {
      await this.connection.disconnect();

      this.connection = null;
      this.dispatcher = null;
    }

    this.timeout = null;
  }

  private async join(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;

    // Only try to join the sender's voice channel if they are in one themselves
    if (!msg.member?.voice.channel) {
      msg.reply('You need to join a voice channel first!');
      return;
    }

    this.connection = await msg.member.voice.channel.join();
  }

  private async leave(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;

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

    const url = args[0];

    if (!url) {
      msg.reply('Error: Invalid URL');
      return;
    }

    // Handled msg
    await msg.delete();

    ytdl
      .getBasicInfo(url)
      .then(async (info) => {
        if (!this.connection && msg.member?.voice.channel) {
          this.connection = await msg.member.voice.channel.join();
        }

        if (this.connection) {
          // TODO: queue

          if (this.timeout) {
            clearTimeout(this.timeout);
            this.timeout = null;
          }

          this.dispatcher = this.connection.play(
            ytdl(args[0], { filter: 'audioonly', quality: 'highestaudio' }),
            { volume: 0.1 }
          );

          this.dispatcher.on('start', async () => {
            const embed = new Discord.MessageEmbed()
              .setTitle('🎶 Now Playing: ' + info.videoDetails.title)
              .setColor(0xff0000)
              .setDescription(url)
              .setURL(url);
            await msg.channel.send(embed);
          });

          this.dispatcher.on('finish', () => {
            // TODO queue
            this.dispatcher?.destroy();
            this.dispatcher = null;

            this.timeout = setTimeout(async () => {
              await this.timeoutCheck();
            }, 60000);
          });
        }
      })
      .catch((err) => {
        msg.reply('Error: URL is not a YouTube domain!');
      });
  }

  private async stop(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;

    if (this.dispatcher) {
      this.dispatcher.destroy();
      this.dispatcher = null;
    }
  }
}
