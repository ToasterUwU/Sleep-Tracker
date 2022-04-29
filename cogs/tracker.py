import datetime
import nextcord
from nextcord.ext import commands

from internal_tools.discord import *
from internal_tools.configuration import CONFIG


class Tracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        return True

    async def get_or_fetch_log_channel(self) -> nextcord.TextChannel:
        channel = self.bot.get_channel(CONFIG["TRACKER"]["LOG_CHANNEL_ID"])
        if not channel:
            channel = await self.bot.fetch_channel(CONFIG["TRACKER"]["LOG_CHANNEL_ID"])

        return channel

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: nextcord.Member,
        before: nextcord.VoiceState,
        after: nextcord.VoiceState,
    ):
        if not before.channel and after.channel:
            channel = await self.get_or_fetch_log_channel()
            await channel.send(
                embed=fancy_embed(
                    f"{member.display_name} joined the call.",
                    fields={
                        "Current time:": f"<t:{int(datetime.datetime.now().timestamp())}:t>"
                    },
                    color=nextcord.Colour(0x7CFC00),
                )
            )

        if before.channel and not after.channel:
            channel = await self.get_or_fetch_log_channel()
            await channel.send(
                embed=fancy_embed(
                    f"{member.display_name} left the call.",
                    fields={
                        "Current time:": f"<t:{int(datetime.datetime.now().timestamp())}:t>"
                    },
                    color=nextcord.Colour(0xFF0000),
                )
            )


def setup(bot):
    bot.add_cog(Tracker(bot))
