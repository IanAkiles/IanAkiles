#!/usr/bin/env python3
"""
Gerador dos assets SVG do README de perfil — Ian Akiles.
Texto é convertido em <path> (fonts: Inter Display + JetBrains Mono, ambas OFL),
então o resultado renderiza igual em qualquer lugar, inclusive no <img> do GitHub.

Requisitos:
  pip install fonttools uharfbuzz
  npm install @fontsource/jetbrains-mono        (ajuste FONTS abaixo para a pasta files/)
  Inter Display (.otf) instalada                (ajuste INTER abaixo)
Edite os textos nas funções (banner, terminal, cards...) e rode:
  python3 build_assets.py <pasta_de_saida>      -> copie os .svg para IanAkiles/assets/
"""
import io, math, os, sys
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "fonts", "node_modules", "@fontsource", "jetbrains-mono", "files")
INTER = "/usr/share/fonts/opentype/inter"

# ───────────────────────── design tokens ─────────────────────────
INK, INK2 = "#0A0A0A", "#151515"
PAPER, PAPER2 = "#F2F0EA", "#E3E0D6"
ACC = "#FFE600"
MUTE_P = "#66645D"      # texto secundário sobre papel
MUTE_I = "#9A978E"      # texto secundário sobre tinta
DIM_I = "#4B4A45"       # texto terciário sobre tinta
HAIR_I = "#2E2E2C"      # fio sobre tinta
SQ2 = math.sqrt(2)


def n(v):
    s = f"{v:.2f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# ───────────────────────── tipografia → paths ─────────────────────────
class Font:
    def __init__(self, path, plain=False):
        tt = TTFont(path)
        if path.endswith(".woff"):
            tt.flavor = None
            b = io.BytesIO(); tt.save(b)
            data = b.getvalue(); tt = TTFont(io.BytesIO(data))
        else:
            data = open(path, "rb").read()
        self.tt, self.upem = tt, tt["head"].unitsPerEm
        self.gs, self.names = tt.getGlyphSet(), tt.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob(data)))
        self.feat = {"liga": False, "calt": False, "clig": False} if plain else {}

    def shape(self, text):
        buf = hb.Buffer(); buf.add_str(text); buf.guess_segment_properties()
        hb.shape(self.hb, buf, self.feat)
        return [(self.names[i.codepoint], p.x_advance, p.x_offset, p.y_offset)
                for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def width(self, text, size, tr=0.0):
        g = self.shape(text); s = size / self.upem
        return sum(a for _, a, _, _ in g) * s + tr * size * max(len(g) - 1, 0)

    def path(self, text, size, x, y, tr=0.0, anchor="s"):
        g = self.shape(text); s = size / self.upem
        w = self.width(text, size, tr)
        if anchor == "m": x -= w / 2
        elif anchor == "e": x -= w
        cx, cmds = x, []
        for name, adv, xo, yo in g:
            pen = SVGPathPen(self.gs, ntos=n)
            self.gs[name].draw(TransformPen(pen, (s, 0, 0, -s, cx + xo * s, y - yo * s)))
            c = pen.getCommands()
            if c: cmds.append(c)
            cx += adv * s + tr * size
        return "".join(cmds), w

    def fit(self, text, width, tr=0.0, max_size=999):
        return min(max_size, width / self.width(text, 1.0, tr))

    def cap(self, size):
        return self.tt["OS/2"].sCapHeight / self.upem * size


DISP = Font(f"{INTER}/InterDisplay-Black.otf")
DISPX = Font(f"{INTER}/InterDisplay-ExtraBold.otf")
M5 = Font(f"{FONTS}/jetbrains-mono-latin-500-normal.woff", plain=True)
M7 = Font(f"{FONTS}/jetbrains-mono-latin-700-normal.woff", plain=True)
M8 = Font(f"{FONTS}/jetbrains-mono-latin-800-normal.woff", plain=True)


def T(font, text, size, x, y, fill, tr=0.0, anchor="s", extra=""):
    d, _ = font.path(text, size, x, y, tr, anchor)
    return f'<path d="{d}" fill="{fill}"{extra}/>'


def RUNS(font, runs, size, x, y, tr=0.0):
    out, cx = [], x
    for t, f in runs:
        d, w = font.path(t, size, cx, y, tr)
        out.append(f'<path d="{d}" fill="{f}"/>')
        cx += w + tr * size
    return "".join(out), cx - x - tr * size


# ───────────────────────── primitivas ─────────────────────────
def R(x, y, w, h, fill="none", stroke=None, sw=0, extra=""):
    s = f' stroke="{stroke}" stroke-width="{n(sw)}"' if stroke else ""
    return f'<rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}" fill="{fill}"{s}{extra}/>'


def BOX(x, y, w, h, fill, stroke=INK, sw=3, extra=""):
    """retângulo cuja borda fica DENTRO de (x,y,w,h)"""
    return R(x + sw / 2, y + sw / 2, w - sw, h - sw, fill, stroke, sw, extra)


def LINE(x1, y1, x2, y2, stroke=INK, sw=2, extra=""):
    return (f'<line x1="{n(x1)}" y1="{n(y1)}" x2="{n(x2)}" y2="{n(y2)}" '
            f'stroke="{stroke}" stroke-width="{n(sw)}"{extra}/>')


def ARROW(x, y, length, head, stroke, sw=4):
    """seta brutalista: haste reta + ponta em chevron (miter)"""
    d = (f"M{n(x)} {n(y)}H{n(x + length)}M{n(x + length - head)} {n(y - head)}"
         f"L{n(x + length)} {n(y)}L{n(x + length - head)} {n(y + head)}")
    return (f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{n(sw)}" '
            f'stroke-linejoin="miter" stroke-linecap="butt"/>')


def TRI_UP(cx, by, w, h, fill, stroke=None, sw=0):
    s = f' stroke="{stroke}" stroke-width="{n(sw)}"' if stroke else ""
    return (f'<path d="M{n(cx - w / 2)} {n(by)}L{n(cx)} {n(by - h)}L{n(cx + w / 2)} {n(by)}Z" '
            f'fill="{fill}"{s}/>')


def BLINK(dur=1.0):
    return (f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.5;1" '
            f'dur="{dur}s" repeatCount="indefinite"/>')


def hazard(uid, x, y, w, h, dur=2.4, stripe=10, reverse=False):
    per = stripe * 2 * SQ2
    defs = (f'<pattern id="{uid}p" width="{stripe * 2}" height="{stripe * 2}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)"><rect width="{stripe}" height="{stripe * 2}" fill="{INK}"/>'
            f'<rect x="{stripe}" width="{stripe}" height="{stripe * 2}" fill="{ACC}"/></pattern>'
            f'<clipPath id="{uid}c"><rect x="{n(x)}" y="{n(y)}" width="{n(w)}" height="{n(h)}"/></clipPath>')
    a, b = ("0 0", f"{per:.2f} 0") if not reverse else (f"{per:.2f} 0", "0 0")
    body = (f'<g clip-path="url(#{uid}c)"><g><animateTransform attributeName="transform" type="translate" '
            f'from="{a}" to="{b}" dur="{dur}s" repeatCount="indefinite"/>'
            f'<rect x="{n(x - per * 2)}" y="{n(y)}" width="{n(w + per * 4)}" height="{n(h)}" fill="url(#{uid}p)"/></g></g>')
    return defs, body


def SVG(w, h, body, title, defs=""):
    title = title.replace("&", "&amp;").replace("<", "&lt;")
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img">\n<title>{title}</title>\n'
            f'<defs>{defs}</defs>\n{body}\n</svg>\n')


