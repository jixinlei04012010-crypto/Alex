# TikTok — Los tiburones son más antiguos que los árboles

`tiburones_tiktok.mp4`: vertical 1080×1920, 30 fps, ~60 s, con voz en español, subtítulos animados y música.

Voz: Piper `es_ES-sharvard-medium`, locutor 0 (masculina, grave), con ecualización y compresión de locutor.
De cada frase se generan varias tomas y se elige la que Whisper entiende mejor.

Regenerarlo:

```bash
pip install piper-tts sherpa-onnx soundfile pillow numpy
R=https://github.com/k2-fsa/sherpa-onnx/releases/download
curl -LO $R/tts-models/vits-piper-es_ES-sharvard-medium.tar.bz2 && tar xjf vits-piper-es_ES-sharvard-medium.tar.bz2
curl -LO $R/asr-models/sherpa-onnx-whisper-small.tar.bz2 && tar xjf sherpa-onnx-whisper-small.tar.bz2   # opcional
python3 tiktok/narracion.py vits-piper-es_ES-sharvard-medium/es_ES-sharvard-medium.onnx salida/ sherpa-onnx-whisper-small
python3 tiktok/make_tiktok.py salida/
```

El guion está en `FRASES` (narracion.py).
