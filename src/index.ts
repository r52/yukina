import Discord from 'discord.js';
import config from 'config';
import Conf from 'conf';
import { Handler } from './handler';

import { ConfStore } from 'types/store';

const client = new Discord.Client();

const store = new Conf<ConfStore>({
  defaults: {
    prefix: 'y.',
  },
  watch: true,
});

// prep
const handler = new Handler(client, store);

// loaded
client.once('ready', () => {
  handler.loadModules();

  console.log('Ready!');
});

const discordtoken = config.get<string>('discord.token');

if (discordtoken.trim()) {
  client.login(discordtoken);
} else {
  console.error('No Discord token configured');
}
