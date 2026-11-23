#!/usr/bin/env python3
"""Video vertical (1080x1920) para TikTok: los tiburones son más antiguos que los árboles.

Necesita la narración generada por narracion.py (voz.wav + tiempos.json).
Uso:  python3 make_tiktok.py <dir_con_voz_y_tiempos> [salida.mp4]
"""
import json
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FPS = 30
SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
VDIR = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "tiburones_tiktok.mp4")

INFO = json.load(open(os.path.join(VDIR, "tiempos.json")))
FR = INFO["frases"]
TOTAL = FR[-1]["end"] + 1.6

FB = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FX = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FS = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FE = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
YELLOW = (255, 225, 77)

_fc = {}


def font(p, s):
    s = max(6, int(s))
    if (p, s) not in _fc:
        _fc[(p, s)] = ImageFont.truetype(p, s)
    return _fc[(p, s)]


# ------------------------------------------------------------------ easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def eo(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def eb(t, s=1.9):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def eio(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ gráficos
def vgrad(stops):
    """Degradado vertical a partir de [(pos, (r,g,b)), ...]."""
    ys = np.linspace(0, 1, H)
    cols = np.zeros((H, 3))
    for c in range(3):
        cols[:, c] = np.interp(ys, [p for p, _ in stops], [col[c] for _, col in stops])
    img = np.repeat(cols[:, None, :], W, axis=1)
    xx = np.linspace(-1, 1, W)[None, :, None]
    img *= 1 - 0.25 * xx ** 2
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB").convert("RGBA")


BGS = {}


def bg(name):
    if name not in BGS:
        BGS[name] = {
            "ocean": lambda: vgrad([(0, (20, 120, 190)), (0.45, (8, 60, 120)), (1, (2, 18, 48))]),
            "deep": lambda: vgrad([(0, (40, 20, 60)), (0.5, (60, 15, 35)), (1, (10, 5, 20))]),
            "barren": lambda: vgrad([(0, (250, 160, 90)), (0.55, (240, 120, 80)), (1, (120, 60, 40))]),
            "green": lambda: vgrad([(0, (120, 200, 255)), (0.6, (190, 235, 255)), (1, (90, 160, 90))]),
            "night": lambda: vgrad([(0, (16, 22, 60)), (0.5, (30, 40, 110)), (1, (8, 10, 30))]),
            "gold": lambda: vgrad([(0, (255, 190, 60)), (0.5, (240, 110, 40)), (1, (120, 30, 60))]),
            "pink": lambda: vgrad([(0, (255, 80, 140)), (0.5, (150, 40, 200)), (1, (40, 20, 90))]),
        }[name]()
    return BGS[name].copy()


_ec = {}


def emoji(ch, size, flip=False):
    size = max(2, int(size))
    key = (ch, size, flip)
    if key not in _ec:
        b = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(b).text((80, 80), ch, font=font(FE, 109), embedded_color=True, anchor="mm")
        b = b.crop(b.getbbox())
        sc = size / max(b.size)
        im = b.resize((max(1, int(b.width * sc)), max(1, int(b.height * sc))), Image.LANCZOS)
        if flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        _ec[key] = im
    return _ec[key]


def paste(base, im, cx, cy, rot=0.0, alpha=1.0):
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def layer():
    L = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return L, ImageDraw.Draw(L, "RGBA")


def big_text(d, xy, txt, size, fill=(255, 255, 255), alpha=1.0, fnt=FB, stroke=10, anchor="mm"):
    a = int(255 * clamp(alpha))
    if a <= 0:
        return
    d.text(xy, txt, font=font(fnt, size), fill=fill + (a,), anchor=anchor,
           stroke_width=stroke, stroke_fill=(0, 0, 0, a))


def bubbles(d, t, seed, n=26, alpha=70):
    r = random.Random(seed)
    for _ in range(n):
        x, y0, rad, sp, ph = r.uniform(0, W), r.uniform(0, H), r.uniform(4, 18), r.uniform(60, 180), r.uniform(0, 6)
        y = (y0 - sp * t) % (H + 60) - 30
        xx = x + 12 * math.sin(t * 2 + ph)
        d.ellipse([xx - rad, y - rad, xx + rad, y + rad], outline=(255, 255, 255, alpha), width=3)


def light_rays(d, t):
    for k in range(6):
        x = 120 + k * 190 + 60 * math.sin(t * 0.6 + k)
        w = 60 + 30 * math.sin(t + k * 1.7)
        d.polygon([(x - w / 2, 0), (x + w / 2, 0), (x + w * 2.4 - 160, H), (x - w * 1.2 - 160, H)],
                  fill=(255, 255, 255, 16))


