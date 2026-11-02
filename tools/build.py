#!/usr/bin/env python3
"""Builds the profile README (EN + PT-BR) and every SVG it shows, from tools/content.py.

GitHub strips JavaScript and web fonts from READMEs, so each display block is an SVG with
Funnel Display / Funnel Sans converted to outlines at build time (HarfBuzz shaping, kerning
included). Nothing is loaded when the image is viewed. Motion is plain CSS inside the SVG and
stops under prefers-reduced-motion.

    pip install -r tools/requirements.txt
    python tools/build.py
"""

from __future__ import annotations

import io
import shutil
import sys
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

try:
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover - guidance for first run
    sys.exit(f"Missing dependency '{exc.name}'. Run: pip install -r tools/requirements.txt")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import content as C  # noqa: E402

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
ASSETS = ROOT / "assets"
W = 1000  # viewBox width. GitHub scales every block to the README column (~830px on desktop).

ARROW_UP_RIGHT = '<path d="M7 17L17 7M7 7h10v10"/>'
ARROW_DOWN_RIGHT = '<path d="M6 6l12 12M18 8v10H8"/>'
GLOBE = '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 2.8 3.9 5.8 3.9 9s-1.3 6.2-3.9 9c-2.6-2.8-3.9-5.8-3.9-9s1.3-6.2 3.9-9z"/>'


def num(value: float) -> str:
    text = f"{value:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return "0" if text == "-0" else text


# ---------------------------------------------------------------- type


class Face:
    """A variable font loaded once; HarfBuzz instances are cached per weight."""

    def __init__(self, path: Path) -> None:
        if not path.exists():
            sys.exit(f"Font not found: {path}")
        font = TTFont(path)
        font.flavor = None  # woff2 -> sfnt, which HarfBuzz reads directly
        buffer = io.BytesIO()
        font.save(buffer)
        self.face = hb.Face(buffer.getvalue())
        self.upem = self.face.upem
        self.cap = font["OS/2"].sCapHeight / self.upem
        self.ascent = font["hhea"].ascent / self.upem
        self.descent = -font["hhea"].descent / self.upem
        self._instances: dict[int, hb.Font] = {}

    def at(self, weight: int) -> hb.Font:
        if weight not in self._instances:
            instance = hb.Font(self.face)
            instance.set_variations({"wght": weight})
            self._instances[weight] = instance
        return self._instances[weight]


DISPLAY = Face(TOOLS / "fonts" / "funnel-display.woff2")
SANS = Face(TOOLS / "fonts" / "funnel-sans.woff2")


@dataclass(frozen=True)
class Type:
    face: Face
    weight: int
    size: float
    tracking: float = 0.0  # em, like CSS letter-spacing

    @property
    def cap(self) -> float:
        return self.face.cap * self.size

    @property
    def center(self) -> float:
        """Distance from baseline up to the centre of a CSS line box (used for flex items-center)."""
        return (self.face.ascent - self.face.descent) / 2 * self.size

    def _shape(self, text: str) -> tuple[list[tuple[int, float, float]], float]:
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.face.at(self.weight), buffer, {"kern": True, "liga": True})
        scale = self.size / self.face.upem
        track = self.tracking * self.size
        glyphs, x = [], 0.0
        for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions):
            glyphs.append((info.codepoint, x + pos.x_offset * scale, pos.y_offset * scale))
            x += pos.x_advance * scale + track
        return glyphs, (x - track if glyphs else 0.0)

    def width(self, text: str) -> float:
        return self._shape(text)[1]

    def glyphs(self, text: str, x: float, anchor: str = "start") -> tuple[list[tuple[int, float, float]], float]:
        """Shaped glyph ids with absolute pen positions, honouring the anchor."""
        glyphs, width = self._shape(text)
        if anchor == "end":
            x -= width
        elif anchor == "middle":
            x -= width / 2
        return [(gid, x + gx, gy) for gid, gx, gy in glyphs], width

    def glyph_outline(self, gid: int) -> str:
        """One glyph drawn at the origin (baseline y=0), for reuse through <use>."""
        scale = self.size / self.face.upem
        pen = SVGPathPen(None, ntos=num)
        self.face.at(self.weight).draw_glyph_with_pen(gid, TransformPen(pen, (scale, 0, 0, -scale, 0, 0)))
        return pen.getCommands()

    @property
    def space(self) -> float:
        return self.width("a a") - 2 * self.width("a")

    def wrap(self, text: str, max_width: float) -> list[str]:
        lines: list[str] = []
        current = ""
        for word in text.split():
            candidate = f"{current} {word}" if current else word
            if current and self.width(candidate) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        return lines


