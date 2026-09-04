import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "audit_distribution_test", ROOT / "tools" / "audit_distribution.py"
)
audit_distribution = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_distribution
SPEC.loader.exec_module(audit_distribution)
LEDGER = ROOT / "distribution" / "release-3.json"


def test_release_3_ledger_validates_local_trees_source_binding_and_transport():
    report = audit_distribution.audit(ROOT, LEDGER, online=False, timeout=1)

    assert report["kind"] == "ainglish.distribution-audit.v1"
    assert report["release"] == "3"
    assert [item["id"] for item in report["artifacts"]] == ["core", "training"]
    core, training = report["artifacts"]
    assert core["local"]["files"] == 7
    assert training["local"]["files"] == 14
    assert training["transport"]["files"] == 15
    assert training["transport"]["sha256"] == hashlib.sha256(
        (ROOT / "deposits" / "ainglish-training-v3.tar.gz").read_bytes()
    ).hexdigest()
    assert audit_distribution.incomplete(report) == []


def test_verified_remote_failure_is_fatal(monkeypatch):
    def unavailable(channel, local, timeout):
        raise OSError("fixture unavailable")

    monkeypatch.setattr(audit_distribution, "verify_remote_tree", unavailable)
    report = audit_distribution.audit(ROOT, LEDGER, online=True, timeout=1)
    core, training = report["artifacts"]

    assert all(row["result"] in {"failed", "manual_receipt"} for row in core["channels"])
    origin = next(row for row in training["channels"] if row["id"] == "authoritative-origin")
    assert origin["result"] == "failed"
    assert any("verified channel failed" in issue for issue in audit_distribution.incomplete(report))


def test_ready_to_promote_requires_an_explicit_ledger_promotion(monkeypatch):
    monkeypatch.setattr(
        audit_distribution,
        "verify_remote_tree",
        lambda channel, local, timeout: {"files": local["files"]},
    )
    report = audit_distribution.audit(ROOT, LEDGER, online=True, timeout=1)
    training = next(item for item in report["artifacts"] if item["id"] == "training")
    origin = next(row for row in training["channels"] if row["id"] == "authoritative-origin")

    # The durable release-3 row is now verified. Recreate the earlier pending declaration in the
    # result envelope to pin the generic rule: a successful probe does not promote its own ledger.
    origin["declared_status"] = "pending"
    origin["result"] = "ready_to_promote"
    assert origin["result"] == "ready_to_promote"
    assert "training/authoritative-origin: required channel is not declared verified" in audit_distribution.incomplete(report)


def test_unsafe_checksum_path_is_refused():
    with pytest.raises(ValueError, match="unsafe"):
        audit_distribution.parse_sums(("a" * 64 + "  ../escape\n").encode(), "fixture")


def test_ledger_identity_is_bound_to_frozen_manifests():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    for artifact in ledger["artifacts"]:
        manifest = ROOT / artifact["directory"] / "MANIFEST.json"
        sums = ROOT / artifact["directory"] / "SHA256SUMS"
        assert hashlib.sha256(manifest.read_bytes()).hexdigest() == artifact["manifest_sha256"]
        assert hashlib.sha256(sums.read_bytes()).hexdigest() == artifact["sha256sums_sha256"]
