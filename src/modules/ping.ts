import Discord from 'discord.js';
import Conf from 'conf';

import { Module, RegCmd } from '../module';
import { ConfStore } from 'types/store';

export class Ping implements Module {
  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    regCmd(
      { name: 'ping', description: 'Pong!' },
      async (msg: Discord.Message, args: string[]) => {
        await msg.channel.send('Pong');
      }
    );

    console.log('Ping module loaded');
  }
}
