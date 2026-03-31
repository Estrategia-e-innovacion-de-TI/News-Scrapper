"""Async database engine and session factory."""
from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://newsradar:newsradar@localhost:5432/newsradar")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    from newsradar_api.infrastructure.driven_adapters.db_models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
