# Example Dockerfile for Railway
FROM python:3.9-slim

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Create app directory
WORKDIR /app

# Copy requirement file
COPY requirements.txt /app/

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY web_server.py /app/
COPY discord_bot.py /app/

# Expose Flask port (Railway will map the actual port)
EXPOSE 5000

# For demonstration, run both Gunicorn (Flask) and the Discord bot.
# In production, consider running them as separate services or processes.
CMD gunicorn --bind 0.0.0.0:$PORT web_server:app & python discord_bot.py