def display(size: float, weight: int = 600, tracking: float = -0.045) -> Type:
    return Type(DISPLAY, weight, size, tracking)


def sans(size: float, weight: int = 400) -> Type:
    return Type(SANS, weight, size)


# ---------------------------------------------------------------- svg


@dataclass
class Svg:
    label: str
    width: float = W
    height: float = 0
    css: list[str] = field(default_factory=list)
    defs: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    glyph_ids: dict[tuple, str] = field(default_factory=dict)

    def _glyph(self, t: Type, gid: int) -> str | None:
        """Each glyph is defined once per type style and reused, which keeps text-heavy blocks small."""
        key = (id(t.face), t.weight, t.size, gid)
        if key not in self.glyph_ids:
            d = t.glyph_outline(gid)
            if not d:
                self.glyph_ids[key] = ""
            else:
                ref = f"g{len(self.glyph_ids)}"
                self.glyph_ids[key] = ref
                self.defs.append(f'<path id="{ref}" d="{d}"/>')
        return self.glyph_ids[key] or None

    def text(self, t: Type, text: str, x: float, y: float, fill: str, anchor: str = "start", opacity: float | None = None) -> float:
        glyphs, width = t.glyphs(text, x, anchor)
        uses = []
        for gid, gx, gy in glyphs:
            ref = self._glyph(t, gid)
            if ref:
                uses.append(f'<use href="#{ref}" x="{num(gx)}" y="{num(y - gy)}"/>')
        if uses:
            extra = f' fill-opacity="{opacity}"' if opacity is not None else ""
            self.body.append(f'<g fill="{fill}"{extra}>{"".join(uses)}</g>')
        return width

    def lines(self, t: Type, lines: list[str], x: float, y: float, leading: float, fill: str, anchor: str = "start", opacity: float | None = None) -> float:
        """Draws stacked lines starting at baseline y; returns the last baseline."""
        for index, line in enumerate(lines):
            self.text(t, line, x, y + index * leading, fill, anchor, opacity)
        return y + (len(lines) - 1) * leading

    def rect(self, x: float, y: float, w: float, h: float, fill: str, rx: float = 0) -> None:
        radius = f' rx="{num(rx)}"' if rx else ""
        self.body.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"{radius} fill="{fill}"/>')

    def icon(self, inner: str, x: float, y: float, size: float, stroke: str, stroke_width: float, cls: str = "") -> None:
        scale = size / 24
        group_class = f' class="{cls}"' if cls else ""
        self.body.append(
            f'<g transform="translate({num(x)} {num(y)}) scale({scale:.4f})" fill="none" stroke="{stroke}" '
            f'stroke-width="{stroke_width}" stroke-linecap="square"><g{group_class}>{inner}</g></g>'
        )

    def render(self) -> str:
        style = ""
        if self.css:
            style = "<style>" + "".join(self.css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>"
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        h = num(self.height)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{num(self.width)}" height="{h}" '
            f'viewBox="0 0 {num(self.width)} {h}" role="img" aria-labelledby="title">'
            f'<title id="title">{escape(self.label)}</title>{style}{defs}{"".join(self.body)}</svg>\n'
        )


def color_of(key: str, theme: dict[str, str]) -> str:
    return theme[key] if key in theme else C.COLORS[key]


