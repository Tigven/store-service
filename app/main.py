import os
from contextlib import asynccontextmanager

import asyncpg
import httpx
from fastapi import FastAPI

from app.api import catalog, purchases
from app.repositories.store import StoreRepository
from app.services.purchase_service import AnalyticsClient, PurchaseService


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = await asyncpg.create_pool(
        dsn=os.environ["DATABASE_URL"],
        min_size=2,
        max_size=20,
    )
    repo = StoreRepository(pool)
    analytics_session = httpx.AsyncClient(timeout=5.0)

    app.state.pool = pool
    app.state.store_repo = repo
    app.state.purchase_service = PurchaseService(
        pool,
        repo,
        AnalyticsClient(analytics_session, os.environ["ANALYTICS_URL"]),
    )
    try:
        yield
    finally:
        await analytics_session.aclose()
        await pool.close()


app = FastAPI(title="store-service", lifespan=lifespan)
app.include_router(catalog.router)
app.include_router(purchases.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
