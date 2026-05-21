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
                "name": "春季产品发布 — 智能腕环",
                "purpose": "marketing",
                "status": "rendering",
                "progress": 0.62,
                "aspect_ratio": "9:16",
                "duration_seconds": 28,
                "owner": "Ava Chen",
                "updated_at": _iso(-9),
                "cover": "wearable-hub",
                "tags": ["主推", "付费社媒"],
            },
            {
                "id": 102,
                "name": "入职培训 · 销售工程师训练营",
                "purpose": "training",
                "status": "review",
                "progress": 1.0,
                "aspect_ratio": "16:9",
                "duration_seconds": 96,
                "owner": "Marcus Lee",
                "updated_at": _iso(-44),
                "cover": "bootcamp",
                "tags": ["内部", "学习发展"],
            },
            {
                "id": 103,
                "name": "AI Copilot · 60 秒产品演示",
                "purpose": "product_demo",
                "status": "scripting",
                "progress": 0.18,
                "aspect_ratio": "16:9",
                "duration_seconds": 60,
                "owner": "Priya Rao",
                "updated_at": _iso(-180),
                "cover": "copilot",
                "tags": ["销售", "演示"],
            },
            {
                "id": 104,
                "name": "TikTok 预告 — C 轮发布",
                "purpose": "social",
                "status": "done",
                "progress": 1.0,
                "aspect_ratio": "9:16",
                "duration_seconds": 15,
                "owner": "Diego Alvarez",
                "updated_at": _iso(-1440),
                "cover": "series-c",
                "tags": ["社交", "品牌"],
            },
            {
                "id": 105,
                "name": "Q3 客户故事 — Helios Logistics",
                "purpose": "marketing",
                "status": "draft",
                "progress": 0.04,
                "aspect_ratio": "16:9",
                "duration_seconds": 75,
                "owner": "Ava Chen",
                "updated_at": _iso(-2),
                "cover": "helios",
                "tags": ["客户案例"],
            },
            {
                "id": 106,
                "name": "合规培训 — GDPR 要点",
                "purpose": "training",
                "status": "draft",
                "progress": 0.0,
                "aspect_ratio": "16:9",
                "duration_seconds": 180,
                "owner": "Marcus Lee",
                "updated_at": _iso(-720),
                "cover": "gdpr",
                "tags": ["合规"],
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
                    "分镜已渲染 6/6 · style=editorial",
                    "配音 4 个版本 · 响度 -14 LUFS",
                    "空镜素材匹配 18 段 · CC 协议",
                    "合成 62% · 等待叠加层 #3",
                    "排在 2 个加急任务之后",
                ][idx],
            }
            for idx, stage in enumerate(stages)
        ]
    }


def assets_fixture() -> dict:
    items = [
        ("品牌 logo · 主色", "image", "logo-primary", 48_212),
        ("品牌 logo · 单色", "image", "logo-mono", 41_900),
        ("创始人空镜 · 主题演讲", "video", "founder-keynote", 184_300_000),
        ("配音 · Ava 旁白", "audio", "voice-ava", 5_840_000),
        ("产品 UI · 工作台", "image", "ui-dashboard", 612_440),
        ("产品 UI · 编辑器", "image", "ui-studio", 588_212),
        ("素材 · 城市天际线", "video", "skyline", 92_111_000),
        ("素材 · 机房推轨", "video", "server-room", 88_900_000),
        ("字体 · Inter Display", "font", "inter-display", 412_000),
        ("字体 · JetBrains Mono", "font", "jetbrains-mono", 388_000),
    ]
    return {
        "items": [
            {
                "id": idx + 1,
                "name": name,
                "kind": kind,
                "slug": slug,
                "size_bytes": size,
                "tags": ["品牌", "已审核"] if "logo" in slug else ["资源库"],
                "created_at": _iso(-(idx + 1) * 37),
            }
            for idx, (name, kind, slug, size) in enumerate(items)
        ],
        "totals": {"video": 14, "image": 86, "audio": 9, "font": 4, "logo": 3},
    }


