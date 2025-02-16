import asyncio
from typing import Dict, Set
import aiosqlite

class UserManager:
    def __init__(self):
        self.user_games: Dict[int, Set[int]] = {}  # user_id -> set of channel_ids
        self.created_games: Dict[int, Set[int]] = {}  # user_id -> set of created channel_ids
        self.join_game_lock = asyncio.Lock()
        self.db_path = "werewolf.db"
        
        # データベースの初期化
        asyncio.create_task(self.initialize_database())

    async def initialize_database(self):
        """データベースの初期化"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_games (
                    user_id INTEGER,
                    channel_id INTEGER,
                    is_creator BOOLEAN,
                    PRIMARY KEY (user_id, channel_id)
                )
            """)
            await db.commit()

    async def can_create_game(self, user_id: int) -> bool:
        """ユーザーが新しいゲームを作成できるかチェック"""
        created_games = self.created_games.get(user_id, set())
        return len(created_games) < 2

    async def can_join_game(self, user_id: int) -> bool:
        """ユーザーが新しいゲームに参加できるかチェック"""
        joined_games = self.user_games.get(user_id, set())
        return len(joined_games) < 2

    async def add_created_game(self, user_id: int, channel_id: int) -> bool:
        """ユーザーの作成したゲームを記録"""
        try:
            if not await self.can_create_game(user_id):
                return False

            if user_id not in self.created_games:
                self.created_games[user_id] = set()
            self.created_games[user_id].add(channel_id)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO user_games (user_id, channel_id, is_creator) VALUES (?, ?, ?)",
                    (user_id, channel_id, True)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"Error in add_created_game: {str(e)}")
            return False

    async def add_game_participation(self, user_id: int) -> bool:
        """ユーザーのゲーム参加を記録"""
        try:
            if not await self.can_join_game(user_id):
                return False

            if user_id not in self.user_games:
                self.user_games[user_id] = set()
            self.user_games[user_id].add(channel_id)

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO user_games (user_id, channel_id, is_creator) VALUES (?, ?, ?)",
                    (user_id, channel_id, False)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"Error in add_game_participation: {str(e)}")
            return False

    async def remove_created_game(self, user_id: int, channel_id: int):
        """ユーザーの作成したゲームを削除"""
        try:
            if user_id in self.created_games:
                self.created_games[user_id].discard(channel_id)
                if not self.created_games[user_id]:
                    del self.created_games[user_id]

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM user_games WHERE user_id = ? AND channel_id = ? AND is_creator = ?",
                    (user_id, channel_id, True)
                )
                await db.commit()
        except Exception as e:
            print(f"Error in remove_created_game: {str(e)}")

    async def remove_game_participation(self, user_id: int):
        """ユーザーのゲーム参加を削除"""
        try:
            if user_id in self.user_games:
                self.user_games[user_id].discard(channel_id)
                if not self.user_games[user_id]:
                    del self.user_games[user_id]

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM user_games WHERE user_id = ? AND channel_id = ? AND is_creator = ?",
                    (user_id, channel_id, False)
                )
                await db.commit()
        except Exception as e:
            print(f"Error in remove_game_participation: {str(e)}")
