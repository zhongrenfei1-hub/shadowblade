# 部署指南

> **前端 Vercel 自动跑** + **后端选 Railway / Render / Fly** 三选一。
>
> Vercel 不能跑后端（serverless 60s 超时 + 没 ffmpeg 二进制 + 没持久 storage）。

---

## 架构

```
┌────────────────┐       ┌──────────────────────────┐
│   Vercel       │       │  Railway / Render / Fly  │
│   Next.js 14   │ ───→  │  FastAPI + ffmpeg +      │
│   (无状态)     │  API  │  yt-dlp + edge-tts +     │
│                │       │  whisper + persistent    │
│                │       │  /data/storage volume    │
└────────────────┘       └──────────────────────────┘
       ↑                            ↑
       │ 你的域名                    │ <backend>.up.railway.app
       │ (frontend-next-two-lac     │
       │  .vercel.app)
       │
   浏览器
```

---

## 第 1 步：后端部署（3 选 1）

### 选项 A · Railway（推荐 · 1 分钟）

1. 去 [railway.com/new](https://railway.com/new) → **"Deploy from GitHub repo"** → 选 `zhongrenfei1-hub/shadowblade`
2. Railway 会自动看到 `railway.json` + `backend/Dockerfile`
3. 部署完成后，Settings → 加 **Volume**：mount path `/data`，1 GB 起步
4. **Settings → Networking → Generate Domain** 拿到 URL，如 `shadowblade-backend.up.railway.app`
5. 测试：
   ```bash
   curl https://shadowblade-backend.up.railway.app/api/v1/health
   # → {"status":"ok",...}
   ```

**费用**：$5/月起 hobby plan。或者用 trial（$5 免费额度）跑一个月。

---

### 选项 B · Render（免费层有）

1. [render.com/blueprints](https://render.com/blueprints) → **"New Blueprint Instance"** → 选 repo
2. Render 自动读 `render.yaml`，建好一个 web service + 1 GB disk
3. 部署完成后顶部就有 URL（如 `shadowblade-backend.onrender.com`）
4. 免费层 15 分钟无访问会 sleep，下次请求会冷启 30 秒

**费用**：免费 750 小时/月，付费 $7/月。

---

### 选项 C · Fly.io（接近裸金属 · 全球边缘）

```bash
# 装 flyctl
curl -L https://fly.io/install.sh | sh

# 登录
fly auth login

# 部署（从 repo 根目录）
cd shadowblade
fly launch --copy-config --name shadowblade-backend
fly volumes create shadowblade_data --size 1 --region nrt
fly deploy
```

Fly 自动读 `fly.toml`，配 Tokyo 区域（国内最快）。部署完拿到 `https://shadowblade-backend.fly.dev`。

**费用**：免费 3 个共享 VM + 3 GB 持久 disk。

---

## 第 2 步：前端 Vercel 配环境变量

你的 Vercel 已经在跑了（`frontend-next-two-lac.vercel.app`），git push 后会自动重建。要让它能调后端，**加 2 个环境变量**：

1. 打开 [Vercel Dashboard](https://vercel.com/dashboard) → 选 `frontend-next` 项目 → **Settings → Environment Variables**
2. 加 2 行（**值用上一步拿到的 URL**）：

   | Key | Value | 作用 |
   |---|---|---|
   | `BACKEND_URL` | `https://shadowblade-backend.up.railway.app` | Next.js rewrites（`/api/v1/*` 代理到后端）|
   | `NEXT_PUBLIC_STATIC_BASE` | `https://shadowblade-backend.up.railway.app/static` | `<video src>` 直接拉后端的 MP4 |

3. **Deployments → 最新一条 → ... → Redeploy** （让环境变量生效）

完成。打开 `https://frontend-next-two-lac.vercel.app/studio`，点立即生成视频，应该真能出片了。

---

## 第 3 步（可选）：配 API key

部署后端后，去 Studio 页面右上 **"🔑 API keys"** 按钮，粘 Pexels / OpenAI / DeepSeek key 进去即可。后端会写到 `~/.shadowblade/secrets.json`（Railway / Render / Fly 都是 root 用户，路径是 `/root/.shadowblade/secrets.json`），下次重启仍然在。

或者通过环境变量在 Railway dashboard 直接设：
- `PEXELS_API_KEY`
- `OPENAI_API_KEY`
- `DEEPSEEK_API_KEY`
- `ANTHROPIC_API_KEY`

---

## 验证清单

```bash
# 1. 后端健康
curl https://<your-backend>/api/v1/health

# 2. 通过 Vercel rewrite 调后端
curl https://frontend-next-two-lac.vercel.app/api/v1/health

# 3. 列出 keys
curl https://frontend-next-two-lac.vercel.app/api/v1/keys

# 4. 端到端跑一次（自动按主题搜素材）
curl -X POST https://frontend-next-two-lac.vercel.app/api/v1/generate \
  -H 'content-type: application/json' \
  -d '{
    "topic":"春季美容护肤套餐 - 新客首单 5 折",
    "stock_source":"search",
    "stock_query":"skincare beauty",
    "skip_asr":true,
    "preset":"preview_360_9x16",
    "color_look":"cinematic",
    "length":200
  }'
# → {"job_id":"...","status":"queued",...}
```

---

## 故障排查

| 症状 | 原因 | 解决 |
|---|---|---|
| Vercel `/api/v1/*` 仍然 404 | `BACKEND_URL` 没生效 | 必须 Redeploy 一次环境变量才生效 |
| Studio 点生成 `Failed to fetch` | CORS | 后端 `backend/app/main.py` 的 `cors_origins` 加上你的 Vercel 域 |
| 后端冷启超时 | Render 免费层 sleep | 升级 Render 付费、或换 Railway/Fly |
| 视频生成后播不出 | `NEXT_PUBLIC_STATIC_BASE` 没设 | 看第 2 步 |
| 后端 OOM 挂掉 | faster-whisper base 模型要 1.5GB | 切到 Railway 1 GB plan 或更大 |
| 关键词搜索超时 | yt-dlp 搜 YouTube 太慢 | 用 `stock_source=pexels` 或换 archive.org-only 搜索 |
| Pexels test 失败 | key 错或 IP 被屏 | dashboard 检查 key + 试用 curl 直接 hit Pexels |

---

## 别人 fork 你的 repo 后怎么部署

1. fork `zhongrenfei1-hub/shadowblade`
2. **Vercel** Import 自己 fork 的 repo → 自动建项目
3. **Railway** Deploy from GitHub repo → 选 fork
4. 把 Railway URL 配到 Vercel 的 `BACKEND_URL`
5. 完成

整套部署成本 0–$12/月，看选哪家。

---

## 为什么不能全栈 Vercel？

| 限制 | 影响 |
|---|---|
| Serverless function 60 秒超时（pro）/ 10 秒（hobby） | 一次混剪要 10–60 秒 ❌ |
| 函数内存上限 1 GB | faster-whisper base 模型 1.5 GB ❌ |
| 没 ffmpeg / yt-dlp 二进制 | 整套混剪栈跑不了 ❌ |
| 没持久 storage | 渲染输出无法保存 ❌ |
| 函数体最大 50 MB | 镜像装不下依赖 ❌ |

**结论**：前端归 Vercel，后端归一个真服务器。这是 Next.js + 重计算后端的标准模式。
