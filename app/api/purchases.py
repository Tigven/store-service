from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.repositories.store import StoreRepository
from app.schemas import PurchaseHistoryOut, PurchaseIn, PurchaseOut
from app.services import purchase as purchase_service

router = APIRouter(prefix="/v1/store", tags=["purchases"])


def get_repo(request: Request) -> StoreRepository:
    return request.app.state.store_repo


@router.post("/purchases", response_model=PurchaseOut)
async def create_purchase(
    payload: PurchaseIn,
    repo: StoreRepository = Depends(get_repo),
):
    try:
        return await purchase_service.purchase(repo, payload)
    except purchase_service.PurchaseError as exc:
        raise HTTPException(status_code=400, detail=exc.code)
    except Exception:
        return JSONResponse(
            status_code=200,
            content={"ok": False, "detail": "purchase_failed"},
        )


@router.get(
    "/players/{player_id}/purchases",
    response_model=list[PurchaseHistoryOut],
)
async def list_purchases(
    player_id: UUID,
    sort: str = "created_at",
    repo: StoreRepository = Depends(get_repo),
) -> list[PurchaseHistoryOut]:
    return await purchase_service.history(repo, player_id, sort)
