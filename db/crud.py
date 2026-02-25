from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from .models import Product, Order, Representative
from typing import Optional
import json


# ─── Products ────────────────────────────────────────────────

async def get_all_products(db: AsyncSession) -> list[Product]:
    result = await db.execute(select(Product).where(Product.is_active == True).order_by(Product.id))
    return result.scalars().all()


async def get_product(db: AsyncSession, product_id: int) -> Optional[Product]:
    result = await db.execute(select(Product).where(Product.id == product_id))
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, name: str, description: str = "",
                          unit: str = "шт", stock: int = 0, price: float = 0.0) -> Product:
    product = Product(name=name, description=description, unit=unit, stock=stock, price=price)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_stock(db: AsyncSession, product_id: int, new_stock: int) -> Optional[Product]:
    await db.execute(update(Product).where(Product.id == product_id).values(stock=new_stock))
    await db.commit()
    return await get_product(db, product_id)


async def add_stock(db: AsyncSession, product_id: int, amount: int) -> Optional[Product]:
    product = await get_product(db, product_id)
    if product:
        return await update_stock(db, product_id, product.stock + amount)
    return None


async def deduct_stock(db: AsyncSession, items: list[dict]) -> bool:
    for item in items:
        product = await get_product(db, item["product_id"])
        if not product or product.stock < item["quantity"]:
            return False
    for item in items:
        product = await get_product(db, item["product_id"])
        await update_stock(db, item["product_id"], product.stock - item["quantity"])
    return True


# ─── Representatives ─────────────────────────────────────────

async def get_rep_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[Representative]:
    result = await db.execute(select(Representative).where(Representative.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_rep_by_code(db: AsyncSession, code: str) -> Optional[Representative]:
    result = await db.execute(select(Representative).where(Representative.code == code))
    return result.scalar_one_or_none()


async def get_all_reps(db: AsyncSession) -> list[Representative]:
    result = await db.execute(select(Representative).order_by(Representative.code))
    return result.scalars().all()


async def create_rep(db: AsyncSession, code: str, telegram_id: int, full_name: str) -> Representative:
    rep = Representative(code=code, telegram_id=telegram_id, full_name=full_name)
    db.add(rep)
    await db.commit()
    await db.refresh(rep)
    return rep


async def delete_rep(db: AsyncSession, rep_id: int):
    from sqlalchemy import delete
    await db.execute(delete(Representative).where(Representative.id == rep_id))
    await db.commit()


# ─── Orders ──────────────────────────────────────────────────

async def create_order(db: AsyncSession, telegram_id: int, telegram_username: str,
                        rep_code: str, full_name: str, institution: str,
                        items: list[dict], total_price: float,
                        payment_percent: int) -> Order:
    total_qty = sum(i["quantity"] for i in items)
    payment_amount = round(total_price * payment_percent / 100, 2)
    order = Order(
        telegram_id=telegram_id,
        telegram_username=telegram_username,
        rep_code=rep_code,
        full_name=full_name,
        institution=institution,
        items_json=json.dumps(items, ensure_ascii=False),
        total_items=total_qty,
        total_price=total_price,
        payment_percent=payment_percent,
        payment_amount=payment_amount,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


async def get_orders(db: AsyncSession, limit: int = 100) -> list[Order]:
    result = await db.execute(select(Order).order_by(Order.created_at.desc()).limit(limit))
    return result.scalars().all()


async def update_order_status(db: AsyncSession, order_id: int, status: str):
    await db.execute(update(Order).where(Order.id == order_id).values(status=status))
    await db.commit()
