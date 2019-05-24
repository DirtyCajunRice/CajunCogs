from redbot.core import commands
import discord


class Responses(commands.Cog):
    """Issues common responses, beautifully."""

    @commands.command()
    async def logs(self, ctx, member: discord.Member = None):
        """Replies with a summary on how to get your logs"""
        if member is not None:
            msg_content = f"{member.mention} Please post a link to your **complete** Varken logs to our LogBin."
        else:
            msg_content = "Please post a link to your **complete** Varken logs to our LogBin."
        title = "How to Find Your Logs"
        description = "Logs can be found in your data folder or via the console. The default log location is" \
                      " typically `/opt/Varken/data/logs/varken.log`. Paste the logs on " \
                      "[Log Bin](https://bin.cajun.pro) and post the RAW link here, " \
                      "**do not upload** the file as an attachment."
        foot = f"Called by {ctx.author}"
        embed = discord.Embed(title=title, colour=ctx.author.colour, description=description)
        embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
        await ctx.send(content= msg_content, embed= embed)

    @commands.command()
    async def xyz(self, ctx):
        """Answers the XY Problem"""
        title = "The XY Problem"
        field = "What is it?"
        description = "The XY problem is asking about your attempted solution rather than your actual problem. " \
                      "This leads to enormous amounts of wasted time and energy, both on the part of people " \
                      "asking for help, and on the part of those providing help.\n" \
                      "\n• User wants to do X." \
                      "\n• User doesn't know how to do X, but thinks they can fumble " \
                      "their way to a solution if they can just manage to do Y." \
                      "\n• User doesn't know how to do Y either." \
                      "\n• User asks for help with Y." \
                      "\n• Others try to help user with Y, but are confused " \
                      "because Y seems like a strange problem to want to solve." \
                      "\n\nAfter much interaction and wasted time, it finally becomes clear that the " \
                      "user really wants help with X, and that Y wasn't even a suitable solution for X." \
                      "The problem occurs when people get stuck on what they believe is the solution " \
                      "and are unable step back and explain the issue in full."
        foot = f"Called by {ctx.author}"
        url = "http://xyproblem.info/"
        embed = discord.Embed(title=title, colour=ctx.author.colour, url=url)
        embed.add_field(name=field, value=description)
        embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
        await ctx.send(embed= embed)
