from mime.mime import MIME


def setup(bot):
    cog = MIME()
    bot.add_listener(cog.file_sniffer, "on_message")
    bot.add_listener(cog.bin_link_sniffer, "on_message")
    bot.add_cog(cog)
