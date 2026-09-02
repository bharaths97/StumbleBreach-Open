"""Scope enforcement and activity logging shared by every native MCP tool.

Plain Python functions, imported directly by other registries — never
exposed as an MCP tool themselves. A `check_scope` MCP tool would enforce
nothing, since nothing stops a model from calling `recon.nmap_scan`
directly without ever calling it first. See the MCP wiring design
notes on the hub_guard server spec and `require_installed`.
"""

from __future__ import annotations

import datetime
import json
import os
import re
import shutil
from pathlib import Path


class ScopeError(Exception):
    """Raised when a target/action isn't authorized for this engagement."""


class ToolNotInstalledError(Exception):
    """Raised when a tool's underlying binary isn't on PATH."""


# Single source of truth for install commands, referenced by both
# require_installed()'s error messages and tools_mcp/doctor.py. Verified
# working on this machine during implementation -- several of the base
# plan's original guesses didn't actually work as written (nuclei/dalfox
# needed plain `brew install`, not a tap; arjun/commix needed `pipx`, not
# `pip`, to land an isolated venv with a PATH-visible script; dirb isn't
# packaged for macOS via Homebrew at all).
INSTALL_COMMANDS: dict[str, str] = {
    "nmap": "brew install nmap",
    "gobuster": "brew install gobuster",
    "dirb": "not available via Homebrew on macOS -- build from source "
    "(https://github.com/v0re/dirb) or use gobuster/ffuf instead",
    "whois": "brew install whois",
    "dig": "brew install bind",
    "subfinder": "brew install subfinder",
    "nuclei": "brew install nuclei",
    "sqlmap": "brew install sqlmap",
    "arjun": "pipx install arjun",
    "searchsploit": "brew install exploitdb",
    "dalfox": "brew install dalfox",
    "commix": "pipx install commix",
    "ffuf": "brew install ffuf",
    "hydra": "brew install hydra",
    "httpx": "brew install httpx",
    "nikto": "brew install nikto",
    "wpscan": "brew install wpscanteam/tap/wpscan",
    "tshark": "brew install wireshark",
    # Blockchain tooling. These commands were checked against the local
    # package registries (Homebrew, PyPI, and npm) but are intentionally
    # never executed by a tool wrapper: installation is a user-confirmed,
    # local-machine change.
    "npx": "brew install node",
    "forge": "brew install foundry",
    "slither": "pipx install slither-analyzer",
    "echidna": "brew install echidna",
    "myth": "pipx install mythril",
    "sol2uml": "npm install --global sol2uml",
}

# Update commands for tools/data that go stale independent of the binary
# version itself (see the MCP wiring design notes). Not
# auto-executed -- same rationale as INSTALL_COMMANDS: this is a
# visibility mechanism (surfaced by tools_mcp/doctor.py's staleness
# pass), not an auto-updater. Run the command yourself, then record it
# with `tools_mcp/mark_updated.py <tool>`.
UPDATE_COMMANDS: dict[str, str] = {
    "nuclei": "nuclei -update-templates",
    # `searchsploit -u`'s git self-update doesn't work cleanly against a
    # Homebrew install (tries to sudo/git-pull inside the Cellar path,
    # verified to fail on this machine) -- `brew upgrade exploitdb` is
    # the correct update path when installed this way.
    "searchsploit": "brew upgrade exploitdb",
    "wpscan": "wpscan --update",
    "seclists": "git -C tools-env/seclists pull",
}

# Recorded by tools_mcp/mark_updated.py, read by tools_mcp/doctor.py and
# staleness_warning() below -- hub-level state (tied to tools_mcp/
# itself), not per-engagement, so this is relative to this file's own
# location, not CWD.
_TIMESTAMPS_PATH = Path(__file__).resolve().parent.parent / ".update-timestamps.json"
STALENESS_THRESHOLD_DAYS = 7


def _staleness_days(tool: str) -> int | None:
    """Days since `tool` was last marked updated via mark_updated.py, or None if never recorded."""
    if not _TIMESTAMPS_PATH.exists():
        return None
    timestamps = json.loads(_TIMESTAMPS_PATH.read_text())
    recorded = timestamps.get(tool)
    if recorded is None:
        return None
    age = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(recorded)
    return age.days


def staleness_warning(tool: str) -> str:
    """One-line warning to prepend to a tool's output if its data is stale, else ''.

    Soft signal only -- surfaces the nudge at the moment it actually
    matters (see the MCP wiring design notes), on top of
    doctor.py's own staleness pass. Never blocks the tool from running.
    """
    if tool not in UPDATE_COMMANDS:
        return ""
    days = _staleness_days(tool)
    update_cmd = UPDATE_COMMANDS[tool]
    if days is None:
        return (
            f"[!] {tool} has never been marked updated -- run: {update_cmd}, "
            f"then: tools_mcp/mark_updated.py {tool}\n\n"
        )
    if days > STALENESS_THRESHOLD_DAYS:
        return f"[!] {tool} last updated {days}d ago -- consider: {update_cmd}\n\n"
    return ""


