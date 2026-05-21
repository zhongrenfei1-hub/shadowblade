from fastapi import APIRouter

from app.services.fixtures import jobs_fixture

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("")
async def list_jobs():
    return jobs_fixture()
