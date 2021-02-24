import Discord from 'discord.js';
import Conf from 'conf';

import { Module } from '../module';
import { ConfStore } from 'types/store';

export class Moderation extends Module {
  constructor(
    regCmd: (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => void,
    client: Discord.Client,
    store: Conf<ConfStore>
  ) {
    super(regCmd, client, store);

    console.log('Moderation module loaded');
  }

  load(
    regCmd: (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => void,
    client: Discord.Client,
    store: Conf<ConfStore>
  ): void {
    regCmd('prune', async (msg: Discord.Message, args: string[]) => {
      await this.prune(msg, args);
    });
  }

  private async prune(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!args.length) return;

    let num = Number(args[0]);

    if (num > 0) {
      // Also get rid of the command
      num++;

      msg.channel.messages.fetch({ limit: num }).then((messages) => {
        messages.each(async (m) => {
          await m.delete();
        });
      });
    }
  }
}
