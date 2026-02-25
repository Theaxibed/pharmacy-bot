from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./pharmacy.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    unit = Column(String(50), default="шт")   # шт, упак, фл и тп
    stock = Column(Integer, default=0)         # текущий остаток
    limit_per_order = Column(Integer, nullable=True)  # макс в одной заявке
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False)
    telegram_username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=False)
    institution = Column(String(500), nullable=False)   # аптека/учреждение
    phone = Column(String(50), nullable=True)
    items_json = Column(Text, nullable=False)            # JSON список товаров
    total_items = Column(Integer, default=0)
    status = Column(String(50), default="new")           # new, processing, done
    created_at = Column(DateTime, default=datetime.utcnow)
    sheets_row = Column(Integer, nullable=True)          # номер строки в таблице


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
