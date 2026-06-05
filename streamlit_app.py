"""Hugging Face Spaces Streamlit entry point."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


ENTRYPOINT = Path(__file__).resolve()


def _streamlit_command() -> list[str]:
    scripts_dir = "Scripts" if sys.platform.startswith("win") else "bin"
    executable = "streamlit.exe" if sys.platform.startswith("win") else "streamlit"
    project_streamlit = ENTRYPOINT.parent / ".venv" / scripts_dir / executable

    if project_streamlit.exists():
        return [str(project_streamlit)]
    if importlib.util.find_spec("streamlit") is not None:
        return [sys.executable, "-m", "streamlit"]
    return []


def _is_running_with_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


def _launch_with_streamlit() -> None:
    command = _streamlit_command()
    if not command:
        raise SystemExit(
            "Streamlit is not installed for this Python interpreter. "
            "Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
        )

    raise SystemExit(subprocess.run(command + ["run", str(ENTRYPOINT)], check=False).returncode)


def _run_app() -> None:
    from app import main

    main()


if __name__ == "__main__":
    if not _is_running_with_streamlit():
        _launch_with_streamlit()
    _run_app()
