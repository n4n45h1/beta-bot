import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from datetime import datetime

class LogCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channels = {}

    @app_commands.command(name="log", description="ログチャンネルを管理")
    @app_commands.describe(
        channel="ログを送信するチャンネル",
        action="実行するアクション (add/remove)"
    )
    @app_commands.default_permissions(administrator=True)
    async def log(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        action: str
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
            return

        guild_id = str(interaction.guild.id)

        if action == "add":
            if guild_id not in self.log_channels:
                self.log_channels[guild_id] = []
            if channel.id not in self.log_channels[guild_id]:
                self.log_channels[guild_id].append(channel.id)
                await interaction.response.send_message(f"{channel.mention}をログチャンネルとして追加しました。", ephemeral=True)
            else:
                await interaction.response.send_message("このチャンネルは既にログチャンネルとして登録されています。", ephemeral=True)
        
        elif action == "remove":
            if guild_id in self.log_channels and channel.id in self.log_channels[guild_id]:
                self.log_channels[guild_id].remove(channel.id)
                await interaction.response.send_message(f"{channel.mention}をログチャンネルから削除しました。", ephemeral=True)
            else:
                await interaction.response.send_message("このチャンネルはログチャンネルとして登録されていません。", ephemeral=True)

    async def log_event(self, guild: discord.Guild, embed: discord.Embed):
        guild_id = str(guild.id)
        if guild_id in self.log_channels:
            for channel_id in self.log_channels[guild_id]:
                channel = guild.get_channel(channel_id)
                if channel:
                    try:
                        await channel.send(embed=embed)
                    except:
                        pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        embed = discord.Embed(
            title="メンバー参加",
            description=f"{member.mention} がサーバーに参加しました。",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="アカウント作成日", value=discord.utils.format_dt(member.created_at))
        await self.log_event(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        embed = discord.Embed(
            title="メンバー退出",
            description=f"{member.mention} がサーバーを退出しました。",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.set_author(name=member.display_name, icon_url=member.display_avatar.url)
        embed.set_thumbnail(url=member.display_avatar.url)
        await self.log_event(member.guild, embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            embed = discord.Embed(
                title="ニックネーム変更",
                description=f"{after.mention} のニックネームが変更されました。",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_author(name=after.display_name, icon_url=after.display_avatar.url)
            embed.add_field(name="変更前", value=before.nick or before.name)
            embed.add_field(name="変更後", value=after.nick or after.name)
            
            # Get audit log entry for nickname change
            async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id:
                    embed.add_field(
                        name="実行者",
                        value=f"{entry.user.mention} ({entry.user.display_name})",
                        inline=False
                    )
                    break
            
            await self.log_event(after.guild, embed)

        if before.roles != after.roles:
            added_roles = set(after.roles) - set(before.roles)
            removed_roles = set(before.roles) - set(after.roles)
            
            if added_roles or removed_roles:
                embed = discord.Embed(
                    title="ロール変更",
                    description=f"{after.mention} のロールが変更されました。",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.set_author(name=after.display_name, icon_url=after.display_avatar.url)
                if added_roles:
                    embed.add_field(name="追加されたロール", value=", ".join(role.mention for role in added_roles))
                if removed_roles:
                    embed.add_field(name="削除されたロール", value=", ".join(role.mention for role in removed_roles))
                
                # Get audit log entry for role change
                async for entry in after.guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
                    if entry.target.id == after.id:
                        embed.add_field(
                            name="実行者",
                            value=f"{entry.user.mention} ({entry.user.display_name})",
                            inline=False
                        )
                        break
                
                await self.log_event(after.guild, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if not before.author.bot and before.content != after.content:
            embed = discord.Embed(
                title="メッセージ編集",
                description=f"{before.channel.mention} でメッセージが編集されました。",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.set_author(name=before.author.display_name, icon_url=before.author.display_avatar.url)
            embed.add_field(name="編集前", value=before.content or "なし")
            embed.add_field(name="編集後", value=after.content or "なし")
            embed.add_field(name="メッセージリンク", value=f"[クリック]({after.jump_url})", inline=False)
            embed.add_field(
                name="編集者",
                value=f"{before.author.mention} ({before.author.display_name})",
                inline=False
            )
            await self.log_event(before.guild, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if not message.author.bot:
            embed = discord.Embed(
                title="メッセージ削除",
                description=f"{message.channel.mention} でメッセージが削除されました。",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
            embed.add_field(name="内容", value=message.content or "なし")
            
            # Get audit log entry for message deletion
            async for entry in message.guild.audit_logs(limit=1, action=discord.AuditLogAction.message_delete):
                if entry.target.id == message.author.id:
                    embed.add_field(
                        name="削除者",
                        value=f"{entry.user.mention} ({entry.user.display_name})",
                        inline=False
                    )
                    break
            else:
                embed.add_field(
                    name="削除者",
                    value=f"{message.author.mention} ({message.author.display_name}) [自己削除]",
                    inline=False
                )
            
            await self.log_event(message.guild, embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(LogCommands(bot))
