import discord
from redbot.core import commands, checks, Config


class MuteForMoney(commands.Cog):
    """Voice channel mutes for virtual currency"""
    def __init__(self):
        super().__init__()
        self.config = Config.get_conf(self, identifier=8008135)
        self.task = None
        default_guild = {
            "users": {},
            "moneyPerMin": 0,
            "currency": "USD"
        }
        self.config.register_guild(**default_guild)

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
            self.task = ctx.bot.loop.create_task('placeholder')
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
        await self.config.guild(ctx.guild).users.set({})
        await ctx.send("All users deleted")

    @mfm.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def set(self, ctx: commands.Context):
        """set server-wide settings"""
        pass

    @set.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def currency(self, ctx, currency):
        """Set currency suffix"""
        await self.config.guild(ctx.guild).currency.set(currency)
        await ctx.send(f"Currency suffix has been changed to {currency}")

    @set.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def moneypermin(self, ctx, moneypermin: int):
        """Set set amount of money worth 1 minute of mute"""
        await self.config.guild(ctx.guild).moneyPerMin.set(moneypermin)
        await ctx.send(f"Money per minute set to {moneypermin}/min")

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
        users = await self.config.guild(ctx.guild).users()
        if users.get(str(member.id)):
            print('yes user')
            currency = await self.config.guild(ctx.guild).currency()
            money_per_min = await self.config.guild(ctx.guild).moneyPerMin()
            balance = users[str(member.id)]['balance']
            pre = f"{member.name} has a {balance} {currency} balance\n"
            minutes_left = abs(balance / money_per_min)
            if balance >= 0:
                statement = pre + f"They are safe for {minutes_left} minutes"
            else:
                statement = pre + f"You can continue enjoying their sweet silence for {minutes_left} minutes"
            await self.config.guild(ctx.guild).users.set(users)
            await ctx.send(statement)
        else:
            await ctx.send(f"{member.name} has not participated in the event")

    @balance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def set(self, ctx, member: discord.Member, balance_amount: int):
        """Set balance for member"""
        users = await self.config.guild(ctx.guild).users()
        if users.get(str(member.id)):
            users[str(member.id)]["balance"] = balance_amount
            await self.config.guild(ctx.guild).users.set(users)
        else:
            await ctx.send(f"{member.name} has not participated in the event")

    @balance.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def clear(self, ctx, member: discord.Member):
        """clear balance for member"""
        users = await self.config.guild(ctx.guild).users()
        if users.get(str(member.id)):
            users[str(member.id)]["balance"] = 0
            await self.config.guild(ctx.guild).users.set(users)
        else:
            await ctx.send(f"{member.name} has not participated in the event")

    @commands.command()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def donation(self, ctx, donor: discord.Member, amount: int, recipient: discord.Member):
        """Add donation from donator to donatee"""
        created_user = False
        users = await self.config.guild(ctx.guild).users()
        print(users)
        for user in [donor, recipient]:
            if not users.get(str(user.id)):
                created_user = True
                await self.create_user(ctx, user)
        if created_user:
            users = await self.config.guild(ctx.guild).users()
        users[str(donor.id)]["donated"] = users[str(donor.id)]["donated"] + amount
        users[str(recipient.id)]["balance"] = users[str(recipient.id)]["balance"] + amount
        await self.config.guild(ctx.guild).users.set(users)
        await ctx.send(f"Balance changed for {recipient} by {amount}")

    # Backend Functions
    async def create_user(self, ctx, member: discord.Member):
        user = {
            "balance": 0,
            "donated": 0
        }
        users = await self.config.guild(ctx.guild).users()
        users[str(member.id)] = user
        await self.config.guild(ctx.guild).users.set(users)
