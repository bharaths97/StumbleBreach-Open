"""Host/network/subdomain discovery tools.

See the MCP wiring design notes on the recon server spec, and on
`require_installed` and the SecLists wordlist default. Every tool calls `require_installed` (cheaper, more
fundamental check) then `require_in_scope` before touching a subprocess,
and `record_tool_run`/`log_activity` after -- that's what actually makes
scope enforcement real here, not a separate tool the model could choose
to skip.
"""

from __future__ import annotations

import subprocess

from unified_agent.tools import ToolRegistry

from tools_mcp import asyncrun
from tools_mcp.hub_guard.enforce import (
    log_activity,
    ToolOutput,
    record_tool_run,
    require_in_scope,
    require_installed,
)

REGISTRY = ToolRegistry(server_name="recon")

# Default max runtime per scan type (seconds) -- nothing here runs unbounded.
_TIMEOUTS = {
    "nmap": 30 * 60,
    "gobuster": 15 * 60,
    "dirb": 15 * 60,
    "subfinder": 10 * 60,
}

# tools-env/seclists/ is a plain git clone (see the MCP wiring design
# notes), not a Python dependency.
_DEFAULT_DIR_WORDLIST = "tools-env/seclists/Discovery/Web-Content/common.txt"


def _run_sync(binary: str, args: list[str], timeout: int = 60) -> str:
    try:
        result = subprocess.run([binary, *args], capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        return ToolOutput(output, status="timed_out", timed_out=True)
    output = result.stdout + result.stderr
    return ToolOutput(output, status="failed" if result.returncode else "success", exit_code=result.returncode)


@REGISTRY.tool()
def whois_lookup(target: str) -> str:
    """Run whois against a domain or IP. Fast, synchronous."""
    require_installed("whois")
    require_in_scope(target)
    output = _run_sync("whois", [target])
    return record_tool_run(f"recon.whois_lookup(target={target})", output)


@REGISTRY.tool()
def dig_query(target: str, record_type: str = "A") -> str:
    """Run a dig DNS query against a domain. Fast, synchronous."""
    require_installed("dig")
    require_in_scope(target)
    output = _run_sync("dig", [target, record_type])
    return record_tool_run(
        f"recon.dig_query(target={target}, record_type={record_type})", output
    )


def _launch(tool: str, binary: str, argv: list[str], target: str, log_args: str, timeout: int | None = None) -> str:
    require_installed(binary)
    require_in_scope(target)
    handle = asyncrun.launch(tool, argv, timeout if timeout is not None else _TIMEOUTS[tool])
    log_activity(f"recon.launch_{tool}_scan({log_args}) -> handle={handle}")
    return handle


def _fetch(tool: str, handle: str) -> str:
    result = asyncrun.fetch(handle)
    if result.status == "running":
        return f"status=running (handle={handle}); call fetch again later"
    return record_tool_run(
        f"recon.fetch_{tool}_scan(handle={handle}) -> {result.status}", result.output
    )


@REGISTRY.tool()
def launch_nmap_scan(target: str, args: str = "-sV") -> str:
    """Start an nmap scan in the background; returns a handle for fetch_nmap_scan."""
    argv = ["nmap", *args.split(), target]
    return _launch("nmap", "nmap", argv, target, f"target={target}, args={args!r}")


@REGISTRY.tool()
def fetch_nmap_scan(handle: str) -> str:
    """Poll a background nmap scan started by launch_nmap_scan."""
    return _fetch("nmap", handle)


@REGISTRY.tool()
def launch_gobuster_scan(target: str, wordlist: str = _DEFAULT_DIR_WORDLIST, mode: str = "dir") -> str:
    """Start a gobuster scan in the background; returns a handle for fetch_gobuster_scan."""
    argv = ["gobuster", mode, "-u", target, "-w", wordlist]
    return _launch(
        "gobuster",
        "gobuster",
        argv,
        target,
        f"target={target}, wordlist={wordlist}, mode={mode}",
    )


@REGISTRY.tool()
def fetch_gobuster_scan(handle: str) -> str:
    """Poll a background gobuster scan started by launch_gobuster_scan."""
    return _fetch("gobuster", handle)


@REGISTRY.tool()
def launch_dirb_scan(target: str, wordlist: str = _DEFAULT_DIR_WORDLIST) -> str:
    """Start a dirb scan in the background; returns a handle for fetch_dirb_scan."""
    argv = ["dirb", target, wordlist]
    return _launch("dirb", "dirb", argv, target, f"target={target}, wordlist={wordlist}")


@REGISTRY.tool()
def fetch_dirb_scan(handle: str) -> str:
    """Poll a background dirb scan started by launch_dirb_scan."""
    return _fetch("dirb", handle)


@REGISTRY.tool()
def launch_subfinder_scan(target: str) -> str:
    """Start a subfinder subdomain-discovery scan in the background; returns a handle for fetch_subfinder_scan."""
    argv = ["subfinder", "-d", target]
    return _launch("subfinder", "subfinder", argv, target, f"target={target}")


@REGISTRY.tool()
def fetch_subfinder_scan(handle: str) -> str:
    """Poll a background subfinder scan started by launch_subfinder_scan."""
    return _fetch("subfinder", handle)


@REGISTRY.tool()
def httpx_probe(target: str, args: str = "") -> str:
    """Probe a target host/URL with httpx (status, title, tech-detection, etc). Fast, synchronous."""
    require_installed("httpx")
    require_in_scope(target)
    output = _run_sync("httpx", ["-u", target, *args.split()], timeout=120)
    return record_tool_run(f"recon.httpx_probe(target={target}, args={args!r})", output)


@REGISTRY.tool()
def tshark_capture(target: str, interface: str = "en0", duration_seconds: int = 60) -> str:
    """Start a bounded live packet capture filtered to `target` (a host/IP); returns a handle for tshark_read."""
    argv = ["tshark", "-i", interface, "-a", f"duration:{duration_seconds}", "-f", f"host {target}"]
    return _launch(
        "tshark",
        "tshark",
        argv,
        target,
        f"target={target}, interface={interface}, duration_seconds={duration_seconds}",
        timeout=duration_seconds + 30,
    )


@REGISTRY.tool()
def tshark_read(handle: str) -> str:
    """Poll a background packet capture started by tshark_capture."""
    return _fetch("tshark", handle)
