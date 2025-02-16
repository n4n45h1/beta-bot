import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from game_manager import GameState, GamePhase, Role
from message_manager import MessageManager
from typing import Dict, Optional

load_dotenv()

class WerewolfBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="/", intents=intents)
        self.games: Dict[int, GameState] = {}

    async def setup_hook(self):
        await self.tree.sync()

class GameSettingsView(discord.ui.View):
    def __init__(self, game_state: GameState):
        super().__init__(timeout=None)
        self.game_state = game_state

    @discord.ui.button(label="参加人数設定", style=discord.ButtonStyle.primary)
    async def set_players(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game_state.creator_id:
            await interaction.response.send_message("ゲームの作成者のみが設定を変更できます。", ephemeral=True)
            return

        modal = PlayerCountModal(self.game_state)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="参加", style=discord.ButtonStyle.green)
    async def join_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.game_state.can_player_join(interaction.user.id):
            await interaction.response.send_message(
                "このゲームに参加できません。以下の理由が考えられます：\n"
                "- 参加が禁止されている\n"
                "- 参加可能なユーザーリストに含まれていない\n"
                "- ゲームの参加人数が上限に達している",
                ephemeral=True
            )
            return

        if interaction.user.id not in self.game_state.players:
            self.game_state.players[interaction.user.id] = PlayerState(
                member_id=interaction.user.id
            )
            await interaction.response.send_message("ゲームに参加しました！", ephemeral=True)
            
            # 参加者数の更新を表示
            await interaction.channel.send(
                f"現在の参加者数: {len(self.game_state.players)}/{self.game_state.max_players}"
            )
        else:
            await interaction.response.send_message("すでにゲームに参加しています。", ephemeral=True)

class PlayerCountModal(discord.ui.Modal):
    def __init__(self, game_state: GameState):
        super().__init__(title="参加人数設定")
        self.game_state = game_state
        
        self.max_players = discord.ui.TextInput(
            label="最大参加人数",
            placeholder="4-20の間で入力してください",
            default=str(game_state.max_players),
            min_length=1,
            max_length=2
        )
        self.add_item(self.max_players)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            max_players = int(self.max_players.value)
            if 4 <= max_players <= 20:
                self.game_state.max_players = max_players
                await interaction.response.send_message(
                    f"最大参加人数を{max_players}人に設定しました。",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "参加人数は4-20の間で設定してください。",
                    ephemeral=True
                )
        except ValueError:
            await interaction.response.send_message(
                "正しい数値を入力してください。",
                ephemeral=True
            )

class VoteView(discord.ui.View):
    def __init__(self, game_state: GameState):
        super().__init__(timeout=60)
        self.game_state = game_state
        self.add_vote_buttons()

    def add_vote_buttons(self):
        alive_players = self.game_state.get_alive_players()
        for i, player_id in enumerate(alive_players):
            button = discord.ui.Button(
                label=f"{i+1}",
                custom_id=f"vote_{player_id}",
                style=discord.ButtonStyle.primary
            )
            button.callback = self.vote_callback
            self.add_item(button)

    async def vote_callback(self, interaction: discord.Interaction):
        if not interaction.user.id in self.game_state.players:
            await interaction.response.send_message("ゲームに参加していません。", ephemeral=True)
            return

        if not self.game_state.players[interaction.user.id].is_alive:
            await interaction.response.send_message("死亡したプレイヤーは投票できません。", ephemeral=True)
            return

        if self.game_state.players[interaction.user.id].vote_cast:
            await interaction.response.send_message("すでに投票済みです。", ephemeral=True)
            return

        target_id = int(interaction.custom_id.split("_")[1])
        self.game_state.votes[interaction.user.id] = target_id
        self.game_state.players[interaction.user.id].vote_cast = True
        
        await interaction.response.send_message(f"<@{target_id}> に投票しました。", ephemeral=True)

