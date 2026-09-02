"""Detached-subprocess launch/fetch pattern shared by recon and webapp.

For any scan that can run past a few seconds: `launch(...)` starts the
subprocess in the background and returns immediately with an opaque
handle; `fetch(handle)` polls/returns the result once ready. This avoids
blocking the MCP stdio connection for the scan's duration. Technique
reviewed from github.com/ramkansal/pentestMCP during design (technique
only, not its code or tool selection); see the MCP wiring design
notes on the async launch/fetch pattern.

Each server is a stdio process spawned per session; if the client tears
it down when the session ends, a still-running scan risks being killed
with it unless detached from the parent's process group. `launch` uses
`start_new_session=True` for exactly that reason — don't remove it.

Known limitation (documented in the plan, not solved here): the
concurrency this module doesn't cap is cross-process — a `Semaphore`
would only cap launches within one server, not across simultaneously
open sessions. Not built in this pass.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

SCRATCH_ROOT = "tools-env/scratch"


def _scratch_dir(handle: str) -> Path:
    return Path.cwd() / SCRATCH_ROOT / handle


def launch(tool: str, argv: list[str], timeout_seconds: int, cwd: str | Path | None = None) -> str:
    """Start `argv` as a detached background process; return a handle for fetch()."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    handle = f"{tool}-{timestamp}-{uuid.uuid4().hex[:8]}"
    scratch = _scratch_dir(handle)
    scratch.mkdir(parents=True, exist_ok=True)
    stdout_path = scratch / "output.log"
    meta_path = scratch / "meta.json"
    with stdout_path.open("wb") as out:
        proc = subprocess.Popen(
            argv,
            stdout=out,
            stderr=subprocess.STDOUT,
            cwd=str(cwd) if cwd is not None else None,
            start_new_session=True,  # detach: survive this MCP server's own teardown
        )
    meta_path.write_text(
        json.dumps(
            {
                "tool": tool,
                "argv": argv,
                "cwd": str(cwd) if cwd is not None else None,
                "pid": proc.pid,
                "started_at": timestamp,
                "timeout_seconds": timeout_seconds,
                "deadline": time.time() + timeout_seconds,
            }
        )
    )
    return handle


class FetchResult(NamedTuple):
    status: str  # "running" | "done" | "timed_out"
    output: str


def fetch(handle: str) -> FetchResult:
    """Poll a launched scan. Kills and reports timeout past its deadline."""
    scratch = _scratch_dir(handle)
    meta_path = scratch / "meta.json"
    stdout_path = scratch / "output.log"
    if not meta_path.exists():
        raise FileNotFoundError(f"no such launch handle: {handle!r}")
    meta = json.loads(meta_path.read_text())
    pid = meta["pid"]
    output = stdout_path.read_text() if stdout_path.exists() else ""

    alive = _pid_alive(pid)
    if alive and time.time() > meta["deadline"]:
        _kill(pid)
        return FetchResult(status="timed_out", output=output)
    if alive:
        return FetchResult(status="running", output=output)
    return FetchResult(status="done", output=output)


def _pid_alive(pid: int) -> bool:
    """True if `pid` is still running.

    Tries a non-blocking `waitpid` first: since the server process is the
    real parent of a launched scan (`start_new_session` detaches the
    process *group*, not the parent/child relationship), an exited child
    becomes a zombie under it until reaped -- and a zombie still answers
    `kill(pid, 0)` successfully, which would make this report "running"
    forever even long after the scan finished. `waitpid(WNOHANG)` reaps it
    the moment it exits. Falls back to `kill(pid, 0)` if `pid` isn't this
    process's child (e.g. a `fetch` call from a different process).
    """
    try:
        reaped_pid, _status = os.waitpid(pid, os.WNOHANG)
        return reaped_pid != pid
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _kill(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
