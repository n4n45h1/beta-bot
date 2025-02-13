import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from typing import Dict, Optional, List
import re

class ModActionView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Ban", style=discord.ButtonStyle.danger)
    async def ban_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("BANの権限がありません。", ephemeral=True)
            return
        
        try:
            member = await interaction.guild.fetch_member(self.user_id)
            await member.ban(reason="サーバー内での違反")
            await interaction.response.send_message(f"{member.name}をBANしました。", ephemeral=True)
        except:
            await interaction.response.send_message("BANに失敗しました。", ephemeral=True)

    @discord.ui.button(label="Kick", style=discord.ButtonStyle.danger)
    async def kick_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("KICKの権限がありません。", ephemeral=True)
            return
        
        try:
            member = await interaction.guild.fetch_member(self.user_id)
            await member.kick(reason="サバー内での違反")
            await interaction.response.send_message(f"{member.name}をKICKしました。", ephemeral=True)
        except:
            await interaction.response.send_message("KICKに失敗しました。", ephemeral=True)

    @discord.ui.button(label="警告DM", style=discord.ButtonStyle.primary)
    async def warn_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            member = await interaction.guild.fetch_member(self.user_id)
            await member.send(f"{member.name}さん、サーバーのルールに違反する投稿が検出されました。\n今後このような投稿は控えてください。")
            await interaction.response.send_message(f"{member.name}に警告DMを送信しました。", ephemeral=True)
        except:
            await interaction.response.send_message("DMの送信に失敗しました。", ephemeral=True)

class FilterCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.filtered_words: Dict[str, Dict] = {}
        self.block_urls: bool = False
        self.block_invites: bool = False
        self.log_channel: Optional[discord.TextChannel] = None
        self.violation_counts: Dict[int, int] = {}

    @app_commands.command(name="filter", description="コンテンツフィルターを管理")
    @app_commands.describe(
        action="実行するアクション",
        subaction="サブアクション (word用)",
        word="フィルターする単語",
        penalty="違反時のアクション (kick/ban/timeout)",
        timeout="タイムアウト時間（分）",
        value="設定値",
        channel="ログチャンネル"
    )
    async def filter(
        self,
        interaction: discord.Interaction,
        action: str,
        subaction: Optional[str] = None,
        word: Optional[str] = None,
        penalty: Optional[str] = None,
        timeout: Optional[int] = None,
        value: Optional[bool] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
            return

        if action == "word":
            if subaction == "add":
                if not all([word, penalty]):
                    await interaction.response.send_message("単語とペナルティを指定してください。", ephemeral=True)
                    return
                
                if penalty not in ["kick", "ban", "timeout"]:
                    await interaction.response.send_message("無効なペナルティです。", ephemeral=True)
                    return

                self.filtered_words[word] = {
                    'penalty': penalty,
                    'timeout': timeout if penalty == "timeout" else None
                }
                await interaction.response.send_message(f"フィルター単語を追加しました: {word}", ephemeral=True)

            elif subaction == "remove":
                if not word:
                    await interaction.response.send_message("単語を指定してください。", ephemeral=True)
                    return
                
                if word in self.filtered_words:
                    del self.filtered_words[word]
                    await interaction.response.send_message(f"フィルター単語を削除しました: {word}", ephemeral=True)
                else:
                    await interaction.response.send_message("指定された単語は登録されていません。", ephemeral=True)

            elif subaction == "edit":
                if not all([word, penalty]):
                    await interaction.response.send_message("単語とペナルティを指定してください。", ephemeral=True)
                    return
                
                if word not in self.filtered_words:
                    await interaction.response.send_message("指定された単語は登録されていません。", ephemeral=True)
                    return

                self.filtered_words[word] = {
                    'penalty': penalty,
                    'timeout': timeout if penalty == "timeout" else None
                }
                await interaction.response.send_message(f"フィルター設定を更新しました: {word}", ephemeral=True)

            elif subaction == "list":
                if not self.filtered_words:
                    await interaction.response.send_message("フィルター単語は登録されていません。", ephemeral=True)
                    return

                embed = discord.Embed(title="フィルター単語一覧", color=discord.Color.blue())
                for word, settings in self.filtered_words.items():
                    penalty_str = settings['penalty']
                    if settings['timeout']:
                        penalty_str += f" ({settings['timeout']}分)"
                    embed.add_field(name=word, value=penalty_str, inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

        elif action == "url-block":
            if value is None:
                await interaction.response.send_message("値を指定してください。", ephemeral=True)
                return
            
            self.block_urls = value
            await interaction.response.send_message(f"URL制限を{'有効' if value else '無効'}にしました。", ephemeral=True)

        elif action == "inviteurl-block":
            if value is None:
                await interaction.response.send_message("値を指定してください。", ephemeral=True)
                return
            
            self.block_invites = value
            await interaction.response.send_message(f"招待リンク制限を{'有効' if value else '無効'}にしました。", ephemeral=True)

        elif action == "log":
            if not channel:
                await interaction.response.send_message("チャンネルを指定してください。", ephemeral=True)
                return
            
            self.log_channel = channel
            await interaction.response.send_message(f"ログチャンネルを{channel.mention}に設定しました。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not isinstance(message.channel, discord.TextChannel):
            return

        content = message.content.lower()
        violated = False
        reason = None
        detected_word = None

        # Check filtered words
        for word, settings in self.filtered_words.items():
            if word.lower() in content:
                violated = True
                reason = f"禁止ワード: {word}"
                detected_word = word
                await self._handle_violation(message, settings, reason, detected_word)
                break

        # Check URLs
        if self.block_urls and not violated:
            url_pattern = r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
            if re.search(url_pattern, content):
                violated = True
                reason = "URL投稿"
                await self._handle_violation(message, {'penalty': None}, reason, None)

        # Check Discord invites
        if self.block_invites and not violated:
            invite_pattern = r'discord\.gg/\w+'
            if re.search(invite_pattern, content):
                violated = True
                reason = "招待リンク"
                await self._handle_violation(message, {'penalty': None}, reason, None)

        if violated and self.log_channel:
            embed = discord.Embed(
                title="ルール違反",
                description=f"違反者: {message.author.mention} (`{message.author.id}`)\n"
                           f"理由: {reason}\n"
                           f"違反回数: {self.violation_counts.get(message.author.id, 0)}",
                color=discord.Color.red(),
                timestamp=message.created_at
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.add_field(name="メッセージ内容", value=message.content, inline=False)
            if detected_word:
                embed.add_field(name="検出された禁止単語", value=detected_word, inline=False)
            
            view = ModActionView(message.author.id)
            await self.log_channel.send(embed=embed, view=view)

    async def _handle_violation(self, message: discord.Message, settings: Dict, reason: str, detected_word: Optional[str]):
        try:
            # Update violation count
            user_id = message.author.id
            self.violation_counts[user_id] = self.violation_counts.get(user_id, 0) + 1

            # Delete message
            await message.delete()

            # Send warning to the violator
            warning_message = (
                f"{message.author.mention}、現在使用された言葉は、サーバーのルールにより禁止されています"
                f"{f'(禁止単語: {detected_word})' if detected_word else ''}。\n"
                "今後、同じ発言が繰り返されると、BanやKickのリスクがあるため、注意をしてください。"
            )
            await message.channel.send(warning_message, delete_after=10)

            # Apply penalty if specified
            if settings['penalty']:
                if settings['penalty'] == "kick":
                    await message.author.kick(reason=reason)
                elif settings['penalty'] == "ban":
                    await message.author.ban(reason=reason)
                elif settings['penalty'] == "timeout":
                    duration = settings.get('timeout', 5)
                    await message.author.timeout(
                        duration=datetime.timedelta(minutes=duration),
                        reason=reason
                    )
        except Exception as e:
            print(f"Error handling violation: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(FilterCommands(bot))
