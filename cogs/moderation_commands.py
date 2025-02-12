import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import re

class ModerationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.timeout_history: Dict[int, List[Dict]] = {}

    def parse_time(self, time_str: str) -> Optional[timedelta]:
        if not time_str:
            return None
            
        time_units = {
            'y': 365 * 24 * 60 * 60,  # years in seconds
            'm': 30 * 24 * 60 * 60,   # months in seconds
            'w': 7 * 24 * 60 * 60,    # weeks in seconds
            'd': 24 * 60 * 60,        # days in seconds
            'h': 60 * 60,             # hours in seconds
            'm': 60,                   # minutes in seconds
            's': 1                     # seconds
        }

        total_seconds = 0
        pattern = r'(\d+)([ymwdhs])'
        matches = re.finditer(pattern, time_str.lower())
        
        for match in matches:
            value = int(match.group(1))
            unit = match.group(2)
            total_seconds += value * time_units[unit]
        
        return timedelta(seconds=total_seconds) if total_seconds > 0 else None

    @app_commands.command(name="nick", description="ユーザーのニックネームを変更")
    @app_commands.describe(
        user="対象ユーザー",
        name="新しいニックネーム (defaultで元に戻す)"
    )
    @app_commands.default_permissions(manage_nicknames=True)
    async def nick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        name: str
    ):
        if not interaction.user.guild_permissions.manage_nicknames:
            await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
            return

        try:
            old_nick = user.nick or user.name
            new_nick = None if name.lower() == "default" else name
            await user.edit(nick=new_nick)
            
            embed = discord.Embed(
                title="ニックネーム変更",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="対象ユーザー", value=user.mention)
            embed.add_field(name="変更前", value=old_nick)
            embed.add_field(name="変更後", value=new_nick or user.name)
            
            await interaction.response.send_message(embed=embed)
        except:
            await interaction.response.send_message("ニックネームの変更に失敗しました。", ephemeral=True)

    @app_commands.command(name="timeout", description="ユーザーのタイムアウトを管理")
    @app_commands.describe(
        user="対象ユーザー",
        action="実行するアクション",
        time="タイムアウト期間 (例: 1d2h30m)"
    )
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        action: str,
        time: Optional[str] = None
    ):
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
            return

        if user.id not in self.timeout_history:
            self.timeout_history[user.id] = []

        try:
            if action == "add":
                if not time:
                    await interaction.response.send_message("タイムアウト期間を指定してください。", ephemeral=True)
                    return
                
                duration = self.parse_time(time)
                if not duration:
                    await interaction.response.send_message("無効な時間形式です。", ephemeral=True)
                    return
                
                await user.timeout(duration)
                self.timeout_history[user.id].append({
                    'action': 'add',
                    'duration': duration,
                    'moderator': interaction.user.id,
                    'timestamp': datetime.now()
                })
                
                embed = discord.Embed(
                    title="タイムアウト追加",
                    description=f"{user.mention} をタイムアウトしました。",
                    color=discord.Color.red()
                )
                embed.add_field(name="期間", value=time)
                await interaction.response.send_message(embed=embed)

            elif action == "forever":
                max_duration = timedelta(days=28)  # Discord's maximum timeout duration
                await user.timeout(max_duration)
                self.timeout_history[user.id].append({
                    'action': 'forever',
                    'duration': max_duration,
                    'moderator': interaction.user.id,
                    'timestamp': datetime.now()
                })
                await interaction.response.send_message(f"{user.mention} を無期限タイムアウトしました。")

            elif action == "canceling":
                await user.timeout(None)
                self.timeout_history[user.id].append({
                    'action': 'cancel',
                    'moderator': interaction.user.id,
                    'timestamp': datetime.now()
                })
                await interaction.response.send_message(f"{user.mention} のタイムアウトを解除しました。")

            elif action == "view":
                if user.timed_out_until:
                    remaining = user.timed_out_until - datetime.now(user.timed_out_until.tzinfo)
                    await interaction.response.send_message(
                        f"{user.mention} は現在タイムアウト中です。\n"
                        f"解除まで: {remaining.days}日 {remaining.seconds//3600}時間 "
                        f"{(remaining.seconds//60)%60}分 {remaining.seconds%60}秒"
                    )
                else:
                    await interaction.response.send_message(f"{user.mention} は現在タイムアウトされていません。")

            elif action == "history":
                if not self.timeout_history[user.id]:
                    await interaction.response.send_message(f"{user.mention} のタイムアウト履歴はありません。")
                    return
                
                embed = discord.Embed(
                    title=f"{user.display_name} のタイムアウト履歴",
                    color=discord.Color.blue()
                )
                
                for entry in reversed(self.timeout_history[user.id][-10:]):  # Show last 10 entries
                    moderator = interaction.guild.get_member(entry['moderator'])
                    mod_name = moderator.display_name if moderator else "Unknown"
                    
                    value = f"実行者: {mod_name}\n"
                    if 'duration' in entry:
                        value += f"期間: {entry['duration']}\n"
                    value += f"日時: {discord.utils.format_dt(entry['timestamp'])}"
                    
                    embed.add_field(
                        name=f"アクション: {entry['action']}",
                        value=value,
                        inline=False
                    )
                
                await interaction.response.send_message(embed=embed)

            elif action == "remove":
                if not time:
                    await interaction.response.send_message("削除する期間を指定してください。", ephemeral=True)
                    return
                
                duration = self.parse_time(time)
                if not duration:
                    await interaction.response.send_message("無効な時間形式です。", ephemeral=True)
                    return
                
                if user.timed_out_until:
                    new_duration = user.timed_out_until - datetime.now(user.timed_out_until.tzinfo) - duration
                    if new_duration.total_seconds() <= 0:
                        await user.timeout(None)
                        await interaction.response.send_message(f"{user.mention} のタイムアウトを解除しました。")
                    else:
                        await user.timeout(new_duration)
                        await interaction.response.send_message(
                            f"{user.mention} のタイムアウト期間を {time} 短縮しました。\n"
                            f"残り: {new_duration.days}日 {new_duration.seconds//3600}時間 "
                            f"{(new_duration.seconds//60)%60}分 {new_duration.seconds%60}秒"
                        )
                else:
                    await interaction.response.send_message(f"{user.mention} は現在タイムアウトされていません。")

        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {str(e)}", ephemeral=True)

    @app_commands.command(name="fake-user", description="指定したユーザーになりすましてメッセージを送信")
    @app_commands.describe(
        user="なりすますユーザー",
        message="送信するメッセージ"
    )
    @app_commands.default_permissions(manage_webhooks=True)
    async def fake_user(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        message: str
    ):
        if not interaction.user.guild_permissions.manage_webhooks:
            await interaction.response.send_message("このコマンドを使用する権限がありません。", ephemeral=True)
            return

        try:
            webhook = await interaction.channel.create_webhook(name=f"FakeUser_{user.id}")
            await webhook.send(
                content=message,
                username=user.display_name,
                avatar_url=user.display_avatar.url
            )
            await webhook.delete()
            await interaction.response.send_message("メッセージを送信しました。", ephemeral=True)
        except:
            await interaction.response.send_message("メッセージの送信に失敗しました。", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCommands(bot))
