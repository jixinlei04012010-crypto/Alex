"""Genera la narración (voz Kokoro en español) frase a frase y guarda los tiempos."""
import json, os, sys
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

MODEL_DIR = sys.argv[1]
OUT_DIR = sys.argv[2]
VOICE = "em_alex"
SPEED = 1.0
GAP = 0.45  # silencio entre frases (s)

FRASES = [
    "¿Sabías que los tiburones son más antiguos que los árboles? Sí, has oído bien.",
    "Los primeros tiburones ya nadaban en los océanos hace unos cuatrocientos cincuenta millones de años.",
    "En aquella época, la tierra firme era casi un desierto. No había bosques, ni flores, ni dinosaurios.",
    "Las únicas plantas eran pequeños musgos pegados a las rocas, de apenas unos centímetros.",
    "Los primeros árboles de verdad no aparecieron hasta hace unos trescientos ochenta y cinco millones de años.",
    "O sea, los tiburones llevaban unos sesenta y cinco millones de años en el mar cuando creció el primer bosque.",
    "Y desde entonces, han sobrevivido a las cinco grandes extinciones masivas. Incluida la que acabó con los dinosaurios.",
    "Hoy existen más de quinientas especies, desde el diminuto tiburón linterna hasta el gigantesco tiburón ballena.",
    "Así que la próxima vez que veas un tiburón, recuerda: estás mirando a uno de los supervivientes más antiguos del planeta.",
    "Síguenos para más curiosidades que te volarán la cabeza.",
]

k = Kokoro(os.path.join(MODEL_DIR, "kokoro-v1.0.onnx"), os.path.join(MODEL_DIR, "voices-v1.0.bin"))
parts, timings, t = [], [], 0.6
sr = 24000
parts.append(np.zeros(int(0.6 * sr), np.float32))
for f in FRASES:
    a, sr = k.create(f, voice=VOICE, speed=SPEED, lang="es")
    # recorta silencios al principio/fin
    nz = np.where(np.abs(a) > 0.01)[0]
    a = a[max(0, nz[0] - 600): nz[-1] + 1200]
    d = len(a) / sr
    timings.append({"text": f, "start": round(t, 3), "end": round(t + d, 3)})
    parts += [a, np.zeros(int(GAP * sr), np.float32)]
    t += d + GAP
voice = np.concatenate(parts)
sf.write(os.path.join(OUT_DIR, "voz.wav"), voice, sr)
json.dump({"sr": sr, "total": len(voice) / sr, "frases": timings},
          open(os.path.join(OUT_DIR, "tiempos.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(timings, ensure_ascii=False, indent=1), len(voice) / sr)
