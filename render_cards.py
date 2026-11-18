#!/usr/bin/env python3
"""Gera os cards SVG do perfil a partir de profile.json e monta o README.md.

    python3 render_cards.py

Paleta Everforest (dark, medium). Os cards são SVG estáticos, feitos para <img>.
Para mudar o texto, edite profile.json e rode o script de novo.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cards"
P = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))

C = dict(
    bg0="#2d353b", bg1="#343f44", bg3="#475258",
    fg="#d3c6aa", grey1="#859289", grey2="#9da9a0",
    red="#e67e80", orange="#e69875", yellow="#dbbc7f", green="#a7c080",
    aqua="#83c092", blue="#7fbbb3", purple="#d699b6",
)
CYCLE = [C["green"], C["aqua"], C["blue"], C["yellow"], C["orange"], C["purple"], C["red"]]
SANS = "'DejaVu Sans', Helvetica, Arial, sans-serif"
MONO = "'DejaVu Sans Mono', Menlo, Consolas, monospace"

W = 880
PAD = 28
HALF = 428
HPAD = 22
PROJECT_H = 272


def esc(s):
    return html.escape(str(s), quote=True)


def est_w(s, size, fam="sans"):
    """Largura aproximada de um texto. Mono ~0.6em por caractere, sans ~0.56em."""
    return len(s) * size * (0.6 if fam == "mono" else 0.56)


def wrap(s, size, maxw, fam="sans"):
    k = 0.6 if fam == "mono" else 0.56
    fit = max(1, int(maxw / (size * k)))  # caracteres que cabem numa linha
    words = []
    for w in s.split():
        while len(w) > fit:  # quebra palavras longas demais (URLs, e-mails)
            words.append(w[:fit])
            w = w[fit:]
        words.append(w)
    lines, cur = [], ""
    for word in words:
        t = f"{cur} {word}".strip()
        if cur and est_w(t, size, fam) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


class Card:
    def __init__(self, label, w, h):
        self.label, self.w, self.h = label, w, h
        self.parts = []

    def t(self, x, y, s, size=14, color="fg", fam="sans", weight=400, anchor="start", ls=0):
        family = MONO if fam == "mono" else SANS
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        wt = f' font-weight="{weight}"' if weight != 400 else ""
        fill = C.get(color, color)
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-family="{family}" font-size="{size:g}" '
            f'fill="{fill}"{a}{l}{wt}>{esc(s)}</text>'
        )

    def pill(self, x, y, s, color, size=10.5):
        w = est_w(s, size, "mono") + 18
        self.parts.append(
            f'<rect x="{x:g}" y="{y:g}" width="{w:.1f}" height="22" rx="11" fill="none" stroke="{color}" stroke-width="1"/>'
        )
        self.t(x + 9, y + 15, s, size, color, "mono")
        return w

    def line(self, x1, y1, x2, y2, color="bg3"):
        self.parts.append(
            f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{C.get(color, color)}" stroke-width="1"/>'
        )

    def head(self, num, title, color, pad=PAD):
        self.t(pad, 30, f"{num:02d}", 11, color, "mono", weight=700)
        self.t(pad + 30, 30, title.upper(), 11, "grey2", "mono", ls=1.5)
        self.line(pad, 42, self.w - pad, 42)

    def svg(self):
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{esc(self.label)}">'
            f'<title>{esc(self.label)}</title>'
            f'<rect x=".5" y=".5" width="{self.w - 1}" height="{self.h - 1}" rx="8" '
            f'fill="{C["bg0"]}" stroke="{C["bg3"]}"/>'
            + "".join(self.parts) + "</svg>\n"
        )


def write(name, card):
    (OUT / f"{name}.svg").write_text(card.svg(), encoding="utf-8")


# ---- cards -----------------------------------------------------------------
def cover():
    c = Card(f"{P['name']}, @{P['handle']}. {P['role']}", W, 236)
    c.t(PAD, 44, P["kicker"].upper(), 10.5, "aqua", "mono", ls=1.2)
    c.t(PAD, 102, P["name"], 36, "fg", weight=700)
    y = 136
    for line in wrap(P["role"], 16, W - 2 * PAD):
        c.t(PAD, y, line, 16, "grey2")
        y += 24
    x = PAD
    for i, fact in enumerate(P["facts"]):
        x += c.pill(x, 190, fact.upper(), CYCLE[i % len(CYCLE)]) + 10
    write("cover", c)


def link(i, item):
    color = CYCLE[i % len(CYCLE)]
    title_lines = wrap(item["title"], 13, 168)
    h = 50 + len(title_lines) * 17 + 36
    c = Card(f"{item['label']}: {item['title']}, {item['sub']}", 200, max(h, 110))
    c.t(16, 28, item["label"].upper(), 10, color, "mono", ls=1.2)
    y = 52
    for ln in title_lines:
        c.t(16, y, ln, 13, "fg", weight=700)
        y += 17
    c.t(16, y + 14, item["sub"], 11.5, "grey1")
    write(f"link-{i}", c)


def about():
    lines = []
    for para in P["about"]:
        lines += wrap(para, 14.5, W - 2 * PAD)
        lines.append("")
    lines.pop()
    h = 60 + len(lines) * 22 + 28
    c = Card("Sobre mim", W, h)
    c.head(1, "Sobre", C["green"])
    y = 72
    for ln in lines:
        if ln:
            c.t(PAD, y, ln, 14.5, "fg")
        y += 22 if ln else 10
    write("about", c)


def project(i, p):
    color = CYCLE[i % len(CYCLE)]
    c = Card(f"{p['name']}. {p['description']}", HALF, PROJECT_H)
    c.head(i + 1, "Projeto", color, pad=HPAD)
    c.t(HALF - HPAD, 30, p["status"].upper(), 9.5, "grey1", "mono", anchor="end", ls=1)
    c.t(HPAD, 70, p["name"], 18, color, weight=700)
    y = 94
    for ln in wrap(p["description"], 13, HALF - 2 * HPAD):
        c.t(HPAD, y, ln, 13, "fg")
        y += 18
    y += 10
    for b in p["bullets"]:
        lines = wrap(b, 12, HALF - 2 * HPAD - 16)
        for j, ln in enumerate(lines):
            if j == 0:
                c.t(HPAD, y, "›", 12, color, "mono", weight=700)
            c.t(HPAD + 16, y, ln, 12, "grey2")
            y += 16
        y += 4
    x = HPAD
    for tag in p["tags"]:
        w = est_w(tag.upper(), 9.5, "mono") + 16
        if x + w > HALF - HPAD:
            break
        c.pill(x, PROJECT_H - 40, tag.upper(), color, 9.5)
        x += w + 8
    write(f"project-{i}", c)


def focus():
    rows = []
    for label, value in P["focus"]:
        rows.append((label, wrap(value, 14, W - 2 * PAD - 170)))
    h = 60 + sum(len(v) * 22 + 12 for _, v in rows) + 20
    c = Card("Foco técnico", W, h)
    c.head(3, "Foco técnico", C["aqua"])
    y = 74
    for i, (label, value) in enumerate(rows):
        color = CYCLE[i % len(CYCLE)]
        c.t(PAD, y, label.upper(), 11, color, "mono", ls=1)
        for ln in value:
            c.t(PAD + 170, y, ln, 14, "fg")
            y += 22
        y += 12
    write("focus", c)


def how():
    blocks = []
    for item in P["how"]:
        blocks.append((item, wrap(item["body"], 13.5, W - 2 * PAD - 200)))
    h = 74 + sum(max(22, 20 * len(b) + 8) for _, b in blocks) + 14
    c = Card("Como eu trabalho", W, h)
    c.head(4, "Como eu trabalho", C["yellow"])
    y = 74
    for i, (item, body) in enumerate(blocks):
        color = CYCLE[i % len(CYCLE)]
        c.t(PAD, y, item["title"], 14, color, weight=700)
        by = y
        for ln in body:
            c.t(PAD + 230, by, ln, 13.5, "grey2")
            by += 20
        y = max(y + 22, by + 8)
    write("how", c)


def priorities():
    items = [wrap(p, 14, W - 2 * PAD - 40) for p in P["priorities"]]
    h = 62 + sum(len(i) * 21 + 10 for i in items) + 14
    c = Card("Prioridades", W, h)
    c.head(5, "Prioridades", C["orange"])
    y = 74
    for i, lines in enumerate(items):
        color = CYCLE[(i + 2) % len(CYCLE)]
        c.t(PAD, y, f"0{i + 1}", 13, color, "mono", weight=700)
        for ln in lines:
            c.t(PAD + 40, y, ln, 14, "fg")
            y += 21
        y += 10
    write("priorities", c)


def closing():
    words = [w.strip() for w in P["closing"].split("·")]
    c = Card(P["closing"], W, 104)
    spans = []
    for i, w in enumerate(words):
        if i:
            spans.append(f'<tspan fill="{C["grey1"]}">  ·  </tspan>')
        spans.append(f'<tspan fill="{CYCLE[i % len(CYCLE)]}">{esc(w)}</tspan>')
    c.parts.append(
        f'<text x="{W / 2:g}" y="60" text-anchor="middle" xml:space="preserve" font-family="{SANS}" font-size="22" '
        f'font-weight="700">{"".join(spans)}</text>'
    )
    write("closing", c)


# ---- README ----------------------------------------------------------------
def readme():
    link_cells = "".join(
        f'<td width="25%" valign="top"><a href="{esc(l["url"])}">'
        f'<img src="cards/link-{i}.svg" width="100%" alt="{esc(l["label"])}: {esc(l["title"])}, {esc(l["sub"])}" />'
        f'</a></td>'
        for i, l in enumerate(P["links"])
    )
    project_cells = []
    for i, p in enumerate(P["projects"]):
        img = (f'<img src="cards/project-{i}.svg" width="100%" '
               f'alt="{esc(p["name"])}. {esc(p["description"])}" />')
        if p.get("url") and not p.get("private"):
            img = f'<a href="{esc(p["url"])}">{img}</a>'
        project_cells.append(f'<td width="50%" valign="top">{img}</td>')
    rows = "".join(
        f"<tr>{''.join(project_cells[i:i + 2])}</tr>" for i in range(0, len(project_cells), 2)
    )
    return f"""<!-- Os cards em cards/ são gerados por render_cards.py a partir de profile.json. Edite o JSON e rode o script. -->

<div align="center">

<a href="https://github.com/devbianchi"><img src="cards/cover.svg" width="100%" alt="{esc(P['name'])}, @{P['handle']}. {esc(P['role'])}" /></a>

<table>
<tr>{link_cells}</tr>
</table>

<img src="cards/about.svg" width="100%" alt="Sobre mim" />

<table>
{rows}
</table>

<img src="cards/focus.svg" width="100%" alt="Foco técnico" />

<img src="cards/how.svg" width="100%" alt="Como eu trabalho" />

<img src="cards/priorities.svg" width="100%" alt="Prioridades" />

<img src="cards/closing.svg" width="100%" alt="{esc(P['closing'])}" />

</div>
"""


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    cover()
    for i, l in enumerate(P["links"]):
        link(i, l)
    about()
    for i, p in enumerate(P["projects"]):
        project(i, p)
    focus()
    how()
    priorities()
    closing()
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    print("cards gerados em", OUT)
