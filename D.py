"""Compatibility entry point for the DaySense AI Streamlit app."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
