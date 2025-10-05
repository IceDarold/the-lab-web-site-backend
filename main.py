from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from aiogram import Bot, Dispatcher
from aiogram.types import Message, Update
from aiogram.filters import Command
from config import BOT_TOKEN, USER_IDS, WEBHOOK_URL, MODE, SUPABASE_URL, SUPABASE_ANON_KEY
from supabase import create_client
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
            error_msg = f"Failed to set webhook: {str(e)}"
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_error_to_admins_sync, error_msg)
    yield
    # Cleanup on shutdown
    if MODE == "PROD" and WEBHOOK_URL:
        try:
            await bot.delete_webhook()
        except Exception as e:
            error_msg = f"Failed to delete webhook: {str(e)}"
            import asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, send_error_to_admins_sync, error_msg)

app = FastAPI(lifespan=lifespan)

# Initialize Telegram Bot
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set")
bot = Bot(token=BOT_TOKEN)
bot_sender = Bot(token=BOT_TOKEN)  # Separate bot for sending messages
dp = Dispatcher()

# Initialize Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
security = HTTPBearer()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5137", "https://icedarold.github.io"],  # Vite dev server and production frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = f"Unhandled exception in {request.url.path}: {str(exc)}"
    # Send error to admins asynchronously
    import asyncio
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, send_error_to_admins_sync, error_msg)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# Telegram bot handlers
@dp.message(Command("start"))
async def start_command(message: Message):
    try:
        # Use sync requests to avoid event loop issues in serverless
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": message.chat.id,
            "text": "Привет! Я бот для уведомлений о новых заявках. Когда приходит новая заявка, я отправляю её данные администраторам."
        }
        response = requests.post(url, json=data)
        if response.status_code != 200:
            raise Exception(f"Telegram API error: {response.text}")
    except Exception as e:
        error_msg = f"Error in start_command: {str(e)}"
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_error_to_admins_sync, error_msg)

class Application(BaseModel):
    name: str
    telegram: str
    motivation: str

class UserAuth(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict

def get_current_user(credentials: str = Depends(security)):
    try:
        user = supabase.auth.get_user(credentials)
        return user.user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

def send_notification_to_users_sync(application):
    print(f"send_notification_to_users_sync called")
    telegram = application.telegram
    if not telegram.startswith('@'):
        telegram = f"@{telegram}"
    message = f"<b>Новая заявка</b>\n\n<b>Имя:</b> {application.name}\n<b>Telegram:</b> {telegram}\n<b>Мотивация:</b> {application.motivation}"
    print(f"USER_IDS: {USER_IDS}, len: {len(USER_IDS)}")
    for user_id in USER_IDS:
        print(f"Sending to {user_id}")
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {"chat_id": user_id, "text": message, "parse_mode": "HTML"}
            response = requests.post(url, json=data)
            if response.status_code == 200:
                print(f"Message sent successfully to {user_id}")
            else:
                print(f"Failed to send message to {user_id}: {response.text}")
        except Exception as e:
            print(f"Failed to send message to {user_id}: {e}")

def send_error_to_admins_sync(error_message):
    """Send error message to all admin users via Telegram"""
    print(f"Sending error to admins: {error_message}")
    for user_id in USER_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {"chat_id": user_id, "text": f"<b>🚨 Ошибка в приложении</b>\n\n{error_message}", "parse_mode": "HTML"}
            response = requests.post(url, json=data)
            if response.status_code != 200:
                print(f"Failed to send error to {user_id}: {response.text}")
        except Exception as e:
            print(f"Failed to send error to {user_id}: {e}")

@app.post("/auth/register")
async def register(user: UserAuth):
   try:
       response = supabase.auth.sign_up({"email": user.email, "password": user.password})
       return {"message": "User registered", "user": response.user.dict() if response.user else None}
   except Exception as e:
       raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login", response_model=TokenResponse)
async def login(user: UserAuth):
   try:
       response = supabase.auth.sign_in_with_password({"email": user.email, "password": user.password})
       return {
           "access_token": response.session.access_token,
           "refresh_token": response.session.refresh_token,
           "user": response.user.dict()
       }
   except Exception as e:
       raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/auth/me")
async def me(current_user = Depends(get_current_user)):
   return current_user

@app.post("/webhook")
async def telegram_webhook(update: Update):
    try:
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        error_msg = f"Error in telegram_webhook: {str(e)}"
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_error_to_admins_sync, error_msg)
        return {"ok": False, "error": "Internal error"}

@app.post("/api/applications")
async def submit_application(application: Application):
    print(f"Received application: {application.model_dump()}")
    # Save to Supabase
    try:
        supabase.table("applications").insert({"name": application.name, "telegram": application.telegram, "motivation": application.motivation}).execute()
    except Exception as e:
        error_msg = f"Failed to save to database: {str(e)}"
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_error_to_admins_sync, error_msg)
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