def warn(cond, msg):
    if not cond:
        print("  ! layout:", msg, file=sys.stderr)


# ═════════════════════════ BANNER ═════════════════════════
def banner():
    W, H = 1200, 420
    defs, b = [], []
    defs.append(f'<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
                f'<circle cx="12" cy="12" r="1.2" fill="{INK}" opacity="0.17"/></pattern>')
    defs.append('<clipPath id="tk"><rect x="0" y="0" width="1200" height="48"/></clipPath>')

    b.append(R(0, 0, W, H, PAPER))
    b.append(R(0, 51, W, H - 51, "url(#dots)"))

    # ── ticker
    b.append(R(0, 0, W, 48, INK))
    sep = "   //   "
    parts = ["IAN AKILES", "DESENVOLVEDOR WEB", "SAAS", "AUTOMAÇÃO", "IA"]
    runs = []
    for p in parts:
        runs += [(p, PAPER), (sep, ACC)]
    unit_d, unit_w = RUNS(M7, runs, 17, 0, 31, 0.06)
    unit_w += 0.06 * 17
    defs.append(f'<g id="tu">{unit_d}</g>')
    reps = int(math.ceil(W / unit_w)) + 2
    uses = "".join(f'<use xlink:href="#tu" href="#tu" x="{n(i * unit_w)}"/>' for i in range(reps))
    b.append(f'<g clip-path="url(#tk)"><g><animateTransform attributeName="transform" type="translate" '
             f'from="0 0" to="{n(-unit_w)} 0" dur="{n(unit_w / 55)}s" repeatCount="indefinite"/>{uses}</g></g>')
    b.append(R(0, 48, W, 4, ACC))

    # ── marcas de registro (cantos)
    for cx, cy in [(30, 80), (1170, 80), (30, 366), (1170, 366)]:
        b.append(LINE(cx - 8, cy, cx + 8, cy, INK, 1.5, ' opacity="0.55"'))
        b.append(LINE(cx, cy - 8, cx, cy + 8, INK, 1.5, ' opacity="0.55"'))

    # ── tag "IAN"
    b.append(R(60, 92, 18, 18, ACC, INK, 3))
    b.append(T(DISP, "IAN", 34, 92, 118, INK, tr=0.24))
    label = "PERFIL_DEV"
    lw = M7.width(label, 15, 0.12)
    b.append(LINE(222, 106, 826 - lw - 16, 106, INK, 2))
    b.append(T(M7, label, 15, 826, 111, MUTE_P, tr=0.12, anchor="e"))

    # ── AKILES gigante
    size = DISP.fit("AKILES", 744, -0.008)
    base = 300
    b.append(T(DISP, "AKILES", size, 68, base + 8, ACC, tr=-0.008))
    b.append(T(DISP, "AKILES", size, 60, base, INK, tr=-0.008))

    # ── faixa de subtítulo
    sub = [("WEB", PAPER), (" • ", ACC), ("SAAS", PAPER), (" • ", ACC), ("AUTOMAÇÃO", PAPER),
           (" • ", ACC), ("IA", PAPER), (" — ", ACC), ("SISTEMAS PARA RESOLVER PROBLEMAS", PAPER)]
    s_d, s_w = RUNS(M7, sub, 17, 80, 350, 0.035)
    barw = int(s_w + 20 + 14 + 32)
    warn(barw <= 770, f"subtitle bar {barw}")
    b.append(R(60, 322, barw, 44, INK))
    b.append(s_d)
    b.append(R(80 + s_w + 12, 334, 14, 20, ACC, extra=f'>{BLINK(1.0)}</rect' if False else ""))
    # cursor piscante (rect com animate)
    b[-1] = (f'<rect x="{n(80 + s_w + 12)}" y="334" width="14" height="20" fill="{ACC}">{BLINK(1.0)}</rect>')

    # ── painel de status
    px, py, pw, ph = 872, 96, 268, 214
    b.append(R(px + 10, py + 10, pw, ph, INK))
    b.append(BOX(px, py, pw, ph, PAPER, INK, 3))
    b.append(R(px, py, pw, 40, INK))
    b.append(T(M8, "STATUS ::", 15, px + 18, py + 26, ACC, tr=0.1))
    b.append(f'<circle cx="{px + pw - 24}" cy="{py + 20}" r="6.5" fill="{ACC}">{BLINK(1.2)}</circle>')
    fs = DISP.fit("FOCANDO", pw - 40, -0.01)
    b.append(T(DISP, "FOCANDO", fs, px + 20, py + 106, INK, tr=-0.01))
    b.append(T(M8, "BUILD // SHIP // REPEAT", 14.5, px + 20, py + 136, INK, tr=0.04))
    # barra de carga (12 passos)
    bx, by = px + 20, py + 160
    for i in range(12):
        x = bx + i * 19
        b.append(BOX(x, by, 15, 22, PAPER, INK, 2))
        t0 = 0.08 + i * 0.065
        b.append(f'<rect x="{n(x + 2)}" y="{n(by + 2)}" width="11" height="18" fill="{ACC}" opacity="0">'
                 f'<animate attributeName="opacity" values="0;1;1" keyTimes="0;{t0:.3f};1" calcMode="discrete" '
                 f'dur="5s" repeatCount="indefinite"/></rect>')

    # ── régua inferior + hazard
    for i in range(0, W + 1, 12):
        major = i % 60 == 0
        b.append(LINE(i, 388, i, 388 - (14 if major else 7), INK, 1.5 if major else 1,
                      "" if major else ' opacity="0.45"'))
    hd, hb_ = hazard("hz", 0, 400, W, 20, dur=2.8)
    defs.append(hd); b.append(hb_)
    b.append(R(0, 396, W, 4, INK))

    return SVG(W, H, "\n".join(b), "IAN AKILES — Desenvolvedor Web, SaaS, Automação e IA", "".join(defs))


