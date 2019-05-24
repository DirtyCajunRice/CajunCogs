from automodify.automodify import AutoModify


def setup(bot):
    cog = AutoModify()
    bot.add_listener(cog.file_sniffer, "on_message")
    bot.add_listener(cog.bin_link_sniffer, "on_message")
    bot.add_cog(cog)
