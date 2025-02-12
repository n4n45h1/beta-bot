import discord
from discord.ext import commands
import os
import re
import logging
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('discord')

class Bot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.presences = True
        super().__init__(command_prefix='!', intents=intents)
        self.initial_extensions = [
            'cogs.filter_commands',
            'cogs.help_commands',
            'cogs.info_commands',
            'cogs.log_commands',
            'cogs.moderation_commands',
            'cogs.rolepanel_commands',
            'cogs.stats_commands',
            'cogs.ticket_commands'
        ]

    async def setup_hook(self):
        # Load all cogs
        for extension in self.initial_extensions:
            try:
                await self.load_extension(extension)
                logger.info(f'Loaded extension: {extension}')
            except Exception as e:
                logger.error(f'Failed to load extension {extension}: {e}')
        
        await self.tree.sync()
        logger.info('Slash commands synced!')

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')
        
        # Set rich presence
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name="n2ze | /help"
        )
        await self.change_presence(status=discord.Status.online, activity=activity)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("このコマンドを実行する権限がありません。", ephemeral=True)
            return
            
        logger.error(f'Error in command {ctx.command}: {error}')
        await ctx.send("エラーが発生しました。しばらく待ってから再試行してください。", ephemeral=True)

def main():
    # Load environment variables
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        logger.error('DISCORD_TOKEN not found in environment variables')
        return

    # Create and run bot
    bot = Bot()
    
    try:
        logger.info('Starting bot...')
        bot.run(TOKEN, log_handler=None)
    except Exception as e:
        logger.error(f'Failed to start bot: {e}')
        
if __name__ == "__main__":
    main()
