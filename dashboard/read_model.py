"""Read-only dashboard model assembled from Git objects and local reports.

This module deliberately has no HTTP server and no mutation methods.  The
future server can map the documented routes to :func:`build_read_model` and
return these dictionaries as JSON.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .control_config import build_control_catalog


SCHEMA_VERSION = 1
ROUTES = {
    "health": "/api/health",
    "overview": "/api/overview",
    "engagements": "/api/engagements",
    "engagement": "/api/engagements/{branch}",
    "handoffs": "/api/handoffs",
    "tooling": "/api/tooling",
    "run_status": "/api/run-status",
    "controls": "/api/controls",
}
READ_ONLY_METHODS = ("GET",)
REPO_ROOT = Path(__file__).resolve().parent.parent
_SECRET_RE = re.compile(
    r"(?i)(authorization|cookie|password|passwd|secret|token|api[_-]?key|session)"
    r"(\s*[:=]\s*|\s+Bearer\s+)[^\s,;}&)\]]+"
)
_NON_FINDINGS = {"TEMPLATE-finding.md", "plan.md"}
_NON_CHALLENGE_DIRS = {"TEMPLATE", "intake"}


def _redact(value: Any) -> str:
    return _SECRET_RE.sub(lambda match: f"{match.group(1)}=<redacted>", str(value))


def _state(*, present: bool, valid: bool = True, stale: bool = False, detail: str = "") -> dict[str, str]:
    if not present:
        name = "missing"
    elif not valid:
        name = "unknown"
    elif stale:
        name = "stale"
    else:
        name = "fresh"
    return {"state": name, "detail": detail or {"missing": "record unavailable", "unknown": "record could not be read", "stale": "record requires review", "fresh": "available"}[name]}


def _parse_table(text: str | None) -> list[dict[str, str]]:
    if not text:
        return []
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return []
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def _timestamp(text: str | None) -> str | None:
    lines = [line.strip() for line in (text or "").splitlines() if line.strip() and not line.strip().startswith("#")]
    return lines[-1].split(maxsplit=1)[0] if lines else None


def _json(text: str | None) -> tuple[Any, bool]:
    if text is None:
        return None, False
    try:
        return json.loads(text), True
    except (TypeError, json.JSONDecodeError):
        return None, False


class _GitObjects:
    """Read branch files without changing the checked-out branch."""

    def __init__(self, root: Path):
        self.root = root

    def show(self, ref: str, path: str) -> str | None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{ref}:{path}"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.stdout if result.returncode == 0 else None

    def tree(self, ref: str, path: str) -> list[tuple[str, str]]:
        result = subprocess.run(
            ["git", "-C", str(self.root), "ls-tree", ref, path],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            return []
        entries = []
        for line in result.stdout.splitlines():
            if "\t" not in line:
                continue
            meta, name = line.split("\t", 1)
            fields = meta.split()
            if len(fields) == 3:
                entries.append((fields[1], name))
        return entries


class _FixtureObjects:
    def __init__(self, fixture: Mapping[str, Any]):
        self.fixture = fixture
        self.objects = fixture.get("branch_objects", {})

    def show(self, ref: str, path: str) -> str | None:
        value = self.objects.get(ref, {}).get(path)
        if value is None:
            return None
        return value if isinstance(value, str) else json.dumps(value)

    def tree(self, ref: str, path: str) -> list[tuple[str, str]]:
        names = self.objects.get(ref, {}).get("tree", {}).get(path, [])
        kind = "blob" if path == "findings/" else "tree"
        return [(kind, name) for name in names]


def _engagements(objects: _GitObjects | _FixtureObjects, fixture: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if fixture is not None and "engagements" in fixture:
        return [dict(item) for item in fixture["engagements"]]
    rows = _parse_table(objects.show("main", "ENGAGEMENTS.md"))
    return [
        {
            "name": row.get("Name", "").strip("` "),
            "type": row.get("Type", "").strip(),
            "branch": row.get("Branch", "").strip("` "),
            "status": row.get("Status", "").strip(),
            "created": row.get("Created", "").strip(),
            "description": row.get("Description", "").strip(),
        }
        for row in rows
        if row.get("Name")
    ]


def _journey_projection(objects: _GitObjects | _FixtureObjects, branch: str) -> dict[str, Any]:
    value, valid = _json(objects.show(branch, "journey.json"))
    present = isinstance(value, dict)
    projection = value if present else {}
    return {
        "nodes": projection.get("nodes", []),
        "events": projection.get("events", []),
        "edges": projection.get("edges", []),
        "review_queue": projection.get("review_queue", []),
        "gaps": projection.get("gaps", []),
        "source": "journey.json",
        "state": _state(present=present, valid=valid and present),
    }


def _bug_bounty_view(objects: _GitObjects | _FixtureObjects, branch: str) -> dict[str, Any]:
    plan_text = objects.show(branch, "findings/plan.md")
    scope_text = objects.show(branch, "scope.md")
    activity_text = objects.show(branch, "logs/activity.log")
    coverage_text = objects.show(branch, "harness/coverage.json")
    queue_text = objects.show(branch, "harness/queue.md")
    harness_version = (objects.show(branch, "HARNESS_VERSION") or "").strip()
    plan_rows = _parse_table(plan_text)
    counts: dict[str, int] = {}
    for row in plan_rows:
        status = row.get("Status", "").lower() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    coverage, coverage_valid = _json(coverage_text)
    findings = sum(
        1 for kind, name in objects.tree(branch, "findings/")
        if kind == "blob" and name.rsplit("/", 1)[-1].endswith(".md") and name.rsplit("/", 1)[-1] not in _NON_FINDINGS
    )
    return {
        "view": "bug-bounty",
        "journey": _journey_projection(objects, branch),
        "harness_version": {"value": harness_version or None, "source": "HARNESS_VERSION", "state": _state(present=bool(harness_version))},
        "plan": {"total": len(plan_rows), "done": counts.get("done", 0), "status_counts": counts, "source": "findings/plan.md", "state": _state(present=plan_text is not None)},
        "findings": {"count": findings, "source": "findings/", "state": _state(present=bool(objects.tree(branch, "findings/")))},
        "scope": {"source": "scope.md", "state": _state(present=scope_text is not None)},
        "coverage": {"record": coverage if coverage_valid and isinstance(coverage, dict) else None, "source": "harness/coverage.json", "state": _state(present=coverage_text is not None, valid=coverage_valid)},
        "queue": {"source": "harness/queue.md", "state": _state(present=queue_text is not None)},
        "activity": {"last_timestamp": _timestamp(activity_text), "source": "logs/activity.log", "state": _state(present=activity_text is not None)},
    }


def _ctf_view(objects: _GitObjects | _FixtureObjects, branch: str) -> dict[str, Any]:
    status_text = objects.show(branch, "STATUS.md")
    challenges = []
    in_section = False
    pattern = re.compile(r"^[-*]?\s*([\w.\-]+):\s*(.+?)\s*\((\d+|\?)\s*/\s*(\d+|\?)\)\s*$")
    for line in (status_text or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("## Challenges"):
            in_section = True
        elif in_section and stripped.startswith("##"):
            break
        elif in_section:
            match = pattern.match(stripped)
            if match:
                name, state, captured, total = match.groups()
                challenges.append({"name": name, "state": state, "captured": captured, "total": total})
    activity = []
    for kind, name in objects.tree(branch, "challenges/"):
        challenge = name.rsplit("/", 1)[-1]
        if kind == "tree" and challenge not in _NON_CHALLENGE_DIRS:
            activity.append(_timestamp(objects.show(branch, f"{name}/activity.log")))
    known_captured = sum(int(row["captured"]) for row in challenges if row["captured"] != "?")
    known_total = sum(int(row["total"]) for row in challenges if row["total"] != "?")
    return {
        "view": "ctf",
        "journey": _journey_projection(objects, branch),
        "challenges": challenges,
        "flags": {"captured": known_captured, "total": known_total, "total_unknown": any(row["total"] == "?" for row in challenges)},
        "status": {"source": "STATUS.md", "state": _state(present=status_text is not None)},
        "activity": {"last_timestamp": max((value for value in activity if value), default=None), "source": "challenges/*/activity.log", "state": _state(present=any(activity), detail="challenge activity available" if any(activity) else "challenge activity unavailable")},
    }


def _receipt_summary(objects: _GitObjects | _FixtureObjects, branches: list[str], fixture: Mapping[str, Any] | None) -> dict[str, Any]:
    if fixture is not None and "tool_receipts" in fixture:
        raw = fixture["tool_receipts"]
        return {"items": [_safe_receipt(item) for item in raw if isinstance(item, dict)], "state": _state(present=True), "source": "logs/tool-receipts.jsonl"}
    items = []
    present = False
    malformed = False
    for branch in branches:
        text = objects.show(branch, "logs/tool-receipts.jsonl")
        if text is None:
            continue
        present = True
        for line in text.splitlines():
            record, valid = _json(line)
            if valid and isinstance(record, dict):
                items.append(_safe_receipt(record))
            else:
                malformed = True
    return {"items": items, "source": "logs/tool-receipts.jsonl", "state": _state(present=present, valid=not malformed)}


def _safe_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = ("receipt_id", "action", "status", "started_at", "ended_at", "exit_code", "timed_out", "execution_kind", "server_tool", "engagement", "branch", "queue_cell")
    return {key: (_redact(record[key]) if key == "action" else record[key]) for key in allowed if key in record}


def _engagement_collection(engagements: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Return discovery metadata without exposing engagement analysis/data."""
    items = []
    for item in engagements:
        analysis = item.get("analysis")
        view = analysis.get("view", "unknown") if isinstance(analysis, dict) else "unknown"
        items.append(
            {
                "name": _redact(item.get("name", "")),
                "type": _redact(item.get("type", "unknown")),
                "branch": _redact(item.get("branch", "")),
                "status": _redact(item.get("status", "unknown")),
                "view": _redact(view),
                "data_state": item.get("data_state", "unknown"),
            }
        )
    return {
        "items": items,
        "source": "main:ENGAGEMENTS.md",
        "state": _state(present=True),
    }


