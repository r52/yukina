import Discord, { PermissionString } from 'discord.js';
import Conf from 'conf';

import { ConfStore } from 'types/store';

export type CommandInfo = {
  name: string;
  description: string;
  usage?: string;
  aliases?: string[];
  permissions?: PermissionString | PermissionString[];
};

export type CommandFunction = (msg: Discord.Message, args: string[]) => void;
export type RegCmd = (cmdinfo: CommandInfo, fn: CommandFunction) => void;

export interface ModuleConstructor {
  new (regCmd: RegCmd, client: Discord.Client, store: Conf<ConfStore>): Module;
}

export interface Module {
  name: string;

  getHelp(prefix: string): [string, string];
}

export function createModule(
  ctor: ModuleConstructor,
  regCmd: RegCmd,
  client: Discord.Client,
  store: Conf<ConfStore>
): Module {
  return new ctor(regCmd, client, store);
}
