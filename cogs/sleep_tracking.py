import itertools
import time
from typing import Dict, List, Tuple

import nextcord
from nextcord.ext import application_checks, commands

from internal_tools.configuration import JsonDictSaver
from internal_tools.discord import *


class SleepTracking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.internal_state_db: Dict[int, Dict[int, float]] = {}

        self.sleep_tracker_files: Dict[int, JsonDictSaver] = {}

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        Everyone can use this.
        """
        return True

    @commands.Cog.listener()
    async def on_ready(self):
        async for g in self.bot.fetch_guilds(limit=None):
            self.sleep_tracker_files[g.id] = JsonDictSaver(
                str(g.id), default={"SLEEP_CHANNEL_IDS": [], "SLEEP_DATA": {}}
            )

    @commands.Cog.listener()
    async def on_guild_join(self, guild: nextcord.Guild):
        if guild.id not in self.sleep_tracker_files:
            self.sleep_tracker_files[guild.id] = JsonDictSaver(
                str(guild.id), default={"SLEEP_CHANNEL_IDS": [], "SLEEP_DATA": {}}
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: nextcord.Guild):
        if guild.id in self.internal_state_db:
            del self.internal_state_db[guild.id]

        if guild.id in self.sleep_tracker_files:
            del self.sleep_tracker_files[guild.id]

    @nextcord.slash_command(
        "sleep-channel",
        default_member_permissions=nextcord.Permissions(manage_channels=True),
        dm_permission=False,
    )
    async def top_command_sleep_channel(self, interaction: nextcord.Interaction):
        pass

    def sleep_channel_list_embed(self, guild_id: int):
        return fancy_embed(
            "All Sleep Channels",
            description=f"\n".join(
                [
                    f"<#{c_id}>"
                    for c_id in self.sleep_tracker_files[guild_id]["SLEEP_CHANNEL_IDS"]
                ]
            ),
        )

    @top_command_sleep_channel.subcommand(
        "add",
        description="Add Voicechannels to the list of 'Sleep Channels'. Being in there will be considered sleeping.",
    )
    async def add_sleep_channel(
        self,
        interaction: nextcord.Interaction,
        channel: Union[
            nextcord.VoiceChannel, nextcord.CategoryChannel
        ] = nextcord.SlashOption(
            "channel",
            description="Either a Voicechannel or to add a bunch, a Categorychannel which contains Voicechannels to add.",
        ),
    ):
        if isinstance(channel, nextcord.VoiceChannel):
            channel_ids = [channel.id]
        else:
            channel_ids = [x.id for x in channel.voice_channels]

        for c_id in channel_ids:
            if (
                c_id
                not in self.sleep_tracker_files[channel.guild.id]["SLEEP_CHANNEL_IDS"]
            ):
                self.sleep_tracker_files[channel.guild.id]["SLEEP_CHANNEL_IDS"].append(
                    c_id
                )

        self.sleep_tracker_files[channel.guild.id].save()

        await interaction.send(embed=self.sleep_channel_list_embed(channel.guild.id))

    @top_command_sleep_channel.subcommand(
        "list", description="List all Voicechannels that are set as Sleep Channels."
    )
    async def list_sleep_channels(self, interaction: nextcord.Interaction):
        if not interaction.guild:
            raise application_checks.errors.ApplicationNoPrivateMessage()

        if (
            len(self.sleep_tracker_files[interaction.guild.id]["SLEEP_CHANNEL_IDS"])
            == 0
        ):
            await interaction.send(
                f"There are no Sleep Channels set yet. Use {self.add_sleep_channel.get_mention()} to add one or multiple."
            )
        else:
            await interaction.send(
                embed=self.sleep_channel_list_embed(interaction.guild.id)
            )

    @top_command_sleep_channel.subcommand(
        "remove", description="Remove Voicechannels from the list of 'Sleep Channels'."
    )
    async def remove_sleep_channel(
        self,
        interaction: nextcord.Interaction,
        channel: Union[
            nextcord.VoiceChannel, nextcord.CategoryChannel
        ] = nextcord.SlashOption(
            "channel",
            description="Either a Voicechannel or to add a bunch, a Categorychannel which contains Voicechannels to add.",
        ),
    ):
        if isinstance(channel, nextcord.VoiceChannel):
            channel_ids = [channel.id]
        else:
            channel_ids = [x.id for x in channel.voice_channels]

        for c_id in channel_ids:
            while (
                c_id in self.sleep_tracker_files[channel.guild.id]["SLEEP_CHANNEL_IDS"]
            ):
                self.sleep_tracker_files[channel.guild.id]["SLEEP_CHANNEL_IDS"].remove(
                    c_id
                )

        self.sleep_tracker_files[channel.guild.id].save()

    def convert_seconds_to_time_dict(self, seconds: int):
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        return {
            "Days": int(days),
            "Hours": int(hours),
            "Minutes": int(minutes),
            "Seconds": int(seconds),
        }

    def get_sleeping_entries(
        self, guild_id: int, user_id: int, with_user_id: Optional[int] = None
    ) -> List[Tuple[List[int], Dict[str, int]]]:
        entries = []

        for user_ids, seconds in self.sleep_tracker_files[guild_id][
            "SLEEP_DATA"
        ].items():
            user_ids = [int(x) for x in user_ids.split("/")]
            if user_id in user_ids and (
                with_user_id == None or with_user_id in user_ids
            ):
                user_ids.remove(user_id)
                time_data = self.convert_seconds_to_time_dict(seconds)

                entries.append([user_ids, time_data, seconds])

        entries.sort(key=lambda x: x[2], reverse=True)

        clean_entries: List[Tuple[List[int], Dict[str, int]]] = [
            (entry[0], entry[1]) for entry in entries
        ]

        return clean_entries

    @nextcord.slash_command("sleep-tracker", dm_permission=False)
    async def top_command_sleep_tracker(self, interaction: nextcord.Interaction):
        pass

    @top_command_sleep_tracker.subcommand(
        "slept-in-total-for",
        description="Shows how long you have slept in total, including alone.",
    )
    async def sleep_tracker_slept_alone(self, interaction: nextcord.Interaction):
        if not interaction.guild_id:
            raise application_checks.errors.ApplicationNoPrivateMessage()

        if not interaction.user:
            raise ValueError("Cant proceed without a interaction.user value.")

        if (
            str(interaction.user.id)
            in self.sleep_tracker_files[interaction.guild_id]["SLEEP_DATA"]
        ):
            seconds = self.sleep_tracker_files[interaction.guild_id]["SLEEP_DATA"][
                str(interaction.user.id)
            ]

            await interaction.send(
                embed=fancy_embed(
                    "Slept in total",
                    description="\n".join(
                        [
                            f"{key}: {val}"
                            for key, val in self.convert_seconds_to_time_dict(
                                seconds
                            ).items()
                        ]
                    ),
                )
            )
        else:
            await interaction.send("No data yet.", ephemeral=True)

    @top_command_sleep_tracker.subcommand(
        "slept-together-for",
        description="Show all the stats about how long you slept together with all different people.",
    )
    async def sleep_tracker_slept_together(
        self,
        interaction: nextcord.Interaction,
        member: Optional[nextcord.Member] = nextcord.SlashOption(
            "user",
            description="A User to filter the stats for. Only show stats with you and them.",
            default=None,
        ),
    ):
        if not interaction.guild_id:
            raise application_checks.errors.ApplicationNoPrivateMessage()

        if not interaction.user:
            raise ValueError("Cant proceed without a interaction.user value.")

        if member == interaction.user:
            await interaction.send(
                "You cant check for entries with just yourself.", ephemeral=True
            )
            return

        entries = self.get_sleeping_entries(
            interaction.guild_id, interaction.user.id, member.id if member else None
        )

        fields: Dict[str, str] = {}
        if len(entries) > 0 and any(len(user_ids) != 0 for user_ids, _ in entries):
            i = 1
            for user_ids, time_dict in entries:
                if len(user_ids) == 0:
                    continue

                if i % 20 == 0:
                    await interaction.send(
                        embed=fancy_embed(f"Place {i-19}-{i}", fields=fields)
                    )
                    fields: Dict[str, str] = {}

                fields[f"{i}."] = (
                    "\n".join([f"{key}: {val}" for key, val in time_dict.items()])
                    + "\n\n"
                    + "\n".join([f"<@{u_id}>" for u_id in user_ids])
                )

                i += 1

            lowest_place = i - 19
            if lowest_place < 1:
                lowest_place = 1

            if lowest_place != i - 1:
                title = f"Place {lowest_place}-{i-1}"
            else:
                title = "Sleeping Entries"

            await interaction.send(embed=fancy_embed(title, fields=fields))
        else:
            await interaction.send(
                "There are no entries that match this request.", ephemeral=True
            )

    @nextcord.user_command("Slept together for", dm_permission=False)
    async def slept_together_user_command(
        self, interaction: nextcord.Interaction, member: nextcord.Member
    ):
        await self.sleep_tracker_slept_together(interaction, member=member)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: nextcord.Member,
        before: nextcord.VoiceState,
        after: nextcord.VoiceState,
    ):
        if after.channel and isinstance(after.channel, nextcord.VoiceChannel):
            if (
                after.channel.id
                in self.sleep_tracker_files[after.channel.guild.id]["SLEEP_CHANNEL_IDS"]
                and before.channel != after.channel
            ):
                try:
                    await after.channel.send(
                        embed=fancy_embed(
                            "Good Night!",
                            description=f"{member.mention} joined the sleep call.",
                        )
                    )
                except nextcord.errors.Forbidden:
                    pass

                if after.channel.guild.id not in self.internal_state_db:
                    self.internal_state_db[after.channel.guild.id] = {}

                self.internal_state_db[after.channel.guild.id][member.id] = time.time()

        if before.channel and isinstance(before.channel, nextcord.VoiceChannel):
            if (
                before.channel.id
                in self.sleep_tracker_files[before.channel.guild.id][
                    "SLEEP_CHANNEL_IDS"
                ]
                and after.channel != before.channel
            ):
                try:
                    await before.channel.send(
                        embed=fancy_embed(
                            "Good Morning!",
                            description=f"{member.mention} left the sleep call.",
                        )
                    )
                except nextcord.errors.Forbidden:
                    pass

                if before.channel.guild.id in self.internal_state_db:
                    if member.id in self.internal_state_db[before.channel.guild.id]:
                        slept_with_user_ids = [m.id for m in before.channel.members]
                        slept_with_user_ids.append(member.id)

                        combs: List[List[int]] = []
                        for i in range(1, len(slept_with_user_ids) + 1):
                            combs.extend(
                                [
                                    list(x)
                                    for x in itertools.combinations(
                                        slept_with_user_ids, i
                                    )
                                ]
                            )

                        for comb in combs:
                            if member.id not in comb:
                                continue

                            comb.sort()

                            comb_key = "/".join([str(x) for x in comb])
                            if (
                                comb_key
                                not in self.sleep_tracker_files[
                                    before.channel.guild.id
                                ]["SLEEP_DATA"]
                            ):
                                self.sleep_tracker_files[before.channel.guild.id][
                                    "SLEEP_DATA"
                                ][comb_key] = 0

                            joined_at_values = [
                                self.internal_state_db[before.channel.guild.id][x]
                                for x in comb
                                if x in self.internal_state_db[before.channel.guild.id]
                            ]
                            newest_join_value = max(joined_at_values)

                            seconds_spent_together = time.time() - newest_join_value
                            if seconds_spent_together > 0:
                                self.sleep_tracker_files[before.channel.guild.id][
                                    "SLEEP_DATA"
                                ][comb_key] += seconds_spent_together

                        self.sleep_tracker_files[before.channel.guild.id].save()

                        del self.internal_state_db[before.channel.guild.id][member.id]


async def setup(bot):
    bot.add_cog(SleepTracking(bot))
