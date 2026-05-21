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
            {"id": 1, "name": "Ava Chen", "role": "工作空间管理员"},
            {"id": 2, "name": "Marcus Lee", "role": "制作人"},
            {"id": 3, "name": "Priya Rao", "role": "品牌负责人"},
            {"id": 4, "name": "Diego Alvarez", "role": "审核员"},
        ],
    }