def dust(d, t, seed, col=(255, 255, 255), n=30, alpha=60):
    r = random.Random(seed)
    for _ in range(n):
        x, y0, rad, sp = r.uniform(0, W), r.uniform(0, H), r.uniform(2, 6), r.uniform(10, 40)
        y = (y0 - sp * t) % H
        d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=col + (alpha,))


def ground(d, top, col, col2, seed=3, wav=40):
    pts = [(0, H)]
    r = random.Random(seed)
    ph = r.uniform(0, 6)
    for x in range(0, W + 40, 40):
        pts.append((x, top + wav * math.sin(x / 170 + ph) + 15 * math.sin(x / 53)))
    pts.append((W, H))
    d.polygon(pts, fill=col)
    for _ in range(14):
        x, y = r.uniform(0, W), r.uniform(top + 60, H)
        rw = r.uniform(30, 90)
        d.ellipse([x - rw, y - rw * 0.45, x + rw, y + rw * 0.45], fill=col2)


def tree(d, x, base, h, grow, sway=0.0):
    """Árbol estilizado que crece con grow∈[0,1]."""
    if grow <= 0:
        return
    th = h * eo(grow / 0.6)
    tw = h * 0.09
    top = base - th
    d.polygon([(x - tw, base), (x + tw, base), (x + tw * 0.55 + sway, top), (x - tw * 0.55 + sway, top)],
              fill=(110, 70, 40, 255))
    cg = eb((grow - 0.4) / 0.6)
    if cg > 0:
        for dx, dy, rr in [(0, -0.05, 0.42), (-0.28, 0.12, 0.3), (0.28, 0.12, 0.3), (0, 0.22, 0.32),
                           (-0.15, -0.25, 0.25), (0.17, -0.22, 0.26)]:
            R = rr * h * 0.62 * cg
            cx, cy = x + sway + dx * h * 0.6 * cg, top + dy * h * 0.6 * cg
            d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(46, 160, 67, 255))
            d.ellipse([cx - R * 0.6 - R * 0.2, cy - R * 0.75, cx + R * 0.2, cy - R * 0.05],
                      fill=(78, 188, 92, 255))


def counter(d, t, val, label, y=470, color=YELLOW, delay=0.2, dur=1.4, size=230):
    p = eo((t - delay) / dur)
    if p <= 0:
        return
    v = int(round(val * p))
    s = 1 + 0.12 * math.exp(-max(0, t - delay - dur) * 6) * (1 if p >= 1 else 0)
    big_text(d, (W / 2, y), f"{v}", size * s, fill=color, stroke=14)
    big_text(d, (W / 2, y + size * 0.72), label, 62, alpha=eo((t - delay - 0.3) / 0.5), stroke=8)


def title(d, t, txt, y=300, size=92, delay=0.0, fill=(255, 255, 255)):
    p = eb((t - delay) / 0.5)
    if p <= 0.01:
        return
    big_text(d, (W / 2, y), txt, size * p, fill=fill, stroke=11)


# ------------------------------------------------------------------ escenas
def sc_hook(t, dur):
    f = bg("ocean")
    L, d = layer()
    light_rays(d, t)
    bubbles(d, t, 1, 16)
    f.alpha_composite(L)
    L, d = layer()
    # mitad inferior: tierra
    split = H * 0.5 + 18 * math.sin(t * 2)
    d.rectangle([0, split, W, H], fill=(140, 210, 255, 255))
    ground(d, split + 330, (110, 170, 80, 255), (90, 150, 70, 255))
    d.rectangle([0, split - 6, W, split + 6], fill=(255, 255, 255, 255))
    f.alpha_composite(L)
    # tiburón y árbol
    a = eb((t - 0.15) / 0.6)
    paste(f, emoji("🦈", 420 * a), W / 2 + 15 * math.sin(t * 3), H * 0.31 + 12 * math.sin(t * 2.4),
          rot=5 * math.sin(t * 2.2))
    b = eb((t - 0.45) / 0.6)
    paste(f, emoji("🌳", 360 * b), W / 2, H * 0.635, rot=3 * math.sin(t * 1.7))
    L, d = layer()
    # VS
    v = eb((t - 0.9) / 0.5)
    if v > 0.01:
        r = 105 * v * (1 + 0.06 * math.sin(t * 8))
        cy = split
        d.ellipse([W / 2 - r, cy - r, W / 2 + r, cy + r], fill=(255, 50, 80, 255), outline=(255, 255, 255, 255), width=10)
        big_text(d, (W / 2, cy + 4), "VS", 100 * v, stroke=6)
    title(d, t, "¿QUIÉN LLEGÓ", 250, 96, 0.2)
    title(d, t, "PRIMERO?", 360, 120, 0.35, fill=YELLOW)
    f.alpha_composite(L)
    # medalla para el tiburón al final de la frase
    m = eb((t - 3.3) / 0.5)
    if m > 0.01:
        paste(f, emoji("🥇", 170 * m), W / 2 + 290, H * 0.25, rot=-10)
    return f


