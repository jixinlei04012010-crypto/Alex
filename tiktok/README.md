# TikTok — Los tiburones son más antiguos que los árboles

`tiburones_tiktok.mp4`: vertical 1080×1920, 30 fps, ~64 s, con voz en español, subtítulos animados y música.

Regenerarlo:

```bash
pip install kokoro-onnx soundfile pillow numpy
# modelo de voz (Kokoro, licencia Apache 2.0)
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
python3 tiktok/narracion.py <carpeta_modelo> <carpeta_salida>   # voz.wav + tiempos.json
python3 tiktok/make_tiktok.py <carpeta_salida>
```

El guion está en `FRASES` (narracion.py). La voz es `em_alex`; también hay `ef_dora` (femenina) y `em_santa`.
