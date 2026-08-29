#!/usr/bin/env python3
"""Stage, but never publish, the next Ainglish language release decision."""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen


SHA256 = re.compile(r"[0-9a-f]{64}")


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_time(value: str) -> str:
    parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("captured_at must use canonical UTC")
    return value


def read_live(path: Path | None, url: str) -> dict:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    request = Request(url, headers={"User-Agent": "ainglish-release-readiness/1"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f"live register returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def validate_live(value: dict) -> None:
    if value.get("kind") != "ainglish.register.release":
        raise ValueError("unexpected live register kind")
    if not isinstance(value.get("version"), str) or not SHA256.fullmatch(value.get("digest", "")):
        raise ValueError("live register identity is incomplete")
    entries = value.get("entries")
    if not isinstance(entries, list) or any(not isinstance(row, dict) for row in entries):
        raise ValueError("live register entries are malformed")
    slugs = [row.get("slug") for row in entries]
    if any(not isinstance(slug, str) or not slug for slug in slugs) or len(slugs) != len(set(slugs)):
        raise ValueError("live register slugs are missing or duplicated")


def language_projection(entries: list[dict]) -> dict[str, dict]:
    rows = {}
    for entry in entries:
        if entry.get("kind") == "protocol":
            continue
        row = {key: entry.get(key) for key in ("slug", "kind", "form", "english_mapping")}
        if any(not isinstance(row[key], str) or not row[key] for key in row):
            raise ValueError(f"language entry is incomplete: {entry.get('slug')}")
        rows[row["slug"]] = row
    return rows


def baseline_projection(bundle: Path) -> tuple[dict, dict[str, dict]]:
    manifest = json.loads((bundle / "MANIFEST.json").read_text(encoding="utf-8"))
    register = json.loads((bundle / "register.json").read_text(encoding="utf-8"))
    if manifest.get("register_digest") != register.get("register_digest"):
        raise ValueError("baseline manifest/register digest drift")
    return manifest, language_projection(register["entries"])


def compare(baseline: dict[str, dict], live: dict[str, dict]) -> tuple[list[str], list[str], list[dict]]:
    added = sorted(live.keys() - baseline.keys())
    removed = sorted(baseline.keys() - live.keys())
    changed = []
    for slug in sorted(live.keys() & baseline.keys()):
        fields = [field for field in ("kind", "form", "english_mapping") if live[slug][field] != baseline[slug][field]]
        if fields:
            changed.append({"slug": slug, "fields": fields})
    return added, removed, changed


def build_report(bundle: Path, live: dict, captured_at: str, next_sequence: int, source: str) -> dict:
    validate_live(live)
    manifest, baseline = baseline_projection(bundle)
    current = language_projection(live["entries"])
    added, removed, changed = compare(baseline, current)
    delta = bool(added or removed or changed)
    same_register = live["version"] == manifest.get("register_version", manifest["version"]) and live["digest"] == manifest["register_digest"]
    if same_register and delta:
        raise ValueError("same register identity produced a language projection delta")
    if not delta and not same_register:
        decision = "wait_no_visible_language_delta"
    elif not delta:
        decision = "wait_same_register_no_language_delta"
    else:
        decision = "core_compilation_ready"
    report = {
        "kind": "ainglish.language.next-release-readiness.v1",
        "captured_at": canonical_time(captured_at),
        "next_release": {"sequence": str(next_sequence), "core_bundle": f"ainglish-core-v{next_sequence}", "training_pack": f"ainglish-training-v{next_sequence}"},
        "baseline": {
            "bundle": bundle.name,
            "release_version": manifest["version"],
            "register_version": manifest.get("register_version", manifest["version"]),
            "register_digest": manifest["register_digest"],
            "language_entries": len(baseline),
        },
        "live": {
            "source": source,
            "register_version": live["version"],
            "register_digest": live["digest"],
            "all_ratified_entries": len(live["entries"]),
            "language_entries": len(current),
            "protocol_entries_excluded": sum(row.get("kind") == "protocol" for row in live["entries"]),
        },
        "delta": {"added_language_slugs": added, "removed_language_slugs": removed, "changed_language_entries": changed},
        "decision": decision,
        "ready_for_core_compilation": delta,
        "publication_ready": False,
        "required_next_gates": (
            [
                "compile the official core bundle from the live server with rights validation",
                "verify core checksums, register digest, agent reference, examples, and release pointers",
                "build and verify the matching train-only pack with an explicit UTC generation time",
                "review canonical and non-normative examples without importing evaluation or holdout answers",
                "merge and deploy before external catalogue, archive, and DOI hand-offs",
            ]
            if delta else
            ["wait for at least one visible ratified language addition, removal, or immutable-entry change"]
        ),
        "scope_policy": {
            "normative": "current visible ratified non-protocol language only",
            "research_candidates": "excluded from the core and training pack; publish lifecycle-labelled research catalogues separately",
            "evaluation_data": "excluded",
            "private_or_identity_data": "excluded",
        },
        "sha256": None,
    }
    report["sha256"] = hashlib.sha256(canonical({**report, "sha256": None}).encode()).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("baseline_bundle", type=Path)
    parser.add_argument("--captured-at", required=True)
    parser.add_argument("--next-release-sequence", type=int, required=True)
    parser.add_argument("--live-register", type=Path)
    parser.add_argument("--register-url", default="https://ainglish.org/api/v1/register.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.next_release_sequence < 1:
        parser.error("--next-release-sequence must be positive")
    live = read_live(args.live_register, args.register_url)
    source = str(args.live_register) if args.live_register else args.register_url
    report = build_report(args.baseline_bundle, live, args.captured_at, args.next_release_sequence, source)
    rendered = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
