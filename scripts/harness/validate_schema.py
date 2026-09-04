#!/usr/bin/env python3
"""Mechanically validate the front matter of a candidate finding."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

BASE_FIELDS = ("slug", "area", "attack_class", "domain")
DOMAIN_FIELDS = {
    "web": ("endpoint", "method", "parameter", "auth_state"),
    "blockchain": ("contract_address", "chain_id", "repo_commit", "poc_environment"),
    "binary": ("function", "binary_build", "confirmation"),
}


def front_matter(path: Path, *, strict: bool = True) -> dict[str, str]:
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        if strict:
            raise ValueError("missing opening YAML front-matter delimiter")
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        if strict:
            raise ValueError("missing closing YAML front-matter delimiter") from exc
        return {}

    fields = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            if strict:
                raise ValueError(f"invalid front-matter line: {line!r}")
            return {}
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip().strip("'\"")
    return fields


def is_placeholder(value: str | None) -> bool:
    return not value or value == "N/A" or "<" in value or "{{" in value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("finding", type=Path)
    args = parser.parse_args()

    try:
        fields = front_matter(args.finding)
    except (OSError, ValueError) as exc:
        print(f"INVALID: {args.finding}: {exc}", file=sys.stderr)
        return 1

    errors = [f"missing or placeholder {field}" for field in BASE_FIELDS if is_placeholder(fields.get(field))]
    domain = fields.get("domain", "")
    if domain not in DOMAIN_FIELDS:
        errors.append(f"domain must be one of: {', '.join(DOMAIN_FIELDS)}")
    else:
        errors.extend(
            f"missing or placeholder {field}"
            for field in DOMAIN_FIELDS[domain]
            if is_placeholder(fields.get(field))
        )
    if fields.get("slug") and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", fields["slug"]):
        errors.append("slug must use lowercase letters, digits, and hyphens")

    if errors:
        print(f"INVALID: {args.finding}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"VALID: {args.finding}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
