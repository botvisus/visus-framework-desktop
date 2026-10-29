"""Each command an AI agent runs is a new process: its start-up is paid on every
step. Heavy imports (cv2, numpy, rapidocr, pywinauto) must stay inside the
commands that use them, so a light command answers fast.
"""

from __future__ import annotations

import statistics
import subprocess
import sys
import time

LIMIT_S = 1.5


def test_display_size_inicia_rapido(tmp_path) -> None:
    runs = []
    for _ in range(3):
        start = time.monotonic()
        proc = subprocess.run(
            [sys.executable, "-m", "visus.desktop.cli", "display-size"],
            capture_output=True, text=True, timeout=60, cwd=str(tmp_path),
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        runs.append(time.monotonic() - start)
        assert proc.returncode == 0, proc.stdout + proc.stderr
    mean = statistics.mean(runs)
    print(f"\ndisplay-size: {', '.join(f'{r:.2f}' for r in runs)} s (média {mean:.2f} s)")
    assert mean <= LIMIT_S, f"início lento: média {mean:.2f} s > {LIMIT_S} s ({runs})"
