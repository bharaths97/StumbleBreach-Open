#!/usr/bin/env python3
"""Initialize harness state for an already-created bug-bounty engagement.

This does not create Git branches or update the private engagement registry.
Run it from a branch that was instantiated from ``templates/bugbounty``.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def target_env_value(path: Path, key: str) -> str:
    if not path.exists():
        return ""
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.partition("=")[2].strip()
    return ""


def initialise_target_env(root: Path, surfaces: list[str], dry_run: bool) -> None:
    target_env = root / "config" / "target.env"
    example = root / "config" / "target.env.example"
    if target_env.exists():
        if target_env_value(target_env, "TARGET_SURFACES"):
            return
        raise ValueError(
            f"{target_env} already exists but TARGET_SURFACES is blank; "
            "set it explicitly before running the scaffold again"
        )
    if not example.exists():
        raise ValueError(f"missing template configuration: {example}")
    if dry_run:
        print(f"[dry-run] would create {target_env} with TARGET_SURFACES={','.join(surfaces)}")
        return
    target_env.parent.mkdir(parents=True, exist_ok=True)
    content = example.read_text()
    content = content.replace("TARGET_SURFACES=", f"TARGET_SURFACES={','.join(surfaces)}", 1)
    target_env.write_text(content)
    print(f"created {target_env} (ignored local placeholder configuration)")


def copy_harness_version(root: Path, dry_run: bool) -> None:
    """Copy HARNESS_VERSION from the repo root (main's version) into the engagement."""
    repo_root = Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        check=True, capture_output=True, text=True,
    ).stdout.strip())
    src = repo_root / "HARNESS_VERSION"
    dst = root / "HARNESS_VERSION"
    if not src.exists():
        return
    if dst.exists():
        return
    if dry_run:
        print(f"[dry-run] would copy {src} → {dst}")
        return
    dst.write_text(src.read_text())
    print(f"copied HARNESS_VERSION ({src.read_text().strip()}) into engagement")


def validate_layout(root: Path, surfaces: list[str]) -> None:
    required = ("scope.md", "findings/plan.md", "harness/coverage.json", "harness/queue.md")
    missing = [str(root / path) for path in required if not (root / path).exists()]
    if missing:
        raise ValueError(
            "not a bug-bounty engagement created from templates/bugbounty; missing: "
            + ", ".join(missing)
        )
    missing_adapters = [surface for surface in surfaces if not (root / "harness" / "adapters" / f"{surface}.md").exists()]
    if missing_adapters:
        raise ValueError(f"no adapter for surface(s): {', '.join(missing_adapters)}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."), help="bug-bounty engagement root")
    parser.add_argument(
        "--surface",
        action="append",
        required=True,
        choices=("web", "blockchain", "binary"),
        help="adapter to seed; repeat for a mixed engagement",
    )
    parser.add_argument(
        "--area",
        action="append",
        required=True,
        help="SURFACE:ID=DESCRIPTION or ID=DESCRIPTION (uses the first surface); repeatable",
    )
    parser.add_argument("--dry-run", action="store_true", help="validate and show the coverage command without writing")
    args = parser.parse_args()

    root = args.root.resolve()
    surfaces = list(dict.fromkeys(args.surface))
    try:
        validate_layout(root, surfaces)
        copy_harness_version(root, args.dry_run)
        initialise_target_env(root, surfaces, args.dry_run)
        configured_surfaces = {
            value.strip() for value in target_env_value(root / "config" / "target.env", "TARGET_SURFACES").split(",") if value.strip()
        }
        if not args.dry_run and not set(surfaces).issubset(configured_surfaces):
            parser.error(
                "selected adapter(s) are not declared in config/target.env TARGET_SURFACES; "
                "update the local configuration explicitly before continuing"
            )
    except ValueError as exc:
        parser.error(str(exc))

    coverage_init = Path(__file__).resolve().parent / "harness" / "coverage_init.py"
    command = [
        sys.executable,
        str(coverage_init),
        "--scope",
        str(root / "scope.md"),
        "--target-env",
        str(root / "config" / "target.env"),
        "--adapters-dir",
        str(root / "harness" / "adapters"),
        "--coverage",
        str(root / "harness" / "coverage.json"),
    ]
    for surface in surfaces:
        command.extend(("--surface", surface))
    for area in args.area:
        command.extend(("--area", area))

    if args.dry_run:
        print("[dry-run] would run: " + " ".join(command))
        return 0
    if not coverage_init.exists():
        parser.error(f"missing shared harness helper: {coverage_init}")
    subprocess.run(command, check=True)
    print("initialized coverage state; now fill scope.md before any testing and have the overseer set the plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
