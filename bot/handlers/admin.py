from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession
from db import crud
import os

router = Router()

def is_admin(user_id: int) -> bool:
    admin_ids = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    return user_id in admin_ids


# ─── /addproduct Название | Описание | единица | остаток ────────────────────
@router.message(Command("addproduct"))
async def cmd_add_product(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")
    
    try:
        parts = message.text.split("|")
        # /addproduct Название | Описание | шт | 1000
        cmd_name = parts[0].replace("/addproduct", "").strip()
        description = parts[1].strip() if len(parts) > 1 else ""
        unit = parts[2].strip() if len(parts) > 2 else "шт"
        stock = int(parts[3].strip()) if len(parts) > 3 else 0
        
        product = await crud.create_product(db, cmd_name, description, unit, stock)
        await message.answer(
            f"✅ Препарат добавлен:\n"
            f"ID: <b>{product.id}</b>\n"
            f"Название: <b>{product.name}</b>\n"
            f"Единица: {product.unit}\n"
            f"Остаток: {product.stock}",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}\n\nФормат: /addproduct Название | Описание | шт | 1000")


# ─── /setstock 5 1500 ────────────────────────────────────────────────────────
@router.message(Command("setstock"))
async def cmd_set_stock(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")
    
    try:
        _, product_id, amount = message.text.split()
        product = await crud.update_stock(db, int(product_id), int(amount))
        await message.answer(f"✅ <b>{product.name}</b> — остаток установлен: {product.stock} {product.unit}", parse_mode="HTML")
    except:
        await message.answer("Формат: /setstock [id препарата] [количество]\nПример: /setstock 3 1500")


# ─── /addstock 5 500 ─────────────────────────────────────────────────────────
@router.message(Command("addstock"))
async def cmd_add_stock(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")
    
    try:
        _, product_id, amount = message.text.split()
        product = await crud.add_stock(db, int(product_id), int(amount))
        await message.answer(f"✅ <b>{product.name}</b> — добавлено {amount}, итого: {product.stock} {product.unit}", parse_mode="HTML")
    except:
        await message.answer("Формат: /addstock [id] [количество]\nПример: /addstock 3 500")


# ─── /products — список всех препаратов ──────────────────────────────────────
@router.message(Command("products"))
async def cmd_products(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")
    
    products = await crud.get_all_products(db)
    if not products:
        return await message.answer("Препаратов пока нет. Добавьте через /addproduct")
    
    text = "📋 <b>Список препаратов:</b>\n\n"
    for p in products:
        status = "✅" if p.stock > 0 else "❌"
        text += f"{status} ID <code>{p.id}</code> | <b>{p.name}</b>\n"
        text += f"   Остаток: {p.stock} {p.unit}"
        if p.limit_per_order:
            text += f" | Лимит/заявка: {p.limit_per_order}"
        text += "\n\n"
    
    await message.answer(text, parse_mode="HTML")


# ─── /setlimit 5 200 — лимит на одну заявку ──────────────────────────────────
@router.message(Command("setlimit"))
async def cmd_set_limit(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")
    
    try:
        _, product_id, limit = message.text.split()
        from sqlalchemy import update
        from db.models import Product, AsyncSessionLocal
        async with AsyncSessionLocal() as s:
            await s.execute(update(Product).where(Product.id == int(product_id)).values(limit_per_order=int(limit)))
            await s.commit()
        product = await crud.get_product(db, int(product_id))
        await message.answer(f"✅ Лимит для <b>{product.name}</b> установлен: {limit} {product.unit} за 1 заявку", parse_mode="HTML")
    except:
        await message.answer("Формат: /setlimit [id] [лимит]\nПример: /setlimit 3 200")


# ─── /orders — последние заявки ──────────────────────────────────────────────
@router.message(Command("orders"))
async def cmd_orders(message: Message, db: AsyncSession):
    if not is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")
    
    orders = await crud.get_orders(db, limit=10)
    if not orders:
        return await message.answer("Заявок пока нет")
    
    text = "📦 <b>Последние 10 заявок:</b>\n\n"
    for o in orders:
        text += (
            f"<b>#{o.id}</b> | {o.created_at.strftime('%d.%m %H:%M')}\n"
            f"👤 {o.full_name} | 🏥 {o.institution}\n"
            f"📊 Позиций: {o.total_items} | Статус: {o.status}\n\n"
        )
    
    await message.answer(text, parse_mode="HTML")


# ─── /help ───────────────────────────────────────────────────────────────────
@router.message(Command("adminhelp"))
async def cmd_admin_help(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    await message.answer(
        "🔧 <b>Команды администратора:</b>\n\n"
        "/products — список всех препаратов\n"
        "/addproduct Название | Описание | шт | 1000 — добавить препарат\n"
        "/setstock [id] [кол-во] — установить остаток\n"
        "/addstock [id] [кол-во] — пополнить остаток\n"
        "/setlimit [id] [лимит] — макс кол-во в 1 заявке\n"
        "/orders — последние 10 заявок",
        parse_mode="HTML"
    )
