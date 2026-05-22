from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root is two levels above this file: backend/app/core/config.py → repo
_REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHADOWBLADE_", env_file=".env")

    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./shadowblade.db"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    jwt_ttl_minutes: int = 60 * 12
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        # Vercel preview + production. Override via
        # SHADOWBLADE_CORS_ORIGINS='["https://your-app.vercel.app"]'
        "https://frontend-next-two-lac.vercel.app",
    ]
    # Default storage path — anchored to the repo root, not the CWD, so it
    # behaves the same whether uvicorn is started from `./` or from `backend/`.
    storage_root: str = str(_REPO_ROOT / "storage")
    render_concurrency: int = 4


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
