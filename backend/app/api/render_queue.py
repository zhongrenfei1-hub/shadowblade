from fastapi import APIRouter

from app.services.fixtures import render_queue_fixture

router = APIRouter(prefix="/render-queue", tags=["render_queue"])


@router.get("")
async def list_render_queue():
    return render_queue_fixture()
