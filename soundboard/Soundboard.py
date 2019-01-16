import aiohttp
import asyncio
import datetime
import discord

import lavalink

import time
import os
import redbot.core
from redbot.core import Config, commands, checks
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import box

from .manager import shutdown_lavalink_server

_ = Translator("Audio", __file__)

__version__ = 1.0

@cog_i18n(_)
class Soundboard(commands.Cog):
    """Play audio through voice channels."""

    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        self.config = Config.get_conf(self, 1436521234, force_registration=True)

        default_global = {
            "host": "localhost",
            "rest_port": "2333",
            "ws_port": "2332",
            "password": "youshallnotpass",
            "status": False,
            "current_version": redbot.core.VersionInfo.from_str("3.0.0a0").to_json()
        }

        default_guild = {
            "emptydc_enabled": False,
            "emptydc_timer": 0,
            "volume": 100
        }

        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)
        self.session = aiohttp.ClientSession()
        self._disconnect_task = None
        self._cleaned_up = False

    async def initialize(self):
        host = await self.config.host()
        password = await self.config.password()
        rest_port = await self.config.rest_port()
        ws_port = await self.config.ws_port()

        await lavalink.initialize(
            bot=self.bot,
            host=host,
            password=password,
            rest_port=rest_port,
            ws_port=ws_port,
            timeout=60,
        )

        self._disconnect_task = self.bot.loop.create_task(self.disconnect_timer())

    @commands.group()
    @commands.guild_only()
    async def soundboardset(self, ctx):
        """Music configuration options."""
        pass

    @soundboardset.command()
    @checks.mod_or_permissions(administrator=True)
    async def sbemptydisconnect(self, ctx, seconds: int):
        """Auto-disconnection after x seconds while stopped. 0 to disable."""
        if seconds < 0:
            return await self._embed_msg(ctx, _("Can't be less than zero."))
        if 10 > seconds > 0:
            seconds = 10
        if seconds == 0:
            enabled = False
            await self._embed_msg(ctx, _("Empty disconnect disabled."))
        else:
            enabled = True
            await self._embed_msg(
                ctx,
                _("Empty disconnect timer set to {num_seconds}.").format(
                    num_seconds=self._dynamic_time(seconds)
                ),
            )

        await self.config.guild(ctx.guild).emptydc_timer.set(seconds)
        await self.config.guild(ctx.guild).emptydc_enabled.set(enabled)

    @soundboardset.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx, role_name: discord.Role):
        """Set the role to use for DJ mode."""
        await self.config.guild(ctx.guild).dj_role.set(role_name.id)
        dj_role_obj = ctx.guild.get_role(await self.config.guild(ctx.guild).dj_role())
        await self._embed_msg(ctx, _("DJ role set to: {role.name}.").format(role=dj_role_obj))

    @soundboardset.command()
    async def settings(self, ctx):
        """Show the current settings."""
        data = await self.config.guild(ctx.guild).all()
        global_data = await self.config.all()
        emptydc_enabled = data["emptydc_enabled"]
        emptydc_timer = data["emptydc_timer"]
        jarbuild = redbot.core.__version__

        msg = "----" + _("Server Settings") + "----\n"
        if emptydc_enabled:
            msg += _("Disconnect timer: [{num_seconds}]\n").format(
                num_seconds=self._dynamic_time(emptydc_timer)
            )
        msg += _(
            "---Lavalink Settings---\n"
            "Cog version:      [{version}]\n"
            "Jar build:        [{jarbuild}]\n"
            "External server:  [{use_external_lavalink}]"
        ).format(version=__version__, jarbuild=jarbuild, **global_data)

        embed = discord.Embed(colour=await ctx.embed_colour(), description=box(msg, lang="ini"))
        return await ctx.send(embed=embed)

    @commands.command(aliases=["sbdc"])
    @commands.guild_only()
    async def sbdisconnect(self, ctx):
        """Disconnect from the voice channel."""
        dj_enabled = await self.config.guild(ctx.guild).dj_enabled()
        if self._player_check(ctx):

            if  not await self._is_alone(
                ctx, ctx.author
            ):
                return await self._embed_msg(ctx, _("There are other people listening to music."))
            else:
                await lavalink.get_player(ctx.guild.id).stop()
                return await lavalink.get_player(ctx.guild.id).disconnect()

    @commands.command(aliases=["sc", "sb"])
    @commands.guild_only()
    async def soundclip(self, ctx, *, query):
        """play a soundclip"""
        if not self._player_check(ctx):
            try:
                if not ctx.author.voice.channel.permissions_for(ctx.me).connect or self._userlimit(
                    ctx.author.voice.channel
                ):
                    return await self._embed_msg(
                        ctx, _("I don't have permission to connect to your channel.")
                    )
                await lavalink.connect(ctx.author.voice.channel)
                player = lavalink.get_player(ctx.guild.id)
                player.store("connect", datetime.datetime.utcnow())
            except AttributeError:
                return await self._embed_msg(ctx, _("Connect to a voice channel first."))
        player = lavalink.get_player(ctx.guild.id)
        player.store("channel", ctx.channel.id)
        player.store("guild", ctx.guild.id)
        if not ctx.author.voice or ctx.author.voice.channel != player.channel:
            return await self._embed_msg(
                ctx, _("You must be in the voice channel to play a soundclip.")
            )
        if not query:
            return await self._embed_msg(ctx, _("Please name a soundclip! E.g. !sb zebra"))

        uri = f"/opt/localtracks/sc/{query}.mp3"

        allowed_files = (".mp3", ".flac", ".ogg")

        tracks = await player.get_tracks(uri)
        if not tracks:
            return await self._embed_msg(ctx, _(f"{query} does not exist :("))


        single_track = tracks[0]
        player.add(ctx.author, single_track)

        description = f"{query}"

        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Soundclip"), description=description
        )
        embed.set_footer(
            text=_(f"Called by: {ctx.author}")
        )
        if not player.current:
            await player.play()

        await ctx.send(embed=embed)

    @commands.command(aliases=["sclist"])
    @commands.guild_only()
    async def soundclip_list(self, ctx):
        """play a soundclip"""

        path = "/opt/localtracks/sc/"
        files = [os.path.join(dp, f) for dp, dn, fn in os.walk(path) for f in fn]
        short_files = [full_path.replace(path, '') for full_path in files]
        user_dict = {}
        for file in short_files:
            user = file.split('/')[0]
            mp3 = file.split('/')[1]
            if not user_dict.get(user):
                user_dict.update({user: []})
            user_dict[user].append(mp3.replace('.mp3', ''))

        description = '\n'.join(files)
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Soundclip List:"), description=description
        )
        embed.set_footer(
            text=_(f"Called by: {ctx.author}")
        )
        for user, file_names in user_dict.items():
            file_names.sort()
            value = '\n'.join(file_names)
            embed.add_field(name=user, value=value)

        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def sbvolume(self, ctx, vol: int = None):
        """Set the volume, 1% - 150%."""
        if not vol:
            vol = await self.config.guild(ctx.guild).volume()
            embed = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Current Volume:"),
                description=str(vol) + "%",
            )
            if not self._player_check(ctx):
                embed.set_footer(text=_("Nothing playing."))
            return await ctx.send(embed=embed)
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            if not ctx.author.voice or ctx.author.voice.channel != player.channel:
                return await self._embed_msg(
                    ctx, _("You must be in the voice channel to change the volume.")
                )
        if vol < 0:
            vol = 0
        if vol > 150:
            vol = 150
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check(ctx):
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        else:
            await self.config.guild(ctx.guild).volume.set(vol)
            if self._player_check(ctx):
                await lavalink.get_player(ctx.guild.id).set_volume(vol)
        embed = discord.Embed(
            colour=await ctx.embed_colour(), title=_("Volume:"), description=str(vol) + "%"
        )
        if not self._player_check(ctx):
            embed.set_footer(text=_("Nothing playing."))
        await ctx.send(embed=embed)

    async def _data_check(self, ctx):
        player = lavalink.get_player(ctx.guild.id)
        shuffle = await self.config.guild(ctx.guild).shuffle()
        repeat = await self.config.guild(ctx.guild).repeat()
        volume = await self.config.guild(ctx.guild).volume()
        if player.repeat != repeat:
            player.repeat = repeat
        if player.shuffle != shuffle:
            player.shuffle = shuffle
        if player.volume != volume:
            await player.set_volume(volume)

    async def disconnect_timer(self):
        stop_times = {}

        while True:
            for p in lavalink.players:
                server = p.channel.guild

                if server.id not in stop_times:
                    stop_times[server.id] = None

                if [self.bot.user] == p.channel.members:
                    if stop_times[server.id] is None:
                        stop_times[server.id] = int(time.time())

            for sid in stop_times:
                server_obj = self.bot.get_guild(sid)
                emptydc_enabled = await self.config.guild(server_obj).emptydc_enabled()
                if emptydc_enabled:
                    if stop_times[sid] is not None and [self.bot.user] == p.channel.members:
                        emptydc_timer = await self.config.guild(server_obj).emptydc_timer()
                        if stop_times[sid] and (
                            int(time.time()) - stop_times[sid] > emptydc_timer
                        ):
                            stop_times[sid] = None
                            await lavalink.get_player(sid).disconnect()

            await asyncio.sleep(5)

    @staticmethod
    async def _embed_msg(ctx, title):
        embed = discord.Embed(colour=await ctx.embed_colour(), title=title)
        await ctx.send(embed=embed)

    async def _get_embed_colour(self, channel: discord.abc.GuildChannel):
        # Unfortunately we need this for when context is unavailable.
        if await self.bot.db.guild(channel.guild).use_bot_color():
            return channel.guild.me.color
        else:
            return self.bot.color

    async def _get_playing(self, ctx):
        if self._player_check(ctx):
            player = lavalink.get_player(ctx.guild.id)
            return len([player for p in lavalink.players if p.is_playing])
        else:
            return 0

    @staticmethod
    def _player_check(ctx):
        try:
            lavalink.get_player(ctx.guild.id)
            return True
        except KeyError:
            return False

    @staticmethod
    def _userlimit(channel):
        if channel.user_limit == 0:
            return False
        if channel.user_limit < len(channel.members) + 1:
            return True
        else:
            return False

    async def on_voice_state_update(self, member, before, after):
        if after.channel != before.channel:
            try:
                self.skip_votes[before.channel.guild].remove(member.id)
            except (ValueError, KeyError, AttributeError):
                pass

    def __unload(self):
        if not self._cleaned_up:
            self.session.detach()
            if self._disconnect_task:
                self._disconnect_task.cancel()
            self.bot.loop.create_task(lavalink.close())
            shutdown_lavalink_server()
            self._cleaned_up = True

    __del__ = __unload

