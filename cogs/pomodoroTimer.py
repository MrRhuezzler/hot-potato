import asyncio
import discord
from discord_slash import SlashContext


class PomodoroTimer:

    sessions = dict()

    def __init__(self, ctx : SlashContext, pt : int, bt : int) -> None:
        self.ctx = ctx
        self.user = ctx.author
        self.channel = ctx.channel
        self.prod_timer = pt * 60
        self.break_timer = bt * 60
        self.total_pomos = 0
        self.has_finished = False
        self.titles = ["Work Time", "Break Time", "Session done"]
        self.colors = [0x00df00, 0x00e6e6, 0xe10000]
        PomodoroTimer.sessions[self.user.id] = self

    def get_embed(self, t_index, c_index, message):
        embed = discord.Embed(title="Pomodoro Session", description="Current Status of Pomodoro", color=self.colors[c_index])
        embed.add_field(name="User", value=f"{self.user.mention}")
        embed.add_field(name=f"{self.titles[t_index]}", value=f"{message}")
        return embed

    async def send_embed(self):
        self.embed_message = await self.ctx.send(embed=self.get_embed(0, 0, f"<{self.prod_timer // 60} minutes left."))
        await self.embed_message.pin()

    async def start(self):

        await self.send_embed()

        prod_timer = self.prod_timer
        break_timer = self.break_timer

        while not self.has_finished:

            if not self.has_finished:
                await self.ctx.send(f"{self.user.mention} Get productive...")

            while prod_timer:
                prod_timer -= 30

                if self.has_finished:
                    break

                break_timer = self.break_timer

                if prod_timer % 60:
                    await self.embed_message.edit(embed=self.get_embed(0, 0, f"<{prod_timer // 60} minute(s) left."))
                await asyncio.sleep(30)

            if not self.has_finished:
                await self.ctx.send(f"{self.user.mention} Take some rest...")

            while break_timer:
                break_timer -= 30

                if self.has_finished:
                    break

                prod_timer = self.prod_timer

                if break_timer % 60:
                    await self.embed_message.edit(embed=self.get_embed(1, 1, f"<{break_timer // 60} minute(s) left."))
                await asyncio.sleep(30)

            self.total_pomos += 1

    async def stop(self):
        self.has_finished = True
        await self.embed_message.edit(embed=self.get_embed(2, 2, f"Completed {self.total_pomos} pomodoros."))
        await self.ctx.send(f"{self.user.mention} You have completed {self.total_pomos} pomodoros.")
        await self.embed_message.unpin()
        await asyncio.sleep(1)

    @staticmethod
    def get_session(author_id):
        return PomodoroTimer.sessions.get(author_id, None)