def sc_450(t, dur):
    f = bg("ocean")
    L, d = layer()
    light_rays(d, t)
    bubbles(d, t, 2)
    # fondo marino
    ground(d, H - 260, (194, 170, 120, 255), (170, 150, 100, 255), seed=9, wav=25)
    for k, x in enumerate([90, 260, 860, 1000]):
        for j in range(5):
            sw = 18 * math.sin(t * 1.8 + j * 0.6 + k)
            d.line([(x + j * 6, H - 230), (x + j * 6 + sw, H - 360 - j * 18)], fill=(40, 170, 110, 220), width=12)
    f.alpha_composite(L)
    # tiburones nadando
    for k, (sz, yy, sp, off) in enumerate([(380, 1030, 260, 0), (170, 1330, 180, 500), (120, 820, 140, 800)]):
        x = W + 300 - ((t * sp + off) % (W + 600))
        paste(f, emoji("🦈", sz), x, yy + 20 * math.sin(t * 2.5 + k), rot=4 * math.sin(t * 3 + k))
    L, d = layer()
    counter(d, t, 450, "MILLONES DE AÑOS")
    title(d, t, "HACE…", 260, 80, 0.0)
    f.alpha_composite(L)
    return f


def sc_barren(t, dur):
    f = bg("barren")
    L, d = layer()
    sr = 150
    d.ellipse([W - 330, 260, W - 330 + sr * 2, 260 + sr * 2], fill=(255, 235, 170, 255))
    dust(d, t, 4, (255, 230, 200))
    ground(d, 1150, (150, 90, 60, 255), (125, 75, 50, 255), seed=5, wav=70)
    for x, y, s in [(170, 1250, 90), (760, 1200, 130), (520, 1380, 70)]:
        d.polygon([(x - s, y), (x - s * 0.4, y - s * 0.9), (x + s * 0.3, y - s * 0.7), (x + s, y)], fill=(110, 70, 55, 255))
    f.alpha_composite(L)
    L, d = layer()
    title(d, t, "TIERRA FIRME:", 260, 86, 0.0)
    title(d, t, "¡CASI UN DESIERTO!", 370, 88, 0.3, fill=YELLOW)
    f.alpha_composite(L)
    # iconos tachados
    words_t = [2.3, 3.3, 4.3]
    for k, (e, tt) in enumerate(zip(["🌳", "🌸", "🦕"], words_t)):
        a = eb((t - tt + 0.6) / 0.5)
        if a <= 0.01:
            continue
        x = 220 + k * 320
        y = 720
        paste(f, emoji(e, 200 * a), x, y)
        c = eo((t - tt) / 0.3)
        if c > 0:
            L, d = layer()
            r = 120
            d.line([(x - r, y - r), (x - r + 2 * r * c, y - r + 2 * r * c)], fill=(230, 30, 50, 255), width=26)
            d.line([(x + r, y - r), (x + r - 2 * r * c, y - r + 2 * r * c)], fill=(230, 30, 50, 255), width=26)
            f.alpha_composite(L)
    return f


