import Discord from 'discord.js';
import Conf from 'conf';

import { ConfStore } from 'types/store';
import { Module } from './module';
import { Ping } from './modules/ping';
import { Music } from './modules/music';

export class Handler {
  private client: Discord.Client;
  private store: Conf<ConfStore>;

  private prefix: string;

  private commands = new Map<
    string,
    (msg: Discord.Message, args: string[]) => void
  >();

  private modules: Module[] = [];

  constructor(client: Discord.Client, store: Conf<ConfStore>) {
    this.client = client;
    this.store = store;

    // prefix
    this.prefix = store.get('prefix');

    store.onDidChange('prefix', (n) => {
      if (n) {
        this.prefix = n as string;

        console.log('Prefix changed to', this.prefix);
      }
    });

    console.log('Prefix loaded as', this.prefix);

    client.on('message', async (msg) => {
      this.handleMessage(msg);
    });

    console.log('Handler created');
  }

  public loadModules() {
    const regcmd = (
      cmd: string,
      fn: (msg: Discord.Message, args: string[]) => void
    ) => {
      this.registerCommand(cmd, fn);
    };

    // load modules
    this.modules.push(new Ping(regcmd, this.client, this.store));
    this.modules.push(new Music(regcmd, this.client, this.store));

    console.log('All Modules loaded');
  }

  public registerCommand(
    cmd: string,
    fn: (msg: Discord.Message, args: string[]) => void
  ) {
    if (this.commands.has(cmd)) {
      console.error('Command', cmd, 'already exists.');
      return;
    }

    this.commands.set(cmd, fn);

    console.log('Command', cmd, 'registered.');
  }

  private handleMessage(msg: Discord.Message) {
    if (!msg.content.startsWith(this.prefix) || msg.author.bot) return;

    const args = msg.content.slice(this.prefix.length).trim().split(/ +/);
    const cmd = args.shift();

    if (cmd && this.commands.has(cmd)) {
      const fn = this.commands.get(cmd);

      if (fn) {
        fn(msg, args);
      }
    }
  }
}
