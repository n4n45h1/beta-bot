import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
import re

class ModerationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clear", description="メッセージを一括削除")
    @app_commands.describe(
        amount="削除するメッセージ数 (1-100)",
        user="特定のユーザーのメッセージのみ削除"
    )
    @app_commands.default_permissions(manage_messages=True)
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: Optional[discord.Member] = None
    ):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("メッセージの管理権限が必要です！", ephemeral=True)
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message("1から100の間で指定してください！", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if user:
            messages = []
            async for message in interaction.channel.history(limit=100):
                if message.author == user:
                    messages.append(message)
                    if len(messages) >= amount:
                        break
            
            if messages:
                await interaction.channel.delete_messages(messages)
                await interaction.followup.send(
                    f"{user.mention} のメッセージを {len(messages)}件 削除しました。",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"{user.mention} の最近のメッセージは見つかりませんでした。",
                    ephemeral=True
                )
        else:
            deleted = await interaction.channel.purge(limit=amount)
            await interaction.followup.send(
                f"メッセージを {len(deleted)}件 削除しました。",
                ephemeral=True
            )

    @app_commands.command(name="nuke", description="チャンネルのメッセージをすべて削除")
    @app_commands.default_permissions(administrator=True)
    async def nuke(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("管理者権限が必要です！", ephemeral=True)
            return

        # 確認メッセージ
        embed = discord.Embed(
            title="⚠️ 警告",
            description=(
                "このチャンネルのメッセージをすべて削除しようとしています。\n"
                "この操作は取り消せません。続行しますか？"
            ),
            color=discord.Color.red()
        )

        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.value = None

            @discord.ui.button(label="はい", style=discord.ButtonStyle.danger)
            async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()
                await button_interaction.response.defer()

            @discord.ui.button(label="いいえ", style=discord.ButtonStyle.secondary)
            async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()
                await button_interaction.response.defer()

        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        await view.wait()

        if view.value:
            # チャンネルを複製して古いチャンネルを削除
            new_channel = await interaction.channel.clone()
            await interaction.channel.delete()
            
            # 完了メッセージを送信
            embed = discord.Embed(
                title="✅ 完了",
                description="チャンネルのメッセージをすべて削除しました。",
                color=discord.Color.green()
            )
            await new_channel.send(embed=embed)
        else:
            await interaction.edit_original_response(
                content="操作をキャンセルしました。",
                embed=None,
                view=None
            )

    @app_commands.command(name="ping", description="BOTの応答速度を表示")
    async def ping(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏓 Pong!",
            color=discord.Color.green()
        )
        embed.add_field(
            name="レイテンシ",
            value=f"{round(self.bot.latency * 1000)}ms"
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="list", description="BANまたはKICKされたユーザーの一覧を表示")
    @app_commands.describe(type="表示する一覧の種類")
    @app_commands.choices(type=[
        app_commands.Choice(name="BAN一覧", value="ban"),
        app_commands.Choice(name="KICK一覧", value="kick")
    ])
    @app_commands.default_permissions(ban_members=True, kick_members=True)
    async def list_users(
        self,
        interaction: discord.Interaction,
        type: str
    ):
        if type == "ban" and not interaction.user.guild_permissions.ban_members:
            await interaction.response.send_message("BANの権限が必要です！", ephemeral=True)
            return
            
        if type == "kick" and not interaction.user.guild_permissions.kick_members:
            await interaction.response.send_message("KICKの権限が必要です！", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        if type == "ban":
            bans = [entry async for entry in interaction.guild.bans()]
            if not bans:
                await interaction.followup.send("BANされているユーザーはいません。", ephemeral=True)
                return

            embed = discord.Embed(
                title="BANされているユーザー",
                color=discord.Color.red()
            )
            
            for ban in bans:
                embed.add_field(
                    name=f"{ban.user.name} ({ban.user.id})",
                    value=f"理由: {ban.reason or '理由なし'}",
                    inline=False
                )

        elif type == "kick":
            # KICKの履歴はDiscord APIで直接は取得できないため、
            # 監査ログから最近のKICKを取得
            kicks = []
            async for entry in interaction.guild.audit_logs(action=discord.AuditLogAction.kick):
                if len(kicks) >= 25:  # 最大25件まで
                    break
                kicks.append(entry)

            if not kicks:
                await interaction.followup.send("最近KICKされたユーザーはいません。", ephemeral=True)
                return

            embed = discord.Embed(
                title="最近KICKされたユーザー",
                color=discord.Color.orange()
            )
            
            for kick in kicks:
                embed.add_field(
                    name=f"{kick.target} ({kick.target.id})",
                    value=(
                        f"実行者: {kick.user.name}\n"
                        f"日時: {discord.utils.format_dt(kick.created_at)}\n"
                        f"理由: {kick.reason or '理由なし'}"
                    ),
                    inline=False
                )

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationCommands(bot))
