#!/usr/bin/env python3
"""Backpatch ``main`` into an engagement branch safely and idempotently.

The command is deliberately limited to the framework merge. It does not reset
engagement data or change ``ENGAGEMENTS.md``; the planner owns registry status
and reset is a separate, explicitly reviewed operation.

Usage:
    python3 scripts/resume_engagement.py <branch-name> [--dry-run]
    python3 scripts/resume_engagement.py <branch-name> --allow-closed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


FRAMEWORK_PREFIXES = ("roles/", "scripts/", "templates/", ".githooks/")
FRAMEWORK_ROOT_FILES = (
    "AGENTS.md",
    "CLAUDE.md",
    "RULES.md",
    "HARNESS_VERSION",
    "HARNESS_CHANGELOG.md",
)
STALE_FRAMEWORK_PREFIXES = ("templates/bugbounty/harness/scripts/",)
RUNTIME_SKILL_LINKS = (".claude/skills", ".agents/skills")
AUTO_RESOLVE_PREFIXES = (
    ".githooks/",
    "dashboard/",
    "docs/",
    "internal-docs/",
    "plans/",
    "profiles/",
    "roles/",
    "roles-example/",
    "scripts/",
    "templates/",
    "tools_mcp/",
    "harness/scripts/",
)
MANUAL_RESOLVE_PREFIXES = (
    "challenges/",
    "config/",
    "findings/",
    "harness/",
    "logs/",
    "planning/",
    "references/",
    "scripts/poc/",
    "scope.md",
    "STATUS.md",
)
AUTO_RESOLVE_ROOT_FILES = {
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "ENGAGEMENTS.md",
    "HARNESS_CHANGELOG.md",
    "HARNESS_VERSION",
    "LICENSE",
    "README.md",
    "RULES.md",
    "SECURITY.md",
}


def git(root: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode, result.args, result.stdout, result.stderr
        )
    return result.stdout


def git_action(root: Path, *args: str) -> int:
    return subprocess.run(["git", *args], cwd=root, text=True).returncode


def read_version(root: Path, ref: str) -> str:
    try:
        return git(root, "show", f"{ref}:HARNESS_VERSION").strip()
    except subprocess.CalledProcessError:
        return "(absent)"


def tracked_framework_files(root: Path, ref: str) -> set[str]:
    paths = set(
        git(root, "ls-tree", "-r", "--name-only", ref, "--", *FRAMEWORK_PREFIXES)
        .splitlines()
    )
    for path in FRAMEWORK_ROOT_FILES:
        try:
            git(root, "cat-file", "-e", f"{ref}:{path}")
        except subprocess.CalledProcessError:
            continue
        paths.add(path)
    return paths


def blob_id(root: Path, ref: str, path: str) -> str | None:
    try:
        return git(root, "rev-parse", f"{ref}:{path}").strip()
    except subprocess.CalledProcessError:
        return None


def compatibility_report(root: Path, branch: str, main_ref: str = "main") -> dict[str, object]:
    """Return framework drift without changing the worktree."""

    main_files = tracked_framework_files(root, main_ref)
    branch_files = tracked_framework_files(root, branch)
    missing = sorted(main_files - branch_files)
    changed = sorted(
        path
        for path in main_files & branch_files
        if blob_id(root, main_ref, path) != blob_id(root, branch, path)
    )
    stale = sorted(
        path
        for path in branch_files
        if any(path.startswith(prefix) for prefix in STALE_FRAMEWORK_PREFIXES)
    )
    return {
        "branch": branch,
        "main": main_ref,
        "branch_version": read_version(root, branch),
        "main_version": read_version(root, main_ref),
        "missing": missing,
        "changed": changed,
        "stale": stale,
    }


def report_has_drift(report: dict[str, object]) -> bool:
    return bool(
        report["branch_version"] != report["main_version"]
        or report["missing"]
        or report["changed"]
        or report["stale"]
    )


def local_runtime_warnings(root: Path) -> list[str]:
    warnings: list[str] = []
    for relative in RUNTIME_SKILL_LINKS:
        path = root / relative
        if not path.exists() and not path.is_symlink():
            warnings.append(f"{relative} is absent; run workspace initialization")
        elif path.is_symlink() and not path.resolve().exists():
            warnings.append(f"{relative} is dangling: {path.readlink()}")
    return warnings


def local_runtime_errors(root: Path) -> list[str]:
    return [warning for warning in local_runtime_warnings(root) if "dangling" in warning]


def print_report(report: dict[str, object], *, runtime_warnings: list[str] | None = None) -> None:
    print(
        f"Harness version: {report['branch_version']} (branch) "
        f"-> {report['main_version']} (main)"
    )
    for key, label in (
        ("missing", "Missing framework files"),
        ("changed", "Framework files differing from main"),
        ("stale", "Stale framework paths"),
    ):
        values = report[key]
        if values:
            print(f"[FAIL] {label}:")
            for value in values:
                print(f"  - {value}")
    if report["branch_version"] != report["main_version"]:
        print("[FAIL] HARNESS_VERSION differs from main")
    if not report_has_drift(report):
        print("[OK] Framework is already compatible with main; no merge needed.")
    for warning in runtime_warnings or []:
        print(f"[WARN] {warning}")


def get_engagement_status(root: Path, branch: str) -> str | None:
    try:
        text = git(root, "show", "main:ENGAGEMENTS.md")
    except subprocess.CalledProcessError:
        return None
    for line in text.splitlines():
        if not line.startswith("|") or "---" in line:
            continue
        columns = [column.strip().strip("`") for column in line.split("|")[1:-1]]
        if len(columns) >= 4 and columns[2] == branch:
            return columns[3]
    return None


def worktree_is_clean(root: Path) -> bool:
    return not git(root, "status", "--porcelain=v1", "--untracked-files=all").strip()


def read_changelog_delta(root: Path, old_version: str) -> str:
    try:
        lines = git(root, "show", "main:HARNESS_CHANGELOG.md").splitlines()
    except subprocess.CalledProcessError:
        return ""
    collecting = False
    delta: list[str] = []
    for line in lines:
        if line.startswith("## ") and old_version not in line:
            collecting = True
        elif line.startswith("## ") and old_version in line:
            break
        if collecting:
            delta.append(line)
    return "\n".join(delta).strip()


def current_branch(root: Path) -> str:
    return git(root, "branch", "--show-current").strip()


def unmerged_paths(root: Path) -> list[str]:
    return sorted(
        path
        for path in git(root, "diff", "--name-only", "--diff-filter=U").splitlines()
        if path
    )


def is_auto_resolvable(path: str) -> bool:
    if path in AUTO_RESOLVE_ROOT_FILES:
        return True
    if path.startswith("harness/scripts/"):
        return True
    if any(path.startswith(prefix) for prefix in MANUAL_RESOLVE_PREFIXES):
        return False
    return any(path.startswith(prefix) for prefix in AUTO_RESOLVE_PREFIXES)


def resolve_safe_conflicts(root: Path, paths: list[str]) -> list[str]:
    """Resolve only paths where the documented main-wins policy is safe."""

    manual = [path for path in paths if not is_auto_resolvable(path)]
    for path in paths:
        if path in manual:
            continue
        if blob_id(root, "main", path) is None:
            result = subprocess.run(
                ["git", "rm", "-f", "--ignore-unmatch", "--", path],
                cwd=root,
                text=True,
            )
        else:
            result = subprocess.run(
                ["git", "checkout", "--theirs", "--", path],
                cwd=root,
                text=True,
            )
        if result.returncode:
            continue
        if git_action(root, "add", "-A", "--", path):
            continue
    return sorted(set(manual))


def finish_conflicted_merge(root: Path, *, auto_resolve: bool) -> int:
    paths = unmerged_paths(root)
    if not paths:
        return 0
    if not auto_resolve:
        print("Manual merge resolution required for:", file=sys.stderr)
        for path in paths:
            print(f"  - {path}", file=sys.stderr)
        return 1
    manual = resolve_safe_conflicts(root, paths)
    remaining = unmerged_paths(root)
    if manual or remaining:
        print(
            "Backpatch stopped. Resolve these engagement/ambiguous conflicts manually, "
            "then stage and commit the merge:",
            file=sys.stderr,
        )
        for path in sorted(set(manual + remaining)):
            print(f"  - {path}", file=sys.stderr)
        return 1
    print("Only main-owned framework conflicts found; completing the merge.")
    return git_action(root, "commit", "--no-edit")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("branch", help="local engagement branch to backpatch")
    parser.add_argument("--dry-run", action="store_true", help="report without switching or merging")
    parser.add_argument(
        "--allow-closed",
        action="store_true",
        help="allow framework backpatch of a Closed registry entry; does not reopen it",
    )
    parser.add_argument(
        "--no-auto-resolve",
        action="store_true",
        help="leave all merge conflicts for manual resolution",
    )
    args = parser.parse_args(argv)

    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    if not git(root, "branch", "--list", args.branch).strip():
        print(f"error: branch {args.branch!r} does not exist locally", file=sys.stderr)
        return 1
    if args.branch == "main":
        print("error: backpatch target must be an engagement branch", file=sys.stderr)
        return 1

    status = get_engagement_status(root, args.branch)
    if status == "Closed" and not args.allow_closed:
        print(
            "error: engagement is Closed; pass --allow-closed after explicitly authorizing a restart",
            file=sys.stderr,
        )
        return 1
    if status is None:
        print(f"warning: {args.branch} is not registered in main:ENGAGEMENTS.md", file=sys.stderr)

    report = compatibility_report(root, args.branch)
    runtime_warnings = local_runtime_warnings(root) if current_branch(root) == args.branch else []
    print_report(report, runtime_warnings=runtime_warnings)
    if report["stale"]:
        print(
            "error: remove stale framework paths explicitly before backpatching; "
            "the merge must not silently delete files",
            file=sys.stderr,
        )
        return 1
    if not report_has_drift(report):
        if local_runtime_errors(root):
            print("error: local skill links are dangling; repair workspace initialization", file=sys.stderr)
            return 1
        return 0
    if args.dry_run:
        print(f"[dry-run] would switch to {args.branch} and merge main")
        return 0

    if current_branch(root) != args.branch and not worktree_is_clean(root):
        print("error: current worktree is dirty; commit or safely preserve it first", file=sys.stderr)
        return 1
    if current_branch(root) != args.branch:
        print(f"Switching to {args.branch}...")
        if git_action(root, "switch", args.branch):
            return 1

    old_version = read_version(root, "HEAD")
    print("Merging main for the framework backpatch...")
    merge_result = git_action(root, "merge", "main", "--no-edit")
    if merge_result and not unmerged_paths(root):
        print("Backpatch stopped: git merge failed without a resolvable conflict.", file=sys.stderr)
        return 1
    if merge_result and finish_conflicted_merge(root, auto_resolve=not args.no_auto_resolve):
        print(
            "Backpatch stopped. Resolve the merge, then rerun this command; "
            "no reset was performed.",
            file=sys.stderr,
        )
        return 1

    after = compatibility_report(root, args.branch)
    print_report(after, runtime_warnings=local_runtime_warnings(root))
    if report_has_drift(after) or local_runtime_errors(root):
        print(
            "error: post-merge compatibility check failed; inspect the listed framework drift",
            file=sys.stderr,
        )
        return 1
    delta = read_changelog_delta(root, old_version)
    if delta:
        print(f"\nHarness changelog delta:\n{delta}")
    print("Backpatch complete. Registry status was not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
