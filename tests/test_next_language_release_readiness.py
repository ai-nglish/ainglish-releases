import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_module():
    path = ROOT / "tools/audit_next_language_release.py"
    spec = importlib.util.spec_from_file_location("next_release_readiness_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


readiness = load_module()


def live_from_baseline() -> dict:
    source = json.loads((ROOT / "ainglish-core-v0.35.0/register.json").read_text())
    return {
        "kind": "ainglish.register.release",
        "version": source["version"],
        "digest": source["register_digest"],
        "entries": [
            {key: row[key] for key in ("slug", "kind", "form", "english_mapping")}
            for row in source["entries"]
        ],
    }


def test_same_register_is_an_explicit_no_op():
    live = live_from_baseline()
    live["entries"].append({
        "slug": "protocol-only-row",
        "kind": "protocol",
        "form": "protocol form",
        "english_mapping": "protocol mapping",
    })
    report = readiness.build_report(
        ROOT / "ainglish-core-v0.35.0", live, "2026-08-29T13:30:00Z", 3, "fixture"
    )
    assert report["decision"] == "wait_same_register_no_language_delta"
    assert report["ready_for_core_compilation"] is False
    assert report["live"]["protocol_entries_excluded"] == 1
    assert report["delta"] == {
        "added_language_slugs": [],
        "removed_language_slugs": [],
        "changed_language_entries": [],
    }


def test_new_language_entry_opens_compilation_not_publication():
    live = live_from_baseline()
    live["version"] = "0.36.0"
    live["digest"] = "a" * 64
    live["entries"].append({
        "slug": "new-language-entry",
        "kind": "lexical",
        "form": "new-form",
        "english_mapping": "A complete careful-English mapping.",
    })
    report = readiness.build_report(
        ROOT / "ainglish-core-v0.35.0", live, "2026-09-02T13:30:00Z", 3, "fixture"
    )
    assert report["decision"] == "core_compilation_ready"
    assert report["ready_for_core_compilation"] is True
    assert report["publication_ready"] is False
    assert report["delta"]["added_language_slugs"] == ["new-language-entry"]
    assert report["next_release"]["core_bundle"] == "ainglish-core-v3"
    assert report["release_cadence"] == {
        "minimum_gap_days": 7,
        "previous_release_generated_at": "2026-08-25T08:00:00Z",
        "earliest_ordinary_publication_at": "2026-09-01T08:00:00Z",
        "ordinary_cadence_gate_open": True,
        "exception_policy": "publish earlier only for a documented exceptional circumstance",
    }


def test_language_delta_can_be_compiled_while_publication_waits_for_cadence():
    live = live_from_baseline()
    live["version"] = "0.36.0"
    live["digest"] = "c" * 64
    live["entries"].append({
        "slug": "new-language-entry",
        "kind": "lexical",
        "form": "new-form",
        "english_mapping": "A complete careful-English mapping.",
    })
    report = readiness.build_report(
        ROOT / "ainglish-core-v0.35.0", live, "2026-08-18T13:30:00Z", 3, "fixture"
    )
    assert report["decision"] == "core_compilation_ready_waiting_cadence"
    assert report["ready_for_core_compilation"] is True
    assert report["publication_ready"] is False
    assert report["release_cadence"]["ordinary_cadence_gate_open"] is False
    assert report["required_next_gates"][0].startswith("wait until 2026-09-01T08:00:00Z")


def test_non_language_candidates_never_enter_the_projection():
    live = live_from_baseline()
    live["version"] = "0.36.0"
    live["digest"] = "b" * 64
    live["entries"].append({
        "slug": "new-protocol-entry",
        "kind": "protocol",
        "form": "machine rule",
        "english_mapping": "A governance-only rule.",
    })
    report = readiness.build_report(
        ROOT / "ainglish-core-v0.35.0", live, "2026-08-29T13:30:00Z", 3, "fixture"
    )
    assert report["decision"] == "wait_no_visible_language_delta"
    assert report["ready_for_core_compilation"] is False
    assert report["scope_policy"]["research_candidates"].startswith("excluded")
