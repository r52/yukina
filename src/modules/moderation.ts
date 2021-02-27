import Discord from 'discord.js';
import Conf from 'conf';

import { CommandInfo, Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';

export class Moderation implements Module {
  name = 'Moderation';

  private commands = new Discord.Collection<string, CommandInfo>([
    [
      'prune',
      {
        name: 'prune',
        description: 'Prunes the last # messages in a channel',
        permissions: 'MANAGE_MESSAGES',
        usage: '<# of messages to prune>',
      },
    ],
  ]);

  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    regCmd(
      this.commands.get('prune') as CommandInfo,
      async (msg: Discord.Message, args: string[]) => {
        await this.prune(msg, args);
      }
    );

    console.log(`${this.name} module loaded`);
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

  public getHelp(prefix: string): [string, string] {
    let cmds: string[] = [];

    this.commands.forEach((cmd) => {
      cmds.push(`${prefix}${cmd.name}`);
    });

    const desc = cmds.join('\n');

    return [this.name, desc];
  }
}
