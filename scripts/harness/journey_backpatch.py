#!/usr/bin/env python3
"""Read legacy engagement records and emit a reviewable Journey projection.

This command never writes.  It only makes high-confidence, source-linked
nodes/events/edges and places ambiguous history in ``review_queue``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

EDGE_TYPES = {
    "derived_from": "derived-from",
    "derived-from": "derived-from",
    "follow_up_to": "follow-up",
    "follow-up": "follow-up",
    "duplicate_of": "duplicate-of",
    "duplicate-of": "duplicate-of",
    "blocked_by": "blocked-by",
    "blocked-by": "blocked-by",
    "supersedes": "supersedes",
    "pivot_to": "pivot",
    "pivot-to": "pivot",
}
_TOKEN = re.compile(r"(?i)(\b(?:authorization|password|secret|token|api[_ -]?key)\b\s*[:=]\s*)[^\s,;]+")
_LOG = re.compile(r"^(\S+)\s+\[([^/\]]+)(?:/([^\]]+))?\]\s+(.*)$")
_KV = re.compile(r"(?<![\w-])([a-z][\w-]*)=([\w./:@+-]+)")


def _redact(value: str) -> str:
    return _TOKEN.sub(r"\1<redacted>", value)


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return value or "unknown"


def _prov(source: str | list[str], confidence: str = "high", kind: str = "derived") -> dict[str, Any]:
    refs = [source] if isinstance(source, str) else source
    return {"kind": kind, "source_refs": refs, "confidence": confidence, "review_state": "candidate" if kind != "unresolved" else "needs-review"}


def _node(node_id: str, kind: str, label: str, state: str, source: str) -> dict[str, Any]:
    return {"id": node_id, "kind": kind, "label": _redact(label), "state": state, "provenance": _prov(source)}


def _gap(gaps: list[dict[str, Any]], source: str, state: str, detail: str) -> None:
    gaps.append({"source": source, "state": state, "detail": detail, "provenance": _prov(source, "high", "unresolved")})


def _review(queue: list[dict[str, Any]], reason: str, source: str | list[str], candidate: str) -> None:
    refs = [source] if isinstance(source, str) else source
    queue.append({
        "id": "review-" + _slug(str(len(queue) + 1) + "-" + candidate),
        "reason": _redact(reason),
        "source_refs": refs,
        "candidate": _redact(candidate),
        "provenance": _prov(refs, "low", "unresolved"),
    })


def _read_json(path: Path, gaps: list[dict[str, Any]]) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _gap(gaps, str(path), "missing", "legacy source is not present")
    except (OSError, json.JSONDecodeError) as exc:
        _gap(gaps, str(path), "malformed", f"cannot read JSON: {exc}")
    return None


def _front_matter(path: Path) -> dict[str, Any]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, value = line.partition(":")
        if not separator:
            continue
        value = value.strip()
        if value.startswith("[") or value.startswith("{"):
            try:
                result[key.strip()] = json.loads(value)
                continue
            except json.JSONDecodeError:
                pass
        result[key.strip()] = value.strip("'\"")
    return result


def _values(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None or value == "":
        return []
    return [str(value)]


def _state(value: Any) -> str:
    value = str(value or "").lower()
    if value in {"done", "confirmed", "submitted", "solved", "complete", "closed"}:
        return "complete"
    if value in {"blocked", "rejected"}:
        return "blocked"
    if value in {"active", "in_progress", "testing", "selected"}:
        return "active"
    if value in {"skipped", "not_applicable"}:
        return "skipped"
    return "pending" if value else "unknown"


def _coverage(root: Path, nodes: list[dict[str, Any]], node_ids: dict[str, str], gaps: list[dict[str, Any]]) -> None:
    source = root / "harness" / "coverage.json"
    data = _read_json(source, gaps)
    if not isinstance(data, dict):
        return
    areas = data.get("areas")
    if not isinstance(areas, dict):
        _gap(gaps, str(source), "malformed", "areas must be an object")
        return
    for area_id, area in areas.items():
        cells = area.get("cells", {}) if isinstance(area, dict) else {}
        if not isinstance(cells, dict):
            _gap(gaps, f"{source}#areas.{area_id}.cells", "malformed", "cells must be an object")
            continue
        for cell_id, cell in cells.items():
            key = f"{area_id} / {cell_id}"
            ident = "coverage:" + _slug(key)
            node_ids["coverage:" + _slug(key)] = ident
            node_ids["coverage:" + _slug(cell_id)] = ident
            node_ids[_slug(cell_id)] = ident
            nodes.append(_node(ident, "coverage", key, _state(cell.get("status") if isinstance(cell, dict) else ""), f"{source}#areas.{area_id}.cells.{cell_id}"))


def _queue(root: Path, nodes: list[dict[str, Any]], node_ids: dict[str, str], edges: list[dict[str, Any]], reviews: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> None:
    source = root / "harness" / "queue.md"
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        _gap(gaps, str(source), "missing", "legacy source is not present")
        return
    except OSError as exc:
        _gap(gaps, str(source), "malformed", f"cannot read queue: {exc}")
        return
    for line_no, line in enumerate(lines, 1):
        if not line.lstrip().startswith("|") or set(line.replace("|", "").replace("-", "").replace(":", "").strip()) <= set():
            continue
        columns = [part.strip() for part in line.strip().strip("|").split("|")]
        if len(columns) < 4 or columns[0].lower() in {"cell (area / attack-class)", "cell"}:
            continue
        if all(not item or set(item) <= {"-", ":"} for item in columns):
            continue
        cell, proposed_by, reason, status = columns[:4]
        ident = "queue:" + _slug(cell)
        node_ids["queue:" + _slug(cell)] = ident
        node_ids.setdefault("queue:" + _slug(cell.rsplit("/", 1)[-1]), ident)
        node_ids.setdefault(_slug(cell), ident)
        nodes.append(_node(ident, "queue", cell, _state(status), f"{source}#L{line_no}"))
        coverage_id = node_ids.get("coverage:" + _slug(cell)) or node_ids.get(_slug(cell))
        if coverage_id and coverage_id != ident:
            edges.append({"id": f"edge-{ident}-coverage", "from": ident, "to": coverage_id, "type": "derived-from", "provenance": _prov(f"{source}#L{line_no}")})
        if status.lower() not in {"selected", "done", "rejected", "hunted"}:
            _review(reviews, "legacy queue row still requires an explicit operator decision", f"{source}#L{line_no}", f"queue {cell}: {status} ({proposed_by})")


def _findings(root: Path, nodes: list[dict[str, Any]], node_ids: dict[str, str], edges: list[dict[str, Any]], reviews: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> None:
    directory = root / "findings"
    if not directory.is_dir():
        _gap(gaps, str(directory), "missing", "legacy findings directory is not present")
        return
    for path in sorted(directory.glob("*.md")):
        if path.name in {"plan.md", "TEMPLATE-finding.md", "JOURNEY.md"}:
            continue
        slug = path.stem
        ident = "finding:" + _slug(slug)
        node_ids[slug] = ident
        fields = _front_matter(path)
        nodes.append(_node(ident, "finding", slug, _state(fields.get("status")), str(path)))
        for field, edge_type in EDGE_TYPES.items():
            for value in _values(fields.get(field)):
                target_slug = Path(value).stem
                target = node_ids.get(target_slug) or node_ids.get(_slug(target_slug))
                if target and target != ident:
                    edges.append({"id": f"edge-{ident}-{edge_type}-{_slug(target_slug)}", "from": ident, "to": target, "type": edge_type, "provenance": _prov(f"{path}#{field}")})
                else:
                    _review(reviews, f"explicit {field} reference does not resolve to a known node", f"{path}#{field}", f"{slug} {field} {value}")
        for field in ("queue_ref", "coverage_cell"):
            for value in _values(fields.get(field)):
                target = node_ids.get(("queue:" if field == "queue_ref" else "coverage:") + _slug(value)) or node_ids.get(_slug(value))
                if target:
                    edges.append({"id": f"edge-{ident}-{field}-{_slug(value)}", "from": ident, "to": target, "type": "derived-from", "provenance": _prov(f"{path}#{field}")})
                else:
                    _review(reviews, f"explicit {field} reference does not resolve to a queue or coverage node", f"{path}#{field}", f"{slug} {field} {value}")
        for value in _values(fields.get("evidence_refs", fields.get("evidence"))):
            evidence_id = "evidence:" + _slug(value)
            if not any(node["id"] == evidence_id for node in nodes):
                nodes.append(_node(evidence_id, "evidence", value, "unknown", f"{path}#evidence"))
            edges.append({"id": f"edge-{ident}-evidence-{_slug(value)}", "from": ident, "to": evidence_id, "type": "evidence-for", "provenance": _prov(f"{path}#evidence")})


def _narrative(path: Path, events: list[dict[str, Any]], reviews: list[dict[str, Any]]) -> None:
    """Extract explicit session headings without guessing links between them."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    sessions = []
    for line_no, line in enumerate(lines, 1):
        match = re.match(r"^## Session\s+(\S+)\s*(?:--\s*(.*))?$", line.strip())
        if match:
            sessions.append((match.group(1), match.group(2), line_no))
    for number, title, line_no in sessions:
        title = title or f"Session {number}"
        date = title.split(",", 1)[0].strip()
        events.append({
            "id": f"event-journey-session-{_slug(str(number))}",
            "timestamp": date or f"legacy-session-{number}",
            "actor": "unknown",
            "role": "",
            "summary": _redact(title),
            "node_ids": [],
            "provenance": _prov(f"{path}#L{line_no}"),
        })
    if lines and not sessions:
        reviews.append({
            "id": "review-journey-narrative",
            "reason": "legacy Journey narrative has no recognized session headings",
            "source_refs": [str(path)],
            "candidate": "interpret narrative manually",
            "provenance": _prov(str(path), "low", "unresolved"),
        })


