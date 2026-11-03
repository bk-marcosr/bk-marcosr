#!/usr/bin/env python3
"""Renders the SVG blocks of the profile README (EN + PT-BR, light + dark).

    python .github/readme/build.py            # banner, project cards, stack, contact buttons
    python .github/readme/build.py activity   # activity card (run daily by .github/workflows/activity.yml)

Text is converted to outlines at build time (HarfBuzz shaping, kerning included), so every
viewer sees the same type no matter which fonts their system has. The typing line is plain CSS
inside the SVG and stops under prefers-reduced-motion.
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from html import escape
from pathlib import Path

try:
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
except ImportError as exc:  # pragma: no cover - guidance for first run
    sys.exit(f"Missing dependency '{exc.name}'. Run: pip install -r .github/readme/requirements.txt")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ASSETS = ROOT / "assets"

LOGIN = os.environ.get("PROFILE_LOGIN", "bk-marcosr")
LANGS = ("en", "pt")
THEMES = {
    # Zinc greys; colour only comes from the projects.
    "dark": {"bg": "#18181b", "chip": "#27272a", "icon": "#27272a", "fg": "#fafafa", "mute": "#a1a1aa", "faint": "#71717a", "line": "#3f3f46"},
    "light": {"bg": "#f4f4f5", "chip": "#e4e4e7", "icon": "#e4e4e7", "fg": "#09090b", "mute": "#52525b", "faint": "#a1a1aa", "line": "#d4d4d8"},
}
ACCENT = {"rotor": "#7aa2f7", "prazinho": "#2fc68a", "talos": "#ef5f67", "rigor": "#e9a23b"}

COPY = {
    "en": {
        "location": "Belém, BR · UTC−3",
        "role": "Full stack developer · Founder of BKode",
        "typing": [
            "building Rotor, a trading bot on Binance",
            "shipping Prazinho, finance for small resellers",
            "automating data at RR Chevrolet",
            "studying Information Systems at UFRA",
        ],
        "stack": {"Languages": ["TypeScript", "JavaScript", "Python"], "Frontend": ["React", "NextJS", "Vite", "TailwindCSS"], "Backend": ["NodeJS", "ExpressJS", "Prisma", "Supabase"], "Data": ["PostgreSQL", "Redis", "SQLite"], "Delivery": ["Vitest", "Docker", "GithubActions", "Vercel"]},
        "buttons": {"linkedin": "LinkedIn", "email": "E-mail", "portfolio": "Portfolio"},
        "activity": {"title": "Activity", "aside": "last 12 months", "total": "contributions", "current": "current streak", "longest": "longest streak", "day": "day", "days": "days", "months": "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec", "pending": "Updated daily by a GitHub Action"},
    },
    "pt": {
        "location": "Belém, BR · UTC−3",
        "role": "Desenvolvedor full stack · Fundador da BKode",
        "typing": [
            "construindo o Rotor, robô de trading na Binance",
            "evoluindo o Prazinho, finanças pra revendedor",
            "automatizando dados na RR Chevrolet",
            "cursando Sistemas de Informação na UFRA",
        ],
        "stack": {"Linguagens": ["TypeScript", "JavaScript", "Python"], "Front-end": ["React", "NextJS", "Vite", "TailwindCSS"], "Back-end": ["NodeJS", "ExpressJS", "Prisma", "Supabase"], "Dados": ["PostgreSQL", "Redis", "SQLite"], "Entrega": ["Vitest", "Docker", "GithubActions", "Vercel"]},
        "buttons": {"linkedin": "LinkedIn", "email": "E-mail", "portfolio": "Portfólio"},
        "activity": {"title": "Atividade", "aside": "últimos 12 meses", "total": "contribuições", "current": "sequência atual", "longest": "maior sequência", "day": "dia", "days": "dias", "months": "jan fev mar abr mai jun jul ago set out nov dez", "pending": "Atualizado todo dia por uma GitHub Action"},
    },
}

PROJECTS = [
    {
        "slug": "rotor",
        "name": "Rotor",
        "stack": "React · Supabase · Edge Functions · Binance API",
        "en": ("Trading", "Trading bot running real money on Binance. Every order passes an idempotent lock. Live since September 2026."),
        "pt": ("Trading", "Robô de trading com dinheiro real na Binance. Toda ordem passa por uma trava idempotente. No ar desde setembro de 2026."),
    },
    {
        "slug": "prazinho",
        "name": "Prazinho",
        "stack": "React · TypeScript · Supabase · Vitest",
        "en": ("Finance", "Sales on credit, inventory and month-end close for small resellers. Row-level security on every table."),
        "pt": ("Finanças", "Venda a prazo, estoque e fechamento do mês para pequeno revendedor. RLS em todas as tabelas."),
    },
    {
        "slug": "talos",
        "name": "Talos",
        "stack": "Node.js · Baileys · Gemini · Next.js",
        "en": ("AI support", "WhatsApp support with AI for small businesses. When the model fails, the chat goes to a human instead of waiting."),
        "pt": ("Atendimento IA", "Atendimento no WhatsApp com IA para pequenas empresas. Se o modelo falha, a conversa vai para um humano."),
    },
    {
        "slug": "rigor",
        "name": "Rigor",
        "stack": "Python · SQLite · Supabase · React",
        "en": ("Data", "Fifteen years of CVM filings turned into twelve indicators per B3 company, each traceable to its source."),
        "pt": ("Dados", "Quinze anos de balanços da CVM viram doze indicadores por empresa da B3, cada um rastreável até a origem."),
    },
]

LUCIDE = {
    "mail": '<path d="m22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7"/><rect x="2" y="4" width="20" height="16" rx="2"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
    "arrow": '<path d="M7 7h10v10"/><path d="M7 17 17 7"/>',
}


def num(value: float) -> str:
    text = f"{value:.1f}"
    if text.endswith(".0"):
        text = text[:-2]
    return "0" if text == "-0" else text


# ---------------------------------------------------------------- type


class Face:
    def __init__(self, path: Path) -> None:
        font = TTFont(path)
        font.flavor = None
        buffer = io.BytesIO()
        font.save(buffer)
        self.face = hb.Face(buffer.getvalue())
        self.upem = self.face.upem
        self.cap = font["OS/2"].sCapHeight / self.upem
        self.variable = "fvar" in font
        self._fonts: dict[int, hb.Font] = {}

    def at(self, weight: int) -> hb.Font:
        if weight not in self._fonts:
            instance = hb.Font(self.face)
            if self.variable:
                instance.set_variations({"wght": weight})
            self._fonts[weight] = instance
        return self._fonts[weight]


DISPLAY = Face(HERE / "fonts" / "funnel-display.woff2")
SANS = Face(HERE / "fonts" / "funnel-sans.woff2")
MONO = Face(HERE / "fonts" / "jetbrains-mono.woff2")


@dataclass(frozen=True)
class Type:
    face: Face
    weight: int
    size: float
    tracking: float = 0.0

    @property
    def cap(self) -> float:
        return self.face.cap * self.size

    def shape(self, text: str, x: float = 0.0) -> tuple[list[tuple[int, float, float]], float]:
        buffer = hb.Buffer()
        buffer.add_str(text)
        buffer.guess_segment_properties()
        hb.shape(self.face.at(self.weight), buffer, {"kern": True, "liga": True})
        scale = self.size / self.face.upem
        track = self.tracking * self.size
        glyphs, pen_x = [], 0.0
        for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions):
            glyphs.append((info.codepoint, x + pen_x + pos.x_offset * scale, pos.y_offset * scale))
            pen_x += pos.x_advance * scale + track
        return glyphs, (pen_x - track if glyphs else 0.0)

    def width(self, text: str) -> float:
        return self.shape(text)[1]

    def outline(self, gid: int) -> str:
        scale = self.size / self.face.upem
        pen = SVGPathPen(None, ntos=num)
        self.face.at(self.weight).draw_glyph_with_pen(gid, TransformPen(pen, (scale, 0, 0, -scale, 0, 0)))
        return pen.getCommands()

    def wrap(self, text: str, max_width: float) -> list[str]:
        lines, current = [], ""
        for word in text.split():
            candidate = f"{current} {word}" if current else word
            if current and self.width(candidate) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        return lines + ([current] if current else [])


def display(size: float, weight: int = 600, tracking: float = -0.03) -> Type:
    return Type(DISPLAY, weight, size, tracking)


def sans(size: float, weight: int = 400) -> Type:
    return Type(SANS, weight, size)


def mono(size: float) -> Type:
    return Type(MONO, 400, size)


# ---------------------------------------------------------------- svg


@dataclass
class Svg:
    label: str
    width: float
    height: float
    css: list[str] = field(default_factory=list)
    defs: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)
    glyphs: dict[tuple, str] = field(default_factory=dict)

    def _glyph(self, t: Type, gid: int) -> str:
        key = (id(t.face), t.weight, t.size, gid)
        if key not in self.glyphs:
            d = t.outline(gid)
            self.glyphs[key] = f"g{len(self.glyphs)}" if d else ""
            if d:
                self.defs.append(f'<path id="{self.glyphs[key]}" d="{d}"/>')
        return self.glyphs[key]

    def text(self, t: Type, text: str, x: float, y: float, fill: str, anchor: str = "start", extra: str = "") -> float:
        width = t.width(text)
        if anchor == "end":
            x -= width
        elif anchor == "middle":
            x -= width / 2
        glyphs, _ = t.shape(text, x)
        uses = "".join(f'<use href="#{ref}" x="{num(gx)}" y="{num(y - gy)}"/>' for gid, gx, gy in glyphs if (ref := self._glyph(t, gid)))
        if uses:
            self.body.append(f'<g fill="{fill}"{extra}>{uses}</g>')
        return width

    def rect(self, x: float, y: float, w: float, h: float, fill: str, rx: float = 0, extra: str = "") -> None:
        radius = f' rx="{num(rx)}"' if rx else ""
        self.body.append(f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{num(h)}"{radius} fill="{fill}"{extra}/>')

    def icon(self, name: str, x: float, y: float, size: float, stroke: str, width: float = 2) -> None:
        self.body.append(
            f'<g transform="translate({num(x)} {num(y)}) scale({size / 24:.4f})" fill="none" stroke="{stroke}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{LUCIDE[name]}</g>'
        )

    def render(self) -> str:
        style = ""
        if self.css:
            style = "<style>" + "".join(self.css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}</style>"
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        w, h = num(self.width), num(self.height)
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title">'
            f'<title id="title">{escape(self.label)}</title>{style}{defs}{"".join(self.body)}</svg>\n'
        )


# ---------------------------------------------------------------- blocks


def banner(lang: str, theme: dict) -> Svg:
    copy = COPY[lang]
    W, H = 1000, 300
    svg = Svg(f"Marcos Gabriel — {copy['role']}. {copy['location']}.", W, H)
    svg.defs.append(f'<clipPath id="card"><rect width="{W}" height="{H}" rx="18"/></clipPath>')
    svg.body.append('<g clip-path="url(#card)">')
    svg.rect(0, 0, W, H, theme["bg"])
    # Four project colours as a single hairline across the top.
    for index, colour in enumerate(ACCENT.values()):
        svg.rect(index * W / 4, 0, W / 4, 5, colour)

    meta = mono(15)
    svg.text(meta, "~/bk-marcosr", 44, 56, theme["faint"])
    svg.text(meta, copy["location"], W - 44, 56, theme["faint"], anchor="end")
    svg.text(display(80, 600, -0.035), "Marcos Gabriel", 42, 154, theme["fg"])
    svg.text(sans(24), copy["role"], 44, 196, theme["mute"])

    # Typing line: each phrase is revealed by a cover that slides right in character-sized steps.
    t = mono(22)
    prompt_width = svg.text(t, "$", 44, 252, ACCENT["prazinho"])
    x0 = 44 + prompt_width + t.size * 0.6
    char = t.width("a")
    slots, total = [], 0.0
    for phrase in copy["typing"]:
        n = len(phrase)
        timing = {"type": max(1.2, n * 0.055), "hold": 2.2, "erase": max(0.5, n * 0.02), "gap": 0.35}
        slots.append((phrase, n, total, timing))
        total += sum(timing.values())
    pct = lambda seconds: f"{seconds / total * 100:.3f}%"  # noqa: E731
    top, height = 252 - 22 * 0.82, 22 * 1.12
    for index, (phrase, n, start, timing) in enumerate(slots):
        span = n * char
        typed, held, erased = start + timing["type"], start + timing["type"] + timing["hold"], start + timing["type"] + timing["hold"] + timing["erase"]
        end = start + sum(timing.values())
        first = "0%{opacity:1}" if index == 0 else f"0%{{opacity:0}}{pct(start)}{{opacity:1}}"
        svg.css.append(
            f".v{index}{{animation:v{index} {total:.2f}s step-end infinite}}"
            f"@keyframes v{index}{{{first}{pct(end)}{{opacity:0}}100%{{opacity:0}}}}"
            f".c{index}{{animation:c{index} {total:.2f}s linear infinite}}"
            f"@keyframes c{index}{{0%{{transform:translateX(0)}}"
            f"{pct(start)}{{transform:translateX(0);animation-timing-function:steps({n},end)}}"
            f"{pct(typed)}{{transform:translateX({num(span)}px);animation-timing-function:linear}}"
            f"{pct(held)}{{transform:translateX({num(span)}px);animation-timing-function:steps({n},end)}}"
            f"{pct(erased)}{{transform:translateX(0)}}100%{{transform:translateX(0)}}}}"
        )
        hidden = "" if index == 0 else ' opacity="0"'
        svg.body.append(f'<g class="v{index}"{hidden}>')
        svg.text(t, phrase, x0, 252, theme["fg"])
        svg.body.append(f'<g class="c{index}">')
        svg.rect(x0, top, span + 40, height, theme["bg"])
        svg.rect(x0 + 1, top + 2, char * 0.62, height - 4, theme["fg"], extra=' class="caret"')
        svg.body.append("</g></g>")
    svg.css.append(".caret{animation:blink 1s step-end infinite}@keyframes blink{50%{opacity:0}}")
    # Without motion, show the first phrase fully typed.
    svg.css.append(f"@media (prefers-reduced-motion:reduce){{.c0{{transform:translateX({num(len(slots[0][0]) * char)}px)}}}}")

    svg.text(display(22, 600, -0.02), "BKode", W - 44, 256, theme["faint"], anchor="end")
    svg.body.append("</g>")
    return svg


def card(project: dict, lang: str, theme: dict) -> Svg:
    W, H = 490, 232
    category, description = project[lang]
    colour = ACCENT[project["slug"]]
    svg = Svg(f"{project['name']} — {category}. {description} Stack: {project['stack']}.", W, H)
    svg.rect(0, 0, W, H, theme["bg"], rx=14)

    name = display(30, 600, -0.03)
    svg.rect(28, 50 - name.cap / 2 - 6, 12, 12, colour)
    svg.text(name, project["name"], 50, 50, theme["fg"])

    chip = sans(14, 500)
    chip_w = chip.width(category) + 26
    svg.rect(W - 28 - chip_w, 26, chip_w, 28, theme["chip"], rx=14)
    svg.text(chip, category, W - 28 - chip_w / 2, 45, theme["mute"], anchor="middle")

    body = sans(18)
    for index, line in enumerate(body.wrap(description, W - 56)[:3]):
        svg.text(body, line, 28, 98 + index * 27, theme["fg"])

    svg.rect(28, 168, W - 56, 1, theme["line"])
    svg.text(mono(13.5), project["stack"], 28, 202, theme["mute"])
    svg.icon("arrow", W - 28 - 20, 186, 20, colour, 2.2)
    return svg


def load_icon(name: str, theme_name: str, theme: dict, prefix: str) -> str:
    """Inlines a skill-icons SVG, re-tinting its tile to the card palette and namespacing its ids."""
    path = HERE / "icons" / f"{name}-{theme_name.title()}.svg"
    if not path.exists():
        path = HERE / "icons" / f"{name}.svg"
    source = path.read_text(encoding="utf-8")
    inner = source[source.index(">") + 1 : source.rindex("</svg>")]
    # Only the neutral tiles are re-tinted; brand tiles (TypeScript blue, Docker blue, JS yellow...) stay as they are.
    inner = re.sub(r'fill="#(?:242938|F4F2ED)"', f'fill="{theme["icon"]}"', inner, count=1, flags=re.IGNORECASE)
    ids = set(re.findall(r'id="([^"]+)"', inner))
    for old in ids:
        inner = inner.replace(f'id="{old}"', f'id="{prefix}{old}"').replace(f"url(#{old})", f"url(#{prefix}{old})")
    return inner


def stack(lang: str, theme_name: str, theme: dict) -> Svg:
    groups = COPY[lang]["stack"]
    W, row_h, icon, gap, pad = 1000, 74, 50, 12, 30
    columns = [list(groups.items())[:3], list(groups.items())[3:]]
    rows = max(len(column) for column in columns)
    H = pad * 2 + rows * row_h - (row_h - icon)
    svg = Svg(" · ".join(f"{label}: {', '.join(items)}" for label, items in groups.items()), W, H)
    svg.rect(0, 0, W, H, theme["bg"], rx=14)
    label_t = sans(16, 500)
    for col, column in enumerate(columns):
        x = 32 + col * (W / 2)
        for row, (label, items) in enumerate(column):
            y = pad + row * row_h
            svg.text(label_t, label, x, y + icon / 2 + label_t.cap / 2, theme["mute"])
            for index, item in enumerate(items):
                ix = x + 128 + index * (icon + gap)
                svg.body.append(
                    f'<svg x="{num(ix)}" y="{num(y)}" width="{icon}" height="{icon}" viewBox="0 0 256 256">'
                    f"{load_icon(item, theme_name, theme, f'i{col}{row}{index}')}</svg>"
                )
    return svg


def button(kind: str, label: str, theme: dict) -> Svg:
    t = sans(19, 500)
    width = 28 + 24 + 12 + t.width(label) + 14 + 16 + 24
    svg = Svg(label, width, 56)
    svg.rect(0, 0, width, 56, theme["bg"], rx=28)
    if kind == "linkedin":
        svg.rect(28, 16, 24, 24, "none", rx=5, extra=f' stroke="{theme["fg"]}" stroke-width="2"')
        svg.text(sans(13, 700), "in", 40, 33, theme["fg"], anchor="middle")
    else:
        svg.icon("mail" if kind == "email" else "globe", 28, 16, 24, theme["fg"])
    label_x = 28 + 24 + 12
    label_w = svg.text(t, label, label_x, 35, theme["fg"])
    svg.icon("arrow", label_x + label_w + 12, 20, 16, theme["mute"], 2.2)
    return svg


# ---------------------------------------------------------------- activity


QUERY = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{date contributionCount}}}}}}"""


