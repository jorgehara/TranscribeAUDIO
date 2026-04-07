import os
import sys
import subprocess

import questionary
import whisper
from questionary import Style
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from transcribe import (
    AUDIOS_DIR,
    MP3_DIR,
    MP3_INPUT_DIR,
    MP4_DIR,
    OUTPUT_DIR,
    convert_to_mp3,
    save_transcription,
    transcribe_audio,
)

console = Console()


def is_windows_console():
    """Check if running in a proper Windows console."""
    try:
        import prompt_toolkit.output.win32
        return True
    except Exception:
        return False


def check_questionary_compatibility():
    """Check if questionary can run in current environment."""
    try:
        questionary.select("Test", choices=[questionary.Choice("test", value="test")]).ask()
        return True
    except (InvalidGeometry, Exception) as e:
        return False


def fallback_mode_interactive(ogg_files, mp4_files, mp3_files):
    """Fallback when TUI doesn't work - use command line arguments."""
    import argparse
    
    parser = argparse.ArgumentParser(description="TranscribeAUDIO - Modo fallback")
    parser.add_argument("--mode", choices=["ogg", "mp3", "mp4", "all", "auto"], default="auto",
                        help="Modo de procesamiento: ogg, mp3, mp4, all, o auto (detecta)")
    parser.add_argument("--model", default="base", 
                        help="Modelo Whisper: tiny, base, small, medium, large")
    parser.add_argument("--language", default="Spanish",
                        help="Idioma: Spanish, English, Portuguese, French, o 'auto'")
    parser.add_argument("--files", nargs="*", 
                        help="Archivos específicos a procesar (deja vacío para procesar todos)")
    
    args = parser.parse_args()
    
    # Auto mode: detect what to process
    selected_ogg = ogg_files
    selected_mp4 = mp4_files
    selected_mp3 = mp3_files
    
    if args.mode == "ogg":
        selected_ogg = [f for f in ogg_files if args.files is None or f in args.files]
        selected_mp4 = []
        selected_mp3 = []
    elif args.mode == "mp3":
        selected_ogg = []
        selected_mp4 = []
        selected_mp3 = [f for f in mp3_files if args.files is None or f in args.files]
    elif args.mode == "mp4":
        selected_ogg = []
        selected_mp4 = [f for f in mp4_files if args.files is None or f in args.files]
        selected_mp3 = []
    elif args.mode == "all":
        pass  # Use all files
    elif args.mode == "auto":
        # Process what exists
        if not ogg_files and not mp3_files and not mp4_files:
            console.print("[yellow]No hay archivos para procesar.[/yellow]")
            return
    
    return selected_ogg, selected_mp4, selected_mp3, args.model, args.language

CUSTOM_STYLE = Style([
    ("qmark",       "fg:#00d7ff bold"),
    ("question",    "bold"),
    ("answer",      "fg:#00ff88 bold"),
    ("pointer",     "fg:#00d7ff bold"),
    ("highlighted", "fg:#00d7ff bold"),
    ("selected",    "fg:#00ff88"),
    ("separator",   "fg:#444444"),
    ("instruction", "fg:#888888 italic"),
    ("disabled",    "fg:#666666 italic"),
])

WHISPER_MODELS = [
    questionary.Choice("tiny   — ultra rápido, menor precisión",          value="tiny"),
    questionary.Choice("base   — rápido y preciso  [recomendado]",        value="base"),
    questionary.Choice("small  — más preciso, más lento",                 value="small"),
    questionary.Choice("medium — muy preciso, requiere más RAM",          value="medium"),
    questionary.Choice("large  — máxima precisión",                       value="large"),
]

LANGUAGES = [
    questionary.Choice("Español",      value="Spanish"),
    questionary.Choice("English",      value="English"),
    questionary.Choice("Portugués",    value="Portuguese"),
    questionary.Choice("Francés",      value="French"),
    questionary.Choice("Auto-detectar", value=None),
]


# ─────────────────────────── helpers ────────────────────────────

def abort(msg: str = "Cancelado."):
    console.print(f"\n[dim]{msg}[/dim]")
    sys.exit(0)


def ask(fn, *args, **kwargs):
    """Wrapper para abortar limpiamente si el usuario presiona Ctrl+C."""
    result = fn(*args, **kwargs).ask()
    if result is None:
        abort()
    return result


