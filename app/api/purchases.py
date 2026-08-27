from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.schemas import PurchaseRequest, PurchaseResponse, RefundResponse
from app.services.purchase_service import PurchaseError, PurchaseService

router = APIRouter(prefix="/v1/store", tags=["purchases"])


def get_service(request: Request) -> PurchaseService:
    return request.app.state.purchase_service


@router.post(
    "/players/{player_id}/purchases",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_purchase(
    player_id: UUID,
    body: PurchaseRequest,
    service: PurchaseService = Depends(get_service),
) -> PurchaseResponse:
    try:
        return await service.purchase(player_id, body)
    except PurchaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code)


@router.post(
    "/players/{player_id}/purchases/{purchase_id}/refund",
    response_model=RefundResponse,
)
async def refund_purchase(
    player_id: UUID,
    purchase_id: UUID,
    service: PurchaseService = Depends(get_service),
) -> RefundResponse:
    try:
        return await service.refund(player_id, purchase_id)
    except PurchaseError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.code)
