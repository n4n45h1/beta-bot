import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Dict
import re

class WelcomeCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.welcome_settings: Dict[str, Dict] = {}
        self.dm_settings: Dict[str, Dict] = {}

    def parse_placeholders(self, message: str, member: discord.Member, invite=None) -> str:
        replacements = {
            '@user': member.name,
            '@user.mention': member.mention,
            '@date': discord.utils.format_dt(discord.utils.utcnow()),
            '@member.count': str(member.guild.member_count),
            '@server': member.guild.name
        }
        
        if invite:
            replacements.update({
                '@invite.url': invite.url,
                '@invite.url.user': invite.inviter.name if invite.inviter else '不明'
            })

        result = message
        for key, value in replacements.items():
            result = result.replace(f"[{key}]", value)
        return result

    @app_commands.command(name="welcome", description="参加メッセージを設定")
    @app_commands.describe(
        action="実行するアクション",
        channel="メッセージを送信するチャンネル",
        message="送信するメッセージ",
        embed="埋め込みメッセージを使用",
        color="埋め込みの色 (#RRGGBB)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="チャンネル設定", value="set"),
        app_commands.Choice(name="チャンネル解除", value="unset"),
        app_commands.Choice(name="DM設定", value="dm_set"),
        app_commands.Choice(name="DM解除", value="dm_unset")
    ])
    @app_commands.default_permissions(administrator=True)
    async def welcome(
        self,
        interaction: discord.Interaction,
        action: str,
        channel: Optional[discord.TextChannel] = None,
        message: Optional[str] = None,
        embed: Optional[bool] = True,
        color: Optional[str] = "#5865F2"
    ):
        guild_id = str(interaction.guild.id)

        if action == "set":
            if not channel:
                await interaction.response.send_message("チャンネルを指定してください！", ephemeral=True)
                return

            # デフォルトメッセージ
            default_message = (
                "[@user.mention]さん、ようこそ！\n"
                "メンバー数: [@member.count]人"
            )

            self.welcome_settings[guild_id] = {
                'channel_id': channel.id,
                'message': message or default_message,
                'embed': embed,
                'color': int(color.lstrip('#'), 16) if color else 0x5865F2
            }

            # プレビューを表示
            preview = self.parse_placeholders(
                message or default_message,
                interaction.user
            )

            if embed:
                embed_preview = discord.Embed(
                    description=preview,
                    color=int(color.lstrip('#'), 16) if color else 0x5865F2
                )
                await interaction.response.send_message(
                    f"参加メッセージを {channel.mention} に設定しました！\n\nプレビュー:",
                    embed=embed_preview,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"参加メッセージを {channel.mention} に設定しました！\n\nプレビュー:\n{preview}",
                    ephemeral=True
                )

        elif action == "unset":
            if not channel:
                await interaction.response.send_message("チャンネルを指定してください！", ephemeral=True)
                return

            if guild_id in self.welcome_settings:
                del self.welcome_settings[guild_id]
                await interaction.response.send_message(
                    f"{channel.mention} の参加メッセージを削除しました。",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "参加メッセージは設定されていません。",
                    ephemeral=True
                )

        elif action == "dm_set":
            # デフォルトDMメッセージ
            default_dm = (
                "こんにちは、[@user.mention]さん！\n"
                "[@server]へようこそ！\n"
                "招待リンク: [@invite.url]\n"
                "招待者: [@invite.url.user]"
            )

            self.dm_settings[guild_id] = {
                'message': message or default_dm,
                'embed': embed,
                'color': int(color.lstrip('#'), 16) if color else 0x5865F2
            }

            # プレビューを表示
            preview = self.parse_placeholders(
                message or default_dm,
                interaction.user
            )

            if embed:
                embed_preview = discord.Embed(
                    description=preview,
                    color=int(color.lstrip('#'), 16) if color else 0x5865F2
                )
                await interaction.response.send_message(
                    "DM参加メッセージを設定しました！\n\nプレビュー:",
                    embed=embed_preview,
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"DM参加メッセージを設定しました！\n\nプレビュー:\n{preview}",
                    ephemeral=True
                )

        elif action == "dm_unset":
            if guild_id in self.dm_settings:
                del self.dm_settings[guild_id]
                await interaction.response.send_message(
                    "DM参加メッセージを削除しました。",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "DM参加メッセージは設定されていません。",
                    ephemeral=True
                )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild_id = str(member.guild.id)

        # チャンネルメッセージ
        if guild_id in self.welcome_settings:
            settings = self.welcome_settings[guild_id]
            channel = member.guild.get_channel(settings['channel_id'])
            
            if channel:
                message = self.parse_placeholders(settings['message'], member)
                
                if settings.get('embed', True):
                    embed = discord.Embed(
                        description=message,
                        color=settings.get('color', 0x5865F2)
                    )
                    await channel.send(embed=embed)
                else:
                    await channel.send(message)

        # DMメッセージ
        if guild_id in self.dm_settings:
            settings = self.dm_settings[guild_id]
            message = self.parse_placeholders(settings['message'], member)
            
            try:
                if settings.get('embed', True):
                    embed = discord.Embed(
                        description=message,
                        color=settings.get('color', 0x5865F2)
                    )
                    await member.send(embed=embed)
                else:
                    await member.send(message)
            except:
                pass  # DMが送れない場合は無視

async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCommands(bot))
