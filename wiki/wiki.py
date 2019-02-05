import discord

from typing import Optional
from bs4 import BeautifulSoup
from markdown import markdown
from fuzzywuzzy import process
from aiohttp import ClientSession
from redbot.core import commands, checks, Config


class Wiki(commands.Cog):

    def __init__(self):
        super().__init__()
        self.config = Config.get_conf(self, identifier=1991991991)
        default_guild = {
            'wiki_base_url': "",
            'wiki_pages': {},
        }
        self.config.register_guild(**default_guild)

    @commands.group()
    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    async def wikiset(self, ctx: commands.Context):
        """Wiki page and section referencer"""
        pass

    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @wikiset.command()
    async def baseurl(self, ctx, baseurl):
        """Set wiki Base Url"""
        await self.config.guild(ctx.guild).wiki_base_url.set(baseurl)
        await ctx.send(f"Baseurl set to {baseurl}")

    @commands.command()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.guild_only()
    async def wikipages(self, ctx):
        wiki_base_url = await self.config.guild(ctx.guild).wiki_base_url()
        if not wiki_base_url:
            await ctx.send("baseurl not set")
            return

        async with self.config.guild(ctx.guild).wiki_pages() as wiki_pages:
            if not wiki_pages:
                await ctx.send("No wiki pages")
                return

            description = '\n'.join([f"[{k}]({d['url']})" for k, d in wiki_pages.items()])

        title = f"{wiki_base_url.split('com/')[1].split('/wiki')[0]} wiki pages"
        foot = f'Called by "{ctx.author}"'
        embed = discord.Embed(title=title, url=wiki_base_url, colour=ctx.author.colour, description=description)
        embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)

    @commands.command()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.guild_only()
    async def wikipage(self, ctx, page, *, query=None):
        wiki_base_url = await self.config.guild(ctx.guild).wiki_base_url()
        if not wiki_base_url:
            await ctx.send("baseurl not set")
            return

        async with self.config.guild(ctx.guild).wiki_pages() as wiki_pages:
            title = None
            content = None
            description = None
            if not wiki_pages:
                await ctx.send("No wiki pages")
                return
            for k, d in wiki_pages.items():
                if page in k.lower():
                    title = f"Have you read the {k} wiki page?"
                    url = d['url']
                    foot = f'Called by "{ctx.author}"'
                    if query:
                        member_strings = [word for word in query.split(" ") if '@' in word]
                        member_ids = [int(''.join([n for n in member if n.isdigit()])) for member in member_strings]
                        members = [ctx.bot.get_user(member) for member in member_ids]
                        if members:
                            content = ' '.join([member.mention for member in members])
                        query_words = [word for word in query.split(" ") if '@' not in word]
                        responses = list(
                            set(
                                [q[0] for word in query_words for q in process.extract(
                                    word, d['links']
                                ) if q[1] >= 60]
                            )
                        )
                        if query_words and not responses:
                            await ctx.send(f'No links found with "{query}"')
                        elif responses:
                            foot = f'Called by "{ctx.author}" | Query: "{" ".join(query_words)}"'
                            description = '\n'.join([f"{q[0]}. [{q[1][0]}]({q[1][1]})"
                                                     for q in enumerate(responses, 1)])

                    embed = discord.Embed(title=title, colour=ctx.author.colour, description=description, url=url)
                    embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed, content=content)
                    return

            if not title:
                await ctx.send(f'No wiki page matches "{page}"')
                return

    @commands.command()
    @checks.admin_or_permissions(manage_roles=True)
    @commands.guild_only()
    async def wikiupdate(self, ctx):
        """Update the local list of FAQ questions"""
        await self.build_list(ctx)
        await ctx.send("Wiki pages updated")

    # Backend functions
    async def build_list(self, ctx):
        """Build and update list of pages"""
        wiki_base_url = await self.config.guild(ctx.guild).wiki_base_url()
        g = await self.get(wiki_base_url + '/Home' + '.md')
        page = BeautifulSoup(markdown(g), "html.parser")
        links = page.find_all('a', href=True)
        async with self.config.guild(ctx.guild).wiki_pages() as wiki_pages:
            for link in links:
                wiki_pages[link.text] = {'url': f"{wiki_base_url}/{link['href']}"}
                g = await self.get(f'{wiki_pages[link.text]["url"]}.md')
                page = BeautifulSoup(markdown(g), "html.parser")
                plinks = page.find_all('a', href=True)
                wiki_pages[link.text]['links'] = [
                    (
                        plink.text,
                        f'{wiki_pages[link.text]["url"] if plink["href"].startswith("#") else ""}{plink["href"]}'
                    )
                    for plink in plinks
                ]

    @staticmethod
    async def get(url):
        async with ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
