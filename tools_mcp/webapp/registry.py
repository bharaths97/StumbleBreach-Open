"""Web application testing tools -- vulnerability classes beyond `recon`.

See the MCP wiring design notes on the webapp server spec, and on
`require_installed` and the SecLists wordlist default. Every tool calls `require_installed` then
`require_in_scope` (or, for `hydra_bruteforce`, the stricter
`require_authorized_bruteforce`) before touching a subprocess, and
`record_tool_run`/`log_activity` after -- the same enforcement contract
as `recon`.

No SSRF/CSRF tool here by design: there's no standard CLI scanner for
either the way there is for XSS/SQLi/command injection -- see the plan
for why (Burp Collaborator / interactsh-client for SSRF OOB, Burp's own
CSRF PoC generator for CSRF). Don't invent one.
"""

from __future__ import annotations

import subprocess

from unified_agent.tools import ToolRegistry

from tools_mcp import asyncrun
from tools_mcp.hub_guard.enforce import (
    log_activity,
    record_tool_run,
    require_authorized_bruteforce,
    require_in_scope,
    require_installed,
    staleness_warning,
    ToolOutput,
)

REGISTRY = ToolRegistry(server_name="webapp")

# Long-running (async launch/fetch), per the plan's spec table.
_ASYNC_TIMEOUTS = {
    "sqlmap": 30 * 60,
    "nuclei": 20 * 60,
}

# Synchronous, but still bounded -- nothing in scope here runs unbounded.
_SYNC_TIMEOUT_SECONDS = 10 * 60
_FAST_TIMEOUT_SECONDS = 60

# tools-env/seclists/ is a plain git clone (see the MCP wiring design
# notes), not a Python dependency.
_DEFAULT_FUZZ_WORDLIST = "tools-env/seclists/Discovery/Web-Content/common.txt"


def _run_sync(binary: str, args: list[str], timeout: int) -> str:
    try:
        result = subprocess.run([binary, *args], capture_output=True, text=True, timeout=timeout)
        output = result.stdout + result.stderr
        return ToolOutput(output, status="failed" if result.returncode else "success", exit_code=result.returncode)
    except subprocess.TimeoutExpired as e:
        partial = (e.stdout or "") + (e.stderr or "")
        return ToolOutput(
            f"{partial}\n\n[timed out after {timeout}s]",
            status="timed_out",
            timed_out=True,
        )


def _launch(tool: str, binary: str, argv: list[str], target: str, log_args: str) -> str:
    require_installed(binary)
    require_in_scope(target)
    handle = asyncrun.launch(tool, argv, _ASYNC_TIMEOUTS[tool])
    log_activity(f"webapp.launch_{tool}_scan({log_args}) -> handle={handle}")
    return handle


def _fetch(tool: str, handle: str) -> str:
    result = asyncrun.fetch(handle)
    if result.status == "running":
        return f"status=running (handle={handle}); call fetch again later"
    output = record_tool_run(
        f"webapp.fetch_{tool}_scan(handle={handle}) -> {result.status}", result.output
    )
    return staleness_warning(tool) + output


@REGISTRY.tool()
def launch_sqlmap_scan(target: str, args: str = "--batch") -> str:
    """Start a sqlmap SQL-injection scan in the background; returns a handle for fetch_sqlmap_scan."""
    argv = ["sqlmap", "-u", target, *args.split()]
    return _launch("sqlmap", "sqlmap", argv, target, f"target={target}, args={args!r}")


@REGISTRY.tool()
def fetch_sqlmap_scan(handle: str) -> str:
    """Poll a background sqlmap scan started by launch_sqlmap_scan."""
    return _fetch("sqlmap", handle)


@REGISTRY.tool()
def launch_nuclei_scan(target: str, args: str = "") -> str:
    """Start a nuclei template-based vulnerability scan in the background; returns a handle for fetch_nuclei_scan."""
    argv = ["nuclei", "-u", target, *args.split()]
    return _launch("nuclei", "nuclei", argv, target, f"target={target}, args={args!r}")


@REGISTRY.tool()
def fetch_nuclei_scan(handle: str) -> str:
    """Poll a background nuclei scan started by launch_nuclei_scan."""
    return _fetch("nuclei", handle)


