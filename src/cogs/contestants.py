import io
import os
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
        view = self.ContestantView(contestants=contestants)
        await ctx.send(embed=embed, file=f, view=view)
        os.remove(f.filename)
        return
    
    @staticmethod
    async def create_image(contestants: List[Contestant]):
        # preemptively calculates the height of the image so we can set it when creating the background.
        height = 25
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
            
        #Create the background and write the game name
        background = Image.new('RGB', (150, height), color='black')
        draw = ImageDraw.Draw(background)
        titlefont = ImageFont.truetype("OpenSans-VariableFont.ttf",8)
        _, _, w, h = draw.textbbox((0,0), "Game Name") #TODO select the game in the base command and use it here
        draw.text(((150-w)/2,(25-h)/2), "Game Name", fill="white")

        #Create the embed
        embed = discord.Embed(
            title="Test Image",
            description="This is a generated image",
            color=discord.Color.green()
        )
        
        #Start drawing the contestants
        teamCount = 0
        curTeam = 0
        #curHeight keeps track of how far down we are
        curHeight = 25
        font = ImageFont.truetype("OpenSans-VariableFont.ttf",8)
        for contestant in contestants:
            try:
                #If we have reached a new team
                if contestant.team != curTeam:
                    #Update to new team and index within that team
                    curTeam = contestant.team
                    teamCount = 1
                    #Increase the height, unless we are on the first team in which case we don't need to
                    if teamCount % 2 == 1 and curTeam != 1:
                        curHeight+= 65

                    #draw the team name and update the height again
                    _, _, textw, _ = draw.textbbox((0,0), f"Team {curTeam}",font)

                    draw.text(((150-textw)/2,curHeight),f"Team {curTeam}",fill="white", font=font)
                    curHeight+=15
                else:
                    #Update the index within the team, update the height if moving to new row
                    teamCount += 1
                    if teamCount % 2 == 1:
                        curHeight+= 65

                #Get the image from the URL stored in the DB, then resize it to 50x50
                response = requests.get(contestant.picture, stream=True)
                response.raise_for_status()
                newImg = Image.open(io.BytesIO(response.content)).resize((50,50))

                
                _, _, textw, _ = draw.textbbox((0,0), contestant.name, font)
                # ((75-textw)/2)+70*((teamCount-1)%2) : Center the text horizontally over one half of the image, 
                # move it to the right if on the second column
                # curHeight+50 : draw the text just below the image
                draw.text((((75-textw)/2)+70*((teamCount-1)%2),curHeight+50), contestant.name,fill="white",font=font)

                #Draw the image 15px away from the left, or 85 if on second column
                background.paste(newImg, (15+70*((teamCount+1)%2),curHeight))
            except requests.exceptions.RequestException:
                print(f'Image for {contestant.name} unloadable')

        
        background.save(f'game-{contestants[0].gameid}.png')


        f = discord.File(f"game-{contestants[0].gameid}.png", filename=f"game-{contestants[0].gameid}.png")

        embed.set_image(url=f'attachment://game-{contestants[0].gameid}.png')
        return embed, f
    
    class ContestantView(discord.ui.View):
        
        def __init__(self, *, contestants:List[Contestant], timeout = 180):
            self.contestants = contestants
            self.options = [discord.SelectOption(label=c.name, value = c.name) for c in contestants]
            super().__init__(timeout=timeout)
            self.selectObj = self.select()
            self.add_item(self.selectObj)

        async def select_callback(self, interaction: discord.Interaction):
            await interaction.response.send_message(f'Selected {self.selectObj.values[0]}', ephemeral=True,delete_after=3)
            

        def select(self):
            select = discord.ui.Select(placeholder="Select a contestant",
                           options=self.options)
            select.callback = self.select_callback
            return select


        @discord.ui.button(label="Edit",style=discord.ButtonStyle.success)
        async def test_callback(self,interaction: discord.Interaction,button: discord.ui.Button):
            #modal = self.GameModal(self.game)
            if len(self.selectObj.values) > 0:
                modal = self.ContestantModal(next((n for n in self.contestants if n.name == self.selectObj.values[0])))
                await interaction.response.send_modal(modal)
            else:
                await interaction.response.send_message('No Contestant Selected', ephemeral=True)

        class ContestantModal(discord.ui.Modal):
            def __init__(self,contestant :Contestant):
                self.contestant = contestant
                self.name=discord.ui.TextInput(label="Name",style=discord.TextStyle.short,placeholder="Enter New Name...",default=contestant.name, max_length=50)
                self.team=discord.ui.TextInput(label="Team",style=discord.TextStyle.short,default=contestant.team)
                self.imageurl=discord.ui.TextInput(label="Image URL",style=discord.TextStyle.short,placeholder="Enter the Image URL...",default=contestant.picture)
                self.userid=discord.ui.TextInput(label="User ID",style=discord.TextStyle.short,placeholder="If This Contestant is a User, Enter Their ID...", required=False,default=contestant.userref)
                super().__init__(title=f"Edit Contestant",custom_id=str(contestant.name),)
                self.add_item(self.name)
                self.add_item(self.team)
                self.add_item(self.imageurl)
                self.add_item(self.userid)

            async def on_submit(self, interaction: discord.Interaction):
                
                bot : commands.Bot = interaction.client
                session = bot.session
                try:
                    id = int(self.userid.value)
                    self.contestant.name = self.name.value
                    self.contestant.team = self.team.value
                    self.contestant.userref = id
                    self.contestant.picture = self.imageurl.value

                    await session.merge(self.contestant)
                    await session.commit()

                    await session.close()
                    await interaction.response.send_message("Contestant Editted")

                except ValueError:
                    await interaction.followup.send("User ID must be an integer.", ephemeral=True)
                except IntegrityError:
                    await session.rollback()
                    await interaction.response.send_message("A user with that name already exists in this game.")
                    
                    
                    
                return await super().on_submit(interaction)

        
    
    