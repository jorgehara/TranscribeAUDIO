import whisper
import argparse
import os
import subprocess

AUDIOS_DIR = "audios"
OUTPUT_DIR = "transcripciones"


def convert_to_mp3(input_path: str) -> str:
    """Convierte un archivo de audio a MP3 usando FFmpeg. Retorna el path del MP3."""
    output_path = os.path.splitext(input_path)[0] + ".mp3"
    subprocess.run(
        ["ffmpeg", "-i", input_path, "-codec:a", "libmp3lame", "-qscale:a", "2", output_path, "-y"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Transcribir audios con Whisper")
    parser.add_argument("--language", default="Spanish", help="Idioma del audio (default: Spanish)")
    parser.add_argument("--model", default="base", help="Modelo Whisper a usar (default: base)")
    args = parser.parse_args()

    if not os.path.exists(AUDIOS_DIR):
        print(f"[ERROR] No existe la carpeta '{AUDIOS_DIR}'. Creala y poné los .ogg ahí.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    ogg_files = [f for f in os.listdir(AUDIOS_DIR) if f.lower().endswith(".ogg")]

    if not ogg_files:
        print(f"[INFO] No hay archivos .ogg en '{AUDIOS_DIR}'.")
        return

    print(f"\nCargando modelo '{args.model}'...")
    model = whisper.load_model(args.model)
    print(f"Archivos encontrados: {len(ogg_files)}\n")

    for filename in ogg_files:
        audio_path = os.path.join(AUDIOS_DIR, filename)

        print(f"[Convirtiendo] {filename} → MP3...")
        mp3_path = convert_to_mp3(audio_path)

        print(f"[Transcribiendo] {filename}...")
        result = model.transcribe(mp3_path, language=args.language)
        text = result["text"].strip()

        print(f"\n--- {filename} ---")
        print(text)
        print("-" * 40)

        txt_filename = os.path.splitext(filename)[0] + ".txt"
        out_path = os.path.join(OUTPUT_DIR, txt_filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[Guardado] {out_path}\n")

        os.remove(mp3_path)


if __name__ == "__main__":
    main()