def _handoffs(fixture: Mapping[str, Any] | None, root: Path) -> dict[str, Any]:
    if fixture is not None and "handoffs" in fixture:
        records = fixture["handoffs"]
    else:
        path = root / "docs/integration/fixtures/handoffs.json"
        try:
            records = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            records = None
    if not isinstance(records, list):
        return {"items": [], "source": "docs/integration/fixtures/handoffs.json", "state": _state(present=records is not None, valid=False)}
    return {"items": [dict(item) for item in records if isinstance(item, dict)], "source": "docs/integration/fixtures/handoffs.json", "state": _state(present=True)}


def _health(fixture: Mapping[str, Any] | None, root: Path) -> dict[str, Any]:
    report = fixture.get("health") if fixture is not None else None
    if fixture is None:
        path = root / "tools_mcp/doctor-report.json"
        try:
            report, valid = _json(path.read_text(encoding="utf-8"))
        except OSError:
            report, valid = None, False
    else:
        valid = isinstance(report, dict)
    return {"report": report if isinstance(report, dict) else None, "source": "tools_mcp/doctor-report.json", "state": _state(present=report is not None, valid=valid)}


def build_read_model(root: Path | str | None = None, *, fixture: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Return the stable read model; ``fixture`` avoids all filesystem access in tests."""
    root_path = Path(root) if root is not None else REPO_ROOT
    objects: _GitObjects | _FixtureObjects = _FixtureObjects(fixture) if fixture is not None else _GitObjects(root_path)
    engagements = _engagements(objects, fixture)
    enriched = []
    for item in engagements:
        kind = str(item.get("type", "unknown")).lower()
        view = _bug_bounty_view(objects, item.get("branch", "")) if kind in {"bugbounty", "bug-bounty"} else _ctf_view(objects, item.get("branch", "")) if kind == "ctf" else {"view": "unknown", "state": _state(present=True, valid=False, detail="unsupported engagement type")}
        enriched.append({**item, "type": "bug-bounty" if kind in {"bugbounty", "bug-bounty"} else kind, "data_state": "fresh" if view.get("view") != "unknown" else "unknown", "analysis": view})
    bug_bounty = [item for item in enriched if item["type"] == "bug-bounty"]
    ctf = [item for item in enriched if item["type"] == "ctf"]
    branches = [item.get("branch", "") for item in enriched if item.get("branch")]
    engagement_collection = _engagement_collection(enriched)
    handoffs = _handoffs(fixture, root_path)
    health = _health(fixture, root_path)
    tooling = _receipt_summary(objects, branches, fixture)
    controls = fixture.get("controls") if fixture is not None else None
    if not isinstance(controls, Mapping):
        controls = build_control_catalog()
    return {
        "schema_version": SCHEMA_VERSION,
        "read_only": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {"registry": "main:ENGAGEMENTS.md", "branch_reads": "git show/git ls-tree; no checkout"},
        "overview": {"engagement_count": len(enriched), "bug_bounty_count": len(bug_bounty), "ctf_count": len(ctf), "unknown_count": len(enriched) - len(bug_bounty) - len(ctf)},
        "engagement_collection": engagement_collection,
        "views": {"bug_bounty": bug_bounty, "ctf": ctf},
        "engagements": enriched,
        "handoffs": handoffs,
        "tooling": tooling,
        "controls": dict(controls),
        "health": health,
        "run_status": {"state": "unknown", "detail": "No runner is configured; runner integration is on hold."},
    }


def read_route(model: Mapping[str, Any], route: str) -> dict[str, Any]:
    """Resolve a documented read route without providing an action endpoint."""
    if route == ROUTES["health"]:
        return dict(model["health"])
    if route == ROUTES["overview"]:
        return dict(model["overview"])
    if route == ROUTES["engagements"]:
        return dict(model["engagement_collection"])
    if route == ROUTES["handoffs"]:
        return dict(model["handoffs"])
    if route == ROUTES["tooling"]:
        return dict(model["tooling"])
    if route == ROUTES["controls"]:
        return dict(model["controls"])
    if route == ROUTES["run_status"]:
        return dict(model["run_status"])
    prefix = "/api/engagements/"
    if route.startswith(prefix):
        branch = route[len(prefix):]
        for item in model["engagements"]:
            if item.get("branch") == branch:
                return dict(item)
    raise KeyError(f"unknown read route: {route}")