class NightActionView(discord.ui.View):
    def __init__(self, game_state: GameState, player_id: int):
        super().__init__(timeout=60)
        self.game_state = game_state
        self.player_id = player_id
        self.add_action_buttons()

    def add_action_buttons(self):
        alive_players = [
            pid for pid in self.game_state.get_alive_players()
            if pid != self.player_id
        ]
        for i, target_id in enumerate(alive_players):
            button = discord.ui.Button(
                label=f"{i+1}",
                custom_id=f"action_{target_id}",
                style=discord.ButtonStyle.primary
            )
            button.callback = self.action_callback
            self.add_item(button)

    async def action_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.player_id:
            await interaction.response.send_message("このアクションは実行できません。", ephemeral=True)
            return

        if self.game_state.players[self.player_id].action_performed:
            await interaction.response.send_message("すでにアクションを実行済みです。", ephemeral=True)
            return

        target_id = int(interaction.custom_id.split("_")[1])
        player = self.game_state.players[self.player_id]
        
        # 狩人の場合、同じ対象を連続で守れない
        if (player.role == Role.GUARD and 
            player.last_action_target == target_id and 
            player.last_action_day == self.game_state.day - 1):
            await interaction.response.send_message(
                "同じ対象を連続で守ることはできません。",
                ephemeral=True
            )
            return

        self.game_state.night_actions[self.player_id] = target_id
        self.game_state.players[self.player_id].action_performed = True
        
        await interaction.response.send_message(f"アクションを実行しました。", ephemeral=True)

@bot.event
async def on_ready():
    print(f"{bot.user} としてログインしました")

@bot.tree.command(name="werewolf", description="人狼ゲームを作成します")
async def create_werewolf(interaction: discord.Interaction):
    # カテゴリーの作成/取得
    category = discord.utils.get(interaction.guild.categories, name="Werewolf")
    if not category:
        category = await interaction.guild.create_category("Werewolf")

    # チャンネル名の設定
    channel_name = f"{interaction.user.name}の人狼"
    
    # テキストチャンネルの作成
    text_channel = await interaction.guild.create_text_channel(
        channel_name,
        category=category
    )
    
    # ボイスチャンネルの作成
    voice_channel = await interaction.guild.create_voice_channel(
        channel_name,
        category=category
    )
    
    # ゲームインスタンスの作成
    game_state = GameState(interaction.user.id, text_channel.id)
    game_state.text_channel_id = text_channel.id
    game_state.voice_channel_id = voice_channel.id
    game_state.game_name = channel_name
    bot.games[text_channel.id] = game_state
    
    # 設定用の埋め込みメッセージを作成
    embed = MessageManager.create_game_settings_embed()
    view = GameSettingsView(game_state)
    
    await text_channel.send(embed=embed, view=view)
    await interaction.response.send_message(
        f"人狼ゲームを作成しました！ {text_channel.mention} で設定してください。",
        ephemeral=True
    )

@bot.tree.command(name="start", description="人狼ゲームを開始します")
async def start_game(interaction: discord.Interaction):
    game_state = bot.games.get(interaction.channel.id)
    if not game_state:
        await interaction.response.send_message(
            "このチャンネルでゲームは作成されていません。",
            ephemeral=True
        )
        return
        
    if interaction.user.id != game_state.creator_id:
        await interaction.response.send_message(
            "ゲームの作成者のみがゲームを開始できます。",
            ephemeral=True
        )
        return

    if not game_state.is_ready_to_start():
        # 参加人数が足りない場合の処理
        view = StartGameConfirmView(game_state)
        await interaction.response.send_message(
            f"現在の参加人数が不足しています（{len(game_state.players)}/{game_state.min_players}人）\n"
            "どうしますか？",
            view=view,
            ephemeral=True
        )
        return

    await start_game_process(interaction, game_state)

