import datetime
import math
import nextcord
from nextcord.ext import commands

from internal_tools.discord import *
from internal_tools.configuration import CONFIG, JsonDataSaver


class Tracker(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tracking_data = JsonDataSaver(
            "tracking_data",
            default={"SLEEPING_TOGETHER_FOR_MINUTES": 0},
        )

        self.did_setup = False

        self.aki_sleeps = False
        self.slippy_sleeps = False
        self.sleeping_together_since = None

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
        if not self.did_setup:
            if after.channel:
                members = after.channel.members
            else:
                members = before.channel.members

            member_ids = [m.id for m in members]
            self.aki_sleeps = CONFIG["TRACKER"]["AKI_ID"] in member_ids
            self.slippy_sleeps = CONFIG["TRACKER"]["SLIPPY_ID"] in member_ids

            if self.aki_sleeps and self.slippy_sleeps:
                self.sleeping_together_since = datetime.datetime.now()

            self.did_setup = True

        if not before.channel and after.channel:
            if member.id == CONFIG["TRACKER"]["AKI_ID"]:
                self.aki_sleeps = True
            elif member.id == CONFIG["TRACKER"]["SLIPPY_ID"]:
                self.slippy_sleeps = True

            if self.aki_sleeps and self.slippy_sleeps:
                self.sleeping_together_since = datetime.datetime.now()

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
            if self.aki_sleeps and self.slippy_sleeps:
                if member.id == CONFIG["TRACKER"]["AKI_ID"]:
                    self.aki_sleeps = False
                elif member.id == CONFIG["TRACKER"]["SLIPPY_ID"]:
                    self.slippy_sleeps = False

                if (
                    not (self.aki_sleeps and self.slippy_sleeps)
                    and self.sleeping_together_since
                ):
                    minutes = int(
                        (
                            datetime.datetime.now() - self.sleeping_together_since
                        ).total_seconds()
                        / 60
                    )
                    self.tracking_data["SLEEPING_TOGETHER_FOR_MINUTES"] += minutes
                    self.tracking_data.save()

                    self.sleeping_together_since = None

            total_minutes = self.tracking_data["SLEEPING_TOGETHER_FOR_MINUTES"]

            days = math.floor(total_minutes / (24*60))
            leftover = total_minutes % (24*60)

            hours = math.floor(leftover / 60)
            minutes = total_minutes - (days * (24*60)) - (hours * 60)

            channel = await self.get_or_fetch_log_channel()
            await channel.send(
                embed=fancy_embed(
                    f"{member.display_name} left the call.",
                    fields={
                        "Current time:": f"<t:{int(datetime.datetime.now().timestamp())}:t>",
                        "Total time slept together:": f"Days: {days}, Hours: {hours}, Minutes: {minutes}",
                    },
                    color=nextcord.Colour(0xFF0000),
                )
            )


def setup(bot):
    bot.add_cog(Tracker(bot))
