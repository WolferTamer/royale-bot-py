import discord
from discord.ext import commands


class HelpCog(commands.Cog):
    def __init__(self,bot: commands.Bot):
        self.bot = bot
    
    @commands.hybrid_command()
    async def help(self,ctx: commands.Context,command: str = commands.parameter(description="The command you want help with.",default=None)):
        if command == None:
            embed = self.helpEmbed()
            await ctx.reply(embed=embed)
        else:
            embed = self.commandEmbed(command)
            if embed == None:
                await ctx.reply("No command of that name found", ephemeral=True)
            else:
                await ctx.reply(embed=embed)
        
    def helpEmbed(self):
        cogs = self.bot.cogs
        embed = discord.Embed(
            title="Commands",
            description="A list of all commands",
            color=discord.Color.green()
        )
        for cog in cogs.values():
            if hasattr(cog,"help_index") :
                string = ""
                for command in cog.help_index.keys():
                    string += f'`{command}` '
                embed.add_field(name=cog.__cog_name__,value=string)
        return embed
    
    def commandEmbed(self, command):
        cogs = self.bot.cogs
        for cog in cogs.values():
            if hasattr(cog,"help_index"):
                if command in cog.help_index.keys():
                    info = cog.help_index[command]
                    embed = discord.Embed(
                        title=info["name"],
                        description=info["description"],
                        color=discord.Color.green()
                    )
                    for param in info["parameters"]:
                        embed.add_field(name=f"{param["name"]} : {param["type"]}",value=param["usage"])
                    return embed
        return None
        
