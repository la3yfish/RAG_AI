from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SafeRunResult:
    ok: bool
    returncode: int | None
    timed_out: bool
    oom_suspected: bool
    stdout: str
    stderr: str
    duration_ms: int


class SafeRunnerError(RuntimeError):
    pass


def run_python_module(
    *,
    module: str,
    args: list[str] | None = None,
    input_json: dict[str, Any] | None = None,
    timeout_sec: int = 20,
    memory_mb: int | None = 512,
    cpu_sec: int | None = 10,
    cwd: str | None = None,
    env: dict[str, str] | None = None,
) -> SafeRunResult:
    """
    Run `python -m <module> ...` in a sandboxed subprocess.

    Safety:
      - hard timeout (all platforms)
      - kill entire process group (all platforms)
      - memory/cpu limits (POSIX only: Linux/macOS)

    Communication:
      - optional JSON payload via stdin
      - expects stdout/stderr text; JSON output is caller's responsibility

    Returns SafeRunResult with best-effort oom detection.
    """
    if timeout_sec <= 0:
        raise ValueError("timeout_sec must be > 0")

    cmd = [sys.executable, "-m", module]
    if args:
        cmd.extend(args)

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    stdin_data = None
    if input_json is not None:
        stdin_data = json.dumps(input_json, ensure_ascii=False).encode("utf-8")

    start = time.monotonic()
    timed_out = False
    oom_suspected = False

    preexec_fn = None
    creationflags = 0

    # Create an isolated process group so we can kill the whole tree.
    if os.name == "posix":
        def _preexec() -> None:
            os.setsid()
            _apply_posix_limits(memory_mb=memory_mb, cpu_sec=cpu_sec)

        preexec_fn = _preexec
    else:
        # Windows: create new process group so we can send CTRL_BREAK_EVENT if needed.
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    p = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_data is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=cwd,
        env=merged_env,
        preexec_fn=preexec_fn,
        creationflags=creationflags,
    )

    try:
        out, err = p.communicate(input=stdin_data, timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        timed_out = True
        _kill_process_tree(p)
        out, err = _best_effort_collect_output(p)
    except Exception as e:
        _kill_process_tree(p)
        raise SafeRunnerError(f"Sandbox run failed: {e}") from e

    duration_ms = int((time.monotonic() - start) * 1000)

    stdout = (out or b"").decode("utf-8", errors="replace")
    stderr = (err or b"").decode("utf-8", errors="replace")

    returncode = p.returncode
    if os.name == "posix" and returncode in (-signal.SIGKILL, -signal.SIGABRT):
        # Heuristic: killed by OOM killer often shows SIGKILL; ABRT sometimes for alloc failures.
        oom_suspected = True
    if "MemoryError" in stderr or "std::bad_alloc" in stderr:
        oom_suspected = True

    ok = (not timed_out) and (returncode == 0)

    return SafeRunResult(
        ok=ok,
        returncode=returncode,
        timed_out=timed_out,
        oom_suspected=oom_suspected,
        stdout=stdout,
        stderr=stderr,
        duration_ms=duration_ms,
    )


def _apply_posix_limits(*, memory_mb: int | None, cpu_sec: int | None) -> None:
    """Apply POSIX resource limits. Best-effort; if unavailable, proceed."""
    try:
        import resource
    except Exception:
        return

    # CPU time limit (seconds)
    if cpu_sec is not None:
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_sec, cpu_sec))
        except Exception:
            pass

    # Address space limit (bytes) – prevents runaway allocations
    if memory_mb is not None:
        limit_bytes = int(memory_mb) * 1024 * 1024
        try:
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
        except Exception:
            # Some systems disallow RLIMIT_AS; try data segment limit as fallback.
            try:
                resource.setrlimit(resource.RLIMIT_DATA, (limit_bytes, limit_bytes))
            except Exception:
                pass


def _kill_process_tree(p: subprocess.Popen[bytes]) -> None:
    """Kill process group (preferred) and then the process itself."""
    try:
        if os.name == "posix":
            # Kill the whole process group created by setsid()
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except Exception:
                pass
        else:
            # Windows best-effort: terminate process (child processes may remain for some cases)
            try:
                p.send_signal(signal.SIGTERM)
            except Exception:
                pass
    finally:
        try:
            p.kill()
        except Exception:
            pass
        try:
            p.wait(timeout=2)
        except Exception:
            pass


def _best_effort_collect_output(p: subprocess.Popen[bytes]) -> tuple[bytes, bytes]:
    """Try to read what remains in pipes after killing."""
    out = b""
    err = b""
    try:
        if p.stdout:
            out = p.stdout.read() or b""
    except Exception:
        pass
    try:
        if p.stderr:
            err = p.stderr.read() or b""
    except Exception:
        pass
    return out, err