@REGISTRY.tool()
def arjun_scan(target: str, args: str = "") -> str:
    """Discover hidden HTTP parameters on a target URL with arjun."""
    require_installed("arjun")
    require_in_scope(target)
    argv = ["-u", target, *args.split()]
    output = _run_sync("arjun", argv, _SYNC_TIMEOUT_SECONDS)
    return record_tool_run(f"webapp.arjun_scan(target={target}, args={args!r})", output)


@REGISTRY.tool()
def searchsploit_lookup(product: str, version: str = "") -> str:
    """Look up known CVEs/PoCs for a product (and optional version) via searchsploit."""
    require_installed("searchsploit")
    query = f"{product} {version}".strip()
    require_in_scope(query)
    output = _run_sync("searchsploit", [query], _FAST_TIMEOUT_SECONDS)
    result = record_tool_run(
        f"webapp.searchsploit_lookup(product={product!r}, version={version!r})", output
    )
    return staleness_warning("searchsploit") + result


@REGISTRY.tool()
def dalfox_scan(target: str, args: str = "") -> str:
    """Scan a target URL for XSS with dalfox."""
    require_installed("dalfox")
    require_in_scope(target)
    argv = ["url", target, *args.split()]
    output = _run_sync("dalfox", argv, _SYNC_TIMEOUT_SECONDS)
    return record_tool_run(f"webapp.dalfox_scan(target={target}, args={args!r})", output)


@REGISTRY.tool()
def commix_scan(target: str, args: str = "--batch") -> str:
    """Scan a target URL for OS command injection with commix."""
    require_installed("commix")
    require_in_scope(target)
    argv = ["--url", target, *args.split()]
    output = _run_sync("commix", argv, _SYNC_TIMEOUT_SECONDS)
    return record_tool_run(f"webapp.commix_scan(target={target}, args={args!r})", output)


@REGISTRY.tool()
def ffuf_fuzz(target: str, wordlist: str = _DEFAULT_FUZZ_WORDLIST, args: str = "") -> str:
    """Fuzz a target URL (parameters/forms/paths) with ffuf. `target` must contain a FUZZ placeholder."""
    require_installed("ffuf")
    require_in_scope(target)
    argv = ["-u", target, "-w", wordlist, *args.split()]
    output = _run_sync("ffuf", argv, _SYNC_TIMEOUT_SECONDS)
    return record_tool_run(
        f"webapp.ffuf_fuzz(target={target}, wordlist={wordlist}, args={args!r})", output
    )


@REGISTRY.tool()
def hydra_bruteforce(
    target: str,
    service: str,
    userlist: str,
    passlist: str,
    i_have_confirmed_this_is_authorized: bool = False,
) -> str:
    """Brute-force credentials against a service with hydra.

    Requires explicit human authorization beyond the normal scope check
    (scope.md treats DoS/lockout-risk testing as presumptively
    disallowed) -- pass i_have_confirmed_this_is_authorized=True only
    after the user has actually confirmed this specific action.
    """
    require_installed("hydra")
    require_authorized_bruteforce(target, i_have_confirmed_this_is_authorized)
    argv = ["-L", userlist, "-P", passlist, target, service]
    output = _run_sync("hydra", argv, _SYNC_TIMEOUT_SECONDS)
    return record_tool_run(
        f"webapp.hydra_bruteforce(target={target}, service={service})", output
    )


@REGISTRY.tool()
def nikto_scan(target: str, args: str = "") -> str:
    """Scan a target URL/host for known web-server vulnerabilities and misconfigurations with nikto."""
    require_installed("nikto")
    require_in_scope(target)
    argv = ["-h", target, *args.split()]
    output = _run_sync("nikto", argv, _SYNC_TIMEOUT_SECONDS)
    return record_tool_run(f"webapp.nikto_scan(target={target}, args={args!r})", output)


@REGISTRY.tool()
def wpscan_scan(target: str, args: str = "") -> str:
    """Scan a WordPress site for vulnerable plugins/themes/core with wpscan."""
    require_installed("wpscan")
    require_in_scope(target)
    argv = ["--url", target, *args.split()]
    output = _run_sync("wpscan", argv, _SYNC_TIMEOUT_SECONDS)
    result = record_tool_run(f"webapp.wpscan_scan(target={target}, args={args!r})", output)
    return staleness_warning("wpscan") + result
