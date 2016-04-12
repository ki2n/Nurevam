from discord.ext import commands
from .Utils import Read
import discord
import asyncio
import Storage


def Setup(): #To set up commands for use
    global Command
    Command=Read.Bot_Config["Cogs"]["Channel"] #command so it is easier to call it

def check_roles(msg):
    Roles= Storage.Redis().data.hgetall("{}:Channel:Config".format(msg.message.server.id))
    Roles= "{},{}".format(Roles["Admin_Roles"],Roles["Roles"])
    checking=msg.message.author.roles
    print(Roles)
    for name in checking:
        if str(name) in Roles:
            return True

def is_enable(msg):
    check = Storage.Redis().data.hget("{}:Config".format(msg.message.server.id),"Channel")
    print(check)
    if check == "on":
        return True
    else:
        return False

class Channel():
    """
    Allow user create a temp channel within time limit
    """
    def __init__(self,bot):
        self.bot = bot
        self.Temp_Chan={} #Making a Dict so it can track of channel in
        self.Temp_Count=0 #To count how many channel for limit
        self.allow=discord.Permissions.none()
        self.deny=discord.Permissions.none()
        self.allow.read_messages=True
        self.deny.read_messages=True
        self.bot.add_listener(self.channel_status,"on_channel_delete")
        loop = asyncio.get_event_loop()
        loop.create_task(self.Redis_Data())
    Setup()

    async def Redis_Data(self):#To call Redis so it can begin data.
        self.redis = await Storage.Redis().Start()

    async def channel_status(self,name):
        if self.Temp_Chan.get(name.name):
            self.Temp_Chan.pop(name.name)
            self.Temp_Count -=1

    @commands.check(is_enable)
    @commands.check(check_roles)
    @commands.group(name=Command["Channel"],brief="Main command of sub for channel related.",pass_context=True,invoke_without_command=True)
    async def Channel(self,msg):
        await self.bot.say("\n\nYou need to enter subcommand in!")

    @commands.check(is_enable)
    @commands.check(check_roles)
    @Channel.command(name=Command["Create_Channel"],brief="Allow to create a temp channel for relative topic.",pass_context=True,invoke_without_command=True)
    async def Create_Channel(self,msg,*,name:str):
        '''
        Allow User to make a channel.
        There will be time limit.
        It will then delete a channel.
        '''
        print(msg.message.server)
        server_id = msg.message.server.id
        if self.Temp_Count == await self.redis.hget("{}:Channel:Config".format(server_id),"limit"): #Checking Total channel that already created and compare to atually limit to see
            await self.bot.say("There is already limit channel! Please wait!")
            return
        name = name.replace(" ","-").lower() #to prevert error due to space not allow in channel name
        check = discord.utils.find(lambda c:c.name == name, msg.message.server.channels) #Check if there is exist one, so that user can create one if there is none
        if check is None:
            data= await self.bot.create_channel(msg.message.server,name) #Create channel
            await self.bot.edit_channel_permissions(data,msg.message.server.roles[0],deny=self.deny) #remove @everyone from this channel
            await self.bot.edit_channel_permissions(data,msg.message.author,allow=self.allow) #Invite person to view this channel
            await self.bot.say("{} have now been created.".format(name)) #To info that this channel is created
            self.Temp_Chan.update({server_id:{name:{"Name":data,"Creator":msg.message.author.id}}}) #Channel Name have Channel ID and Creator (Creator ID)
            self.Temp_Count +=1 #add 1 to "Total atm" so we can keep maintain to limit channel
            loop = asyncio.get_event_loop()
            loop.call_later(int(await self.redis.hget("{}:Channel:Config".format(server_id),"Time")), lambda: loop.create_task(self.Timeout(server_id,name))) #Time for channel to be gone soon
        else:
            await self.bot.say("It is already exist, try again!")

    @commands.check(is_enable)
    @Channel.command(name=Command["Join_Channel"],brief="Allow user to join channel",pass_context=True,invoke_without_command=True)
    async def Join_Channel(self,msg,*,name:str): #If user want to join the channel
        '''
        Allow user to join a channel
        '''
        name = name.replace(" ","-").lower() #In case user type channel join with space on name
        if not self.Temp_Chan.get(msg.message.server.id):
            return
        if name in self.Temp_Chan[msg.message.server.id]: #To ensure if channel still exist and in the list
            await self.bot.edit_channel_permissions(self.Temp_Chan[msg.message.server.id][name]["Name"],msg.message.author,allow=self.allow)
            await self.bot.say("You can now view and chat in {}".format(name))
        else:
            await self.bot.say("I am afraid that didn't exist, please double check spelling and case")


    @commands.check(is_enable)
    @commands.check(check_roles)
    @Channel.command(name=Command["Delete_Channel"],brief="Allow user or mod delete channel",pass_context=True,invoke_without_command=True)
    async def Delete_Channel(self,msg,*,name:str): #Allow Admin/Mod or Creator of that channel delete it
        """
        Allow creator delete that certain channel that he have created.
        Mod/Higher up can also delete Channel as well.
        """
        name = name.replace(" ","-").lower()
        mod_bool= False
        Roles= Storage.Redis().data.hgetall("{}:Channel:Config".format(msg.message.server.id))
        Roles= "{},{}".format(Roles["Admin_Roles"],Roles["Roles"])
        if name in self.Temp_Chan[msg.message.server.id]:
            for role in msg.message.author.roles:
                print(role)
                if role.name in Roles:
                    mod_bool = True
                    break
            if msg.message.author.id == self.Temp_Chan[msg.message.server.id][name]["Creator"] or mod_bool is True:
                await self.bot.delete_channel(self.Temp_Chan[msg.message.server.id][name]["Name"])
                await self.bot.say("{} is now delete.".format(name))
            else:
                await self.bot.say("You do not have right to delete this!\nYou need to be either creator of {} or mod".format(name))
        else:
            await self.bot.say("{} does not exist! Please double check spelling".format(name))

    async def Timeout(self,id,name): #Timer, first it will warning user that they have X amount to talk here for while.
        if name not in self.Temp_Chan[id]:
            return
        if int(await self.redis.hget("{}:Channel:Config".format(id),"Warning"))<= 60:
            unit = "second"
            time = int(await self.redis.hget("{}:Channel:Config".format(id),"Warning"))
        else:
            unit= "minute"
            time = int(await self.redis.hget("{}:Channel:Config".format(id),"Warning"))/60
            print (time)
        await self.bot.send_message(self.Temp_Chan[id][name]["Name"],"You have {} {} Left!".format(format(time,".2f"),unit))
        await asyncio.sleep(int(self.redis.hget("{}:Channel:Config".format(id),"Warning")))
        if name not in self.Temp_Chan[id]: #Double check in case user delete it before that time up
            return
        await self.bot.delete_channel(self.Temp_Chan[id][name]["Name"])

def setup(bot):
    bot.add_cog(Channel(bot))