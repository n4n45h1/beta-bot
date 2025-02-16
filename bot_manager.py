import discord
from typing import Optional

class BotManager:
    def __init__(self):
        self.status_message = "n2ze | werewolfbot.netlify.app"
        self.current_activity: Optional[discord.Activity] = None
        self.current_status: discord.Status = discord.Status.online

    async def update_status(self, client: discord.Client):
        """ボットのステータスを更新"""
        try:
            activity = discord.Game(name=self.status_message)
            await client.change_presence(
                activity=activity,
                status=self.current_status
            )
            self.current_activity = activity
        except Exception as e:
            print(f"Error updating bot status: {str(e)}")

    def get_current_activity(self) -> Optional[discord.Activity]:
        """現在のアクティビティを取得"""
        return self.current_activity

    def get_current_status(self) -> discord.Status:
        """現在のステータスを取得"""
        return self.current_status

    def set_status_message(self, message: str):
        """ステータスメッセージを設定"""
        self.status_message = message
