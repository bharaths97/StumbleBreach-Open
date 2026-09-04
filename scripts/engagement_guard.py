#!/usr/bin/env python3
"""Non-destructive branch guard for StumbleBreach engagement data."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


# Root-level data paths created by the CTF and bug-bounty templates. Keep this
# deliberately narrow: architecture paths are always permitted.
ENGAGEMENT_PATHS = (
    "scope.md", "config/", "findings/", "logs/", "references/",
    "challenges/", "STATUS.md", "planning/", "scripts/poc/",
)
ARCHITECTURE_EXAMPLES = (
    "dashboard/", "docs/", "plans/", "templates/", "tools_mcp/",
    "harness/", "scripts/",
)
FRAMEWORK_PATHS = ("roles/", "templates/", "scripts/")
HUB_WORK_BRANCH_RE = re.compile(r"^(?:feat|patch)-[a-z0-9]+(?:-[a-z0-9]+){1,2}$")
SECRET_SUFFIXES = (".env", ".pem", ".key", ".p12")
LOCAL_STATE_ROOTS = {
    ".agents/", ".claude/", ".codex/", ".mcp.json", ".vscode/",
    ".DS_Store", "tools-env/",
}
LEFTOVER_ENGAGEMENT_ROOTS = set(ENGAGEMENT_PATHS)
SUSPICIOUS_TOOL_STATE = (
    "tools-env/scratch",
)


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, text=True, stdout=subprocess.PIPE
    ).stdout


def branch() -> str:
    return git("branch", "--show-current").strip()


def is_hub_work_branch(name: str) -> bool:
    """Return whether name follows the tracked hub-work branch convention."""
    return bool(HUB_WORK_BRANCH_RE.fullmatch(name))


def is_engagement_path(path: str) -> bool:
    normalized = PurePosixPath(path).as_posix()
    return any(
        normalized == protected.rstrip("/") or normalized.startswith(protected)
        for protected in ENGAGEMENT_PATHS
    )


def staged_paths() -> list[str]:
    output = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"],
        check=True, stdout=subprocess.PIPE,
    ).stdout
    return [path.decode("utf-8", "surrogateescape") for path in output.split(b"\0") if path]


def is_secret_path(path: str) -> bool:
    normalized = PurePosixPath(path).as_posix().lower()
    return not normalized.endswith(".env.example") and normalized.endswith(SECRET_SUFFIXES)


def ignored_paths() -> list[str]:
    status = git("status", "--porcelain=v1", "--ignored", "--untracked-files=normal")
    return [line[3:] for line in status.splitlines() if line.startswith("!! ")]


def hygiene() -> int:
    ordinary = git("status", "--porcelain=v1", "--untracked-files=all")
    if ordinary:
        print("engagement guard: ordinary uncommitted files require review:\n" + ordinary, file=sys.stderr)
        return 1

    current = branch()
    flagged: list[str] = []
    for path in ignored_paths():
        normalized = PurePosixPath(path).as_posix()
        if current == "main" and any(
            normalized == root.rstrip("/") or normalized.startswith(root)
            for root in LEFTOVER_ENGAGEMENT_ROOTS
        ):
            flagged.append(normalized)
    for path in SUSPICIOUS_TOOL_STATE:
        if Path(path).exists():
            flagged.append(path)

    if flagged:
        print("engagement guard: local engagement or recon data needs ownership review:", file=sys.stderr)
        for path in sorted(set(flagged)):
            print(f"  - {path}", file=sys.stderr)
        print("Commit non-secret evidence to its owning branch or explicitly archive/delete it.", file=sys.stderr)
        return 1

    local_state = [path for path in ignored_paths() if path in LOCAL_STATE_ROOTS]
    if local_state:
        print("engagement guard: only approved local operating state is present")
    else:
        print("engagement guard: workspace hygiene passed")
    return 0


def registry_branches() -> set[str]:
    try:
        registry = git("show", "main:ENGAGEMENTS.md")
    except subprocess.CalledProcessError:
        return set()
    branches: set[str] = set()
    for line in registry.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) >= 5 and cells[0] == "" and cells[3].startswith("`"):
            branches.add(cells[3].strip("`"))
    return branches


def precommit() -> int:
    staged = staged_paths()
    secrets = [path for path in staged if is_secret_path(path)]
    if secrets:
        print("engagement guard: refusing staged secret-like file(s):", file=sys.stderr)
        for path in secrets:
            print(f"  - {path}", file=sys.stderr)
        return 1
    current = branch()
    if current != "main" and not is_hub_work_branch(current):
        framework = [
            path for path in staged
            if any(PurePosixPath(path).as_posix().startswith(fw) for fw in FRAMEWORK_PATHS)
        ]
        if framework:
            print("engagement guard: WARNING — framework files edited on a non-main branch:", file=sys.stderr)
            for path in framework:
                print(f"  - {path}", file=sys.stderr)
            print(
                "These changes cannot merge back to main and will be overwritten by "
                "`git merge main`. Edit framework files on main instead, then backpatch.",
                file=sys.stderr,
            )
        return 0
    blocked = [path for path in staged if is_engagement_path(path)]
    if not blocked:
        return 0
    print("engagement guard: refusing engagement data on main:", file=sys.stderr)
    for path in blocked:
        print(f"  - {path}", file=sys.stderr)
    print(
        "Commit this data on its registered CTF/bug-bounty branch instead. "
        "Architecture paths remain allowed: " + ", ".join(ARCHITECTURE_EXAMPLES),
        file=sys.stderr,
    )
    return 1


def preflight() -> int:
    current = branch()
    if current == "main":
        print("engagement guard: main is the hub control branch")
        return hygiene()
    if current in registry_branches():
        print(f"engagement guard: {current} is registered on main")
        return hygiene()
    print(
        f"engagement guard: {current!r} is not in main:ENGAGEMENTS.md; "
        "use a registered engagement branch or update the registry on main.",
        file=sys.stderr,
    )
    return 1


def closeout() -> int:
    if preflight():
        return 1
    dirty = git("status", "--porcelain")
    if dirty:
        print("engagement guard: worktree is not clean:\n" + dirty, file=sys.stderr)
        return 1
    print("engagement guard: close-out preflight passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("pre-commit", "preflight", "closeout", "hygiene"))
    command = parser.parse_args().command
    return {"pre-commit": precommit, "preflight": preflight, "closeout": closeout, "hygiene": hygiene}[command]()


if __name__ == "__main__":
    raise SystemExit(main())
