import Discord from 'discord.js';
import Conf from 'conf';

import { Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';

export class Ping implements Module {
  name = 'Ping';

  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    regCmd(
      { name: 'ping', description: 'Pong!' },
      async (msg: Discord.Message, args: string[]) => {
        await msg.channel.send('Pong');
      }
    );

    console.log(`${this.name} module loaded`);
  }

  public getHelp(prefix: string): [string, string] {
    const desc = `${prefix}ping`;
    return [this.name, desc];
  }
}
