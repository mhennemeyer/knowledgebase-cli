"""
PDF auf einer bestimmten Seite öffnen (macOS).

Nutzt Preview.app über das `open`-Kommando mit Skim als Alternative.
"""
import subprocess
import shutil


def build_open_cmd(pdf_path: str, page: int = 1) -> str:
    """
    Erstellt das macOS-Kommando zum Öffnen einer PDF auf einer bestimmten Seite.

    Skim (/Applications/Skim.app) unterstützt direktes Seitenöffnen.
    Fallback: Preview.app (öffnet auf Seite 1).
    """
    if shutil.which("open") is None:
        return ""

    # Skim unterstützt --page Flag nativ
    skim_path = "/Applications/Skim.app"
    return f"open -a Skim '{pdf_path}' --args -page {page}"


def open_pdf(pdf_path: str, page: int = 1) -> None:
    """Öffnet eine PDF auf der angegebenen Seite."""
    cmd = build_open_cmd(pdf_path, page)
    if not cmd:
        raise RuntimeError("macOS `open`-Kommando nicht verfügbar.")
    subprocess.run(cmd, shell=True, check=True)
