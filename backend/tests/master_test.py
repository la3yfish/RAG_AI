from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[2]  # repo root (RAG_AI/)
    staged_dir = root / "backend" / "tests" / "staged"

    if not staged_dir.exists():
        print(f"[master_test] staged tests dir not found: {staged_dir}")
        return 2

    # Ensure we always run with the current interpreter.
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(staged_dir),
        "-W",
        "error",
    ]

    env = os.environ.copy()
    # Make output stable/deterministic.
    env.setdefault("PYTHONHASHSEED", "0")

    print("[master_test] running:", " ".join(cmd))
    p = subprocess.run(cmd, cwd=str(root), env=env)
    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
