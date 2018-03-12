import configparser
import discord
from discord.ext import commands

import sys, traceback

initial_extensions = ['cogs.mal', 'cogs.weeb']

def get_prefix(bot, message):
    prefixes = ['y.', 'senpai ']
    return commands.when_mentioned_or(*prefixes)(bot, message)

bot = commands.Bot(command_prefix=get_prefix)

@bot.event
async def on_ready():
    print(
        f'\n\nLogged in as: {bot.user.name} - {bot.user.id}\nVersion: {discord.__version__}\n')
    await bot.change_presence(game=discord.Game(name='with Senpai'))


if __name__ == '__main__':
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            print(f'Failed to load extension {extension}.', file=sys.stderr)
            traceback.print_exc()

config = configparser.ConfigParser()
config.read('config.ini')

bot.run(config['DEFAULT']['token'])
