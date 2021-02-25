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

  client.user
    ?.setPresence({
      activity: {
        name: 'with senpai',
        type: 'PLAYING',
      },
    })
    .catch(console.error);
});

const token = config.get<string>('discord.token');

if (token.trim()) {
  client.login(token);
} else {
  console.error('No Discord token configured');
}
