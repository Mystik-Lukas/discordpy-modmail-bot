import discord
from discord.ext import commands
import json
import asyncio
import pymongo
from pymongo import MongoClient
import embedtools
import time
import random

intents=discord.Intents.default()
intents.members=True

with open('secrets.json', 'r') as f:
    secrets=json.load(f)

class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            emby = discord.Embed(description=page, color=discord.Color.greyple())
            await destination.send(embed=emby)

bot=commands.Bot(command_prefix="cm!", intents=intents, help_command=MyNewHelp())

cluster = MongoClient(
    secrets['database_constr'])
db = cluster["aio"]
config = db["wts"]

@bot.event
async def on_ready():
    print("Ready")
    await bot.change_presence(activity=discord.Game("DM For Support"))

keys=[
    {"trigger": "assist", "replace": "Is there anything I can assist with?"},
    {"trigger": "thanks", "replace": "Thank you for contacting support, this thread will close soon, if you have any questions, don't feel afraid to DM the bot later."},
    {"trigger": "reported ", "replace": "The user that you reported has been reported to our moderation team and will be reviewed shortly. Do not hesitate to DM the bot for further reports."},
    {"trigger": "needanswer", "replace": "Hello, I need an answer from you within one hour, or else this thread will close."},
    {"trigger": "trolling", "replace": "Please do not troll with our bot, if you continue, you will be blocked from the bot and will not be able to use it."},
    {"trigger": "hi", "replace": "Hello, this is the support team. If you have any questions, do not feel afraid to ask."},
]

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author == bot.user:
        return
    guild=bot.get_guild() #server id where bot is in
    if not isinstance(message.channel, discord.channel.DMChannel):
        cid=message.channel.id
        ticket=config.find_one({"ticket": int(cid)})
        if ticket is None:
            return
        ticchannel=bot.get_channel(config.find_one({"user": ticket['user']})['ticket'])
        user=await bot.fetch_user(ticket['user'])
        if message.channel.id == ticket['ticket']:
            for key in keys:
                if f"-{key['trigger']}" == message.content.lower():
                    message.content = f"-{key['replace']}"
            if message.attachments and len(message.content) == 0:
                return
            if message.content[0] != "-": 
                return

            if len(message.content) != 0:
                message.content = message.content[1:]
            embed5=discord.Embed(
                color=embedtools.Colors.rand(),
                timestamp=embedtools.Timestamp.time(),
                description=message.content
            )
            embed5.set_author(
                name="Staff",
                icon_url='https://cdn.iconscout.com/icon/free/png-256/businessman-707-1128970.png'
            )
            embed6=discord.Embed(
                color=discord.Color.red(),
                timestamp=embedtools.Timestamp.time(),
                description=message.content
            )
            embed6.set_author(
                name=f"📨 sent by {str(message.author)}",
                icon_url=message.author.avatar_url
            )
            await ticchannel.send(embed=embed6)
            try:
                await user.send(embed=embed5)
            except:
                pass
            num=1
            for attachment in message.attachments:
                embed=discord.Embed(
                    title=f"Attachment #{num}",
                    url=attachment.url
                )
                embed.set_image(
                    url=attachment.url
                )
                num+=1
                await ticchannel.send(embed=embed)
                try:
                    await user.send(embed=embed)
                except:
                    pass
            await message.delete()
            return
    else:
        search=config.find_one({"user": message.author.id})
        if search is None:
            config.insert_one({"user": message.author.id, "inaticket": False, "ticket": None})
        if config.find_one({"user": message.author.id})['inaticket'] is False:
            conf=await message.channel.send("Are you sure you want to send this message?")
            reactions=["✅", "❌"]
            await conf.add_reaction(reactions[0])
            await conf.add_reaction(reactions[1])
            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in ["✅", "❌"]
            try:
                reaction, user=await bot.wait_for('reaction_add', check=check, timeout=30)
            except asyncio.TimeoutError:
                embed=discord.Embed(
                color=discord.Color.red(),
                description='Timed out, you didnt choose an answer',
                timestamp=message.created_at
                )
                return await message.channel.send(embed=embed) 
            if str(reaction.emoji) == "✅":
                
                guild=bot.get_guild() #server id where bot is in
                ticchannel=await guild.create_text_channel(f"{message.author.name}-{message.author.discriminator}")
                roleids=[] #support role ids
                botrole=# bot role in server
                await ticchannel.set_permissions(guild.get_role(botrole), read_messages=True, send_messages=True)
                await ticchannel.set_permissions(guild.default_role, read_messages=False)
                for role in roleids:
                    await ticchannel.set_permissions(guild.get_role(role), read_messages=True, send_messages=True)
                config.update_one({"user": message.author.id}, {"$set":{"inaticket": True}})
                embed=discord.Embed(
                    color=discord.Color.green(),
                    timestamp=message.created_at,
                    description='Thank you for contacting modmail, we will get back to you shortly.'
                )
                embed.set_footer(
                    icon_url=message.author.avatar_url,
                )
                try:
                    await message.author.send(embed=embed)
                except:
                    pass
                config.update_one({"user": message.author.id}, {"$set":{"ticket": ticchannel.id}})
                embed=discord.Embed(
                    color=discord.Color.blue(),
                    title='A new ticket has been created',
                    description='To interact with the ticket, here are some commands and tips:\n\n- Use `-` in front of your message to send it\n- Use s!close to close this'
                )
                s2=config.find_one({"guild": guild.id})
                if s2['logging'] is not None:
                    embedopened=discord.Embed(title="Ticket opened", color=discord.Color.orange())
                    embedopened.add_field(name='Channel', value=ticchannel.mention)
                    embedopened.add_field(name='Created by', value=str(message.author))
                    await bot.get_channel(config.find_one({"guild": guild.id})['logging']).send(embed=embedopened)
                await ticchannel.send(embed=embed)
                embed5=discord.Embed(
                color=discord.Color.blue(),
                timestamp=embedtools.Timestamp.time(),
                description=message.content
                )
                embed5.set_author(
                name=f"📩 received by {str(message.author)}",
                icon_url=message.author.avatar_url
                )
                await ticchannel.send(embed=embed5)
                num=1
                for attachment in message.attachments:
                    embed=discord.Embed(
                        title=f"Attachment #{num}",
                        url=attachment.url
                    )
                    embed.set_image(
                        url=attachment.url
                    )
                    num+=1
                    await ticchannel.send(embed=embed)
                await message.add_reaction("✅")
            elif str(reaction.emoji) == "❌":
                embed=discord.Embed(
                color=discord.Color.red(),
                description='Mail canceled',
                timestamp=message.created_at
                )
                return await message.channel.send(embed=embed)
        else:
            ticchannel=bot.get_channel(config.find_one({"user": message.author.id})['ticket'])
            embed5=discord.Embed(
                color=discord.Color.blue(),
                timestamp=embedtools.Timestamp.time(),
                description=message.content
            )
            embed5.set_author(
                name=f"📩 received by {str(message.author)}",
                icon_url=message.author.avatar_url
            )
            await ticchannel.send(embed=embed5)
            num=1
            for attachment in message.attachments:
                embeda=discord.Embed(
                    title=f"Attachment #{num}",
                    url=attachment.url
                )
                embeda.set_image(
                    url=attachment.url
                )
                num+=1
                await ticchannel.send(embed=embeda)
            await message.add_reaction("✅")
        await message.add_reaction("✅")
    
