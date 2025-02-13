import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict, List
from datetime import datetime

class LogCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_settings: Dict[str, Dict] = {}  # guild_id -> settings

    @app_commands.command(name="log", description="ログの設定を管理")
    @app_commands.describe(
        channel="ログを送信するチャンネル",
        action="add (追加) / remove (削除)",
        events="記録するイベント (カンマ区切り)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="追加", value="add"),
        app_commands.Choice(name="削除", value="remove")
    ])
    @app_commands.default_permissions(administrator=True)
    async def log(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        action: str,
        events: Optional[str] = None
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("管理者権限が必要です！", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)
        
        # 利用可能なイベント一覧
        available_events = {
            "all": "すべてのイベント",
            "message_edit": "メッセージ編集",
            "message_delete": "メッセージ削除",
            "channel_create": "チャンネル作成",
            "channel_delete": "チャンネル削除",
            "channel_edit": "チャンネル設定変更",
            "webhook_create": "Webhook作成",
            "webhook_delete": "Webhook削除",
            "webhook_edit": "Webhook設定変更",
            "emoji_add": "絵文字追加",
            "emoji_remove": "絵文字削除",
            "emoji_edit": "絵文字変更",
            "role_create": "ロール作成",
            "role_delete": "ロール削除",
            "role_edit": "ロール設定変更",
            "member_join": "メンバー参加",
            "member_leave": "メンバー退出",
            "member_update": "メンバー情報更新",
            "member_ban": "メンバーBAN",
            "member_unban": "メンバーBAN解除",
            "member_timeout": "メンバータイムアウト"
        }

        if action == "add":
            if guild_id not in self.log_settings:
                self.log_settings[guild_id] = {}
            
            if str(channel.id) not in self.log_settings[guild_id]:
                self.log_settings[guild_id][str(channel.id)] = []

            if not events:
                # イベント指定がない場合は選択肢を表示
                embed = discord.Embed(
                    title="ログイベントの設定",
                    description="記録したいイベントをカンマ区切りで指定してください。\n例: `message_edit,member_join,role_edit`",
                    color=discord.Color.blue()
                )
                
                for event, desc in available_events.items():
                    embed.add_field(name=event, value=desc, inline=True)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            # イベントの追加
            requested_events = [e.strip() for e in events.lower().split(",")]
            valid_events = []
            invalid_events = []
            
            for event in requested_events:
                if event in available_events or event == "all":
                    valid_events.append(event)
                else:
                    invalid_events.append(event)

            if valid_events:
                if "all" in valid_events:
                    self.log_settings[guild_id][str(channel.id)] = list(available_events.keys())
                else:
                    self.log_settings[guild_id][str(channel.id)].extend(valid_events)
                    self.log_settings[guild_id][str(channel.id)] = list(set(self.log_settings[guild_id][str(channel.id)]))

            response = []
            if valid_events:
                response.append(f"✅ {channel.mention} に以下のログを追加しました：\n" + ", ".join(valid_events))
            if invalid_events:
                response.append(f"❌ 無効なイベント：{', '.join(invalid_events)}")

            await interaction.response.send_message("\n".join(response), ephemeral=True)

        elif action == "remove":
            if not guild_id in self.log_settings or not str(channel.id) in self.log_settings[guild_id]:
                await interaction.response.send_message("このチャンネルにはログ設定がありません。", ephemeral=True)
                return

            if not events:
                # チャンネルの全設定を削除
                del self.log_settings[guild_id][str(channel.id)]
                await interaction.response.send_message(f"{channel.mention} のすべてのログ設定を削除しました。", ephemeral=True)
                return

            # 指定されたイベントを削除
            requested_events = [e.strip() for e in events.lower().split(",")]
            removed_events = []
            not_found_events = []

            for event in requested_events:
                if event in self.log_settings[guild_id][str(channel.id)]:
                    self.log_settings[guild_id][str(channel.id)].remove(event)
                    removed_events.append(event)
                else:
                    not_found_events.append(event)

            response = []
            if removed_events:
                response.append(f"✅ {channel.mention} から以下のログを削除しました：\n" + ", ".join(removed_events))
            if not_found_events:
                response.append(f"❌ 設定されていないイベント：{', '.join(not_found_events)}")

            await interaction.response.send_message("\n".join(response), ephemeral=True)

    # 以下、各種イベントリスナーの実装...
    # (既存のイベントリスナーはそのまま維持)
