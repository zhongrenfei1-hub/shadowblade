"""Realistic fixtures used by the Design ring to power the UI before the
real pipeline is wired in. Mirrors the shape the production endpoints will
return so the Next.js frontend can be coded against final contracts."""

from datetime import datetime, timedelta, timezone


def _iso(delta_minutes: int = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=delta_minutes)).isoformat()


def projects_fixture() -> dict:
    return {
        "items": [
            {
                "id": 101,
                "name": "Spring product launch — wearable hub",
                "purpose": "marketing",
                "status": "rendering",
                "progress": 0.62,
                "aspect_ratio": "9:16",
                "duration_seconds": 28,
                "owner": "Ava Chen",
                "updated_at": _iso(-9),
                "cover": "wearable-hub",
                "tags": ["Hero", "Paid social"],
            },
            {
                "id": 102,
                "name": "Onboarding · Sales engineering bootcamp",
                "purpose": "training",
                "status": "review",
                "progress": 1.0,
                "aspect_ratio": "16:9",
                "duration_seconds": 96,
                "owner": "Marcus Lee",
                "updated_at": _iso(-44),
                "cover": "bootcamp",
                "tags": ["Internal", "L&D"],
            },
            {
                "id": 103,
                "name": "AI Copilot — 60s product demo",
                "purpose": "product_demo",
                "status": "scripting",
                "progress": 0.18,
                "aspect_ratio": "16:9",
                "duration_seconds": 60,
                "owner": "Priya Rao",
                "updated_at": _iso(-180),
                "cover": "copilot",
                "tags": ["Sales", "Demo"],
            },
            {
                "id": 104,
                "name": "TikTok teaser — Series C announcement",
                "purpose": "social",
                "status": "done",
                "progress": 1.0,
                "aspect_ratio": "9:16",
                "duration_seconds": 15,
                "owner": "Diego Alvarez",
                "updated_at": _iso(-1440),
                "cover": "series-c",
                "tags": ["Social", "Brand"],
            },
            {
                "id": 105,
                "name": "Q3 customer story — Helios Logistics",
                "purpose": "marketing",
                "status": "draft",
                "progress": 0.04,
                "aspect_ratio": "16:9",
                "duration_seconds": 75,
                "owner": "Ava Chen",
                "updated_at": _iso(-2),
                "cover": "helios",
                "tags": ["Case study"],
            },
            {
                "id": 106,
                "name": "Compliance refresher — GDPR essentials",
                "purpose": "training",
                "status": "draft",
                "progress": 0.0,
                "aspect_ratio": "16:9",
                "duration_seconds": 180,
                "owner": "Marcus Lee",
                "updated_at": _iso(-720),
                "cover": "gdpr",
                "tags": ["Compliance"],
            },
        ],
        "total": 38,
    }


def jobs_fixture() -> dict:
    stages = ["script", "storyboard", "tts", "b_roll", "compose", "render"]
    return {
        "items": [
            {
                "id": idx + 1,
                "project_id": 101,
                "stage": stage,
                "status": "succeeded"
                if idx < 4
                else ("running" if idx == 4 else "queued"),
                "progress": 1.0 if idx < 4 else (0.62 if idx == 4 else 0.0),
                "runtime_seconds": [8.4, 12.1, 18.6, 41.0, 73.0, 0.0][idx],
                "log_tail": [
                    "scene_count=6 voice=alloy-en-female",
                    "boards rendered 6/6 · style=editorial",
                    "voiceover 4 takes · loudness -14 LUFS",
                    "b-roll matched 18 clips · CC license",
                    "compose 62% · waiting on overlay #3",
                    "queued behind 2 rush jobs",
                ][idx],
            }
            for idx, stage in enumerate(stages)
        ]
    }


def assets_fixture() -> dict:
    items = [
        ("Brand logo · primary", "image", "logo-primary", 48_212),
        ("Brand logo · monochrome", "image", "logo-mono", 41_900),
        ("Founder b-roll · keynote", "video", "founder-keynote", 184_300_000),
        ("Voice · Ava narration", "audio", "voice-ava", 5_840_000),
        ("Product UI · dashboard", "image", "ui-dashboard", 612_440),
        ("Product UI · studio", "image", "ui-studio", 588_212),
        ("Stock · skyline drone", "video", "skyline", 92_111_000),
        ("Stock · server room dolly", "video", "server-room", 88_900_000),
        ("Font · Inter Display", "font", "inter-display", 412_000),
        ("Font · JetBrains Mono", "font", "jetbrains-mono", 388_000),
    ]
    return {
        "items": [
            {
                "id": idx + 1,
                "name": name,
                "kind": kind,
                "slug": slug,
                "size_bytes": size,
                "tags": ["brand", "approved"] if "logo" in slug else ["library"],
                "created_at": _iso(-(idx + 1) * 37),
            }
            for idx, (name, kind, slug, size) in enumerate(items)
        ],
        "totals": {"video": 14, "image": 86, "audio": 9, "font": 4, "logo": 3},
    }


