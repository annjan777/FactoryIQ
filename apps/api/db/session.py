import re
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, declared_attr
from core.config import settings

class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        # Fallback table name pluralizer if not overridden
        name = cls.__name__
        pattern = re.compile(r'(?<!^)(?=[A-Z])')
        snake = pattern.sub('_', name).lower()
        if snake.endswith('y'):
            return f"{snake[:-1]}ies"
        elif snake.endswith('s'):
            return f"{snake}es"
        else:
            return f"{snake}s"

# Async Engine for core operations
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Synchronous Engine for migrations/setup seeding
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sync_engine = create_engine(settings.SYNC_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)
