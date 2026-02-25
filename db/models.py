from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, BigInteger
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
    unit = Column(String(50), default="шт")
    stock = Column(Integer, default=0)
    price = Column(Float, default=0.0)          # цена за единицу
    limit_per_order = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)


class Representative(Base):
    __tablename__ = "representatives"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)   # короткий код, напр. "4"
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, nullable=False)
    telegram_username = Column(String(255), nullable=True)
    rep_code = Column(String(50), nullable=True)             # код медпредставителя
    full_name = Column(String(255), nullable=False)
    institution = Column(String(500), nullable=False)
    items_json = Column(Text, nullable=False)
    total_items = Column(Integer, default=0)
    total_price = Column(Float, default=0.0)                 # полная сумма
    payment_percent = Column(Integer, default=100)           # 50 или 100
    payment_amount = Column(Float, default=0.0)              # итого к оплате
    status = Column(String(50), default="new")
    created_at = Column(DateTime, default=datetime.utcnow)
    sheets_row = Column(Integer, nullable=True)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
