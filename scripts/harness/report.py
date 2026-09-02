#!/usr/bin/env python3
"""Generate a compact harness coverage and finding-status report."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path


def front_matter(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    result = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip().strip("'\"")
    return result


def finding_status(path: Path) -> str:
    fields = front_matter(path)
    if fields.get("status"):
        return fields["status"]
    for line in path.read_text().splitlines():
        match = re.match(r"- \*\*Status:\*\*\s*(.+)", line)
        if match:
            return match.group(1).split("/")[0].strip()
    return "unknown"


def queue_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) == 4 and cells[0] != "Cell (area / attack-class)":
            rows.append(cells)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=Path("harness/coverage.json"))
    parser.add_argument("--findings-dir", type=Path, default=Path("findings"))
    parser.add_argument("--queue", type=Path, default=Path("harness/queue.md"))
    parser.add_argument("--output", type=Path, default=Path("harness/report.md"))
    args = parser.parse_args()

    coverage = json.loads(args.coverage.read_text()) if args.coverage.exists() else {"areas": {}}
    areas = coverage.get("areas", {})
    cells = [cell for area in areas.values() for cell in area.get("cells", {}).values()]
    status_counts = Counter(cell.get("status", "unknown") for cell in cells)
    complete = sum(status_counts[status] for status in ("hunted", "validated", "rejected", "duplicate", "reported", "n_a"))

    finding_exclusions = {"TEMPLATE-finding.md", "plan.md"}
    findings = [
        path for path in sorted(args.findings_dir.glob("*.md"))
        if path.name not in finding_exclusions
    ] if args.findings_dir.exists() else []
    severity_counts = Counter(front_matter(path).get("severity", "unspecified") for path in findings)
    finding_statuses = Counter(finding_status(path) for path in findings)
    open_queue = [row for row in queue_rows(args.queue) if row[3].lower() not in {"rejected", "done"}]

    lines = [
        "# Harness report",
        "",
        f"Generated: {datetime.now(UTC).replace(microsecond=0).isoformat().replace('+00:00', 'Z')}",
        "",
        "## Coverage",
        "",
        f"Completed cells: {complete}/{len(cells)}",
        "",
        "| Status | Cells |",
        "|---|---:|",
    ]
    lines.extend(f"| {status} | {count} |" for status, count in sorted(status_counts.items()))
    lines.extend(["", "## Area coverage", "", "| Area | Surface | Attack class | Status | Stage | Last run |", "|---|---|---|---|---|---|"])
    for area_id, area in sorted(areas.items()):
        for attack_class, cell in sorted(area.get("cells", {}).items()):
            lines.append(
                f"| {area_id} | {area.get('surface', 'unknown')} | {attack_class} | "
                f"{cell.get('status', 'unknown')} | {cell.get('stage', 'unknown')} | "
                f"{cell.get('last_run', '')} |"
            )

    lines.extend(["", "## Findings", "", "| Severity | Findings |", "|---|---:|"])
    lines.extend(f"| {severity} | {count} |" for severity, count in sorted(severity_counts.items()))
    lines.extend(["", "| Status | Findings |", "|---|---:|"])
    lines.extend(f"| {status} | {count} |" for status, count in sorted(finding_statuses.items()))

    lines.extend(["", "## Open queue", "", "| Cell (area / attack-class) | Proposed by | Reason | Status |", "|---|---|---|---|"])
    lines.extend(f"| {' | '.join(row)} |" for row in open_queue)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