# ═════════════════════════ DIVISOR ═════════════════════════
def divider():
    W, H = 912, 14
    hd, hb_ = hazard("hd", 0, 4, W, 10, dur=3.0)
    body = R(0, 0, W, 4, INK) + hb_
    return SVG(W, H, body, "divisor", hd)


# ═════════════════════════ CABEÇALHOS DE SEÇÃO ═════════════════════════
def section(num, title, total=5):
    W, H = 912, 80
    b = [R(0, 0, W, 72, INK), R(0, 0, 96, 72, ACC), R(0, 72, W, 4, ACC)]
    b.append(T(DISP, f"{num:02d}", 44, 48, 51, INK, tr=-0.03, anchor="m"))
    b.append(T(DISP, title, 36, 128, 49, PAPER, tr=-0.012))
    b.append(T(M7, f"SEC {num:02d}/{total:02d}", 14, W - 28, 32, MUTE_I, tr=0.14, anchor="e"))
    for i in range(total):
        x = W - 28 - total * 12 - (total - 1) * 6 + i * 18
        if i < num:
            b.append(R(x, 42, 12, 12, ACC))
        else:
            b.append(BOX(x, 42, 12, 12, "none", MUTE_I, 1.5))
    return SVG(W, H, "\n".join(b), f"{num:02d} — {title}")


# ═════════════════════════ FRASE (substitui o blockquote) ═════════════════════════
def quote():
    W, H = 912, 112
    b = [R(10, 10, 900, 98, INK), BOX(0, 0, 900, 98, PAPER, INK, 3), R(0, 0, 96, 98, INK)]
    b.append(T(DISP, "“", 130, 48, 128, ACC, anchor="m"))
    size = 34
    b.append(T(DISP, "NÃO COLECIONO TUTORIAL.", size, 128, 44, INK, tr=-0.02))
    d, w = DISP.path("COLECIONO COISA QUE ", size, 128, 84, -0.02)
    d2, w2 = DISP.path("RODA.", size, 128 + w - 0.02 * size, 84, -0.02)
    hx = 128 + w - 0.02 * size
    b.append(f'<path d="{d}" fill="{INK}"/>')
    b.append(R(hx - 8, 84 - 30, w2 + 16, 40, ACC))
    b.append(f'<path d="{d2}" fill="{INK}"/>')
    b.append(T(M7, "// LEMA", 14, 872, 34, MUTE_P, tr=0.14, anchor="e"))
    return SVG(W, H, "\n".join(b), "Não coleciono tutorial. Coleciono coisa que roda.")


