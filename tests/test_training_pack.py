import importlib.util
import hashlib
import json
import subprocess
import sys
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / "ainglish-training-v0.35.0"
SOURCE = ROOT / "ainglish-core-v0.35.0"
SPEC = importlib.util.spec_from_file_location(
    "verify_training_pack", ROOT / "tools" / "verify_training_pack.py"
)
verify_training_pack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify_training_pack)


def test_published_training_pack_verifies_and_is_source_bound():
    receipt = verify_training_pack.verify(PACK, SOURCE)
    assert receipt["version"] == "0.35.0"
    assert receipt["counts"] == {
        "canonical_parallel": 15,
        "constructs": 19,
        "dolma_documents": 19,
        "instruction": 133,
        "non_normative_parallel": 42,
        "parallel": 57,
        "pretrain_documents": 19,
        "register": 19,
    }


def test_pack_is_a_reproducible_projection():
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_training_pack.py"),
            str(SOURCE),
            str(PACK),
            "--check",
        ],
        check=True,
    )


def test_pack_excludes_measurement_and_evaluation_payloads():
    manifest = json.loads((PACK / "MANIFEST.json").read_text(encoding="utf-8"))
    assert "measurement prompts and answers" in manifest["exclusions"]
    assert "evaluation and holdout data" in manifest["exclusions"]
    assert manifest["scope"] == "train-only-projection-of-frozen-language-release"


def test_deposit_archive_is_reproducible_and_contains_the_exact_pack():
    archive = ROOT / "deposits" / "ainglish-training-v0.35.0.tar.gz"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "build_training_archive.py"),
            str(PACK),
            str(archive),
            "--check",
        ],
        check=True,
    )
    with tarfile.open(archive, "r:gz") as source:
        members = {member.name: member for member in source.getmembers() if member.isfile()}
        for path in PACK.rglob("*"):
            if not path.is_file():
                continue
            name = f"{PACK.name}/{path.relative_to(PACK).as_posix()}"
            assert name in members
            extracted = source.extractfile(members[name])
            assert extracted is not None
            assert hashlib.sha256(extracted.read()).digest() == hashlib.sha256(path.read_bytes()).digest()
