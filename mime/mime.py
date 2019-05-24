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
                                  "[Log Bin](https://bin.cajun.pro) and post the RAW link here, " \
                                  "**do not upload** the file as an attachment."
                    foot = f"Called by {message.author}"
                    embed = discord.Embed(title=title, colour=message.author.colour, description=description)
                    embed.set_footer(text=foot, icon_url=message.author.avatar_url)
                    await message.channel.send(content=msg_content, embed=embed)

    @staticmethod
    async def bin_link_sniffer(message):
        bin_link = "https://bin.cajun.pro/"
        raw = f"{bin_link}raw/"
        image = f"{bin_link}images/"
        content = message.content
        if bin_link in content and not any([raw in content or image in content]):
            fixed_links = []
            links = [link for link in content.split() if bin_link in link]
            for link in links:
                if link.count('.') > 2:
                    fixed_links.append('.'.join(link.split('.')[:-1]).replace('.pro/', '.pro/raw/'))
            msg_content = f"Here is the RAW for {message.author.mention}'s paste"
            description = '\n'.join(link for link in fixed_links)
            foot = f"Automatically updated by your friendly neighborhood bot"
            embed = discord.Embed(colour=message.author.colour, description=description)
            embed.set_footer(text=foot, icon_url=message.author.avatar_url)
            await message.channel.send(content=msg_content, embed=embed)