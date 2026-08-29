from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings


engine = create_async_engine(settings.database_url, echo=settings.sql_echo)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


def ensure_data_directory() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)


async def create_db_and_tables() -> None:
    ensure_data_directory()
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
