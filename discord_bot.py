import os
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import requests

# 環境変数のロード
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
TARGET_GUILD_ID = int(os.getenv("TARGET_GUILD_ID", "0"))
FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix=".", intents=intents)

# ログチャンネルとIP使用状況の管理
verification_log_channels = {}
recent_ip_usage = {}
user_account_creation = {}

app = Flask(__name__)

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
    verify_link = "https://beta-authsystem.up.railway.app/"
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

@app.route("/verify", methods=["POST"])
def verify():
    data = request.json
    user_id = int(data["user_id"])
    email = data["email"]
    ip = data["ip"]
    country = data["country"]
    vpn_or_proxy = data["vpn_or_proxy"]

    guild = bot.get_guild(TARGET_GUILD_ID)
    if not guild:
        return jsonify({"error": "Guild not found or TARGET_GUILD_ID not set."}), 400

    user = guild.get_member(user_id)
    if not user:
        return jsonify({"error": "User not found in the guild."}), 400

    # 1) VPN/Proxy check
    if vpn_or_proxy:
        bot.loop.create_task(user.send(f"@{user.name}、vpn,proxyを外してから認証をしてください。"))
        bot.loop.create_task(send_verification_log(guild, user, data, success=False))
        return jsonify({"status": "failed", "reason": "vpn_or_proxy"}), 200

    # 2) If not JP => partial check for account age
    account_age_days = (datetime.utcnow() - user.created_at).days
    if country != "JP":
        if account_age_days < 3:
            bot.loop.create_task(user.send(
                f"@{user.name}、あなたのアカウントは新しすぎるので認証されませんでした、"
                "後日サイド認証を行ってください。"
            ))
            bot.loop.create_task(send_verification_log(guild, user, data, success=False))
            return jsonify({"status": "failed", "reason": "account_age"}), 200

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
    if ip not in recent_ip_usage:
        recent_ip_usage[ip] = []
    else:
        for (logged_user_id, log_time) in recent_ip_usage[ip]:
            # If we have the same IP used by a different user in the last 7 days
            if logged_user_id != user.id and (now - log_time).days < 7:
                # If used in less than 24 hours, ban
                if (now - log_time) < timedelta(days=1):
                    bot.loop.create_task(user.ban(reason="Duplicate account usage from same IP within 24 hours."))
                    bot.loop.create_task(user.send(
                        f"@{user.name}、複垢と見られるものが検出されました。"
                        f"検出アカウント:@{user.name}、もし何かの間違いであればn2zeまで連絡してください。"
                    ))
                    bot.loop.create_task(send_verification_log(guild, user, data, success=False))
                    return jsonify({"status": "failed", "reason": "duplicate_account"}), 200
                else:
                    # Over 24 hours but still within a week => deny verification
                    bot.loop.create_task(user.send(
                        f"@{user.name}、同じIPアドレスで1週間以内に別の認証がありました。認証できません。"
                    ))
                    bot.loop.create_task(send_verification_log(guild, user, data, success=False))
                    return jsonify({"status": "failed", "reason": "duplicate_ip"}), 200

    # If we reach here, user passes all checks => assign a role
    # Example role name "Verified"
    role_to_assign = None
    for r in guild.roles:
        if r.name.lower() == "verified":
            role_to_assign = r
            break

    if role_to_assign:
        bot.loop.create_task(user.add_roles(role_to_assign, reason="Verification success"))
    
    # Log success
    bot.loop.create_task(send_verification_log(guild, user, data, success=True))
    # Track usage
    recent_ip_usage[ip].append((user.id, now))
    
    return jsonify({"status": "success"}), 200

if __name__ == "__main__":
    bot.loop.create_task(bot.start(DISCORD_BOT_TOKEN))
    app.run(host="0.0.0.0", port=FLASK_PORT)
