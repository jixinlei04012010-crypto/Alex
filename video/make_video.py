#!/usr/bin/env python3
"""Genera un video animado (MP4, 1920x1080, 30 fps) con curiosidades del mundo.

Todo se dibuja con Pillow y la música/efectos se sintetizan con numpy.
Requisitos: python3, pillow, numpy, ffmpeg.

Uso:  python3 make_video.py [salida.mp4]
"""
import math
import os
import random
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
SR = 44100
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "curiosidades.mp4")

FONT_BLACK = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
FONT_XBOLD = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
FONT_SEMI = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
FONT_EMOJI = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
if not os.path.exists(FONT_BLACK):
    FONT_BLACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    FONT_XBOLD = FONT_SEMI = FONT_BLACK

_font_cache = {}


def font(path, size):
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# ---------------------------------------------------------------- contenido
FACTS = [
    dict(emoji="🍯", extras=["🏺", "🐝"], colors=("#f7b733", "#fc4a1a"),
         title="La miel nunca caduca",
         text="Se ha encontrado miel en tumbas egipcias de más de 3.000 años… "
              "¡y todavía era comestible!"),
    dict(emoji="🐙", extras=["💙", "💙", "💙"], colors=("#7f53ac", "#647dee"),
         title="Los pulpos tienen 3 corazones",
         text="Dos bombean sangre a las branquias y uno al resto del cuerpo. "
              "Y su sangre es azul."),
    dict(emoji="VENUS", extras=["☀️", "⏳"], colors=("#ff9a44", "#c2185b"),
         title="En Venus, un día dura más que un año",
         text="Venus tarda 243 días en girar sobre sí mismo, pero solo 225 en "
              "dar la vuelta al Sol."),
    dict(emoji="🍌", extras=["☢️", "😮"], colors=("#a8e063", "#2f9e44"),
         title="Los plátanos son un poco radiactivos",
         text="Tienen potasio-40, un isótopo natural. Tranquilo: harían falta "
              "millones a la vez para que fuera peligroso."),
    dict(emoji="🦈", extras=["🌳", "🦕"], colors=("#00c6ff", "#0052d4"),
         title="Los tiburones son más antiguos que los árboles",
         text="Hay tiburones desde hace unos 450 millones de años; los primeros "
              "árboles llegaron hace unos 385."),
    dict(emoji="EIFFEL", extras=["🌡️", "☀️"], colors=("#ff758c", "#ff7eb3"),
         title="La Torre Eiffel crece en verano",
         text="Con el calor, el hierro se dilata y la torre puede ganar hasta "
              "15 cm de altura."),
    dict(emoji="⚡", extras=["☀️", "🔥"], colors=("#3a1c71", "#d76d77"),
         title="Un rayo está más caliente que el Sol",
         text="Un rayo alcanza unos 30.000 °C: cerca de cinco veces más que la "
              "superficie del Sol."),
    dict(emoji="🦩", extras=["🦐", "🌿"], colors=("#f953c6", "#b91d73"),
         title="Los flamencos son rosas por lo que comen",
         text="Los pigmentos de las algas y los camarones que comen tiñen sus "
              "plumas. Al nacer, son grises."),
]

INTRO_DUR = 4.5
FACT_DUR = 8.0
OUTRO_DUR = 6.0
TRANS = 0.6  # duración de la transición circular
SCENES = [("intro", INTRO_DUR, None)] + [("fact", FACT_DUR, i) for i in range(len(FACTS))] \
    + [("outro", OUTRO_DUR, None)]
TOTAL = sum(s[1] for s in SCENES)


# ---------------------------------------------------------------- utilidades
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_in_out(t):
    t = clamp(t)
    return t * t * (3 - 2 * t)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(c1, c2):
    a, b = np.array(hex2rgb(c1), float), np.array(hex2rgb(c2), float)
    yy, xx = np.mgrid[0:H, 0:W]
    t = ((xx / W) * 0.55 + (yy / H) * 0.45)[..., None]
    img = a * (1 - t) + b * t
    # viñeta suave
    d = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)[..., None]
    img *= 1 - 0.35 * d
    return Image.fromarray(img.clip(0, 255).astype(np.uint8), "RGB")


