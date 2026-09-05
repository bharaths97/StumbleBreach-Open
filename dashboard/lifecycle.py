"""Explicit local start/stop commands for the Pavilion service card."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PID_FILE = ROOT / ".stumblebreach-dashboard.pid"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4400
STOP_TIMEOUT_SECONDS = 3
_CHILDREN: dict[int, subprocess.Popen[bytes]] = {}
# ponytail: a small PID file keeps this service self-contained; an OS service
# manager is the upgrade path if multiple dashboard instances ever matter.


def _read_state(pid_file: Path) -> dict[str, int] | None:
    try:
        value = json.loads(pid_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or not isinstance(value.get("pid"), int):
        return None
    return value


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except (ProcessLookupError, OSError):
        return False
    return True


def _remove_state(pid_file: Path) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


def _write_state(pid_file: Path, pid: int, port: int) -> None:
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    temporary = pid_file.with_suffix(".tmp")
    temporary.write_text(json.dumps({"pid": pid, "port": port}) + "\n", encoding="utf-8")
    temporary.replace(pid_file)


def start(*, port: int = DEFAULT_PORT, pid_file: Path = PID_FILE) -> int:
    state = _read_state(pid_file)
    if state and _alive(state["pid"]):
        return state["pid"]
    if state:
        _remove_state(pid_file)

    child = subprocess.Popen(
        [sys.executable, "-m", "dashboard.server", "--host", DEFAULT_HOST, "--port", str(port)],
        cwd=ROOT.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    _CHILDREN[child.pid] = child
    _write_state(pid_file, child.pid, port)
    return child.pid


def stop(*, pid_file: Path = PID_FILE) -> int | None:
    state = _read_state(pid_file)
    if not state:
        _remove_state(pid_file)
        return None

    pid = state["pid"]
    child = _CHILDREN.pop(pid, None)
    if child is not None:
        try:
            child.terminate()
            child.wait(timeout=STOP_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=STOP_TIMEOUT_SECONDS)
    elif _alive(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        deadline = time.monotonic() + STOP_TIMEOUT_SECONDS
        while _alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        if _alive(pid):
            try:
                os.kill(pid, getattr(signal, "SIGKILL", signal.SIGTERM))
            except ProcessLookupError:
                pass
    _remove_state(pid_file)
    return pid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop"))
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if args.action == "start":
        print(f"dashboard started: pid={start(port=args.port)}")
    else:
        print(f"dashboard stopped: pid={stop()}")


if __name__ == "__main__":
    main()
