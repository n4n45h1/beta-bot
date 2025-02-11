import os
import requests
from flask import Flask, request, redirect, url_for, session, render_template_string
from datetime import datetime
from dotenv import load_dotenv

# If needed, uncomment this line if you also use local .env in dev
# load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace_with_random_secret_key")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")
IPINFO_API_TOKEN = os.getenv("IPINFO_API_TOKEN", "")

# Simple in-memory store: "auth_records" to keep user’s data
auth_records = {}

# Basic HTML templates
success_template = """
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"><title>Verification Success</title></head>
  <body style="background-color:#f0fff0;">
    <h1>Success!</h1>
    <p>Your account has been verified. You may close this page or return to Discord.</p>
  </body>
</html>
"""

failed_template = """
<!DOCTYPE html>
<html>
  <head><meta charset="utf-8"><title>Verification Failed</title></head>
  <body style="background-color:#fff0f0;">
    <h1>Failed!</h1>
    <p>Unfortunately, we could not verify your account. Please check your Discord DM for details.</p>
  </body>
</html>
"""

@app.route("/")
def index():
    # Redirect user to Discord OAuth
    authorize_url = (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        "&scope=identify%20email"
    )
    return f'<a href="{authorize_url}">Start Discord OAuth</a>'

@app.route("/callback")
def callback():
    # Exchange code for Discord token
    code = request.args.get("code")
    if not code:
        return "No code provided by Discord.", 400

    data = {
        "client_id": DISCORD_CLIENT_ID,
        "client_secret": DISCORD_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": DISCORD_REDIRECT_URI,
        "scope": "identify email"
    }

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_resp = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
    if token_resp.status_code != 200:
        return "Failed to get token from Discord.", 400

    access_token = token_resp.json()["access_token"]
    # Get user info from Discord
    user_info = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    # Store in session
    session["discord_user_id"] = user_info["id"]
    session["discord_email"] = user_info.get("email", "unknown")

    return redirect(url_for("collect_info"))

@app.route("/collect_info")
def collect_info():
    # Emulate collecting IP, browser, OS from request headers
    user_agent = request.headers.get("User-Agent", "unknown")
    user_ip = request.remote_addr or "0.0.0.0"

    # Use ipinfo API to check for VPN/Proxy
    try:
        ipinfo_url = f"https://ipinfo.io/{user_ip}?token={IPINFO_API_TOKEN}"
        ipinfo_resp = requests.get(ipinfo_url, timeout=5)
        ip_data = ipinfo_resp.json() if ipinfo_resp.status_code == 200 else {}
    except Exception:
        ip_data = {}

    # Basic fields
    country = ip_data.get("country", "unknown")
    privacy_info = ip_data.get("privacy", {})
    is_proxy = privacy_info.get("proxy", False)
    is_vpn = privacy_info.get("vpn", False)
    is_tor = privacy_info.get("tor", False)
    # Some IPInfo variants use 'hosting' or 'relay' etc.
    vpn_or_proxy = any([is_proxy, is_vpn, is_tor])

    user_id = session.get("discord_user_id", "0")
    email = session.get("discord_email", "unknown")

    # Save to in-memory store
    record = {
        "user_id": user_id,
        "email": email,
        "ip": user_ip,
        "country": country,
        "vpn_or_proxy": vpn_or_proxy,
        "user_agent": user_agent,
        "timestamp": datetime.utcnow().isoformat()
    }
    auth_records[user_id] = record

    # Decide immediate outcome for the user’s web page
    if vpn_or_proxy:
        return render_template_string(failed_template)
    else:
        # The Discord bot will handle final checks (account age, repeated IP, etc.)
        return render_template_string(success_template)

def create_app():
    return app

if __name__ == "__main__":
    # For local usage. On Railway, you can use Gunicorn or direct run.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
