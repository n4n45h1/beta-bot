import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View
from typing import Dict, Optional, List
import re

class RolePanelView(View):
    def __init__(self, roles_data: List[Dict]):
        super().__init__(timeout=None)
        self.roles_data = roles_data

    async def handle_role(self, interaction: discord.Interaction, role_id: int, add: bool):
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("ロールが見つかりません。", ephemeral=True)
            return

        member = interaction.user
        try:
            if add:
                if role not in member.roles:
                    await member.add_roles(role)
                    await interaction.response.send_message(f"{role.name}ロールを付与しました。", ephemeral=True)
                else:
                    await interaction.response.send_message("既にこのロールを持っています。", ephemeral=True)
            else:
                if role in member.roles:
                    await member.remove_roles(role)
                    await interaction.response.send_message(f"{role.name}ロールを削除しました。", ephemeral=True)
                else:
                    await interaction.response.send_message("このロールを持っていません。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("ロールの変更に失敗しました。", ephemeral=True)

class RolePanelCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.panels: Dict[str, Dict] = {}
        self.selected_panel: Optional[str] = None

    @app_commands.command(name="rolepanel", description="ロールパネルを管理")
    @app_commands.describe(
        action="実行するアクション",
        role="対象のロール",
        emoji="ロールに対応する絵文字",
        color="パネルの色 (#RRGGBB)",
        title="パネルのタイトル"
    )
    async def rolepanel(
        self,
        interaction: discord.Interaction,
        action: str,
        role: Optional[discord.Role] = None,
        emoji: Optional[str] = None,
        color: Optional[str] = None,
        title: Optional[str] = None
    ):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("このコマンドは管理者のみ使用できます。", ephemeral=True)
            return

        if action == "create":
            if not all([role, emoji]):
                await interaction.response.send_message("ロールと絵文字を指定してください。", ephemeral=True)
                return

            panel_id = str(len(self.panels) + 1)
            self.panels[panel_id] = {
                'roles': [{
                    'id': role.id,
                    'emoji': emoji
                }],
                'color': int(color.lstrip('#'), 16) if color else 0x7289DA,
                'title': title or "ロール選択",
                'message_id': None
            }
            self.selected_panel = panel_id
            
            await self._update_panel(interaction)
            await interaction.response.send_message("ロールパネルを作成しました。", ephemeral=True)

        elif action == "add":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return

            if not all([role, emoji]):
                await interaction.response.send_message("ロールと絵文字を指定してください。", ephemeral=True)
                return

            panel = self.panels[self.selected_panel]
            panel['roles'].append({
                'id': role.id,
                'emoji': emoji
            })
            
            await self._update_panel(interaction)
            await interaction.response.send_message("ロールを追加しました。", ephemeral=True)

        elif action == "edit":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return

            panel = self.panels[self.selected_panel]
            if color:
                panel['color'] = int(color.lstrip('#'), 16)
            if title:
                panel['title'] = title
            
            await self._update_panel(interaction)
            await interaction.response.send_message("パネルを更新しました。", ephemeral=True)

        elif action == "remove":
            if not self.selected_panel or not role:
                await interaction.response.send_message("パネルとロールを指定してください。", ephemeral=True)
                return

            panel = self.panels[self.selected_panel]
            panel['roles'] = [r for r in panel['roles'] if r['id'] != role.id]
            
            await self._update_panel(interaction)
            await interaction.response.send_message("ロールを削除しました。", ephemeral=True)

        elif action == "copy":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return

            panel_id = str(len(self.panels) + 1)
            self.panels[panel_id] = self.panels[self.selected_panel].copy()
            self.panels[panel_id]['message_id'] = None
            self.selected_panel = panel_id
            
            await interaction.response.send_message("パネルをコピーしました。", ephemeral=True)

        elif action == "delete":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return

            del self.panels[self.selected_panel]
            self.selected_panel = None
            await interaction.response.send_message("パネルを削除しました。", ephemeral=True)

        elif action == "selected":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return

            panel = self.panels[self.selected_panel]
            if panel['message_id']:
                await interaction.response.send_message(f"現在のパネル: {panel['message_id']}", ephemeral=True)
            else:
                await interaction.response.send_message("パネルはまだ設置されていません。", ephemeral=True)

        elif action == "refresh":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return
            
            await self._update_panel(interaction)
            await interaction.response.send_message("パネルを更新しました。", ephemeral=True)

        elif action == "autoremove":
            if not self.selected_panel:
                await interaction.response.send_message("パネルが選択されていません。", ephemeral=True)
                return

            panel = self.panels[self.selected_panel]
            original_count = len(panel['roles'])
            panel['roles'] = [r for r in panel['roles'] if interaction.guild.get_role(r['id'])]
            removed_count = original_count - len(panel['roles'])
            
            await self._update_panel(interaction)
            await interaction.response.send_message(f"{removed_count}個の削除されたロールを除去しました。", ephemeral=True)

        elif action == "debug":
            bot_member = interaction.guild.get_member(self.bot.user.id)
            permissions = bot_member.guild_permissions
            
            debug_info = [
                f"管理者権限: {permissions.administrator}",
                f"ロール管理: {permissions.manage_roles}",
                f"メッセージ管理: {permissions.manage_messages}",
                f"絵文字表示: {permissions.use_external_emojis}",
                f"メッセージ送信: {permissions.send_messages}",
                f"埋め込み送信: {permissions.embed_links}"
            ]
            
            await interaction.response.send_message("\n".join(debug_info), ephemeral=True)

    async def _update_panel(self, interaction: discord.Interaction):
        panel = self.panels[self.selected_panel]
        
        embed = discord.Embed(
            title=panel['title'],
            description="下のボタンでロールを選択できます。",
            color=panel['color']
        )

        view = RolePanelView(panel['roles'])
        for role_data in panel['roles']:
            role = interaction.guild.get_role(role_data['id'])
            if role:
                button = Button(
                    label=role.name,
                    emoji=role_data['emoji'],
                    style=discord.ButtonStyle.primary,
                    custom_id=f"role_{role.id}"
                )
                button.callback = lambda i, r=role.id: view.handle_role(i, r, True)
                view.add_item(button)

        if panel['message_id']:
            try:
                message = await interaction.channel.fetch_message(panel['message_id'])
                await message.edit(embed=embed, view=view)
            except:
                message = await interaction.channel.send(embed=embed, view=view)
                panel['message_id'] = message.id
        else:
            message = await interaction.channel.send(embed=embed, view=view)
            panel['message_id'] = message.id

async def setup(bot: commands.Bot):
    await bot.add_cog(RolePanelCommands(bot))
