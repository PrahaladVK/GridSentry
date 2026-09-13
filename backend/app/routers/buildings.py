from fastapi import APIRouter

from app.services import forecast_service

router = APIRouter(prefix="/buildings", tags=["buildings"])


@router.get("")
def list_buildings():
    return forecast_service.get_buildings()
