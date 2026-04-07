import whisper
import argparse
import os
import subprocess

AUDIOS_DIR = "audios"
MP4_DIR = "mp4"
MP3_DIR = "mp3"
MP3_INPUT_DIR = "mp3-input"
OUTPUT_DIR = "transcripciones"


def convert_to_mp3(input_path: str, output_path: str) -> str:
    """Convierte cualquier archivo de audio/video a MP3 usando FFmpeg. Retorna el path del MP3."""
    subprocess.run(
        ["ffmpeg", "-i", input_path, "-codec:a", "libmp3lame", "-qscale:a", "2", output_path, "-y"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_path


def transcribe_audio(model, audio_path: str, language: str) -> str:
    """Transcribe un archivo de audio y retorna el texto. Sin side effects."""
    result = model.transcribe(audio_path, language=language)
    return result["text"].strip()


def save_transcription(text: str, source_filename: str) -> str:
    """Guarda la transcripción en OUTPUT_DIR. Retorna el path del archivo guardado."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    txt_filename = os.path.splitext(source_filename)[0] + ".txt"
    out_path = os.path.join(OUTPUT_DIR, txt_filename)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path


def process_ogg_files(model, language: str, filenames: list = None):
    """Procesa archivos .ogg desde audios/. Si filenames=None, procesa todos."""
    if not os.path.exists(AUDIOS_DIR):
        print(f"[INFO] No existe la carpeta '{AUDIOS_DIR}', omitiendo.")
        return

    files = filenames or [f for f in os.listdir(AUDIOS_DIR) if f.lower().endswith(".ogg")]
    if not files:
        print(f"[INFO] No hay archivos .ogg en '{AUDIOS_DIR}'.")
        return

    print(f"\n[OGG] Archivos a procesar: {len(files)}")
    for filename in files:
        audio_path = os.path.join(AUDIOS_DIR, filename)
        mp3_path = os.path.splitext(audio_path)[0] + ".mp3"

        print(f"[Convirtiendo] {filename} → MP3...")
        convert_to_mp3(audio_path, mp3_path)

        print(f"[Transcribiendo] {filename}...")
        text = transcribe_audio(model, mp3_path, language)
        out_path = save_transcription(text, filename)
        os.remove(mp3_path)

        print(f"\n--- {filename} ---\n{text}\n{'-' * 40}")
        print(f"[Guardado] {out_path}\n")


def process_mp4_files(model, language: str, filenames: list = None):
    """Convierte archivos .mp4 desde mp4/ a mp3/ y los transcribe."""
    if not os.path.exists(MP4_DIR):
        print(f"[INFO] No existe la carpeta '{MP4_DIR}', omitiendo.")
        return

    os.makedirs(MP3_DIR, exist_ok=True)

    files = filenames or [f for f in os.listdir(MP4_DIR) if f.lower().endswith(".mp4")]
    if not files:
        print(f"[INFO] No hay archivos .mp4 en '{MP4_DIR}'.")
        return

    print(f"\n[MP4] Archivos a procesar: {len(files)}")
    for filename in files:
        mp4_path = os.path.join(MP4_DIR, filename)
        mp3_filename = os.path.splitext(filename)[0] + ".mp3"
        mp3_path = os.path.join(MP3_DIR, mp3_filename)

        print(f"[Convirtiendo] {filename} → {MP3_DIR}/{mp3_filename}...")
        convert_to_mp3(mp4_path, mp3_path)

        print(f"[Transcribiendo] {filename}...")
        text = transcribe_audio(model, mp3_path, language)
        out_path = save_transcription(text, filename)

        print(f"\n--- {filename} ---\n{text}\n{'-' * 40}")
        print(f"[Guardado] {out_path}\n")


def process_mp3_input_files(model, language: str, filenames: list = None):
    """Transcribe archivos .mp3 desde mp3-input/ directamente, sin conversión."""
    if not os.path.exists(MP3_INPUT_DIR):
        print(f"[INFO] No existe la carpeta '{MP3_INPUT_DIR}', omitiendo.")
        return

    files = filenames or [f for f in os.listdir(MP3_INPUT_DIR) if f.lower().endswith(".mp3")]
    if not files:
        print(f"[INFO] No hay archivos .mp3 en '{MP3_INPUT_DIR}'.")
        return

    print(f"\n[MP3] Archivos a procesar: {len(files)}")
    for filename in files:
        audio_path = os.path.join(MP3_INPUT_DIR, filename)

        print(f"[Transcribiendo] {filename}...")
        text = transcribe_audio(model, audio_path, language)
        out_path = save_transcription(text, filename)

        print(f"\n--- {filename} ---\n{text}\n{'-' * 40}")
        print(f"[Guardado] {out_path}\n")


def main():
    parser = argparse.ArgumentParser(description="Transcribir audios con Whisper")
    parser.add_argument("--language", default="Spanish", help="Idioma del audio (default: Spanish)")
    parser.add_argument("--model", default="base", help="Modelo Whisper a usar (default: base)")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"\nCargando modelo '{args.model}'...")
    model = whisper.load_model(args.model)

    process_ogg_files(model, args.language)
    process_mp4_files(model, args.language)


if __name__ == "__main__":
    main()