_emoji_cache = {}


def emoji_img(ch, size):
    key = (ch, size)
    if key in _emoji_cache:
        return _emoji_cache[key]
    if ch == "EIFFEL":
        im = eiffel(size)
    elif ch == "VENUS":
        im = venus(size)
    else:
        f = font(FONT_EMOJI, 109)
        base = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(base).text((80, 80), ch, font=f, embedded_color=True, anchor="mm")
        base = base.crop(base.getbbox())
        sc = size / max(base.size)
        im = base.resize((max(1, int(base.width * sc)), max(1, int(base.height * sc))),
                         Image.LANCZOS)
    _emoji_cache[key] = im
    return im


def venus(size):
    """Planeta Venus: esfera amarillo-anaranjada con bandas de nubes."""
    S = 400
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    nx, ny = (xx - S / 2) / (S / 2 - 4), (yy - S / 2) / (S / 2 - 4)
    r2 = nx ** 2 + ny ** 2
    inside = r2 <= 1
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    light = np.clip(0.5 + 0.6 * (-0.45 * nx - 0.45 * ny + 0.77 * nz), 0, 1.15)
    bands = 0.5 + 0.5 * np.sin(ny * 9 + 1.2 * np.sin(nx * 3))
    base = np.array([240, 196, 120]) * (1 - bands[..., None] * 0.25) \
        + np.array([214, 140, 70]) * bands[..., None] * 0.25
    rgb = np.clip(base * light[..., None], 0, 255)
    a = np.where(inside, 255, 0)
    im = np.dstack([rgb, a]).astype(np.uint8)
    return Image.fromarray(im, "RGBA").resize((size, size), Image.LANCZOS)


def eiffel(size):
    """Silueta sencilla de la Torre Eiffel."""
    S = 400
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    col = (74, 52, 46, 255)
    d.polygon([(40, 395), (360, 395), (255, 250), (145, 250)], fill=col)
    d.polygon([(150, 255), (250, 255), (222, 120), (178, 120)], fill=col)
    d.polygon([(180, 125), (220, 125), (203, 20), (197, 20)], fill=col)
    d.rectangle([128, 240, 272, 258], fill=col)
    d.rectangle([168, 112, 232, 126], fill=col)
    d.rectangle([197, 0, 203, 25], fill=col)
    # arco
    d.pieslice([110, 300, 290, 470], 180, 360, fill=(0, 0, 0, 0))
    d.polygon([(110, 395), (290, 395), (290, 385), (110, 385)], fill=(0, 0, 0, 0))
    # celosía
    for y in range(140, 250, 22):
        d.line([(170, y), (230, y + 18)], fill=(0, 0, 0, 0), width=3)
        d.line([(230, y), (170, y + 18)], fill=(0, 0, 0, 0), width=3)
    d.rectangle([150, 272, 250, 284], fill=(0, 0, 0, 0))
    return im.resize((size, size), Image.LANCZOS)