SQUARE_CYCLE = ["rotor", "prazinho", "talos", "rigor", "rr"]


def marquee(
    svg: Svg,
    key: str,
    items: list[str],
    t: Type,
    baseline: float,
    fill: str,
    *,
    direction: int,
    speed: float,
    pad_left: float,
    pad_right: float,
    square: float,
    gap_after: float,
    square_drop: float = 0.0,
) -> None:
    """A row of words separated by coloured squares that loops forever (two identical copies)."""
    ids: dict[str, str] = {}
    widths: dict[str, float] = {}
    for item in items:
        if item in ids:
            continue
        ids[item] = f"{key}{len(ids)}"
        glyphs, widths[item] = t.glyphs(item, 0)
        uses = "".join(
            f'<use href="#{ref}" x="{num(gx)}" y="{num(-gy)}"/>'
            for gid, gx, gy in glyphs
            if (ref := svg._glyph(t, gid))
        )
        svg.defs.append(f'<g id="{ids[item]}">{uses}</g>')

    em = t.size
    side = square * em
    square_y = baseline - t.center + square_drop * em - side / 2
    parts, x = [], 0.0
    for index, item in enumerate(items):
        x += pad_left * em
        parts.append(f'<use href="#{ids[item]}" x="{num(x)}" y="{num(baseline)}"/>')
        x += widths[item] + pad_right * em
        colour = C.COLORS[SQUARE_CYCLE[index % len(SQUARE_CYCLE)]]
        parts.append(f'<rect x="{num(x)}" y="{num(square_y)}" width="{num(side)}" height="{num(side)}" fill="{colour}"/>')
        x += side + gap_after * em
    copy_width = x
    copy = "".join(parts)

    start, end = (0, -copy_width) if direction < 0 else (-copy_width, 0)
    duration = copy_width / speed
    svg.css.append(
        f".{key}{{animation:{key} {duration:.1f}s linear infinite}}"
        f"@keyframes {key}{{from{{transform:translateX({num(start)}px)}}to{{transform:translateX({num(end)}px)}}}}"
    )
    svg.body.append(
        f'<g class="{key}" fill="{fill}" transform="translate({num(start)} 0)"><g>{copy}</g>'
        f'<g transform="translate({num(copy_width)} 0)">{copy}</g></g>'
    )


# ---------------------------------------------------------------- blocks


def hero(lang: dict, theme: dict) -> Svg:
    copy = lang["hero"]
    svg = Svg(copy["alt"])

    # Top left: spinning globe chip + where I am.
    svg.body.append(f'<circle cx="28" cy="30" r="28" fill="{theme["fg"]}"/>')
    svg.icon(GLOBE, 28 - 17, 30 - 17, 34, theme["inv"], 1.4, cls="spin")
    svg.css.append(".spin{transform-box:fill-box;transform-origin:center;animation:spin 12s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}")
    meta = display(23, 500, 0)
    svg.text(meta, copy["location"][0], 72, 25, theme["fg"])
    svg.text(meta, copy["location"][1], 72, 53, theme["mute"])

    # Top right: arrow + role.
    svg.icon(ARROW_DOWN_RIGHT, W - 30, 0, 30, theme["fg"], 1.6)
    role = display(38, 500, -0.02)
    svg.lines(role, copy["role"], W, 82, 41, theme["fg"], anchor="end")

    # The name, running, with squares in the project colours.
    name = display(176, 600, -0.045)
    baseline = 170 + name.cap
    marquee(
        svg, "mq", [C.NAME] * 5, name, baseline, theme["fg"],
        direction=-1, speed=95, pad_left=0.12, pad_right=0.28, square=0.16, gap_after=0.28, square_drop=0.06,
    )
    svg.height = baseline + 22
    return svg


