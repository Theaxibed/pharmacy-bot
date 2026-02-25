"""
Единая точка входа: FastAPI + Telegram Bot (webhook)
"""
import asyncio
import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from db.models import init_db
from api.routes.products import router as products_router
from api.routes.orders import router as orders_router
from bot.main import bot, dp, setup_bot, process_update

logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", "")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Инициализация БД
    await init_db()
    
    # Настройка бота
    await setup_bot()
    
    # Установка webhook
    if WEBAPP_URL:
        webhook_url = f"{WEBAPP_URL}/webhook"
        await bot.set_webhook(webhook_url)
        logger.info(f"Webhook установлен: {webhook_url}")
    
    yield
    
    await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(title="Pharmacy Bot", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API роуты
app.include_router(products_router)
app.include_router(orders_router)


# Webhook endpoint для Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    await process_update(data)
    return {"ok": True}


@app.get("/health")
async def health():
    return {"status": "ok"}


# Фронтенд Mini App
if os.path.exists("frontend"):
    app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
