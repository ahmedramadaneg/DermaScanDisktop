"""Locating files both in development and inside a PyInstaller build."""
import sys
from pathlib import Path


def app_dir() -> Path:
    """Folder containing the .exe (frozen) or the project root (development)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def bundle_dir() -> Path:
    """Folder where PyInstaller unpacked bundled data (_MEIPASS / _internal)."""
    return Path(getattr(sys, "_MEIPASS", app_dir()))


def find_assets():
    """Return (model_path | None, labels_path | None).

    Search order: <exe folder>/assets, then the bundled copy. Files placed next
    to the .exe therefore override anything baked into the build.
    """
    model, labels = None, None
    for folder in (app_dir() / "assets", bundle_dir() / "assets"):
        if not folder.is_dir():
            continue
        if model is None:
            tflites = sorted(folder.glob("*.tflite"))
            preferred = [p for p in tflites if p.name == "model_quant_fp16.tflite"]
            model = (preferred or tflites or [None])[0]
        if labels is None and (folder / "labels.txt").is_file():
            labels = folder / "labels.txt"
    return model, labels
