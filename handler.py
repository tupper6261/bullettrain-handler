#Bullet Train Handler Bot. Copyright Timothy Marshall Upper, 2022. All Rights Reserved.
#Version 1.1 - January 4, 2022

import os
import random
import urllib.request
import time
import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from discord.commands import Option
from dotenv import load_dotenv
import psycopg2
import json
import requests
import datetime
import asyncio

load_dotenv()

TOKEN = os.getenv('HANDLER_TOKEN')
DATABASETOKEN = os.getenv('DATABASE_URL')
NIFTYSDATABASETOKEN = os.getenv('NIFTYS_DATABASE_URL')
niftysAuthorization = os.getenv('NIFTYS_BEARER_TOKEN')
niftysAuthKeyID = os.getenv('NIFTYS_AUTH_KEY')

niftysAPIHeaders = {
    'accept': 'application/json',
    'Authorization': niftysAuthorization,
    'auth-key-id': niftysAuthKeyID,
}

#To be honest, I don't know enough about what the below does, I just know it's what Google told me to do XD
#I would think I'm initializing a Client object, but I never call it again, so....
client = discord.Client()
#This one tells the bot to look for commands that start with ! (ie. !fight)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="%", intents=intents)

#Defines a View class. Overrides the default View class primarily so I can override the timeout timer/reaction
class MyView(View):
    
    def __init__(self, ctx):
        super().__init__(timeout = 10)
        self.ctx = ctx

    async def on_timeout(self):
        for i in self.children:
            if isinstance(i, Button):
                i.disabled = True
        for i in self.children:
            if isinstance(i, Select):
                self.remove_item(i)
        await self.message.edit_original_message(view = self)

async def winning(interaction, assignmentView, assassins, wallet):
    guild = bot.get_guild(869370430287384576)
    channel = discord.utils.get(guild.channels, id = 1052988866967122041)
    numAssassins = len(assassins)
    eligibleNFT = 1671566400
    while int(time.time()) > eligibleNFT:
        eligibleNFT += 604800
    eventEmbed = discord.Embed(color = 0x000000)
    eventEmbed.description = interaction.user.mention + " found the briefcase!"
    await channel.send(embed = eventEmbed)
    assignmentView.clear_items()
    assignmentEmbed = discord.Embed(color = 0x000000)
    assignmentEmbed.title = "Success!"
    if numAssassins == 0:
        assignmentEmbed.description = """You found the briefcase!\n\n
                                            You do not, however, have any Assassins eligible for a briefcase NFT. You will be eligible again <t:{0}:R>""".format(str(eligibleNFT))
    elif numAssassins == 1:
        assignmentEmbed.description = """You found the briefcase!\n\n
                                            You will be sent 1 briefcase NFT. Your handler will be calling you to let you know how to proceed with it."""
    else:
        assignmentEmbed.description = """You found the briefcase!\n\n
                                            You will be sent {0} briefcase NFTs. Your handler will be calling you to let you know how to proceed with them.""".format(str(numAssassins))
    await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
    if numAssassins > 0:
        #Update the user's cooldown time, so he can't mint a breifcase while we update the assassin table
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+numAssassins, interaction.user.id)
        cur.execute(command)
        conn.commit()
        for assassin in assassins:
            command = "update btassignment2assassins set cooldown_time = {0} where token_id = {1}".format(eligibleNFT, assassin)
            cur.execute(command)
            conn.commit()
        cur.close()
        conn.commit()
        conn.close()

        while numAssassins > 0:
            #mint the NFTs
            headers = {
                'accept': 'application/json',
                'Authorization': 'Bearer CDE92CA478D2C882B4442A34BF7ED72451B823308758FFC8D58026D1AEBA1696',
                'auth-key-id': 'cl09vur0n04903mqn7y7feewr',
            }
            if numAssassins < 10:
                mintPayload = {
                  "contractAddress": "0x191be1aebdfed6dad012693d73cf4db43562c1fe",
                  "network": "PALM",
                  "toAddress": wallet,
                  "amount": numAssassins
                }
                numAssassins = 0
            else:
                mintPayload = {
                  "contractAddress": "0x191be1aebdfed6dad012693d73cf4db43562c1fe",
                  "network": "PALM",
                  "toAddress": wallet,
                  "amount": 10
                }
                numAssassins = numAssassins - 10
            response = requests.post('https://api.niftys.com/v1/public/mint-items', headers=headers, json = mintPayload)
            data = json.loads(response.text)
            while str(response) != "<Response [200]>":
                data = json.loads(response.text)
                response = requests.post('https://api.niftys.com/v1/public/mint-items', headers=headers, json = mintPayload)
        return

