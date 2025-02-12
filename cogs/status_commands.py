import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime
import pytz
import re
from typing import Optional, Dict

# Major cities with timezone
MAJOR_CITIES = {
    'Tokyo': 'Asia/Tokyo',
    'New York': 'America/New_York',
    'London': 'Europe/London',
    'Paris': 'Europe/Paris',
    'Sydney': 'Australia/Sydney',
    'Los Angeles': 'America/Los_Angeles',
    'Dubai': 'Asia/Dubai',
    'Singapore': 'Asia/Singapore',
    'Hong Kong': 'Asia/Hong_Kong',
    'Moscow': 'Europe/Moscow',
    'Berlin': 'Europe/Berlin',
    'Rome': 'Europe/Rome',
    'Madrid': 'Europe/Madrid',
    'Beijing': 'Asia/Shanghai',
    'Seoul': 'Asia/Seoul',
    'Bangkok': 'Asia/Bangkok',
    'Mumbai': 'Asia/Kolkata',
    'Toronto': 'America/Toronto',
    'Sao Paulo': 'America/Sao_Paulo',
    'Mexico City': 'America/Mexico_City'
}

class StatsCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stat_tasks: Dict[int, asyncio.Task] = {}
        self.stat_channels: Dict[int, Dict] = {}

    def cog_unload(self):
        # Cancel all running tasks when the cog is unloaded
        for task in self.stat_tasks.values():
            task.cancel()

    async def update_time_channel(self, channel: discord.VoiceChannel, timezone_str: str):
        try:
            while True:
                tz = pytz.timezone(timezone_str)
                current_time = datetime.now(tz)
                await channel.edit(name=f"🕒 {current_time.strftime('%H:%M')}")
                await asyncio.sleep(60)  # 1分ごとに更新
        except Exception as e:
            print(f"Error updating time channel: {e}")

    async def update_date_channel(self, channel: discord.VoiceChannel, timezone_str: str):
        try:
            while True:
                tz = pytz.timezone(timezone_str)
                current_date = datetime.now(tz)
                await channel.edit(name=f"📅 {current_date.strftime('%Y/%m/%d')}")
                await asyncio.sleep(86400)  # 1日ごとに更新
        except Exception as e:
            print(f"Error updating date channel: {e}")

    async def update_member_count(self, channel: discord.VoiceChannel, guild: discord.Guild, type_: str):
        try:
            while True:
                if type_ == "online_member":
                    count = len([m for m in guild.members if m.status != discord.Status.offline])
                    await channel.edit(name=f"🟢 オンライン: {count}")
                elif type_ == "offline_member":
                    count = len([m for m in guild.members if m.status == discord.Status.offline])
                    await channel.edit(name=f"⚫ オフライン: {count}")
                elif type_ == "member":
                    count = guild.member_count
                    await channel.edit(name=f"👥 メンバー数: {count}")
                await asyncio.sleep(300)  # 5分ごとに更新
        except Exception as e:
            print(f"Error updating member count channel: {e}")

    @app_commands.command(name="stat", description="統計情報チャンネルを作成")
    @app_commands.describe(
        type="チャンネルの種類 (time/day/online_member/offline_member/member)",
        timezone="タイムゾーン (UTC+/-n または都市名)"
    )
    async def stat(
        self,
        interaction: discord.Interaction,
        type: str,
        timezone: Optional[str] = None
    ):
        try:
            # Check for admin permissions
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
                return

            if type in ["time", "day"]:
                if not timezone:
                    await interaction.response.send_message("タイムゾーンを指定してください。", ephemeral=True)
                    return

                # Handle timezone input
                if timezone.title() in MAJOR_CITIES:
                    tz_str = MAJOR_CITIES[timezone.title()]
                else:
                    match = re.match(r'UTC([+-]\d+)', timezone.upper())
                    if match:
                        offset = int(match.group(1))
                        if -12 <= offset <= 14:
                            tz_str = f"Etc/GMT{-offset}"
                        else:
                            await interaction.response.send_message("無効なUTCオフセットです。", ephemeral=True)
                            return
                    else:
                        await interaction.response.send_message("無効なタイムゾーン形式です。", ephemeral=True)
                        return

                # Check for existing category
                category = discord.utils.get(interaction.guild.categories, name="Server Stats")
                if not category:
                    category = await interaction.guild.create_category(
                        "Server Stats",
                        overwrites={
                            interaction.guild.default_role: discord.PermissionOverwrite(connect=False)
                        }
                    )

                channel = await category.create_voice_channel(f"Loading...")

                if type == "time":
                    task = self.bot.loop.create_task(self.update_time_channel(channel, tz_str))
                else:
                    task = self.bot.loop.create_task(self.update_date_channel(channel, tz_str))

                self.stat_tasks[channel.id] = task
                self.stat_channels[channel.id] = {"type": type, "timezone": tz_str}

            elif type in ["online_member", "offline_member", "member"]:
                category = discord.utils.get(interaction.guild.categories, name="Server Stats")
                if not category:
                    category = await interaction.guild.create_category(
                        "Server Stats",
                        overwrites={
                            interaction.guild.default_role: discord.PermissionOverwrite(connect=False)
                        }
                    )

                channel = await category.create_voice_channel(f"Loading...")
                task = self.bot.loop.create_task(
                    self.update_member_count(channel, interaction.guild, type)
                )
                self.stat_tasks[channel.id] = task
                self.stat_channels[channel.id] = {"type": type}

            await interaction.response.send_message("統計チャンネルを作成しました。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatsCommands(bot))