async def start_game_process(interaction: discord.Interaction, game_state: GameState):
    if not game_state.calculate_roles():
        await interaction.response.send_message(
            "プレイヤーが足りません（最低4人必要です）。",
            ephemeral=True
        )
        return

    # ゲーム開始処理
    game_state.phase = GamePhase.NIGHT
    game_state.started_at = datetime.now()
    channel = interaction.channel
    
    # 役職の通知
    for player_id in game_state.players:
        member = interaction.guild.get_member(player_id)
        if member:
            embed = MessageManager.create_role_embed(player_id, game_state)
            try:
                await member.send(embed=embed)
            except discord.Forbidden:
                await channel.send(
                    f"{member.mention} にDMを送信できませんでした。",
                    ephemeral=True
                )

    # チャンネルの設定変更
    await channel.purge()
    
    # 参加者のみがアクセスできるように権限を設定
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.guild.me: discord.PermissionOverwrite(read_messages=True)
    }
    for player_id in game_state.players:
        member = interaction.guild.get_member(player_id)
        if member:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True)
    
    await channel.edit(overwrites=overwrites)
    
    # ゲーム開始メッセージ
    await channel.send("ゲームを開始します！各プレイヤーにDMで役職が通知されました。")
    
    # ゲームループの開始
    asyncio.create_task(game_loop(game_state, channel))