def about(lang: dict, theme: dict) -> Svg:
    copy = lang["about"]
    t = display(56, 500, -0.035)
    leading = 1.08 * t.size
    label = sans(22)

    # Build clusters: units that must stay together (a word plus any glued punctuation).
    clusters: list[list[dict]] = []
    alt_words: list[str] = []
    for token in copy["tokens"]:
        kind = token[0]
        if kind == "text":
            for word in token[1].split():
                clusters.append([{"kind": "word", "text": word}])
            alt_words.append(token[1])
        elif kind == "underline":
            clusters.append([{"kind": "word", "text": token[1], "underline": token[2]}])
            alt_words.append(token[1])
        elif kind == "pill":
            clusters[-1].append({"kind": "pill", "color": token[1], "space": True})
        elif kind == "glue":
            clusters[-1].append({"kind": "word", "text": token[1]})
            alt_words[-1] += token[1]

    pill_w, pill_h, pill_drop = 1.6 * t.size, 0.74 * t.size, 0.08 * t.size
    max_width, space = 930, t.space
    for cluster in clusters:
        for unit in cluster:
            unit["width"] = pill_w if unit["kind"] == "pill" else t.width(unit["text"])
            unit["lead"] = space if unit.get("space") else 0.0
    lines: list[list[list[dict]]] = [[]]
    line_width = 0.0
    for cluster in clusters:
        width = sum(unit["lead"] + unit["width"] for unit in cluster)
        needed = width if not lines[-1] else line_width + space + width
        if lines[-1] and needed > max_width:
            lines.append([cluster])
            line_width = width
        else:
            lines[-1].append(cluster)
            line_width = needed

    svg = Svg(" ".join(alt_words).replace(" .", "."))
    top = 70
    svg.text(label, copy["label"], 0, top, theme["mute"])
    baseline = top + 46 + t.cap
    for index, line in enumerate(lines):
        y = baseline + index * leading
        x = 0.0
        for cluster in line:
            for unit in cluster:
                x += unit["lead"]
                if unit["kind"] == "pill":
                    svg.rect(x, y + pill_drop - pill_h, unit["width"], pill_h, C.COLORS[unit["color"]], rx=pill_h / 2)
                else:
                    svg.text(t, unit["text"], x, y, theme["fg"])
                    if "underline" in unit:
                        svg.rect(x, y + 0.11 * t.size, unit["width"], 0.075 * t.size, C.COLORS[unit["underline"]])
                x += unit["width"]
            x += space
    svg.height = baseline + (len(lines) - 1) * leading + 0.3 * t.size
    return svg


def work_header(lang: dict, theme: dict) -> Svg:
    copy = lang["work"]
    svg = Svg(f'{copy["title"]} — {copy["aside"]}')
    baseline = 96
    svg.text(display(40, 500, -0.02), copy["title"], 0, baseline, theme["fg"])
    svg.text(sans(22), copy["aside"], W, baseline, theme["mute"], anchor="end")
    svg.height = baseline + 34
    return svg


def work_row(project: dict, lang: dict, theme: dict, last: bool) -> Svg:
    copy = lang["work"]["projects"][project["slug"]]
    colour = C.COLORS[project["slug"]]
    stack = " · ".join(project["stack"])
    svg = Svg(f'{project["name"]} — {copy["category"]}, {project["year"]}. {copy["line"]} Stack: {stack}.')

    svg.rect(0, 0, W, 1.5, theme["line"])
    name = display(112, 600, -0.045)
    name_baseline = 34 + name.cap
    svg.text(name, project["name"], 0, name_baseline, theme["fg"])

    meta = sans(23)
    meta_baseline = name_baseline - name.cap / 2 + meta.cap / 2
    year_width = svg.text(meta, project["year"], W - 44, meta_baseline, theme["mute"], anchor="end")
    category_end = W - 44 - year_width - 36
    category_width = svg.text(meta, copy["category"], category_end, meta_baseline, theme["mute"], anchor="end")
    svg.rect(category_end - category_width - 21, meta_baseline - meta.cap / 2 - 4.5, 9, 9, colour)
    svg.icon(ARROW_UP_RIGHT, W - 28, meta_baseline - meta.cap / 2 - 14, 28, colour, 2)

    body = sans(26)
    line_baseline = name_baseline + 56
    last_baseline = svg.lines(body, body.wrap(copy["line"], W), 0, line_baseline, 37, theme["fg"])
    stack_baseline = last_baseline + 40
    svg.text(sans(20), stack, 0, stack_baseline, theme["mute"])

    svg.height = stack_baseline + 40
    if last:
        svg.rect(0, svg.height - 1.5, W, 1.5, theme["line"])
    return svg


