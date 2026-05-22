# Templates — 视频剪辑模板框架

这个目录存放**用户自定义的视频剪辑模板** (JSON)。每个模板声明一套
混剪规则(过渡、字幕、节奏、BGM、封面、水印、智能剪辑、编码),
被 `POST /api/v1/mix-video?template=<name>` 引用。

## 文件命名

```
templates/
├── base.json          # 文件名 stem = 模板 slug ("base")
├── social_punchy.json
└── cinematic_calm.json
```

文件名的 stem 即为模板名(`load_template("base")` → `base.json`)。

## 解析顺序

1. `$SHADOWBLADE_TEMPLATES_DIR`(逗号分隔)
2. 本目录 `<repo>/templates/`
3. 内置 `backend/app/services/template/builtin/`

第一个找到的同名文件胜出 —— 你可以在本目录覆盖任何内置模板。

## 字段速查

完整字段定义见 `backend/app/services/template/schema.py`。所有字段
**都是可选的**(`null` = 不覆盖)。按 8 大组分:

| 组         | 字段                                                          |
|-----------|----------------------------------------------------------------|
| transition | `style`, `max_duration`                                        |
| subtitle   | `enabled`, `max_chars_per_line`, `max_lines`, `cps_warn`, `cps_fail`, `size_baseline`, `margin_v_baseline`, `fill_color`, `outline_color` |
| pacing     | `target_shot`, `min_shot`, `max_shot`, `snap_to_beats`, `must_include_hero` |
| audio      | `target_lufs`, `target_tp`, `adaptive_bgm_mix`, `bgm_gain_db`, `duck_threshold_db`, `duck_ratio`, `fade_in`, `fade_out` |
| cover      | `enabled`, `style`, `title_required`, `timestamp_strategy`     |
| watermark  | `enabled`, `position`, `opacity`, `width_pct`, `require_logo`  |
| color      | `look`, `lut_path`, `auto_white_balance`                       |
| encode     | `preset`                                                       |

加上元数据 `name` / `version` / `description` / `extends` / `tags`,
以及未来扩展用的 `extras` (free-form dict)。

## 模板继承

```json
{
  "name": "social_punchy",
  "extends": "base",
  "transition": { "style": "energetic" },
  "color":      { "look": "punchy" }
}
```

`base` 的所有字段先填进来,然后 `social_punchy` 中**非 null** 的字段
覆盖父级。在 `Template.merged_with` 里实现。

## 优先级(谁说了算)

```
用户 POST JSON 显式字段 > 模板字段 > MixVideoRequest 内置默认
```

所以模板永远不会推翻你的显式参数 —— 它只是把没填的位置填上。

## 端点

- `GET  /api/v1/templates`              列出所有可见模板
- `GET  /api/v1/templates/{name}`       返回某模板的解析后完整 JSON
- `POST /api/v1/mix-video` 中加 `"template": "base"` 字段即可

## 创建新模板

最小化的新模板:

```json
{
  "name": "vlog_warm",
  "extends": "base",
  "description": "温暖向 vlog —— 慢节奏 + 暖色调",
  "pacing":     { "target_shot": 5.0, "max_shot": 9.0 },
  "color":      { "look": "warm" },
  "transition": { "style": "calm" }
}
```

放到本目录,重启 API 服务即可生效。
