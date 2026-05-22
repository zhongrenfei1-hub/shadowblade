"""Template CLI — ``python -m app.services.template <command>``.

Commands
========

list                          show every discoverable template (one row per)
show NAME                     dump one fully-resolved template as JSON
validate FILE                 validate a JSON file against the Template schema
schema                        dump the Pydantic-generated JSON Schema
diff NAME_A NAME_B            field-level diff between two resolved templates
search-paths                  print the ordered template search path

All commands exit 0 on success, non-zero on error. ``--quiet`` suppresses
the human-readable header and keeps the JSON payload clean for piping.

Examples::

    python -m app.services.template list
    python -m app.services.template show product-demo --quiet > resolved.json
    python -m app.services.template validate templates/new.json
    python -m app.services.template schema | jq '.properties | keys'
    python -m app.services.template diff product-demo product-demo-tutorial
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from app.services.template import (
    Template,
    TemplateNotFoundError,
    list_templates,
    load_template,
    template_search_paths,
)


def _eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


# ---------- commands -------------------------------------------------------


def cmd_list(args: argparse.Namespace) -> int:
    summaries = list_templates()
    if args.json:
        payload = [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "extends": s.extends,
                "tags": list(s.tags),
                "builtin": s.builtin,
                "source": s.source,
            }
            for s in summaries
        ]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    if not summaries:
        _eprint("(no templates discovered)")
        return 0
    name_w = max(len(s.name) for s in summaries)
    for s in summaries:
        flag = "B" if s.builtin else "U"
        extends = f"  ← {s.extends}" if s.extends else ""
        tags = ", ".join(s.tags[:4])
        if len(s.tags) > 4:
            tags += ", …"
        print(f"  [{flag}] {s.name:<{name_w}}  {tags}{extends}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    try:
        tmpl = load_template(args.name, fresh=True)
    except TemplateNotFoundError as exc:
        _eprint(f"error: {exc}")
        return 2
    print(json.dumps(tmpl.model_dump(), ensure_ascii=False, indent=2))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    path = Path(args.file).expanduser().resolve()
    if not path.exists():
        _eprint(f"error: file not found: {path}")
        return 2
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _eprint(f"error: malformed JSON: {exc}")
        return 2
    raw.setdefault("name", path.stem)
    try:
        tmpl = Template.model_validate(raw)
    except Exception as exc:  # ValidationError, etc.
        _eprint(f"validation failed for {path}:")
        _eprint(str(exc))
        return 1
    if not args.quiet:
        print(f"  ✓ {path.name} → {tmpl.name} v{tmpl.version}")
    return 0


def cmd_schema(args: argparse.Namespace) -> int:
    print(json.dumps(Template.model_json_schema(), ensure_ascii=False, indent=2))
    return 0


def cmd_diff(args: argparse.Namespace) -> int:
    try:
        a = load_template(args.name_a, fresh=True)
        b = load_template(args.name_b, fresh=True)
    except TemplateNotFoundError as exc:
        _eprint(f"error: {exc}")
        return 2
    da = a.model_dump()
    db = b.model_dump()
    differences = _diff_dict(da, db)
    if args.json:
        print(json.dumps(differences, ensure_ascii=False, indent=2))
        return 0
    if not differences:
        print(f"  (no differences between {args.name_a} and {args.name_b})")
        return 0
    print(f"  {args.name_a}  →  {args.name_b}")
    for path, (av, bv) in differences.items():
        print(f"    {path:30s}  {av!r:>20s}  →  {bv!r}")
    return 0


def cmd_search_paths(args: argparse.Namespace) -> int:
    for p in template_search_paths():
        marker = "  (exists)" if p.is_dir() else "  (missing)"
        print(f"  {p}{marker}")
    return 0


def _diff_dict(a: dict, b: dict, prefix: str = "") -> dict[str, tuple[Any, Any]]:
    out: dict[str, tuple[Any, Any]] = {}
    keys = set(a) | set(b)
    for k in sorted(keys):
        path = f"{prefix}.{k}" if prefix else k
        av, bv = a.get(k, "<missing>"), b.get(k, "<missing>")
        if isinstance(av, dict) and isinstance(bv, dict):
            out.update(_diff_dict(av, bv, prefix=path))
        elif av != bv:
            out[path] = (av, bv)
    return out


# ---------- entry point ----------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m app.services.template",
        description="ShadowBlade video-template CLI",
    )
    p.add_argument("--quiet", action="store_true", help="Suppress human-readable headers.")
    sub = p.add_subparsers(dest="command", required=True)

    s_list = sub.add_parser("list", help="List discoverable templates.")
    s_list.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    s_list.set_defaults(func=cmd_list)

    s_show = sub.add_parser("show", help="Dump one resolved template as JSON.")
    s_show.add_argument("name")
    s_show.set_defaults(func=cmd_show)

    s_val = sub.add_parser("validate", help="Validate a JSON file against the schema.")
    s_val.add_argument("file")
    s_val.set_defaults(func=cmd_validate)

    s_sch = sub.add_parser("schema", help="Dump the Pydantic-generated JSON Schema.")
    s_sch.set_defaults(func=cmd_schema)

    s_diff = sub.add_parser("diff", help="Field-level diff between two resolved templates.")
    s_diff.add_argument("name_a")
    s_diff.add_argument("name_b")
    s_diff.add_argument("--json", action="store_true")
    s_diff.set_defaults(func=cmd_diff)

    s_paths = sub.add_parser("search-paths", help="Print the template search path.")
    s_paths.set_defaults(func=cmd_search_paths)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover — exercised via subprocess in tests
    raise SystemExit(main())