def also(lang: dict, theme: dict) -> Svg:
    copy = lang["also"]
    svg = Svg(
        f'{copy["title"]}: '
        + " ".join(f'{item["name"]} — {copy["items"][item["name"]]}' for item in C.OTHER_PROJECTS)
        + f' {copy["note"]}'
    )
    heading = display(56, 600, -0.03)
    y = 80 + heading.cap
    svg.text(heading, copy["title"], 0, y, theme["fg"])
    y += 50

    name_t, desc_t, tag_t = display(36, 500, -0.02), sans(22), sans(19)
    desc_leading, desc_width = 33, 420
    for item in C.OTHER_PROJECTS:
        svg.rect(0, y, W, 1.5, theme["line"])
        baseline = y + 26 + name_t.cap
        left = svg.text(name_t, item["name"], 0, baseline, theme["fg"])
        if item.get("url"):
            tag_x = left + 16
            tag_width = svg.text(tag_t, copy["tag"], tag_x, baseline - 4, theme["mute"])
            svg.icon(ARROW_UP_RIGHT, tag_x + tag_width + 2, baseline - 4 - 17, 18, theme["mute"], 2)
            left = tag_x + tag_width + 22
        # The description takes whatever the name leaves, so short rows stay on one line.
        desc_lines = desc_t.wrap(copy["items"][item["name"]], max(desc_width, W - left - 56))
        last = svg.lines(desc_t, desc_lines, W, baseline, desc_leading, theme["mute"], anchor="end")
        y = max(baseline, last) + 28
    svg.rect(0, y, W, 1.5, theme["line"])
    note_baseline = y + 40
    svg.text(sans(19), copy["note"], 0, note_baseline, theme["faint"])
    svg.height = note_baseline + 10
    return svg


def ledger(lang: dict, theme: dict) -> Svg:
    copy = lang["ledger"]
    svg = Svg(
        f'{copy["label"]}: '
        + " ".join(
            f'{item["org"]}, {copy["items"][item["org"]]["role"]} ({copy["items"][item["org"]]["period"]}). {copy["items"][item["org"]]["description"]}'
            for item in C.EXPERIENCE
        )
    )
    label = sans(22)
    svg.text(label, copy["label"], 0, 70, theme["mute"])
    y = 98

    org_t, small, body = display(78, 600, -0.045), sans(21), sans(23)
    pad, col_org = 28, 170
    minus_x = W - pad - 26
    # Role column starts after the widest organisation name, so long names never collide with it.
    col_role = col_org + max(org_t.width(item["org"]) for item in C.EXPERIENCE) + 44
    role_width = minus_x - 28 - col_role
    for item in C.EXPERIENCE:
        data = copy["items"][item["org"]]
        inverted = item["color"] == "fg"
        fill = theme["fg"] if inverted else C.COLORS[item["color"]]
        ink = theme["inv"] if inverted else theme["ink"]

        org_baseline = y + 30 + org_t.cap
        mid = org_baseline - org_t.cap / 2
        small_baseline = mid + small.cap / 2
        role_lines = small.wrap(data["role"], role_width)
        role_top = small_baseline - (len(role_lines) - 1) * 28 / 2
        desc_lines = body.wrap(data["description"], 600)
        desc_baseline = org_baseline + 52
        band_bottom = desc_baseline + (len(desc_lines) - 1) * 37 + 34

        svg.rect(0, y, W, band_bottom - y, fill)
        svg.text(small, data["period"], pad, small_baseline, ink, opacity=0.7)
        svg.text(org_t, item["org"], col_org, org_baseline, ink)
        svg.lines(small, role_lines, col_role, role_top, 28, ink, opacity=0.75)
        svg.rect(minus_x, mid - 1, 26, 2.5, ink)  # open row: the "+" has turned into "−"
        svg.lines(body, desc_lines, col_org, desc_baseline, 37, ink)
        y = band_bottom + 2  # a hairline of page colour between bands
    svg.height = y
    return svg