def sc_moss(t, dur):
    f = bg("barren")
    L, d = layer()
    dust(d, t, 6, (255, 230, 200))
    ground(d, 1250, (150, 90, 60, 255), (125, 75, 50, 255), seed=7, wav=40)
    # roca grande
    cx, cy = W / 2, 980
    d.polygon([(cx - 380, cy + 260), (cx - 300, cy - 60), (cx - 80, cy - 170), (cx + 200, cy - 120),
               (cx + 380, cy + 40), (cx + 420, cy + 260)], fill=(120, 110, 105, 255))
    d.polygon([(cx - 300, cy - 60), (cx - 80, cy - 170), (cx + 200, cy - 120), (cx + 60, cy - 60)],
              fill=(150, 140, 135, 255))
    # musgo creciendo
    r = random.Random(11)
    for k in range(70):
        g = eo((t - 0.5 - k * 0.03) / 0.5)
        if g <= 0:
            continue
        x = cx + r.uniform(-330, 360)
        y = cy - 150 + abs(x - cx) * 0.18 + r.uniform(-10, 40) + (60 if abs(x - cx) > 250 else 0)
        rr = r.uniform(14, 30) * g
        d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(80 + r.randint(0, 40), 160 + r.randint(0, 40), 60, 255))
    # regla
    rp = eo((t - 2.5) / 0.6)
    if rp > 0:
        x0 = 120
        d.rounded_rectangle([x0, 640, x0 + 70, 640 + 300 * rp], radius=8, fill=(255, 220, 90, 255))
        for k in range(int(10 * rp)):
            d.line([(x0, 660 + k * 30), (x0 + (40 if k % 5 == 0 else 22), 660 + k * 30)], fill=(60, 40, 20, 255), width=4)
        big_text(d, (x0 + 35, 600), "cm", 54, alpha=rp, stroke=6)
    f.alpha_composite(L)
    L, d = layer()
    title(d, t, "LAS ÚNICAS PLANTAS:", 260, 78, 0.0)
    title(d, t, "MUSGOS DIMINUTOS", 370, 92, 0.3, fill=(140, 255, 120))
    f.alpha_composite(L)
    paste(f, emoji("🔍", 210 * eb((t - 1.2) / 0.5)), cx + 250 + 30 * math.sin(t * 1.5), cy - 260 + 20 * math.cos(t * 1.5))
    return f


def sc_trees(t, dur):
    f = bg("green")
    L, d = layer()
    d.ellipse([60, 560, 300, 800], fill=(255, 240, 150, 255))
    ground(d, 1300, (100, 160, 70, 255), (85, 140, 60, 255), seed=8, wav=30)
    for k, (x, h, dl) in enumerate([(540, 620, 0.5), (220, 430, 1.0), (860, 470, 1.4), (90, 300, 1.9),
                                     (990, 320, 2.2), (390, 280, 2.6), (700, 300, 2.9)]):
        g = clamp((t - dl) / 1.6)
        base = 1330 + (k % 3) * 25
        tree(d, x, base, h, g, sway=8 * math.sin(t * 1.5 + k))
    f.alpha_composite(L)
    L, d = layer()
    title(d, t, "LOS PRIMEROS ÁRBOLES…", 250, 70, 0.0)
    counter(d, t, 385, "MILLONES DE AÑOS", y=430, color=(60, 230, 90), delay=1.6, size=200)
    f.alpha_composite(L)
    return f


def sc_timeline(t, dur):
    f = bg("night")
    L, d = layer()
    dust(d, t, 12, (255, 255, 255), 50, 90)
    title(d, t, "VENTAJA DEL TIBURÓN", 250, 82, 0.0, fill=YELLOW)
    x = 300
    y0, y1 = 520, 1180
    p = eio((t - 0.2) / 1.2)
    d.rounded_rectangle([x - 9, y0, x + 9, y0 + (y1 - y0) * p], radius=9, fill=(255, 255, 255, 230))
    f.alpha_composite(L)

    def ypos(v):
        return y0 + (450 - v) / 450 * (y1 - y0)

    marks = [(450, "🦈", "450 M", "Tiburones", 0.4), (385, "🌳", "385 M", "Árboles", 0.9),
             (230, "🦕", "230 M", "Dinosaurios", 1.4), (0, "🧍", "HOY", "Humanos", 1.9)]
    for v, e, lab, name, dl in marks:
        a = eb((t - dl) / 0.5)
        if a <= 0.01:
            continue
        y = ypos(v)
        L, d = layer()
        r = 22 * a
        d.ellipse([x - r, y - r, x + r, y + r], fill=YELLOW + (255,), outline=(0, 0, 0, 255), width=4)
        big_text(d, (x - 50, y), lab, 52 * a, anchor="rm", stroke=7)
        big_text(d, (x + 190, y), name, 58 * a, anchor="lm", stroke=7)
        f.alpha_composite(L)
        paste(f, emoji(e, 110 * a), x + 110, y)
    # llave de ventaja
    b = eo((t - 2.6) / 0.7)
    if b > 0:
        L, d = layer()
        ya, yb = ypos(450), ypos(450) + (ypos(385) - ypos(450)) * b
        xb = 860
        d.line([(xb, ya), (xb + 40, ya), (xb + 40, yb), (xb, yb)], fill=(255, 80, 100, 255), width=10)
        big_text(d, (690, ypos(230) + 130), "+65 MILLONES", 78, fill=(255, 90, 110), alpha=b, stroke=10)
        big_text(d, (690, ypos(230) + 205), "DE AÑOS ANTES", 56, alpha=b, stroke=8)
        f.alpha_composite(L)
    return f


