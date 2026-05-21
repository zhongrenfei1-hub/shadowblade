from fastapi import APIRouter

from app.services.fixtures import templates_fixture

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("")
async def list_templates():
    return templates_fixture()
