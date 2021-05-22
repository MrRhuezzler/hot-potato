import os
import re
import typing as t
from datetime import datetime

import discord
from discord.ext import commands
from discord.utils import _URL_REGEX

from discord_slash import cog_ext, SlashContext

import wavelink
from wavelink.node import Node
from wavelink import WavelinkMixin, Player
from wavelink.player import Track, TrackPlaylist


class duration:
    def __init__(self, secs) -> None:
        self.secs = secs

    def __add__(self, other : "duration"):
        return duration(self.secs + other.secs)

    @property
    def hr(self):
        return int(self.secs // 3600)
    
    @property
    def mi(self):
        return int((self.secs % 3600) // 60)

    @property
    def se(self):
        return int((self.secs % 3600) % 60)

    def __str__(self) -> str:
        if self.hr:
            return f"{str(self.hr).zfill(2)}:{str(self.mi).zfill(2)}:{str(self.se).zfill(2)}"
        else:
            return f"{str(self.mi).zfill(2)}:{str(self.se).zfill(2)}"

class Queue:
    def __init__(self) -> None:
        self._q = []
        self._pos = 0
        self._repeat = False
        self._loop = False
    
    def add(self, *tracks):
        self._q.extend(tracks)


    def empty(self):
        self._q.clear()

    def __len__(self):
        return len(self._q)

    def toggle_repeat(self):
        self._repeat = not(self._repeat)
        return self._repeat

    def toggle_loop(self):
        self._loop = not(self._loop)
        return self._loop

    @property
    def q(self):
        return self._q


    @property
    def repeat(self):
        return self._repeat

    @property
    def loop(self):
        return self._loop

    @property
    def total_duration(self):
        dur = duration(0)
        for track in self._q:
            dur += duration(track.duration // 1e3)

        return dur

    @property
    def current(self):
        if self._pos < len(self):
            return self._q[self._pos]

    @property
    def history(self):
        return self._q[:self._pos]

    @property
    def upcoming(self):
        return self._q[self._pos:]

    @property
    def first_track(self):
        return self._q[self._pos]

    @property
    def next_track(self):
        if self._repeat:
            return self._q[self._pos]
        
        self._pos += 1
        if self._loop:
            if self._pos == len(self._q):
                self._pos = 0
        
        if self._pos < len(self._q):
            return self._q[self._pos]

        return None

class MusicPlayer(Player):
    def __init__(self, bot: t.Union[commands.Bot, commands.AutoShardedBot], guild_id: int, node, **kwargs):
        super().__init__(bot, guild_id, node, **kwargs)
        self.queue = Queue()


    async def join(self, ctx : SlashContext, channel : t.Optional[discord.VoiceChannel]):
        if channel:
            self.voice_channel = channel
            await self.connect(self.voice_channel.id)
            await ctx.send(f"Connected to {self.voice_channel.name}")
        else:
            user = ctx.author
            if user.voice:
                self.voice_channel = user.voice.channel
                await self.connect(self.voice_channel.id)
                await ctx.send(f"Connected to {self.voice_channel.name}")
            else:
                await ctx.send(f"{user.mention} please connect to a voice channel")

    async def leave(self, ctx : SlashContext):
        await ctx.send("Bye !")
        await self.destroy()


    async def add_tracks(self, ctx : SlashContext, tracks : t.Union[TrackPlaylist, Track]):
        if tracks:
            if isinstance(tracks, TrackPlaylist):
                self.queue.add(*tracks.tracks)
                await ctx.send(f"Added {len(tracks.tracks)}")
            else:
                self.queue.add(tracks[0])
                await ctx.send(f"Added {tracks[0].title}")

            if not self.is_playing:
                await self.start_playback()

        else:
            await ctx.send("Couldn't find any tracks. Try with a different search query")

    async def start_playback(self):
        await self.play(self.queue.first_track)
    
    async def next_track(self):
        if (x := self.queue.next_track):
            await self.play(x)


    @staticmethod
    def shorten(string, length):
        if len(string) > length:
            return string[:length - 3] + '...'
        else:
            return string

    async def get_queue(self, ctx : SlashContext, size : t.Optional[int] = 10):
        em = discord.Embed(
            color=ctx.author.color,
            timestamp=datetime.utcnow()
        )

        q_str = "```"
        if len(self.queue) > 0:
            total_q = 0
            for track in self.queue.history[::-1][:size // 2][::-1]:
                q_str += f"    {MusicPlayer.shorten(track.title, 25) : <25}     {duration(track.duration // 1e3)}\n"
                total_q += 1

            q_str += f"--> {MusicPlayer.shorten(self.queue.current.title, 25)  : <25} <-- {duration(self.queue.current.duration // 1e3)}\n"
            total_q += 1

            if total_q < size:

                for track in self.queue.upcoming[1: size - total_q + 1]:
                    q_str += f"    {MusicPlayer.shorten(track.title, 25) : <25}     {duration(track.duration // 1e3)}\n"

        else:
            q_str += "Queue is Empty\n"

        q_str += "```"
        em.add_field(
            name=f"Queue for {ctx.guild}",
            value=q_str,
            inline=False
        )

        em.add_field(name="Total Tracks", value=f"{len(self.queue)}", inline=True)
        em.add_field(name="Total Duration", value=f"{self.queue.total_duration}", inline=True)
        em.add_field(name="Repeat", value=f"{self.queue.repeat}", inline=True)
        em.add_field(name="Loop", value=f"{self.queue.loop}", inline=True)
        em.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar_url)

        await ctx.send(embed=em)


class Music(commands.Cog, WavelinkMixin):
    def __init__(self, bot : t.Union[commands.Bot, commands.AutoShardedBot]) -> None:
        self.bot = bot
        self.wavelink = wavelink.Client(bot=bot)        
        self.bot.loop.create_task(self.start_nodes())

    async def start_nodes(self):
        nodes = [
            {
                "identifier" : "MAIN",
                "host" : os.environ.get("LAVALINK_HOST", "127.0.0.1"),
                "port" : int(os.environ.get("LAVALINK_PORT", 2333)),
                "rest_uri" : os.environ.get("LAVALINK_URI", "http://127.0.0.1:2333"),
                "password" : os.environ.get("LAVALINK_PASS", "youshallnotpass"),
                "region" : os.environ.get("LAVALINK_HOST", "us_central")
            }
        ]

        for node in nodes:
            await self.wavelink.initiate_node(**node)


    @wavelink.WavelinkMixin.listener()
    async def on_node_ready(self, node: Node):
        print(f"Wavelink Node {{{node}}} has been Initialized")


    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def _next_track(self, node : Node, payload):
        await payload.player.next_track()


    def get_player(self, guild : discord.Guild):
        return self.wavelink.get_player(guild.id, cls=MusicPlayer)

    @commands.command(name="join")
    async def _join(self, ctx : SlashContext, *, voiceChannel : t.Optional[discord.VoiceChannel]):
        player = self.get_player(ctx.guild)
        await player.join(ctx, voiceChannel)

    @commands.command(name="leave")
    async def _leave(self, ctx : SlashContext):
        await self.get_player(ctx.guild).leave(ctx)

    @commands.command(name="play")
    async def _play(self, ctx : SlashContext, *, query : t.Optional[str]):
        player = self.get_player(ctx.guild)
        if not player.is_connected:
            await player.join(ctx, None)

        if player.is_connected:
            if query:
                if not re.match(_URL_REGEX, query):
                    query = f"ytsearch:{query}"
                
                tracks = await self.wavelink.get_tracks(query)
                await player.add_tracks(ctx, tracks)

            else:
                if player.is_paused:
                    await player.set_pause(False)

    @commands.command(name="q")
    async def _q(self, ctx : SlashContext, size : t.Optional[int] = 10):
        await self.get_player(ctx.guild).get_queue(ctx, size)

    @commands.command(name="pause")
    async def _pause(self, ctx : SlashContext, *, query : t.Optional[str]):
        await self.get_player(ctx.guild).set_pause(True)

    @commands.command(name="stop")
    async def _stop(self, ctx : SlashContext):
        self.get_player(ctx.guild).queue.empty()
        await self.get_player(ctx.guild).stop()

    @commands.command(name="repeat")
    async def _repeat(self, ctx : SlashContext):
        if self.get_player(ctx.guild).queue.toggle_repeat():
            await ctx.send("Repeating Enabled")
        else:
            await ctx.send("Repeating Disabled")

    @commands.command(name="loop")
    async def _loop(self, ctx : SlashContext):
        if self.get_player(ctx.guild).queue.toggle_loop():
            await ctx.send("Loop Enabled")
        else:
            await ctx.send("Loop Disabled")


def setup(bot):
    bot.add_cog(Music(bot))