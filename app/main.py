import os
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI

from app.api import catalog, purchases
from app.repositories.store import StoreRepository


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"],
        min_size=2,
        max_size=20,
    )
    app.state.pool = pool
    app.state.store_repo = StoreRepository(pool)
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="store-service", lifespan=lifespan)
app.include_router(catalog.router)
app.include_router(purchases.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
