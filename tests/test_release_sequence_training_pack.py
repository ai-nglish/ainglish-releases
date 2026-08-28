import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pyarrow.parquet as pq
import pytest


ROOT = Path(__file__).resolve().parent.parent
LEGACY_SOURCE = ROOT / "ainglish-core-v0.35.0"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load_module("build_training_pack_sequence_test", ROOT / "tools/build_training_pack.py")
verify_bundle = load_module("verify_bundle_sequence_test", ROOT / "tools/verify_bundle.py")
verify_pack = load_module("verify_training_pack_sequence_test", ROOT / "tools/verify_training_pack.py")


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def rewrite_sums(bundle: Path) -> None:
    names = [line.split(maxsplit=1)[1] for line in (bundle / "SHA256SUMS").read_text().splitlines()]
    (bundle / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256((bundle / name).read_bytes()).hexdigest()}  {name}\n"
            for name in names
        )
    )


def sequence_source(tmp_path: Path) -> Path:
    source = tmp_path / "ainglish-core-v3"
    shutil.copytree(LEGACY_SOURCE, source)

    register = json.loads((source / "register.json").read_text())
    register["version"] = "0.40.0"
    register["release_version"] = "3"
    write_json(source / "register.json", register)

    examples = json.loads((source / "examples.json").read_text())
    examples["version"] = "0.40.0"
    examples["release_version"] = "3"
    write_json(source / "examples.json", examples)

    reference = (source / "AGENT-REFERENCE.md").read_text().replace(
        "> Register version: `0.35.0`", "> Register version: `0.40.0`"
    )
    (source / "AGENT-REFERENCE.md").write_text(reference)

    manifest = json.loads((source / "MANIFEST.json").read_text())
    manifest["version"] = "3"
    manifest["register_version"] = "0.40.0"
    manifest["agent_reference"]["sha256"] = hashlib.sha256(
        (source / "AGENT-REFERENCE.md").read_bytes()
    ).hexdigest()
    write_json(source / "MANIFEST.json", manifest)
    rewrite_sums(source)
    return source


def test_release_sequence_source_builds_verifies_and_reproduces(tmp_path):
    source = sequence_source(tmp_path)
    output = tmp_path / "ainglish-training-v3"
    generated_at = "2026-09-02T03:04:05Z"

    core_receipt = verify_bundle.verify(source)
    assert core_receipt["version"] == "3"
    assert core_receipt["register_version"] == "0.40.0"

    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_training_pack.py"),
            str(source),
            str(output),
            "--generated-at",
            generated_at,
        ],
        check=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_training_pack.py"),
            str(source),
            str(output),
            "--check",
        ],
        check=True,
    )

    receipt = verify_pack.verify(output, source)
    assert receipt["version"] == "3"
    assert receipt["register_version"] == "0.40.0"
    manifest = json.loads((output / "MANIFEST.json").read_text())
    assert manifest["generated_at"] == generated_at
    assert manifest["register_version"] == "0.40.0"
    assert manifest["source"]["bundle"] == "ainglish-core-v3"
    assert manifest["source"]["register_version"] == "0.40.0"
    register_rows = [json.loads(line) for line in (output / "data/register.jsonl").read_text().splitlines()]
    assert {row["source_release_version"] for row in register_rows} == {"3"}
    assert pq.read_table(output / "data/parquet/register.parquet").num_rows == len(register_rows)
    croissant = json.loads((output / "metadata/croissant.json").read_text())
    assert croissant["version"] == "3"
    assert "Ainglish v0.40.0 public-domain register" in croissant["description"]
    readme = (output / "README.md").read_text()
    assert "ainglish-training-v3" in readme
    assert "--source ainglish-core-v3" in readme
    assert "v0.35.0" not in readme


def test_release_sequence_source_refuses_pointer_drift(tmp_path):
    source = sequence_source(tmp_path)
    examples = json.loads((source / "examples.json").read_text())
    examples["release_version"] = "4"
    write_json(source / "examples.json", examples)
    rewrite_sums(source)
    with pytest.raises(ValueError, match="examples release pointer"):
        builder.verify_source_bundle(source)


def test_new_build_requires_explicit_generated_at(tmp_path):
    source = sequence_source(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools/build_training_pack.py"),
            str(source),
            str(tmp_path / "ainglish-training-v3"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--generated-at is required" in result.stderr
