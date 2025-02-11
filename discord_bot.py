import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta

# If you use local .env in dev, uncomment:
# from dotenv import load_dotenv
# load_dotenv()

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
TARGET_GUILD_ID = int(os.getenv("TARGET_GUILD_ID", "0"))

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents)

# Store log channels for verification
verification_log_channels = {}

# Track IP usage: ip -> list of (user_id, timestamp)
recent_ip_usage = {}
# Store known user creation times, updated on member join or as needed
user_account_creation = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_member_join(member):
    user_account_creation[member.id] = member.created_at

@bot.command()
async def verify(ctx, role: discord.Role):
    """
    Usage: .verify @role
    Sends an embed with instructions or link to complete OAuth.
    """
    embed = discord.Embed(
        title="Discord Verification",
        description=(
            "Please visit the site below to verify.\n"
            "Once completed, you’ll see a success or failure page.\n"
            "The bot will confirm your account and (if all checks pass) assign your role."
        ),
        color=discord.Color.blue()
    )
    embed.add_field(name="Role to be assigned on success", value=role.mention, inline=False)

    # Replace "https://your-app.onrender.com" with your Railway domain or custom domain
    verify_link = "https://beta-authsystem.up.railway.app"
    embed.add_field(name="Verification Link", value=f"[Click here]({verify_link})", inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def log(ctx, action: str, channel: discord.TextChannel = None):
    """
    Usage:
    .log set #channel => sets verification log channel
    .log unset => unsets verification log channel
    """
    if action.lower() == "set" and channel is not None:
        verification_log_channels[ctx.guild.id] = channel.id
        await ctx.send(f"Verification log channel set to {channel.mention}")
    elif action.lower() == "unset":
        if ctx.guild.id in verification_log_channels:
            del verification_log_channels[ctx.guild.id]
            await ctx.send("Verification log channel unset.")
        else:
            await ctx.send("No verification log channel was set.")
    else:
        await ctx.send("Usage: .log set #channel OR .log unset")

async def send_verification_log(guild, user, data, success: bool):
    """
    Send an embed to the log channel if defined.
    """
    if guild.id not in verification_log_channels:
        return

    channel_id = verification_log_channels[guild.id]
    channel = bot.get_channel(channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title="Verification Log",
        color=discord.Color.green() if success else discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.set_author(name=str(user), icon_url=user.avatar_url if user.avatar else "")
    embed.add_field(name="User ID", value=str(user.id), inline=False)
    embed.add_field(name="Username", value=user.name, inline=False)
    embed.add_field(name="Email", value=data.get("email", "unknown"), inline=False)
    embed.add_field(name="Created At", value=str(user.created_at), inline=False)
    embed.add_field(name="IP", value=data.get("ip", "N/A"), inline=False)
    embed.add_field(name="Country", value=data.get("country", "unknown"), inline=False)
    embed.add_field(name="VPN/Proxy", value=str(data.get("vpn_or_proxy", False)), inline=False)
    embed.add_field(name="Status", value="Success" if success else "Failed", inline=False)
    await channel.send(embed=embed)

@bot.event
async def on_message(message):
    """
    Here we can simulate or trigger final verification checks after the user
    completes the web flow. In a real prod system, you'd likely have the web
    server send a direct request to the bot or to a DB. For demonstration,
    we assume a manual or simulated approach using .complete_verify.
    
    Usage example:
    .complete_verify <user_id> <email> <ip> <country> <vpn_flag>,
    e.g. .complete_verify 123456789 "someone@example.com" 8.8.8.8 "JP" False
    """
    if message.author == bot.user:
        return
    
    if message.content.startswith(".complete_verify"):
        try:
            # Example format with 5 args
            # .complete_verify user_id email ip country vpn_or_proxy
            parts = message.content.split(maxsplit=5)
            if len(parts) != 6:
                await message.channel.send("Invalid format. Use .complete_verify user_id email ip country vpn_bool")
                return

            _, user_id_str, email_str, ip_str, country_str, vpn_str = parts
            user_id = int(user_id_str)
            vpn_flag = vpn_str.lower() in ["true", "1", "yes", "on"]
            
            guild = bot.get_guild(TARGET_GUILD_ID)
            if not guild:
                await message.channel.send("Guild not found or TARGET_GUILD_ID not set.")
                return

            user = guild.get_member(user_id)
            if not user:
                await message.channel.send("User not found in the guild.")
                return

            data = {
                "email": email_str.strip('"'),
                "ip": ip_str,
                "country": country_str,
                "vpn_or_proxy": vpn_flag
            }

            # 1) VPN/Proxy check
            if vpn_flag:
                await user.send(f"@{user.name}、vpn,proxyを外してから来い")
                await send_verification_log(guild, user, data, success=False)
                return

            # 2) If not JP => partial check for account age
            account_age_days = (datetime.utcnow() - user.created_at).days
            if country_str != "JP":
                if account_age_days < 3:
                    await user.send(
                        f"@{user.name}、あなたのアカウントは新しすぎるので認証されませんでした、"
                        "後日サイド認証を行ってください。"
                    )
                    await send_verification_log(guild, user, data, success=False)
                    return

            # 3) Duplicate IP check within 1 week
            now = datetime.utcnow()
            # Remove old logs older than 7 days
            for ip, usage_list in list(recent_ip_usage.items()):
                new_list = [(uid, ts) for (uid, ts) in usage_list if (now - ts).days < 7]
                if new_list:
                    recent_ip_usage[ip] = new_list
                else:
                    del recent_ip_usage[ip]

            # Check for existing usage on the same IP
            if ip_str not in recent_ip_usage:
                recent_ip_usage[ip_str] = []
            else:
                for (logged_user_id, log_time) in recent_ip_usage[ip_str]:
                    # If we have the same IP used by a different user in the last 7 days
                    if logged_user_id != user.id and (now - log_time).days < 7:
                        # If used in less than 24 hours, ban
                        if (now - log_time) < timedelta(days=1):
                            await user.ban(reason="Duplicate account usage from same IP within 24 hours.")
                            await user.send(
                                f"@{user.name}の本垢、複垢と見られるものが検出されました。"
                                f"検出アカウント:@{user.name}、もし何かの間違いであれば@adminまで連絡してください。"
                            )
                            await send_verification_log(guild, user, data, success=False)
                            return
                        else:
                            # Over 24 hours but still within a week => deny verification
                            await user.send(
                                f"@{user.name}、同じIPで1週間以内に別の認証がありました。認証できません。"
                            )
                            await send_verification_log(guild, user, data, success=False)
                            return

            # If we reach here, user passes all checks => assign a role
            # Example role name "Verified"
            role_to_assign = None
            for r in guild.roles:
                if r.name.lower() == "verified":
                    role_to_assign = r
                    break

            if role_to_assign:
                await user.add_roles(role_to_assign, reason="Verification success")
            
            # Log success
            await send_verification_log(guild, user, data, success=True)
            # Track usage
            recent_ip_usage[ip_str].append((user.id, now))
            
            await message.channel.send(f"User <@{user.id}> verified successfully.")
        except Exception as ex:
            await message.channel.send(f"Error: {ex}")

    await bot.process_commands(message)

bot.run(DISCORD_BOT_TOKEN)