def templates_fixture() -> dict:
    palette = [
        ("hero-launch", "发布主推 · 30 秒", "marketing", "9:16", 30),
        ("product-explainer", "产品讲解 · 60 秒", "product_demo", "16:9", 60),
        ("training-module", "培训模块 · 3 分钟", "training", "16:9", 180),
        ("social-teaser", "社交预告 · 15 秒", "social", "9:16", 15),
        ("case-study", "客户案例 · 75 秒", "marketing", "16:9", 75),
        ("onboarding-loop", "入职循环 · 45 秒", "training", "1:1", 45),
        ("recap-monthly", "月度回顾 · 90 秒", "marketing", "16:9", 90),
        ("press-quote", "媒体引用 · 20 秒", "social", "9:16", 20),
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
                "project": "春季产品发布 — 智能腕环",
                "priority": "rush",
                "status": "running",
                "progress": 0.62,
                "eta_seconds": 64,
                "worker": "gpu-cluster-3",
            },
            {
                "id": 902,
                "project": "AI Copilot · 60 秒产品演示",
                "priority": "high",
                "status": "running",
                "progress": 0.31,
                "eta_seconds": 142,
                "worker": "gpu-cluster-1",
            },
            {
                "id": 903,
                "project": "入职培训 · 销售工程师训练营",
                "priority": "normal",
                "status": "queued",
                "progress": 0.0,
                "eta_seconds": 612,
                "worker": None,
            },
            {
                "id": 904,
                "project": "媒体引用 · C 轮发布",
                "priority": "normal",
                "status": "queued",
                "progress": 0.0,
                "eta_seconds": 740,
                "worker": None,
            },
            {
                "id": 905,
                "project": "合规培训 — GDPR 要点",
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
                "name": "Acme · 核心版",
                "primary_color": "#0F2A4A",
                "accent_color": "#22D3B7",
                "font_heading": "Inter Display",
                "font_body": "Inter",
                "voice": "alloy-en-female",
                "tone": {
                    "voice_profile": "自信、平实、不夸张",
                    "do": [
                        "先讲客户得到了什么",
                        "用单音节动词",
                        "屏幕上每句话不超过 14 字",
                    ],
                    "avoid": ["行业黑话", "陈词滥调", "感叹号"],
                },
            },
            {
                "id": 2,
                "name": "Acme · 线下活动",
                "primary_color": "#101728",
                "accent_color": "#FF7849",
                "font_heading": "Inter Display",
                "font_body": "Inter",
                "voice": "ember-en-male",
                "tone": {
                    "voice_profile": "温暖、像主持人在聊天",
                    "do": ["先点出城市", "用一个问题开场"],
                    "avoid": ["千篇一律的活动套话"],
                },
            },
        ]
    }


def analytics_fixture() -> dict:
    return {
        "kpis": [
            {
                "label": "本月渲染次数",
                "value": 387,
                "delta": 0.124,
                "unit": "videos",
            },
            {
                "label": "首版成片平均耗时",
                "value": 4.8,
                "delta": -0.31,
                "unit": "minutes",
            },
            {
                "label": "一次审核通过率",
                "value": 0.92,
                "delta": 0.06,
                "unit": "ratio",
            },
            {
                "label": "较外包代理节省",
                "value": 168_400,
                "delta": 0.21,
                "unit": "usd",
            },
        ],
        "timeseries": [
            {"day": "周一", "rendered": 42, "approved": 38, "rejected": 4},
            {"day": "周二", "rendered": 51, "approved": 47, "rejected": 4},
            {"day": "周三", "rendered": 49, "approved": 46, "rejected": 3},
            {"day": "周四", "rendered": 63, "approved": 60, "rejected": 3},
            {"day": "周五", "rendered": 74, "approved": 67, "rejected": 7},
            {"day": "周六", "rendered": 48, "approved": 45, "rejected": 3},
            {"day": "周日", "rendered": 60, "approved": 55, "rejected": 5},
        ],
        "distribution": [
            {"label": "营销", "value": 41},
            {"label": "培训", "value": 24},
            {"label": "产品演示", "value": 19},
            {"label": "社交", "value": 16},
        ],
    }
