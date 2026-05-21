# Empty-state showcase assets

Pass-002 of the Showcase ring shipped a set of empty-state SVGs in `showcase/empty/`. Only one is wired into the product so far; the others are queued for routes that do not yet have an empty-state surface.

## Wired

| Asset | Route | Trigger |
| --- | --- | --- |
| `showcase/empty/empty-inbox.svg` | `frontend/public/notifications.html` | Surfaces when the user selects the **Archived** tab (see inline `<script>` at the bottom of the page). |

## Pending — pull in as routes ship empty-state UI

| Asset | Suggested route | Trigger |
| --- | --- | --- |
| `showcase/empty/empty-projects.svg` | `frontend/public/projects.html` | When `loadProjects()` returns zero rows (or filters resolve to none). Use as the centred figure inside `.sb-content` with a "Start a new project" CTA. |
| `showcase/empty/empty-assets.svg` | `frontend/public/assets.html` | When the asset library is empty for a freshly-onboarded workspace, or when a tag/filter combination matches nothing. |
| `showcase/empty/empty-queue.svg` | `frontend/public/render-queue.html` | When no jobs are in flight (rare but real in off-hours). Position above the priorities table. |
| `showcase/empty/empty-search.svg` | Any topbar search that returns zero results — `projects.html`, `templates.html`, `assets.html`, `team.html`. Render below the search input. |

## Authoring notes

- Every empty-state SVG follows the same vocabulary as the rest of `showcase/` — deep navy + graphite ground, accent cyan-green focal element, ≤ 50 KB, no remote fonts.
- Wire them with `<img src="/showcase/empty/...svg" alt="" />` (decorative) sitting inside a `.sb-empty-state` block. The class is defined in `notifications.html`; promote it to `styles/app.css` once a second route adopts it.
- Always pair the SVG with a short headline + one sentence of body copy so screen-reader users get the same message even when the image is decorative.
