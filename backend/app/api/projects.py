from fastapi import APIRouter

from app.services.fixtures import projects_fixture

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("")
async def list_projects():
    return projects_fixture()


@router.get("/{project_id}")
async def get_project(project_id: int):
    data = projects_fixture()
    for project in data["items"]:
        if project["id"] == project_id:
            return project
    return {"error": "not_found"}
