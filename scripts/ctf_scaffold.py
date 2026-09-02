#!/usr/bin/env python3
"""Create per-challenge CTF records from challenges/challenges.json."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


def slugify(title: str, category: str, sub_category: str | None) -> str:
    prefix = category.lower()
    if sub_category:
        prefix = f"{prefix}-{sub_category.lower()}"
    title_slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"{prefix}-{title_slug}"


def write_if_missing(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True


def challenge_files(challenge: dict[str, object]) -> dict[str, str]:
    title = str(challenge["title"])
    category = str(challenge["category"])
    sub_category = challenge.get("sub_category")
    category_display = f"{category} ({sub_category})" if sub_category else category
    artifacts = challenge.get("artifacts") or []
    artifact_lines = "\n".join(f"- `artifacts/{item}`" for item in artifacts) or "(none)"
    flag = challenge.get("flag")
    state = "solved — needs writeup" if challenge.get("solved") else "not started"
    flag_row = f"| flag1 | {flag} | (date tbd) |" if flag else "| flag1 | (not captured) | |"
    description = challenge.get("description") or "(tbd)"
    connection = challenge.get("connection") or "(none)"
    notes = challenge.get("notes") or ""

    notes_suffix = f"\n{notes}\n" if notes else ""
    return {
        "STATUS.md": (
            f"# Status — {title}\n\nLast updated: (scaffolded)\n\n"
            f"## State\n\n{state}\n\n## Blockers\n\n(none)\n\n## Flags\n\n"
            "| Label | Value | Captured (date, UTC) |\n|---|---|---|\n"
            f"{flag_row}\n\n## Recent activity\n\n(none yet)\n"
        ),
        "planning.md": (
            f"# Planning — {title}\n\n**Category:** {category_display}  \n"
            f"**Points:** {challenge.get('points', 0)}  \n"
            f"**Difficulty:** {challenge.get('difficulty', 'unknown')}  \n\n"
            f"## Description\n\n{description}\n\n## Summary\n\n(tbd)\n\n"
            f"## Scope\n\n**Connection:** {connection}  \n**Artifacts:**\n"
            f"{artifact_lines}\n\n## Approach / recon steps\n\n(tbd)\n\n"
            "## Likely vuln classes / attack surface\n\n(tbd)\n\n## Tools needed\n\n(tbd)\n"
        ),
        "notes.md": (
            f"# Notes — {title}\n\nRunning log of findings, dead ends, and things worth "
            "remembering. Not the polished report — see `report/report.md` after a flag "
            f"is captured.\n{notes_suffix}"
        ),
        "activity.log": (
            "# Activity log — <ISO8601 timestamp> [<actor>/<role>] <action>\n"
            "# actor: user | claude | codex   role: overseer | worker\n"
            "# See RULES.md. Append one line per tool run or user-confirmed action.\n"
        ),
    }


def scaffold(challenges_dir: Path, challenge: dict[str, object], dry_run: bool) -> tuple[str, bool]:
    slug = slugify(
        str(challenge["title"]), str(challenge["category"]), challenge.get("sub_category") or None
    )
    destination = challenges_dir / slug
    if destination.exists():
        return slug, False
    if dry_run:
        return slug, True

    destination.mkdir(parents=True)
    (destination / "artifacts").mkdir()
    (destination / "results").mkdir()
    (destination / "report" / "evidence").mkdir(parents=True)
    for relative_path, content in challenge_files(challenge).items():
        write_if_missing(destination / relative_path, content)
    write_if_missing(destination / "artifacts" / ".gitkeep", "")
    write_if_missing(destination / "results" / ".gitkeep", "")
    write_if_missing(destination / "report" / "evidence" / ".gitkeep", "")
    return slug, True


def write_status(root: Path, event_title: str, challenges: list[dict[str, object]]) -> None:
    by_category: dict[str, list[tuple[str, dict[str, object]]]] = defaultdict(list)
    for challenge in challenges:
        by_category[str(challenge["category"])].append(
            (slugify(str(challenge["title"]), str(challenge["category"]), challenge.get("sub_category") or None), challenge)
        )
    total = len(challenges)
    solved = sum(bool(challenge.get("solved")) for challenge in challenges)
    lines = [
        f"# Project Status — {event_title}",
        "",
        "Last updated: (scaffolded), by: scripts/ctf_scaffold.py",
        "",
        "Owned only by the overseer session. Aggregated from challenge records.",
        "",
        "## Challenges",
        "",
        f"**Total:** {total} | **Solved:** {solved} | **Remaining:** {total - solved}",
        "",
    ]
    for category in sorted(by_category):
        entries = by_category[category]
        category_solved = sum(bool(challenge.get("solved")) for _, challenge in entries)
        lines.extend([f"### {category} ({category_solved}/{len(entries)})", ""])
        for slug, challenge in entries:
            state = "solved" if challenge.get("solved") else "not started"
            sub_category = challenge.get("sub_category")
            tag = f" [{sub_category}]" if sub_category else ""
            lines.append(
                f"- `{slug}`: {state} ({challenge.get('points', 0)}pts, "
                f"{challenge.get('difficulty', 'unknown')}){tag}"
            )
        lines.append("")
    lines.extend(["## Cross-challenge notes / priorities", "", "(none yet)", ""])
    (root / "STATUS.md").write_text("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="CTF engagement root")
    parser.add_argument("--event-title", required=True, help="CTF name for root STATUS.md")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = args.root.resolve()
    challenges_dir = root / "challenges"
    data = json.loads((challenges_dir / "challenges.json").read_text())
    challenges = [item for item in data["challenges"] if item.get("title")]
    created = 0
    skipped = 0
    for challenge in challenges:
        slug, created_now = scaffold(challenges_dir, challenge, args.dry_run)
        print(f"  {'[dry-run] ' if args.dry_run else ''}{'created' if created_now else 'skipped'}: {slug}")
        created += int(created_now)
        skipped += int(not created_now)
    if not args.dry_run:
        write_status(root, args.event_title, challenges)
    print(f"\n{'[dry-run] ' if args.dry_run else ''}Done: {created} created, {skipped} already existed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