def sc_extinct(t, dur):
    f = bg("deep")
    L, d = layer()
    bubbles(d, t, 21, 18, 50)
    # escudo pulsante
    cx, cy = W / 2, 940
    for k in range(3):
        rr = 220 + k * 45 + 15 * math.sin(t * 3 + k)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=(120, 220, 255, 120 - k * 35), width=10)
    f.alpha_composite(L)
    paste(f, emoji("🦈", 320), cx + 10 * math.sin(t * 2), cy + 12 * math.sin(t * 2.5), rot=5 * math.sin(t * 2.2))
    icons = ["🧊", "🌊", "🌋", "🔥", "☄️"]
    n_on = 0
    for k, e in enumerate(icons):
        tk = 0.6 + k * 0.55
        a = eb((t - tk) / 0.4)
        if a <= 0.01:
            continue
        n_on = k + 1
        ang = -math.pi / 2 + (k - 2) * 0.62
        rr = 460
        x, y = cx + rr * math.cos(ang) * 0.95, cy - 120 + rr * math.sin(ang) * 0.75 + 40
        x = 140 + k * 200
        y = 600 + 20 * math.sin(t * 3 + k)
        paste(f, emoji(e, 140 * a), x, y)
    # meteorito cruzando (extinción de los dinosaurios)
    m = (t - 4.0) / 1.2
    if 0 < m < 1:
        paste(f, emoji("☄️", 240), lerp(W + 150, -150, m), lerp(400, 1500, m), rot=0)
    if 0.75 < m < 1.1:
        L, d = layer()
        d.rectangle([0, 0, W, H], fill=(255, 200, 150, int(160 * (1 - abs(m - 0.9) / 0.2))))
        f.alpha_composite(L)
    L, d = layer()
    big_text(d, (W / 2, 300), f"{n_on}", 170, fill=(255, 90, 110), stroke=12, alpha=1 if n_on else 0)
    title(d, t, "EXTINCIONES MASIVAS", 430, 78, 0.2)
    s = eb((t - 3.2) / 0.5)
    if s > 0.01:
        d.rounded_rectangle([W / 2 - 330 * s, 1275 - 60 * s, W / 2 + 330 * s, 1275 + 60 * s], radius=60 * s,
                            fill=(60, 200, 120, 255), outline=(255, 255, 255, 255), width=6)
        big_text(d, (W / 2, 1277), "✓ SOBREVIVIÓ" if s > 0.6 else "", 64 * s, stroke=0)
    f.alpha_composite(L)
    return f


def sc_species(t, dur):
    f = bg("ocean")
    L, d = layer()
    light_rays(d, t)
    bubbles(d, t, 31)
    f.alpha_composite(L)
    L, d = layer()
    counter(d, t, 500, "ESPECIES", y=380, delay=0.1, dur=1.2, size=200)
    p = eb((t - 0.1) / 0.4)
    if p > 0.01:
        big_text(d, (W / 2 - 230, 380), "+", 160 * p, fill=YELLOW, stroke=12)
    f.alpha_composite(L)
    # linterna (pequeño) vs ballena (enorme)
    a = eb((t - 1.8) / 0.5)
    if a > 0.01:
        L, d = layer()
        d.rounded_rectangle([60, 680, 400, 1000], radius=40, fill=(255, 255, 255, int(40 * a)))
        big_text(d, (230, 1050), "LINTERNA", 52 * a, stroke=7)
        big_text(d, (230, 1115), "~20 cm", 56 * a, fill=YELLOW, stroke=7)
        # brillo de linterna
        g = 60 + 20 * math.sin(t * 6)
        d.ellipse([230 - g, 840 - g, 230 + g, 840 + g], fill=(120, 230, 255, 60))
        f.alpha_composite(L)
        paste(f, emoji("🦈", 80 * a), 230, 840 + 8 * math.sin(t * 4))
    b = eb((t - 3.6) / 0.6)
    if b > 0.01:
        paste(f, emoji("🦈", 480 * b), 730 + 10 * math.sin(t * 1.5), 850 + 15 * math.sin(t * 1.8), rot=3 * math.sin(t))
        L, d = layer()
        big_text(d, (740, 1150), "BALLENA", 52 * b, stroke=7)
        big_text(d, (740, 1215), "+12 m", 56 * b, fill=YELLOW, stroke=7)
        f.alpha_composite(L)
    return f


