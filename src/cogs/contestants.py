from discord.ext import commands

from main import RoyaleBot


class ContestantCog(commands.Cog):
    def __init__(self,bot : RoyaleBot):
        self.bot = bot

    @commands.hybrid_command()
    async def add_contestant(self,ctx):
        return
