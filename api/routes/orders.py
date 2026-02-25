from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from db.models import get_db
from db import crud
from api.sheets import append_order_to_sheet
import json

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderItem(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    telegram_id: int
    telegram_username: str = ""
    full_name: str
    institution: str
    phone: str = ""
    items: list[OrderItem]


@router.post("/")
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    if not payload.items:
        raise HTTPException(400, "Корзина пустая")

    # Проверяем остатки и лимиты
    for item in payload.items:
        product = await crud.get_product(db, item.product_id)
        if not product:
            raise HTTPException(404, f"Препарат {item.product_id} не найден")
        if product.stock < item.quantity:
            raise HTTPException(400, f"Недостаточно '{product.name}': доступно {product.stock} {product.unit}")
        if product.limit_per_order and item.quantity > product.limit_per_order:
            raise HTTPException(400, f"Лимит на '{product.name}': не более {product.limit_per_order} {product.unit} за раз")

    # Списываем остатки
    items_dicts = [{"product_id": i.product_id, "quantity": i.quantity} for i in payload.items]
    success = await crud.deduct_stock(db, items_dicts)
    if not success:
        raise HTTPException(400, "Ошибка списания остатков, попробуйте снова")

    # Создаём заявку
    order = await crud.create_order(
        db,
        telegram_id=payload.telegram_id,
        telegram_username=payload.telegram_username,
        full_name=payload.full_name,
        institution=payload.institution,
        phone=payload.phone,
        items=items_dicts,
    )

    # Пишем в Google Sheets
    try:
        products_map = {}
        for item in payload.items:
            p = await crud.get_product(db, item.product_id)
            if p:
                products_map[item.product_id] = p.name
                items_dicts_with_unit = [
                    {**d, "unit": (await crud.get_product(db, d["product_id"])).unit}
                    for d in items_dicts
                ]
        
        append_order_to_sheet(
            order_id=order.id,
            full_name=payload.full_name,
            username=payload.telegram_username,
            institution=payload.institution,
            phone=payload.phone,
            items=items_dicts_with_unit,
            products_map=products_map,
        )
    except Exception as e:
        # Таблица не критична — заявка всё равно сохранена в БД
        print(f"[Sheets ERROR] {e}")

    return {"ok": True, "order_id": order.id}