def sc_survivor(t, dur):
    f = bg("gold")
    L, d = layer()
    cx, cy = W / 2, 960
    for k in range(18):
        ang = k * math.pi / 9 + t * 0.35
        d.polygon([(cx, cy), (cx + 1800 * math.cos(ang - 0.07), cy + 1800 * math.sin(ang - 0.07)),
                   (cx + 1800 * math.cos(ang + 0.07), cy + 1800 * math.sin(ang + 0.07))], fill=(255, 255, 255, 30))
    dust(d, t, 41, (255, 255, 220), 40, 120)
    f.alpha_composite(L)
    s = eb((t - 0.2) / 0.7)
    paste(f, emoji("🦈", 560 * s * (1 + 0.03 * math.sin(t * 3))), cx, cy + 15 * math.sin(t * 2), rot=4 * math.sin(t * 2))
    c = eb((t - 1.0) / 0.5)
    paste(f, emoji("👑", 220 * c), cx + 40, cy - 330 + 15 * math.sin(t * 3), rot=-12)
    for k in range(5):
        a = 0.5 + 0.5 * math.sin(t * 4 + k * 1.3)
        paste(f, emoji("✨", 90 * a * c + 2), cx + 380 * math.cos(k * 1.26 + 0.4), cy + 330 * math.sin(k * 1.26 + 0.4))
    L, d = layer()
    title(d, t, "UNO DE LOS", 260, 78, 0.8)
    title(d, t, "SUPERVIVIENTES", 370, 104, 1.1, fill=YELLOW)
    f.alpha_composite(L)
    return f


def sc_cta(t, dur):
    f = bg("pink")
    L, d = layer()
    dust(d, t, 51, (255, 255, 255), 40, 80)
    f.alpha_composite(L)
    paste(f, emoji("🦈", 300 * eb(t / 0.5)), W / 2, 700 + 15 * math.sin(t * 3), rot=6 * math.sin(t * 2.5))
    paste(f, emoji("🤯", 160 * eb((t - 0.3) / 0.5)), W / 2 + 230, 560, rot=10 * math.sin(t * 3))
    L, d = layer()
    title(d, t, "¡SÍGUENOS!", 330, 130, 0.0, fill=YELLOW)
    s = eb((t - 0.6) / 0.5) * (1 + 0.05 * math.sin(t * 7))
    if s > 0.01:
        d.rounded_rectangle([W / 2 - 300 * s, 1000 - 75 * s, W / 2 + 300 * s, 1000 + 75 * s], radius=75 * s,
                            fill=(255, 44, 85, 255), outline=(255, 255, 255, 255), width=6)
        big_text(d, (W / 2, 1003), "+ SEGUIR", 70 * s, stroke=0)
    big_text(d, (W / 2, 1180), "para más curiosidades", 58, alpha=eo((t - 1.0) / 0.5), fnt=FX, stroke=7)
    # fundido final
    fo = clamp((t - (dur - 0.7)) / 0.7)
    if fo > 0:
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(255 * fo)))
    f.alpha_composite(L)
    # corazones subiendo
    r = random.Random(5)
    for k in range(10):
        st = 0.8 + k * 0.3
        u = (t - st) / 2.2
        if 0 < u < 1:
            x = 880 + r.uniform(-60, 60) + 40 * math.sin(u * 8 + k)
            paste(f, emoji("❤️", 80 + r.uniform(-20, 20)), x, lerp(1500, 700, u), alpha=1 - u)
    return f


SCENES = [sc_hook, sc_450, sc_barren, sc_moss, sc_trees, sc_timeline, sc_extinct, sc_species,
          sc_survivor, sc_cta]
assert len(SCENES) == len(FR), (len(SCENES), len(FR))

# límites de escena: a mitad del silencio entre frases
BOUNDS = [0.0]
for i in range(1, len(FR)):
    BOUNDS.append((FR[i - 1]["end"] + FR[i]["start"]) / 2)
BOUNDS.append(TOTAL)


# ------------------------------------------------------------------ subtítulos
def build_captions():
    chunks = []
    for fr in FR:
        words = fr["text"].split()
        n = sum(len(w) + 2 for w in words)
        t = fr["start"]
        span = fr["end"] - fr["start"]
        wt = []
        for w in words:
            dt = span * (len(w) + 2) / n
            wt.append((w, t, t + dt))
            t += dt
        cur = []
        for w in wt:
            cur.append(w)
            if len(cur) >= 3 or w[0][-1] in ".,?!:" :
                chunks.append(cur)
                cur = []
        if cur:
            chunks.append(cur)
    return chunks


CAPS = build_captions()


