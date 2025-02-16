import aiosqlite
from typing import Optional, List, Dict, Any
import json

class DatabaseManager:
    def __init__(self):
        self.db_path = "werewolf.db"

    async def initialize(self):
        """データベースの初期化"""
        async with aiosqlite.connect(self.db_path) as db:
            # ゲーム情報テーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS games (
                    channel_id INTEGER PRIMARY KEY,
                    creator_id INTEGER NOT NULL,
                    game_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    settings TEXT
                )
            """)

            # プレイヤー情報テーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER,
                    channel_id INTEGER,
                    role TEXT,
                    is_alive BOOLEAN DEFAULT TRUE,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, channel_id),
                    FOREIGN KEY (channel_id) REFERENCES games(channel_id)
                )
            """)

            # ゲームログテーブル
            await db.execute("""
                CREATE TABLE IF NOT EXISTS game_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    action_type TEXT NOT NULL,
                    action_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES games(channel_id)
                )
            """)

            await db.commit()

    async def create_game(self, channel_id: int, creator_id: int, game_name: str, settings: Dict[str, Any]) -> bool:
        """新しいゲームをデータベースに作成"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO games (channel_id, creator_id, game_name, status, settings) VALUES (?, ?, ?, ?, ?)",
                    (channel_id, creator_id, game_name, "WAITING", json.dumps(settings))
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"Error creating game: {str(e)}")
            return False

    async def add_player(self, user_id: int, channel_id: int, role: Optional[str] = None) -> bool:
        """プレイヤーをゲームに追加"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO players (user_id, channel_id, role) VALUES (?, ?, ?)",
                    (user_id, channel_id, role)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"Error adding player: {str(e)}")
            return False

    async def update_game_status(self, channel_id: int, status: str) -> bool:
        """ゲームのステータスを更新"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE games SET status = ? WHERE channel_id = ?",
                    (status, channel_id)
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"Error updating game status: {str(e)}")
            return False

    async def add_game_log(self, channel_id: int, action_type: str, action_data: Dict[str, Any]) -> bool:
        """ゲームログを追加"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO game_logs (channel_id, action_type, action_data) VALUES (?, ?, ?)",
                    (channel_id, action_type, json.dumps(action_data))
                )
                await db.commit()
            return True
        except Exception as e:
            print(f"Error adding game log: {str(e)}")
            return False

    async def get_game_logs(self, channel_id: int) -> List[Dict[str, Any]]:
        """ゲームのログを取得"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    "SELECT * FROM game_logs WHERE channel_id = ? ORDER BY created_at",
                    (channel_id,)
                ) as cursor:
                    logs = await cursor.fetchall()
                    return [
                        {
                            "id": log["id"],
                            "action_type": log["action_type"],
                            "action_data": json.loads(log["action_data"]),
                            "created_at": log["created_at"]
                        }
                        for log in logs
                    ]
        except Exception as e:
            print(f"Error getting game logs: {str(e)}")
            return []

    async def cleanup_old_games(self, days_old: int = 7):
        """古いゲーム記録を削除"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM game_logs 
                    WHERE channel_id IN (
                        SELECT channel_id 
                        FROM games 
                        WHERE created_at < datetime('now', ?)
                    )
                """, (f'-{days_old} days',))
                
                await db.execute("""
                    DELETE FROM players 
                    WHERE channel_id IN (
                        SELECT channel_id 
                        FROM games 
                        WHERE created_at < datetime('now', ?)
                    )
                """, (f'-{days_old} days',))
                
                await db.execute("""
                    DELETE FROM games 
                    WHERE created_at < datetime('now', ?)
                """, (f'-{days_old} days',))
                
                await db.commit()
        except Exception as e:
            print(f"Error cleaning up old games: {str(e)}")
