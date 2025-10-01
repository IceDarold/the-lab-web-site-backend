from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from aiogram.filters import Command
from config import BOT_TOKEN, USER_IDS, WEBHOOK_URL, MODE
import asyncio

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Set webhook on startup only in PROD mode
    if MODE == "PROD" and WEBHOOK_URL:
        await bot.set_webhook(WEBHOOK_URL)
    yield
    # Cleanup on shutdown
    if MODE == "PROD" and WEBHOOK_URL:
        await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

# Initialize Telegram Bot
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://icedarold.github.io"],  # Vite dev server and production frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram bot handlers
@dp.message(Command("start"))
async def start_command(message: Message):
    await message.reply("Привет! Я бот для уведомлений о новых заявках. Когда приходит новая заявка, я отправляю её данные администраторам.")

class Application(BaseModel):
    name: str
    telegram: str
    motivation: str

async def send_notification_to_users(application: Application):
    message = f"Новая заявка:\nИмя: {application.name}\nTelegram: {application.telegram}\nМотивация: {application.motivation}"
    for user_id in USER_IDS:
        try:
            await bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

@app.post("/webhook")
async def telegram_webhook(update: Update):
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.post("/api/applications")
async def submit_application(application: Application):
    print(f"Received application: {application.model_dump()}")
    # Send notification to users
    asyncio.create_task(send_notification_to_users(application))
    return {"message": "Application received"}

# For local testing
if __name__ == "__main__":
    import uvicorn
    if MODE == "DEV":
        # Run bot with polling
        asyncio.run(dp.start_polling(bot))
    else:
        # Run FastAPI server for PROD
        uvicorn.run(app, host="0.0.0.0", port=8000)