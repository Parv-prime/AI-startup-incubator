"""Print local hardware facts used for model selection."""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys


def main() -> None:
    print("os:", platform.platform())
    print("python:", sys.version.split()[0], sys.executable)
    print("ollama:", shutil.which("ollama") or "not found")
    try:
        subprocess.run(["ollama", "list"], check=False)
    except FileNotFoundError:
        print("Ollama CLI is not available.")


if __name__ == "__main__":
    main()
