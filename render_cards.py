#!/usr/bin/env python3
"""Gera os cards SVG do perfil a partir de profile.json e monta o README.md.

    python3 render_cards.py

Paleta Everforest escura. Fontes OFL (Fraunces, Space Grotesk, Space Mono) em fonts/,
subconjuntos embutidos em cada SVG para que o <img> do GitHub as renderize.
Para mudar o texto, edite profile.json e rode o script de novo.
"""
import base64
import html
import json
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cards"
P = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))

C = dict(
    bg="#1d2326",       # fundo do card
    edge="#38434a",     # contorno
    rule="#2c373d",     # linhas internas
    fg="#d3c6aa",
    grey1="#7f8b84",
    grey2="#a3ada5",
    red="#e67e80",
    orange="#e69875",
    yellow="#dbbc7f",
    green="#a7c080",
    aqua="#83c092",
    blue="#7fbbb3",
    purple="#d699b6",
)
CYCLE = [C["green"], C["aqua"], C["blue"], C["yellow"], C["orange"], C["purple"], C["red"]]

# face -> (arquivo em fonts/, nome da família no SVG)
FACES = {
    "disp": ("Fraunces-400.woff", "PDisp"),
    "sans": ("SpaceGrotesk-400.woff", "PSans"),
    "sansb": ("SpaceGrotesk-600.woff", "PSansB"),
    "mono": ("SpaceMono-400.woff", "PMono"),
}

W = 880          # largura do card de largura total (sem margem)
M = 14           # margem transparente em volta de cada card (espaçamento entre cards)
PAD = 36         # margem interna
HALF = 428       # card dentro de uma célula de tabela de duas colunas
HPAD = 26
PROJECT_H = 300


# ---- métricas reais das fontes (largura exata do texto) ---------------------
@lru_cache(None)
def _font(face):
    f = TTFont(ROOT / "fonts" / FACES[face][0])
    return f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm


def tw(face, s, size, ls=0.0):
    cmap, hmtx, upem = _font(face)
    total = 0
    for ch in s:
        g = cmap.get(ord(ch))
        if g is None:
            sys.exit(f"glifo {ch!r} (U+{ord(ch):04X}) não existe na fonte {face}")
        total += hmtx[g][0]
    return total * size / upem + ls * len(s)


def wrap(face, s, size, maxw):
    """Quebra por palavra; palavra maior que a linha é quebrada por caractere."""
    words = []
    for w in s.split():
        cur = ""
        for ch in w:
            if tw(face, cur + ch, size) > maxw and cur:
                words.append(cur)
                cur = ch
            else:
                cur += ch
        words.append(cur)
    lines, cur = [], ""
    for word in words:
        t = f"{cur} {word}".strip()
        if cur and tw(face, t, size) > maxw:
            lines.append(cur)
            cur = word
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


@lru_cache(None)
def subset_b64(face, chars):
    src = ROOT / "fonts" / FACES[face][0]
    with tempfile.TemporaryDirectory() as td:
        dst = Path(td) / "s.woff"
        uni = ",".join(f"U+{ord(c):04X}" for c in sorted(set(chars) | {" "}))
        subprocess.run(
            ["pyftsubset", str(src), f"--unicodes={uni}", "--flavor=woff", "--no-hinting",
             "--layout-features=kern,liga", f"--output-file={dst}"],
            check=True, capture_output=True,
        )
        return base64.b64encode(dst.read_bytes()).decode()


def esc(s):
    return html.escape(str(s), quote=True)


