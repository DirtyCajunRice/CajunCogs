from redbot.core import commands
import discord
import re


class MIME(commands.Cog):
    """Deletes messages with attachments that are not images."""

    @staticmethod
    async def file_sniffer(message):
        allowed_types = r"([^\s]+(\.(?i)(jpg|png|gif|bmp))$)"
        if message.attachments:
            for attachment in message.attachments:
                if re.match(allowed_types, attachment.filename) is None:
                    await message.delete()
                    msg_content = f"{message.author.mention} Please do not post attachments."
                    title = "How to Find Your Logs"
                    description = "Logs can be found in your data folder or via the console. The default log " \
                                  "location is" \
                                  " typically `/opt/Varken/data/logs/varken.log`. Paste the logs on " \
                                  "[Log Bin](https://bin.cajun.pro) and post the link here, " \
                                  "**do not upload** the file as an attachment."
                    foot = f"Called by {message.author}"
                    embed = discord.Embed(title=title, colour=message.author.colour, description=description)
                    embed.set_footer(text=foot, icon_url=message.author.avatar_url)
                    await message.channel.send(content=msg_content, embed=embed)
