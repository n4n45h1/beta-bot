import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="コマンドの使い方を表示")
    @app_commands.describe(
        command="詳細を表示するコマンド (省略可)"
    )
    async def help(
        self,
        interaction: discord.Interaction,
        command: Optional[str] = None
    ):
        if command:
            # 特定のコマンドのヘルプを表示
            if command == "rolepanel":
                embed = discord.Embed(
                    title="ロールパネルコマンド",
                    description="ボタンでロールを付与できるパネルを作成・管理します",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/rolepanel create",
                    value="新しいロールパネルを作成\n"
                          "```\n"
                          "role: 追加するロール\n"
                          "emoji: ロールに対応する絵文字\n"
                          "color: パネルの色 (#RRGGBB)\n"
                          "title: パネルのタイトル\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="/rolepanel add",
                    value="既存のパネルにロールを追加\n"
                          "```\n"
                          "role: 追加するロール\n"
                          "emoji: ロールに対応する絵文字\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="その他の操作",
                    value="```\n"
                          "edit: タイトルと色を変更\n"
                          "remove: ロールを削除\n"
                          "copy: パネルを複製\n"
                          "delete: パネルを削除\n"
                          "selected: 現在のパネルを表示\n"
                          "refresh: ロールを再適用\n"
                          "autoremove: 削除済みロールを除去\n"
                          "```",
                    inline=False
                )

            elif command == "filter":
                embed = discord.Embed(
                    title="フィルターコマンド",
                    description="不適切な投稿を自動的に管理します",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/filter word add",
                    value="禁止ワードを追加\n"
                          "```\n"
                          "word: 禁止する単語\n"
                          "penalty: 違反時の処罰\n"
                          "- kick: サーバーから追放\n"
                          "- ban: サーバーからBAN\n"
                          "- timeout: 一時的なミュート\n"
                          "timeout: タイムアウト時間（分）\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="URL制限",
                    value="```\n"
                          "/filter url-block true/false\n"
                          "URLの投稿を制限\n\n"
                          "/filter invite-url true/false\n"
                          "招待リンクの投稿を制限\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="その他の操作",
                    value="```\n"
                          "word remove: 禁止ワードを削除\n"
                          "word edit: 禁止ワードの設定を変更\n"
                          "word list: 禁止ワード一覧を表示\n"
                          "log: ログチャンネルを設定\n"
                          "```",
                    inline=False
                )

            elif command == "stat":
                embed = discord.Embed(
                    title="統計情報コマンド",
                    description="サーバーの統計情報を表示するチャンネルを作成",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/stat time",
                    value="現在時刻を表示するチャンネル\n"
                          "```\n"
                          "timezone: タイムゾーン\n"
                          "- UTC+/-n (例: UTC+9)\n"
                          "- 主要都市名 (例: Tokyo)\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="/stat day",
                    value="現在の日付を表示するチャンネル\n"
                          "```\n"
                          "timezone: タイムゾーン\n"
                          "- UTC+/-n (例: UTC+9)\n"
                          "- 主要都市名 (例: Tokyo)\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="メンバー統計",
                    value="```\n"
                          "/stat online_member\n"
                          "オンラインメンバー数を表示\n\n"
                          "/stat offline_member\n"
                          "オフラインメンバー数を表示\n\n"
                          "/stat member\n"
                          "総メンバー数を表示\n"
                          "```",
                    inline=False
                )

            elif command == "log":
                embed = discord.Embed(
                    title="ログコマンド",
                    description="サーバーのログを記録します",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/log",
                    value="ログチャンネルを設定\n"
                          "```\n"
                          "channel: ログを送信するチャンネル\n"
                          "action: add/remove\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="記録される項目",
                    value="```\n"
                          "- チャンネルの作成/削除/編集\n"
                          "- メッセージの編集/削除\n"
                          "- 絵文字の追加/削除/編集\n"
                          "- ロールの追加/削除/編集\n"
                          "- メンバーのロール変更\n"
                          "- メンバーの参加/退出\n"
                          "- タイムアウト/キック/BAN\n"
                          "```",
                    inline=False
                )

            elif command == "timeout":
                embed = discord.Embed(
                    title="タイムアウトコマンド",
                    description="メンバーのタイムアウトを管理します",
                    color=discord.Color.blue()
                )
                embed.add_field(
                    name="/timeout",
                    value="```\n"
                          "user: 対象ユーザー\n"
                          "action: 実行するアクション\n"
                          "time: タイムアウト期間\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="アクション一覧",
                    value="```\n"
                          "add: タイムアウトを追加\n"
                          "forever: 無期限タイムアウト\n"
                          "canceling: タイムアウトを解除\n"
                          "view: 現在の状態を表示\n"
                          "history: タイムアウト履歴\n"
                          "remove: タイムアウト期間を短縮\n"
                          "```",
                    inline=False
                )
                embed.add_field(
                    name="時間指定形式",
                    value="```\n"
                          "y: 年\n"
                          "m: 月\n"
                          "w: 週\n"
                          "d: 日\n"
                          "h: 時間\n"
                          "m: 分\n"
                          "s: 秒\n"
                          "例: 1d12h30m = 1日12時間30分\n"
                          "```",
                    inline=False
                )

            else:
                embed = discord.Embed(
                    title="エラー",
                    description="指定されたコマンドが見つかりません。",
                    color=discord.Color.red()
                )

        else:
            # コマンド一覧を表示
            embed = discord.Embed(
                title="使用可能なコマンド",
                description="詳細は `/help <コマンド名>` で確認できます",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🎭 ロール管理",
                value="```\n"
                      "/rolepanel - ロール付与パネルを作成\n"
                      "```",
                inline=False
            )
            embed.add_field(
                name="🛡️ モデレーション",
                value="```\n"
                      "/filter - コンテンツフィルターを設定\n"
                      "/timeout - タイムアウトを管理\n"
                      "/nick - ニックネームを変更\n"
                      "```",
                inline=False
            )
            embed.add_field(
                name="📊 統計情報",
                value="```\n"
                      "/stat - 統計情報チャンネルを作成\n"
                      "```",
                inline=False
            )
            embed.add_field(
                name="📝 ログ管理",
                value="```\n"
                      "/log - ログチャンネルを設定\n"
                      "```",
                inline=False
            )
            embed.add_field(
                name="ℹ️ 情報表示",
                value="```\n"
                      "/avatar - アバター画像を表示\n"
                      "/user_info - ユーザー情報を表示\n"
                      "/server_info - サーバー情報を表示\n"
                      "```",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCommands(bot))
