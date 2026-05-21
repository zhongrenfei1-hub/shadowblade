from fastapi import APIRouter

from app.services.fixtures import assets_fixture

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("")
async def list_assets():
    return assets_fixture()
