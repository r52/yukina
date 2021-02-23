import Discord from 'discord.js';
import Conf from 'conf';

import { ConfStore } from 'types/store';

export abstract class Module {
  constructor(
    regCmd: (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => void,
    client: Discord.Client,
    store: Conf<ConfStore>
  ) {
    this.load(regCmd, client, store);
  }

  abstract load(
    regCmd: (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => void,
    client: Discord.Client,
    store: Conf<ConfStore>
  ): void;
}
