import Discord from 'discord.js';
import Conf from 'conf';

import { Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';

export class Moderation implements Module {
  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    regCmd(
      {
        name: 'prune',
        description: 'Prunes the last # messages',
        permissions: 'MANAGE_MESSAGES',
      },
      async (msg: Discord.Message, args: string[]) => {
        await this.prune(msg, args);
      }
    );

    console.log('Moderation module loaded');
  }

  private async prune(msg: Discord.Message, args: string[]) {
    if (!msg.guild) return;
    if (!args.length) return;
    if (!(msg.channel.type === 'text')) return;

    let num = Number(args[0]);

    if (num > 0) {
      // Also get rid of the command
      num++;

      msg.channel.messages.fetch({ limit: num }).then(async (messages) => {
        if (msg.channel.type === 'text') {
          await msg.channel.bulkDelete(messages);
        }
      });
    }
  }
}
