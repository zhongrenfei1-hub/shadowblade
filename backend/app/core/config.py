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
    # Refresh tokens get a much longer life; the access token rotates often
    # so a 30-day window for refresh is a fair trade-off between user
    # convenience and risk on a stolen credential.
    jwt_refresh_ttl_minutes: int = 60 * 24 * 30
    # Password reset links should be short-lived; 1 hour matches what
    # most production templates ship with.
    password_reset_ttl_minutes: int = 60
    # Email verification can be a bit more forgiving — users may not check
    # mail immediately. 48 hours covers a Saturday-night signup that gets
    # picked up Monday morning.
    email_verify_ttl_minutes: int = 60 * 48
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        # Claude Preview / Workbench dev server uses :3010 by default —
        # see .claude/launch.json. Keeping it here means the studio.html
        # workbench page can hit the API without an env override during
        # day-to-day development.
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        # Vercel preview + production. Override via
        # SHADOWBLADE_CORS_ORIGINS='["https://your-app.vercel.app"]'
        "https://frontend-next-two-lac.vercel.app",
    ]
    # Default storage path — anchored to the repo root, not the CWD, so it
    # behaves the same whether uvicorn is started from `./` or from `backend/`.
    storage_root: str = str(_REPO_ROOT / "storage")
    render_concurrency: int = 4

    # -----------------------------------------------------------------
    # Google OAuth — env via SHADOWBLADE_GOOGLE_CLIENT_ID / _SECRET /
    # _REDIRECT_URI.
    #
    # The dance:
    # 1. GET /api/v1/auth/google/login → 302 to Google with state +
    #    PKCE verifier stashed in the signed session cookie.
    # 2. User consents → Google 302s to ``google_redirect_uri``.
    # 3. GET /api/v1/auth/google/callback consumes the state, exchanges
    #    the code for an id_token + access_token, fetches userinfo, and
    #    redirects back to ``google_post_login_redirect`` with a
    #    short-lived auth code that the frontend swaps for a JWT pair.
    #
    # ``google_redirect_uri`` is registered as an "authorised redirect
    # URI" inside the Google Cloud Console for the OAuth client — it
    # MUST exactly match what's sent in the authorize step.
    # ``google_post_login_redirect`` is where the frontend lives.
    # -----------------------------------------------------------------
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = (
        "http://localhost:8000/api/v1/auth/google/callback"
    )
    # Where the callback ultimately bounces the browser once auth is
    # complete. The token pair is appended as a URL fragment so it never
    # touches the server log (fragment isn't sent over the wire after the
    # initial GET). The frontend's auth boot extracts it from
    # ``window.location.hash``.
    google_post_login_redirect: str = "http://localhost:3000/auth/callback"
    # Scopes for the consent screen. ``openid email profile`` is the
    # minimal set that returns email + name + picture without asking for
    # contact lists or drive access — keep it tight.
    google_oauth_scopes: str = "openid email profile"
    # Discovery URL — Google's OIDC well-known document. Pulled in once
    # per process start by Authlib, then cached.
    google_oidc_metadata_url: str = (
        "https://accounts.google.com/.well-known/openid-configuration"
    )
    # Used to sign the SessionMiddleware cookie that carries the OAuth
    # state across the login → callback hop. Defaults to ``jwt_secret``
    # so a single env var pins the whole crypto surface; prod deployments
    # can split the two.
    session_secret_key: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    # If the operator didn't override session_secret_key, fall back to
    # jwt_secret. Centralising the "one secret for everything" default
    # here means the rest of the code can treat ``session_secret_key``
    # as always populated.
    if not s.session_secret_key:
        s.session_secret_key = s.jwt_secret
    return s


settings = get_settings()
