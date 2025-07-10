import io
from typing import List
from PIL import Image, ImageDraw, ImageFont
import discord
from discord.ext import commands
import requests
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy import Row, Sequence, Tuple, select
from sqlalchemy.ext.asyncio import AsyncSession

from schemas import Contestant, Game

class ContestantCog(commands.Cog):
    

    def __init__(self,bot : commands.Bot):
        self.bot = bot

    # Requires gameid, either user reference or image + name, has to have team number
    # Check for game first. Game existing implies existence of User, no need to check for that.
    # If game exists, create the Contestant object

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided: {error}")
        else:
            # Handle other types of errors or re-raise them
            raise error

    @commands.hybrid_group(name="add_contestant", description="Add a contestant to a game")
    async def add_contestant(self,ctx: commands.Context):
        await ctx.send("You shouldn't be calling this i think.")
    
    @add_contestant.command(name="user")
    async def add_contestant_user(self,ctx: commands.Context, user: discord.User, gameid: int):
        session = self.bot.session
        gameInstance = (await session.execute(select(Game).where(Game.userid == ctx.author.id and Game.gameid == gameid))).first()

        if(not gameInstance):
            await ctx.send("Error, game not found", ephemeral=True)
            return
        gameInstance = gameInstance[0]
        contestant = Contestant(name=user.display_name,picture=user.display_avatar,gameid=gameid,userref=user.id)
        session.add(contestant)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await ctx.send("A user with that name already exists in this game.")
            return
        except DataError:
            await session.rollback()
            await ctx.send('Image URL is too long.')
        await ctx.send(f"Contestant with name {user.display_name} created for game {gameInstance.name}.")
        
        return
    
    @add_contestant.command(name="custom")
    async def add_contestant_custom(self,ctx: commands.Context, name: str, imageurl: str, gameid: int):
        session = self.bot.session
        gameInstance = (await session.execute(select(Game).where(Game.userid == ctx.author.id and Game.gameid == gameid))).first()

        if(not gameInstance):
            await ctx.send("Error, game not found", ephemeral=True)
            return
        gameInstance = gameInstance[0]
        contestant = Contestant(name=name,picture=imageurl,gameid=gameid)
        session.add(contestant)
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            await ctx.send("A user with that name already exists in this game.")
            return
        except DataError:
            await session.rollback()
            await ctx.send('Image URL is too long.')
        await ctx.send(f"Contestant with name {name} created for game {gameInstance.name}.")

        return
    
    # Returns an image based list of the contestants.
    # Select option to choose a contestant and button to open a modal that edits it
    # 
    @commands.hybrid_command()
    async def contestants(self,ctx: commands.Context, gameid:int):
        session : AsyncSession = self.bot.session
        defer = ctx.defer()
        res = (await session.execute(select(Contestant).where(Contestant.gameid==gameid).order_by(Contestant.team))).all()
        contestants = [r for r, in res]
        if(len(contestants) < 1):
            await defer
            await ctx.send("No contestants in this game", ephemeral=True)
            return
        embed, f = await self.create_image(contestants)
        await defer
        await ctx.send(embed=embed, file=f)
        return
    
    async def create_image(self, contestants: List[Contestant]):
        height = 25 # Caclulating the height of the image
        teamCount = 0
        curTeam = 0
        for contestant in contestants:
            if contestant.team != curTeam:
                curTeam = contestant.team
                teamCount = 1
                height+= 80 #add 15 px for title, 60 pixels for ever row of team
            else:
                teamCount += 1
                if teamCount % 2 == 1:
                    height+=65
            
        
        background = Image.new('RGB', (150, height), color='black')
        draw = ImageDraw.Draw(background)
        titlefont = ImageFont.truetype("OpenSans-VariableFont.ttf",8)
        _, _, w, h = draw.textbbox((0,0), "Game Name")
        draw.text(((150-w)/2,(25-h)/2), "Game Name", fill="white")
        embed = discord.Embed(
            title="Test Image",
            description="This is a generated image",
            color=discord.Color.green()
        )
        
        teamCount = 0
        curTeam = 0
        curHeight = 25
        font = ImageFont.truetype("OpenSans-VariableFont.ttf",8)
        for contestant in contestants:
            try:
                if contestant.team != curTeam:
                    curTeam = contestant.team
                    teamCount = 1
                    if teamCount % 2 == 1 and curTeam != 1:
                        curHeight+= 65
                    _, _, textw, _ = draw.textbbox((0,0), f"Team {curTeam}",font)

                    draw.text(((150-textw)/2,curHeight),f"Team {curTeam}",fill="white", font=font)
                    curHeight+=15
                else:
                    teamCount += 1
                    if teamCount % 2 == 1:
                        curHeight+= 65
                response = requests.get(contestant.picture, stream=True)
                response.raise_for_status()
                newImg = Image.open(io.BytesIO(response.content)).resize((50,50))
                #Every new team add 15 px for text
                #Put first column 15 x
                #Put second row 85 x
                #15 px underneath for text
                #new row
                _, _, textw, _ = draw.textbbox((0,0), contestant.name, font)
                draw.text((((75-textw)/2)+70*((teamCount-1)%2),curHeight+50), contestant.name,fill="white",font=font)
                background.paste(newImg, (15+70*((teamCount+1)%2),curHeight))
            except requests.exceptions.RequestException:
                print(f'Image for {contestant.name} unloadable')


        background.save('game.png')


        f = discord.File("game.png", filename="game.png")

        embed.set_image(url='attachment://game.png')
        return embed, f

        
    
    