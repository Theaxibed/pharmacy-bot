from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, select
from pydantic import BaseModel
from typing import Optional
from db.models import get_db, Product, Order, Representative
from db import crud
import os
import json

router = APIRouter(prefix="/api/admin", tags=["admin"])


def check_admin_token(x_admin_token: Optional[str] = Header(default=None, alias="x-admin-token")):
    token = os.getenv("ADMIN_TOKEN", "").strip()
    if not token:
        raise HTTPException(500, "ADMIN_TOKEN не задан в переменных окружения")
    if not x_admin_token or x_admin_token.strip() != token:
        raise HTTPException(401, "Unauthorized")
    return True


@router.get("/ping")
async def ping():
    token = os.getenv("ADMIN_TOKEN", "")
    return {"ok": True, "token_set": bool(token), "token_len": len(token)}


# ════════════════════════════════════════════════════════════
#  PRODUCTS
# ════════════════════════════════════════════════════════════

class ProductCreate(BaseModel):
    name: str
    description: str = ""
    unit: str = "шт"
    stock: int = 0
    price: float = 0.0
    limit_per_order: Optional[int] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    stock: Optional[int] = None
    price: Optional[float] = None
    limit_per_order: Optional[int] = None
    is_active: Optional[bool] = None


@router.get("/products")
async def admin_list_products(db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    result = await db.execute(select(Product).order_by(Product.id))
    return [
        {
            "id": p.id, "name": p.name, "description": p.description or "",
            "unit": p.unit, "stock": p.stock, "price": p.price,
            "limit_per_order": p.limit_per_order, "is_active": p.is_active,
        }
        for p in result.scalars().all()
    ]


@router.post("/products")
async def admin_create_product(payload: ProductCreate, db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    product = Product(**payload.model_dump(), is_active=True)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return {"ok": True, "id": product.id}


@router.patch("/products/{product_id}")
async def admin_update_product(product_id: int, payload: ProductUpdate,
                                db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    values = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not values:
        raise HTTPException(400, "Нет данных для обновления")
    await db.execute(update(Product).where(Product.id == product_id).values(**values))
    await db.commit()
    return {"ok": True}


@router.delete("/products/{product_id}")
async def admin_delete_product(product_id: int, db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    await db.execute(delete(Product).where(Product.id == product_id))
    await db.commit()
    return {"ok": True}


@router.post("/products/{product_id}/toggle")
async def admin_toggle_product(product_id: int, db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(404, "Препарат не найден")
    await db.execute(update(Product).where(Product.id == product_id).values(is_active=not product.is_active))
    await db.commit()
    return {"ok": True, "is_active": not product.is_active}


# ════════════════════════════════════════════════════════════
#  REPRESENTATIVES
# ════════════════════════════════════════════════════════════

class RepCreate(BaseModel):
    code: str
    telegram_id: int
    full_name: str


class RepUpdate(BaseModel):
    code: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/reps")
async def admin_list_reps(db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    reps = await crud.get_all_reps(db)
    return [
        {
            "id": r.id, "code": r.code,
            "telegram_id": r.telegram_id, "full_name": r.full_name,
            "is_active": r.is_active,
        }
        for r in reps
    ]


@router.post("/reps")
async def admin_create_rep(payload: RepCreate, db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    # Проверка уникальности
    existing_code = await crud.get_rep_by_code(db, payload.code)
    if existing_code:
        raise HTTPException(400, f"Код «{payload.code}» уже занят")
    existing_tg = await crud.get_rep_by_telegram_id(db, payload.telegram_id)
    if existing_tg:
        raise HTTPException(400, f"Telegram ID {payload.telegram_id} уже зарегистрирован")
    rep = await crud.create_rep(db, payload.code, payload.telegram_id, payload.full_name)
    return {"ok": True, "id": rep.id}


@router.patch("/reps/{rep_id}")
async def admin_update_rep(rep_id: int, payload: RepUpdate,
                            db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    values = {k: v for k, v in payload.model_dump().items() if v is not None}
    await db.execute(update(Representative).where(Representative.id == rep_id).values(**values))
    await db.commit()
    return {"ok": True}


@router.delete("/reps/{rep_id}")
async def admin_delete_rep(rep_id: int, db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    await crud.delete_rep(db, rep_id)
    return {"ok": True}


# ════════════════════════════════════════════════════════════
#  ORDERS
# ════════════════════════════════════════════════════════════

@router.get("/orders")
async def admin_list_orders(db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    orders = await crud.get_orders(db, limit=100)
    result = await db.execute(select(Product))
    products = {p.id: p for p in result.scalars().all()}
    return [
        {
            "id": o.id,
            "created_at": o.created_at.strftime("%d.%m.%Y %H:%M"),
            "rep_code": o.rep_code or "—",
            "full_name": o.full_name,
            "username": o.telegram_username or "",
            "institution": o.institution,
            "status": o.status,
            "total_items": o.total_items,
            "total_price": o.total_price,
            "payment_percent": o.payment_percent,
            "payment_amount": o.payment_amount,
            "items": [
                {
                    **item,
                    "product_name": products[item["product_id"]].name if item["product_id"] in products else "?",
                }
                for item in json.loads(o.items_json)
            ],
        }
        for o in orders
    ]


@router.patch("/orders/{order_id}/status")
async def admin_update_order_status(order_id: int, payload: dict,
                                     db: AsyncSession = Depends(get_db), _=Depends(check_admin_token)):
    status = payload.get("status", "")
    if status not in ("new", "processing", "done", "cancelled"):
        raise HTTPException(400, "Неверный статус")
    await crud.update_order_status(db, order_id, status)
    return {"ok": True}
