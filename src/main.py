from random import random
from typing import List
from cogs.help import HelpCog
from events.event import Event
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
from cogs.play import PlayCog
from schemas import Base
import json

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
        try:
            with open('events.json', 'r') as f:
                data = json.load(f)
            self.events = [] 
            self.fightevents = [] #events where 2+ groups fight eachother
            self.groupevents = [] #events where 1 group doesn't fight
            self.soloevents = [] #events where an individual does something
            self.deathevents = [] #events where an individual dies alone
            for i in range(0,len(data)):
                cat = data[i]
                for eventdata in cat:
                    event = Event(eventdata["message"],eventdata["groups"],[tuple(t) for t in eventdata["deaths"]])
                    self.events.append(event)
                    match i:
                        case 0: self.fightevents.append(event)
                        case 1: self.groupevents.append(event)
                        case 2: self.soloevents.append(event)
                        case 3: self.deathevents.append(event)

        except FileNotFoundError:
            print("Error: 'events.json' not found. Please ensure the file exists in the correct directory.")
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in 'events.json'.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    def get_any_event(self):
        rand = int(random()*len(self.events))
        return self.events[rand]
    
    def get_event_of_type(self, type : str):
        l = self.get_type_array(type)
        rand = int(random()*len(l))
        return l[rand]
    
    def get_event_filter(self, type : str = "none", max_groups: List[int] = [], max_deaths: int = 99):
        l = self.get_type_array(type)
        def matches(e : Event):
            for g in range(0,len(e.groups)):
                if(len(max_groups) > g and e.groups[g] > max_groups[g]) :
                    return False
                
            if max_deaths < len(e.dead):
                return False
            return True
        filtered = list(filter(matches, l))
        rand = int(random()*len(filtered))
        return filtered[rand]

    def get_type_array(self, type : str):
        match type:
            case "fight": return self.fightevents
            case "group": return self.groupevents
            case "solo": return self.soloevents
            case "death": return self.deathevents
        return self.events

    async def setup_hook(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @property
    def session(self) -> AsyncSession:
        return self.AsyncSessionLocal()

bot = RoyaleBot(command_prefix='+',intents=intents, help_command=None)

@bot.event
async def on_ready():  
    await bot.add_cog(GamesCog(bot))
    await bot.add_cog(ContestantCog(bot))
    await bot.add_cog(PlayCog(bot))
    await bot.add_cog(HelpCog(bot))
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