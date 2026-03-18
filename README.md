# Whisper Transcriber

Transcripción local de audios usando OpenAI Whisper. Sin APIs externas, sin costo por uso.

## Requisitos previos

- Python 3.9+
- ffmpeg instalado en el sistema:
  - **Windows:** descargar desde https://ffmpeg.org/download.html y agregar al PATH
  - **macOS:** `brew install ffmpeg`
  - **Ubuntu/Debian:** `sudo apt install ffmpeg`

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Transcribir un archivo
python transcribe.py audio1.mp3

# Transcribir múltiples archivos
python transcribe.py audio1.mp3 audio2.mp3 audio3.mp3

# Especificar idioma
python transcribe.py audio1.mp3 --language Spanish

# Usar modelo más preciso
python transcribe.py audio1.mp3 --model small --language Spanish

# Guardar resultados como .txt
python transcribe.py audio1.mp3 audio2.mp3 --language Spanish --save
```

## Opciones

| Opción | Default | Descripción |
|--------|---------|-------------|
| `--language` | Spanish | Idioma del audio |
| `--model` | base | Modelo Whisper a usar |
| `--save` | false | Guarda cada transcripción en un `.txt` |

## Modelos disponibles

| Modelo | Velocidad | Precisión | VRAM aprox |
|--------|-----------|-----------|------------|
| tiny | Muy rápido | Básica | ~1 GB |
| base | Rápido | Buena | ~1 GB |
| small | Moderado | Mejor | ~2 GB |
| medium | Lento | Alta | ~5 GB |
| large | Muy lento | Máxima | ~10 GB |

Recomendado: `base` para pruebas, `small` para producción en español.