def require_installed(binary: str) -> None:
    """Raise ToolNotInstalledError with an actionable install command if missing.

    Never installs anything itself -- installing a new system binary is
    exactly the state-changing action bb-vigilante-shit's own guardrail requires
    explicit human confirmation for. This only fails with a message the
    model can relay to the user; it must not run the install command
    unprompted.
    """
    if shutil.which(binary) is None:
        hint = INSTALL_COMMANDS.get(binary, "(no known install command -- check tools_mcp/MANIFEST.md)")
        raise ToolNotInstalledError(f"{binary!r} is not installed. Install it with:\n  {hint}\nThen re-run this.")


def _target_env_values() -> tuple[Path, dict[str, str]]:
    # Relative to CWD at call time (the MCP server's launch directory), not
    # a hardcoded path — works unmodified on whichever engagement branch is
    # currently checked out.
    target_env = Path.cwd() / "config" / "target.env"
    if not target_env.exists():
        raise ScopeError(
            f"{target_env} not found — either scope hasn't been filled in for "
            "this engagement yet, or this is a CTF-template branch (no "
            "config/target.env there at all; recon/webapp tools are "
            "unavailable on CTF branches in this version, by design)"
        )
    values: dict[str, str] = {}
    for line in target_env.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return target_env, values


def _csv(values: dict[str, str], name: str) -> list[str]:
    return [item.strip() for item in values.get(name, "").split(",") if item.strip()]


def _in_scope_targets() -> list[str]:
    target_env, values = _target_env_values()
    # New mixed-surface engagements may keep web targets separate. Older
    # engagements have no TARGET_SURFACES/IN_SCOPE_WEB_TARGETS fields, so the
    # original IN_SCOPE_TARGETS behavior remains unchanged for them.
    web_targets = _csv(values, "IN_SCOPE_WEB_TARGETS")
    if web_targets:
        return web_targets
    targets = _csv(values, "IN_SCOPE_TARGETS")
    if targets:
        return targets
    raise ScopeError(
        f"{target_env} has no IN_SCOPE_WEB_TARGETS or IN_SCOPE_TARGETS line — "
        "this engagement predates the machine-parseable scope field and hasn't been migrated"
    )


def require_in_scope(target: str) -> None:
    """Raise ScopeError unless `target` is listed in config/target.env's IN_SCOPE_TARGETS.

    Every recon/webapp tool function must call this as its first line,
    before touching a subprocess.
    """
    in_scope = _in_scope_targets()
    if target not in in_scope:
        raise ScopeError(f"{target!r} is not in IN_SCOPE_TARGETS — refusing")


def require_authorized_bruteforce(
    target: str, i_have_confirmed_this_is_authorized: bool
) -> None:
    """Stricter gate for lockout/DoS-risk tools (hydra, etc.).

    Being in IN_SCOPE_TARGETS is not enough on its own — scope.md already
    treats DoS/lockout-risk testing as presumptively disallowed ("assume
    not allowed until confirmed"). The caller must also pass explicit
    human confirmation for this specific action.
    """
    require_in_scope(target)
    if not i_have_confirmed_this_is_authorized:
        raise ScopeError(
            f"brute-force against {target!r} needs explicit human authorization "
            "beyond the normal scope check — re-call with "
            "i_have_confirmed_this_is_authorized=True only after the user has "
            "actually confirmed this specific action is allowed"
        )


def _truthy(values: dict[str, str], name: str) -> bool:
    return values.get(name, "").strip().lower() == "true"


def _require_blockchain_member(
    values: dict[str, str], field: str, requested: str, label: str, *, case_insensitive: bool = False
) -> None:
    allowed = _csv(values, field)
    if case_insensitive:
        allowed_match = {value.casefold() for value in allowed}
        matches = requested.casefold() in allowed_match
    else:
        matches = requested in allowed
    if not matches:
        rendered = ", ".join(allowed) if allowed else "(none declared)"
        raise ScopeError(
            f"{label} {requested!r} is not in {field} ({rendered}) — refusing"
        )