def wrap(text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if fnt.getlength(test) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def paste_center(base, im, cx, cy, alpha=1.0):
    if alpha < 1:
        a = im.getchannel("A").point(lambda v: int(v * alpha))
        im = im.copy()
        im.putalpha(a)
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


class Particles:
    def __init__(self, seed, n=34):
        r = random.Random(seed)
        self.p = [(r.uniform(0, W), r.uniform(0, H), r.uniform(6, 34), r.uniform(15, 60),
                   r.uniform(0, 6.28), r.uniform(25, 70)) for _ in range(n)]

    def draw(self, d, t):
        for x, y, rad, sp, ph, a in self.p:
            yy = (y - sp * t) % (H + 100) - 50
            xx = x + 25 * math.sin(t * 0.8 + ph)
            d.ellipse([xx - rad, yy - rad, xx + rad, yy + rad], fill=(255, 255, 255, int(a)))


def shadow_text(d, xy, txt, fnt, fill=(255, 255, 255), alpha=255, anchor="la", off=5):
    x, y = xy
    d.text((x + off, y + off), txt, font=fnt, fill=(0, 0, 0, int(alpha * 0.28)), anchor=anchor)
    d.text((x, y), txt, font=fnt, fill=fill + (int(alpha),), anchor=anchor)


# ---------------------------------------------------------------- escenas
BG = {}


def bg_for(key, c1, c2):
    if key not in BG:
        BG[key] = gradient(c1, c2).convert("RGBA")
    return BG[key]


PARTS = {}


def render_intro(t):
    frame = bg_for("intro", "#ff512f", "#6a11cb").copy()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    PARTS.setdefault("intro", Particles(1)).draw(d, t)
    # rayos girando
    cx, cy = W / 2, 400
    for k in range(16):
        ang = k * math.pi / 8 + t * 0.25
        p = [(cx, cy), (cx + 1600 * math.cos(ang - 0.08), cy + 1600 * math.sin(ang - 0.08)),
             (cx + 1600 * math.cos(ang + 0.08), cy + 1600 * math.sin(ang + 0.08))]
        d.polygon(p, fill=(255, 255, 255, 18))
    frame.alpha_composite(layer)

    s = ease_out_back((t - 0.2) / 0.8)
    if s > 0.01:
        em = emoji_img("🤯", max(2, int(300 * s)))
        em = em.rotate(8 * math.sin(t * 3), resample=Image.BICUBIC, expand=True)
        paste_center(frame, em, cx, cy + 10 * math.sin(t * 2.5))

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    p = ease_out_cubic((t - 0.8) / 0.7)
    f = font(FONT_BLACK, 150)
    shadow_text(d, (W / 2, 720 + 60 * (1 - p)), "¿SABÍAS QUE…?", f, alpha=255 * p, anchor="mm", off=8)
    p2 = ease_out_cubic((t - 1.5) / 0.7)
    f2 = font(FONT_SEMI, 52)
    shadow_text(d, (W / 2, 850 + 40 * (1 - p2)), "8 curiosidades que te van a volar la cabeza",
                f2, alpha=255 * p2, anchor="mm", off=4)
    frame.alpha_composite(layer)
    return frame


def render_fact(i, t):
    fct = FACTS[i]
    frame = bg_for(i, *fct["colors"]).copy()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    PARTS.setdefault(i, Particles(100 + i)).draw(d, t)

    # destello para el rayo
    if fct["emoji"] == "⚡":
        for ft in (1.2, 1.35, 4.0):
            if 0 <= t - ft < 0.12:
                d.rectangle([0, 0, W, H], fill=(255, 255, 230, 120))

    # círculo detrás del emoji
    cx, cy = 520, 500
    cs = ease_out_back((t - 0.3) / 0.7)
    r = 330 * cs
    pulse = 1 + 0.03 * math.sin(t * 4)
    if r > 1:
        d.ellipse([cx - r * pulse, cy - r * pulse, cx + r * pulse, cy + r * pulse],
                  fill=(255, 255, 255, 55))
        r2 = r * 0.82
        d.ellipse([cx - r2, cy - r2, cx + r2, cy + r2], fill=(255, 255, 255, 70))

    # panel de texto (altura según el contenido)
    px0, px1 = 950, 1840
    tx = px0 + 70
    ft = font(FONT_BLACK, 72)
    fd = font(FONT_SEMI, 42)
    tlines = wrap(fct["title"], ft, px1 - tx - 60)
    dlines = wrap(fct["text"], fd, px1 - tx - 60)
    ph = 60 + 116 + 40 + 86 * len(tlines) + 24 + 56 * len(dlines) + 50
    ptop = int(cy - ph / 2)
    pp = ease_out_cubic((t - 0.5) / 0.6)
    if pp > 0:
        off = 80 * (1 - pp)
        d.rounded_rectangle([px0 + off, ptop, px1 + off, ptop + ph], radius=48,
                            fill=(0, 0, 0, int(70 * pp)))
    frame.alpha_composite(layer)

    # emoji principal
    es = ease_out_back((t - 0.45) / 0.8)
    if es > 0.01:
        if fct["emoji"] == "EIFFEL":
            grow = 1 + 0.08 * ease_in_out((t - 3.0) / 1.2) * (0.6 + 0.4 * math.sin(t * 2))
            em = emoji_img("EIFFEL", 440)
            em = em.resize((max(2, int(440 * es)), max(2, int(440 * es * grow))), Image.LANCZOS)
            paste_center(frame, em, cx, cy + 20 - (em.height - 440 * es) / 2)
        else:
            em = emoji_img(fct["emoji"], max(2, int(380 * es)))
            ang = 6 * math.sin(t * 2.2)
            em = em.rotate(ang, resample=Image.BICUBIC, expand=True)
            paste_center(frame, em, cx, cy + 14 * math.sin(t * 2.6))

    # emojis secundarios orbitando
    ex = fct["extras"]
    for k, e in enumerate(ex):
        a = ease_out_back((t - 1.0 - 0.25 * k) / 0.6)
        if a <= 0.01:
            continue
        ang = t * 0.9 + k * 2 * math.pi / len(ex)
        rr = 310
        x = cx + rr * math.cos(ang)
        y = cy + rr * 0.75 * math.sin(ang)
        sz = max(2, int(120 * a * (0.85 + 0.15 * math.sin(ang))))
        paste_center(frame, emoji_img(e, sz), x, y)

    # etiqueta "+15 cm" para la torre
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    if fct["emoji"] == "EIFFEL":
        la = ease_out_cubic((t - 3.2) / 0.5)
        if la > 0:
            shadow_text(d, (cx + 230, 230), "+15 cm", font(FONT_BLACK, 70), alpha=255 * la, anchor="mm")
            d.line([(cx + 230, 280), (cx + 230, 380)], fill=(255, 255, 255, int(255 * la)), width=8)
            d.polygon([(cx + 210, 290), (cx + 250, 290), (cx + 230, 260)],
                      fill=(255, 255, 255, int(255 * la)))

    # insignia con número
    bs = ease_out_back((t - 0.7) / 0.5)
    if bs > 0.01:
        br = 58 * bs
        bx, by = tx + 58, ptop + 60 + 58
        d.ellipse([bx - br, by - br, bx + br, by + br], fill=(255, 255, 255, 255))
        d.text((bx, by + 2), f"#{i + 1}", font=font(FONT_BLACK, int(max(8, 52 * bs))),
               fill=hex2rgb(fct["colors"][1]) + (255,), anchor="mm")
        lab = ease_out_cubic((t - 0.9) / 0.4)
        d.text((bx + 85, by), "CURIOSIDAD", font=font(FONT_XBOLD, 34),
               fill=(255, 255, 255, int(220 * lab)), anchor="lm")

    # título palabra a palabra
    y = ptop + 60 + 116 + 40
    widx = 0
    for line in tlines:
        x = tx
        for w in line.split():
            wa = ease_out_cubic((t - 1.1 - 0.09 * widx) / 0.35)
            if wa > 0:
                shadow_text(d, (x, y + 30 * (1 - wa)), w, ft, alpha=255 * wa)
            x += ft.getlength(w + " ")
            widx += 1
        y += 86

    # texto descriptivo
    ta = ease_out_cubic((t - 2.0 - 0.09 * widx * 0.5) / 0.6)
    if ta > 0:
        y += 24
        for line in dlines:
            d.text((tx, y + 20 * (1 - ta)), line, font=fd, fill=(255, 255, 255, int(235 * ta)))
            y += 56

    # barra de progreso inferior
    n = len(FACTS)
    gap = 54
    x0 = W / 2 - gap * (n - 1) / 2
    for k in range(n):
        x = x0 + gap * k
        if k == i:
            d.rounded_rectangle([x - 22, 950, x + 22, 970], radius=10, fill=(255, 255, 255, 255))
        else:
            rr = 9
            d.ellipse([x - rr, 960 - rr, x + rr, 960 + rr],
                      fill=(255, 255, 255, 200 if k < i else 90))
    # barra de tiempo de la escena
    d.rectangle([0, H - 10, W * clamp(t / FACT_DUR), H], fill=(255, 255, 255, 160))
    frame.alpha_composite(layer)
    return frame


def render_outro(t):
    frame = bg_for("outro", "#11998e", "#38ef7d").copy()
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    PARTS.setdefault("outro", Particles(999, 50)).draw(d, t)
    frame.alpha_composite(layer)

    cx = W / 2
    for k, e in enumerate(["🍯", "🐙", "VENUS", "🍌", "🦈", "⚡", "🦩"]):
        a = ease_out_back((t - 0.2 - 0.12 * k) / 0.5)
        if a > 0.01:
            x = cx + (k - 3) * 190
            y = 300 + 20 * math.sin(t * 3 + k)
            paste_center(frame, emoji_img(e, max(2, int(130 * a))), x, y)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer, "RGBA")
    p = ease_out_cubic((t - 1.0) / 0.7)
    shadow_text(d, (cx, 560 + 50 * (1 - p)), "¿Cuál te sorprendió más?", font(FONT_BLACK, 110),
                alpha=255 * p, anchor="mm", off=7)
    p2 = ease_out_cubic((t - 1.8) / 0.7)
    shadow_text(d, (cx, 700 + 40 * (1 - p2)), "Compártelo con alguien igual de curioso que tú 👇"
                .replace(" 👇", ""), font(FONT_SEMI, 54), alpha=255 * p2, anchor="mm", off=4)
    p3 = ease_out_back((t - 2.6) / 0.6)
    if p3 > 0.01:
        bw, bh = 560 * p3, 110 * p3
        by = 860
        d.rounded_rectangle([cx - bw / 2, by - bh / 2, cx + bw / 2, by + bh / 2], radius=55 * p3,
                            fill=(255, 255, 255, 255))
        d.text((cx, by + 2), "¡Sigue aprendiendo!", font=font(FONT_BLACK, max(8, int(50 * p3))),
               fill=(17, 153, 142, 255), anchor="mm")
    # fundido a negro final
    fo = clamp((t - (OUTRO_DUR - 0.8)) / 0.8)
    if fo > 0:
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, int(255 * fo)))
    frame.alpha_composite(layer)
    return frame


