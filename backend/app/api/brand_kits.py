from fastapi import APIRouter

from app.services.fixtures import brand_kit_fixture

router = APIRouter(prefix="/brand-kits", tags=["brand_kits"])


@router.get("")
async def list_brand_kits():
    return brand_kit_fixture()