class Card:
    def __init__(self, label, w, h):
        self.label, self.w, self.h = label, w, h
        self.parts = []
        self.used = {}

    def t(self, x, y, s, face="sans", size=14, color="fg", anchor="start", ls=0):
        self.used.setdefault(face, set()).update(s)
        fam = FACES[face][1]
        a = f' text-anchor="{anchor}"' if anchor != "start" else ""
        l = f' letter-spacing="{ls}"' if ls else ""
        self.parts.append(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size:g}" '
            f'fill="{C.get(color, color)}"{a}{l}>{esc(s)}</text>'
        )

    def box(self, x, y, w, h, stroke):
        self.parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="none" '
            f'stroke="{C.get(stroke, stroke)}" stroke-width="1"/>'
        )

    def pill(self, x, y, s, color, size=9.5):
        w = tw("mono", s, size, 0.6) + 18
        self.box(x, y, w, 22, color)
        self.t(x + 9, y + 15, s, "mono", size, color, ls=0.6)
        return w

    def line(self, x1, y1, x2, y2, color="rule"):
        self.parts.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{C.get(color, color)}" stroke-width="1"/>'
        )

    def head(self, num, title, color, pad=PAD):
        self.t(pad, 32, f"{num:02d}", "mono", 11, color)
        self.t(pad + 34, 32, title.upper(), "mono", 10, "grey2", ls=1.6)
        self.line(pad, 46, self.w - pad, 46)

    def svg(self):
        css = []
        for face, chars in sorted(self.used.items()):
            fam = FACES[face][1]
            css.append(
                f"@font-face{{font-family:'{fam}';font-weight:400;font-style:normal;"
                f"src:url(data:font/woff;base64,{subset_b64(face, ''.join(sorted(chars)))}) format('woff')}}"
            )
        tw_, th = self.w + 2 * M, self.h + 2 * M
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{tw_}" height="{th}" '
            f'viewBox="0 0 {tw_} {th}" role="img" aria-label="{esc(self.label)}">'
            f'<title>{esc(self.label)}</title>'
            f'<style>{"".join(css)}</style>'
            f'<rect x="{M + 0.5}" y="{M + 0.5}" width="{self.w - 1}" height="{self.h - 1}" fill="{C["bg"]}" '
            f'stroke="{C["edge"]}" stroke-width="1"/>'
            f'<g transform="translate({M},{M})">{"".join(self.parts)}</g></svg>\n'
        )


def write(name, card):
    (OUT / f"{name}.svg").write_text(card.svg(), encoding="utf-8")


# ---- cards -----------------------------------------------------------------
def cover():
    c = Card(f"{P['name']}, @{P['handle']}. {P['role']}", W, 250)
    c.t(PAD, 50, P["kicker"].upper(), "mono", 10, "aqua", ls=1.4)
    c.t(PAD, 112, P["name"], "disp", 46, "fg")
    y = 150
    for line in wrap("sans", P["role"], 16, W - 2 * PAD):
        c.t(PAD, y, line, "sans", 16, "grey2")
        y += 25
    x = PAD
    for i, fact in enumerate(P["facts"]):
        x += c.pill(x, 196, fact.upper(), CYCLE[i % len(CYCLE)]) + 10
    write("cover", c)


LINK_W, LINK_H = 200, 118  # todos os cards de link têm o mesmo tamanho


def link(i, item):
    color = CYCLE[i % len(CYCLE)]
    title_lines = wrap("disp", item["title"], 15, LINK_W - 2 * 18)
    c = Card(f"{item['label']}: {item['title']}, {item['sub']}", LINK_W, LINK_H)
    c.t(18, 30, item["label"].upper(), "mono", 9.5, color, ls=1.4)
    c.line(18, 42, LINK_W - 18, 42)
    y = 66
    for ln in title_lines:
        c.t(18, y, ln, "disp", 15, "fg")
        y += 21
    c.t(18, LINK_H - 20, item["sub"], "sans", 11.5, "grey1")
    write(f"link-{i}", c)


def about():
    blocks = [wrap("sans", p, 15, W - 2 * PAD) for p in P["about"]]
    h = 70 + sum(len(b) * 24 + 14 for b in blocks) + 18
    c = Card("Sobre mim", W, h)
    c.head(1, "Sobre", C["green"])
    y = 80
    for b in blocks:
        for ln in b:
            c.t(PAD, y, ln, "sans", 15, "fg")
            y += 24
        y += 14
    write("about", c)