def templates_fixture() -> dict:
    palette = [
        ("hero-launch", "Launch hero · 30s", "marketing", "9:16", 30),
        ("product-explainer", "Product explainer · 60s", "product_demo", "16:9", 60),
        ("training-module", "Training module · 3 min", "training", "16:9", 180),
        ("social-teaser", "Social teaser · 15s", "social", "9:16", 15),
        ("case-study", "Case study · 75s", "marketing", "16:9", 75),
        ("onboarding-loop", "Onboarding loop · 45s", "training", "1:1", 45),
        ("recap-monthly", "Monthly recap · 90s", "marketing", "16:9", 90),
        ("press-quote", "Press quote · 20s", "social", "9:16", 20),
    ]
    return {
        "items": [
            {
                "id": idx + 1,
                "slug": slug,
                "name": name,
                "category": cat,
                "aspect_ratio": ratio,
                "duration_seconds": dur,
                "scenes": 4 + (idx % 3),
            }
            for idx, (slug, name, cat, ratio, dur) in enumerate(palette)
        ]
    }


def render_queue_fixture() -> dict:
    return {
        "concurrency": 4,
        "items": [
            {
                "id": 901,
                "project": "Spring product launch — wearable hub",
                "priority": "rush",
                "status": "running",
                "progress": 0.62,
                "eta_seconds": 64,
                "worker": "gpu-cluster-3",
            },
            {
                "id": 902,
                "project": "AI Copilot — 60s product demo",
                "priority": "high",
                "status": "running",
                "progress": 0.31,
                "eta_seconds": 142,
                "worker": "gpu-cluster-1",
            },
            {
                "id": 903,
                "project": "Onboarding · Sales engineering bootcamp",
                "priority": "normal",
                "status": "queued",
                "progress": 0.0,
                "eta_seconds": 612,
                "worker": None,
            },
            {
                "id": 904,
                "project": "Press quote · Series C announcement",
                "priority": "normal",
                "status": "queued",
                "progress": 0.0,
                "eta_seconds": 740,
                "worker": None,
            },
            {
                "id": 905,
                "project": "Compliance refresher — GDPR essentials",
                "priority": "low",
                "status": "queued",
                "progress": 0.0,
                "eta_seconds": 1340,
                "worker": None,
            },
        ],
    }


def brand_kit_fixture() -> dict:
    return {
        "items": [
            {
                "id": 1,
                "name": "Acme · Core",
                "primary_color": "#0F2A4A",
                "accent_color": "#22D3B7",
                "font_heading": "Inter Display",
                "font_body": "Inter",
                "voice": "alloy-en-female",
                "tone": {
                    "voice_profile": "Confident, plainspoken, never breathless",
                    "do": [
                        "Lead with the customer outcome",
                        "Use single-syllable verbs",
                        "Cap sentences at 14 words on-screen",
                    ],
                    "avoid": ["Buzzwords", "Stock metaphors", "Exclamation marks"],
                },
            },
            {
                "id": 2,
                "name": "Acme · Field events",
                "primary_color": "#101728",
                "accent_color": "#FF7849",
                "font_heading": "Inter Display",
                "font_body": "Inter",
                "voice": "ember-en-male",
                "tone": {
                    "voice_profile": "Warm host, conversational",
                    "do": ["Name the city", "Open with a question"],
                    "avoid": ["Generic event language"],
                },
            },
        ]
    }


def analytics_fixture() -> dict:
    return {
        "kpis": [
            {
                "label": "Renders this month",
                "value": 387,
                "delta": 0.124,
                "unit": "videos",
            },
            {
                "label": "Avg time to first cut",
                "value": 4.8,
                "delta": -0.31,
                "unit": "minutes",
            },
            {
                "label": "Approval rate",
                "value": 0.92,
                "delta": 0.06,
                "unit": "ratio",
            },
            {
                "label": "Saved vs agency baseline",
                "value": 168_400,
                "delta": 0.21,
                "unit": "usd",
            },
        ],
        "timeseries": [
            {"day": "Mon", "rendered": 42, "approved": 38, "rejected": 4},
            {"day": "Tue", "rendered": 51, "approved": 47, "rejected": 4},
            {"day": "Wed", "rendered": 49, "approved": 46, "rejected": 3},
            {"day": "Thu", "rendered": 63, "approved": 60, "rejected": 3},
            {"day": "Fri", "rendered": 74, "approved": 67, "rejected": 7},
            {"day": "Sat", "rendered": 48, "approved": 45, "rejected": 3},
            {"day": "Sun", "rendered": 60, "approved": 55, "rejected": 5},
        ],
        "distribution": [
            {"label": "Marketing", "value": 41},
            {"label": "Training", "value": 24},
            {"label": "Product demo", "value": 19},
            {"label": "Social", "value": 16},
        ],
    }
