import discord
from discord.ext import commands
from discord.ext.commands.core import command
from discord_slash import cog_ext, SlashContext


class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping')
    # @cog_ext.cog_slash(name="ping", description="Gets the Response time of Test-Bot", guild_ids = [839022624012894208])
    async def _ping(self, ctx: SlashContext):
        em = discord.Embed(
            description=f":heartbeat:  {int(self.bot.latency * 1000)}ms",
            color=0x15ead5
        )
        await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(Utils(bot))