# ═════════════════════════ TERMINAL ═════════════════════════
def terminal():
    W, H = 912, 330
    FS, CW = 22, 22 * 0.6
    defs, b = [], []
    b.append(R(10, 10, W - 12, H - 12, ACC))
    b.append(R(0, 0, W - 12, H - 12, INK))
    ww = W - 12
    b.append(R(0, 0, ww, 46, INK2))
    b.append(R(0, 46, ww, 2, HAIR_I))
    title = RUNS(M7, [("akiles@brutal", PAPER), (":~$ ", ACC), ("cat quem.txt", MUTE_I)], 17, 28, 30, 0.02)[0]
    b.append(title)
    for i, c in enumerate([None, None, ACC]):
        x = ww - 28 - 3 * 14 - 2 * 8 + i * 22
        b.append(BOX(x, 17, 14, 14, c or "none", c or MUTE_I, 2) if not c else R(x, 17, 14, 14, c))

    rows = [("NOME", "IAN AKILES", PAPER), ("FUNÇÃO", "DESENVOLVEDOR WEB", ACC),
            ("FAZ", "PRODUTOS DIGITAIS E SISTEMAS", PAPER), ("", "QUE RESOLVEM PROBLEMAS", PAPER),
            ("MÉTODO", "CONSTRUIR. QUEBRAR. CONSERTAR. ENTREGAR.", ACC), ("SITE", "www.ianakiles.com.br", PAPER)]
    COL = 15
    T_LOOP, t = 16.0, 0.5
    for i, (k, v, vc) in enumerate(rows):
        base = 92 + i * 36
        pad = (k + " " + "." * (COL - 2 - len(k)) + " ") if k else "." * (COL - 1) + " "
        if not k: pad = "." * (COL - 2) + " "
        pad = pad.ljust(COL)
        b.append(T(M5, f"{i + 1:02d}", 14, 28, base - 1, DIM_I, tr=0.05))
        x0 = 64
        parts = [("> ", ACC)]
        kd, kw = M7.path(pad[:COL], FS, x0 + 2 * CW, base)
        b_line = (T(M7, ">", FS, x0, base, ACC) +
                  (T(M7, k, FS, x0 + 2 * CW, base, MUTE_I) if k else "") +
                  T(M5, pad[len(k):COL].rstrip() if k else pad.rstrip(), FS,
                    x0 + (2 + (len(k) if k else 0)) * CW, base, DIM_I) +
                  T(M7, v, FS, x0 + (2 + COL) * CW, base, vc))
        nch = 2 + COL + len(v)
        fullw = nch * CW + 4
        dur = 0.032 * nch
        vals = [0] + [min(k_ * CW + 2, fullw) for k_ in range(1, nch + 1)] + [fullw]
        kts = [0] + [(t + dur * k_ / nch) / T_LOOP for k_ in range(1, nch + 1)] + [1.0]
        defs.append(f'<clipPath id="c{i}"><rect x="{x0 - 4}" y="{base - 26}" width="{n(fullw)}" height="36">'
                    f'<animate attributeName="width" calcMode="discrete" dur="{T_LOOP}s" repeatCount="indefinite" '
                    f'values="{";".join(n(x) for x in vals)}" keyTimes="{";".join(f"{x:.4f}" for x in kts)}"/></rect></clipPath>')
        b.append(f'<g clip-path="url(#c{i})">{b_line}</g>')
        t += dur + 0.28
        warn(x0 + fullw < ww - 20, f"terminal row {i} width")
    base = 92 + 6 * 36
    b.append(T(M5, "07", 14, 28, base - 1, DIM_I, tr=0.05))
    b.append(T(M7, ">", FS, 64, base, ACC))
    b.append(f'<rect x="{64 + 2 * CW:.1f}" y="{base - 20}" width="{CW:.1f}" height="26" fill="{ACC}">{BLINK(1.0)}</rect>')
    return SVG(W, H, "\n".join(b),
               "Ian Akiles. Desenvolvedor Web. Faz produtos digitais e sistemas que resolvem problemas. "
               "Método: construir, quebrar, consertar, entregar.", "".join(defs))


# ═════════════════════════ CARDS DE PROJETO ═════════════════════════
def card_frame(idx, title_lines, tsize, desc_lines, tags, illo, defs_extra="", title_base=None):
    W, H = 620, 380
    defs, b = [defs_extra], []
    CW_, CH_ = 600, 360
    b.append(R(12, 12, CW_, CH_, INK))
    b.append(R(0, 0, CW_, CH_, PAPER))
    # grid sutil
    defs.append(f'<pattern id="gp" width="20" height="20" patternUnits="userSpaceOnUse">'
                f'<circle cx="10" cy="10" r="0.9" fill="{INK}" opacity="0.14"/></pattern>')
    b.append(R(0, 46, CW_, CH_ - 46, "url(#gp)"))
    # header
    b.append(R(0, 0, CW_, 46, INK))
    b.append(T(M8, f"PROJETO_{idx:02d}", 17, 24, 30, ACC, tr=0.06))
    b.append(R(446, 0, 154, 46, ACC))
    b.append(T(M8, "ABRIR", 16, 466, 30, INK, tr=0.08))
    b.append(f'<g>{ARROW(540, 23, 26, 8, INK, 3.5)}<animateTransform attributeName="transform" type="translate" '
             f'values="0 0;5 0;0 0" dur="1.8s" repeatCount="indefinite"/></g>')
    # título
    tb = title_base or (110 if len(title_lines) > 1 else 128)
    lh = tsize * 1.08
    for i, ln in enumerate(title_lines):
        b.append(T(DISP, ln, tsize, 24, tb + i * lh, INK, tr=-0.03))
    # régua + descrição
    ry = 226
    b.append(R(24, ry, 64, 8, ACC, INK, 2))
    for i, ln in enumerate(desc_lines):
        b.append(T(M7, ln, 15, 24, 262 + i * 24, INK, tr=0.01))
    # tags
    x = 24
    for i, tg in enumerate(tags):
        tw = M8.width(tg, 14, 0.05)
        cw = tw + 28
        b.append(R(x + 3, 303 + 3, cw, 32, INK))
        b.append(BOX(x, 303, cw, 32, ACC if i == 0 else PAPER, INK, 2.5))
        b.append(T(M8, tg, 14, x + 14, 324, INK, tr=0.05))
        x += cw + 14
        warn(x < 580, f"tags overflow card {idx}: {x}")
    # divisor vertical (termina acima da faixa de tags)
    b.append(R(302, 66, 2, 218, INK, extra=' opacity="0.12"'))
    # ilustração (região 316..576 x 64..336)
    b.append(f'<g transform="translate(320 66)">{illo}</g>')
    b.append(BOX(0, 0, CW_, CH_, "none", INK, 3))
    return SVG(W, H, "\n".join(b), "", "".join(defs))


