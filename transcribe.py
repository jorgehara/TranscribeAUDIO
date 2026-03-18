import whisper
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Transcribir audios con Whisper")
    parser.add_argument("files", nargs="+", help="Archivos de audio a transcribir")
    parser.add_argument("--language", default="Spanish", help="Idioma del audio (default: Spanish)")
    parser.add_argument("--model", default="base", help="Modelo Whisper a usar (default: base)")
    parser.add_argument("--save", action="store_true", help="Guardar transcripciones como archivos .txt")
    args = parser.parse_args()

    print(f"\nCargando modelo '{args.model}'...")
    model = whisper.load_model(args.model)

    for audio_path in args.files:
        if not os.path.exists(audio_path):
            print(f"\n[ERROR] Archivo no encontrado: {audio_path}")
            continue

        print(f"\nTranscribiendo: {audio_path}")
        result = model.transcribe(audio_path, language=args.language)
        text = result["text"].strip()

        print(f"\n--- {audio_path} ---")
        print(text)
        print("-" * 40)

        if args.save:
            out_path = os.path.splitext(audio_path)[0] + ".txt"
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"[Guardado] {out_path}")


if __name__ == "__main__":
    main()
