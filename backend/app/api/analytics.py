from fastapi import APIRouter

from app.services.fixtures import analytics_fixture

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview():
    return analytics_fixture()