def stack(lang: dict, theme: dict) -> Svg:
    copy = lang["stack"]
    tools = copy["tools"]
    svg = Svg(f'{copy["label"]}: ' + ", ".join(tools) + ".")
    svg.text(sans(22), copy["label"], 0, 70, theme["mute"])

    t = display(64, 600, -0.035)
    half = (len(tools) + 1) // 2
    first = 100 + t.cap + 8
    second = first + 1.05 * t.size
    common = dict(speed=60, pad_left=0.3, pad_right=0.3, square=0.18, gap_after=0)
    marquee(svg, "sa", tools[:half], t, first, theme["fg"], direction=-1, **common)
    marquee(svg, "sb", tools[half:], t, second, theme["mute"], direction=1, **common)
    svg.height = second + 0.3 * t.size
    return svg


def contact(lang: dict, theme: dict) -> Svg:
    copy = lang["contact"]
    svg = Svg(f'{" ".join(copy["title"])} {C.EMAIL}')
    title = display(150, 600, -0.045)
    first = 90 + title.cap
    last = svg.lines(title, copy["title"], 0, first, 0.88 * title.size, theme["fg"])
    email = display(40, 500, -0.02)
    email_baseline = last + 100
    width = svg.text(email, C.EMAIL, 0, email_baseline, theme["fg"])
    svg.rect(0, email_baseline + 12, width, 2.5, theme["faint"])
    svg.height = email_baseline + 30
    return svg


def text_link(label: str, theme: dict) -> Svg:
    svg = Svg(label)
    t = display(26, 500, -0.01)
    width = svg.text(t, label, 0, 28, theme["fg"])
    svg.icon(ARROW_UP_RIGHT, width + 4, 28 - t.cap - 2, 22, theme["fg"], 2.2)
    svg.rect(0, 36, width, 2, theme["faint"])
    svg.width = width + 30
    svg.height = 44
    return svg


def lang_switch(label: str, active: bool, theme: dict) -> Svg:
    svg = Svg(label)
    t = display(26, 500, -0.01)
    colour = theme["fg"] if active else theme["mute"]
    width = svg.text(t, label, 0, 28, colour)
    if active:
        svg.rect(0, 35, width, 3, theme["fg"])
    else:
        svg.rect(0, 36, width, 2, theme["line"])
    svg.width = width + 2
    svg.height = 44
    return svg


# ---------------------------------------------------------------- readme


def picture(path: str, alt: str, href: str, size: str = 'width="100%"') -> str:
    dark, light = f"assets/{path.format(theme='dark')}.svg", f"assets/{path.format(theme='light')}.svg"
    return (
        f'<a href="{escape(href)}"><picture>'
        f'<source media="(prefers-color-scheme: dark)" srcset="{dark}">'
        f'<source media="(prefers-color-scheme: light)" srcset="{light}">'
        f'<img src="{light}" alt="{escape(alt)}" {size}>'
        f"</picture></a>"
    )


