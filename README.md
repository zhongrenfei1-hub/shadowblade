# ShadowBlade

Enterprise AI short-video generation cloud. Brief → broadcast-ready video in
under five minutes, against your brand kit.

## Stack at a glance

| Layer        | Tech                                           |
| ------------ | ---------------------------------------------- |
| Backend      | FastAPI 0.115 · SQLAlchemy 2 async · Redis     |
| Workers      | Celery (render, TTS, b-roll, compose)          |
| Frontend     | Vanilla HTML + design tokens (Inter / JetBrains Mono) |
| Storage      | S3-compatible object store                     |
| Auth         | SAML SSO + SCIM provisioning                   |

## Workspace surface (Design ring shipped)

| Route               | Page                                          |
| ------------------- | --------------------------------------------- |
| `index.html`        | Marketing landing with hero pipeline visual   |
| `dashboard.html`    | KPIs · in-flight pipeline · approvals · projects |
| `studio.html`       | Three-column scene editor + multi-track timeline |
| `projects.html`     | Filter chips + dense project table            |
| `templates.html`    | Template gallery with hover-reveal play       |
| `assets.html`       | Folders · tags · drop-zone · content grid    |
| `render-queue.html` | Cluster utilisation · worker grid · queue     |
| `analytics.html`    | KPI strip · 7-day chart · leaderboard · drift |
| `brand-kit.html`    | Kit picker · swatches · type · voice & tone   |
| `team.html`         | Members · roles · permission matrix · SCIM    |
| `settings.html`     | Workspace · render · security · billing · API |

## Run locally

```bash
make install        # one-time
make dev            # backend on :8000, frontend on :3000
```

Open `http://localhost:3000` for the marketing landing, then click "Open
workspace" to enter the cockpit. The frontend will hit `/api/v1/projects` on
the backend through the CORS-enabled FastAPI app and gracefully fall back to
local fixture data if the backend is offline.

## Four-ring flywheel

This repo is being built by four concurrent rings:

1. **Design** — backend + UI design system + every workspace page.
2. **Showcase** — brand assets, marketing visuals, product screens, voice spec.
3. **Test** — a11y, contrast, copy, responsive, brand consistency audit.
4. **Refine** — applies Test findings + wires Showcase assets back in.

Outputs live under `frontend/`, `backend/`, `showcase/`, `docs/`. Each ring
commits its own work; refine the cycle by re-running rings 2-4 after the next
Design wave.
