#!/usr/bin/env python3
"""Seed and merge harness coverage cells from scope, adapters, and Recon areas."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

DEFAULT_CELL = {
    "status": "not_started",
    "stage": "recon",
    "finding_slug": None,
    "notes": "Seeded by coverage_init.py",
}


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def read_target_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def read_target_surfaces(path: Path) -> list[str]:
    values = read_target_env(path)
    surfaces = [item.strip() for item in values.get("TARGET_SURFACES", "").split(",") if item.strip()]
    return surfaces or ["web"]


def read_in_scope_web_targets(path: Path) -> list[str]:
    values = read_target_env(path)
    return [item.strip() for item in values.get("IN_SCOPE_WEB_TARGETS", "").split(",") if item.strip()]


def taxonomy(adapter_path: Path) -> list[str]:
    content = adapter_path.read_text()
    match = re.search(r"^## Taxonomy seed\s*$([\s\S]*?)(?=^## |\Z)", content, re.MULTILINE)
    if not match:
        raise ValueError(f"{adapter_path} has no Taxonomy seed section")
    return [line[2:].strip() for line in match.group(1).splitlines() if line.startswith("- ")]


def scope_areas(path: Path, surface: str) -> list[tuple[str, str, str]]:
    if not path.exists():
        return []
    content = path.read_text()
    match = re.search(r"^## In scope\s*$([\s\S]*?)(?=^## |\Z)", content, re.MULTILINE)
    if not match:
        return []
    areas = []
    for line in match.group(1).splitlines():
        if not line.startswith("- "):
            continue
        description = line[2:].strip()
        if not description or "<" in description or "{{" in description:
            continue
        areas.append((surface, slugify(description), description))
    return areas


def parse_area(raw: str, default_surface: str) -> tuple[str, str, str]:
    if "=" not in raw:
        raise ValueError(f"--area must be ID=DESCRIPTION, got {raw!r}")
    identifier, description = (part.strip() for part in raw.split("=", 1))
    surface = default_surface
    if ":" in identifier:
        surface, identifier = (part.strip() for part in identifier.split(":", 1))
    if not surface or not identifier or not description:
        raise ValueError(f"--area must be ID=DESCRIPTION, got {raw!r}")
    return surface, slugify(identifier), description


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, default=Path("scope.md"))
    parser.add_argument("--target-env", type=Path, default=Path("config/target.env"))
    parser.add_argument("--adapters-dir", type=Path, default=Path("harness/adapters"))
    parser.add_argument("--coverage", type=Path, default=Path("harness/coverage.json"))
    parser.add_argument("--surface", action="append", help="Override TARGET_SURFACES; repeatable.")
    parser.add_argument("--area", action="append", default=[], help="AREA=DESCRIPTION or SURFACE:AREA=DESCRIPTION.")
    args = parser.parse_args()

    base_surfaces = args.surface or read_target_surfaces(args.target_env)
    in_scope_web_targets = read_in_scope_web_targets(args.target_env)

    # Never let an in-scope web surface go missing from the grid just because
    # TARGET_SURFACES forgot to list it. Only auto-add when surfaces came from
    # config/target.env (not an explicit --surface override) so an operator's
    # explicit choice is never silently expanded.
    web_auto_added = False
    surfaces = list(base_surfaces)
    if not args.surface and in_scope_web_targets and "web" not in surfaces:
        web_auto_added = True
        surfaces.append("web")
        print(
            "coverage_init.py: auto-added 'web' surface because "
            "IN_SCOPE_WEB_TARGETS is set in config/target.env but 'web' is "
            "missing from TARGET_SURFACES.",
            file=sys.stderr,
        )

    unknown = [surface for surface in surfaces if not (args.adapters_dir / f"{surface}.md").exists()]
    if unknown:
        parser.error(f"no adapter for surface(s): {', '.join(unknown)}")

    if args.coverage.exists():
        data = json.loads(args.coverage.read_text())
    else:
        data = {"areas": {}}
    if not isinstance(data, dict) or not isinstance(data.get("areas"), dict):
        parser.error(f"{args.coverage} must contain an object with an areas object")

    areas = []
    if len(base_surfaces) == 1:
        areas.extend(scope_areas(args.scope, base_surfaces[0]))
    if web_auto_added:
        claimed_ids = {identifier for _, identifier, _ in areas}
        web_areas = [
            area for area in scope_areas(args.scope, "web") if area[1] not in claimed_ids
        ]
        if not web_areas:
            web_areas = [("web", slugify(target), target) for target in in_scope_web_targets]
        areas.extend(web_areas)
    for raw in args.area:
        areas.append(parse_area(raw, surfaces[0]))

    created_areas = 0
    created_cells = 0
    timestamp = now()
    for surface, identifier, description in areas:
        if surface not in surfaces:
            parser.error(f"area {identifier!r} uses undeclared surface {surface!r}")
        area = data["areas"].setdefault(
            identifier, {"surface": surface, "description": description, "cells": {}}
        )
        if area["surface"] != surface:
            parser.error(f"area {identifier!r} already belongs to {area['surface']!r}")
        area.setdefault("description", description)
        area.setdefault("cells", {})
        if len(area["cells"]) == 0:
            created_areas += 1
        for attack_class in taxonomy(args.adapters_dir / f"{surface}.md"):
            if attack_class not in area["cells"]:
                cell = {**DEFAULT_CELL, "last_run": timestamp}
                area["cells"][attack_class] = cell
                created_cells += 1

    args.coverage.parent.mkdir(parents=True, exist_ok=True)
    args.coverage.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Seeded {created_cells} cell(s) across {created_areas} new area(s) in {args.coverage}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
