import asyncio
import discord
from discord.ext import commands
from discord.ext.commands.core import command
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

from .pomodoroTimer import PomodoroTimer

async def createSession(ctx : SlashContext, pt : int, bt : int):
    if not PomodoroTimer.get_session(ctx.author.id):
        session = PomodoroTimer(ctx, pt, bt)
        await session.start()
        del PomodoroTimer.sessions[ctx.author.id]
    else:
        await ctx.send(f"{ctx.author.mention} duplicate sessions aren't allowed")


class Pomodoro(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='startpomo')
    # @cog_ext.cog_slash(name="start", description="Starts a pomodoro timer", guild_ids = [839022624012894208])
    async def _startpomo(self, ctx: SlashContext, prod_timer : int = 25, break_timer : int = 5):
        self.bot.loop.create_task(createSession(ctx, prod_timer, break_timer))

    @commands.command(name='stoppomo')
    # @cog_ext.cog_slash(name="stop", description="Stops a pomodoro timer", guild_ids = [839022624012894208])
    async def _stoppomo(self, ctx: SlashContext):
        if PomodoroTimer.get_session(ctx.author.id):
            await PomodoroTimer.get_session(ctx.author.id).stop()
            await ctx.send(f"{ctx.author.mention} your session has stopped!")
        else:
            await ctx.send(f"{ctx.author.mention} There is no active session to actually stop.")


def setup(bot):
    bot.add_cog(Pomodoro(bot))