import discord

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
            'wiki_type': 'github'
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

    @commands.guild_only()
    @checks.admin_or_permissions(manage_roles=True)
    @wikiset.command()
    async def type(self, ctx, wiki_type):
        """Set wiki type. (github or bookstack)"""
        if wiki_type.lower() in ('github', 'bookstack'):
            await self.config.guild(ctx.guild).wiki_type.set(wiki_type.lower())
            await ctx.send(f"Wiki type set to {wiki_type}")
        else:
            await ctx.send(f"{wiki_type} is not a valid wiki type. (Bookstack, Github)")

    @commands.command(aliases=["w"])
    @checks.admin_or_permissions(manage_roles=True)
    @commands.guild_only()
    async def wiki(self, ctx, page, *, query=None):
        """Query the wiki. Commands build off of each other. !wiki <chapter> [<page> <bookmark> <@username>]"""
        wiki_base_url = await self.config.guild(ctx.guild).wiki_base_url()
        wiki_type = await self.config.guild(ctx.guild).wiki_type()

        async with self.config.guild(ctx.guild).wiki_pages() as wiki_pages:
            title = None
            content = None
            description = None
            if not await self.configuration_check(ctx, wiki_base_url, wiki_type, wiki_pages):
                return
            if wiki_type == "github":
                for k, d in wiki_pages.items():
                    if page in k.lower():
                        title = f"Have you read the {k} wiki page?"
                        url = d['url']
                        foot = f'Called by "{ctx.author} | Page Query: "{page}"'
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
                                qw = " ".join(query_words)
                                foot = foot + f' | Search Query: "{qw}"'
                                description = '\n'.join([f"{q[0]}. [{q[1][0]}]({q[1][1]})"
                                                         for q in enumerate(responses, 1)])

                        embed = discord.Embed(title=title, colour=ctx.author.colour, description=description, url=url)
                        embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
                        await ctx.send(embed=embed, content=content)
                        return

                if not title:
                    await ctx.send(f'No wiki page matches "{page}"')
                    return

            if wiki_type == "bookstack":
                embed = None
                for chapter, data in wiki_pages.items():
                    if 'faq' in page.lower():
                        page = 'Questions'
                    if page.lower() in chapter.lower():
                        title = f"__**Have you read the {chapter} chapter in the wiki?**__"
                        url = data['url']
                        foot = f'Called by "{ctx.author} | Queries -Chapter: "{"faq" if "Quest" in page else page}"'
                        embed = discord.Embed(title=title, colour=ctx.author.colour, url=url)
                        if query:
                            member_strings = [word for word in query.split(" ") if '@' in word]
                            member_ids = [int(''.join([n for n in member if n.isdigit()])) for member in
                                          member_strings]
                            members = [ctx.bot.get_user(member) for member in member_ids]
                            if members:
                                content = ' '.join([member.mention for member in members])
                            query_words = [word for word in query.split(" ") if '@' not in word]
                            if not query_words:
                                break
                            for p, d in data['pages'].items():
                                if query_words[0].lower() in p.lower():
                                    title = f"__**Have you read the {p} wiki page in the {chapter} chapter?**__"
                                    url = d['url']
                                    foot = f'{foot} -Page: "{query_words[0]}"'
                                    embed = discord.Embed(title=title, colour=ctx.author.colour, url=url)
                                    if len(query_words) == 1:
                                        break
                                    else:
                                        responses = list(
                                            set(
                                                [q[0] for word in query_words[1:] for q in process.extract(
                                                    word, list(d['bookmarks'].items())
                                                ) if q[1] >= 60]
                                            )
                                        )
                                        if not responses:
                                            query_words_text = ' '.join(query_words[1:])
                                            await ctx.send(f'No matches for bookmark query "{query_words_text}"')
                                            break
                                        else:
                                            qw = " ".join(query_words[1:])
                                            foot = f'{foot} -Bookmark: "{qw}"'
                                            description = '\n'.join([f"{q[0]}. [{q[1][0]}]({d['url']}#{q[1][1]})"
                                                                    for q in enumerate(responses, 1)])
                                            embed = discord.Embed(title=title, colour=ctx.author.colour,
                                                                  description=description, url=url)
                if embed:
                    embed.set_footer(text=foot, icon_url=ctx.author.avatar_url)
                    await ctx.send(embed=embed, content=content)
                else:
                    await ctx.send(f'No wiki chapters match "{page}"')

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
        wiki_type = await self.config.guild(ctx.guild).wiki_type()
        if wiki_type == "github":
            g = await self.get(wiki_base_url + '/Home' + '.md')
            page = BeautifulSoup(markdown(g), "html.parser")
            links = page.find_all('a', href=True)
            await self.config.guild(ctx.guild).wiki_pages.set({})
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
        elif wiki_type == "bookstack":
            g = await self.get(wiki_base_url)
            page = BeautifulSoup(g, "html.parser")
            chapters = page.find("div", class_="book-content").find_all("a", class_="chapter")
            await self.config.guild(ctx.guild).wiki_pages.set({})
            async with self.config.guild(ctx.guild).wiki_pages() as wiki_pages:
                for chapter in chapters:
                    chapter_title = chapter.find('h4').text
                    chapter_url = chapter.get('href')
                    wiki_pages[chapter_title] = {
                        "url": chapter_url,
                        "pages": {}
                    }
                    g = await self.get(chapter_url)
                    page = BeautifulSoup(g, "html.parser")
                    for p in page.find("div", class_="chapter-content").find_all("a", class_="page"):
                        page_title = p.find('h4').text
                        page_url = p.get('href')
                        wiki_pages[chapter_title]['pages'][page_title] = {
                            "url": page_url,
                            "bookmarks": {}
                        }
                        g = await self.get(page_url)
                        page = BeautifulSoup(g, "html.parser")
                        for bkmrk in page.find_all("h4", id=lambda value: value and value.startswith("bkmrk")):
                            wiki_pages[chapter_title]['pages'][page_title]["bookmarks"][bkmrk.text] = bkmrk.get('id')

    @staticmethod
    async def configuration_check(ctx, wiki_base_url, wiki_type, wiki_pages):
        if not wiki_base_url:
            await ctx.send("baseurl not set")
            return

        if not wiki_type:
            await ctx.send("wiki type not set")
            return

        if not wiki_pages:
            await ctx.send("No wiki pages")
            return

        return True

    @staticmethod
    async def get(url):
        async with ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
