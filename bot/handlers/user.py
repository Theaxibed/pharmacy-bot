from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import os

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    webapp_url = os.getenv("WEBAPP_URL", "")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛒 Открыть каталог препаратов",
            web_app=WebAppInfo(url=webapp_url)
        )]
    ])
    
    await message.answer(
        f"👋 Привет, <b>{message.from_user.full_name}</b>!\n\n"
        "Здесь вы можете оформить заявку на препараты.\n"
        "Нажмите кнопку ниже, чтобы открыть каталог 👇",
        reply_markup=keyboard,
        parse_mode="HTML"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ <b>Как оформить заявку:</b>\n\n"
        "1. Нажмите /start и откройте каталог\n"
        "2. Выберите нужные препараты и укажите количество\n"
        "3. Нажмите «Оформить заявку»\n"
        "4. Укажите название учреждения и контактные данные\n"
        "5. Подтвердите — заявка отправлена!\n\n"
        "Остатки обновляются в реальном времени.\n"
        "Если препарат недоступен — кнопка заблокирована.",
        parse_mode="HTML"
    )
