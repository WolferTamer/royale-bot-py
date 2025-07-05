from typing import Literal
from discord.ext import commands
import discord
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from schemas import Game, User


class GamesCog(commands.Cog):
    help_index = [
        {"name":"Create Game",
         "command":"/create_game <name> [teamtype] [teams] [autoprogress]",
         "parameters": [
            {"name":"Name",
             "type":"String",
             "usage":"The you want your game to have."},
             {"name":"Team Type",
             "type":"district | team | solo",
             "usage":"What type of team you want to have."},
             {"name":"Teams",
             "type":"Integer",
             "usage":"The amount of teams in your game."},
             {"name":"Auto Progress",
             "type":"Yes/No",
             "usage":"Whether the game should progress automatically when started."}
         ],
         "description":"Create a game"},
         {"name":"games",
         "command":"/games",
         "parameters": [
         ],
         "description":"View a list of your games and their IDs"},
         {"name":"Game",
         "command":"/game <id>",
         "parameters": [
            {"name":"Game ID",
             "type":"Integer",
             "usage":"The id of the game you want to view"}
         ],
         "description":"View information about one of your games"}
    ]

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

        await session.close()

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
        await session.close()
        result = [r for r, in games]
        
        if len(result) > 0:
            embed = self.gamesEmbed(result, ctx.author)
            await ctx.send(embed=embed)
            return
        else:
            await ctx.send("No games found")

    @commands.hybrid_command()
    async def game(self, ctx: commands.Context, id:int):
        statement = select(Game).where(Game.userid==ctx.author.id,Game.gameid==id)
        session : AsyncSession = self.bot.session
        response = (await session.execute(statement)).first()
        await session.close()
        if not response:
            await ctx.reply("No game found with that ID", ephemeral=True)
            return
        else:
            game : Game = response[0]
            embed = self.gameEmbed(game)
            view = self.GameView(game=game)
            await ctx.send(embed=embed, view=view)

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
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Invalid argument provided: {error}")
        else:
            # Handle other types of errors or re-raise them
            raise error
    
    @staticmethod
    def gameEmbed(game: Game):
        embed = discord.Embed(
            title=game.name,
            description=f"**ID** {game.gameid}",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Team Types", value=f"{game.teamtype}: {GamesCog.teamtypedescriptions[game.teamtype]}")
        embed.add_field(name="Team Count", value=f"{game.teamcount} teams")
        embed.add_field(name="Autoprogress", value=f"{game.autoprogress}")
        return embed
    
    @staticmethod
    def gamesEmbed(games: list[Game], user):
        embed = discord.Embed(
            title=f"{user.display_name}'s Games",
            color=discord.Color.blurple()
        )
        for game in games:
            embed.add_field(name=game.name,value=game.gameid)
        
        return embed
    
    class GameView(discord.ui.View):
        
        def __init__(self, *, game:Game, timeout = 180):
            self.game = game
            super().__init__(timeout=timeout)

        @discord.ui.button(label="Edit",style=discord.ButtonStyle.success)
        async def test_callback(self,interaction: discord.Interaction,button: discord.ui.Button):
            modal = self.GameModal(self.game)
            await interaction.response.send_modal(modal)

        class GameModal(discord.ui.Modal):
            def __init__(self,game :Game):
                self.game = game
                self.name=discord.ui.TextInput(label="Name",style=discord.TextStyle.short,placeholder="Enter New Name...",default=game.name, max_length=50)
                self.teamtype=discord.ui.TextInput(label="Team Type",style=discord.TextStyle.short,default=game.teamtype)
                self.teamcount=discord.ui.TextInput(label="Team Count",style=discord.TextStyle.short,placeholder="Enter Amount of Teams",default=game.teamcount)
                self.auto=discord.ui.TextInput(label="Autoprogress",style=discord.TextStyle.short,placeholder="Enter Text Thing",default=str(game.autoprogress))
                super().__init__(title=f"Edit Game {game.gameid}",custom_id=str(game.gameid),)
                self.add_item(self.name)
                self.add_item(self.teamtype)
                self.add_item(self.teamcount)
                self.add_item(self.auto)

            async def on_submit(self, interaction: discord.Interaction):
                if self.teamtype.value not in GamesCog.teamtypedescriptions.keys():
                    await interaction.response.send_message("Team Type must be \"district\", \"team\", or \"solo\".")
                elif self.auto.value != "False" and self.auto.value != "True":
                    await interaction.response.send_message("Auto Progress must be \"True\" or \"False\".")
                else:
                    try:
                        count = int(self.teamcount.value)
                        self.game.name = self.name.value
                        self.game.teamtype = self.teamtype.value
                        self.game.teamcount = count
                        self.game.autoprogress = self.auto.value == "True"
                        bot : commands.Bot = interaction.client
                        session = bot.session
                        await session.merge(self.game)
                        await session.commit()

                        await session.close()
                        await interaction.response.edit_message(embed=GamesCog.gameEmbed(game=self.game))

                    except ValueError:
                        await interaction.followup.send("Team Count must be an integer.")
                        
                    
                    
                    
                return await super().on_submit(interaction)
            

    
