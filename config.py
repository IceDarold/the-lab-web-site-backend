import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Set in environment variables
USER_IDS_STR = os.getenv("USER_IDS", "")  # Comma-separated list, e.g., "123,456"
USER_IDS = [int(uid.strip()) for uid in USER_IDS_STR.split(",") if uid.strip()]
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Set in environment variables
MODE = os.getenv("MODE", "DEV")  # DEV for polling, PROD for webhooks