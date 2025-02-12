import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from typing import Dict, Optional

class TicketButton(Button):
    def __init__(self, panel_name: str, ticket_data: Dict):
        super().__init__(label="チケットを作成", style=discord.ButtonStyle.primary)
        self.panel_name = panel_name
        self.ticket_data = ticket_data

    async def callback(self, interaction: discord.Interaction):
        try:
            user_id = str(interaction.user.id)
            
            # Check ticket limit
            if user_id in self.ticket_data['user_tickets']:
                if len(self.ticket_data['user_tickets'][user_id]) >= 3:
                    await interaction.response.send_message("チケットの上限（3枚）に達しています。", ephemeral=True)
                    return

            panel = self.ticket_data['panels'][self.panel_name]
            if not panel['admin_role']:
                await interaction.response.send_message("管理者ロールが設定されていません。", ephemeral=True)
                return

            admin_role = interaction.guild.get_role(panel['admin_role'])
            if not admin_role:
                await interaction.response.send_message("管理者ロールが見つかりません。", ephemeral=True)
                return
            
            # Create ticket channel
            self.ticket_data['ticket_count'] += 1
            channel_name = f"ticket-{self.ticket_data['ticket_count']}"
            
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            category = discord.utils.get(interaction.guild.categories, name="Tickets")
            if not category:
                category = await interaction.guild.create_category("Tickets")

            channel = await interaction.guild.create_text_channel(
                channel_name,
                category=category,
                overwrites=overwrites
            )

            # Create close button
            close_button = Button(label="チケットを閉じる", style=discord.ButtonStyle.danger)
            
            async def close_callback(inter: discord.Interaction):
                if inter.user.get_role(panel['admin_role']) or inter.user.id == interaction.user.id:
                    await channel.delete()
                    if user_id in self.ticket_data['user_tickets']:
                        if channel.id in self.ticket_data['user_tickets'][user_id]:
                            self.ticket_data['user_tickets'][user_id].remove(channel.id)
                else:
                    await inter.response.send_message("このボタンを使用する権限がありません。", ephemeral=True)

            close_button.callback = close_callback
            view = View()
            view.add_item(close_button)

            embed = discord.Embed(
                title="チケットが作成されました",
                description=f"作成者: {interaction.user.mention}",
                color=discord.Color.green()
            )
            await channel.send(embed=embed, view=view)

            if user_id not in self.ticket_data['user_tickets']:
                self.ticket_data['user_tickets'][user_id] = []
            self.ticket_data['user_tickets'][user_id].append(channel.id)

            await interaction.response.send_message(f"チケットを作成しました: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"チケットの作成に失敗しました: {str(e)}", ephemeral=True)

class TicketCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ticket_data = {
            'panels': {},
            'user_tickets': {},
            'ticket_count': 0
        }

    @app_commands.command(name="ticket-create", description="Create a ticket panel")
    @app_commands.default_permissions(administrator=True)
    async def create_ticket_panel(
        self,
        interaction: discord.Interaction,
        panel_name: str
    ):
        if panel_name in self.ticket_data['panels']:
            await interaction.response.send_message("同名のパネルが既に存在します。", ephemeral=True)
            return

        self.ticket_data['panels'][panel_name] = {
            'embed_color': 0x00ff00,
            'description': "下のボタンをクリックしてチケットを作成",
            'title': "サポートチケット",
            'image': None,
            'admin_role': None
        }
        
        await interaction.response.send_message(f"チケットパネル '{panel_name}' を作成しました！", ephemeral=True)

    @app_commands.command(name="ticket-set", description="Set up a ticket panel in the channel")
    @app_commands.default_permissions(administrator=True)
    async def setup_ticket_panel(
        self,
        interaction: discord.Interaction,
        panel_name: str
    ):
        if panel_name not in self.ticket_data['panels']:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return

        panel = self.ticket_data['panels'][panel_name]
        if not panel['admin_role']:
            await interaction.response.send_message("管理者ロールが設定されていません。", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=panel['title'],
            description=panel['description'],
            color=panel['embed_color']
        )
        if panel['image']:
            embed.set_image(url=panel['image'])

        view = View(timeout=None)
        view.add_item(TicketButton(panel_name, self.ticket_data))
        
        await interaction.channel.send(embed=embed, view=view)
        await interaction.response.send_message("チケットパネルを設置しました！", ephemeral=True)

    @app_commands.command(name="ticket-settings", description="Configure a ticket panel")
    @app_commands.default_permissions(administrator=True)
    async def configure_ticket_panel(
        self,
        interaction: discord.Interaction,
        panel_name: str,
        embed_color: Optional[str] = None,
        description: Optional[str] = None,
        image: Optional[str] = None,
        title: Optional[str] = None,
        admin_role: Optional[discord.Role] = None
    ):
        if panel_name not in self.ticket_data['panels']:
            await interaction.response.send_message("パネルが見つかりません。", ephemeral=True)
            return

        panel = self.ticket_data['panels'][panel_name]
        
        if embed_color:
            if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', embed_color):
                await interaction.response.send_message("無効な色形式です。16進数形式を使用してください（例: #FF0000）", ephemeral=True)
                return
            panel['embed_color'] = int(embed_color.lstrip('#'), 16)
        
        if description:
            panel['description'] = description
        
        if image:
            panel['image'] = image
        
        if title:
            panel['title'] = title
        
        if admin_role:
            panel['admin_role'] = admin_role.id

        await interaction.response.send_message(f"パネル '{panel_name}' の設定を更新しました！", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCommands(bot))
