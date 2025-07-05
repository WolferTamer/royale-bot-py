from typing import Literal
from discord.ext import commands
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import Game, User


class GamesCog(commands.Cog):
    teamtypedescriptions = {
        "district": "Each player starts on a team that they may be more inclined to cooperate with, but there will only be one winner.",
        "team": "Each player starts on a team, and everyone on that team is able to win together. They will not harm team members.",
        "solo": "There are no teams, and each player is completely independent."
        }

    def __init__(self,bot):
        self.bot = bot

    @commands.hybrid_command(description="Create a game")
    async def create_game(self,ctx, 
                          name: str = commands.parameter(description="The name of your game"),
                          teamtype: Literal["district","team","solo"] = commands.parameter(description="The type of teams you have",default="district"),
                          teams: int = commands.parameter(description="The amount of teams", default=12),
                          autoprogress: bool = commands.parameter(description="Whether the turns should keep going automatically", default=False)):
        session = self.bot.session
        userInstance = (await session.execute(select(User).where(User.userid == ctx.author.id))).first()
        if not userInstance:
            newuser = User(userid=ctx.author.id)
            session.add(newuser)
            await session.commit()
            userInstance = newuser
        else:
            userInstance = userInstance[0]
        game = Game(name=name, teamtype=teamtype, teamcount=teams,autoprogress=autoprogress, userid=userInstance.userid)
        session.add(game)
        await session.commit()

        await ctx.send(embed=self.gameEmbed(game))

        return
    
    @commands.hybrid_command()
    async def games(self, ctx :commands.Context):
        userid = ctx.author.id
        session : AsyncSession = self.bot.session
        userInstance = (await session.execute(select(User).where(User.userid == userid))).first()
        if not userInstance:
            newuser = User(userid=userid)
            session.add(newuser)
            await session.commit()
            userInstance = newuser
        else:
            userInstance = userInstance[0]
        games = await session.execute(select(Game).where(Game.userid == userid))

        result = [r for r, in games]
        
        if len(result) > 0:
            embed = self.gamesEmbed(result, ctx.author)
            await ctx.send(embed=embed)
            return
        else:
            await ctx.send("No games found")

    def gameEmbed(self, gameid: int, name: str, teamtype: str, teamcount: int, autoprogress: bool):
        embed = discord.Embed(
            title=name,
            description=f"**ID** {gameid}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Team Types", value=f"{teamtype}: {self.teamtypedescriptions[teamtype]}")
        embed.add_field(name="Team Count", value=f"{teamcount} teams")
        embed.add_field(name="Autoprogress", value=f"{autoprogress}")
        return embed
    
    def gameEmbed(self, game: Game):
        embed = discord.Embed(
            title=game.name,
            description=f"**ID** {game.gameid}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Team Types", value=f"{game.teamtype}: {self.teamtypedescriptions[game.teamtype]}")
        embed.add_field(name="Team Count", value=f"{game.teamcount} teams")
        embed.add_field(name="Autoprogress", value=f"{game.autoprogress}")
        return embed
    
    def gamesEmbed(self, games: list[Game], user):
        embed = discord.Embed(
            title=f"{user.display_name}'s Games",
            color=discord.Color.blurple()
        )
        for game in games:
            embed.add_field(name=game.name,value=game.gameid)
        
        return embed

    

