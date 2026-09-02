#!/usr/bin/env python3
"""Validate that a promoted finding has its required review records."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from validate_schema import BASE_FIELDS, DOMAIN_FIELDS, front_matter, is_placeholder


PROMOTION_STATUSES = {"confirmed", "submitted"}
COMPLETE_CELL_STATUSES = {"validated", "reported"}
COMPLETE_QUEUE_STATUSES = {"selected", "done"}
REQUIRED_SECTIONS = ("Summary", "Reproduction steps", "Impact")
REQUIRED_SIGNOFFS = (
    "In scope per scope.md",
    "Not a known/duplicate issue",
    "Reproducible steps confirmed",
    "Evidence attached",
)
PLACEHOLDER_MARKERS = ("<", "{{", "(tbd)", "yes/no", "one or two sentences")


def body(path: Path) -> str:
    lines = path.read_text().splitlines()
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing YAML front-matter delimiter") from exc
    return "\n".join(lines[end + 1 :])


def section(content: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$([\s\S]*?)(?=^## |\Z)",
        content,
        re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def is_substantive(value: str) -> bool:
    normalized = value.strip().casefold()
    if len(normalized) < 12 or any(marker in normalized for marker in PLACEHOLDER_MARKERS):
        return False
    return bool(re.search(r"[a-z0-9]", normalized))


def schema_errors(fields: dict[str, str]) -> list[str]:
    errors = [
        f"missing or placeholder {field}"
        for field in BASE_FIELDS
        if is_placeholder(fields.get(field))
    ]
    domain = fields.get("domain", "")
    if domain not in DOMAIN_FIELDS:
        return errors + [f"domain must be one of: {', '.join(DOMAIN_FIELDS)}"]
    errors.extend(
        f"missing or placeholder {field}"
        for field in DOMAIN_FIELDS[domain]
        if is_placeholder(fields.get(field))
    )
    if fields.get("slug") and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", fields["slug"]):
        errors.append("slug must use lowercase letters, digits, and hyphens")
    return errors


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evidence_files(evidence_dir: Path) -> list[Path]:
    manifest = evidence_dir / "manifest.json"
    return sorted(path for path in evidence_dir.rglob("*") if path.is_file() and path != manifest)


def write_manifest(evidence_dir: Path) -> list[str]:
    files = evidence_files(evidence_dir)
    if not files:
        return [f"no curated evidence files in {evidence_dir}"]
    manifest = {
        "version": 1,
        "files": {str(path.relative_to(evidence_dir)): digest(path) for path in files},
    }
    (evidence_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return []


def validate_manifest(evidence_dir: Path) -> list[str]:
    manifest_path = evidence_dir / "manifest.json"
    if not manifest_path.is_file():
        return [f"missing evidence manifest: {manifest_path}"]
    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        return [f"invalid evidence manifest: {exc.msg}"]
    entries = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(entries, dict):
        return ["evidence manifest must contain an object named files"]

    actual = {str(path.relative_to(evidence_dir)): path for path in evidence_files(evidence_dir)}
    errors = []
    for name, expected_hash in entries.items():
        path = actual.get(name)
        if path is None:
            errors.append(f"evidence manifest lists missing file: {name}")
        elif not isinstance(expected_hash, str) or digest(path) != expected_hash:
            errors.append(f"evidence hash mismatch: {name}")
    for name in sorted(set(actual) - set(entries)):
        errors.append(f"evidence manifest omits file: {name}")
    if not actual:
        errors.append(f"no curated evidence files in {evidence_dir}")
    return errors


def queue_rows(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0] != "Cell (area / attack-class)":
            rows.append((cells[0], cells[3].casefold()))
    return rows


def scope_has_in_scope_item(path: Path) -> bool:
    if not path.is_file():
        return False
    content = path.read_text()
    value = section(content, "In scope")
    return any(
        line.startswith("- ")
        and is_substantive(line[2:])
        and "list explicitly" not in line.casefold()
        for line in value.splitlines()
    )


def readiness_errors(
    finding: Path,
    coverage_path: Path,
    queue_path: Path,
    activity_path: Path,
    scope_path: Path,
    *,
    write_evidence_manifest: bool = False,
) -> list[str]:
    try:
        fields = front_matter(finding)
        content = body(finding)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    errors = schema_errors(fields)
    status = fields.get("status", "").casefold()
    if status not in PROMOTION_STATUSES:
        return errors

    for heading in REQUIRED_SECTIONS:
        if not is_substantive(section(content, heading)):
            errors.append(f"missing or placeholder {heading} section")

    prior_art = section(content, "Prior-art check")
    for source in ("Exploit-DB", "NVD/CVE", "GitHub"):
        match = re.search(
            rf"^- {re.escape(source)}[^:]*:\s*(yes|no)\s*(?:--|—)\s*result:\s*(.+)$",
            prior_art,
            re.IGNORECASE | re.MULTILINE,
        )
        if not match or not is_substantive(match.group(2)):
            errors.append(f"missing substantive prior-art result for {source}")

    checked = {
        match.group(1).strip()
        for match in re.finditer(r"^- \[x\] (.+)$", section(content, "Overseer sign-off"), re.MULTILINE | re.IGNORECASE)
    }
    for item in REQUIRED_SIGNOFFS:
        if item not in checked:
            errors.append(f"missing completed sign-off: {item}")
    if status == "submitted" and not any(item.startswith("Ready to submit") for item in checked):
        errors.append("missing completed sign-off: Ready to submit")

    discovered_by = fields.get("discovered_by", "")
    if is_placeholder(discovered_by):
        errors.append("missing or placeholder discovered_by")
    reviewer = fields.get("reviewed_by", "")
    if is_placeholder(reviewer):
        errors.append("missing or placeholder reviewed_by")
    elif reviewer.casefold() == discovered_by.casefold():
        errors.append("reviewed_by must differ from discovered_by")
    if fields.get("reviewer_role", "").casefold() != "overseer":
        errors.append("reviewer_role must be overseer")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", fields.get("reviewed_at", "")):
        errors.append("reviewed_at must be ISO8601 UTC (YYYY-MM-DDTHH:MM:SSZ)")

    slug = fields.get("slug", "")
    evidence_dir = finding.parent / "evidence" / slug
    if write_evidence_manifest and evidence_dir.is_dir():
        errors.extend(write_manifest(evidence_dir))
    elif write_evidence_manifest:
        errors.append(f"missing evidence directory: {evidence_dir}")
    if evidence_dir.is_dir():
        errors.extend(validate_manifest(evidence_dir))
    else:
        errors.append(f"missing evidence directory: {evidence_dir}")

    try:
        coverage = json.loads(coverage_path.read_text())
        cell = coverage["areas"][fields["area"]]["cells"][fields["attack_class"]]
        if cell.get("finding_slug") != slug:
            errors.append("coverage cell finding_slug does not match finding slug")
        if cell.get("status") not in COMPLETE_CELL_STATUSES:
            errors.append("coverage cell status must be validated or reported")
    except (OSError, KeyError, TypeError, json.JSONDecodeError):
        errors.append("missing matching coverage cell")

    queue_ref = fields.get("queue_ref", "")
    expected_ref = f"{fields.get('area', '')} / {fields.get('attack_class', '')}"
    if queue_ref != expected_ref:
        errors.append("queue_ref must equal area / attack_class")
    elif (queue_ref, "selected") not in queue_rows(queue_path) and (queue_ref, "done") not in queue_rows(queue_path):
        errors.append("missing selected or done queue row for queue_ref")

    if not scope_has_in_scope_item(scope_path):
        errors.append("scope.md lacks a substantive In scope item")
    expected_activity = (f"finding={slug}", f"reviewer={reviewer}", f"decision={status}")
    if not activity_path.is_file() or not any(
        all(token in line for token in expected_activity)
        for line in activity_path.read_text().splitlines()
    ):
        errors.append("missing structured reviewer activity entry")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("finding", type=Path)
    parser.add_argument("--coverage", type=Path, default=Path("harness/coverage.json"))
    parser.add_argument("--queue", type=Path, default=Path("harness/queue.md"))
    parser.add_argument("--activity", type=Path, default=Path("logs/activity.log"))
    parser.add_argument("--scope", type=Path, default=Path("scope.md"))
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args(argv)

    errors = readiness_errors(
        args.finding,
        args.coverage,
        args.queue,
        args.activity,
        args.scope,
        write_evidence_manifest=args.write_manifest,
    )
    if errors:
        print(f"INVALID: {args.finding}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"READY: {args.finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
