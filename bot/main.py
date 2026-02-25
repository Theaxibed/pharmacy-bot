import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from fastapi import Request
from db.models import AsyncSessionLocal

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


async def setup_bot():
    from bot.handlers import user, admin
    
    # Middleware для инжекта БД в хэндлеры
    from aiogram import BaseMiddleware
    from typing import Callable, Dict, Any, Awaitable
    
    class DbMiddleware(BaseMiddleware):
        async def __call__(self, handler: Callable, event: Any, data: Dict[str, Any]) -> Any:
            async with AsyncSessionLocal() as session:
                data["db"] = session
                return await handler(event, data)
    
    dp.message.middleware(DbMiddleware())
    dp.include_router(user.router)
    dp.include_router(admin.router)


async def start_polling():
    """Запуск в режиме polling (для локальной разработки)"""
    await setup_bot()
    logger.info("Bot started (polling mode)")
    await dp.start_polling(bot)


async def process_update(update_data: dict):
    """Обработка одного update (для webhook режима)"""
    update = Update.model_validate(update_data)
    await dp.feed_update(bot, update)


if __name__ == "__main__":
    asyncio.run(start_polling())