def fetch_calendar() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is required to render the activity card.")
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": f"{LOGIN}-readme"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except OSError as exc:
        sys.exit(f"GitHub API request failed: {exc}")
    if payload.get("errors") or not payload.get("data", {}).get("user"):
        sys.exit(f"GitHub API returned an error: {payload.get('errors')}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def streaks(days: list[tuple[date, int]]) -> tuple[int, int]:
    longest = run = 0
    for _, count in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    current = 0
    # Today may still be empty; the streak is alive if yesterday counted.
    trimmed = days[:-1] if days and days[-1][1] == 0 else days
    for _, count in reversed(trimmed):
        if not count:
            break
        current += 1
    return current, longest


def activity(calendar: dict, lang: str, theme: dict) -> Svg:
    copy = COPY[lang]["activity"]
    days = [(date.fromisoformat(d["date"]), d["contributionCount"]) for week in calendar["weeks"] for d in week["contributionDays"]]
    weeks = [sum(d["contributionCount"] for d in week["contributionDays"]) for week in calendar["weeks"]]
    total = calendar["totalContributions"]
    current, longest = streaks(days)
    unit = lambda n: copy["day"] if n == 1 else copy["days"]  # noqa: E731

    W, H = 1000, 260
    svg = Svg(f"{copy['title']}: {total} {copy['total']}; {copy['current']} {current} {unit(current)}; {copy['longest']} {longest} {unit(longest)}.", W, H)
    svg.rect(0, 0, W, H, theme["bg"], rx=14)
    svg.text(sans(15), copy["aside"], 32, 48, theme["faint"])

    big = display(64, 600, -0.04)
    svg.text(big, f"{total:,}".replace(",", "." if lang == "pt" else ","), 32, 128, theme["fg"])
    svg.text(sans(16), copy["total"], 32, 156, theme["mute"])
    small_n, small_l = display(26, 600, -0.02), sans(15)
    for index, (label, value) in enumerate(((copy["current"], current), (copy["longest"], longest))):
        x = 32 + index * 150
        width = svg.text(small_n, str(value), x, 224, theme["fg"])
        svg.text(small_l, unit(value), x + width + 6, 224, theme["mute"])
        svg.text(small_l, label, x, 196, theme["faint"])

    # Weekly bars: last week of the window highlighted, empty weeks drawn as a short tick.
    left, right, base, top = 360, W - 32, 210, 40
    step = (right - left) / len(weeks)
    bar = step * 0.62
    peak = max(weeks) or 1
    for index, value in enumerate(weeks):
        x = left + index * step + (step - bar) / 2
        height = max(2.0, (value / peak) * (base - top))
        fill = ACCENT["prazinho"] if index == len(weeks) - 1 else theme["fg"]
        opacity = ' fill-opacity="0.85"' if value else ' fill-opacity="0.25"'
        svg.rect(x, base - height, bar, height, fill, rx=min(2.0, bar / 2), extra=opacity)
    svg.rect(left, base + 6, right - left, 1, theme["line"])
    months = copy["months"].split()
    seen = set()
    for index, week in enumerate(calendar["weeks"]):
        first = date.fromisoformat(week["contributionDays"][0]["date"])
        if first.day <= 7 and first.month not in seen and index < len(weeks) - 2:
            seen.add(first.month)
            svg.text(sans(12), months[first.month - 1], left + index * step, base + 26, theme["faint"])
    return svg


def placeholder(lang: str, theme: dict) -> Svg:
    copy = COPY[lang]["activity"]
    svg = Svg(copy["pending"], 1000, 96)
    svg.rect(0, 0, 1000, 96, theme["bg"], rx=14)
    svg.text(sans(17), copy["pending"], 32, 54, theme["mute"])
    return svg


def sample_calendar() -> dict:
    """Deterministic fake data, only for local previews (python build.py activity --sample)."""
    start = date.today() - timedelta(days=date.today().weekday() + 1 + 52 * 7)
    weeks = []
    for w in range(53):
        days = []
        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            if day > date.today():
                break
            count = ((w * 7 + d) * 37 % 11) if (w % 9) not in (3, 4) else 0
            days.append({"date": day.isoformat(), "contributionCount": count})
        if days:
            weeks.append({"contributionDays": days})
    total = sum(d["contributionCount"] for w in weeks for d in w["contributionDays"])
    return {"totalContributions": total, "weeks": weeks}


# ---------------------------------------------------------------- main


def write(path: Path, svg: Svg) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg.render(), encoding="utf-8")


def build_static() -> None:
    for theme_name, theme in THEMES.items():
        for lang in LANGS:
            out = ASSETS / lang / theme_name
            write(out / "banner.svg", banner(lang, theme))
            for project in PROJECTS:
                write(out / f"card-{project['slug']}.svg", card(project, lang, theme))
            write(out / "stack.svg", stack(lang, theme_name, theme))
            for kind, label in COPY[lang]["buttons"].items():
                write(out / f"button-{kind}.svg", button(kind, label, theme))
            activity_path = out / "activity.svg"
            if not activity_path.exists():
                write(activity_path, placeholder(lang, theme))
    print(f"Static blocks written to {ASSETS.relative_to(ROOT)}/")


def build_activity(sample: bool) -> None:
    calendar = sample_calendar() if sample else fetch_calendar()
    for theme_name, theme in THEMES.items():
        for lang in LANGS:
            write(ASSETS / lang / theme_name / "activity.svg", activity(calendar, lang, theme))
    print(f"Activity card written ({calendar['totalContributions']} contributions{' — SAMPLE DATA' if sample else ''}).")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "activity":
        build_activity(sample="--sample" in sys.argv)
    else:
        build_static()
