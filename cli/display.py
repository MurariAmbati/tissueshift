"""TissueShift CLI — banner, formatting, and shared utilities."""

from __future__ import annotations

import shutil
import sys

VERSION = "0.1.0"

# ── Banner ────────────────────────────────────────────────────────────────────

BANNER = r"""
 _____ _                      ____  _     _  __ _
|_   _(_)___ ___ _   _  ___  / ___|| |__ (_)/ _| |_
  | | | / __/ __| | | |/ _ \ \___ \| '_ \| | |_| __|
  | | | \__ \__ \ |_| |  __/  ___) | | | | |  _| |_
  |_| |_|___/___/\__,_|\___| |____/|_| |_|_|_|  \__|
"""

TAGLINE = "Open Temporal Histopathology-to-Omics | Breast Cancer Subtype Emergence & Progression"


def _term_width() -> int:
    return shutil.get_terminal_size((80, 24)).columns


def _rule(char: str = "-", width: int | None = None) -> str:
    w = width or min(_term_width(), 88)
    return char * w


def print_banner() -> None:
    """Print the TissueShift startup banner."""
    w = min(_term_width(), 88)
    sys.stdout.write("\n")
    for line in BANNER.strip("\n").splitlines():
        sys.stdout.write(f"  {line}\n")
    sys.stdout.write("\n")
    sys.stdout.write(f"  v{VERSION}  |  {TAGLINE}\n")
    sys.stdout.write(f"  {_rule('-', w - 2)}\n\n")


def print_header(title: str) -> None:
    """Print a section header."""
    w = min(_term_width(), 88)
    sys.stdout.write(f"\n  {title.upper()}\n")
    sys.stdout.write(f"  {_rule('-', w - 2)}\n")


def print_kv(key: str, value: str, indent: int = 4) -> None:
    """Print a key-value pair."""
    pad = " " * indent
    sys.stdout.write(f"{pad}{key:<28} {value}\n")


def print_step(step: int, total: int, msg: str) -> None:
    """Print a numbered step indicator."""
    tag = f"[{step}/{total}]"
    sys.stdout.write(f"  {tag:<10} {msg}\n")


def print_ok(msg: str) -> None:
    sys.stdout.write(f"  [OK]      {msg}\n")


def print_warn(msg: str) -> None:
    sys.stdout.write(f"  [WARN]    {msg}\n")


def print_err(msg: str) -> None:
    sys.stderr.write(f"  [ERROR]   {msg}\n")


def print_done() -> None:
    w = min(_term_width(), 88)
    sys.stdout.write(f"\n  {_rule('-', w - 2)}\n")
    sys.stdout.write("  DONE\n\n")


def print_footer() -> None:
    w = min(_term_width(), 88)
    sys.stdout.write(f"\n  {_rule('-', w - 2)}\n")
    sys.stdout.write(f"  TISSUE SHIFT v{VERSION}  |  Apache 2.0  |  github.com/MurariAmbati/tissueshift\n")
    sys.stdout.write(f"  {_rule('-', w - 2)}\n\n")