def scan_files(directory: str, extension: str) -> list[str]:
    if not os.path.exists(directory):
        return []
    return sorted(f for f in os.listdir(directory) if f.lower().endswith(extension))


def print_banner():
    title = Text("TranscribeAUDIO", style="bold cyan")
    subtitle = Text("  Whisper + FFmpeg · TUI", style="dim")
    console.print(Panel(title + subtitle, border_style="cyan", padding=(0, 2)))
    console.print()


def print_file_summary(ogg_files: list, mp4_files: list, mp3_files: list):
    table = Table(show_header=True, header_style="bold cyan", border_style="dim", box=None)
    table.add_column("Carpeta",   style="dim", min_width=24)
    table.add_column("Archivos",  justify="right")
    table.add_column("Estado",    justify="left")

    def status(files): return "[green]listo[/green]" if files else "[yellow]vacío[/yellow]"

    table.add_row("audios/    (.ogg)", str(len(ogg_files)), status(ogg_files))
    table.add_row("mp4/       (.mp4)", str(len(mp4_files)), status(mp4_files))
    table.add_row("mp3-input/ (.mp3)", str(len(mp3_files)), status(mp3_files))

    console.print(table)
    console.print()


# ─────────────────────────── selección ──────────────────────────

def select_mode(has_ogg: bool, has_mp4: bool, has_mp3: bool) -> str:
    choices = []
    if has_ogg:
        choices.append(questionary.Choice("Transcribir archivos OGG",              value="ogg"))
    if has_mp3:
        choices.append(questionary.Choice("Transcribir archivos MP3",              value="mp3"))
    if has_mp4:
        choices.append(questionary.Choice("Convertir MP4 → MP3 y transcribir",    value="mp4"))
    if sum([has_ogg, has_mp3, has_mp4]) > 1:
        choices.append(questionary.Choice("Procesar todo",                         value="all"))
    choices.append(questionary.Choice("Salir",                                     value="exit"))

    return ask(questionary.select, "¿Qué querés hacer?", choices=choices, style=CUSTOM_STYLE)


def select_files(files: list, label: str) -> list[str]:
    if not files:
        console.print(f"[yellow]No hay archivos {label} disponibles.[/yellow]\n")
        return []

    selected = ask(
        questionary.checkbox,
        f"Seleccioná los archivos {label}  [espacio para marcar, enter para confirmar]:",
        choices=files,
        style=CUSTOM_STYLE,
    )
    console.print()
    return selected


def select_model() -> str:
    return ask(
        questionary.select,
        "¿Qué modelo Whisper querés usar?",
        choices=WHISPER_MODELS,
        default=WHISPER_MODELS[1],
        style=CUSTOM_STYLE,
    )


def select_language() -> str | None:
    return ask(
        questionary.select,
        "¿En qué idioma están los audios?",
        choices=LANGUAGES,
        style=CUSTOM_STYLE,
    )


# ─────────────────────────── pipeline ───────────────────────────

def run_pipeline(ogg_files: list, mp4_files: list, mp3_files: list, model_name: str, language: str | None):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(MP3_DIR, exist_ok=True)

    total = len(ogg_files) + len(mp4_files) + len(mp3_files)

    console.print(f"\n[bold]Cargando modelo [cyan]{model_name}[/cyan]...[/bold]")
    model = whisper.load_model(model_name)
    console.print("[green]Modelo listo.[/green]\n")

    results: list[tuple[str, str]] = []  # (filename, out_path)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[cyan]{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("Iniciando...", total=total)

        for filename in ogg_files:
            audio_path = os.path.join(AUDIOS_DIR, filename)
            mp3_path   = os.path.splitext(audio_path)[0] + ".mp3"

            progress.update(task, description=f"[yellow]Convirtiendo[/yellow]  {filename}")
            convert_to_mp3(audio_path, mp3_path)

            progress.update(task, description=f"[cyan]Transcribiendo[/cyan] {filename}")
            text     = transcribe_audio(model, mp3_path, language)
            out_path = save_transcription(text, filename)
            os.remove(mp3_path)

            results.append((filename, out_path))
            progress.advance(task)

        for filename in mp3_files:
            audio_path = os.path.join(MP3_INPUT_DIR, filename)

            progress.update(task, description=f"[cyan]Transcribiendo[/cyan] {filename}")
            text     = transcribe_audio(model, audio_path, language)
            out_path = save_transcription(text, filename)

            results.append((filename, out_path))
            progress.advance(task)

        for filename in mp4_files:
            mp4_path     = os.path.join(MP4_DIR, filename)
            mp3_filename = os.path.splitext(filename)[0] + ".mp3"
            mp3_path     = os.path.join(MP3_DIR, mp3_filename)

            progress.update(task, description=f"[yellow]Convirtiendo[/yellow]  {filename}")
            convert_to_mp3(mp4_path, mp3_path)

            progress.update(task, description=f"[cyan]Transcribiendo[/cyan] {filename}")
            text     = transcribe_audio(model, mp3_path, language)
            out_path = save_transcription(text, filename)

            results.append((filename, out_path))
            progress.advance(task)

    # Resumen final
    console.print()
    summary = Table(show_header=True, header_style="bold green", border_style="dim", box=None)
    summary.add_column("Archivo fuente", style="dim")
    summary.add_column("Transcripción guardada", style="cyan")

    for filename, out_path in results:
        summary.add_row(filename, out_path)

    console.print(Panel(summary, title="[bold green]Listo[/bold green]", border_style="green"))
    console.print()


