from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from aiogram.filters import Command
from config import BOT_TOKEN, USER_IDS, WEBHOOK_URL, MODE
import asyncio
import threading
import uvicorn
import requests

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set webhook on startup only in PROD mode
    if MODE == "PROD" and WEBHOOK_URL:
        try:
            await bot.set_webhook(WEBHOOK_URL)
        except Exception as e:
            print(f"Failed to set webhook: {e}")
    yield
    # Cleanup on shutdown
    if MODE == "PROD" and WEBHOOK_URL:
        try:
            await bot.delete_webhook()
        except Exception as e:
            print(f"Failed to delete webhook: {e}")

app = FastAPI(lifespan=lifespan)

# Initialize Telegram Bot
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")
bot = Bot(token=BOT_TOKEN)
bot_sender = Bot(token=BOT_TOKEN)  # Separate bot for sending messages
dp = Dispatcher()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5137", "https://icedarold.github.io"],  # Vite dev server and production frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram bot handlers
@dp.message(Command("start"))
async def start_command(message: Message):
    # Use sync requests to avoid event loop issues in serverless
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": message.chat.id,
        "text": "Привет! Я бот для уведомлений о новых заявках. Когда приходит новая заявка, я отправляю её данные администраторам."
    }
    requests.post(url, json=data)

class Application(BaseModel):
    name: str
    telegram: str
    motivation: str

def send_notification_to_users_sync(application):
    print(f"send_notification_to_users_sync called")
    telegram = application.telegram
    if not telegram.startswith('@'):
        telegram = f"@{telegram}"
    message = f"**Новая заявка**\n\\**Имя:** {application.name}\n**Telegram:** {telegram}\n**Мотивация:** {application.motivation}"
    print(f"USER_IDS: {USER_IDS}, len: {len(USER_IDS)}")
    for user_id in USER_IDS:
        print(f"Sending to {user_id}")
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {"chat_id": user_id, "text": message}
            response = requests.post(url, json=data)
            if response.status_code == 200:
                print(f"Message sent successfully to {user_id}")
            else:
                print(f"Failed to send message to {user_id}: {response.text}")
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

@app.post("/webhook")
async def telegram_webhook(update: Update):
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.post("/api/applications")
async def submit_application(application: Application):
    print(f"Received application: {application.model_dump()}")
    # Send notification to users synchronously
    send_notification_to_users_sync(application)
    return {"message": "Application received"}

# For local testing
if __name__ == "__main__":
    if MODE == "DEV":
        # Run both bot and FastAPI in DEV mode
        def run_bot():
            asyncio.run(dp.start_polling(bot))

        def run_api():
            uvicorn.run(app, host="0.0.0.0", port=8004)

        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        run_api()
    else:
        # Run FastAPI server for PROD
        uvicorn.run(app, host="0.0.0.0", port=8001)