def illo_saas():
    o, d = [], []
    # poste de barbeiro (listras animadas, passo 56.57 = loop perfeito)
    d.append('<pattern id="pole" width="40" height="40" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
             f'<rect width="14" height="40" fill="{INK}"/><rect x="14" width="13" height="40" fill="{PAPER}"/>'
             f'<rect x="27" width="13" height="40" fill="{ACC}"/></pattern>'
             '<clipPath id="polec"><rect x="9" y="14" width="46" height="190"/></clipPath>')
    o.append(R(0, 0, 64, 14, INK)); o.append(R(0, 204, 64, 14, INK))
    o.append(R(9, 14, 46, 190, PAPER))
    o.append('<g clip-path="url(#polec)"><g><animateTransform attributeName="transform" type="translate" '
             'from="0 0" to="0 56.57" dur="2.4s" repeatCount="indefinite"/>'
             '<rect x="0" y="-80" width="64" height="400" fill="url(#pole)"/></g></g>')
    o.append(BOX(9, 14, 46, 190, "none", INK, 3))
    # agenda
    ax, aw = 92, 164
    o.append(R(ax + 6, 6, aw, 108, INK))
    o.append(R(ax, 0, aw, 108, INK))
    o.append(R(ax, 0, aw, 26, ACC))
    o.append(T(M8, "AGENDA", 14, ax + 12, 18, INK, tr=0.08))
    on = {1, 8, 9, 15}
    for r in range(3):
        for c in range(6):
            k = r * 6 + c
            x, y = ax + 10 + c * 25, 36 + r * 24
            o.append(R(x, y, 20, 20, ACC if k in on else "#2B2B29"))
    o.append(f'<rect x="{ax + 10 + 3 * 25}" y="{36 + 2 * 24}" width="20" height="20" fill="{PAPER}" opacity="0">'
             f'<animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;0.3;0.31;0.7;0.71" dur="3.2s" repeatCount="indefinite"/></rect>')
    # faturamento
    o.append(R(ax, 130, aw, 3, INK))
    lab = "FATURAMENTO"
    o.append(T(M8, lab, 14, ax, 156, INK, tr=0.06))
    o.append(TRI_UP(ax + M8.width(lab, 14, 0.06) + 20, 155, 15, 13, ACC, INK, 2))
    hs = [14, 20, 16, 28, 34, 42, 54]
    base = 212
    for i, h in enumerate(hs):
        x = ax + 4 + i * 23.5
        hot = i == len(hs) - 1
        st = f' stroke="{INK}" stroke-width="2.5"' if hot else ""
        k0, k1 = 0.05 + i * 0.07, 0.3 + i * 0.07
        o.append(f'<rect x="{n(x)}" y="{base - h}" width="16" height="{h}" fill="{ACC if hot else INK}"{st}>'
                 f'<animate attributeName="height" values="0;0;{h};{h}" keyTimes="0;{k0:.2f};{k1:.2f};1" dur="4s" repeatCount="indefinite"/>'
                 f'<animate attributeName="y" values="{base};{base};{base - h};{base - h}" keyTimes="0;{k0:.2f};{k1:.2f};1" dur="4s" repeatCount="indefinite"/></rect>')
    o.append(R(ax, base, aw, 4, INK))
    return "".join(o), "".join(d)


def illo_quantica():
    o = []
    layers = [(20, [30, 86, 142]), (112, [6, 58, 110, 162]), (204, [28, 86, 144])]
    nodes = [[(x, y) for y in ys] for x, ys in layers]
    for a, bb in zip(nodes, nodes[1:]):
        for (x1, y1) in a:
            for (x2, y2) in bb:
                o.append(LINE(x1 + 11, y1 + 11, x2 + 11, y2 + 11, INK, 1.4, ' opacity="0.32"'))
    # órbita tracejada + elétron
    rx, ry, cx, cy, rot = 124, 46, 128, 98, -16
    o.append(f'<g transform="translate({cx} {cy}) rotate({rot})">'
             f'<ellipse cx="0" cy="0" rx="{rx}" ry="{ry}" fill="none" stroke="{INK}" stroke-width="2.2" stroke-dasharray="7 7">'
             f'<animate attributeName="stroke-dashoffset" from="0" to="-28" dur="1.6s" repeatCount="indefinite"/></ellipse>'
             f'<circle cx="{rx}" cy="0" r="7.5" fill="{ACC}" stroke="{INK}" stroke-width="2.5">'
             f'<animateMotion dur="6s" repeatCount="indefinite" path="M0,0 A{rx},{ry} 0 1 0 {-2 * rx},0 A{rx},{ry} 0 1 0 0,0"/></circle></g>')
    hot = {(0, 1), (1, 2), (2, 0), (2, 2), (1, 0)}
    for li, layer in enumerate(nodes):
        for ni, (x, y) in enumerate(layer):
            o.append(R(x, y, 22, 22, ACC, INK, 2.5) if (li, ni) in hot else R(x, y, 22, 22, INK))
    lab = "|0> + |1>"
    lw = M8.width(lab, 14, 0.04) + 26
    o.append(R(258 - lw + 6, 188 + 6, lw, 30, INK))
    o.append(R(258 - lw, 188, lw, 30, INK))
    o.append(T(M8, lab, 14, 258 - lw + 13, 208, ACC, tr=0.04))
    return "".join(o), ""