def require_blockchain_scope(
    contract: str | None = None,
    repo: str | None = None,
    chain_id: str | int | None = None,
    rpc_endpoint: str | None = None,
    attack_class: str | None = None,
    requires_transaction: bool = False,
    requires_live_oracle_manipulation: bool = False,
    requires_live_mev: bool = False,
    requires_dos_or_gas_griefing: bool = False,
    transaction_environment: str | None = None,
) -> None:
    """Fail closed unless a blockchain action is explicitly authorized.

    This is an in-process guard, not an MCP tool: registries call it before
    starting a subprocess. Exact scope values belong in ``config/target.env``.
    ``transaction_environment`` is required for any transaction-capable
    action and must be one of ``mainnet``, ``testnet``, or ``local-fork``.
    """
    target_env, values = _target_env_values()
    surfaces = _csv(values, "TARGET_SURFACES")
    if "blockchain" not in surfaces:
        rendered = ", ".join(surfaces) if surfaces else "(missing)"
        raise ScopeError(
            f"{target_env} does not authorize the blockchain surface "
            f"(TARGET_SURFACES={rendered}) — refusing"
        )
    if not any((contract, repo, chain_id is not None, rpc_endpoint)):
        raise ScopeError(
            "blockchain action has no contract, repo, chain ID, or RPC endpoint "
            "to check against explicit scope — refusing"
        )
    if contract is not None:
        _require_blockchain_member(values, "IN_SCOPE_CONTRACTS", contract, "contract", case_insensitive=True)
    if repo is not None:
        _require_blockchain_member(values, "IN_SCOPE_REPOS", repo, "repository")
    if chain_id is not None:
        _require_blockchain_member(values, "IN_SCOPE_CHAIN_IDS", str(chain_id), "chain ID")
    if rpc_endpoint is not None:
        _require_blockchain_member(values, "IN_SCOPE_RPC_ENDPOINTS", rpc_endpoint, "RPC endpoint")
    if attack_class is not None:
        _require_blockchain_member(values, "AUTHORIZED_ATTACK_CLASSES", attack_class, "attack class")
        if attack_class == "fuzz" and not _truthy(values, "ALLOW_FUZZING"):
            raise ScopeError("ALLOW_FUZZING is not true in config/target.env — refusing fuzzing")
        if attack_class == "invariant" and not _truthy(values, "ALLOW_INVARIANT_TESTING"):
            raise ScopeError(
                "ALLOW_INVARIANT_TESTING is not true in config/target.env — refusing invariant testing"
            )

    if requires_transaction:
        flag_for_environment = {
            "mainnet": "ALLOW_MAINNET_TX",
            "testnet": "ALLOW_TESTNET_TX",
            "local-fork": "ALLOW_LOCAL_FORK_MUTATION",
        }.get(transaction_environment or "")
        if flag_for_environment is None:
            raise ScopeError(
                "transaction-capable blockchain actions require transaction_environment "
                "of mainnet, testnet, or local-fork — refusing"
            )
        if not _truthy(values, flag_for_environment):
            raise ScopeError(
                f"{flag_for_environment} is not true in {target_env} — refusing transaction-capable action"
            )
    if requires_live_oracle_manipulation and not _truthy(values, "ALLOW_LIVE_ORACLE_MANIPULATION"):
        raise ScopeError("live oracle manipulation is not explicitly authorized — refusing")
    if requires_live_mev and not _truthy(values, "ALLOW_LIVE_MEV_TESTING"):
        raise ScopeError("live MEV testing is not explicitly authorized — refusing")
    if requires_dos_or_gas_griefing and not _truthy(values, "ALLOW_DOS_OR_GAS_GRIEFING"):
        raise ScopeError("DoS or gas-griefing is not explicitly authorized — refusing")


def _actor_role() -> tuple[str, str]:
    actor = os.environ.get("MCP_ACTOR", "unknown")
    role = os.environ.get("MCP_ROLE", "worker")
    return actor, role


def log_activity(action: str) -> None:
    """Append one line to logs/activity.log in this project's standard format."""
    actor, role = _actor_role()
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_path = Path.cwd() / "logs" / "activity.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as f:
        f.write(f"{timestamp} [{actor}/{role}] {action}\n")


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_.-]")


def record_tool_run(action: str, output: str, max_inline_chars: int = 4000) -> str:
    """Log `action`, persist raw `output` under logs/, return an inline copy.

    Logs one activity.log line (success or failure — callers should include
    the outcome in `action`) and writes the full output to
    logs/agent-scan-logs/ so large scan output isn't lost to context
    truncation. Returns the text a tool function should actually return to
    the model — truncated with a pointer to the full file if it's large.
    """
    log_activity(action)
    log_dir = Path.cwd() / "logs" / "agent-scan-logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_action = _SAFE_NAME_RE.sub("_", action)[:80]
    out_path = log_dir / f"{timestamp}-{safe_action}.log"
    out_path.write_text(output)
    if len(output) <= max_inline_chars:
        return output
    return (
        output[:max_inline_chars]
        + f"\n\n[... truncated; full output saved to {out_path} ...]"
    )
