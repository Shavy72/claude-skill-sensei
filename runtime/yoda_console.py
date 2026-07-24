"""yoda_console.py - Sensei skill rendering engine.

Callers: SKILL.md (render_mini / render_normal / render_gross), idle_check.py.
Schema: items = [{icon, title, body, roi, effort, kb_ref}],
        audit = {title, intro, mood, items, pareto_score, why_alignment}
"""

from __future__ import annotations

import os
import sys
import textwrap
from typing import Literal

# Windows: force UTF-8 stdout so the ASCII Yoda + box drawing render correctly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass

# ---------------------------------------------------------------------------
# ANSI 24-bit colour codes (with 256-colour fallback)
# ---------------------------------------------------------------------------
_TRUECOLOR = os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")

if _TRUECOLOR:
    SKIN_GREEN = "\033[38;2;124;179;87m"
    TEXT_GREEN = "\033[38;2;113;208;120m"
    ROBE_BROWN = "\033[38;2;139;90;43m"
    RED = "\033[38;2;220;80;60m"
    YELLOW = "\033[38;2;230;180;50m"
else:
    SKIN_GREEN = "\033[32m"
    TEXT_GREEN = "\033[92m"
    ROBE_BROWN = "\033[33m"
    RED = "\033[91m"
    YELLOW = "\033[93m"

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

Mood = Literal["wise", "angry", "proud", "questioning"]

# ============================================================
# MASTER YODA - 3 variants
# Recognisable features:
#   - long pointed ears left/right
#   - wide wrinkled forehead
#   - large round eyes
#   - brown robe
#
# Colour markers used by _apply_face_colors:
#   ▲      -> DARK_GREEN  (ear tip)
#   ╱ ╲    -> OLIVE_GREEN (ear contour, lips)
#   ▰      -> SKIN_GREEN  (ear centre)
#   ║═╔╚╗╝ -> MID_GREEN   (head frame)
#   ≋      -> OLIVE_GREEN (forehead wrinkles, wise/proud)
#   §      -> ANGER_RED   (forehead wrinkles, angry)
#   ◖ ◗    -> BEARD_WHITE (eye white)
#   ◉      -> EYE_YELLOW  (pupils)
#   ▼      -> BEARD_WHITE (teeth)
#   ▓      -> ROBE_BROWN  (robe)
# ============================================================

# NORMAL - wise, calm eyes, neutral mouth with 2 teeth
ASCII_FACE_NORMAL = r"""
   ▲                             ▲
  ╱╲                             ╱╲
 ╱▰╲╲                           ╱╱▰╲
╱▰▰╲╲╲   ╔═══════════════════╗   ╱╱╱▰▰╲
╲▰▰▰╲══╝                     ╚══╱▰▰▰╱
        ║  ≋  ≋  ≋  ≋  ≋  ≋  ║
        ║                       ║
        ║   ◖◉◗         ◖◉◗    ║
        ║                       ║
        ║       ╱─────╲         ║
        ║      │ ▼   ▼ │        ║
        ║       ╲─────╱         ║
        ╚═══════════════════════╝
                ▓▓▓▓▓▓▓▓▓▓▓
               ▓▓▓▓▓▓▓▓▓▓▓▓▓
              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"""

# ANGRY - slanted brows, snarling mouth with 5 teeth, red forehead wrinkles
ASCII_FACE_ANGRY = r"""
   ▲                             ▲
  ╱╲                             ╱╲
 ╱▰╲╲                           ╱╱▰╲
╱▰▰╲╲╲   ╔═══════════════════╗   ╱╱╱▰▰╲
╲▰▰▰╲══╝                     ╚══╱▰▰▰╱
        ║  §  §  §  §  §  §  ║
        ║                       ║
        ║   ╲◖◉◗╱       ╲◖◉◗╱  ║
        ║                       ║
        ║       ╱─────╲         ║
        ║      │▼▼ ▼ ▼▼│        ║
        ║       ╲─────╱         ║
        ╚═══════════════════════╝
                ▓▓▓▓▓▓▓▓▓▓▓
               ▓▓▓▓▓▓▓▓▓▓▓▓▓
              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"""