def render_scene(kind, idx, t):
    if kind == "intro":
        return render_intro(t)
    if kind == "fact":
        return render_fact(idx, t)
    return render_outro(t)


# ---------------------------------------------------------------- audio
def synth_audio(path):
    n = int(TOTAL * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    bpm = 108
    beat = 60 / bpm
    prog = [[60, 64, 67], [55, 59, 62, 67], [57, 60, 64], [53, 57, 60, 65]]  # C G Am F

    def mtof(m):
        return 440 * 2 ** ((m - 69) / 12)

    def add(sig, start):
        s = int(start * SR)
        if s >= n:
            return
        e = min(n, s + len(sig))
        out[s:e] += sig[:e - s]

    bar = 4 * beat
    nbars = int(TOTAL / bar) + 1
    for b in range(nbars):
        chord = prog[b % 4]
        t0 = b * bar
        # pad
        L = int(bar * SR)
        tt = np.arange(L) / SR
        env = np.minimum(1, tt / 0.3) * np.minimum(1, (bar - tt) / 0.3)
        pad = sum(np.sin(2 * np.pi * mtof(m) * tt) + 0.3 * np.sin(4 * np.pi * mtof(m) * tt)
                  for m in chord)
        add(0.035 * pad * env, t0)
        # bajo
        for k in range(4):
            Lb = int(beat * SR)
            tb = np.arange(Lb) / SR
            f = mtof(chord[0] - 24)
            add(0.16 * np.sin(2 * np.pi * f * tb) * np.exp(-tb * 4), t0 + k * beat)
        # arpegio
        notes = chord + [chord[0] + 12]
        for k in range(8):
            m = notes[[0, 1, 2, 3, 2, 1, 2, 3][k] % len(notes)] + 12
            Lp = int(0.4 * SR)
            tp = np.arange(Lp) / SR
            f = mtof(m)
            pl = (np.sin(2 * np.pi * f * tp) + 0.4 * np.sin(4 * np.pi * f * tp)) * np.exp(-tp * 9)
            add(0.07 * pl, t0 + k * beat / 2)
        # batería
        for k in range(4):
            if k % 2 == 0:
                Lk = int(0.3 * SR)
                tk = np.arange(Lk) / SR
                ph = 2 * np.pi * np.cumsum(50 + 90 * np.exp(-tk * 30)) / SR
                add(0.35 * np.sin(ph) * np.exp(-tk * 12), t0 + k * beat)
            else:
                Ls = int(0.18 * SR)
                ts = np.arange(Ls) / SR
                rng = np.random.default_rng(b * 10 + k)
                add(0.09 * rng.uniform(-1, 1, Ls) * np.exp(-ts * 22), t0 + k * beat)
            Lh = int(0.05 * SR)
            th = np.arange(Lh) / SR
            rng = np.random.default_rng(b * 100 + k)
            hh = np.diff(rng.uniform(-1, 1, Lh + 1))
            add(0.035 * hh * np.exp(-th * 80), t0 + k * beat + beat / 2)

    # fade in/out de la música
    out *= np.minimum(1, t / 1.5) * np.clip((TOTAL - t) / 2.0, 0, 1)

    # efectos: whoosh en cada transición y "pop" al aparecer el emoji
    rng = np.random.default_rng(7)
    start = 0.0
    for kind, dur, idx in SCENES:
        if start > 0:
            Lw = int(0.7 * SR)
            tw = np.arange(Lw) / SR
            noise = rng.uniform(-1, 1, Lw)
            # filtro paso bajo variable (simple, de un polo)
            y = np.zeros(Lw)
            acc = 0.0
            cut = 0.02 + 0.25 * np.sin(np.pi * tw / 0.7) ** 2
            for j in range(Lw):
                acc += cut[j] * (noise[j] - acc)
                y[j] = acc
            add(0.5 * y * np.sin(np.pi * tw / 0.7) ** 2, start - 0.35)
        if kind == "fact":
            Lp = int(0.15 * SR)
            tp = np.arange(Lp) / SR
            ph = 2 * np.pi * np.cumsum(300 + 900 * tp / 0.15) / SR
            add(0.22 * np.sin(ph) * np.exp(-tp * 25), start + 0.5)
            # campanita al aparecer la insignia
            Lc = int(0.6 * SR)
            tc = np.arange(Lc) / SR
            add(0.08 * (np.sin(2 * np.pi * 1568 * tc) + 0.5 * np.sin(2 * np.pi * 2349 * tc))
                * np.exp(-tc * 6), start + 0.75)
        start += dur

    out = out / max(1e-9, np.abs(out).max()) * 0.85
    pcm = (out * 32767).astype(np.int16)
    stereo = np.stack([pcm, pcm], axis=1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(stereo.tobytes())


# ---------------------------------------------------------------- main
def main():
    audio_path = os.path.join(HERE, "_audio.wav")
    print("Sintetizando audio…", flush=True)
    synth_audio(audio_path)

    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", audio_path,
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    total_frames = int(TOTAL * FPS)
    starts = []
    acc = 0.0
    for s in SCENES:
        starts.append(acc)
        acc += s[1]

    prev_last = None
    for fi in range(total_frames):
        T = fi / FPS
        si = max(k for k in range(len(SCENES)) if starts[k] <= T + 1e-9)
        kind, dur, idx = SCENES[si]
        lt = T - starts[si]
        frame = render_scene(kind, idx, lt)
        if si > 0 and lt < TRANS:
            if prev_last is None:
                pk, pd, pi = SCENES[si - 1]
                prev_last = render_scene(pk, pi, pd - 1 / FPS).convert("RGB")
            p = ease_in_out(lt / TRANS)
            mask = Image.new("L", (W, H), 0)
            rad = p * math.hypot(W, H) / 2 * 1.05
            ImageDraw.Draw(mask).ellipse([W / 2 - rad, H / 2 - rad, W / 2 + rad, H / 2 + rad], fill=255)
            frame = Image.composite(frame.convert("RGB"), prev_last, mask)
        else:
            prev_last = None
            frame = frame.convert("RGB")
        proc.stdin.write(frame.tobytes())
        if fi % 150 == 0:
            print(f"  frame {fi}/{total_frames}", flush=True)

    proc.stdin.close()
    proc.wait()
    os.remove(audio_path)
    print("Listo:", OUT)


if __name__ == "__main__":
    main()
