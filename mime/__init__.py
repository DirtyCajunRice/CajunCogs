from mime.mime import MIME


def setup(bot):
    n = MIME()
    bot.add_listener(n.file_sniffer, "on_message")
    bot.add_cog(n)
