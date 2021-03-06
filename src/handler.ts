import Discord from 'discord.js';
import Conf from 'conf';

import { ConfStore } from 'types/store';
import {
  CommandFunction,
  CommandInfo,
  createModule,
  Module,
  RegCmd,
} from './module';
import { Ping } from './modules/ping';
import { Music } from './modules/music';
import { Moderation } from './modules/moderation';
import { Anime } from './modules/anime';

export class Handler {
  private client: Discord.Client;
  private store: Conf<ConfStore>;

  private prefix: string;

  private commands = new Discord.Collection<
    string,
    { info: CommandInfo; fn: CommandFunction }
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
    const regcmd: RegCmd = (cmdinfo: CommandInfo, fn: CommandFunction) => {
      this.registerCommand(cmdinfo, fn);
    };

    // load modules
    this.modules.push(createModule(Ping, regcmd, this.client, this.store));
    this.modules.push(createModule(Music, regcmd, this.client, this.store));
    this.modules.push(
      createModule(Moderation, regcmd, this.client, this.store)
    );
    this.modules.push(createModule(Anime, regcmd, this.client, this.store));

    console.log('All Modules loaded');

    this.registerCommand(
      { name: 'help', description: 'Displays this/usage', usage: '<command>' },
      (msg, args) => {
        this.getHelp(msg, args);
      }
    );
  }

  public registerCommand(cmdinfo: CommandInfo, fn: CommandFunction) {
    if (this.commands.has(cmdinfo.name)) {
      console.error('Command', cmdinfo.name, 'already exists.');
      return;
    }

    this.commands.set(cmdinfo.name, { info: cmdinfo, fn: fn });

    console.log('Command', cmdinfo.name, 'registered.');
  }

  private handleMessage(msg: Discord.Message) {
    if (!msg.content.startsWith(this.prefix) || msg.author.bot) return;

    const args = msg.content.slice(this.prefix.length).trim().split(/ +/);
    const cmd = args.shift();

    if (cmd) {
      // handle aliases
      const command =
        this.commands.get(cmd) ||
        this.commands.find((c) => {
          if (c.info.aliases) {
            return c.info.aliases.includes(cmd);
          }

          return false;
        });

      if (command) {
        // check permissions
        if (command.info.permissions && msg.channel.type == 'text') {
          const authorPerms = msg.channel.permissionsFor(msg.author);

          let hasPerms = false;

          if (authorPerms) {
            if (Array.isArray(command.info.permissions)) {
              hasPerms = command.info.permissions.every((p) => {
                return authorPerms.has(p);
              });
            } else {
              hasPerms = authorPerms.has(command.info.permissions);
            }
          }

          if (!hasPerms) {
            return;
          }
        }

        command.fn(msg, args);
      }
    }
  }

  private async getHelp(msg: Discord.Message, args: string[]) {
    const arg = args[0];

    if (!arg) {
      // generic help
      const embed = new Discord.MessageEmbed()
        .setTitle('Yukina help')
        .setColor(0x800080);

      this.modules.forEach((module) => {
        const [modname, help] = module.getHelp(this.prefix);
        embed.addField(modname, help, true);
      });

      embed.setDescription(`Use ${this.prefix}help <command> for more info`);

      await msg.channel.send(embed);

      return;
    }

    // specific command
    const command =
      this.commands.get(arg) ||
      this.commands.find((c) => {
        if (c.info.aliases) {
          return c.info.aliases.includes(arg);
        }

        return false;
      });

    if (command) {
      const embed = new Discord.MessageEmbed()
        .setTitle(`${this.prefix}${command.info.name}`)
        .setColor(0x800080);

      if (command.info.permissions) {
        embed.addField(
          'Permissions Required',
          command.info.permissions.toString(),
          true
        );
      }

      if (command.info.aliases) {
        embed.addField('Aliases', command.info.aliases.join(', '), true);
      }

      if (command.info.usage) {
        embed.addField(
          'Usage',
          `${this.prefix}${command.info.name} ${command.info.usage}`,
          true
        );
      }

      embed.setDescription(command.info.description);

      await msg.channel.send(embed);
    }
  }
}