SEG = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
       "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def seg_digit(x, y, w, h, t, ch, on=ACC, off="#262624"):
    hs = t * 0.5
    def hor(yy):  # segmento horizontal
        return (f"M{n(x + t * 0.55)} {n(yy + hs)}L{n(x + t)} {n(yy)}H{n(x + w - t)}L{n(x + w - t * 0.55)} {n(yy + hs)}"
                f"L{n(x + w - t)} {n(yy + t)}H{n(x + t)}Z")
    def ver(xx, y0, y1):
        return (f"M{n(xx + hs)} {n(y0 + t * 0.55)}L{n(xx + t)} {n(y0 + t)}V{n(y1 - t)}L{n(xx + hs)} {n(y1 - t * 0.55)}"
                f"L{n(xx)} {n(y1 - t)}V{n(y0 + t)}Z")
    mid = y + h / 2
    P = {"a": hor(y), "g": hor(mid - t / 2), "d": hor(y + h - t),
         "f": ver(x, y, mid), "b": ver(x + w - t, y, mid),
         "e": ver(x, mid, y + h), "c": ver(x + w - t, mid, y + h)}
    on_set = SEG.get(ch, "")
    return "".join(f'<path d="{P[s]}" fill="{on if s in on_set else off}"/>' for s in "abcdefg")


def illo_relogio():
    o = []
    X, Y, WW, HH = 0, 0, 258, 210
    o.append(R(X + 7, Y + 7, WW, HH, INK))
    o.append(R(X, Y, WW, HH, INK2))
    o.append(R(X, Y, WW, 28, PAPER))
    o.append(R(X, Y + 28, WW, 3, INK))
    o.append(T(M8, "relogio.exe", 13.5, X + 12, Y + 19.5, INK, tr=0.02))
    for i in range(3):
        o.append(R(X + WW - 14 - (3 - i) * 16 + 4, Y + 9, 10, 10, INK))
    # display 7-seg
    dw, dh, dt, gap = 32, 56, 7, 8
    total = 4 * dw + 4 * gap + 18
    sx, sy = X + (WW - total) / 2, Y + 46
    o.append(R(X + 12, sy - 12, WW - 24, dh + 24, "#0D0D0C", HAIR_I, 2))
    x = sx
    for i, ch in enumerate("0845"):
        o.append(seg_digit(x, sy, dw, dh, dt, ch))
        x += dw + gap
        if i == 1:
            for cyy in (sy + dh * 0.32, sy + dh * 0.68):
                o.append(f'<rect x="{n(x + 4)}" y="{n(cyy - 4.5)}" width="9" height="9" fill="{ACC}">'
                         f'<animate attributeName="opacity" values="1;1;0.15;0.15" keyTimes="0;0.5;0.5;1" dur="1.4s" repeatCount="indefinite"/></rect>')
            x += 18 + gap
    # comando + progresso + resultado
    cy = Y + 142
    o.append(RUNS(M7, [("$ ", ACC), ("pyinstaller --onefile", PAPER)], 14, X + 14, cy, 0.0)[0])
    o.append(BOX(X + 14, cy + 12, WW - 28, 20, "none", MUTE_I, 2))
    o.append(f'<rect x="{X + 18}" y="{cy + 16}" width="{WW - 36}" height="12" fill="{ACC}">'
             f'<animate attributeName="width" values="0;{WW - 36};{WW - 36}" keyTimes="0;0.7;1" dur="4s" repeatCount="indefinite"/></rect>')
    o.append(RUNS(M8, [(">> ", MUTE_I), ("relogio.exe ", PAPER), ("OK", ACC)], 14, X + 14, cy + 56, 0.0)[0])
    return "".join(o), ""


def illo_despesas():
    o = []
    lab = "R$ PARA ONDE FOI?"
    lw = M8.width(lab, 14.5, 0.04) + 28
    o.append(R(6, 6, lw, 32, INK)); o.append(R(0, 0, lw, 32, INK))
    o.append(T(M8, lab, 14.5, 14, 21.5, ACC, tr=0.04))
    base = 184
    for gy in (52, 84, 116, 148):
        o.append(LINE(0, gy, 252, gy, INK, 1.5, ' stroke-dasharray="5 6" opacity="0.28"'))
    months = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN"]
    hs = [54, 74, 48, 108, 82, 96]
    bw, gp, x0 = 28, 13, 8
    for i, (m, h) in enumerate(zip(months, hs)):
        x = x0 + i * (bw + gp)
        hot = i == 3
        st = f' stroke="{INK}" stroke-width="3"' if hot else ""
        k0, k1 = 0.05 + i * 0.06, 0.35 + i * 0.06
        o.append(f'<rect x="{x}" y="{base - h}" width="{bw}" height="{h}" fill="{ACC if hot else INK}"{st}>'
                 f'<animate attributeName="height" values="0;0;{h};{h}" keyTimes="0;{k0:.2f};{k1:.2f};1" dur="4s" repeatCount="indefinite"/>'
                 f'<animate attributeName="y" values="{base};{base};{base - h};{base - h}" keyTimes="0;{k0:.2f};{k1:.2f};1" dur="4s" repeatCount="indefinite"/></rect>')
        o.append(T(M8, m, 13, x + bw / 2, base + 25, INK, tr=0.02, anchor="m"))
    o.append(R(0, base, 252, 4, INK))
    return "".join(o), ""


