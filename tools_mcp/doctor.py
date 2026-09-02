"""Preflight check for the MCP tool servers.

See the MCP wiring design notes. Plain script, not an MCP
tool -- run it directly, not auto-injected into any session startup:

    tools-env/.venv/bin/python tools_mcp/doctor.py            # human-readable
    tools-env/.venv/bin/python tools_mcp/doctor.py --json      # machine-readable

Supersedes hand-maintaining tools_mcp/MANIFEST.md: regenerate MANIFEST.md
from this script's --json output rather than hand-editing it (see
tools_mcp/generate_manifest.py) -- a generated record can't drift from
reality the way a manually updated one can. If both exist, this script is
authoritative, MANIFEST.md is a convenience index, never the other way
around.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENV_PYTHON = REPO_ROOT / "tools-env" / ".venv" / "bin" / "python"
SECLISTS_DIR = REPO_ROOT / "tools-env" / "seclists"

# The actual configured stdio ToolRegistry servers (hub_guard is a shared
# library, not a spawnable MCP server -- see hub_guard/enforce.py's
# module docstring -- so it isn't listed here).
STDIO_SERVERS = {
    "recon": "tools_mcp.recon.registry:REGISTRY",
    "webapp": "tools_mcp.webapp.registry:REGISTRY",
    "blockchain": "tools_mcp.blockchain.registry:REGISTRY",
}

# External, GUI-app-hosted servers this project doesn't build -- just
# checking whether the app is currently open with its extension loaded.
# metasploit is NOT here: unlike burp/binrev, msfmcpd doesn't need a
# pre-existing open GUI app -- it auto-starts its own RPC daemon, so a
# real stdio handshake (see check_metasploit below) is the meaningful
# check, not a port ping.
EXTERNAL_SERVERS = {
    "burp": "http://127.0.0.1:9876",
    "binrev": "http://127.0.0.1:8080/",  # Ghidra's own HTTP server (not the bridge's stdio process)
}

MSFMCPD_WRAPPER = REPO_ROOT / "tools-env" / "msfmcpd_wrapper.sh"


def check_venv() -> dict:
    if not VENV_PYTHON.exists():
        return {"ok": False, "detail": f"{VENV_PYTHON} missing -- run: python3 -m venv tools-env/.venv"}
    result = subprocess.run(
        [str(VENV_PYTHON), "-c", "import unified_agent; print(unified_agent.__file__)"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"ok": False, "detail": f"unified_agent not importable: {result.stderr.strip()}"}
    return {"ok": True, "detail": result.stdout.strip()}


def check_seclists() -> dict:
    if SECLISTS_DIR.is_dir():
        return {"ok": True, "detail": str(SECLISTS_DIR)}
    return {
        "ok": False,
        "detail": f"missing -- git clone --depth 1 https://github.com/danielmiessler/SecLists.git {SECLISTS_DIR}",
    }


def check_binaries() -> dict:
    sys.path.insert(0, str(REPO_ROOT))
    from tools_mcp.hub_guard.enforce import INSTALL_COMMANDS

    return {
        binary: {
            "installed": (path := shutil.which(binary)) is not None,
            "path": path,
            "install_command": install_cmd,
        }
        for binary, install_cmd in INSTALL_COMMANDS.items()
    }


async def _handshake(command: str, args: list[str], env: dict | None, timeout: float) -> dict:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(command=command, args=args, env=env, cwd=str(REPO_ROOT))
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=timeout)
                tools = await asyncio.wait_for(session.list_tools(), timeout=timeout)
                return {"ok": True, "tool_count": len(tools.tools)}
    except Exception as e:  # noqa: BLE001 -- reporting any failure reason is the point
        return {"ok": False, "detail": str(e)}


def _registry_handshake(spec: str) -> dict:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT), "MCP_ACTOR": "doctor", "MCP_ROLE": "worker"}
    return asyncio.run(_handshake(str(VENV_PYTHON), ["-m", "unified_agent.tool_server", spec], env, timeout=10))


def check_stdio_servers() -> dict:
    return {name: _registry_handshake(spec) for name, spec in STDIO_SERVERS.items()}


def check_metasploit() -> dict:
    if not MSFMCPD_WRAPPER.exists():
        return {"ok": False, "detail": f"{MSFMCPD_WRAPPER} missing -- see tools_mcp/MANIFEST.md"}
    # Generous timeout: msfmcpd auto-starts its own RPC daemon on first
    # connect, which takes real wall-clock time (verified ~several
    # seconds on this machine).
    return asyncio.run(_handshake(str(MSFMCPD_WRAPPER), [], None, timeout=60))


def check_external(url: str) -> dict:
    try:
        urllib.request.urlopen(url, timeout=2)  # noqa: S310 -- localhost-only, fixed URLs
        return {"ok": True, "detail": f"{url} reachable"}
    except urllib.error.HTTPError as e:
        # any HTTP response (even 404/405) proves something is listening
        return {"ok": True, "detail": f"{url} reachable (HTTP {e.code})"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "detail": f"{url} unreachable ({e}) -- is the app open with its extension loaded?"}


def check_external_servers() -> dict:
    return {name: check_external(url) for name, url in EXTERNAL_SERVERS.items()}


def check_staleness() -> dict:
    sys.path.insert(0, str(REPO_ROOT))
    from tools_mcp.hub_guard.enforce import UPDATE_COMMANDS, staleness_warning

    result = {}
    for tool in UPDATE_COMMANDS:
        warning = staleness_warning(tool).strip()
        detail = warning.removeprefix("[!] ") if warning else "up to date"
        result[tool] = {"stale": bool(warning), "detail": detail}
    return result


def build_report() -> dict:
    return {
        "venv": check_venv(),
        "seclists": check_seclists(),
        "binaries": check_binaries(),
        "stdio_servers": check_stdio_servers(),
        "metasploit": check_metasploit(),
        "external_servers": check_external_servers(),
        "staleness": check_staleness(),
    }


def print_human(report: dict) -> None:
    def line(ok: bool, label: str, detail: str = "") -> None:
        mark = "OK  " if ok else "MISS"
        print(f"[{mark}] {label}" + (f" -- {detail}" if detail else ""))

    print("== venv / unified-agent ==")
    line(report["venv"]["ok"], "tools-env/.venv", report["venv"]["detail"])

    print("\n== SecLists ==")
    line(report["seclists"]["ok"], "tools-env/seclists/", report["seclists"]["detail"])

    print("\n== stdio MCP servers ==")
    for name, result in report["stdio_servers"].items():
        detail = f"{result.get('tool_count', '?')} tools" if result["ok"] else result["detail"]
        line(result["ok"], name, detail)

    print("\n== metasploit (self-starting RPC, no GUI app needed) ==")
    m = report["metasploit"]
    line(m["ok"], "metasploit", f"{m.get('tool_count', '?')} tools" if m["ok"] else m["detail"])

    print("\n== external MCP servers (app must be open right now) ==")
    for name, result in report["external_servers"].items():
        line(result["ok"], name, result["detail"])

    print("\n== binaries ==")
    for binary, result in report["binaries"].items():
        detail = result["path"] if result["installed"] else f"install with: {result['install_command']}"
        line(result["installed"], binary, detail)

    print("\n== staleness (soft warning only, does not block) ==")
    for tool, result in report["staleness"].items():
        mark = "STALE" if result["stale"] else "FRESH"
        print(f"[{mark}] {tool} -- {result['detail']}")

    all_ok = (
        report["venv"]["ok"]
        and all(r["ok"] for r in report["stdio_servers"].values())
        and report["metasploit"]["ok"]
        and all(r["installed"] for r in report["binaries"].values())
    )
    print(f"\n{'READY' if all_ok else 'NOT READY'} -- see MISS lines above for what's missing.")


def main() -> None:
    report = build_report()
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2))
    else:
        print_human(report)


if __name__ == "__main__":
    main()
