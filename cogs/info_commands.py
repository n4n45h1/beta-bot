import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional

class InfoCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="ユーザーのアバター画像を表示")
    async def avatar(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        embed = discord.Embed(title=f"{user.display_name}のアバター", color=discord.Color.blue())
        
        # Add avatar URLs for different formats
        avatar = user.display_avatar
        formats = {
            'jpg': avatar.replace(format='jpg', size=4096).url,
            'png': avatar.replace(format='png', size=4096).url,
            'webp': avatar.replace(format='webp', size=4096).url
        }
        
        embed.set_image(url=avatar.url)
        embed.description = "ダウンロードリンク:\n" + "\n".join(
            f"[{format.upper()}]({url})" for format, url in formats.items()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="user_info", description="ユーザー情報を表示")
    async def user_info(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        embed = discord.Embed(title=f"ユーザー情報: {user.display_name}", color=discord.Color.blue())
        embed.set_thumbnail(url=user.display_avatar.url)
        
        # Basic info
        embed.add_field(
            name="基本情報",
            value=f"**ユーザー名:** {user.name}\n"
                  f"**表示名:** {user.display_name}\n"
                  f"**ユーザーID:** {user.id}",
            inline=False
        )
        
        # Dates
        embed.add_field(
            name="日付",
            value=f"**アカウント作成:** {discord.utils.format_dt(user.created_at)}\n"
                  f"**サーバー参加:** {discord.utils.format_dt(user.joined_at)}",
            inline=False
        )
        
        # Roles
        roles = [role.mention for role in reversed(user.roles[1:])]  # Exclude @everyone
        embed.add_field(
            name=f"ロール [{len(roles)}]",
            value=" ".join(roles) if roles else "なし",
            inline=False
        )
        
        # Badges
        flags = [str(flag)[10:].replace('_', ' ').title() for flag, enabled in user.public_flags if enabled]
        embed.add_field(
            name="バッジ",
            value="\n".join(flags) if flags else "なし",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="server_info", description="サーバー情報を表示")
    async def server_info(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"サーバー情報: {guild.name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic info
        embed.add_field(
            name="基本情報",
            value=f"**作成日:** {discord.utils.format_dt(guild.created_at)}\n"
                  f"**オーナー:** {guild.owner.mention}\n"
                  f"**サーバーID:** {guild.id}",
            inline=False
        )
        
        # Counts
        embed.add_field(
            name="統計",
            value=f"**総メンバー数:** {guild.member_count}\n"
                  f"**総チャンネル数:** {len(guild.channels)}\n"
                  f"**総ロール数:** {len(guild.roles)}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCommands(bot))