def project(i, p):
    color = CYCLE[i % len(CYCLE)]
    c = Card(f"{p['name']}. {p['description']}", HALF, PROJECT_H)
    c.head(i + 1, "Projeto", color, pad=HPAD)
    c.t(HALF - HPAD, 32, p["status"].upper(), "mono", 9, "grey1", anchor="end", ls=1.2)
    c.t(HPAD, 80, p["name"], "disp", 22, color)
    y = 106
    for ln in wrap("sans", p["description"], 13.5, HALF - 2 * HPAD):
        c.t(HPAD, y, ln, "sans", 13.5, "fg")
        y += 20
    y += 12
    for b in p["bullets"]:
        lines = wrap("sans", b, 12.5, HALF - 2 * HPAD - 18)
        for j, ln in enumerate(lines):
            if j == 0:
                c.t(HPAD, y, "›", "mono", 12.5, color)
            c.t(HPAD + 18, y, ln, "sans", 12.5, "grey2")
            y += 18
        y += 4
    x = HPAD
    for tag in p["tags"]:
        w = tw("mono", tag.upper(), 9.5, 0.6) + 18
        if x + w > HALF - HPAD:
            break
        c.pill(x, PROJECT_H - 48, tag.upper(), color)
        x += w + 8
    write(f"project-{i}", c)


def focus():
    rows = [(lab, wrap("sans", val, 14, W - 2 * PAD - 190)) for lab, val in P["focus"]]
    h = 74 + sum(len(v) * 24 + 12 for _, v in rows) + 18
    c = Card("Foco técnico", W, h)
    c.head(3, "Foco técnico", C["aqua"])
    y = 84
    for i, (lab, val) in enumerate(rows):
        c.t(PAD, y, lab.upper(), "mono", 10.5, CYCLE[i % len(CYCLE)], ls=1.2)
        for ln in val:
            c.t(PAD + 190, y, ln, "sans", 14, "fg")
            y += 24
        y += 12
    write("focus", c)


def how():
    blocks = [(it, wrap("sans", it["body"], 13.5, W - 2 * PAD - 250)) for it in P["how"]]
    h = 74 + sum(max(26, 21 * len(b) + 10) for _, b in blocks) + 14
    c = Card("Como eu trabalho", W, h)
    c.head(4, "Como eu trabalho", C["yellow"])
    y = 84
    for i, (it, body) in enumerate(blocks):
        c.t(PAD, y, it["title"], "sansb", 14, CYCLE[i % len(CYCLE)])
        by = y
        for ln in body:
            c.t(PAD + 250, by, ln, "sans", 13.5, "grey2")
            by += 21
        y = max(y + 26, by + 10)
    write("how", c)


def priorities():
    items = [wrap("sans", p, 14, W - 2 * PAD - 44) for p in P["priorities"]]
    h = 74 + sum(len(i) * 22 + 12 for i in items) + 16
    c = Card("Prioridades", W, h)
    c.head(5, "Prioridades", C["orange"])
    y = 84
    for i, lines in enumerate(items):
        c.t(PAD, y, f"0{i + 1}", "mono", 12, CYCLE[(i + 2) % len(CYCLE)])
        for ln in lines:
            c.t(PAD + 44, y, ln, "sans", 14, "fg")
            y += 22
        y += 12
    write("priorities", c)


def closing():
    words = [w.strip() for w in P["closing"].split("·")]
    gap = 22  # espaço de cada lado do separador
    sep_w = tw("mono", "·", 18)
    total = sum(tw("disp", w, 26) for w in words) + (sep_w + 2 * gap) * (len(words) - 1)
    c = Card(P["closing"], W, 110)
    x = (W - total) / 2
    for i, w in enumerate(words):
        if i:
            x += gap
            c.t(x, 64, "·", "mono", 18, "grey1")
            x += sep_w + gap
        c.t(x, 64, w, "disp", 26, CYCLE[i % len(CYCLE)])
        x += tw("disp", w, 26)
    write("closing", c)


# ---- README ----------------------------------------------------------------
def readme():
    link_cells = "".join(
        f'<td width="25%" valign="top"><a href="{esc(l["url"])}">'
        f'<img src="cards/link-{i}.svg" width="100%" alt="{esc(l["label"])}: {esc(l["title"])}, {esc(l["sub"])}" />'
        f"</a></td>"
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
    if not shutil.which("pyftsubset"):
        sys.exit("instale fonttools: pip install fonttools")
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
