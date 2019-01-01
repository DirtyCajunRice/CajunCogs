import discord
from time import sleep
from redbot.core import bank, commands, checks, Config


class MuteForMoney(commands.Cog):
    """Voice channel mutes for virtual currency"""
    def __init__(self):
        super().__init__()
        self.config = Config.get_conf(self, identifier=8008135)
        self.task = None
        default_guild = {
            'currency': 'USD',
            "moneyPerMin": 0,
            "eventChannel": None
        }
        default_member = {
            "balance": 0,
            "donated": 0,
            "on_hold": False
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def mfm(self, ctx: commands.Context):
        """Main Commands"""
        pass

    @mfm.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def start(self, ctx):
        """Start event"""
        if not self.task:
            self.task = ctx.bot.loop.create_task(self.live_event(ctx))
            await ctx.send("Event started!")
        else:
            await ctx.send('Event already running')

    @mfm.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def stop(self, ctx):
        """Stop event"""
        if self.task:
            self.task.cancel()
            self.task = None
            await ctx.send("Event Ended!")
        else:
            await ctx.send("Event not currently running")

    @mfm.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def reset(self, ctx):
        """Reset, deleting all users"""
        await self.config.clear_all_members(ctx.guild)
        await ctx.send("All users deleted")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def setserver(self, ctx: commands.Context):
        """set server-wide settings"""
        pass

    @setserver.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def currency(self, ctx, currency):
        """Set currency suffix"""
        await self.config.guild(ctx.guild).currency.set(currency)
        await ctx.send(f"Currency suffix has been changed to {currency}")

    @setserver.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def moneypermin(self, ctx, moneypermin: int):
        """Set amount of money worth 1 minute of mute"""
        await self.config.guild(ctx.guild).moneyPerMin.set(moneypermin)
        await ctx.send(f"Money per minute set to {moneypermin}/min")

    @setserver.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def channel(self, ctx, channelid: int):
        """Set event voice channel"""
        try:
            channel = ctx.message.guild.get_channel(channelid)
            if not isinstance(channel, discord.VoiceChannel):
                await ctx.send(f"{channel.name} is not a voice channel")
            else:
                await ctx.send(f"{channel.name} set as event channel")
                await self.config.guild(ctx.guild).eventChannel.set(channel.id)
        except Exception as e:
            print(e)
            await ctx.send(f"i cannot find a voice channel with id {channelid}")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def getserversettings(self, ctx):
        """Get current server-wide settings"""
        currency = await self.config.guild(ctx.guild).currency()
        money_per_minute = await self.config.guild(ctx.guild).moneyPerMin()
        event_channel_id = await self.config.guild(ctx.guild).eventChannel()
        await ctx.send(f"Currency: {currency}\nMoneyPerMinute: {money_per_minute}\nEventChannelID: {event_channel_id}")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def balance(self, ctx: commands.Context):
        """Balance manipulation"""
        pass

    @balance.command()
    @commands.guild_only()
    async def get(self, ctx, member: discord.Member):
        """Get balance for member"""
        balance = await self.config.member(member).balance()
        currency = await self.config.guild(ctx.guild).currency()
        money_per_min = await self.config.guild(ctx.guild).moneyPerMin()
        pre = f"{member.name} has a {balance} {currency} balance\n"
        minutes_left = abs(balance / money_per_min)
        if balance >= 0:
            statement = pre + f"They are safe for {minutes_left} minutes"
        else:
            statement = pre + f"You can continue enjoying their sweet silence for {minutes_left} minutes"
        await ctx.send(statement)

    @balance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def set(self, member: discord.Member, balance_amount: int):
        """Set balance for member"""
        await self.config.member(member).balance.set(balance_amount)

    @balance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def clear(self, member: discord.Member):
        """clear balance for member"""
        await self.config.member(member).balance.set(0)

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def donation(self, ctx, donor: discord.Member, amount: int, recipient: discord.Member):
        """Add donation from donor to recipient"""
        donated = await self.config.member(donor).donated()
        donated += amount
        await self.config.member(donor).donated.set(donated)

        balance = await self.config.member(recipient).balance()
        balance += amount
        await self.config.member(donor).balance.set(balance)

        await ctx.send(f"Balance changed for {recipient} by {amount}")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def multidonation(self, ctx, donor: discord.Member, amount: int, all_recipients):
        """Add donation from donor to multiple recipients evenly"""
        recipients = [member for member in ctx.message.mentions if str(member.id) != str(donor.id)]
        created_user = False
        divided_amount = amount / len(recipients)
        users = await self.config.guild(ctx.guild).users()
        for recipient in recipients:
            if not users.get(str(recipient.id)):
                created_user = True
                await self.create_user(ctx, recipient)
        if created_user:
            users = await self.config.guild(ctx.guild).users()
        users[str(donor.id)]["donated"] = users[str(donor.id)]["donated"] + amount
        for recipient in recipients:
            users[str(recipient.id)]["balance"] = users[str(recipient.id)]["balance"] + divided_amount
        await self.config.guild(ctx.guild).users.set(users)
        await ctx.send(f"Balance changed for all recipients by {divided_amount}")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def channeldonation(self, ctx, donor: discord.Member, amount: int):
        """Add donation from donor to entire channel evenly (except donor)"""
        channelid = await self.config.guild(ctx.guild).eventChannel()
        channel = ctx.message.guild.get_channel(channelid)
        recipients = [member for member in channel.members if str(member.id) != str(donor.id)]
        created_user = False
        divided_amount = amount / len(recipients)
        users = await self.config.guild(ctx.guild).users()
        for recipient in recipients:
            if not users.get(str(recipient.id)):
                created_user = True
                await self.create_user(ctx, recipient)
        if created_user:
            users = await self.config.guild(ctx.guild).users()
        users[str(donor.id)]["donated"] = users[str(donor.id)]["donated"] + amount
        for recipient in recipients:
            users[str(recipient.id)]["balance"] = users[str(recipient.id)]["balance"] + divided_amount
        await self.config.guild(ctx.guild).users.set(users)
        await ctx.send(f"Balance changed for all recipients by {divided_amount}")

    # Backend Functions
    async def create_user(self, ctx, member: discord.Member):
        user = {
            "balance": 0,
            "donated": 0,
            "on_hold": False
        }
        users = await self.config.guild(ctx.guild).users()
        users[str(member.id)] = user
        await self.config.guild(ctx.guild).users.set(users)

    async def live_event(self, ctx):
        while True:
            sleep(60)
            channelid = await self.config.guild(ctx.guild).eventChannel()
            channel = ctx.message.guild.get_channel(channelid)
            users = await self.config.guild(ctx.guild).users()
            money_per_min = await self.config.guild(ctx.guild).moneyPerMin()
            for participant in channel.members:
                user = users[str(participant.id)]
                overwrites = channel.overwrites_for(participant)
                if not user["on_hold"]:
                    if -money_per_min < user["balance"] < 0:
                        user["balance"] = 0
                    elif user["balance"] < -money_per_min:
                        user["balance"] -= -money_per_min
                    if not overwrites.speak and user['balance'] >= 0:
                        overwrites.speak = True
                    elif overwrites.speak and user['balance'] < 0:
                        overwrites.speak = False
                    users[str(participant.id)] = user
            await self.config.guild(ctx.guild).users.set(users)

