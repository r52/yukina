import Discord from 'discord.js';
import Conf from 'conf';

import { ConfStore } from 'types/store';

export type RegCmd = (
  cmd: string,
  fn: (msg: Discord.Message, args: string[]) => void
) => void;

export abstract class Module {
  constructor(regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>) {
    this.load(regCmd, client, store);
  }

  abstract load(
    regCmd: RegCmd,
    client: Discord.Client,
    store: Conf<ConfStore>
  ): void;
}