def cards():
    out = {}
    il, df = illo_saas()
    out["card-saas.svg"] = card_frame(1, ["SAAS"], 96, ["SISTEMA COMPLETO", "PARA BARBEARIA."],
                                      ["JAVASCRIPT", "SAAS"], il, df, title_base=150)
    il, df = illo_quantica()
    out["card-quantica.svg"] = card_frame(2, ["REDE", "NEURAL", "QUÂNTICA"], 40,
                                          ["SIMULAÇÃO DA ESTRUTURA", "DE UMA REDE QUÂNTICA."],
                                          ["HTML", "IA", "SIMULAÇÃO"], il, df, title_base=98)
    il, df = illo_relogio()
    out["card-relogio.svg"] = card_frame(3, ["RELÓGIO", "DIGITAL"], 46,
                                         ["PYTHON + TKINTER", "EMPACOTADO EM .EXE."],
                                         ["PYTHON", "TKINTER", "PYINSTALLER"], il, df, title_base=112)
    il, df = illo_despesas()
    out["card-despesas.svg"] = card_frame(4, ["GRÁFICO", "DESPESAS"], 46,
                                          ["APP QUE TRANSFORMA", "GASTO EM GRÁFICO."],
                                          ["PYTHON", "DADOS"], il, df, title_base=112)
    # títulos de acessibilidade
    titles = {"card-saas.svg": "SaaS — sistema completo para barbearia (JavaScript)",
              "card-quantica.svg": "Rede Neural Quântica — simulação da estrutura de uma rede neural quântica (HTML)",
              "card-relogio.svg": "Relógio Digital — Python com Tkinter, empacotado em .exe com PyInstaller",
              "card-despesas.svg": "Gráfico de Despesas — app que transforma gasto em gráfico (Python)"}
    for k, v in titles.items():
        out[k] = out[k].replace("<title></title>", f"<title>{v}</title>")
    return out


# ═════════════════════════ FERRAMENTAS ═════════════════════════
def ferramentas():
    W, H = 912, 362
    items = [("01 / LINGUAGEM", "PYTHON"), ("02 / LINGUAGEM", "JAVASCRIPT"), ("03 / ESTRUTURA", "HTML5"),
             ("04 / ESTILO", "CSS3"), ("05 / INTERFACE DESKTOP", "TKINTER"), ("06 / EMPACOTA .EXE", "PYINSTALLER"),
             ("07 / VERSIONAMENTO", "GIT"), ("08 / CÓDIGO NA NUVEM", "GITHUB")]
    fills = [ACC, PAPER, INK, PAPER, INK, PAPER, INK, ACC]
    tw, th = 225, 128
    b = []
    for i, (lab, name) in enumerate(items):
        r_, c_ = divmod(i, 4)
        x, y = c_ * tw, r_ * th
        f = fills[i]
        b.append(R(x, y, tw + 3, th + 3, f))
        fg = INK if f in (ACC, PAPER) else PAPER
        sub = MUTE_P if f == PAPER else (INK if f == ACC else MUTE_I)
        acc_mark = INK if f == ACC else (ACC if f == INK else INK)
        b.append(T(M7, lab, 12, x + 20, y + 36, sub if f != ACC else INK, tr=0.02))
        warn(20 + M7.width(lab, 12, 0.02) < tw - 34, f"tile label overlaps marker: {lab}")
        b.append(R(x + tw - 28, y + 26, 10, 10, acc_mark))
        size = DISP.fit(name, tw - 44, -0.03, 42)
        b.append(T(DISP, name, size, x + 18, y + th - 24, fg, tr=-0.03))
    # grelha externa e internas
    b.append(BOX(0, 0, tw * 4 + 3, th * 2 + 3, "none", INK, 3))
    for c_ in range(1, 4):
        b.append(R(c_ * tw, 0, 3, th * 2 + 3, INK))
    b.append(R(0, th, tw * 4 + 3, 3, INK))
    # barra de áreas
    by = th * 2 + 3 + 24
    bh = 62
    b.append(R(10, by + 10, tw * 4 + 3, bh, ACC))
    b.append(R(0, by, tw * 4 + 3, bh, INK))
    b.append(T(M8, "ÁREAS DE ATAQUE:", 15, 22, by + 36, ACC, tr=0.08))
    x = 22 + M8.width("ÁREAS DE ATAQUE:", 15, 0.08) + 26
    for ch in ["WEB", "SAAS", "AUTOMAÇÃO", "IA", "DESKTOP"]:
        cw = M8.width(ch, 15, 0.06) + 32
        b.append(R(x, by + 15, cw, 32, PAPER))
        b.append(T(M8, ch, 15, x + 16, by + 37, INK, tr=0.06))
        x += cw + 12
    warn(x < tw * 4, f"areas overflow {x}")
    return SVG(W, by + bh + 12, "\n".join(b),
               "Python, JavaScript, HTML5, CSS3, Tkinter, PyInstaller, Git e GitHub. "
               "Áreas de ataque: Web, SaaS, Automação, IA e Desktop.")


