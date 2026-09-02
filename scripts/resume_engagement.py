#!/usr/bin/env python3
"""Resume a paused engagement: merge main for harness updates, flip status.

Usage:
    python3 scripts/resume_engagement.py <branch-name>
    python3 scripts/resume_engagement.py <branch-name> --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], *, check: bool = True, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def read_version(ref: str, path: str = "HARNESS_VERSION") -> str:
    try:
        result = run(["git", "show", f"{ref}:{path}"])
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "(absent)"


def read_changelog_delta(old_ver: str, new_ver: str) -> str:
    try:
        result = run(["git", "show", "main:HARNESS_CHANGELOG.md"])
    except subprocess.CalledProcessError:
        return ""
    lines = result.stdout.splitlines()
    collecting = False
    delta: list[str] = []
    for line in lines:
        if line.startswith("## ") and old_ver not in line:
            collecting = True
        elif line.startswith("## ") and old_ver in line:
            break
        if collecting:
            delta.append(line)
    return "\n".join(delta) if delta else ""


def get_engagements(root: Path) -> list[dict]:
    eng_file = root / "ENGAGEMENTS.md"
    if not eng_file.exists():
        return []
    text = eng_file.read_text()
    try:
        return json.loads(text.split("| Name |")[0].strip()) if text.strip().startswith("[") else []
    except (json.JSONDecodeError, IndexError):
        pass
    entries = []
    for line in text.splitlines():
        if line.startswith("|") and "---" not in line and "Name" not in line:
            cols = [c.strip() for c in line.split("|")[1:-1]]
            if len(cols) >= 6:
                entries.append({
                    "Name": cols[0], "Type": cols[1],
                    "Branch": cols[2].strip("`"), "Status": cols[3],
                    "Created": cols[4], "Description": cols[5],
                })
    return entries


def find_engagement(root: Path, branch: str) -> dict | None:
    for eng in get_engagements(root):
        if eng["Branch"] == branch:
            return eng
    return None


def branch_exists(branch: str) -> bool:
    result = run(["git", "branch", "--list", branch], check=False)
    return bool(result.stdout.strip())


def current_branch() -> str:
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", help="engagement branch to resume")
    parser.add_argument("--dry-run", action="store_true", help="preview without changes")
    parser.add_argument("--skip-status-update", action="store_true",
                        help="skip ENGAGEMENTS.md status flip (useful for periodic sync)")
    args = parser.parse_args()

    root = Path(run(["git", "rev-parse", "--show-toplevel"]).stdout.strip())

    if not branch_exists(args.branch):
        print(f"error: branch '{args.branch}' does not exist", file=sys.stderr)
        return 1

    eng = find_engagement(root, args.branch)
    if eng and eng["Status"].lower() not in ("paused", "active"):
        print(f"warning: engagement status is '{eng['Status']}', not Paused", file=sys.stderr)

    old_ver = read_version(args.branch)
    new_ver = read_version("main")
    print(f"Harness version: {old_ver} (branch) → {new_ver} (main)")

    if old_ver == new_ver:
        print("Already up to date — no harness changes to merge.")
    else:
        delta = read_changelog_delta(old_ver, new_ver)
        if delta:
            print(f"\nChangelog delta:\n{delta}\n")

    if args.dry_run:
        print("[dry-run] would:")
        print(f"  1. git checkout {args.branch}")
        print(f"  2. git merge main --no-edit")
        if not args.skip_status_update and eng:
            print(f"  3. update ENGAGEMENTS.md: {eng['Status']} → Active")
        print(f"  4. run engagement_guard.py preflight")
        print("\nResume checklist:")
        print("  - Read findings/plan.md for current status")
        print("  - Read findings/signals.md for pending signals")
        print("  - Read logs/activity.log for last actions")
        return 0

    if current_branch() != args.branch:
        print(f"Switching to {args.branch}...")
        run(["git", "checkout", args.branch])

    if old_ver != new_ver:
        print("Merging main for harness updates...")
        result = run(["git", "merge", "main", "--no-edit"], check=False)
        if result.returncode != 0:
            print("Merge conflicts detected. Resolve them, then run:", file=sys.stderr)
            print(f"  git add -A && git commit", file=sys.stderr)
            print(f"  python3 scripts/resume_engagement.py {args.branch} --skip-status-update", file=sys.stderr)
            return 1
        actual = read_version("HEAD")
        print(f"Harness updated: {old_ver} → {actual}")

    if not args.skip_status_update and eng and eng["Status"].lower() == "paused":
        print("\nTo update ENGAGEMENTS.md status, switch to main and edit manually")
        print(f"(engagement data must not be committed on main).")

    guard = root / "scripts" / "engagement_guard.py"
    if guard.exists():
        print("\nRunning preflight check...")
        run([sys.executable, str(guard), "preflight"], check=False)

    print("\n--- Resume checklist ---")
    print("  1. Read findings/plan.md for current status")
    print("  2. Read findings/signals.md for pending signals")
    print("  3. Read logs/activity.log for last actions")
    print(f"  4. Check HARNESS_VERSION: {read_version('HEAD')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
