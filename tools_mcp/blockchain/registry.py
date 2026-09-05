"""Blockchain and smart-contract analysis tools with fail-closed scope gates.

All tools operate on a checked-out repository explicitly listed in
``IN_SCOPE_REPOS``. They use fixed local-analysis commands and never submit
transactions, inject a private key, or accept a free-form command argument.
Long-running analysis uses the shared detached launch/fetch lifecycle.
"""

from __future__ import annotations

from pathlib import Path

from unified_agent.tools import ToolRegistry

from tools_mcp import asyncrun
from tools_mcp.hub_guard.enforce import (
    ScopeError,
    log_activity,
    record_tool_failure,
    record_tool_run,
    require_blockchain_scope,
    require_installed,
)

REGISTRY = ToolRegistry(server_name="blockchain")

_TIMEOUTS = {
    "hardhat_test": 20 * 60,
    "forge_test": 20 * 60,
    "forge_fuzz": 30 * 60,
    "forge_invariant": 30 * 60,
    "slither_scan": 20 * 60,
    "echidna_fuzz": 30 * 60,
    "mythril_analyze": 30 * 60,
    "sol2uml_graph": 10 * 60,
}


def _repo_directory(repo: str) -> Path:
    directory = Path(repo).expanduser()
    if not directory.is_dir():
        raise ScopeError(
            f"in-scope repository {repo!r} is not a local checked-out directory — "
            "clone or symlink it under the engagement's ignored references/ directory first"
        )
    return directory.resolve()


def _launch(
    tool: str,
    binary: str,
    argv: list[str],
    repo: str,
    attack_class: str,
) -> str:
    try:
        require_installed(binary)
        require_blockchain_scope(repo=repo, attack_class=attack_class)
        directory = _repo_directory(repo)
    except ScopeError as exc:
        record_tool_failure(
            f"blockchain.launch_{tool}(repo={repo!r}, attack_class={attack_class!r})",
            str(exc),
            scope_decision="rejected",
            status="rejected",
        )
        raise
    handle = asyncrun.launch(tool, argv, _TIMEOUTS[tool], cwd=directory)
    log_activity(
        f"blockchain.launch_{tool}(repo={repo!r}, attack_class={attack_class}) -> handle={handle}"
    )
    return handle


def _fetch(tool: str, handle: str) -> str:
    result = asyncrun.fetch(handle)
    if result.status == "running":
        return f"status=running (handle={handle}); call fetch_{tool} again later"
    return record_tool_run(
        f"blockchain.fetch_{tool}(handle={handle}) -> {result.status}", result.output
    )


@REGISTRY.tool()
def launch_hardhat_test(repo: str) -> str:
    """Run a project's local Hardhat test suite; returns a handle for fetch_hardhat_test.

    Uses ``npx --no-install`` so it cannot download or install Hardhat. The
    selected project therefore needs its own declared dev dependency first.
    """
    return _launch(
        "hardhat_test", "npx", ["npx", "--no-install", "hardhat", "test"], repo, "static"
    )


@REGISTRY.tool()
def fetch_hardhat_test(handle: str) -> str:
    """Poll a Hardhat test run started by launch_hardhat_test."""
    return _fetch("hardhat_test", handle)


@REGISTRY.tool()
def launch_forge_test(repo: str) -> str:
    """Run the standard Foundry test suite; returns a handle for fetch_forge_test."""
    return _launch("forge_test", "forge", ["forge", "test"], repo, "static")


@REGISTRY.tool()
def fetch_forge_test(handle: str) -> str:
    """Poll a Foundry test run started by launch_forge_test."""
    return _fetch("forge_test", handle)


@REGISTRY.tool()
def launch_forge_fuzz(repo: str, fuzz_runs: int = 256) -> str:
    """Run Foundry fuzz tests; requires ALLOW_FUZZING and returns a fetch handle."""
    if fuzz_runs < 1 or fuzz_runs > 100_000:
        raise ValueError("fuzz_runs must be between 1 and 100000")
    return _launch(
        "forge_fuzz", "forge", ["forge", "test", "--fuzz-runs", str(fuzz_runs)], repo, "fuzz"
    )


@REGISTRY.tool()
def fetch_forge_fuzz(handle: str) -> str:
    """Poll a Foundry fuzz run started by launch_forge_fuzz."""
    return _fetch("forge_fuzz", handle)


@REGISTRY.tool()
def launch_forge_invariant(repo: str, runs: int = 256) -> str:
    """Run Foundry invariant tests; requires ALLOW_INVARIANT_TESTING and returns a fetch handle."""
    if runs < 1 or runs > 100_000:
        raise ValueError("runs must be between 1 and 100000")
    return _launch(
        "forge_invariant",
        "forge",
        ["forge", "test", "--match-test", "^invariant_", "--invariant-runs", str(runs)],
        repo,
        "invariant",
    )


@REGISTRY.tool()
def fetch_forge_invariant(handle: str) -> str:
    """Poll a Foundry invariant run started by launch_forge_invariant."""
    return _fetch("forge_invariant", handle)


@REGISTRY.tool()
def launch_slither_scan(repo: str) -> str:
    """Run Slither against the in-scope repository root; returns a handle for fetch_slither_scan."""
    return _launch("slither_scan", "slither", ["slither", "."], repo, "static")


@REGISTRY.tool()
def fetch_slither_scan(handle: str) -> str:
    """Poll a Slither scan started by launch_slither_scan."""
    return _fetch("slither_scan", handle)


@REGISTRY.tool()
def launch_echidna_fuzz(repo: str, config_file: str = "echidna.yaml") -> str:
    """Run Echidna with a repo-local config; requires ALLOW_FUZZING and returns a fetch handle."""
    config = Path(config_file)
    if config.is_absolute() or ".." in config.parts:
        raise ValueError("config_file must be a relative path inside the in-scope repository")
    return _launch("echidna_fuzz", "echidna", ["echidna", str(config)], repo, "fuzz")


@REGISTRY.tool()
def fetch_echidna_fuzz(handle: str) -> str:
    """Poll an Echidna run started by launch_echidna_fuzz."""
    return _fetch("echidna_fuzz", handle)


@REGISTRY.tool()
def launch_mythril_analyze(repo: str, source_file: str) -> str:
    """Run Mythril static analysis on a repo-local Solidity source file; returns a fetch handle."""
    source = Path(source_file)
    if source.is_absolute() or ".." in source.parts:
        raise ValueError("source_file must be a relative path inside the in-scope repository")
    return _launch("mythril_analyze", "myth", ["myth", "analyze", str(source)], repo, "static")


@REGISTRY.tool()
def fetch_mythril_analyze(handle: str) -> str:
    """Poll a Mythril analysis started by launch_mythril_analyze."""
    return _fetch("mythril_analyze", handle)


@REGISTRY.tool()
def launch_sol2uml_graph(repo: str, source_path: str = "contracts") -> str:
    """Generate a UML graph from a repo-local source path; returns a handle for fetch_sol2uml_graph."""
    source = Path(source_path)
    if source.is_absolute() or ".." in source.parts:
        raise ValueError("source_path must be a relative path inside the in-scope repository")
    return _launch("sol2uml_graph", "sol2uml", ["sol2uml", "class", str(source)], repo, "static")


@REGISTRY.tool()
def fetch_sol2uml_graph(handle: str) -> str:
    """Poll a sol2uml graph generation started by launch_sol2uml_graph."""
    return _fetch("sol2uml_graph", handle)
