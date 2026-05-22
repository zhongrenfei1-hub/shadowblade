// Workbench / Studio landing-page driver.
//
// Loads three Workbench endpoints in parallel on mount and re-polls the
// active-tasks endpoint every 5 seconds so the progress bars stay live.
// All API calls go through one helper so a future swap to a different
// host (e.g. Vite proxy) is a single-line change.

(function () {
  'use strict';

  const API_BASE = (window.SHADOWBLADE_API_BASE || 'http://localhost:8000') + '/api/v1';
  const WORKSPACE_ID = window.SHADOWBLADE_WORKSPACE_ID || '1';
  const POLL_INTERVAL_MS = 5000;

  // --- API helper ----------------------------------------------------------
  async function api(path, opts = {}) {
    const url = `${API_BASE}${path}`;
    const headers = {
      'X-Workspace-Id': String(WORKSPACE_ID),
      ...(opts.headers || {}),
    };
    try {
      const res = await fetch(url, { ...opts, headers });
      if (!res.ok) {
        console.warn('[workbench] api error', res.status, path);
        return null;
      }
      return await res.json();
    } catch (err) {
      console.warn('[workbench] fetch failed', path, err);
      return null;
    }
  }

  // --- Formatting helpers --------------------------------------------------
  const STATUS_LABEL = {
    draft: '草稿',
    scripting: '撰写中',
    rendering: '渲染中',
    review: '待审',
    done: '已完成',
    archived: '归档',
    queued: '排队中',
    running: '运行中',
    succeeded: '成功',
    failed: '失败',
    cancelled: '已取消',
  };
  const SOURCE_LABEL = { render_queue: '渲染队列', mix_video: 'MIX 任务' };

  function fmtRelativeTime(iso) {
    if (!iso) return '';
    const dt = new Date(iso);
    const delta = (Date.now() - dt.getTime()) / 1000;
    if (delta < 60) return `${Math.max(1, Math.round(delta))} 秒前`;
    if (delta < 3600) return `${Math.round(delta / 60)} 分钟前`;
    if (delta < 86400) return `${Math.round(delta / 3600)} 小时前`;
    return `${Math.round(delta / 86400)} 天前`;
  }

  function escapeHtml(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // --- KPI tiles -----------------------------------------------------------
  function renderKpis(kpis) {
    const root = document.getElementById('wb-kpis');
    if (!root || !Array.isArray(kpis)) return;
    root.innerHTML = kpis
      .map(
        (k) => `
          <article class="wb-kpi" data-key="${escapeHtml(k.key)}">
            <span class="wb-kpi__label">${escapeHtml(k.label)}</span>
            <span class="wb-kpi__value">${escapeHtml(String(k.value ?? '—'))}</span>
            <span class="wb-kpi__unit">${escapeHtml(k.unit || '')}</span>
          </article>`
      )
      .join('');
  }

  // --- Brand kit card ------------------------------------------------------
  function renderBrandKit(kit) {
    const body = document.getElementById('wb-brand-body');
    const scopePill = document.getElementById('wb-brand-scope-pill');
    if (!body) return;

    if (!kit) {
      body.innerHTML = `
        <div class="wb-brand-fallback">
          尚未配置品牌套件 — 默认配色将用于下一次渲染。
        </div>`;
      if (scopePill) scopePill.textContent = 'fallback';
      return;
    }

    body.innerHTML = `
      <div class="wb-brand-name">${escapeHtml(kit.name || '默认品牌')}</div>
      <div class="wb-brand-swatch">
        <i style="background:${escapeHtml(kit.primary_color || '#0F2A4A')}"
           title="主色 ${escapeHtml(kit.primary_color || '')}"></i>
        <i style="background:${escapeHtml(kit.accent_color || '#22D3B7')}"
           title="强调色 ${escapeHtml(kit.accent_color || '')}"></i>
        <i style="background:${escapeHtml(kit.secondary_color || '#F5F7FB')}"
           title="次色 ${escapeHtml(kit.secondary_color || '')}"></i>
        <div class="wb-brand-meta">
          ${escapeHtml(kit.font_heading || 'Inter')} ·
          ${escapeHtml(kit.voice || 'alloy-en-female')}
        </div>
      </div>`;
    if (scopePill) {
      scopePill.textContent = kit.scope === 'user' ? '个人覆盖' : '工作区默认';
    }
  }

  // --- Quick actions -------------------------------------------------------
  const ACTION_ICONS = {
    new_video:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
    preview_video:
      '<svg viewBox="0 0 24 24" fill="currentColor"><polygon points="6 4 20 12 6 20 6 4"/></svg>',
    upload_asset:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3v12M5 10l7 7 7-7M5 21h14"/></svg>',
    browse_templates:
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
  };

  function renderQuickActions(actions) {
    const root = document.getElementById('wb-actions');
    if (!root || !Array.isArray(actions)) return;
    root.innerHTML = actions
      .map(
        (a) => `
          <a class="wb-action" href="${escapeHtml(a.href || '#')}">
            <span class="wb-action__icon">${ACTION_ICONS[a.key] || ACTION_ICONS.new_video}</span>
            <span>
              <div class="wb-action__title">${escapeHtml(a.label)}</div>
              <div class="wb-action__desc">${escapeHtml(a.description || '')}</div>
            </span>
            <span class="wb-action__endpoint">${escapeHtml(a.method)} ${escapeHtml(a.endpoint || '')}</span>
          </a>`
      )
      .join('');
  }

  // --- Featured templates --------------------------------------------------
  function renderTemplates(templates) {
    const root = document.getElementById('wb-templates');
    if (!root) return;
    if (!Array.isArray(templates) || templates.length === 0) {
      root.innerHTML = `
        <div class="wb-empty" style="grid-column:1 / -1">
          <b>暂无模板。</b><br/>
          稍后再来，或直接 <a href="/new-video.html">从零开始</a>。
        </div>`;
      return;
    }
    root.innerHTML = templates
      .map((t) => {
        const tags = Array.isArray(t.tags)
          ? t.tags.slice(0, 3).map((tg) => `<span>${escapeHtml(tg)}</span>`).join('')
          : '';
        const builtinBadge = t.builtin ? '<span class="wb-tpl__badge">内置</span>' : '';
        return `
          <a class="wb-tpl" href="${escapeHtml(t.href || '/new-video.html')}">
            <div class="wb-tpl__name">${escapeHtml(t.name)}${builtinBadge}</div>
            <div class="wb-tpl__desc">${escapeHtml(t.description || '可直接使用的模板配置')}</div>
            <div class="wb-tpl__tags">${tags}</div>
          </a>`;
      })
      .join('');
  }

  // --- Recent projects -----------------------------------------------------
  function renderProjects(projects) {
    const root = document.getElementById('wb-projects');
    if (!root) return;
    if (!Array.isArray(projects) || projects.length === 0) {
      root.innerHTML = `
        <div class="wb-empty" style="grid-column:1 / -1">
          <b>还没有项目。</b><br/>
          点击右上角「新建视频」开始你的第一个项目。
        </div>`;
      return;
    }
    root.innerHTML = projects
      .map((p) => {
        const statusClass = `wb-proj__status--${escapeHtml(p.status || 'draft')}`;
        return `
          <a class="wb-proj" href="${escapeHtml(p.href_open)}">
            <div class="wb-proj__head">
              <span class="wb-proj__name">${escapeHtml(p.name)}</span>
              <span class="wb-proj__status ${statusClass}">${escapeHtml(STATUS_LABEL[p.status] || p.status || '')}</span>
            </div>
            <div class="wb-proj__brief">${escapeHtml(p.brief || '尚无简报')}</div>
            <div class="wb-proj__meta">
              <span>${escapeHtml(p.aspect_ratio || '—')}</span>
              <span>${escapeHtml(String(p.duration_seconds || 0))} 秒</span>
              <span>${escapeHtml(fmtRelativeTime(p.updated_at))}</span>
            </div>
          </a>`;
      })
      .join('');
  }

  // --- Active tasks --------------------------------------------------------
  function renderTasks(items) {
    const root = document.getElementById('wb-tasks');
    const pill = document.getElementById('wb-task-pill');
    const livePill = document.getElementById('wb-live-pill');
    const liveCount = document.getElementById('wb-live-count');
    if (!root) return;

    const liveItems = (items || []).filter(
      (t) => t.status === 'running' || t.status === 'queued'
    );

    if (liveItems.length === 0) {
      root.innerHTML = `
        <div class="wb-empty">
          <b>暂无进行中任务。</b><br/>
          按下「新建视频」开始第一个渲染。
        </div>`;
      if (pill) pill.style.display = 'none';
      if (livePill) livePill.style.display = 'none';
      return;
    }

    if (pill) pill.style.display = 'inline-flex';
    if (livePill) livePill.style.display = 'inline-flex';
    if (liveCount) liveCount.textContent = String(liveItems.length);

    root.innerHTML = (items || [])
      .map((t) => {
        const pct = Math.max(0, Math.min(1, Number(t.progress) || 0));
        const pctText = `${Math.round(pct * 100)}%`;
        const name =
          t.project_name ||
          (t.project_id ? `项目 #${escapeHtml(String(t.project_id))}` : '匿名任务');
        const sub = [
          STATUS_LABEL[t.status] || t.status,
          t.preset || '',
          t.priority ? `优先级 ${t.priority}` : '',
          t.worker ? `worker ${t.worker}` : '',
        ]
          .filter(Boolean)
          .join(' · ');
        return `
          <div class="wb-task wb-task--${escapeHtml(t.status)}">
            <span class="wb-task__source">${escapeHtml(SOURCE_LABEL[t.source] || t.source)}</span>
            <div>
              <div class="wb-task__name">${escapeHtml(name)}</div>
              <div class="wb-task__meta">${escapeHtml(sub)}</div>
              <div class="wb-task__bar"><i style="transform:scaleX(${pct})"></i></div>
            </div>
            <span class="wb-task__pct">${pctText}</span>
          </div>`;
      })
      .join('');
  }

  function setFooter(text) {
    const el = document.getElementById('wb-footer-meta');
    if (el) el.textContent = text;
  }

  // --- Boot ---------------------------------------------------------------
  async function loadOverview() {
    const data = await api('/workbench/overview');
    if (!data) return null;
    renderKpis(data.kpis);
    renderBrandKit(data.brand_kit);
    renderQuickActions(data.quick_actions);
    renderTemplates(data.featured_templates);
    setFooter(
      `工作区 #${data.workspace_id} · 数据生成于 ${fmtRelativeTime(data.generated_at) || '刚刚'}`
    );
    return data;
  }

  async function loadProjects() {
    const data = await api('/workbench/recent-projects?limit=8');
    if (!data) return null;
    renderProjects(data.items);
    return data;
  }

  async function loadTasks() {
    const data = await api('/workbench/active-tasks');
    if (!data) return null;
    renderTasks(data.items);
    return data;
  }

  function bootstrap() {
    Promise.all([loadOverview(), loadProjects(), loadTasks()]);
    // Poll just the volatile surface — the dashboard rest of the page is
    // session-stable so re-fetching it every 5 seconds would burn cycles.
    setInterval(loadTasks, POLL_INTERVAL_MS);

    // Refresh KPIs at a slower cadence so 'renders today' nudges up after a
    // job finishes without poking the heavier overview endpoint on every tick.
    setInterval(loadOverview, POLL_INTERVAL_MS * 6);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }
})();