# PROUD - relaxed eyes with ─ brows, warm smile curving upwards
ASCII_FACE_PROUD = r"""
   ▲                             ▲
  ╱╲                             ╱╲
 ╱▰╲╲                           ╱╱▰╲
╱▰▰╲╲╲   ╔═══════════════════╗   ╱╱╱▰▰╲
╲▰▰▰╲══╝                     ╚══╱▰▰▰╱
        ║  ≋  ≋  ≋  ≋  ≋  ≋  ║
        ║                       ║
        ║  ─◖◉◗─       ─◖◉◗─   ║
        ║                       ║
        ║       ╲─────╱         ║
        ║      ╱ ▼   ▼ ╲        ║
        ║       ╱─────╲         ║
        ╚═══════════════════════╝
                ▓▓▓▓▓▓▓▓▓▓▓
               ▓▓▓▓▓▓▓▓▓▓▓▓▓
              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _strip_ansi(s: str) -> str:
    """Removes ANSI escape sequences so string lengths can be measured."""
    import re

    return re.sub(r"\033\[[0-9;]*m", "", s)


def _color(text: str, mood: Mood) -> str:
    """Applies the colour that belongs to the given mood."""
    color_map: dict[str, str] = {
        "wise": TEXT_GREEN,
        "angry": RED,
        "proud": BOLD + SKIN_GREEN,
        "questioning": YELLOW,
    }
    c = color_map.get(mood, TEXT_GREEN)
    return f"{c}{text}{RESET}"


def _apply_face_colors(face_str: str) -> str:
    """Character-based colouring for the Yoda ASCII art.

    Every line from the first robe character (▒ or ▓) downwards is painted
    entirely in ROBE_BROWN; above that each character is coloured by its zone.
    """
    # Extended palette (24-bit when available, otherwise fallback)
    if _TRUECOLOR:
        BEARD_WHITE = "\033[38;2;235;235;220m"
        EYE_YELLOW = "\033[38;2;220;180;40m"
        ANGER_RED = "\033[38;2;200;60;40m"
        DARK_GREEN = "\033[38;2;75;125;55m"
        OLIVE_GREEN = "\033[38;2;90;140;65m"
        MID_GREEN = "\033[38;2;105;160;75m"
    else:
        BEARD_WHITE = "\033[97m"
        EYE_YELLOW = "\033[93m"
        ANGER_RED = "\033[91m"
        DARK_GREEN = "\033[32m"
        OLIVE_GREEN = "\033[32m"
        MID_GREEN = "\033[32m"

    lines = face_str.split("\n")
    colored: list[str] = []
    # Detect the robe lines: ▒ (old art) or ▓ (current art)
    robe_start = next(
        (i for i, ln in enumerate(lines) if ("▒" in ln) or ("▓" in ln)),
        9999,
    )

    # Sets for fast lookup
    EAR_TIP = {"▲"}
    EAR_CONTOUR = {"╱", "╲"}
    EAR_CENTRE = {"▰"}
    FRAME = {"║", "═", "╔", "╚", "╗", "╝"}
    WRINKLE_OK = {"≋", "~"}
    WRINKLE_BAD = {"§", "#"}
    EYE_WHITE = {"○", "◖", "◗"}
    EYE_PUPIL = {"◉"}
    LIP = {"─", "│"}
    TOOTH = {"▼"}

    for i, line in enumerate(lines):
        if i >= robe_start:
            colored.append(f"{ROBE_BROWN}{line}{RESET}")
            continue

        # Character-based colouring
        result = SKIN_GREEN
        for ch in line:
            if ch in EAR_TIP:
                result += DARK_GREEN + ch + SKIN_GREEN
            elif ch in EAR_CONTOUR:
                result += OLIVE_GREEN + ch + SKIN_GREEN
            elif ch in EAR_CENTRE:
                result += SKIN_GREEN + ch
            elif ch in FRAME:
                result += MID_GREEN + ch + SKIN_GREEN
            elif ch in WRINKLE_OK:
                result += OLIVE_GREEN + ch + SKIN_GREEN
            elif ch in WRINKLE_BAD:
                result += ANGER_RED + ch + SKIN_GREEN
            elif ch in EYE_WHITE:
                result += BEARD_WHITE + ch + SKIN_GREEN
            elif ch in EYE_PUPIL:
                result += EYE_YELLOW + ch + SKIN_GREEN
            elif ch in LIP:
                result += OLIVE_GREEN + ch + SKIN_GREEN
            elif ch in TOOTH:
                result += BEARD_WHITE + ch + SKIN_GREEN
            else:
                result += ch

        colored.append(result + RESET)

    return "\n".join(colored)


def _box(text: str, width: int = 50) -> str:
    """Speech bubble drawn with box characters.

    Args:
        text:  content (may contain newlines)
        width: inner width of the box

    Returns:
        Multi-line string with a frame.
    """
    lines: list[str] = []
    for raw_line in text.split("\n"):
        wrapped = textwrap.wrap(raw_line, width=width) if raw_line.strip() else [""]
        lines.extend(wrapped)

    top = "╭" + "─" * (width + 2) + "╮"
    bottom = "╰" + "─" * (width + 2) + "╯"
    body = "\n".join(f"│ {line:<{width}} │" for line in lines)
    return f"{top}\n{body}\n{bottom}"


def _pick_face(mood: Mood) -> str:
    """Picks the ASCII face for the given mood."""
    if mood == "angry":
        return ASCII_FACE_ANGRY
    if mood == "proud":
        return ASCII_FACE_PROUD
    return ASCII_FACE_NORMAL


def _side_by_side(left: str, right: str, gap: int = 2) -> str:
    """Places two multi-line strings next to each other."""
    left_lines = left.split("\n")
    right_lines = right.split("\n")
    max_rows = max(len(left_lines), len(right_lines))
    left_width = max((len(_strip_ansi(l)) for l in left_lines), default=0)

    result: list[str] = []
    for i in range(max_rows):
        l = left_lines[i] if i < len(left_lines) else ""
        r = right_lines[i] if i < len(right_lines) else ""
        raw_len = len(_strip_ansi(l))
        padding = left_width - raw_len + gap
        result.append(l + " " * padding + r)
    return "\n".join(result)


# ---------------------------------------------------------------------------
# Public render functions
# ---------------------------------------------------------------------------


def render_mini(text: str, mood: Mood = "wise") -> str:
    """Returns a coloured speech bubble only (no face).

    Args:
        text: Yoda line or short message
        mood: wise | angry | proud | questioning

    Returns:
        ANSI-coloured speech bubble string.
    """
    box = _box(text, width=48)
    colored_box = _color(box, mood)
    return f"\n{colored_box}\n"


def render_normal(items: list[dict], mood: Mood = "wise") -> str:
    """Face on the left + speech bubble on the right + action items below.

    Args:
        items: list of {icon, title, body, roi, effort, kb_ref}
        mood:  mood used for the colouring

    Returns:
        Complete render string.
    """
    face = _apply_face_colors(_pick_face(mood))

    if not items:
        bubble_text = "Hmm. Nothing to say today I have."
    else:
        first = items[0]
        bubble_text = (
            f"[{first.get('icon', '*')}] {first.get('title', '')}\n"
            f"{first.get('body', '')}"
        )

    bubble = _color(_box(bubble_text, width=44), mood)
    header = _side_by_side(face, bubble, gap=2)

    action_lines: list[str] = []
    for idx, item in enumerate(items, 1):
        icon = item.get("icon", "-")
        title = item.get("title", "")
        body = item.get("body", "")
        roi = item.get("roi", "")
        eff = item.get("effort", "")
        kb = item.get("kb_ref", "")

        action_lines.append(f"{BOLD}{idx}. {icon} {title}{RESET}")
        if body:
            action_lines.append(f"   {DIM}{body}{RESET}")
        meta_parts: list[str] = []
        if roi:
            meta_parts.append(f"ROI: {roi}")
        if eff:
            meta_parts.append(f"Effort: {eff}")
        if kb:
            meta_parts.append(f"KB: {kb}")
        if meta_parts:
            action_lines.append(f"   {TEXT_GREEN}{' · '.join(meta_parts)}{RESET}")
        action_lines.append("")

    actions_block = "\n".join(action_lines)
    separator = _color("─" * 60, mood)

    return f"\n{header}\n\n{separator}\n{actions_block}"


def render_gross(audit: dict) -> str:
    """Full audit: face + speech bubble + N action items + Pareto score + why alignment.

    Args:
        audit: {
            title:         str,
            intro:         str,        # Yoda opening line
            mood:          str,
            items:         list[dict], # same shape as render_normal
            pareto_score:  float,      # 0.0-1.0
            why_alignment: str,        # one sentence about the why chain
        }

    Returns:
        Complete audit string.
    """
    mood: Mood = audit.get("mood", "wise")  # type: ignore[assignment]
    title = audit.get("title", "Sensei audit")
    intro = audit.get("intro", "Hmm. Much to say, I have.")
    items = audit.get("items", [])
    pareto = float(audit.get("pareto_score", 0.0))
    why_al = audit.get("why_alignment", "")

    face = _apply_face_colors(_pick_face(mood))
    bubble = _color(_box(f"{title}\n\n{intro}", width=44), mood)
    header = _side_by_side(face, bubble, gap=2)

    separator = _color("═" * 60, mood)
    thin_sep = _color("─" * 60, mood)

    action_lines: list[str] = []
    for idx, item in enumerate(items, 1):
        icon = item.get("icon", "-")
        title_i = item.get("title", "")
        body = item.get("body", "")
        roi = item.get("roi", "")
        eff = item.get("effort", "")
        kb = item.get("kb_ref", "")

        action_lines.append(f"{BOLD}{idx}. {icon} {title_i}{RESET}")
        if body:
            for bline in textwrap.wrap(body, 56):
                action_lines.append(f"   {bline}")
        meta_parts: list[str] = []
        if roi:
            meta_parts.append(f"ROI: {roi}")
        if eff:
            meta_parts.append(f"Effort: {eff}")
        if kb:
            meta_parts.append(f"KB: {kb}")
        if meta_parts:
            action_lines.append(f"   {TEXT_GREEN}{' · '.join(meta_parts)}{RESET}")
        action_lines.append("")

    actions_block = "\n".join(action_lines)

    # Pareto score bar
    bar_width = 40
    filled = int(pareto * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)
    score_line = f"{TEXT_GREEN}Pareto score  [{bar}] {pareto * 100:.0f}%{RESET}"

    why_line = f"{DIM}Why chain: {why_al}{RESET}" if why_al else ""

    parts = [
        f"\n{header}",
        f"\n{separator}",
        actions_block,
        thin_sep,
        score_line,
    ]
    if why_line:
        parts.append(why_line)
    parts.append("")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# CLI demo
# ---------------------------------------------------------------------------


def _demo() -> None:
    """Demo of all 3 render modes."""
    print("\n" + "=" * 70)
    print("DEMO: render_mini (wise)")
    print("=" * 70)
    print(render_mini("Patience you need. Time growth takes.", mood="wise"))

    print("\n" + "=" * 70)
    print("DEMO: render_mini (angry)")
    print("=" * 70)
    print(
        render_mini(
            "A push while the job still runs?! Dangerous this is!", mood="angry"
        )
    )

    print("\n" + "=" * 70)
    print("DEMO: render_normal")
    print("=" * 70)
    demo_items = [
        {
            "icon": "!",
            "title": "Prevent force-push onto the main branch",
            "body": "Happened 3 times this week. A pre-push hook is missing.",
            "roi": "high (data-loss risk)",
            "effort": "15min",
            "kb_ref": "anti_patterns/force_push_master.md",
        },
        {
            "icon": "~",
            "title": "Check the run lock before every push",
            "body": "Running jobs can be corrupted by a parallel deploy.",
            "roi": "medium",
            "effort": "5min",
            "kb_ref": "workflows/run_lock_before_push.md",
        },
    ]
    print(render_normal(demo_items, mood="angry"))

    print("\n" + "=" * 70)
    print("DEMO: render_gross")
    print("=" * 70)
    demo_audit = {
        "title": "Weekly sensei audit",
        "intro": "Much energy you have. Focus is missing, hmm.",
        "mood": "wise",
        "items": demo_items
        + [
            {
                "icon": "+",
                "title": "Keep the components inventory current",
                "body": "Not updated for 3 days.",
                "roi": "medium",
                "effort": "10min",
                "kb_ref": "workflows/components_inventory_ssot.md",
            }
        ],
        "pareto_score": 0.72,
        "why_alignment": "Goal: ship the first release. Every unfixed bug delays it.",
    }
    print(render_gross(demo_audit))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        _demo()
    else:
        print(f"Usage: python {sys.argv[0]} demo")
