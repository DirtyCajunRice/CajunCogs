from soundboard.Soundboard import Soundboard

from pathlib import Path
from aiohttp import ClientSession
import shutil
import logging

from .manager import start_lavalink_server
from redbot.core import commands
from redbot.core.data_manager import cog_data_path
import redbot.core

log = logging.getLogger("red.soundboard")

LAVALINK_DOWNLOAD_URL = f"https://github.com/Cog-Creators/Red-DiscordBot/releases/download/{redbot.core.__version__}/Lavalink.jar"

LAVALINK_DOWNLOAD_DIR = cog_data_path(raw_name="Soundboard")
LAVALINK_JAR_FILE = LAVALINK_DOWNLOAD_DIR / "Lavalink.jar"

APP_YML_FILE = LAVALINK_DOWNLOAD_DIR / "application.yml"
BUNDLED_APP_YML_FILE = Path(__file__).parent / "data/application.yml"


async def download_lavalink(session):
    with LAVALINK_JAR_FILE.open(mode="wb") as f:
        async with session.get(LAVALINK_DOWNLOAD_URL) as resp:
            while True:
                chunk = await resp.content.read(512)
                if not chunk:
                    break
                f.write(chunk)


async def maybe_download_lavalink(loop, cog):
    jar_exists = LAVALINK_JAR_FILE.exists()
    current_build = redbot.core.VersionInfo.from_json(await cog.config.current_version())

    if not jar_exists or current_build < redbot.core.version_info:
        log.info("Downloading Lavalink.jar")
        LAVALINK_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        async with ClientSession(loop=loop) as session:
            await download_lavalink(session)
        await cog.config.current_version.set(redbot.core.version_info.to_json())

    shutil.copyfile(str(BUNDLED_APP_YML_FILE), str(APP_YML_FILE))


async def setup(bot: commands.Bot):
    cog = Soundboard(bot)

    await maybe_download_lavalink(bot.loop, cog)
    await start_lavalink_server(bot.loop)

    await cog.initialize()

    bot.add_cog(Soundboard(bot))
