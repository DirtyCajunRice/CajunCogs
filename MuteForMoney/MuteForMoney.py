import discord
import asyncio
from datetime import timedelta
from redbot.core import bank, commands, checks, Config


class MuteForMoney(commands.Cog):
    """Voice channel mutes for virtual currency"""
    def __init__(self):
        super().__init__()
        self.config = Config.get_conf(self, identifier=8008135)
        self.tasks = {}
        default_guild = {
            "moneyPerMin": 0,
            "eventChannel": None
        }
        default_member = {
            "insurance": 0,
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
        if not self.tasks.get(ctx.guild.id):
            self.tasks[ctx.guild.id] = ctx.bot.loop.create_task(self.live_event(ctx))
            await ctx.send("Event started!")
        else:
            await ctx.send('Event already running')

    @mfm.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def stop(self, ctx):
        """Stop event"""
        if self.tasks.get(ctx.guild.id):
            self.tasks[ctx.guild.id].cancel()
            del self.tasks[ctx.guild.id]
            await ctx.send("Event Ended!")
        else:
            await ctx.send("Event not currently running")

    @mfm.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def reset(self, ctx):
        """Reset, deleting all users"""
        await self.config.clear_all_members(ctx.guild)
        await bank.wipe_bank(ctx.guild)
        await ctx.send("All users/bank deleted")

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
        default_balance = await bank.get_default_balance(ctx.guild)
        is_global = await bank.is_global()
        if default_balance < 0:
            await bank.set_default_balance(0, ctx.guild)
        if is_global:
            await bank.set_global(False)
        await bank.set_currency_name(currency, ctx.guild)
        await ctx.send(f"Currency name has been changed to {currency}")

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
    async def channelid(self, ctx, channelid: int):
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
        currency = await bank.get_currency_name(ctx.guild)
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
        currency = await bank.get_currency_name(ctx.guild)
        balance = await bank.get_balance(member)
        insurance = await self.config.member(member).insurance()
        donated = await self.config.member(member).donated()
        money_per_min = await self.config.guild(ctx.guild).moneyPerMin()
        minutes_left = insurance / money_per_min if insurance else balance / money_per_min
        formatted_left = await self.time_from_minutes(minutes_left)
        formatted_sanity = formatted_left if formatted_left else "None! Get'em While they are vulnerable!"

        title = "User Balances"
        minutes_title = "Insured" if insurance > 0 else "Silenced"
        foot = f'Called by {ctx.author}'
        embed = discord.Embed(title=title, colour=ctx.author.colour)
        embed.set_author(name=member.name, icon_url=member.avatar_url)
        embed.set_thumbnail(url=member.avatar_url)
        embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Debt:", value=f"{balance} {currency}", inline=True)
        embed.add_field(name="Insurance:", value=f"{insurance} {currency}", inline=True)
        embed.add_field(name="Donated:", value=f"{donated} {currency}", inline=True)
        embed.add_field(name=f"Minutes Left {minutes_title}", value=f"{formatted_sanity}", inline=True)
        await ctx.send(embed=embed)

    @balance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def clear(self, ctx, member: discord.Member):
        """clear balance for member"""
        await bank.set_balance(member, 0)
        await ctx.send(f"Set {member.name}'s balance to 0")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def donation(self, ctx, donor: discord.Member, amount: int, recipient: discord.Member):
        """Add donation from donor to recipient"""
        donated = await self.config.member(donor).donated()
        donated += amount
        await self.config.member(donor).donated.set(donated)

        balance = await bank.get_balance(recipient)
        balance += amount
        await bank.set_balance(recipient, balance)
        await ctx.send(f"Balance changed for {recipient} by {amount}")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def insurance(self, ctx: commands.Context):
        """Self balance removal/Insurance addition"""
        pass

    @insurance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def self(self, ctx, member: discord.Member, amount: int):
        """Set balance for member"""
        balance = await bank.get_balance(member)
        insurance = await self.config.member(member).insurance()

        donated = await self.config.member(member).donated()
        donated += amount
        await self.config.member(member).donated.set(donated)

        if amount < balance > 0:
            await bank.withdraw_credits(member, amount)
        elif balance > 0:
            amount -= balance
            await bank.set_balance(member, 0)
            await self.config.member(member).insurance.set(amount)
        else:
            insurance += amount
            await self.config.member(member).insurance.set(insurance)

        await ctx.send(f"done.")

    @insurance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def donation(self, ctx, donor: discord.Member, amount: int, recipient: discord.Member):
        """Donation balance removal/Insurance addition"""
        balance = await bank.get_balance(recipient)
        insurance = await self.config.member(recipient).insurance()

        donated = await self.config.member(donor).donated()
        donated += amount
        await self.config.member(donor).donated.set(donated)

        if amount < balance > 0:
            await bank.withdraw_credits(recipient, amount)
        elif balance > 0:
            amount -= balance
            await bank.set_balance(recipient, 0)
            await self.config.member(recipient).insurance.set(amount)
        else:
            insurance += amount
            await self.config.member(recipient).insurance.set(insurance)

        await ctx.send(f"done.")

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def donation(self, ctx: commands.Context):
        """Donation options"""
        pass

    @donation.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def single(self, ctx, donor: discord.Member, amount: int, recipient: discord.Member):
        """Donation balance addition/Insurance removal"""
        insurance = await self.config.member(recipient).insurance()

        donated = await self.config.member(donor).donated()
        donated += amount
        await self.config.member(donor).donated.set(donated)

        if amount < insurance > 0:
            insurance -= amount
            await self.config.member(recipient).insurance.set(insurance)
        elif insurance > 0:
            amount -= insurance
            await self.config.member(recipient).insurance.set(0)

        if amount:
            await bank.deposit_credits(recipient, amount)

        await ctx.send(f"done.")

    @donation.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def multi(self, ctx, donor: discord.Member, amount: int, all_recipients):
        """Add donation from donor to multiple recipients evenly"""
        recipients = [member for member in ctx.message.mentions if str(member.id) != str(donor.id)]
        divided_amount = int(amount / len(recipients))

        donated = await self.config.member(donor).donated()
        donated += amount
        await self.config.member(donor).donated.set(donated)

        for recipient in recipients:
            insurance = await self.config.member(recipient).insurance()
            if amount < insurance > 0:
                insurance -= amount
                await self.config.member(recipient).insurance.set(insurance)
            elif insurance > 0:
                amount -= insurance
                await self.config.member(recipient).insurance.set(0)

            if amount:
                await bank.deposit_credits(recipient, divided_amount)

        await ctx.send(f"Balance changed for all recipients by {divided_amount}")

    @donation.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def channel(self, ctx, donor: discord.Member, amount: int):
        """Add donation from donor to entire channel evenly (except donor)"""
        channelid = await self.config.guild(ctx.guild).eventChannel()
        channel = ctx.message.guild.get_channel(channelid)
        recipients = [member for member in channel.members if str(member.id) != str(donor.id)]
        divided_amount = int(amount / len(recipients))

        donated = await self.config.member(donor).donated()
        donated += amount
        await self.config.member(donor).donated.set(donated)

        for recipient in recipients:
            insurance = await self.config.member(recipient).insurance()
            if amount < insurance > 0:
                insurance -= amount
                await self.config.member(recipient).insurance.set(insurance)
            elif insurance > 0:
                amount -= insurance
                await self.config.member(recipient).insurance.set(0)

            if amount:
                await bank.deposit_credits(recipient, divided_amount)

        await ctx.send(f"Balance changed for all recipients by {divided_amount}")

    # Backend Functions
    async def live_event(self, ctx):
        while True:
            await asyncio.sleep(15)
            channelid = await self.config.guild(ctx.guild).eventChannel()
            channel = ctx.message.guild.get_channel(channelid)
            money_per = int(await self.config.guild(ctx.guild).moneyPerMin() / 4)
            for member in channel.members:
                on_hold = await self.config.member(member).on_hold()
                balance = await bank.get_balance(member)
                overwrites = channel.overwrites_for(member)
                if not on_hold:
                    if money_per >= balance > 0:
                        balance = 0
                    elif balance > money_per:
                        balance -= money_per

                    if overwrites.speak is not None and overwrites.speak is False and balance == 0:
                        overwrites.speak = True
                    elif (overwrites.speak is None or overwrites.speak is True) and balance > 0:
                        overwrites.speak = False

                    if member.voice.mute is not None and member.voice.mute is True and balance == 0:
                        await member.edit(mute=False)
                    elif (member.voice.mute is None or member.voice.mute is False) and balance > 0:
                        await member.edit(mute=True)

                    await bank.set_balance(member, balance)

                    try:
                        await channel.set_permissions(member, overwrite=overwrites)
                    except Exception as e:
                        print(e)

    @staticmethod
    async def time_from_minutes(mins):
        secs = timedelta(minutes=mins).seconds
        days = secs // 86400
        hours = (secs - days * 86400) // 3600
        minutes = (secs - days * 86400 - hours * 3600) // 60
        seconds = secs - days * 86400 - hours * 3600 - minutes * 60
        result = (f"{days} Day{'s ' if days != 1 else ' '}" if days else "") + \
                 (f"{hours} Hour{'s ' if hours != 1 else ' '}" if hours else "") + \
                 (f"{minutes} Minute{'s ' if minutes != 1 else ' '}" if minutes else "") + \
                 (f"{seconds} Second{'s' if seconds != 1 else ''}" if seconds else "")
        return result
