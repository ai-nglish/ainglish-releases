import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("verify_bundle", ROOT / "tools" / "verify_bundle.py")
verify_bundle = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_bundle)


def test_published_legacy_bundle_still_verifies_without_fabricating_a_reference():
    receipt = verify_bundle.verify(ROOT / "ainglish-core-v0.24.0")
    assert receipt["version"] == "0.24.0"
    assert receipt["agent_reference"] == "legacy_not_present"


def test_new_bundle_reference_is_bound_to_manifest_and_sums(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    register_digest = "a" * 64
    reference = (
        "# The Ainglish register — agent reference\n\n"
        "> Format: `ainglish.agent-reference.v1`\n"
        "> Register version: `0.35.0`\n"
        f"> Register SHA-256: `{register_digest}`\n"
    ).encode()
    reference_digest = hashlib.sha256(reference).hexdigest()
    manifest = {
        "version": "0.35.0",
        "register_digest": register_digest,
        "agent_reference": {
            "file": "AGENT-REFERENCE.md",
            "format": "ainglish.agent-reference.v1",
            "media_type": "text/markdown; charset=UTF-8",
            "sha256": reference_digest,
        },
    }
    manifest_bytes = json.dumps(manifest).encode()
    (bundle / "AGENT-REFERENCE.md").write_bytes(reference)
    (bundle / "MANIFEST.json").write_bytes(manifest_bytes)
    (bundle / "SHA256SUMS").write_text(
        f"{reference_digest}  AGENT-REFERENCE.md\n"
        f"{hashlib.sha256(manifest_bytes).hexdigest()}  MANIFEST.json\n",
        encoding="utf-8",
    )
    receipt = verify_bundle.verify(bundle)
    assert receipt["agent_reference"] == "verified"


def test_new_bundle_refuses_reference_identity_drift(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    reference = (
        "# The Ainglish register — agent reference\n\n"
        "> Format: `ainglish.agent-reference.v1`\n"
        "> Register version: `0.34.0`\n"
        "> Register SHA-256: `" + "a" * 64 + "`\n"
    ).encode()
    digest = hashlib.sha256(reference).hexdigest()
    manifest = {
        "version": "0.35.0", "register_digest": "a" * 64,
        "agent_reference": {"file": "AGENT-REFERENCE.md", "format": verify_bundle.FORMAT,
                            "media_type": "text/markdown; charset=UTF-8", "sha256": digest},
    }
    manifest_bytes = json.dumps(manifest).encode()
    (bundle / "AGENT-REFERENCE.md").write_bytes(reference)
    (bundle / "MANIFEST.json").write_bytes(manifest_bytes)
    (bundle / "SHA256SUMS").write_text(
        f"{digest}  AGENT-REFERENCE.md\n"
        f"{hashlib.sha256(manifest_bytes).hexdigest()}  MANIFEST.json\n", encoding="utf-8")
    try:
        verify_bundle.verify(bundle)
    except ValueError as error:
        assert "identity disagrees" in str(error)
    else:
        raise AssertionError("drifted reference identity was accepted")
