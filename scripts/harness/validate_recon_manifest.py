#!/usr/bin/env python3
"""Validate an optional, non-authoritative bug-bounty recon manifest."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.0"
CONFIDENCES = {
    "confirmed",
    "probable",
    "unverified",
    "unknown",
    "unowned",
    "quarantined",
    "high",
    "medium",
    "low",
}
TRUSTED_CONFIDENCES = {"confirmed", "probable", "high"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "producer_schema_version",
    "producer",
    "engagement_type",
    "generated_at",
    "assets",
    "ranked_surfaces",
    "secret_references",
    "suggested_vulnerability_classes",
}
ASSET_FIELDS = {
    "id",
    "target",
    "surface_rationale",
    "selected_for_testing",
    "ownership",
    "live_status",
}
SECRET_REFERENCE_KEYS = {
    "id",
    "reference",
    "redaction_ref",
    "location",
    "kind",
    "redacted",
}
PRODUCER_FIELDS = {"name", "schema_version"}
ANCHOR_FIELDS = {"type", "reference"}
OWNERSHIP_FIELDS = {"confidence", "anchors"}
LIVE_STATUS_FIELDS = {"http_status", "technology", "soft_404"}
RANKED_SURFACE_FIELDS = {"surface", "rank", "rationale"}
SECRET_VALUE_PATTERNS = (
    re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(
        r"(?i)\b(?:authorization|cookie|token|api[_-]?key|password|secret|credential)"
        r"\s*[:=]\s*\S+"
    ),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)
RAW_SECRET_KEYS = re.compile(
    r"(?:^|[_-])(?:raw[_-])?(?:secret|token|password|passwd|api[_-]?key|"
    r"private[_-]?key|credential|cookie|authorization|auth[_-]?header)(?:$|[_-])",
    re.IGNORECASE,
)
AUTO_SELECTION_KEYS = {
    "auto_selected",
    "auto_select",
    "automatic_selection",
    "automatically_selected",
}
AUTO_SELECTION_VALUES = {"auto", "automatic", "automated", "discovered"}
CTF_KEYS = {"ctf", "ctf_use", "ctf_artifacts", "challenge", "flag"}
OWNERSHIP_LINK_TYPES = {
    "coverage",
    "coverage_cell",
    "coverage-cell",
    "queue",
    "queue_cell",
    "queue-cell",
    "queue_ref",
    "queue-ref",
}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _utc_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.endswith("Z"):
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _walk_forbidden(value: Any, path: str = "", secret_context: bool = False) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.casefold() in CTF_KEYS:
                errors.append(f"CTF data is not valid in bug-bounty recon manifest: {child_path}")
            reference_context = secret_context or key_text in {
                "secret_references",
                "discovered_secret_references",
            }
            if RAW_SECRET_KEYS.search(key_text):
                allowed = key_text in {
                    "secret_references",
                    "discovered_secret_references",
                    "token_type",
                    "authorization_type",
                }
                if not allowed:
                    errors.append(f"raw secret field is forbidden: {child_path}")
            if secret_context and key_text.casefold() in {
                "value",
                "raw",
                "content",
                "data",
                "payload",
            }:
                errors.append(f"raw secret field is forbidden: {child_path}")
            if key_text.casefold() in AUTO_SELECTION_KEYS:
                if child is True or (isinstance(child, str) and child.casefold() in AUTO_SELECTION_VALUES):
                    errors.append(f"auto-selected queue/work is forbidden: {child_path}")
            if key_text.casefold() in {"selection_mode", "queue_selection"}:
                if isinstance(child, str) and child.casefold() in AUTO_SELECTION_VALUES:
                    errors.append(f"auto-selected queue/work is forbidden: {child_path}")
            errors.extend(_walk_forbidden(child, child_path, reference_context))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk_forbidden(child, f"{path}[{index}]", secret_context))
    return errors


def _reject_unknown_fields(value: Any, prefix: str, allowed: set[str]) -> list[str]:
    if not isinstance(value, dict):
        return []
    return [
        f"{prefix}.{field} is not allowed"
        for field in sorted(set(value) - allowed)
    ]


def _looks_like_secret_value(value: Any) -> bool:
    return isinstance(value, str) and any(
        pattern.search(value) for pattern in SECRET_VALUE_PATTERNS
    )


def _validate_asset(asset: Any, index: int) -> list[str]:
    prefix = f"assets[{index}]"
    errors: list[str] = []
    if not isinstance(asset, dict):
        return [f"{prefix} must be an object"]
    errors.extend(f"{prefix}.{field} is not allowed" for field in sorted(set(asset) - ASSET_FIELDS))
    for field in ("id", "target", "surface_rationale"):
        if not _text(asset.get(field)):
            errors.append(f"{prefix}.{field} is required")

    ownership = asset.get("ownership")
    if not isinstance(ownership, dict):
        errors.append(f"{prefix}.ownership must be an object")
        ownership = {}
    errors.extend(_reject_unknown_fields(ownership, f"{prefix}.ownership", OWNERSHIP_FIELDS))
    confidence = ownership.get("confidence")
    if not isinstance(confidence, str) or confidence.casefold() not in CONFIDENCES:
        errors.append(f"{prefix}.ownership.confidence is invalid")
    else:
        confidence = confidence.casefold()
    anchors = ownership.get("anchors")
    if anchors is not None and not isinstance(anchors, list):
        errors.append(f"{prefix}.ownership.anchors must be an array")
        anchors = []
    if anchors is None:
        anchors = []
    if confidence in TRUSTED_CONFIDENCES and not anchors:
        errors.append(f"{prefix}.ownership needs an ownership anchor")
    for anchor_index, anchor in enumerate(anchors):
        errors.extend(
            _reject_unknown_fields(
                anchor,
                f"{prefix}.ownership.anchors[{anchor_index}]",
                ANCHOR_FIELDS,
            )
        )
        if not isinstance(anchor, dict) or not _text(anchor.get("reference")):
            errors.append(f"{prefix}.ownership.anchors[{anchor_index}] needs a reference")

    live_status = asset.get("live_status")
    if not isinstance(live_status, dict):
        errors.append(f"{prefix}.live_status must be an object")
        live_status = {}
    errors.extend(_reject_unknown_fields(live_status, f"{prefix}.live_status", LIVE_STATUS_FIELDS))
    soft_404 = live_status.get("soft_404")
    if not isinstance(soft_404, bool):
        errors.append(f"{prefix}.live_status.soft_404 must be boolean")

    selected = asset.get("selected_for_testing", False)
    if not isinstance(selected, bool):
        errors.append(f"{prefix}.selected_for_testing must be boolean")
    elif selected:
        if confidence not in TRUSTED_CONFIDENCES:
            errors.append(f"{prefix} unowned/untrusted asset cannot be selected for testing")
        if soft_404 is True:
            errors.append(f"{prefix} soft-404 asset cannot be promoted to testing")
        if not anchors:
            errors.append(f"{prefix} selected work needs an ownership anchor")
        if not any(
            isinstance(anchor, dict)
            and str(anchor.get("type", "")).casefold() in OWNERSHIP_LINK_TYPES
            and _text(anchor.get("reference"))
            for anchor in anchors
        ):
            errors.append(f"{prefix} selected work needs a queue/coverage ownership cell")
    return errors


def _validate_secret_reference(reference: Any, index: int) -> list[str]:
    prefix = f"secret_references[{index}]"
    if not isinstance(reference, dict):
        return [f"{prefix} must be an object containing a redaction reference"]
    errors: list[str] = []
    for field in ("id", "reference"):
        if not _text(reference.get(field)):
            errors.append(f"{prefix}.{field} is required")
    if not _text(reference.get("redaction_ref")):
        errors.append(f"{prefix}.redaction_ref is required")
    if reference.get("redacted") is not True:
        errors.append(f"{prefix}.redacted must be true")
    unknown = set(reference) - SECRET_REFERENCE_KEYS
    if unknown:
        errors.extend(f"{prefix}.{field} is not allowed; store references, never raw values" for field in sorted(unknown))
    for field, value in reference.items():
        if field in SECRET_REFERENCE_KEYS and _looks_like_secret_value(value):
            errors.append(
                f"{prefix}.{field} looks like a raw secret; store a redaction-safe reference"
            )
    return errors


def validate_manifest(data: Any) -> list[str]:
    """Return validation errors; an empty list means the manifest is valid."""
    if not isinstance(data, dict):
        return ["manifest must be a JSON object"]

    errors = _walk_forbidden(data)
    errors.extend(f"{field} is not allowed by the recon manifest schema" for field in sorted(set(data) - TOP_LEVEL_FIELDS))
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if data.get("engagement_type") != "bug-bounty":
        errors.append("engagement_type must be 'bug-bounty'; CTF manifests are separate")
    if any(
        key.casefold() in CTF_KEYS
        for key, value in data.items()
    ):
        errors.append("CTF artifacts and flags are not valid in a bug-bounty recon manifest")
    if not _utc_timestamp(data.get("generated_at")):
        errors.append("generated_at must be an ISO-8601 UTC timestamp ending in Z")

    producer = data.get("producer")
    producer_version = data.get("producer_schema_version")
    if isinstance(producer, dict):
        errors.extend(_reject_unknown_fields(producer, "producer", PRODUCER_FIELDS))
        if not _text(producer.get("name")):
            errors.append("producer.name is required")
        if not _text(producer.get("schema_version")):
            errors.append("producer.schema_version is required")
    elif producer is not None:
        errors.append("producer must be an object")
    else:
        errors.append("producer is required")
    if not _text(producer_version):
        errors.append("producer_schema_version is required")

    assets = data.get("assets")
    if not isinstance(assets, list):
        errors.append("assets must be an array")
    else:
        for index, asset in enumerate(assets):
            errors.extend(_validate_asset(asset, index))

    references = data.get("secret_references", [])
    if not isinstance(references, list):
        errors.append("secret_references must be an array")
    else:
        for index, reference in enumerate(references):
            errors.extend(_validate_secret_reference(reference, index))

    surfaces = data.get("ranked_surfaces")
    if not isinstance(surfaces, list):
        errors.append("ranked_surfaces must be an array")
    else:
        for index, surface in enumerate(surfaces):
            errors.extend(
                _reject_unknown_fields(
                    surface,
                    f"ranked_surfaces[{index}]",
                    RANKED_SURFACE_FIELDS,
                )
            )
            if not isinstance(surface, dict) or not _text(surface.get("surface")) or not _text(surface.get("rationale")):
                errors.append(f"ranked_surfaces[{index}] needs surface and rationale")

    suggestions = data.get("suggested_vulnerability_classes")
    if not isinstance(suggestions, list) or any(not _text(item) for item in suggestions):
        errors.append("suggested_vulnerability_classes must be an array of strings")

    # A manifest may suggest work, but it cannot carry or mutate queue authority.
    if "queue" in data or "queue_rows" in data or "selected_queue" in data:
        errors.append("manifest cannot own queue selection; use the manual queue and coverage authority")
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.manifest.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {args.manifest}: {exc}", file=sys.stderr)
        return 1
    errors = validate_manifest(data)
    if errors:
        print(f"INVALID: {args.manifest}", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"VALID: {args.manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