def readme(code: str, lang: dict) -> str:
    pt_url = f"{C.REPO}/blob/main/README.pt-BR.md"
    switch = "&nbsp;&nbsp;&nbsp;".join(
        [
            picture(f"common/{{theme}}/lang-en-{'on' if code == 'en' else 'off'}", lang["switch"]["en"], C.PROFILE, 'height="26"'),
            picture(f"common/{{theme}}/lang-pt-{'on' if code == 'pt' else 'off'}", lang["switch"]["pt"], pt_url, 'height="26"'),
        ]
    )
    base = f"{code}/{{theme}}"
    blocks = [
        picture(f"{base}/hero", lang["hero"]["alt"], C.PORTFOLIO),
        picture(f"{base}/about", render_alt(about, lang), f"{C.PORTFOLIO}#sobre"),
        picture(f"{base}/work", render_alt(work_header, lang), f"{C.PORTFOLIO}#trabalhos"),
    ]
    for index, project in enumerate(C.PROJECTS):
        last = index == len(C.PROJECTS) - 1
        blocks.append(
            picture(
                f"{base}/work-{project['slug']}",
                work_row(project, lang, C.THEMES["light"], last).label,
                f"{C.PORTFOLIO}projetos/{project['slug']}/",
            )
        )
    blocks += [
        picture(f"{base}/also", render_alt(also, lang), C.PORTFOLIO),
        picture(f"{base}/ledger", render_alt(ledger, lang), f"{C.PORTFOLIO}#sobre"),
        picture(f"{base}/stack", render_alt(stack, lang), f"{C.PORTFOLIO}#sobre"),
        picture(f"{base}/contact", render_alt(contact, lang), f"mailto:{C.EMAIL}"),
    ]
    links = lang["contact"]["links"]
    link_row = "&nbsp;&nbsp;&nbsp;&nbsp;".join(
        [
            picture(f"{base}/link-linkedin", links["linkedin"], C.LINKEDIN, 'height="26"'),
            picture(f"{base}/link-portfolio", links["portfolio"], C.PORTFOLIO, 'height="26"'),
            picture(f"{base}/link-email", links["email"], f"mailto:{C.EMAIL}", 'height="26"'),
        ]
    )
    return "\n".join(
        [
            "<!-- Generated by tools/build.py from tools/content.py. Edit those files and rebuild; do not edit this one by hand. -->",
            "",
            f'<p align="right">{switch}</p>',
            "",
            "<div>",
            *blocks,
            "</div>",
            "",
            f"<p>{link_row}</p>",
            "",
            f"<p><sub>{escape(lang['footer'])}</sub></p>",
            "",
        ]
    )


def render_alt(block, lang: dict) -> str:
    return block(lang, C.THEMES["light"]).label


# ---------------------------------------------------------------- main


def write(path: Path, svg: Svg) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg.render(), encoding="utf-8")


def main() -> None:
    if ASSETS.exists():
        shutil.rmtree(ASSETS)

    for theme_name, theme in C.THEMES.items():
        common = ASSETS / "common" / theme_name
        for code, label in C.LANGS["en"]["switch"].items():
            write(common / f"lang-{code}-on.svg", lang_switch(label, True, theme))
            write(common / f"lang-{code}-off.svg", lang_switch(label, False, theme))

        for code, lang in C.LANGS.items():
            out = ASSETS / code / theme_name
            write(out / "hero.svg", hero(lang, theme))
            write(out / "about.svg", about(lang, theme))
            write(out / "work.svg", work_header(lang, theme))
            for index, project in enumerate(C.PROJECTS):
                write(out / f"work-{project['slug']}.svg", work_row(project, lang, theme, index == len(C.PROJECTS) - 1))
            write(out / "also.svg", also(lang, theme))
            write(out / "ledger.svg", ledger(lang, theme))
            write(out / "stack.svg", stack(lang, theme))
            write(out / "contact.svg", contact(lang, theme))
            for key, label in lang["contact"]["links"].items():
                write(out / f"link-{key}.svg", text_link(label, theme))

    for code, lang in C.LANGS.items():
        (ROOT / lang["readme"]).write_text(readme(code, lang), encoding="utf-8")

    count = sum(1 for _ in ASSETS.rglob("*.svg"))
    size = sum(path.stat().st_size for path in ASSETS.rglob("*.svg"))
    print(f"Built README.md, README.pt-BR.md and {count} SVGs ({size / 1024:.0f} KB).")


if __name__ == "__main__":
    main()
