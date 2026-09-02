#!/usr/bin/env python3
"""Return a deterministic shortlist of possible duplicate findings."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

MATCH_FIELDS = ("endpoint", "function", "contract_address", "attack_class")
STOP_WORDS = {"and", "for", "from", "the", "with", "that", "this", "into", "via"}


def front_matter(path: Path) -> dict[str, str]:
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    fields = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip().strip("'\"")
    return fields


def title(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.startswith("# Finding:"):
            return line.removeprefix("# Finding:").strip()
    return path.stem.replace("-", " ")


def tokens(value: str) -> set[str]:
    if "<" in value or "{{" in value:
        return set()
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z0-9]{4,}", value)
        if token.lower() not in STOP_WORDS
    }


def meaningful(value: str | None) -> bool:
    return bool(value and value != "N/A" and "<" not in value and "{{" not in value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--findings-dir", type=Path, default=Path("findings"))
    args = parser.parse_args()

    if not args.candidate.exists():
        parser.error(f"candidate does not exist: {args.candidate}")
    candidate = front_matter(args.candidate)
    if not candidate:
        print("candidate has no readable front matter", file=sys.stderr)
        return 1

    existing = [
        path for path in sorted(args.findings_dir.glob("*.md"))
        if path.resolve() != args.candidate.resolve() and path.name != "TEMPLATE-finding.md"
    ]
    title_tokens = {path: tokens(title(path)) for path in existing}
    frequencies = Counter(token for values in title_tokens.values() for token in values)
    candidate_tokens = tokens(title(args.candidate))
    candidates = []

    for path in existing:
        fields = front_matter(path)
        matched = [
            field
            for field in MATCH_FIELDS
            if meaningful(candidate.get(field))
            and candidate.get(field) == fields.get(field)
        ]
        rare_title_tokens = sorted(
            token for token in candidate_tokens & title_tokens[path] if frequencies[token] <= 2
        )
        score = len(matched) * 10 + len(rare_title_tokens)
        if score:
            candidates.append(
                {
                    "path": str(path),
                    "slug": fields.get("slug", path.stem),
                    "score": score,
                    "matched_fields": matched,
                    "rare_title_tokens": rare_title_tokens,
                }
            )

    result = {
        "candidate": str(args.candidate),
        "possible_duplicates": sorted(candidates, key=lambda item: (-item["score"], item["path"])),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