async def checkCooldown(interaction, assignmentEmbed, assignmentView):
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()

    #See if the user's cooldown is still in effect
    command = "select * from btassignment2discordusers where discord_user_id = {0}".format(interaction.user.id)
    cur.execute(command)
    status = cur.fetchall()
    cur.close()
    conn.close()
    account = status[0]
    eligibleToClaim = account[1]
    if eligibleToClaim > int(time.time()):
        assignmentView.clear_items()
        assignmentEmbed.title = "Still Recovering"
        assignmentEmbed.description = "You are still recovering. You may attempt this assignment again <t:" + str(eligibleToClaim) +":R>."
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        return True
    else:
        return False

async def event(interaction, assignmentEmbed, assignmentView, trainCar):
    eventRNG = random.randint(1,70)
    guild = bot.get_guild(869370430287384576)
    channel = discord.utils.get(guild.channels, id = 1052988866967122041)
    searchChannel = discord.utils.get(guild.channels, id = 971771679263051787)
    phoneHolderRole = discord.utils.get(guild.roles, id = 1052614060102930473)
    eventPartner = random.randint(0, len(phoneHolderRole.members)-1)
    eventPartner = phoneHolderRole.members[eventPartner]

    luckyView = View(timeout = None)

    async def continueButton_callback(interaction):
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)

    continueButton = Button(label="Continue", style = discord.ButtonStyle.blurple)
    continueButton.callback = continueButton_callback
    
    luckyView.clear_items()
    luckyView.add_item(continueButton)
    
    
    if eventRNG == 1:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " was bitten in the jugular by a snake!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = "You look around hoping to find the briefcase when out of nowhere a snake launches itself at you biting you right in the jugular! You lose! You must wait 3 hours and begin your search again."
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 2:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " was stabbed by a young girl!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = "You continue your search and see a young girl, hunched over crying. You lean in to ask if she needs any help, but she reveals a hidden knife and stabs you! You lose! You must wait 3 hours and begin your search again."
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 3:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " was stabbed by the Momonga!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = """Oh look! It's the loveable Momonga! Surely you have enough time for an autograph!\n
                                            Uh oh... It just flung a knife at you! You lose! You must wait 3 hours and begin your search again."""
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 4:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + "'s water bottle was poisoned!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = """All this searching is making you feel tired, and thirsty. You notice a water bottle, which you grab and take a giant gulp.\n
                                        *This tastes funny...*\n
                                        You passed out! You must wait 3 hours and begin your search again."""
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 5:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = eventPartner.mention + " threatened " + interaction.user.mention + " and they panicked and got off the train!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = """You see a cell phone laying on the center of the floor and reach over to pick it up. Someone is already on the line.\n
                                        "Hello?" you say.\n
                                        It's """ + eventPartner.mention + """! They respond: "Your time is up, I’m coming after you!" You panic and give up your search! You must wait 3 hours and begin your search again"""
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 6:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = eventPartner.mention + " was the better fighter and took out " + interaction.user.mention + "!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = eventPartner.mention + """ just walked in...\n
                                            You stare at each other for 30 seconds before you launch into battle.\n
                                            The battle was neck and neck, but """ + eventPartner.mention + """ got the better of you this time! You must wait 3 hours and begin your search again."""
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 7:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " was poisoned by the beverage cart lady!"
        await channel.send(embed = eventEmbed)
        assignmentView.clear_items()
        assignmentView.timeout = 60
        assignmentEmbed.title = ""
        assignmentEmbed.description = """The beverage cart lady walks by.\n
                                        “Can I offer you any refreshments?” she asks.\n
                                        You nod yes and she reaches into her cart. Oh no, she was an assassin in disguise! Tough luck! You must wait 3 hours and begin your search again."""
        await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time())+10800, interaction.user.id)
        cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return True
    elif eventRNG == 8:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " found 100 Discord coins!"
        await channel.send(embed = eventEmbed)
        luckyEmbed = discord.Embed(color = 0x000000)
        luckyEmbed.description = "You found 100 Discord coins!"
        await interaction.response.edit_message(embed = luckyEmbed, view = luckyView)
        #Give user their coins
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "select * from vault where discord_user_id = {0}".format(interaction.user.id)
        cur.execute(command)
        account = cur.fetchall()
        if account == []:
            command = "insert into vault (discord_user_id, balance, daily_claimed) values ({0}, 10100, {1})".format(interaction.user.id, int(time.time()))
            cur.execute(command)
        else:
            account = account[0]
            newBalance = account[1] + 100
            command = "update vault set balance = {0} where discord_user_id = {1}".format(newBalance,interaction.user.id)
            cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return False
    elif eventRNG == 9:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " searched " + eventPartner.mention + "'s unconscious body and found 100 Discord coins!"
        await channel.send(embed = eventEmbed)
        luckyEmbed = discord.Embed(color = 0x000000)
        luckyEmbed.description = "You notice " + eventPartner.mention + " slumped over in the corner, seemingly unconscious. You search them and find 100 Discord coins in their pocket!"
        await interaction.response.edit_message(embed = luckyEmbed, view = luckyView)
        #Give user their coins
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "select * from vault where discord_user_id = {0}".format(interaction.user.id)
        cur.execute(command)
        account = cur.fetchall()
        if account == []:
            command = "insert into vault (discord_user_id, balance, daily_claimed) values ({0}, 10100, {1})".format(interaction.user.id, int(time.time()))
            cur.execute(command)
        else:
            account = account[0]
            newBalance = account[1] + 100
            command = "update vault set balance = {0} where discord_user_id = {1}".format(newBalance,interaction.user.id)
            cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return False
    elif eventRNG == 10:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " found a coat with 100 Discord coins in the pocket!"
        await channel.send(embed = eventEmbed)
        luckyEmbed = discord.Embed(color = 0x000000)
        luckyEmbed.description = "You notice a seat with a coat draped over it. You search the coat and find 100 Discord coins!"
        await interaction.response.edit_message(embed = luckyEmbed, view = luckyView)
        #Give user their coins
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "select * from vault where discord_user_id = {0}".format(interaction.user.id)
        cur.execute(command)
        account = cur.fetchall()
        if account == []:
            command = "insert into vault (discord_user_id, balance, daily_claimed) values ({0}, 10100, {1})".format(interaction.user.id, int(time.time()))
            cur.execute(command)
        else:
            account = account[0]
            newBalance = account[1] + 100
            command = "update vault set balance = {0} where discord_user_id = {1}".format(newBalance,interaction.user.id)
            cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return False
    elif eventRNG == 11:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + " was the better fighter and took out " + eventPartner.mention + "! " + eventPartner.mention + " had 100 Discord coins in their pocket, which " + interaction.user.mention + " took for themself."
        await channel.send(embed = eventEmbed)
        luckyEmbed = discord.Embed(color = 0x000000)
        luckyEmbed.description = eventPartner.mention + """ just walked in...\n
                                            You stare at each other for 30 seconds before you launch into battle.\n
                                            The battle was neck and neck, but you came out victorious!\n
                                            """ + eventPartner.mention + """ had 100 Discord coins in their pocket, which you take for yourself."""
        await interaction.response.edit_message(embed = luckyEmbed, view = luckyView)
        #Give user their coins
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "select * from vault where discord_user_id = {0}".format(interaction.user.id)
        cur.execute(command)
        account = cur.fetchall()
        if account == []:
            command = "insert into vault (discord_user_id, balance, daily_claimed) values ({0}, 10100, {1})".format(interaction.user.id, int(time.time()))
            cur.execute(command)
        else:
            account = account[0]
            newBalance = account[1] + 100
            command = "update vault set balance = {0} where discord_user_id = {1}".format(newBalance,interaction.user.id)
            cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return False
    elif eventRNG == 12 and trainCar:
        eventEmbed = discord.Embed(color = 0x000000)
        eventEmbed.description = interaction.user.mention + "searched " + eventPartner.mention + "'s unconscious body and found 100 Discord coins!"
        await channel.send(embed = eventEmbed)
        luckyEmbed = discord.Embed(color = 0x000000)
        luckyEmbed.description = """You attempt to enter the car, but the door is stuck? You push the door as hard as you can and accidentally knock out """ + eventPartner.mention + """ who was on the other side of the door...\n
                                    That was lucky! The assassin had 100 Discord coins in their pocket, which you take for yourself."""
        await interaction.response.edit_message(embed = luckyEmbed, view = luckyView)
        #Give user their coins
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()
        command = "select * from vault where discord_user_id = {0}".format(interaction.user.id)
        cur.execute(command)
        account = cur.fetchall()
        if account == []:
            command = "insert into vault (discord_user_id, balance, daily_claimed) values ({0}, 10100, {1})".format(interaction.user.id, int(time.time()))
            cur.execute(command)
        else:
            account = account[0]
            newBalance = account[1] + 100
            command = "update vault set balance = {0} where discord_user_id = {1}".format(newBalance,interaction.user.id)
            cur.execute(command)
        cur.close()
        conn.commit()
        conn.close()
        return False
    else:
        return False

        

@bot.event
async def on_ready():
    guild = bot.get_guild(869370430287384576)
    channel = discord.utils.get(guild.channels, id =1048698143656657057)
    msg = await channel.fetch_message(1048701083393998888)
    view = View(timeout = None)
    view.clear_items()

    async def beginButton_callback(interaction):
        location = random.randint(1,21)
        ownedAssassins = []
        eligibleAssassins = []

        assignmentView = View(timeout = None)
        assignmentEmbed = discord.Embed(color = 0x000000)

        assignmentEmbed.title = "Loading..."
        assignmentEmbed.description = "0%"
        await interaction.response.send_message(embed = assignmentEmbed, ephemeral = True, view = assignmentView)

        assassinHolderRole = discord.utils.get(guild.roles, id = 1024692977261621298)
        phoneHolderRole = discord.utils.get(guild.roles, id = 1052614060102930473)
        #if the user isn't an assassin holder, don't let them complete the assignment
        if assassinHolderRole not in interaction.user.roles:
            assignmentView.clear_items()
            assignmentEmbed.title = "Not an Assassin Holder"
            assignmentEmbed.description = "You must own a Bullet Train Assassin NFT to participate in this assignment. If you feel you are getting this message in error, please make sure your Nifty's handle is linked in <#971831743185297448>. Please see <#971831707735056394> for more information.\n\nIf you require assistance, please head to <#916101533924462592> and someone from the Nifty's team will assist."
            await interaction.edit_original_message(embed = assignmentEmbed, view = assignmentView)
            return
        if phoneHolderRole not in interaction.user.roles:
            assignmentView.clear_items()
            assignmentEmbed.title = "Not a Working Phone Holder"
            assignmentEmbed.description = "You must own a Working Phone NFT to participate in this assignment. If you feel you are getting this message in error, please make sure your Nifty's handle is linked in <#971831743185297448>. Please see <#971831707735056394> for more information.\n\nIf you require assistance, please head to <#916101533924462592> and someone from the Nifty's team will assist."
            await interaction.edit_original_message(embed = assignmentEmbed, view = assignmentView)
            return
        
        assignmentEmbed.description = "10%"
        await interaction.edit_original_message(embed = assignmentEmbed) 
        
        conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
        cur = conn.cursor()

        assignmentEmbed.description = "25%"
        await interaction.edit_original_message(embed = assignmentEmbed)  

        #See if the user's cooldown is still in effect
        command = "select * from btassignment2discordusers where discord_user_id = {0}".format(interaction.user.id)
        cur.execute(command)
        status = cur.fetchall()
        if status == []:
            eligibleToClaim = int(time.time())
            command = "insert into btassignment2discordusers (discord_user_id, cooldown_time) values ({0}, {1})".format(interaction.user.id, eligibleToClaim)
            cur.execute(command)
            account = interaction.user.id
        else:
            account = status[0]
            eligibleToClaim = account[1]
        if eligibleToClaim > int(time.time()):
            assignmentView.clear_items()
            assignmentEmbed.title = "Still Recovering"
            assignmentEmbed.description = "You are still recovering. You may attempt this assignment again <t:" + str(eligibleToClaim) +":R>."
            await interaction.edit_original_message(embed = assignmentEmbed, view = assignmentView)
            return

        #Get the user's owned avatars and find out which ones are eligible for a briefcase NFT.
        command = "select account_name from niftysaccounts where discord_user_id = '{0}'".format(interaction.user.id)
        cur.execute(command)
        accounts = cur.fetchall()
        ownedAccounts = []
        for account in accounts:
            ownedAccounts.append(account[0])
        command = "select wallet from wallets where discord_user_id = {0} and default_wallet = 1".format(interaction.user.id)
        cur.execute(command)
        defaultWallet = cur.fetchall()

        #Make sure the user has their wallet connected.
        if defaultWallet == []:
            assignmentView.clear_items()
            assignmentEmbed.title = "Wallet Not Linked"
            assignmentEmbed.description = "Before you attempt this assignment, you must link your wallet address in <#971831743185297448>. Please see <#971831707735056394> for more information.\n\nIf you require assistance, please head to <#916101533924462592> and someone from the Nifty's team will assist."
            await interaction.edit_original_message(embed = assignmentEmbed, view = assignmentView)
            return
        
        defaultWallet = defaultWallet[0][0]
        command = "select token_id from btassignment2assassins where cooldown_time < {0}".format(int(time.time()))
        cur.execute(command)
        assassins = cur.fetchall()
        for assassin in assassins:
            eligibleAssassins.append(assassin[0])
        cur.close()
        conn.commit()
        conn.close()

        assignmentEmbed.description = "50%"
        await interaction.edit_original_message(embed = assignmentEmbed)
        
        conn2 = psycopg2.connect(psycopg2.connect(NIFTYSDATABASETOKEN, options="-c search_path=postgres")
        cur2 = conn2.cursor()
        for handle in ownedAccounts:
            cur2.execute("""
                select w.address, a.handle
                from public."Account" a
                left join public."Wallet" w on w."accountId" = a.id
                where a.handle = '{0}'
            """.format(handle))
            wallets = cur2.fetchall()
            ownedWallets = []
            for wallet in wallets:
                cur2.execute("""select token_id from public.nft_balance where contract_address = '0xf49034ee4d5d6a0b6f3325a3827bf0a7e6159069' and address = '{0}'""".format(wallet[0]))
                results = cur2.fetchall()
                for i in results:
                    ownedAssassins.append(i[0])
        cur2.close()
        conn2.commit()
        conn2.close()

        assignmentEmbed.description = "75%"
        await interaction.edit_original_message(embed = assignmentEmbed)
        
        assassinNFTs = []
        for assassin in ownedAssassins:
            if int(assassin) in eligibleAssassins:
                assassinNFTs.append(int(assassin))      

        assignmentEmbed.description = "100%"
        await interaction.edit_original_message(embed = assignmentEmbed)

        await asyncio.sleep(1)
            
        async def trainButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(engineButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(firstclassButton)
            assignmentView.add_item(galleyButton)
            assignmentView.add_item(momongaButton)
            assignmentView.add_item(stationButton)
            assignmentEmbed.title = "Board the Train"
            assignmentEmbed.description = "Which car would you like to board?"
            await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)

        async def stationButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(ticketButton)
            assignmentView.add_item(concessionsButton)
            assignmentView.add_item(platformButton)
            assignmentView.add_item(trainButton)
            assignmentEmbed.title = "The Train Station"
            assignmentEmbed.description = "You remain at the station to continue searching. Where do you search next?"
            await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)

        async def ticketButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 1:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(concessionsButton)
            assignmentView.add_item(platformButton)
            assignmentView.add_item(trainButton)
            assignmentEmbed.title = "The Ticket Office"
            assignmentEmbed.description = "You search the ticket office, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def concessionsButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 2:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(ticketButton)
            assignmentView.add_item(platformButton)
            assignmentView.add_item(trainButton)
            assignmentEmbed.title = "The Concessions Area"
            assignmentEmbed.description = "You search the concessions area, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def platformButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 3:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(ticketButton)
            assignmentView.add_item(concessionsButton)
            assignmentView.add_item(trainButton)
            assignmentEmbed.title = "The Platform"
            assignmentEmbed.description = "You search around the platform, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def quietButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(luggageButton)
            assignmentView.add_item(seatButton)
            assignmentView.add_item(pocketButton)
            assignmentView.add_item(engineButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "The Quiet Car"
            assignmentEmbed.description = """You make your way into the Quiet Car and take a seat. You look around and don't see anything obvious, but there are several places where someone might hide a briefcase.\n
                                            This car is behind the Engine Car and in front of the First Class Car, so you can leave and search one of those cars as well. Additionally, the Bathroom is located between this car and the First Class car. Maybe the briefcase is hidden in there?"""
            eventResults = await event(interaction, assignmentEmbed, assignmentView, True)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def luggageButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 4:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(seatButton)
            assignmentView.add_item(pocketButton)
            assignmentView.add_item(engineButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "The Luggage Area"
            assignmentEmbed.description = "You search the luggage area, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def seatButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 5:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(luggageButton)
            assignmentView.add_item(pocketButton)
            assignmentView.add_item(engineButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "Under Your Seat"
            assignmentEmbed.description = "You search under your seat, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def pocketButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 6:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(luggageButton)
            assignmentView.add_item(seatButton)
            assignmentView.add_item(engineButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "Inside Seatback Pocket"
            assignmentEmbed.description = "You search inside the seatback pocket, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def firstclassButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(coatButton)
            assignmentView.add_item(reclinedseatButton)
            assignmentView.add_item(overheadButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "The First Class Car"
            assignmentEmbed.description = """Lucky for you, the Assassins’ Guild provided you with a First Class ticket, so you make your way into the First Class Car and take your assigned seat. It’s actually quite comfortable — like, really comfortable. You lean the seat back — it reclines fully into a bed! Don’t relax for too long though, there’s still a briefcase that needs to be found!\n
                                                This car is behind the Quiet Car and in front of the Galley Car. You can leave and search one of those cars, as well. Additionally, the Bathroom is located between this car and the Quiet car. Maybe the briefcase is hidden in there?"""
            eventResults = await event(interaction, assignmentEmbed, assignmentView, True)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def coatButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 7:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(reclinedseatButton)
            assignmentView.add_item(overheadButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "Coat Closet"
            assignmentEmbed.description = "You search inside the coat closet, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return
            
        async def reclinedseatButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 8:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(coatButton)
            assignmentView.add_item(overheadButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "Under Your Seat"
            assignmentEmbed.description = "You search under your fully-reclined seat, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def overheadButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 9:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(coatButton)
            assignmentView.add_item(reclinedseatButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(bathroomButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "Overhead Bin"
            assignmentEmbed.description = "You search the overhead bin, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def galleyButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(beverageButton)
            assignmentView.add_item(refrigeratorButton)
            assignmentView.add_item(pantryButton)
            assignmentView.add_item(firstclassButton)
            assignmentView.add_item(momongaButton)
            assignmentEmbed.title = "The Galley Car"
            assignmentEmbed.description = """You enter the Galley Car and take a look around. Plenty of places to hide a briefcase in here. You swipe a bottle of water from one of the shelves and take a sip. Time to search!\n
                                                Or, if you’d rather, this car is behind the First Class Car and in front of the Momomon Car, so you can leave and search one of those cars instead."""
            eventResults = await event(interaction, assignmentEmbed, assignmentView, True)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def beverageButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 10:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(refrigeratorButton)
            assignmentView.add_item(pantryButton)
            assignmentView.add_item(firstclassButton)
            assignmentView.add_item(momongaButton)
            assignmentEmbed.title = "Beverage Cart"
            assignmentEmbed.description = "You search the beverage cart, but find nothing."
            await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)

        async def refrigeratorButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 11:
                cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
                if cooldown:
                    return
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(beverageButton)
            assignmentView.add_item(pantryButton)
            assignmentView.add_item(firstclassButton)
            assignmentView.add_item(momongaButton)
            assignmentEmbed.title = "Overhead Bin"
            assignmentEmbed.description = "You search inside the refrigerator, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def pantryButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 12:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(beverageButton)
            assignmentView.add_item(refrigeratorButton)
            assignmentView.add_item(firstclassButton)
            assignmentView.add_item(momongaButton)
            assignmentEmbed.title = "Pantry"
            assignmentEmbed.description = "You search inside the pantry, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def engineButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(cockpitButton)
            assignmentView.add_item(electricalButton)
            assignmentView.add_item(controlpanelButton)
            assignmentView.add_item(quietButton)
            assignmentEmbed.title = "The Engine Car"
            assignmentEmbed.description = """You cautiously make your way into the Engine Car. Luckily, the conductor is elsewhere. You can look around if you’re quick.\n
                                                This car is in front of the Quiet Car, so you can leave and search that car as well, if you would prefer."""
            eventResults = await event(interaction, assignmentEmbed, assignmentView, True)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def cockpitButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 13:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(electricalButton)
            assignmentView.add_item(controlpanelButton)
            assignmentView.add_item(quietButton)
            assignmentEmbed.title = "Cockpit"
            assignmentEmbed.description = "You search the cockpit drawer, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def electricalButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 14:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(cockpitButton)
            assignmentView.add_item(controlpanelButton)
            assignmentView.add_item(quietButton)
            assignmentEmbed.title = "Electrical Box"
            assignmentEmbed.description = "You search the electrical box, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def controlpanelButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 15:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(cockpitButton)
            assignmentView.add_item(electricalButton)
            assignmentView.add_item(quietButton)
            assignmentEmbed.title = "Control Panel"
            assignmentEmbed.description = "You search under the control panel, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def bathroomButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(mirrorButton)
            assignmentView.add_item(sinkButton)
            assignmentView.add_item(stallButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "The Bathroom"
            assignmentEmbed.description = """You head into the Bathroom and close the door behind you. It’s actually a fairly large, family-size bathroom; the largest you’ve ever seen on a train. There are plenty of places here where a briefcase could be hidden.\n
                                                The Bathroom is between the Quiet Car and the First Class Car, so you can also leave and search one of those instead."""
            eventResults = await event(interaction, assignmentEmbed, assignmentView, True)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def mirrorButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 16:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(sinkButton)
            assignmentView.add_item(stallButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "Behind the Mirror"
            assignmentEmbed.description = "You search behind the mirror, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def sinkButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 17:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(mirrorButton)
            assignmentView.add_item(stallButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "Under the Sink"
            assignmentEmbed.description = "You search under the sink, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def stallButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 18:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(mirrorButton)
            assignmentView.add_item(sinkButton)
            assignmentView.add_item(quietButton)
            assignmentView.add_item(firstclassButton)
            assignmentEmbed.title = "Inside the Stall"
            assignmentEmbed.description = "You search inside the stall, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def momongaButton_callback(interaction):
            assignmentView.clear_items()
            assignmentView.add_item(costumeButton)
            assignmentView.add_item(tvButton)
            assignmentView.add_item(momongaoverheadButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "The Momomon Car"
            assignmentEmbed.description = """You enter the Momomon Car and you’re having a hard time not being distracted by the music, lights, and TVs. It is your favorite anime, after all. Luckily, most of the passengers appear distracted too, so you should be able to look around without drawing too much suspicion. That empty Momonga costume slumped over in the corner is odd… There was definitely someone signing autographs at the station...\n
                                                This car is behind the Galley Car, so you can leave and search that car as well, if you would prefer."""
            eventResults = await event(interaction, assignmentEmbed, assignmentView, True)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def costumeButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 19:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(tvButton)
            assignmentView.add_item(momongaoverheadButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "Momonga Costume"
            assignmentEmbed.description = "You search the Momonga costume, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def tvButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 20:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(costumeButton)
            assignmentView.add_item(momongaoverheadButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "Behind the TV's"
            assignmentEmbed.description = "You search behind the TV's, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return

        async def momongaoverheadButton_callback(interaction):
            cooldown = await checkCooldown(interaction, assignmentEmbed, assignmentView)
            if cooldown:
                return
            if location == 21:
                await winning(interaction, assignmentView, assassinNFTs, defaultWallet)
                return
            assignmentView.clear_items()
            assignmentView.add_item(costumeButton)
            assignmentView.add_item(tvButton)
            assignmentView.add_item(galleyButton)
            assignmentEmbed.title = "Overhead Compartment"
            assignmentEmbed.description = "You search the overhead compartment, but find nothing."
            eventResults = await event(interaction, assignmentEmbed, assignmentView, False)
            if eventResults:
                return
            try:
                await interaction.response.edit_message(embed = assignmentEmbed, view = assignmentView)
            finally:
                return
        
        trainButton = Button(label="Board the Train", style = discord.ButtonStyle.blurple)
        trainButton.callback = trainButton_callback
        ticketButton = Button(label="Search the Ticket Office", style = discord.ButtonStyle.blurple)
        ticketButton.callback = ticketButton_callback
        concessionsButton = Button(label="Search the Concessions Area", style = discord.ButtonStyle.blurple)
        concessionsButton.callback = concessionsButton_callback
        platformButton = Button(label="Search the Platform", style = discord.ButtonStyle.blurple)
        platformButton.callback = platformButton_callback
        quietButton = Button(label="Quiet Car", style = discord.ButtonStyle.blurple)
        quietButton.callback = quietButton_callback
        luggageButton = Button(label="Search the Luggage Area", style = discord.ButtonStyle.blurple)
        luggageButton.callback = luggageButton_callback
        seatButton = Button(label="Search Under your Seat", style = discord.ButtonStyle.blurple)
        seatButton.callback = seatButton_callback
        pocketButton = Button(label="Search the Seatback Pocket", style = discord.ButtonStyle.blurple)
        pocketButton.callback = pocketButton_callback
        firstclassButton = Button(label="First Class Car", style = discord.ButtonStyle.blurple)
        firstclassButton.callback = firstclassButton_callback
        coatButton = Button(label="Search the Coat Closet", style = discord.ButtonStyle.blurple)
        coatButton.callback = coatButton_callback
        reclinedseatButton = Button(label="Search Under your Reclined Seat", style = discord.ButtonStyle.blurple)
        reclinedseatButton.callback = reclinedseatButton_callback
        overheadButton = Button(label="Search the Overhead Bin", style = discord.ButtonStyle.blurple)
        overheadButton.callback = overheadButton_callback
        firstclassButton = Button(label="First Class Car", style = discord.ButtonStyle.blurple)
        firstclassButton.callback = firstclassButton_callback
        coatButton = Button(label="Search the Coat Closet", style = discord.ButtonStyle.blurple)
        coatButton.callback = coatButton_callback
        reclinedseatButton = Button(label="Search Under your Reclined Seat", style = discord.ButtonStyle.blurple)
        reclinedseatButton.callback = reclinedseatButton_callback
        overheadButton = Button(label="Search the Overhead Bin", style = discord.ButtonStyle.blurple)
        overheadButton.callback = overheadButton_callback
        galleyButton = Button(label="Galley Car", style = discord.ButtonStyle.blurple)
        galleyButton.callback = galleyButton_callback
        beverageButton = Button(label="Search the Beverage Cart", style = discord.ButtonStyle.blurple)
        beverageButton.callback = beverageButton_callback
        refrigeratorButton = Button(label="Search the Refrigerator", style = discord.ButtonStyle.blurple)
        refrigeratorButton.callback = refrigeratorButton_callback
        pantryButton = Button(label="Search the Pantry", style = discord.ButtonStyle.blurple)
        pantryButton.callback = pantryButton_callback
        engineButton = Button(label="Engine Car", style = discord.ButtonStyle.blurple)
        engineButton.callback = engineButton_callback
        cockpitButton = Button(label="Search the Cockpit Drawer", style = discord.ButtonStyle.blurple)
        cockpitButton.callback = cockpitButton_callback
        electricalButton = Button(label="Search the Electrical Box", style = discord.ButtonStyle.blurple)
        electricalButton.callback = electricalButton_callback
        controlpanelButton = Button(label="Search Under the Control Panel", style = discord.ButtonStyle.blurple)
        controlpanelButton.callback = controlpanelButton_callback
        bathroomButton = Button(label="Bathroom", style = discord.ButtonStyle.blurple)
        bathroomButton.callback = bathroomButton_callback
        mirrorButton = Button(label="Search Behind the Mirror", style = discord.ButtonStyle.blurple)
        mirrorButton.callback = mirrorButton_callback
        sinkButton = Button(label="Search Under the Sink", style = discord.ButtonStyle.blurple)
        sinkButton.callback = sinkButton_callback
        stallButton = Button(label="Search Inside the Stall", style = discord.ButtonStyle.blurple)
        stallButton.callback = stallButton_callback
        momongaButton = Button(label="Momomon Car", style = discord.ButtonStyle.blurple)
        momongaButton.callback = momongaButton_callback
        costumeButton = Button(label="Search the Momonga Costume", style = discord.ButtonStyle.blurple)
        costumeButton.callback = costumeButton_callback
        tvButton = Button(label="Search Behind the TV's", style = discord.ButtonStyle.blurple)
        tvButton.callback = tvButton_callback
        momongaoverheadButton = Button(label="Search the Overhead Bin", style = discord.ButtonStyle.blurple)
        momongaoverheadButton.callback = momongaoverheadButton_callback
        stationButton = Button(label="Remain at the Station", style = discord.ButtonStyle.blurple)
        stationButton.callback = stationButton_callback

        #Start the assignment UI for the user
        assignmentView.clear_items()
        assignmentView.add_item(ticketButton)
        assignmentView.add_item(concessionsButton)
        assignmentView.add_item(platformButton)
        assignmentView.add_item(trainButton)
        assignmentEmbed.title = "The Train Station"
        assignmentEmbed.description = "You have arrived at the train station. You may begin searching for the briefcase here at the station, or you can board the train. Just know that the train is about to depart, so once you board the train, you will no longer be able to go back to the station."
        await interaction.edit_original_message(embed = assignmentEmbed, view = assignmentView)

    
    beginButton = Button(label="Find the Briefcase", style = discord.ButtonStyle.blurple, custom_id="begin")
    beginButton.callback = beginButton_callback

    view.add_item(beginButton)
    
    bot.add_view(view, message_id = 1048701083393998888)
    embed = discord.Embed(color=0x000000)
    embed.title = "Assignment 2"
    embed.description = """Hello,
                            \nYour assignment is to find a briefcase for me. It is somewhere in the station or, more likely, on the train. You need to get in there, find the briefcase, and get out, as quickly as you can.
                            \nOh, and you won't be the only assassin searching for this briefcase. So don't let your guard down..."""
    await msg.edit(content = "", embed = embed, view = view)

@bot.slash_command(guild_ids=[869370430287384576], description = "Reset a user's cooldown.")
async def resetcooldown(ctx, user: Option(discord.Member, "Whose cooldown do you want to reset?")):
    guild = bot.get_guild(869370430287384576)
    #Make sure the command user has the authority to run the command
    staffRole = discord.utils.get(ctx.guild.roles, id = 911663990223024218)
    superModRole = discord.utils.get(ctx.guild.roles, id = 987041256096030790)
    #if the user isn't a supermod or a nifty's staff, don't let them run the command
    if staffRole not in ctx.author.roles and superModRole not in ctx.author.roles:
        response = random.randint(1,5)
        if response == 1:
            await ctx.respond("https://tenor.com/view/nice-try-saturday-night-live-good-try-nice-attempt-nice-shot-gif-25237563")
        if response == 2:
            await ctx.respond("https://tenor.com/view/nice-try-kid-frank-gallagher-william-macy-shameless-nice-one-gif-16165992")
        if response == 3:
            await ctx.respond("https://tenor.com/view/parks-and-rec-bobby-newport-nice-try-laughs-laughing-gif-21862350")
        if response == 4:
            await ctx.respond("https://tenor.com/view/nice-try-jack-donaghy-30rock-good-try-try-again-gif-21903632")
        if response == 5:
            await ctx.respond("https://tenor.com/view/nicetry-lawyer-harveyspecter-gif-4755413")
        return
    
    uid = user.id
    conn = psycopg2.connect(DATABASETOKEN, sslmode='require')
    cur = conn.cursor()
    command = "update btassignment2discordusers set cooldown_time = {0} where discord_user_id = {1}".format(int(time.time()), uid)
    cur.execute(command)
    cur.close()
    conn.commit()
    conn.close()
    await ctx.respond(user.mention + "'s cooldown has been reset!")
    

#Runs the bot using the TOKEN defined in the environmental variables.         
bot.run(TOKEN)