@bot.command()
async def close(ctx):
    result=config.find_one({'ticket': ctx.channel.id})
    if result is None:
        return
    msg=await ctx.send("React with :white_check_mark: to close this ticket - if you dont react within 10 seconds nothing will happen.")
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅"]
    await msg.add_reaction("✅")
    reaction, user = await bot.wait_for('reaction_add', check=check, timeout=10)
    embed5=discord.Embed(
        color=discord.Color.green(),
        title="Ticket closing in 5"
    )
    embed4=discord.Embed(
        color=discord.Color.green(),
        title="Ticket closing in 4"
    )
    embed3=discord.Embed(
        color=0xffff40,
        title="Ticket closing in 3"
    )
    embed2=discord.Embed(
        color=0xffff40,
        title="Ticket closing in 2"
    )
    embed1=discord.Embed(
        color=discord.Color.red(),
        title="Ticket closing in 1"
    )
    embedclosing=discord.Embed(
        color=discord.Color.red(),
        title="Ticket closing..."
    )
    e5=await ctx.send(embed=embed5)
    await asyncio.sleep(1)
    e4=await e5.edit(content="", embed=embed4)
    await asyncio.sleep(1)
    e3=await e5.edit(content="", embed=embed3)
    await asyncio.sleep(1)
    e2=await e5.edit(content="", embed=embed2)
    await asyncio.sleep(1)
    e1=await e5.edit(content="", embed=embed1)
    await asyncio.sleep(1)
    await e5.edit(content="", embed=embedclosing)
    await asyncio.sleep(1)
    try:
        await ctx.guild.get_member(result['user']).send(embed=discord.Embed(title="Ticket closed", description=f'Your ticket in **{ctx.guild.name}** has been closed', color=discord.Color.purple()))
    except:
        pass
    if config.find_one({"guild": ctx.guild.id})['logging'] is not None:
        embed=discord.Embed(title="Ticket closed", color=discord.Color.purple())
        embed.add_field(name='Closed by', value=ctx.author)
        await bot.get_channel(config.find_one({"guild": ctx.guild.id})['logging']).send(embed=embed)
    await ctx.channel.delete()
    config.delete_one({'ticket': ctx.channel.id})

def is_user(id1: int):
    async def predicate(ctx):
        return ctx.author.id == id1
    return commands.check(predicate)

@bot.command()
@is_user() # id of person that can use this command
async def logchannel(ctx, channel:discord.TextChannel=None):
    search=config.find_one({"guild": ctx.guild.id})
    if search is None:
        config.insert_one({"guild": ctx.guild.id, "logging": None})
    if channel is None:
        if config.find_one({"guild": ctx.guild.id})['logging'] is None:
            return await ctx.send("There is no channel set - do `s!logchannel <channel>` to set one.")
        new=config.find_one({"guild": ctx.guild.id})
        return await ctx.send(f"The current log channel for this server is {bot.get_channel(new['logging'])}.")
    await ctx.send(f"Log channel set to {channel.mention}.")
    config.update_one({"guild": ctx.guild.id}, {"$set":{"logging": channel.id}})

@bot.command()
async def ping(ctx):
    before = time.monotonic()
    message=await ctx.send(f"API Ping: {round(bot.latency*1000)}ms\nBot Ping: n/a")
    ping = (time.monotonic() - before) * 1000
    await message.edit(content=f"API Ping: {round(bot.latency*1000)}ms\nBot Ping: `{int(ping)}ms`")
    

@bot.event
async def on_command_error(ctx, error):
    await ctx.send(error)
    raise(error)

@bot.command()
async def keylist(ctx):
    embed=discord.Embed(
        color=discord.Color.blue(),
    )
    for key in keys:
        embed.add_field(
            name=f"-{key['trigger']}",
            value=key['replace'],
            inline=False
        )
    await ctx.send(embed=embed)


bot.run(secrets['token'])