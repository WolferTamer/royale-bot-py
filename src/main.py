import discord
import logging
from discord.ext import commands
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

from cogs.contestants import ContestantCog
from cogs.games import GamesCog
from schemas import Base

load_dotenv()

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

intents = discord.Intents.default()
intents.message_content = True

class RoyaleBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        temp_url = f"mysql+mysqlconnector://{os.getenv("DB_USER")}:{os.getenv("DB_PASS")}@{os.getenv("DB_URL")}"
        if not database_exists(temp_url): create_database(temp_url)
        self.engine = create_async_engine(f"mysql+aiomysql://{os.getenv("DB_USER")}:{os.getenv("DB_PASS")}@{os.getenv("DB_URL")}")
        self.AsyncSessionLocal = sessionmaker(
            self.engine, expire_on_commit=False, class_=AsyncSession
        )

    async def setup_hook(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @property
    def session(self) -> AsyncSession:
        return self.AsyncSessionLocal()

bot = RoyaleBot(command_prefix='+',intents=intents)

@bot.event
async def on_ready():  
    await bot.add_cog(GamesCog(bot))
    await bot.add_cog(ContestantCog(bot))
    print(f'Logged into {bot.user.name}')


@bot.event
async def on_message(message:discord.Message):
    if message.author == bot.user:
        return
    
    if "hello" in message.content.lower():
        await message.channel.send(content="Hello!")

    await bot.process_commands(message)


@bot.hybrid_command(description="A command that says hello")
async def hello(ctx):
    await ctx.send(f"Hello {ctx.author.mention}")

@bot.hybrid_command(description="An admin command that updates bot commands on Discord.")
@commands.guild_only()
async def sync(ctx):
    #Copy all global commands and get them assigned to the test server. Without this you would have to wait an hour plus
    #Just to test slash commands.
    bot.tree.copy_global_to(guild=discord.Object(id=895168869361152021))
    await bot.tree.sync(guild=discord.Object(id=895168869361152021))
    await bot.tree.sync()
    await ctx.send("Sync Complete")

@bot.hybrid_command(description="A test command")
async def test(ctx, name: str =commands.parameter(description="Your name")):
    await ctx.send(f"Hello {name}")



bot.run(os.getenv('DISCORD_KEY'), log_handler=handler, log_level=logging.DEBUG) 