def draw_captions(frame, T):
    cur = None
    for c in CAPS:
        if c[0][1] - 0.05 <= T < c[-1][2] + 0.15:
            cur = c
    if not cur:
        return
    L, d = layer()
    age = T - cur[0][1]
    s = 0.85 + 0.15 * eb(age / 0.18)
    fnt = font(FB, 92 * s)
    words = [w[0].upper() for w in cur]
    widths = [fnt.getlength(w) for w in words]
    space = fnt.getlength(" ")
    # hasta 2 líneas
    lines, line, lw = [], [], 0
    for i, w in enumerate(words):
        if line and lw + space + widths[i] > 940:
            lines.append(line)
            line, lw = [], 0
        lw += (space if line else 0) + widths[i]
        line.append(i)
    lines.append(line)
    y = 1430 - (len(lines) - 1) * 55
    for ln in lines:
        tot = sum(widths[i] for i in ln) + space * (len(ln) - 1)
        x = W / 2 - tot / 2
        for i in ln:
            active = cur[i][1] <= T < cur[i][2] + 0.05
            col = YELLOW if active else (255, 255, 255)
            d.text((x, y), words[i], font=fnt, fill=col + (255,), anchor="lm",
                   stroke_width=11, stroke_fill=(0, 0, 0, 255))
            x += widths[i] + space
        y += 110
    frame.alpha_composite(L)


def draw_hud(frame, T):
    L, d = layer()
    # etiqueta superior
    d.rounded_rectangle([W / 2 - 200, 140, W / 2 + 200, 200], radius=30, fill=(0, 0, 0, 120))
    d.text((W / 2, 171), "¿SABÍAS QUE…?", font=font(FX, 36), fill=(255, 255, 255, 255), anchor="mm")
    # barra de progreso
    d.rectangle([0, 0, W * T / TOTAL, 10], fill=YELLOW + (255,))
    frame.alpha_composite(L)


