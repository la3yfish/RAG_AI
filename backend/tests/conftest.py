from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so `import backend...` works under pytest.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Optional: make tests deterministic across runs/env
os.environ.setdefault("PYTHONHASHSEED", "0")
