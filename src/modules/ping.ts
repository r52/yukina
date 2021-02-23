import Discord from 'discord.js';
import Conf from 'conf';

import { Module } from '../module';
import { ConfStore } from 'types/store';

export class Ping extends Module {
  constructor(
    regCmd: (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => void,
    client: Discord.Client,
    store: Conf<ConfStore>
  ) {
    super(regCmd, client, store);

    console.log('Ping module loaded');
  }

  load(
    regCmd: (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => void,
    client: Discord.Client,
    store: Conf<ConfStore>
  ): void {
    regCmd('ping', async (msg: Discord.Message, args: string[]) => {
      await msg.channel.send('Pong');
    });
  }
}
