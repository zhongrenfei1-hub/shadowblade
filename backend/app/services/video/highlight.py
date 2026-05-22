"""Keyword highlight markers — ``[关键词]`` style in subtitle cues.

The renderers (PNG + ASS) consume the parsed segments and apply a brand
``accent_color`` (青绿) to highlighted spans.

User syntax:

    "让 [SaaS 产品演示] 更专业,只需 [3 步]。"

Parsed → 5 segments:
    [(text="让 ", is_highlight=False),
     (text="SaaS 产品演示", is_highlight=True),
     (text=" 更专业,只需 ", is_highlight=False),
     (text="3 步", is_highlight=True),
     (text="。", is_highlight=False)]

Escaping: use ``\\[`` for a literal ``[``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "HighlightSegment",
    "parse_markers",
    "strip_markers",
    "to_ass_color_override",
    "hex_to_ass_color",
]


@dataclass(slots=True, frozen=True)
class HighlightSegment:
    text: str
    is_highlight: bool


# Match [content] but not \[ ... — the \[ is treated as literal.
# Content may not contain a newline or unescaped ].
_MARKER_RE = re.compile(r"(?<!\\)\[([^\[\]\n]+?)(?<!\\)\]")


def parse_markers(text: str) -> list[HighlightSegment]:
    """Split ``text`` into highlight / plain segments.

    Returns a list of :class:`HighlightSegment` covering the full input.
    Escaped brackets (``\\[`` / ``\\]``) are decoded into literal
    characters in the output segments. Empty segments are dropped.
    """
    out: list[HighlightSegment] = []
    cursor = 0
    for m in _MARKER_RE.finditer(text):
        if m.start() > cursor:
            head = text[cursor : m.start()]
            head = _unescape(head)
            if head:
                out.append(HighlightSegment(head, False))
        kw = _unescape(m.group(1))
        if kw:
            out.append(HighlightSegment(kw, True))
        cursor = m.end()
    tail = text[cursor:]
    tail = _unescape(tail)
    if tail:
        out.append(HighlightSegment(tail, False))
    return out or [HighlightSegment("", False)]


def strip_markers(text: str) -> str:
    """Return ``text`` with all highlight markers removed (escaped chars decoded)."""
    return "".join(s.text for s in parse_markers(text))


def _unescape(s: str) -> str:
    return s.replace(r"\[", "[").replace(r"\]", "]")


# --- ASS helpers ------------------------------------------------------------


def hex_to_ass_color(hex_color: str) -> str:
    """Convert ``#RRGGBB`` to ASS ``&HBBGGRR&`` (alpha implicit 00)."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "&H00FFFFFF&"
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{b.upper()}{g.upper()}{r.upper()}&"


def to_ass_color_override(text: str, color_hex: str, *, bold: bool = False) -> str:
    """Translate ``[词]`` markers into ASS inline color overrides.

    ``{\\1c&HBBGGRR&}词{\\r}`` switches the primary colour for the run and
    ``{\\r}`` resets back to the dialogue style.
    """
    segments = parse_markers(text)
    color = hex_to_ass_color(color_hex)
    bold_open = r"{\b1}" if bold else ""
    bold_close = r"{\b0}" if bold else ""
    parts: list[str] = []
    for seg in segments:
        if seg.is_highlight:
            parts.append(f"{{\\1c{color}}}{bold_open}{seg.text}{bold_close}{{\\r}}")
        else:
            parts.append(seg.text)
    return "".join(parts)
