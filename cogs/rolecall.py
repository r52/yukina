import configparser
import json
import discord
from discord.ext import commands

config = configparser.ConfigParser()
config.read('config.ini')

class RoleCall:
    def __init__(self, bot):
        self.bot = bot

    def _load_config(self, server_id: int):
        if str(server_id) not in config:
            config[str(server_id)] = {}
            return {}

        section = config[str(server_id)]
        if 'rolecall' not in section:
            return {}

        lne = section['rolecall']
        cfg = {}

        try:
            cfg = json.loads(lne)
        except JSONDecodeError:
            print("Invalid config")

        return cfg

    def _save_config(self, server_id: int, cfg):
        if str(server_id) not in config:
            config[str(server_id)] = {}

        config[str(server_id)]['rolecall'] = json.dumps(cfg)
        with open('config.ini', 'w') as configfile:
            config.write(configfile)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def acr(self, ctx, role: str):
        """Adds a role to the list of callable roles"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg:
            cfg['crs'] = set()

        if role in cfg['crs']:
            await ctx.send(f"The role '{role}' is already callable.")
            return

        cfg['crs'].add(role)
        self._save_config(ctx.guild.id, cfg)
        await ctx.send(f"The role '{role}' is now callable.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    async def rcr(self, ctx, role: str):
        """Removes a role from the list of callable roles"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg:
            cfg['crs'] = set()

        if role not in cfg['crs']:
            await ctx.send(f"The role '{role}' is not in the list of callable roles.")
            return

        cfg['crs'].remove(role)
        self._save_config(ctx.guild.id, cfg)
        await ctx.send(f"The role '{role}' has been removed from callable roles.")

    @commands.command()
    @commands.guild_only()
    async def lcr(self, ctx):
        """List all callable roles on this server"""
        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg or len(cfg['crs']) == 0:
            await ctx.send("There are no callable roles on this server.")
            return

        rols = '\n'.join(f'{k}' for k in enumerate(cfg['crs']))
        await ctx.send(f"List of callable roles:\n`{rols}`")

    @commands.command()
    @commands.guild_only()
    async def iam(self, ctx, role: str):
        """Add yourself to a callable role"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        if rol in ctx.message.author.roles:
            await ctx.send(f"You already have the role '{role}'.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg or role not in cfg['crs']:
            await ctx.send(f"The role '{role}' is not in the list of callable roles.")
            return

        await ctx.message.author.add_roles(rol, "y.iam")
        await ctx.send(f"You've been added to '{role}'.")

    @commands.command()
    @commands.guild_only()
    async def iamnot(self, ctx, role: str):
        """Remove yourself from a callable role"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        if rol not in ctx.message.author.roles:
            await ctx.send(f"You are not part of the role '{role}'.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg or role not in cfg['crs']:
            await ctx.send(f"The role '{role}' is not in the list of callable roles.")
            return

        await ctx.message.author.remove_roles(rol, "y.iamnot")
        await ctx.send(f"You've been removed from '{role}'.")

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(change_nickname=True)
    @commands.cooldown(1, 10.0, commands.BucketType.guild)
    async def call(self, ctx, role: str):
        """Calls a callable role (you must be a member)"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        if rol not in ctx.message.author.roles:
            await ctx.send(f"You are not part of the role '{role}'. You can only use this command if you are part of the role.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg or role not in cfg['crs']:
            await ctx.send(f"The role '{role}' is not in the list of callable roles.")
            return

        # Make role temporarily mentionable if it isn't
        temp_mention = False
        if not rol.mentionable:
            rol.edit(mentionable=True)
            temp_mention = True

        if role not in cfg['msgs']:
            # No custom message
            await ctx.send(f"Pinging all members of @{role}!")
        else:
            await ctx.send(cfg['msgs'][role])

        # Reset temp toggle
        if temp_mention:
            rol.edit(mentionable=False)

    @commands.command(aliases=['scm'])
    @commands.has_permissions(manage_roles=True)
    async def setcallmsg(self, ctx, role: str, msg: str):
        """Sets the call message for a callable role"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg or role not in cfg['crs']:
            await ctx.send(f"The role '{role}' is not in the list of callable roles.")
            return

        cfg['msgs'][role] = msg
        self._save_config(ctx.guild.id, cfg)
        await ctx.send(f"Call message for '{role}' has been set.")

    @commands.command(aliases=['rcm'])
    @commands.has_permissions(manage_roles=True)
    async def removecallmsg(self, ctx, role: str):
        """Removes the call message for a callable role"""
        rol = discord.utils.get(ctx.guild.roles, name=role)
        if not rol:
            await ctx.send(f"There is no role '{role}' on this server.")
            return

        cfg = self._load_config(ctx.guild.id)
        if 'crs' not in cfg or role not in cfg['crs']:
            await ctx.send(f"The role '{role}' is not in the list of callable roles.")
            return

        if role not in cfg['msgs']:
            await ctx.send(f"The role '{role}' has no custom call message.")
            return

        del cfg['msgs'][role]
        self._save_config(ctx.guild.id, cfg)
        await ctx.send(f"Call message for '{role}' has been removed.")


def setup(bot):
    bot.add_cog(RoleCall(bot))