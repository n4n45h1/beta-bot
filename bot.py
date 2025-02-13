import discord
from discord.ext import commands
import os
import re
import logging
import asyncio
import sys
from typing import Optional, Dict, List
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('discord')

class Bot(commands.Bot):
    def __init__(self):
        # Configure intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            case_insensitive=True,
            strip_after_prefix=True
        )

        # Initialize cogs list
        self.initial_extensions = [
            'cogs.filter_commands',
            'cogs.help_commands',
            'cogs.info_commands',
            'cogs.log_commands',
            'cogs.moderation_commands',
            'cogs.rolepanel_commands',
            'cogs.ticket_commands',
            'cogs.welcome_commands'
        ]

        # Initialize performance monitoring
        self.start_time = datetime.utcnow()
        self.command_usage = {}
        self.error_count = 0

    async def setup_hook(self):
        """Initialize bot settings and load extensions"""
        try:
            # Load extensions
            for extension in self.initial_extensions:
                try:
                    await self.load_extension(extension)
                    logger.info(f'✅ Loaded extension: {extension}')
                except Exception as e:
                    logger.error(f'❌ Failed to load extension {extension}: {e}')
                    self.error_count += 1

            # Sync commands
            await self.tree.sync()
            logger.info('🔄 Slash commands synced!')

        except Exception as e:
            logger.error(f'❌ Error in setup: {e}')
            self.error_count += 1

    async def on_ready(self):
        """Handle bot ready event"""
        try:
            logger.info(f'✨ Logged in as {self.user} (ID: {self.user.id})')
            logger.info(f'🌐 Connected to {len(self.guilds)} servers')
            logger.info('-------------------')

            # Set rich presence
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{len(self.guilds)} servers | /help"
            )
            await self.change_presence(
                status=discord.Status.online,
                activity=activity
            )

            # Start background tasks
            self.bg_task = self.loop.create_task(self.background_tasks())

        except Exception as e:
            logger.error(f'❌ Error in on_ready: {e}')
            self.error_count += 1

    async def background_tasks(self):
        """Run background maintenance tasks"""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                # Update presence every 5 minutes
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{len(self.guilds)} servers | /help"
                )
                await self.change_presence(
                    status=discord.Status.online,
                    activity=activity
                )

                # Log performance metrics
                uptime = datetime.utcnow() - self.start_time
                logger.info(f'📊 Uptime: {uptime}, Errors: {self.error_count}')

                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f'❌ Error in background task: {e}')
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def on_guild_join(self, guild: discord.Guild):
        """Handle bot joining a new server"""
        logger.info(f'🎉 Joined new guild: {guild.name} (ID: {guild.id})')
        
        # Update presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="n2ze | /help"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx, error):
        """Global error handler"""
        try:
            if isinstance(error, commands.CommandNotFound):
                return
            
            if isinstance(error, commands.MissingPermissions):
                await ctx.send("⚠️ このコマンドを実行する権限がありません。", ephemeral=True)
                return
            
            if isinstance(error, commands.BotMissingPermissions):
                await ctx.send("⚠️ BOTに必要な権限がありません。", ephemeral=True)
                return

            if isinstance(error, commands.MissingRequiredArgument):
                await ctx.send("⚠️ 必要な引数が不足しています。", ephemeral=True)
                return

            # Log unexpected errors
            self.error_count += 1
            logger.error(f'❌ Error in command {ctx.command}: {error}')
            await ctx.send(
                "🔧 エラーが発生しました。しばらく待ってから再試行してください。",
                ephemeral=True
            )

        except Exception as e:
            logger.error(f'❌ Error in error handler: {e}')

def main():
    """Main entry point for the bot"""
    try:
        # Load environment variables
        load_dotenv()
        TOKEN = os.getenv('DISCORD_TOKEN')
        
        if not TOKEN:
            logger.error('❌ DISCORD_TOKEN not found in environment variables')
            return

        # Create and run bot
        bot = Bot()
        
        logger.info('🚀 Starting bot...')
        bot.run(TOKEN, log_handler=None)

    except Exception as e:
        logger.error(f'❌ Critical error: {e}')
        sys.exit(1)

if __name__ == "__main__":
    main()
