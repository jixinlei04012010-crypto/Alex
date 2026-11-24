"""Genera la narración en español frase a frase (voz Piper) y guarda los tiempos.

Uso: python3 narracion.py <modelo.onnx> <carpeta_salida> [carpeta_whisper]
Con la carpeta de Whisper (sherpa-onnx-whisper-small), genera varias tomas de cada
frase y se queda con la que mejor se entiende.
El modelo usado es es_ES-sharvard-medium (locutor 0, voz masculina grave).
"""
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
from piper import PiperVoice, SynthesisConfig

MODEL = sys.argv[1]
OUT_DIR = sys.argv[2]
WHISPER = sys.argv[3] if len(sys.argv) > 3 else None
SPEAKER = 0          # 0 = voz masculina
LENGTH = 0.9         # <1 = habla más rápido
GAP = 0.28           # silencio entre frases (s)

FRASES = [
    "¿Sabías que los tiburones son más antiguos que los árboles? Sí, has oído bien.",
    "Los primeros tiburones ya nadaban en los océanos hace unos cuatrocientos cincuenta millones de años.",
    "En aquella época, la tierra firme era casi un desierto. No había bosques, ni flores, ni dinosaurios.",
    "Las únicas plantas eran pequeños musgos, pegados a las rocas, de apenas unos centímetros.",
    "Los primeros árboles de verdad no aparecieron hasta hace unos trescientos ochenta y cinco millones de años.",
    "O sea, los tiburones llevaban unos sesenta y cinco millones de años en el mar cuando creció el primer bosque.",
    "Y desde entonces, han sobrevivido a las cinco grandes extinciones masivas. Incluida la que acabó con los dinosaurios.",
    "Hoy existen más de quinientas especies, desde el diminuto tiburón linterna hasta el gigantesco tiburón ballena.",
    "Así que la próxima vez que veas un tiburón, recuerda: estás mirando a uno de los supervivientes más antiguos del planeta.",
    "Dale a seguir para más curiosidades que te volarán la cabeza.",
]

voice = PiperVoice.load(MODEL)
cfg = SynthesisConfig(speaker_id=SPEAKER, length_scale=LENGTH, noise_scale=0.6, noise_w_scale=0.8)
sr = voice.config.sample_rate

rec = None
if WHISPER:
    import difflib
    import re
    import unicodedata
    import sherpa_onnx
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=os.path.join(WHISPER, "small-encoder.int8.onnx"),
        decoder=os.path.join(WHISPER, "small-decoder.int8.onnx"),
        tokens=os.path.join(WHISPER, "small-tokens.txt"), language="es", num_threads=4)

    def norm(x):
        x = unicodedata.normalize("NFD", x.lower())
        x = "".join(c for c in x if unicodedata.category(c) != "Mn")
        return re.sub(r"[^a-z ]", " ", x).split()

    NUM = {"450": "cuatrocientos cincuenta", "385": "trescientos ochenta y cinco", "380": "trescientos ochenta",
           "65": "sesenta y cinco", "60": "sesenta", "500": "quinientas", "5": "cinco"}

    def score(a, ref):
        st = rec.create_stream()
        st.accept_waveform(sr, a)
        rec.decode_stream(st)
        hyp = re.sub(r"\d+", lambda m: " " + NUM.get(m.group(), m.group()) + " ", st.result.text)
        r, h = norm(ref), norm(hyp)
        sm = difflib.SequenceMatcher(None, r, h)
        return sum(b.size for b in sm.get_matching_blocks()) / len(r), st.result.text


def take(f):
    if rec is None:
        return np.concatenate([c.audio_float_array for c in voice.synthesize(f, cfg)])
    best = None
    for L in (LENGTH, LENGTH, LENGTH + 0.05, LENGTH + 0.05, LENGTH + 0.1, LENGTH + 0.1):
        c2 = SynthesisConfig(speaker_id=SPEAKER, length_scale=L, noise_scale=0.6, noise_w_scale=0.8)
        a = np.concatenate([c.audio_float_array for c in voice.synthesize(f, c2)])
        sc, txt = score(a, f)
        if best is None or sc > best[0] + 1e-9:
            best = (sc, a, txt)
        if sc >= 0.999:
            break
    print(f"  {best[0]:.2f} | {best[2]}")
    return best[1]


parts, timings, t = [np.zeros(int(0.5 * sr), np.float32)], [], 0.5
for f in FRASES:
    a = take(f)
    nz = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, nz[0] - 300): nz[-1] + 900]
    d = len(a) / sr
    timings.append({"text": f, "start": round(t, 3), "end": round(t + d, 3)})
    parts += [a, np.zeros(int(GAP * sr), np.float32)]
    t += d + GAP

raw = os.path.join(OUT_DIR, "_voz_raw.wav")
sf.write(raw, np.concatenate(parts), sr)
# tratamiento de locutor: graves con cuerpo, presencia, compresión y volumen uniforme
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw, "-af",
                "highpass=f=70,equalizer=f=140:t=q:w=1:g=3,equalizer=f=3200:t=q:w=1.5:g=2.5,"
                "acompressor=threshold=-20dB:ratio=3:attack=5:release=90:makeup=2,"
                "loudnorm=I=-16:TP=-1.5:LRA=7",
                "-ar", "44100", "-ac", "1", os.path.join(OUT_DIR, "voz.wav")], check=True)
os.remove(raw)
total = t
json.dump({"sr": 44100, "total": total, "frases": timings},
          open(os.path.join(OUT_DIR, "tiempos.json"), "w"), ensure_ascii=False, indent=1)
print(f"Narración: {total:.1f} s")
