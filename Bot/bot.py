from discord.ext import commands
from cogs.utils import utils
import datetime
import glob
import storage
import discord
import traceback
import asyncio
import inspect
import re

description = '''Nurevam's Command List. '''
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), description=description,pm_help=False)
bot.db= storage.Redis()

async def say_edit(msg):
    try:
        key = str(inspect.getmodule(inspect.currentframe().f_back.f_code))
        regex = re.compile(r"(cogs.[a-zA-Z]*)")
        get = re.search(regex,key)
        if get:
            word = await bot.say(msg)
            check = await bot.db.redis.hgetall("{}:Config:Delete_MSG".format(word.server.id))
            if check.get(get.groups()[0][5:]) == "on":
                await asyncio.sleep(30)
                await bot.delete_message(word)
        else:
            print("NONE")
        return
    except:
        utils.prRed(traceback.format_exc())
bot.says_edit=say_edit

@bot.event
async def on_ready():
    print('Logged in')
    print(bot.user.id)
    print('------')
    if not hasattr(bot, 'uptime'):
            bot.uptime = datetime.datetime.utcnow()
    utils.redis_connection()
    load_cogs()
    bot.commands["help"].hidden = True

@bot.event
async def on_message(msg): #For help commands.
    try:
        cmd_prefix= (await bot.db.redis.get("{}:Config:CMD_Prefix".format(msg.server.id)))
        cmd_prefix=cmd_prefix.split(",")
        if '' in cmd_prefix: #check if "none-space" as a command, if true, return, in order to prevert any spam in case, lower chance of getting kick heh.
            return
        bot.command_prefix = commands.when_mentioned_or(*cmd_prefix)
        if "help" in msg.content:
            if await bot.db.redis.get("{}:Config:Whisper".format(msg.server.id)) == "on":
                bot.pm_help =True
            else:
                bot.pm_help=False
    except:
        pass

    await bot.process_commands(msg)


def load_cogs():
    cogs = list_cogs()
    for cogs in cogs:
        try:
            bot.load_extension(cogs)
            print ("Load {}".format(cogs))
        except Exception as e:
            utils.prRed(cogs)
            utils.prRed(e)
            # continue
            # raise

def list_cogs():
    cogs = glob.glob("cogs/*.py")
    clean = []
    for c in cogs:
        c = c.replace("/", "\\") # Linux fix
        if "__init__" in c:
            continue
        clean.append("cogs." + c.split("\\")[1].replace(".py", ""))
    return clean

@bot.event
async def on_error(event,*args,**kwargs):
    Current_Time = datetime.datetime.utcnow().strftime("%b/%d/%Y %H:%M:%S UTC")
    utils.prRed(Current_Time)
    utils.prRed("Error!")
    utils.prRed(traceback.format_exc())
    error =  '```py\n{}\n```'.format(traceback.format_exc())
    user=discord.utils.get(bot.get_all_members(),id="105853969175212032")
    await bot.send_message(user, "```py\n{}```".format(Current_Time + "\n"+ "ERROR!") + "\n" + error)

if __name__ == '__main__':
    bot.run(utils.OS_Get("NUREVAM_TOKEN"))

