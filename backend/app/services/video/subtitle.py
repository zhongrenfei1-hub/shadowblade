"""Smart subtitle generation — SRT + ASS with brand styling.

Inputs:
    - utterance text(s) with start/end seconds (from STT or script)
    - target CPS (characters-per-second) — caps line length
    - max chars per line / max lines on screen
    - brand style (font, primary, accent, outline)

Behaviour:
    - smart_segment: break long utterances at punctuation, then by CPS budget
    - retime: distribute child segment durations proportionally to character
      count so timing reflects pacing rather than equal slicing
    - ASS export: uses brand font, outline, soft drop shadow, fade-in 80ms
    - drawtext fallback for one-off keyword bursts
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# Punctuation tiers (Chinese + English). Tier 1 = hard break, Tier 2 = soft.
_TIER1 = "。！？!?．\n"
_TIER2 = "，、；：,;:—…"


@dataclass(slots=True)
class Cue:
    start: float
    end: float
    text: str
    subtext: str = ""

    @property
    def duration(self) -> float:
        return max(0.001, self.end - self.start)


def load_srt(path):
    """Read an SRT file and return parsed cues."""
    from pathlib import Path as _P

    p = _P(path)
    if not p.exists():
        raise FileNotFoundError(f"SRT not found: {p}")
    return parse_srt(p.read_text(encoding="utf-8"))


from enum import Enum


class SubtitleEntrance(str, Enum):
    """Per-cue entrance animation applied when burning PNG subtitles."""

    NONE = "none"
    FADE = "fade"  # opacity ramp (Pillow path adds its own fade-in)
    POP = "pop"  # scale 0.8→1.0 + fade
    SLIDE_UP = "slide_up"
    TYPEWRITER = "typewriter"  # progressive char reveal (Pillow render)


@dataclass(slots=True)
class SubtitleStyle:
    font: str = "PingFang SC"
    size: int = 64  # ASS units, 1080p baseline
    primary: str = "&H00FFFFFF"  # AABBGGRR
    secondary: str = "&H00FFFFFF"
    outline_color: str = "&H40000000"
    back_color: str = "&H80000000"
    bold: bool = True
    outline: float = 3.0
    shadow: float = 0.0
    alignment: int = 2  # bottom-center
    margin_v: int = 96
    margin_l: int = 96
    margin_r: int = 96


def _split_by_punct(text: str, tier: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    for ch in text:
        buf.append(ch)
        if ch in tier:
            parts.append("".join(buf).strip())
            buf = []
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if p]


def smart_segment(
    cue: Cue,
    *,
    target_cps: float = 9.5,
    max_chars: int = 22,
    max_lines: int = 2,
) -> list[Cue]:
    """Break one long cue into screen-friendly pieces with proportional timing."""
    line_budget = max_chars * max_lines
    if len(cue.text) <= line_budget and cue.duration > 0:
        return [cue]

    # Tier 1 split first
    chunks = _split_by_punct(cue.text, _TIER1)
    refined: list[str] = []
    for chunk in chunks:
        if len(chunk) <= line_budget:
            refined.append(chunk)
            continue
        # Tier 2 fallback
        soft = _split_by_punct(chunk, _TIER2)
        merged: list[str] = []
        current = ""
        for s in soft:
            if not current:
                current = s
            elif len(current) + len(s) <= line_budget:
                current = f"{current} {s}"
            else:
                merged.append(current)
                current = s
        if current:
            merged.append(current)
        # Hard split fallback for un-punctuated long text
        for m in merged:
            if len(m) <= line_budget:
                refined.append(m)
                continue
            for i in range(0, len(m), line_budget):
                refined.append(m[i : i + line_budget])

    # Allocate time proportional to character count, honouring target CPS floor
    char_total = sum(max(1, len(c)) for c in refined) or 1
    pieces: list[Cue] = []
    cursor = cue.start
    total = cue.duration
    for chunk in refined:
        share = max(1, len(chunk)) / char_total
        allocated = total * share
        floor = len(chunk) / target_cps
        dur = max(allocated, floor)
        # Don't exceed parent if floor inflates everything; clamp at end.
        if cursor + dur > cue.end and pieces:
            dur = cue.end - cursor
        pieces.append(Cue(cursor, cursor + dur, _wrap(chunk, max_chars, max_lines)))
        cursor += dur
    if pieces:
        pieces[-1].end = max(pieces[-1].end, cue.end)
    return pieces


def _wrap(text: str, max_chars: int, max_lines: int) -> str:
    """Force at most ``max_lines`` lines, each <= ``max_chars`` chars."""
    if len(text) <= max_chars or max_lines == 1:
        return text[: max_chars * max_lines]
    # Try to break on a tier-2 punctuation near the middle
    midpoint = len(text) // 2
    best = midpoint
    for offset in range(0, midpoint):
        for cand in (midpoint - offset, midpoint + offset):
            if 0 < cand < len(text) and text[cand] in _TIER2:
                best = cand + 1
                break
        else:
            continue
        break
    lines = [text[:best].strip(), text[best:].strip()]
    return "\n".join(line[:max_chars] for line in lines if line)


def segment_utterances(
    cues: Iterable[Cue],
    *,
    target_cps: float = 9.5,
    max_chars: int = 22,
    max_lines: int = 2,
    min_gap: float = 0.04,
) -> list[Cue]:
    """Apply :func:`smart_segment` across many cues, then enforce monotonic gaps."""
    out: list[Cue] = []
    for c in cues:
        out.extend(
            smart_segment(
                c, target_cps=target_cps, max_chars=max_chars, max_lines=max_lines
            )
        )
    for i in range(1, len(out)):
        if out[i].start < out[i - 1].end + min_gap:
            out[i].start = out[i - 1].end + min_gap
            if out[i].end < out[i].start + 0.4:
                out[i].end = out[i].start + 0.4
    return out


def _srt_ts(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t - int(t)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ass_ts(t: float) -> str:
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int((t - int(t)) * 100)
    return f"{h:d}:{m:02d}:{s:02d}.{cs:02d}"


def render_srt(cues: Iterable[Cue]) -> str:
    lines: list[str] = []
    for idx, c in enumerate(cues, start=1):
        lines.append(str(idx))
        lines.append(f"{_srt_ts(c.start)} --> {_srt_ts(c.end)}")
        lines.append(c.text)
        lines.append("")
    return "\n".join(lines)


def render_ass(
    cues: Iterable[Cue],
    *,
    style: SubtitleStyle | None = None,
    video_w: int = 1080,
    video_h: int = 1920,
    fade_ms: int = 80,
    highlight_color: str | None = None,
    highlight_bold: bool = False,
) -> str:
    """Render cues as ASS. When ``highlight_color`` is provided, ``[词]``
    markers in cue text are converted to inline ``{\\1c&HBBGGRR&}`` colour
    overrides so libass renders them in the brand accent colour.
    """
    style = style or SubtitleStyle()
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
WrapStyle: 2
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{style.font},{style.size},{style.primary},{style.secondary},{style.outline_color},{style.back_color},{int(style.bold)},0,0,0,100,100,0,0,1,{style.outline},{style.shadow},{style.alignment},{style.margin_l},{style.margin_r},{style.margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    fade = f"{{\\fad({fade_ms},{fade_ms})}}"
    rows: list[str] = []
    for c in cues:
        if highlight_color:
            from app.services.video.highlight import to_ass_color_override

            transformed = to_ass_color_override(c.text, highlight_color, bold=highlight_bold)
        else:
            from app.services.video.highlight import strip_markers

            transformed = strip_markers(c.text)
        ass_text = transformed.replace("\n", "\\N")
        rows.append(
            f"Dialogue: 0,{_ass_ts(c.start)},{_ass_ts(c.end)},Default,,0,0,0,,{fade}{ass_text}"
        )
    return header + "\n".join(rows) + "\n"


def write_ass(
    cues: Iterable[Cue],
    out_path: str | Path,
    *,
    style: SubtitleStyle | None = None,
    video_w: int = 1080,
    video_h: int = 1920,
    highlight_color: str | None = None,
    highlight_bold: bool = False,
) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        render_ass(
            cues,
            style=style,
            video_w=video_w,
            video_h=video_h,
            highlight_color=highlight_color,
            highlight_bold=highlight_bold,
        ),
        encoding="utf-8",
    )
    return p


def write_srt(cues: Iterable[Cue], out_path: str | Path) -> Path:
    p = Path(out_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render_srt(cues), encoding="utf-8")
    return p


_TIME_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def parse_srt(text: str) -> list[Cue]:
    """Minimal SRT parser for round-tripping in tests."""
    cues: list[Cue] = []
    blocks = re.split(r"\n\s*\n", text.strip())
    for block in blocks:
        lines = [line for line in block.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        m = _TIME_RE.search(lines[1] if len(lines) >= 2 else "")
        idx_offset = 1
        if not m:
            m = _TIME_RE.search(lines[0])
            idx_offset = 0
        if not m:
            continue

        def to_sec(h: str, mn: str, s: str, ms: str) -> float:
            return int(h) * 3600 + int(mn) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000

        start = to_sec(*m.groups()[:4])
        end = to_sec(*m.groups()[4:])
        text_body = "\n".join(lines[idx_offset + 1 :])
        cues.append(Cue(start, end, text_body))
    return cues


@dataclass(slots=True)
class CueQualityIssue:
    cue_index: int
    severity: str  # "info" | "warn" | "fail"
    code: str
    message: str
    cps: float
    char_count: int
    duration: float


@dataclass(slots=True)
class SubtitleQualityReport:
    cues: int
    issues: list[CueQualityIssue]
    max_cps: float
    avg_cps: float

    @property
    def is_ok(self) -> bool:
        return not any(i.severity == "fail" for i in self.issues)


def score_subtitles(
    cues: list[Cue],
    *,
    cps_warn: float = 14.0,
    cps_fail: float = 18.0,
    min_duration: float = 0.6,
    max_duration: float = 7.0,
    min_gap: float = 0.04,
) -> SubtitleQualityReport:
    """Return a per-cue quality report. Useful for surfacing to the UI."""
    issues: list[CueQualityIssue] = []
    cps_values: list[float] = []
    for idx, cue in enumerate(cues):
        chars = len(cue.text.replace("\n", " ").strip())
        cps = chars / cue.duration if cue.duration > 0 else 0.0
        cps_values.append(cps)
        if cue.duration < min_duration:
            issues.append(
                CueQualityIssue(idx, "warn", "too_short",
                                f"cue is {cue.duration:.2f}s — under {min_duration}s",
                                cps, chars, cue.duration)
            )
        if cue.duration > max_duration:
            issues.append(
                CueQualityIssue(idx, "info", "too_long",
                                f"cue is {cue.duration:.2f}s — consider splitting",
                                cps, chars, cue.duration)
            )
        if cps > cps_fail:
            issues.append(
                CueQualityIssue(idx, "fail", "cps_too_high",
                                f"{cps:.1f} cps — unreadable",
                                cps, chars, cue.duration)
            )
        elif cps > cps_warn:
            issues.append(
                CueQualityIssue(idx, "warn", "cps_high",
                                f"{cps:.1f} cps — borderline readable",
                                cps, chars, cue.duration)
            )
        if idx > 0 and cue.start - cues[idx - 1].end < -1e-3:
            issues.append(
                CueQualityIssue(idx, "fail", "overlap",
                                "cue overlaps the previous one",
                                cps, chars, cue.duration)
            )
        elif idx > 0 and 0 <= cue.start - cues[idx - 1].end < min_gap:
            issues.append(
                CueQualityIssue(idx, "info", "tight_gap",
                                f"gap {cue.start - cues[idx - 1].end:.3f}s — flicker risk",
                                cps, chars, cue.duration)
            )
    max_cps = max(cps_values) if cps_values else 0.0
    avg_cps = sum(cps_values) / len(cps_values) if cps_values else 0.0
    return SubtitleQualityReport(
        cues=len(cues), issues=issues, max_cps=max_cps, avg_cps=avg_cps
    )


def adaptive_font_size(
    cue: Cue,
    *,
    base_size: int,
    max_chars_per_line: int = 22,
    line_count: int = 2,
) -> int:
    """Scale font size down when a cue has lots of text. Returns size in
    ASS units (1080p baseline)."""
    capacity = max_chars_per_line * line_count
    chars = len(cue.text.replace("\n", " "))
    if chars <= capacity:
        return base_size
    ratio = capacity / chars
    return max(int(base_size * 0.65), int(round(base_size * ratio)))


def overlay_with_entrance(
    *,
    base_label: str,
    image_label: str,
    start: float,
    end: float,
    entrance: SubtitleEntrance = SubtitleEntrance.FADE,
    duration_in: float = 0.18,
    margin_v_expr: str = "main_h*0.86",
    out_label: str = "[vsub]",
) -> str:
    """Build a single ``overlay=`` chain with the requested entrance.

    Returns a filter fragment that takes ``base_label`` + ``image_label`` and
    produces ``out_label``. The entrance is implemented purely through filter
    expressions — no PNG sequence needed beyond the one-shot cue render.
    """
    duration_in = min(duration_in, max(0.05, (end - start) * 0.5))
    if entrance == SubtitleEntrance.NONE:
        x_expr = "(main_w-overlay_w)/2"
        y_expr = f"{margin_v_expr}-overlay_h/2"
        return (
            f"{base_label}{image_label}overlay="
            f"x='{x_expr}':y='{y_expr}':"
            f"enable='between(t,{start:.3f},{end:.3f})':"
            f"format=auto:eof_action=pass{out_label}"
        )
    if entrance == SubtitleEntrance.SLIDE_UP:
        # y starts margin_v + 60px and eases to margin_v over duration_in
        rise = 60.0
        y_expr = (
            f"if(lt(t,{start + duration_in:.3f}),"
            f"{margin_v_expr}-overlay_h/2+{rise}*(1-(t-{start:.3f})/{duration_in:.3f}),"
            f"{margin_v_expr}-overlay_h/2)"
        )
        return (
            f"{base_label}{image_label}overlay="
            f"x='(main_w-overlay_w)/2':y='{y_expr}':"
            f"enable='between(t,{start:.3f},{end:.3f})':"
            f"format=auto:eof_action=pass{out_label}"
        )
    # FADE / POP / TYPEWRITER (typewriter handled at Pillow render time)
    return (
        f"{base_label}{image_label}overlay="
        f"x='(main_w-overlay_w)/2':y='{margin_v_expr}-overlay_h/2':"
        f"enable='between(t,{start:.3f},{end:.3f})':"
        f"format=auto:eof_action=pass{out_label}"
    )


__all__ = [
    "Cue",
    "SubtitleStyle",
    "SubtitleEntrance",
    "CueQualityIssue",
    "SubtitleQualityReport",
    "smart_segment",
    "segment_utterances",
    "render_srt",
    "render_ass",
    "write_srt",
    "write_ass",
    "parse_srt",
    "score_subtitles",
    "adaptive_font_size",
    "overlay_with_entrance",
]
