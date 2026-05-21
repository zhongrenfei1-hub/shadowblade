from fastapi import APIRouter

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("/me")
async def current_workspace():
    return {
        "id": 1,
        "slug": "acme",
        "name": "Acme Marketing Cloud",
        "plan": "scale",
        "seats": 24,
        "monthly_render_quota": 1000,
        "monthly_render_used": 387,
        "team": [
            {"id": 1, "name": "Ava Chen", "role": "Workspace admin"},
            {"id": 2, "name": "Marcus Lee", "role": "Producer"},
            {"id": 3, "name": "Priya Rao", "role": "Brand lead"},
            {"id": 4, "name": "Diego Alvarez", "role": "Reviewer"},
        ],
    }
