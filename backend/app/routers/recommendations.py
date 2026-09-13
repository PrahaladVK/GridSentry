from fastapi import APIRouter

from app.config import BUILDING_ID
from app.services import forecast_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("")
def recommendations():
    return forecast_service.get_recommendations(BUILDING_ID)
