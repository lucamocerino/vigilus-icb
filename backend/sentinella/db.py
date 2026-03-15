from __future__ import annotations
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sentinella.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")
_is_pooler = "pooler.supabase" in settings.database_url

_engine_kwargs = {}
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
# Supabase pooler (PgBouncer) requires statement_cache_size=0
if _is_pooler:
    _engine_kwargs["connect_args"] = {"statement_cache_size": 0, "prepared_statement_cache_size": 0}

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    **_engine_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=True,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    from sentinella.models import score, event, source  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
