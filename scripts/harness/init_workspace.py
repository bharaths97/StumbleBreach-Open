#!/usr/bin/env python3
"""Initialize a fresh StumbleBreach clone for Claude Code and Codex CLI.

This is a local-only, create-only bootstrap. It never touches the network,
never overwrites an existing file, and never deletes anything. Run it once
after cloning to lay down the playbook skeleton that the engine expects:

  * the ``.claude/skills/<role>/SKILL.md`` layout (one stub per role),
  * the Codex ``.agents/skills`` symlink that points at ``.claude/skills``,
  * the versioned git hooks (``core.hooksPath``).

The stubs are generic placeholders. Fill each ``SKILL.md`` body with your own
operating instructions -- that is your playbook, and it stays private. See
docs/SKILLS.md and docs/ENGINE-AND-PLAYBOOK.md.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# (role name, one-line description) -- mirrors docs/SKILLS.md. Bodies are stubs.
ROLES: tuple[tuple[str, str], ...] = (
    ("pentest-planner", "Set up an engagement branch and maintain its work plan; no hands-on testing or sign-off."),
    ("bb-mastermind", "Prioritize, check scope, route work, and accept or reject bug-bounty proposals."),
    ("bb-lavender-haze", "Bug-bounty reconnaissance and artifact mapping; seed coverage within scope."),
    ("bb-vigilante-shit", "Explicitly authorized bug-bounty hands-on hunting, with recorded evidence."),
    ("bb-archer", "Explicitly scoped smart-contract / blockchain review and validation."),
    ("bb-worker", "Generic scoped worker execution for a single approved bug-bounty queue item."),
    ("bb-blockchain-worker", "Worker execution for a scoped on-chain / contract task."),
    ("bb-profiler", "Build and maintain reusable target-organization profile knowledge."),
    ("ctf-mastermind", "Prioritize, check scope, route work, and accept or reject CTF proposals."),
    ("ctf-lavender-haze", "CTF reconnaissance and artifact mapping; seed coverage within scope."),
    ("ctf-vigilante-shit", "Explicitly authorized CTF challenge solving, with recorded evidence."),
    ("ctf-worker", "Generic scoped worker execution for a single approved CTF challenge."),
    ("ctf-overseer", "Oversee a multi-challenge CTF: intake, prioritization, and roll-up."),
    ("karma", "Independent adversarial verifier: challenge evidence and readiness before promotion."),
    ("mirrorball", "Post-engagement retrospective on process, template fit, and tooling."),
    ("hub-architect", "Evolve the engine itself -- templates, harness, and documentation."),
    ("tools-curator", "Curate and wire the MCP tool source into an agent safely."),
    ("clean", "Scrub internal terms and private detail from a draft before it leaves the workspace."),
)

SHARED_BASELINE_NAME = "WORKER-BASELINE.md"

SHARED_BASELINE_STUB = """# Worker baseline (shared)

Fill this with the instructions common to every role: read the active
engagement rules and scope first, confirm authorization before any network
interaction, record evidence for every claim, stay inside the approved queue
item, and stop when scope or authorization is unclear. Individual role skills
read this file so they can stay short.
"""


def skill_stub(name: str, description: str) -> str:
    """Return a generic, fill-me-in SKILL.md body for one role."""
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "---\n"
        f"\n# {name}\n\n"
        f"Read `.claude/skills/_shared/{SHARED_BASELINE_NAME}` and the active "
        "engagement rules first.\n\n"
        "This is a stub. Replace it with your own operating instructions for "
        f"this role. State the role's authority, its inputs, its outputs, and "
        "its stop conditions. Require evidence, keep planning / hands-on work / "
        "review distinct, and never grant permission the operator does not "
        "already have.\n"
    )


def write_if_absent(path: Path, content: str, created: list[Path], skipped: list[Path]) -> None:
    if path.exists():
        skipped.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    created.append(path)


def ensure_symlink(link: Path, target: str, notes: list[str]) -> None:
    """Create ``link`` -> ``target`` if it is not already present."""
    if link.is_symlink() or link.exists():
        notes.append(f"symlink/path exists, left as-is: {link}")
        return
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)
    notes.append(f"created symlink: {link} -> {target}")


def enable_hooks(root: Path, notes: list[str]) -> None:
    hooks_dir = root / ".githooks"
    if not hooks_dir.is_dir():
        notes.append("no .githooks/ directory found; skipped core.hooksPath")
        return
    try:
        subprocess.run(
            ["git", "-C", str(root), "config", "core.hooksPath", ".githooks"],
            check=True,
            capture_output=True,
        )
        notes.append("set git core.hooksPath = .githooks")
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        notes.append(f"could not set core.hooksPath ({exc}); set it manually")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to initialize (default: current directory).",
    )
    parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Do not run git config core.hooksPath .githooks.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    if not (root / "docs").is_dir() or not (root / "templates").is_dir():
        parser.error(f"{root} does not look like a StumbleBreach checkout")

    skills_dir = root / ".claude" / "skills"
    created: list[Path] = []
    skipped: list[Path] = []
    notes: list[str] = []

    write_if_absent(
        skills_dir / "_shared" / SHARED_BASELINE_NAME,
        SHARED_BASELINE_STUB,
        created,
        skipped,
    )
    for name, description in ROLES:
        write_if_absent(
            skills_dir / name / "SKILL.md",
            skill_stub(name, description),
            created,
            skipped,
        )

    # Codex CLI discovers the same skills through this symlink.
    ensure_symlink(root / ".agents" / "skills", "../.claude/skills", notes)

    if not args.no_hooks:
        enable_hooks(root, notes)

    print(f"StumbleBreach workspace init at {root}")
    print(f"  created {len(created)} file(s), skipped {len(skipped)} existing")
    for path in created:
        print(f"    + {path.relative_to(root)}")
    for note in notes:
        print(f"  - {note}")

    print("\nNext steps:")
    print("  1. Edit each .claude/skills/<role>/SKILL.md with your own playbook.")
    print("     See docs/SKILLS.md and docs/ENGINE-AND-PLAYBOOK.md.")
    print("  2. Claude Code: start from this root and invoke a role, e.g. /pentest-planner.")
    print("  3. Codex CLI: start from this root; it discovers roles via .agents/skills.")
    print("  4. To wire MCP tools, create tools-env/.venv and see docs/TOOLING.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