# ─────────────────────────── main ───────────────────────────────

def main():
    print_banner()

    ogg_files = scan_files(AUDIOS_DIR,    ".ogg")
    mp4_files = scan_files(MP4_DIR,       ".mp4")
    mp3_files = scan_files(MP3_INPUT_DIR, ".mp3")

    print_file_summary(ogg_files, mp4_files, mp3_files)

    if not ogg_files and not mp4_files and not mp3_files:
        console.print("[yellow]No hay archivos para procesar.[/yellow]")
        console.print("[dim]  · .ogg  →  audios/[/dim]")
        console.print("[dim]  · .mp3  →  mp3-input/[/dim]")
        console.print("[dim]  · .mp4  →  mp4/[/dim]")
        sys.exit(0)

    # Try TUI mode, fallback to CLI mode if it fails
    try:
        mode = select_mode(bool(ogg_files), bool(mp4_files), bool(mp3_files))
    except Exception as e:
        console.print(f"\n[yellow]La TUI no funciona en este entorno: {type(e).__name__}[/yellow]")
        console.print("[dim]Cambiando a modo automático...[/dim]\n")
        
        # Auto-select all available files
        selected_ogg = ogg_files
        selected_mp4 = mp4_files
        selected_mp3 = mp3_files
        
        if not selected_ogg and not selected_mp3 and not selected_mp4:
            abort("No hay archivos para procesar.")
        
        # Default options
        model_name = "base"
        language = "Spanish"
        
        console.print(f"[cyan]Modo automático:[/cyan]")
        console.print(f"  Archivos OGG: {len(selected_ogg)}")
        console.print(f"  Archivos MP3: {len(selected_mp3)}")
        console.print(f"  Archivos MP4: {len(selected_mp4)}")
        console.print(f"  Modelo: {model_name}")
        console.print(f"  Idioma: {language}\n")
        
        run_pipeline(selected_ogg, selected_mp4, selected_mp3, model_name, language)
        return

    if mode == "exit":
        abort("Saliendo.")

    selected_ogg: list[str] = []
    selected_mp4: list[str] = []
    selected_mp3: list[str] = []

    if mode in ("ogg", "all"):
        selected_ogg = select_files(ogg_files, ".ogg")

    if mode in ("mp3", "all"):
        selected_mp3 = select_files(mp3_files, ".mp3")

    if mode in ("mp4", "all"):
        selected_mp4 = select_files(mp4_files, ".mp4")

    if not selected_ogg and not selected_mp3 and not selected_mp4:
        abort("No seleccionaste ningún archivo.")

    model_name = select_model()
    console.print()

    language = select_language()
    console.print()

    total = len(selected_ogg) + len(selected_mp3) + len(selected_mp4)
    lang_label = language or "auto-detectar"
    confirmed = ask(
        questionary.confirm,
        f"Procesar {total} archivo(s) · modelo '{model_name}' · idioma '{lang_label}'?",
        default=True,
        style=CUSTOM_STYLE,
    )

    if not confirmed:
        abort()

    run_pipeline(selected_ogg, selected_mp4, selected_mp3, model_name, language)


if __name__ == "__main__":
    main()