# ═════════════════════════ MANIFESTO ═════════════════════════
def manifesto():
    W, H = 912, 392
    rows = [["FUNCIONAR VENCE PARECER BONITO."], ["SE REPETE, AUTOMATIZA."],
            ["SE É GRANDE, QUEBRA EM PEDAÇOS."],
            ["PROTÓTIPO FEIO QUE RODA", ">", "IDEIA PERFEITA NO PAPEL."],
            ["PROBLEMA REAL", ">", "PROJETO DE VITRINE."]]
    full = ["".join(r) + ("    " if ">" in r else "") for r in rows]
    size = min(DISPX.fit(t, 712, -0.015) for t in full)
    size = min(size, 31)
    rh, gap = 64, 12
    b = []
    for i, r in enumerate(rows):
        y = i * (rh + gap)
        g = []
        g.append(R(8, y + 8, 892, rh, INK))
        g.append(BOX(0, y, 892, rh, PAPER if i % 2 else ACC, INK, 3))
        g.append(R(0, y, 84, rh, INK))
        g.append(T(DISP, str(i + 1), 40, 42, y + rh / 2 + DISP.cap(40) / 2, ACC if i % 2 == 0 else PAPER, tr=-0.02, anchor="m"))
        x = 112
        base = y + rh / 2 + DISPX.cap(size) / 2
        for seg in r:
            if seg == ">":
                cw_ = DISPX.width(">", size, -0.015) + 20
                x += 14
                g.append(R(x, y + 14, cw_, rh - 28, INK))
                g.append(T(DISPX, ">", size, x + 10, base, ACC, tr=-0.015))
                x += cw_ + 14
            else:
                d, w = DISPX.path(seg, size, x, base, -0.015)
                g.append(f'<path d="{d}" fill="{INK}"/>')
                x += w - 0.015 * size
        warn(x < 880, f"manifesto row {i}: {x}")
        # atraso embutido nos keyTimes: todas começam em 0s (sem "flash" do estado base antes de entrar)
        delay, run = i * 0.14, 0.5
        t1 = delay / (delay + run) if delay else 0.0
        if delay:
            anim = (f'values="-940 0;-940 0;0 0" keyTimes="0;{t1:.4f};1" '
                    f'keySplines="0 0 1 1;0.2 0.8 0.2 1" dur="{delay + run:.2f}s"')
        else:
            anim = f'values="-940 0;0 0" keyTimes="0;1" keySplines="0.2 0.8 0.2 1" dur="{run}s"'
        b.append(f'<g><animateTransform attributeName="transform" type="translate" {anim} '
                 f'begin="0s" fill="freeze" calcMode="spline"/>{"".join(g)}</g>')
    return SVG(W, H, "\n".join(b),
               "1. Funcionar vence parecer bonito. 2. Se repete, automatiza. 3. Se é grande, quebra em pedaços. "
               "4. Protótipo feio que roda é melhor que ideia perfeita no papel. "
               "5. Problema real é melhor que projeto de vitrine.")


# ═════════════════════════ BOTÕES ═════════════════════════
def button(kind):
    W, H = 440, 100
    site = kind == "site"
    fill, fg, shadow, cap, capfg = (ACC, INK, INK, INK, ACC) if site else (INK, PAPER, ACC, ACC, INK)
    name, url = ("SITE", "www.ianakiles.com.br") if site else ("GITHUB", "github.com/IanAkiles")
    b = [R(10, 10, 426, 86, shadow), BOX(0, 0, 426, 86, fill, INK, 3)]
    b.append(R(338, 0, 88, 86, cap))
    b.append(R(335, 0, 3, 86, INK))
    b.append(T(DISP, name, 40, 26, 54, fg, tr=-0.025))
    b.append(T(M8, url, 15.5, 27, 74, fg if site else MUTE_I, tr=0.03))
    b.append(f'<g>{ARROW(358, 43, 40, 12, capfg, 5)}<animateTransform attributeName="transform" type="translate" '
             f'values="0 0;7 0;0 0" dur="1.6s" repeatCount="indefinite"/></g>')
    if not site:
        b.insert(1, R(0, 0, 426, 86, "none", HAIR_I, 1))
    t = "Site — www.ianakiles.com.br" if site else "GitHub — github.com/IanAkiles"
    return SVG(W, H, "\n".join(b), t)


# ═════════════════════════ RODAPÉ ═════════════════════════
def footer():
    W, H = 912, 150
    defs, b = [], []
    b.append(R(0, 0, W, H, INK))
    d1, b1 = hazard("fa", 0, 0, W, 14, dur=2.6)
    d2, b2 = hazard("fb", 0, H - 14, W, 14, dur=2.6, reverse=True)
    defs += [d1, d2]
    b += [b1, b2]
    txt = "VÁ CONSTRUIR ALGUMA COISA."
    size = DISP.fit(txt, 740, -0.025, 56)
    tw = DISP.width(txt, size, -0.025)
    cap = DISP.cap(size)
    cur_w = 22
    total = tw + 20 + cur_w
    x0 = (W - total) / 2
    base = 78 + cap / 2 - 6
    b.append(T(DISP, txt, size, x0, base, PAPER, tr=-0.025))
    b.append(f'<rect x="{n(x0 + tw + 20)}" y="{n(base - cap)}" width="{cur_w}" height="{n(cap)}" fill="{ACC}">{BLINK(1.0)}</rect>')
    b.append(T(M7, "BUILD // SHIP // REPEAT", 13, 28, 124, MUTE_I, tr=0.12))
    b.append(T(M7, "// EOF", 13, W - 28, 124, DIM_I, tr=0.12, anchor="e"))
    return SVG(W, H, "\n".join(b), "Vá construir alguma coisa.", "".join(defs))


# ═════════════════════════ main ═════════════════════════
def build_all():
    out = {"banner.svg": banner(), "divider.svg": divider(), "terminal.svg": terminal(),
           "quote.svg": quote(), "ferramentas.svg": ferramentas(), "manifesto.svg": manifesto(),
           "btn-site.svg": button("site"), "btn-github.svg": button("github"), "footer.svg": footer()}
    for i, t in enumerate(["QUEM", "PROJETOS", "FERRAMENTAS", "MANIFESTO", "CONTATO"], 1):
        out[f"sec-{i:02d}.svg"] = section(i, t)
    out.update(cards())
    return out


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
    os.makedirs(dest, exist_ok=True)
    for name, content in build_all().items():
        with open(os.path.join(dest, name), "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"{name:20s} {len(content) / 1024:6.1f} KB")