class StartGameConfirmView(discord.ui.View):
    def __init__(self, game_state: GameState):
        super().__init__(timeout=60)
        self.game_state = game_state

    @discord.ui.button(label="このまま開始", style=discord.ButtonStyle.danger)
    async def force_start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game_state.creator_id:
            await interaction.response.send_message("ゲームの作成者のみが開始できます。", ephemeral=True)
            return
        await start_game_process(interaction, self.game_state)

    @discord.ui.button(label="募集を続ける", style=discord.ButtonStyle.primary)
    async def continue_recruitment(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.game_state.creator_id:
            await interaction.response.send_message("ゲームの作成者のみが設定を変更できます。", ephemeral=True)
            return
        await interaction.response.send_message("募集を続けます。", ephemeral=True)

async def game_loop(game_state: GameState, channel: discord.TextChannel):
    while True:
        # ゲーム終了チェック
        is_over, winner = game_state.is_game_over()
        if is_over:
            embed = MessageManager.create_game_result_embed(game_state, winner)
            await channel.send(embed=embed)
            break

        if game_state.phase == GamePhase.NIGHT:
            # 夜フェーズの処理
            await handle_night_phase(game_state, channel)
            game_state.phase = GamePhase.DAY
            
        elif game_state.phase == GamePhase.DAY:
            # 昼フェーズの処理
            await handle_day_phase(game_state, channel)
            game_state.phase = GamePhase.VOTE
            
        elif game_state.phase == GamePhase.VOTE:
            # 投票フェーズの処理
            await handle_vote_phase(game_state, channel)
            game_state.phase = GamePhase.NIGHT
            game_state.day += 1

async def handle_night_phase(game_state: GameState, channel: discord.TextChannel):
    await channel.send(f"=== {game_state.day}日目の夜 ===")
    
    # 夜のアクションを処理
    for player_id, player in game_state.players.items():
        if not player.is_alive:
            continue
            
        if player.role in [Role.WEREWOLF, Role.SEER, Role.GUARD]:
            member = channel.guild.get_member(player_id)
            if member:
                embed = MessageManager.create_night_action_embed(player_id, game_state)
                view = NightActionView(game_state, player_id)
                try:
                    await member.send(embed=embed, view=view)
                except discord.Forbidden:
                    continue

    # アクション待機時間
    await asyncio.sleep(60)  # 1分待機
    
    # 夜のアクションの結果を処理
    killed_player, messages = game_state.handle_night_actions()
    
    # 結果を通知
    if killed_player:
        member = channel.guild.get_member(killed_player)
        if member:
            await channel.send(f"{member.mention} が殺害されました。")

    # 各プレイヤーへの結果通知
    for msg_type, actor_id, target_id, role in messages:
        actor = channel.guild.get_member(actor_id)
        if not actor:
            continue

        if msg_type == "seer":
            target = channel.guild.get_member(target_id)
            if target and role:
                embed = discord.Embed(
                    title="占い結果",
                    description=f"{target.mention} の役職は {role.value} でした。",
                    color=discord.Color.gold()
                )
                try:
                    await actor.send(embed=embed)
                except discord.Forbidden:
                    continue

        elif msg_type == "medium":
            target = channel.guild.get_member(target_id)
            if target and role:
                embed = discord.Embed(
                    title="霊媒結果",
                    description=f"処刑された {target.mention} の役職は {role.value} でした。",
                    color=discord.Color.purple()
                )
                try:
                    await actor.send(embed=embed)
                except discord.Forbidden:
                    continue

async def handle_day_phase(game_state: GameState, channel: discord.TextChannel):
    await channel.send(f"=== {game_state.day}日目の昼 ===")
    
    # ステータス表示
    embed = MessageManager.create_game_status_embed(game_state)
    await channel.send(embed=embed)
    
    # 議論時間
    await asyncio.sleep(game_state.discussion_time_minutes * 60)

async def handle_vote_phase(game_state: GameState, channel: discord.TextChannel):
    await channel.send("=== 投票時間 ===")
    
    # 投票の実行
    embed = MessageManager.create_voting_embed(game_state)
    view = VoteView(game_state)
    await channel.send(embed=embed, view=view)
    
    # 投票待機時間
    await asyncio.sleep(60)  # 1分待機
    
    # 投票結果の処理
    eliminated_player = game_state.handle_voting()
    if eliminated_player:
        member = channel.guild.get_member(eliminated_player)
        if member:
            await channel.send(f"{member.mention} が追放されました。")
            # 追放されたプレイヤーの役職を全員に通知
            role = game_state.players[eliminated_player].role
            await channel.send(f"追放された {member.mention} の役職は {role.value} でした。")

@bot.tree.command(name="end", description="人狼ゲームを終了します")
async def end_game(interaction: discord.Interaction):
    game_state = bot.games.get(interaction.channel.id)
    if not game_state:
        await interaction.response.send_message(
            "このチャンネルでゲームは作成されていません。",
            ephemeral=True
        )
        return
        
    if interaction.user.id != game_state.creator_id:
        await interaction.response.send_message(
            "ゲームの作成者のみがゲームを終了できます。",
            ephemeral=True
        )
        return
    
    # チャンネルの削除
    category = interaction.channel.category
    for channel in category.channels:
        if channel.name == game_state.game_name:
            await channel.delete()
    
    # ゲームの削除
    del bot.games[interaction.channel.id]
    
    await interaction.response.send_message("ゲームを終了しました。", ephemeral=True)

@bot.tree.command(name="kick", description="プレイヤーをゲームからキックします")
async def kick_player(interaction: discord.Interaction, player: discord.Member):
    game_state = bot.games.get(interaction.channel.id)
    if not game_state:
        await interaction.response.send_message(
            "このチャンネルでゲームは作成されていません。",
            ephemeral=True
        )
        return
        
    if interaction.user.id != game_state.creator_id:
        await interaction.response.send_message(
            "ゲームの作成者のみがプレイヤーをキックできます。",
            ephemeral=True
        )
        return
    
    if player.id not in game_state.players:
        await interaction.response.send_message(
            "指定されたプレイヤーはゲームに参加していません。",
            ephemeral=True
        )
        return
    
    # プレイヤーの削除
    del game_state.players[player.id]
    game_state.banned_players.add(player.id)
    
    # チャンネルの権限を更新
    overwrites = interaction.channel.overwrites
    del overwrites[player]
    await interaction.channel.edit(overwrites=overwrites)
    
    await interaction.response.send_message(
        f"{player.mention} をゲームからキックしました。",
        ephemeral=True
    )

bot.ru
