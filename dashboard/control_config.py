"""Read-only catalog of controls exposed by the StumbleBreach tool harness.

This is deliberately a catalog, not a settings writer.  The dashboard can use
the snapshot to show which values are authoritative today and which controls
are only candidates for a future prepare/confirm flow.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

CATALOG_VERSION = 1
_DEFAULT_CONFIG = Path.cwd() / "config" / "target.env"
_INLINE_OUTPUT_CHARS = 4000

# Values copied from the existing registries.  Keeping this small and explicit
# makes drift visible in the catalog instead of importing optional MCP deps.
_TIMEOUTS = {
    "recon.nmap": 30 * 60,
    "recon.gobuster": 15 * 60,
    "recon.dirb": 15 * 60,
    "recon.subfinder": 10 * 60,
    "webapp.sqlmap": 30 * 60,
    "webapp.nuclei": 20 * 60,
    "webapp.synchronous": 10 * 60,
    "webapp.fast": 60,
    "blockchain.hardhat_test": 20 * 60,
    "blockchain.forge_test": 20 * 60,
    "blockchain.forge_fuzz": 30 * 60,
    "blockchain.forge_invariant": 30 * 60,
    "blockchain.slither_scan": 20 * 60,
    "blockchain.echidna_fuzz": 30 * 60,
    "blockchain.mythril_analyze": 30 * 60,
    "blockchain.sol2uml_graph": 10 * 60,
}

_AUTH_FLAGS = (
    "ALLOW_FUZZING",
    "ALLOW_INVARIANT_TESTING",
    "ALLOW_MAINNET_TX",
    "ALLOW_TESTNET_TX",
    "ALLOW_LOCAL_FORK_MUTATION",
    "ALLOW_LIVE_ORACLE_MANIPULATION",
    "ALLOW_LIVE_MEV_TESTING",
    "ALLOW_DOS_OR_GAS_GRIEFING",
)
_SCOPE_FIELDS = (
    "IN_SCOPE_TARGETS",
    "IN_SCOPE_WEB_TARGETS",
    "TARGET_SURFACES",
    "IN_SCOPE_CONTRACTS",
    "IN_SCOPE_REPOS",
    "IN_SCOPE_CHAIN_IDS",
    "IN_SCOPE_RPC_ENDPOINTS",
    "AUTHORIZED_ATTACK_CLASSES",
)


def _knob(
    knob_id: str,
    label: str,
    classification: str,
    authority: str,
    *,
    source: str,
    note: str,
    value_type: str = "string",
    safe_values: list[Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": knob_id,
        "label": label,
        "classification": classification,
        "authority": authority,
        "source": source,
        "value_type": value_type,
        "safe_values": safe_values,
        "note": note,
    }


def build_control_catalog() -> dict[str, Any]:
    """Return the stable catalog contract consumed by a future dashboard UI."""
    knobs = [
        _knob(
            "engagement.scope",
            "Scope selection",
            "prepare-only",
            "scope.md and config/target.env",
            source="engagement scope records",
            note="Select an existing authorized scope record; never edit it here.",
            value_type="reference",
        ),
        _knob(
            "engagement.queue_cell",
            "Queue cell",
            "prepare-only",
            "harness/queue.md",
            source="harness/queue.md",
            note="Prepare a packet for an existing queue row; no implicit selection.",
            value_type="reference",
        ),
        _knob(
            "execution.role",
            "Role",
            "prepare-only",
            "role handoff contract",
            source="docs/integration/HANDOFF_CONTRACT.md",
            note="Choose the receiving role for a handoff; does not dispatch it.",
            value_type="enum",
            safe_values=["bb-mastermind", "bb-vigilante-shit", "ctf-mastermind", "ctf-vigilante-shit", "karma"],
        ),
        _knob(
            "execution.timeout_seconds",
            "Execution timeout",
            "confirm-required",
            "tool registry timeout constants",
            source="tools_mcp/{recon,webapp,blockchain}/registry.py",
            note="Future UI may choose a bounded value no greater than the adapter cap.",
            value_type="integer",
        ),
        _knob(
            "execution.output_max_chars",
            "Inline output ceiling",
            "confirm-required",
            "record_tool_run default",
            source="tools_mcp/hub_guard/enforce.py",
            note="Raw output remains in the existing evidence/log path; UI receives bounded text.",
            value_type="integer",
            safe_values=[_INLINE_OUTPUT_CHARS],
        ),
        _knob(
            "execution.adapter_enablement",
            "Adapter enablement",
            "confirm-required",
            "registered ToolRegistry servers",
            source="tools_mcp/{recon,webapp,blockchain}/registry.py",
            note="No mutable enablement authority exists yet; current state is reported as unavailable.",
            value_type="enum",
            safe_values=["recon", "webapp", "blockchain"],
        ),
        _knob(
            "execution.concurrency_limit",
            "Concurrent jobs",
            "confirm-required",
            "unavailable: no cross-process limiter",
            source="tools_mcp/asyncrun.py",
            note="Cross-session concurrency is not capped; the UI must not pretend this knob works.",
            value_type="integer",
        ),
        _knob(
            "dashboard.health_poll_seconds",
            "Health polling interval",
            "prepare-only",
            "dashboard client",
            source="dashboard/server.py and dashboard/app.js",
            note="Currently manual/read-only; a future UI preference may change polling only.",
            value_type="integer",
            safe_values=[5, 10, 30, 60],
        ),
        _knob(
            "evidence.destination",
            "Evidence destination",
            "confirm-required",
            "engagement evidence layout",
            source="docs/WORKFLOW.md and tools_mcp/hub_guard/enforce.py",
            note="Allow only known engagement paths; arbitrary filesystem paths are not a control.",
            value_type="enum",
            safe_values=["logs/agent-scan-logs", "findings/evidence/<finding-slug>"],
        ),
        _knob(
            "redaction.policy",
            "Receipt redaction",
            "display-only",
            "hub guard sanitizer",
            source="tools_mcp/hub_guard/enforce.py",
            note="Always-on safety behavior; the dashboard can display its health, not weaken it.",
            value_type="policy",
        ),
        _knob(
            "gates.backpatch",
            "Backpatch gate",
            "display-only",
            "compatibility record and backpatch validator",
            source="docs/integration/backpatch-compatibility.json and scripts/resume_engagement.py",
            note="Show gate result and blockers; do not bypass it from the UI.",
            value_type="status",
        ),
        _knob(
            "gates.public_export",
            "Public-export gate",
            "display-only",
            "public leak scan and export guard",
            source="scripts/public_leak_scan.py and scripts/public_push_guard.py",
            note="Show dry-run/readiness only; publication remains an operator Git action.",
            value_type="status",
        ),
    ]
    knobs.extend(
        _knob(
            f"authorization.{flag.lower()}",
            flag,
            "confirm-required",
            f"config/target.env:{flag}",
            source="tools_mcp/hub_guard/enforce.py",
            note="A true value is an explicit engagement authorization, never a default.",
            value_type="boolean",
            safe_values=[False, True],
        )
        for flag in _AUTH_FLAGS
    )
    return {
        "schema_version": CATALOG_VERSION,
        "catalog_version": CATALOG_VERSION,
        "knobs": knobs,
        "forbidden": [
            {"id": "execution.arbitrary_command", "reason": "No arbitrary shell endpoint."},
            {"id": "execution.arbitrary_target", "reason": "Targets must come from the authoritative scope."},
            {"id": "execution.secret_value", "reason": "Secrets never enter the catalog, snapshot, or UI."},
            {"id": "server.remote_bind", "reason": "Dashboard remains loopback-only."},
            {"id": "execution.autonomous_dispatch", "reason": "The dashboard cannot silently dispatch agents."},
            {"id": "redaction.disable", "reason": "Receipt redaction is fail-closed and not user-disableable."},
        ],
    }


_SECRET_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|cookie|authorization|session)")


def _read_values(config_path: Path | str | None, values: Mapping[str, str] | None) -> tuple[dict[str, str], str]:
    if values is not None:
        return {str(key): str(value) for key, value in values.items()}, "provided mapping"
    path = Path(config_path) if config_path is not None else _DEFAULT_CONFIG
    if not path.is_file():
        return {}, "missing config/target.env"
    parsed: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip("'\"")
    return parsed, "config/target.env"


def _field_summary(values: Mapping[str, str], field: str) -> dict[str, Any]:
    raw = values.get(field, "")
    # Scope and endpoint contents are deliberately not copied into this snapshot.
    count = len([part for part in raw.split(",") if part.strip()])
    return {"state": "declared" if count else "undeclared", "count": count}


def snapshot_control_state(
    config_path: Path | str | None = None,
    *,
    values: Mapping[str, str] | None = None,
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Return a secret-free, read-only view of current knob availability."""
    config, source = _read_values(config_path, values)
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[1]
    legacy = bool(config) and not any(config.get(field, "").strip() for field in ("TARGET_SURFACES", "IN_SCOPE_WEB_TARGETS"))
    config_state = "missing" if not config else "legacy" if legacy else "current"
    controls: dict[str, dict[str, Any]] = {}
    for knob in build_control_catalog()["knobs"]:
        knob_id = knob["id"]
        item: dict[str, Any] = {
            "classification": knob["classification"],
            "state": "unavailable",
            "value": None,
            "authority": knob["authority"],
        }
        if knob_id == "execution.output_max_chars":
            item.update(state="available", value=_INLINE_OUTPUT_CHARS)
        elif knob_id == "execution.timeout_seconds":
            item.update(state="available", value=dict(_TIMEOUTS))
        elif knob_id == "execution.adapter_enablement":
            item.update(
                state="unavailable",
                value={"registered": ["recon", "webapp", "blockchain"], "mutable": False},
            )
            item["reason"] = "registered adapters have no mutable enablement authority"
        elif knob_id == "redaction.policy":
            item.update(state="available", value="always-on")
        elif knob_id == "gates.backpatch":
            item.update(state="available" if (root / "docs/integration/backpatch-compatibility.json").is_file() else "unavailable", value="present" if (root / "docs/integration/backpatch-compatibility.json").is_file() else None)
        elif knob_id == "gates.public_export":
            item.update(state="available" if (root / "scripts/public_leak_scan.py").is_file() else "unavailable", value="present" if (root / "scripts/public_leak_scan.py").is_file() else None)
        elif knob_id.startswith("authorization."):
            field = knob_id.rsplit(".", 1)[1].upper()
            item.update(state="available" if field in config else "undeclared", value=config.get(field, False) is True or config.get(field, "").lower() == "true")
        elif knob_id == "engagement.scope":
            item.update(state="available" if any(_field_summary(config, field)["count"] for field in _SCOPE_FIELDS) else "unavailable", value={field: _field_summary(config, field) for field in _SCOPE_FIELDS})
        elif knob_id == "dashboard.health_poll_seconds":
            item.update(state="unavailable", value=None)
        elif knob_id == "execution.concurrency_limit":
            item["reason"] = "cross-process limit is not implemented"
        elif knob_id == "evidence.destination":
            item.update(state="available", value=["logs/agent-scan-logs", "findings/evidence/<finding-slug>"])
        controls[knob_id] = item
    return {
        "schema_version": CATALOG_VERSION,
        "catalog_version": CATALOG_VERSION,
        "config_state": config_state,
        "source": source,
        "controls": controls,
        "warnings": ["legacy scope fields detected; history requires review"] if legacy else [],
    }


def diff_control_snapshots(before: Mapping[str, Any], after: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Compare safe snapshots without exposing any raw config values."""
    old = before.get("controls", {})
    new = after.get("controls", {})
    changes = []
    for knob_id in sorted(set(old) | set(new)):
        if old.get(knob_id) != new.get(knob_id):
            changes.append({"id": knob_id, "before": old.get(knob_id), "after": new.get(knob_id)})
    return changes


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    payload = snapshot_control_state(args.config) if args.snapshot else build_control_catalog()
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
