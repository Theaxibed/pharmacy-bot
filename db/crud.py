from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .models import Product, Order
from typing import Optional
import json


# ─── Products ────────────────────────────────────────────────

async def get_all_products(db: AsyncSession) -> list[Product]:
    result = await db.execute(select(Product).where(Product.is_active == True))
    return result.scalars().all()


async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, name: str, description: str = "",
                          unit: str = "шт", stock: int = 0) -> Product:
    product = Product(name=name, description=description, unit=unit, stock=stock)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_stock(db: AsyncSession, product_id: int, new_stock: int) -> Optional[Product]:
    await db.execute(
        update(Product).where(Product.id == product_id).values(stock=new_stock)
    )
    await db.commit()
    return await get_product(db, product_id)


async def add_stock(db: AsyncSession, product_id: int, amount: int) -> Optional[Product]:
    product = await get_product(db, product_id)
    if product:
        return await update_stock(db, product_id, product.stock + amount)
    return None


async def deduct_stock(db: AsyncSession, items: list[dict]) -> bool:
    """Списать остатки. Возвращает False если недостаточно."""
    for item in items:
        product = await get_product(db, item["product_id"])
        if not product or product.stock < item["quantity"]:
            return False
    # Всё ок — списываем
    for item in items:
        product = await get_product(db, item["product_id"])
        await update_stock(db, item["product_id"], product.stock - item["quantity"])
    return True


# ─── Orders ──────────────────────────────────────────────────

async def create_order(db: AsyncSession, telegram_id: int, telegram_username: str,
                        full_name: str, institution: str, phone: str,
                        items: list[dict]) -> Order:
    total = sum(i["quantity"] for i in items)
    order = Order(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        full_name=full_name,
        institution=institution,
        phone=phone,
        items_json=json.dumps(items, ensure_ascii=False),
        total_items=total,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_orders(db: AsyncSession, limit: int = 50) -> list[Order]:
    result = await db.execute(
        select(Order).order_by(Order.created_at.desc()).limit(limit)
    )
    return result.scalars().all()


async def update_order_status(db: AsyncSession, order_id: int, status: str):
    await db.execute(update(Order).where(Order.id == order_id).values(status=status))
    await db.commit()
