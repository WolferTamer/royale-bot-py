import os
from events.event import Event
import discord
from discord.ext import commands
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import Contestant


class PlayCog(commands.Cog):

    def __init__(self,bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command()
    async def test_event(self, ctx: commands.Context, gameid: int):

        session : AsyncSession = self.bot.session
        defer = ctx.defer()
        res = (await session.execute(select(Contestant).where(Contestant.gameid==gameid).order_by(Contestant.team))).all()
        contestants = [r for r, in res]
        if(len(contestants) < 1):
            await defer
            await ctx.send("No contestants in this game", ephemeral=True)
            return
        
        await session.close()
        
        event = self.bot.get_any_event()

        f = event.get_image([[contestants[0],contestants[1]],[contestants[2]]])

        await defer
        await ctx.send(file=f)
        os.remove(f.filename)
        return
    
    @commands.hybrid_command()
    async def test_category(self, ctx: commands.Context, gameid: int, category: str):
        session : AsyncSession = self.bot.session
        defer = ctx.defer()
        res = (await session.execute(select(Contestant).where(Contestant.gameid==gameid).order_by(Contestant.team))).all()
        contestants = [r for r, in res]
        if(len(contestants) < 1):
            await defer
            await ctx.send("No contestants in this game", ephemeral=True)
            return
        
        await session.close()

        event = self.bot.get_event_of_type(category)

        f = event.get_image([[contestants[0],contestants[1]],[contestants[2]]])

        await defer
        await ctx.send(file=f)
        os.remove(f.filename)
        return

    @commands.hybrid_command()
    async def test_filter(self, ctx: commands.Context, gameid: int, max_groups: int, max_deaths: int):
        session : AsyncSession = self.bot.session
        defer = ctx.defer()
        res = (await session.execute(select(Contestant).where(Contestant.gameid==gameid).order_by(Contestant.team))).all()
        contestants = [r for r, in res]
        if(len(contestants) < 1):
            await defer
            await ctx.send("No contestants in this game", ephemeral=True)
            return
        
        await session.close()

        event = self.bot.get_event_filter(max_groups=[99 for x in range(0,max_groups)], max_deaths=max_deaths)

        f = event.get_image([[contestants[0],contestants[1]],[contestants[2]]])

        await defer
        await ctx.send(file=f)
        os.remove(f.filename)
        return
    
    #/play logic:
    #Start by getting a list of all the players. Respond with a message showing a desciption of the game &
    #confirming it is the correct game.
    #If confirmed, send out the initial events. It will either be sent out one event at a time, or have each day's
    #Events in one message. 
