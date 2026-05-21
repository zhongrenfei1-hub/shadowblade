from fastapi import APIRouter
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(_: LoginRequest):
    return LoginResponse(
        access_token="demo.jwt.token",
        user={
            "id": 1,
            "email": "ava.chen@acme.com",
            "full_name": "Ava Chen",
            "role": "admin",
            "workspace": "acme",
        },
    )


@router.post("/logout")
async def logout():
    return {"ok": True}
