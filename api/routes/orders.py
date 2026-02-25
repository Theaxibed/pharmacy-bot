from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from db.models import get_db
from db import crud
from api.sheets import append_order_to_sheet

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderItem(BaseModel):
    product_id: int
    quantity: int


class OrderCreate(BaseModel):
    telegram_id: int
    telegram_username: str = ""
    institution: str
    payment_percent: int = 100   # 50 или 100
    items: list[OrderItem]


@router.post("/")
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    if not payload.items:
        raise HTTPException(400, "Корзина пустая")
    if payload.payment_percent not in (50, 100):
        raise HTTPException(400, "payment_percent должен быть 50 или 100")

    # Проверяем что пользователь зарегистрирован
    rep = await crud.get_rep_by_telegram_id(db, payload.telegram_id)
    if not rep:
        raise HTTPException(403, "Вы не зарегистрированы как медпредставитель. Обратитесь к администратору.")
    if not rep.is_active:
        raise HTTPException(403, "Ваш аккаунт деактивирован.")

    # Проверяем остатки и лимиты
    for item in payload.items:
        product = await crud.get_product(db, item.product_id)
        if not product:
            raise HTTPException(404, f"Препарат {item.product_id} не найден")
        if product.stock < item.quantity:
            raise HTTPException(400, f"Недостаточно «{product.name}»: доступно {product.stock} {product.unit}")
        if product.limit_per_order and item.quantity > product.limit_per_order:
            raise HTTPException(400, f"Лимит «{product.name}»: не более {product.limit_per_order} {product.unit} за раз")

    # Считаем сумму
    total_price = 0.0
    items_dicts = []
    for item in payload.items:
        product = await crud.get_product(db, item.product_id)
        line_total = round(product.price * item.quantity, 2)
        total_price += line_total
        items_dicts.append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": product.price,
            "line_total": line_total,
            "unit": product.unit,
        })
    total_price = round(total_price, 2)

    # Списываем остатки
    if not await crud.deduct_stock(db, [{"product_id": i["product_id"], "quantity": i["quantity"]} for i in items_dicts]):
        raise HTTPException(400, "Ошибка списания остатков, попробуйте снова")

    # Создаём заказ
    order = await crud.create_order(
        db,
        telegram_id=payload.telegram_id,
        telegram_username=payload.telegram_username,
        rep_code=rep.code,
        full_name=rep.full_name,
        institution=payload.institution,
        items=items_dicts,
        total_price=total_price,
        payment_percent=payload.payment_percent,
    )

    # Google Sheets
    try:
        products_map = {}
        for i in items_dicts:
            p = await crud.get_product(db, i["product_id"])
            if p:
                products_map[i["product_id"]] = p.name
        append_order_to_sheet(
            order_id=order.id,
            rep_code=rep.code,
            full_name=rep.full_name,
            username=payload.telegram_username,
            institution=payload.institution,
            items=items_dicts,
            products_map=products_map,
            total_price=total_price,
            payment_percent=payload.payment_percent,
            payment_amount=order.payment_amount,
        )
    except Exception as e:
        print(f"[Sheets ERROR] {e}")

    return {
        "ok": True,
        "order_id": order.id,
        "rep_code": rep.code,
        "total_price": total_price,
        "payment_amount": order.payment_amount,
        "payment_percent": payload.payment_percent,
    }


@router.get("/check-rep/{telegram_id}")
async def check_rep(telegram_id: int, db: AsyncSession = Depends(get_db)):
    """Проверка — зарегистрирован ли пользователь"""
    rep = await crud.get_rep_by_telegram_id(db, telegram_id)
    if not rep or not rep.is_active:
        return {"registered": False}
    return {"registered": True, "code": rep.code, "full_name": rep.full_name}