# ------------------------------------------------------------------ audio
def synth_audio(path):
    import soundfile as sf
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    music = np.zeros(n)
    sfx = np.zeros(n)

    def add(buf, sig, start):
        s = int(start * SR)
        if s >= n or s + len(sig) <= 0:
            return
        if s < 0:
            sig, s = sig[-s:], 0
        e = min(n, s + len(sig))
        buf[s:e] += sig[:e - s]

    def mtof(m):
        return 440 * 2 ** ((m - 69) / 12)

    bpm = 112
    beat = 60 / bpm
    bar = 4 * beat
    prog = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am F C G
    for b in range(int(TOTAL / bar) + 1):
        ch = prog[b % 4]
        t0 = b * bar
        L = int(bar * SR)
        tt = np.arange(L) / SR
        env = np.minimum(1, tt / 0.4) * np.minimum(1, (bar - tt) / 0.4)
        pad = sum(np.sin(2 * np.pi * mtof(m) * tt) + 0.25 * np.sin(4 * np.pi * mtof(m) * tt) for m in ch)
        add(music, 0.03 * pad * env, t0)
        for k in range(8):
            Lb = int(beat / 2 * SR)
            tb = np.arange(Lb) / SR
            add(music, 0.12 * np.sin(2 * np.pi * mtof(ch[0] - 24) * tb) * np.exp(-tb * 7), t0 + k * beat / 2)
        notes = ch + [ch[0] + 12]
        for k in range(8):
            m = notes[[0, 2, 1, 3, 2, 1, 3, 2][k]] + 12
            Lp = int(0.35 * SR)
            tp = np.arange(Lp) / SR
            add(music, 0.05 * (np.sin(2 * np.pi * mtof(m) * tp) + 0.3 * np.sin(6 * np.pi * mtof(m) * tp))
                * np.exp(-tp * 10), t0 + k * beat / 2)
        for k in range(4):
            Lk = int(0.3 * SR)
            tk = np.arange(Lk) / SR
            ph = 2 * np.pi * np.cumsum(48 + 100 * np.exp(-tk * 30)) / SR
            add(music, 0.3 * np.sin(ph) * np.exp(-tk * 11), t0 + k * beat)
            rng = np.random.default_rng(b * 10 + k)
            Lh = int(0.05 * SR)
            th = np.arange(Lh) / SR
            add(music, 0.03 * np.diff(rng.uniform(-1, 1, Lh + 1)) * np.exp(-th * 80), t0 + k * beat + beat / 2)
            if k % 2 == 1:
                Ls = int(0.18 * SR)
                ts = np.arange(Ls) / SR
                add(music, 0.07 * rng.uniform(-1, 1, Ls) * np.exp(-ts * 20), t0 + k * beat)
    music *= np.minimum(1, t / 1.0) * np.clip((TOTAL - t) / 1.5, 0, 1)
    music /= np.abs(music).max()

    rng = np.random.default_rng(3)
    # impacto inicial
    Li = int(1.2 * SR)
    ti = np.arange(Li) / SR
    ph = 2 * np.pi * np.cumsum(35 + 80 * np.exp(-ti * 8)) / SR
    add(sfx, 0.9 * np.sin(ph) * np.exp(-ti * 3), 0.05)
    for b in BOUNDS[1:-1]:
        Lw = int(0.6 * SR)
        tw = np.arange(Lw) / SR
        noise = rng.uniform(-1, 1, Lw)
        y = np.zeros(Lw)
        acc = 0.0
        cut = 0.03 + 0.3 * np.sin(np.pi * tw / 0.6) ** 2
        for j in range(Lw):
            acc += cut[j] * (noise[j] - acc)
            y[j] = acc
        add(sfx, 0.55 * y * np.sin(np.pi * tw / 0.6) ** 2, b - 0.3)
    # "ding" de los contadores
    for sc_i, dl in [(1, 1.6), (4, 3.0), (7, 1.3)]:
        Lc = int(0.7 * SR)
        tc = np.arange(Lc) / SR
        add(sfx, 0.18 * (np.sin(2 * np.pi * 1318 * tc) + 0.6 * np.sin(2 * np.pi * 1976 * tc)) * np.exp(-tc * 5),
            BOUNDS[sc_i] + dl)
    # explosión del meteorito
    Lx = int(1.0 * SR)
    tx = np.arange(Lx) / SR
    rumble = np.convolve(rng.uniform(-1, 1, Lx), np.ones(60) / 60, mode="same") * 6
    add(sfx, 0.6 * rumble * np.exp(-tx * 3.5),
        BOUNDS[6] + 4.0 + 0.9 * 1.2)

    voice, vsr = sf.read(os.path.join(VDIR, "voz.wav"))
    if voice.ndim > 1:
        voice = voice.mean(axis=1)
    vt = np.arange(len(voice)) / vsr
    voice = np.interp(np.arange(int(len(voice) * SR / vsr)) / SR, vt, voice)
    vo = np.zeros(n)
    vo[:min(n, len(voice))] = voice[:n]
    vo /= np.abs(vo).max()
    # ducking: baja la música cuando habla la voz
    env = np.convolve(np.abs(vo), np.ones(4410) / 4410, mode="same")
    duck = 1 - 0.55 * np.clip(env / 0.05, 0, 1)
    mix = 0.95 * vo + 0.32 * music * duck + 0.5 * sfx
    mix /= np.abs(mix).max() / 0.92
    pcm = (mix * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(np.stack([pcm, pcm], 1).tobytes())


# ------------------------------------------------------------------ main
def render(T):
    si = max(k for k in range(len(SCENES)) if BOUNDS[k] <= T + 1e-9)
    return si, SCENES[si](T - BOUNDS[si], BOUNDS[si + 1] - BOUNDS[si])


def main():
    apath = os.path.join(HERE, "_mix.wav")
    print("Mezclando audio…", flush=True)
    synth_audio(apath)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", apath, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nf = int(TOTAL * FPS)
    prev = None
    TR = 0.35
    for fi in range(nf):
        T = fi / FPS
        si, frame = render(T)
        lt = T - BOUNDS[si]
        if si > 0 and lt < TR:
            if prev is None:
                prev = SCENES[si - 1](BOUNDS[si] - BOUNDS[si - 1] - 1 / FPS, BOUNDS[si] - BOUNDS[si - 1])
            p = eio(lt / TR)
            # barrido diagonal con zoom del fotograma anterior
            mask = Image.new("L", (W, H), 0)
            yy = lerp(H + 600, -600, p)
            ImageDraw.Draw(mask).polygon([(0, yy + 300), (W, yy - 300), (W, H + 700), (0, H + 700)], fill=255)
            z = 1 + 0.15 * p
            pz = prev.resize((int(W * z), int(H * z)), Image.BILINEAR).crop(
                (int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
            frame = Image.composite(frame, pz, mask)
        else:
            prev = None
        draw_hud(frame, T)
        draw_captions(frame, T)
        proc.stdin.write(frame.convert("RGB").tobytes())
        if fi % 300 == 0:
            print(f"  {fi}/{nf}", flush=True)
    proc.stdin.close()
    proc.wait()
    os.remove(apath)
    print("Listo:", OUT)


if __name__ == "__main__":
    main()
