from datetime import datetime
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter(prefix="/v1/store", tags=["purchases"])


class PurchaseIn(BaseModel):
    player_id: UUID
    sku: str
    price: int
    quantity: int = 1


class PurchaseOut(BaseModel):
    purchase_id: UUID
    sku: str
    quantity: int
    charged: int
    balance_left: int


@router.post("/purchases", response_model=PurchaseOut)
async def buy_item(payload: PurchaseIn, request: Request):
    pool = request.app.state.pool

    try:
        player = await pool.fetchrow(
            "SELECT id, balance FROM players WHERE id = $1",
            payload.player_id,
        )
        if player is None:
            raise HTTPException(status_code=404, detail="player_not_found")

        item = await pool.fetchrow(
            "SELECT id, sku, price, kind FROM store_items WHERE sku = $1 AND visible = TRUE",
            payload.sku,
        )
        if item is None:
            raise HTTPException(status_code=404, detail="item_not_found")

        if item["kind"] == "unique":
            owned = await pool.fetchval(
                "SELECT count(*) FROM purchases WHERE player_id = $1 AND item_id = $2",
                payload.player_id,
                item["id"],
            )
            if owned > 0:
                raise HTTPException(status_code=400, detail="already_owned")

        total = payload.price * payload.quantity
        if player["balance"] < total:
            raise HTTPException(status_code=400, detail="not_enough_funds")

        balance_left = player["balance"] - total
        await pool.execute(
            "UPDATE players SET balance = $2, updated_at = now() WHERE id = $1",
            payload.player_id,
            balance_left,
        )

        purchase_id = uuid4()
        await pool.execute(
            """
            INSERT INTO purchases (id, player_id, item_id, quantity, created_at)
            VALUES ($1, $2, $3, $4, $5)
            """,
            purchase_id,
            payload.player_id,
            item["id"],
            payload.quantity,
            datetime.utcnow(),
        )

        return PurchaseOut(
            purchase_id=purchase_id,
            sku=item["sku"],
            quantity=payload.quantity,
            charged=total,
            balance_left=balance_left,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=200,
            content={"ok": False, "detail": str(getattr(exc, "detail", "purchase_failed"))},
        )
