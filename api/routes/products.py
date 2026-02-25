from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import get_db
from db import crud

router = APIRouter(prefix="/api/products", tags=["products"])


@router.get("/")
async def list_products(db: AsyncSession = Depends(get_db)):
    products = await crud.get_all_products(db)
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "unit": p.unit,
            "stock": p.stock,
            "price": p.price,
            "limit_per_order": p.limit_per_order,
            "available": p.stock > 0,
        }
        for p in products
    ]
