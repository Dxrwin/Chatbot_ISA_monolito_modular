import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import aiomysql

from core.config import settings

_pool: Optional[aiomysql.Pool] = None
_pool_lock = asyncio.Lock()


async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is not None:
        return _pool
    async with _pool_lock:
        if _pool is None:
            _pool = await aiomysql.create_pool(
                host=settings.DB_HOST,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD_RENOVACION,
                db=settings.DB_NAME_RENOVACION,
                minsize=1,
                maxsize=5,
                autocommit=False,
            )
    return _pool


@asynccontextmanager
async def acquire_conn():
    pool = await get_pool()
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        pool.release(conn)