def _activity(path: Path, nodes: list[dict[str, Any]], known_ids: dict[str, str], events: list[dict[str, Any]], reviews: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        _gap(gaps, str(path), "missing", "legacy source is not present")
        return
    except OSError as exc:
        _gap(gaps, str(path), "malformed", f"cannot read activity: {exc}")
        return
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            continue
        match = _LOG.match(line.strip())
        if not match:
            _gap(gaps, f"{path}#L{line_no}", "malformed", "activity line has no recognized timestamp/actor shape")
            _review(reviews, "legacy activity needs human interpretation", f"{path}#L{line_no}", _redact(line.strip()))
            continue
        timestamp, actor, role, summary = match.groups()
        refs = []
        for key, value in _KV.findall(summary):
            if key == "finding" and value in known_ids:
                refs.append(known_ids[value])
            elif key in {"finding", "queue", "queue_ref", "coverage", "coverage_cell", "challenge"} and _slug(value) in known_ids:
                refs.append(known_ids[_slug(value)])
        events.append({"id": f"event-{_slug(path.name)}-{line_no}", "timestamp": timestamp, "actor": actor, "role": role or "", "summary": _redact(summary), "node_ids": sorted(set(refs)), "provenance": _prov(f"{path}#L{line_no}")})


def derive(root: Path, engagement_type: str | None = None) -> dict[str, Any]:
    root = root.resolve()
    ctf = (root / "challenges").is_dir() or (root / "STATUS.md").is_file()
    track = engagement_type or ("ctf" if ctf else "bug-bounty")
    nodes: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    reviews: list[dict[str, Any]] = []
    node_ids: dict[str, str] = {}
    if track not in {"bug-bounty", "ctf"}:
        raise ValueError("engagement type must be bug-bounty or ctf")
    if track == "bug-bounty":
        _coverage(root, nodes, node_ids, gaps)
        _queue(root, nodes, node_ids, edges, reviews, gaps)
        _findings(root, nodes, node_ids, edges, reviews, gaps)
        activity_paths = [root / "logs" / "activity.log"]
        narrative = root / "findings" / "JOURNEY.md"
        if narrative.is_file():
            _narrative(narrative, events, reviews)
    else:
        challenge_root = root / "challenges" if (root / "challenges").is_dir() else root
        activity_paths = []
        for challenge in sorted(p for p in challenge_root.iterdir() if p.is_dir()) if challenge_root.is_dir() else []:
            status = challenge / "STATUS.md"
            if status.is_file():
                ident = "challenge:" + _slug(challenge.name)
                node_ids[challenge.name] = ident
                text = status.read_text(encoding="utf-8", errors="replace")
                state_match = re.search(r"^## State\s*$\n+([^\n]+)", text, re.MULTILINE)
                nodes.append(_node(ident, "challenge", challenge.name, _state(state_match.group(1).strip() if state_match else ""), str(status)))
            activity_paths.append(challenge / "activity.log")
        if (root / "STATUS.md").is_file():
            activity_paths.append(root / "activity.log")
    for activity_path in activity_paths:
        _activity(activity_path, nodes, node_ids, events, reviews, gaps)
    if not nodes and not events and not gaps:
        _gap(gaps, str(root), "missing", "no supported legacy records found")
    return {
        "schema_version": 1,
        "engagement": {"id": root.name, "type": track, "branch": "legacy-unverified"},
        "nodes": nodes,
        "events": events,
        "edges": edges,
        "gaps": gaps,
        "review_queue": reviews,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="engagement root to scan")
    parser.add_argument("--type", choices=("bug-bounty", "ctf"), dest="engagement_type")
    parser.add_argument("--write", action="store_true", help="write the reviewed projection to root/journey.json")
    args = parser.parse_args(argv)
    try:
        projection = derive(args.root, args.engagement_type)
        if args.write:
            (args.root / "journey.json").write_text(json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        else:
            print(json.dumps(projection, indent=2, sort_keys=True))
    except (OSError, ValueError) as exc:
        print(f"journey backpatch: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
