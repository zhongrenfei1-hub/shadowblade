# ShadowBlade · Backend

FastAPI pipeline for enterprise AI short-video generation.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `http://localhost:8000/docs` for the OpenAPI surface.

## Surface area

| Resource       | Verb  | Path                          |
| -------------- | ----- | ----------------------------- |
| Health         | GET   | `/api/v1/health`              |
| Auth           | POST  | `/api/v1/auth/login`          |
| Workspace      | GET   | `/api/v1/workspaces/me`       |
| Projects       | GET   | `/api/v1/projects`            |
| Jobs (stages)  | GET   | `/api/v1/jobs`                |
| Assets         | GET   | `/api/v1/assets`              |
| Templates      | GET   | `/api/v1/templates`           |
| Render queue   | GET   | `/api/v1/render-queue`        |
| Brand kits     | GET   | `/api/v1/brand-kits`          |
| Analytics      | GET   | `/api/v1/analytics/overview`  |

The Design ring uses fixture payloads in `app/services/fixtures.py` so the
frontend can be built against the final response shapes before the live
pipeline is wired in.
