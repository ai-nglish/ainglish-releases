#!/usr/bin/env python3
"""Verify an Ainglish training pack and its source-release binding."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import re

import pyarrow.parquet as pq


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def verify(pack: pathlib.Path, source: pathlib.Path | None = None) -> dict:
    pack = pathlib.Path(pack)
    sums = {}
    for line in (pack / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or name in sums or name.startswith("/"):
            raise ValueError("invalid SHA256SUMS row")
        path = pack / name
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"checksum mismatch for {name}")
        sums[name] = digest

    manifest = json.loads((pack / "MANIFEST.json").read_text(encoding="utf-8"))
    if manifest["kind"] != "ainglish.language.training-pack" or manifest["splits"] != ["train"]:
        raise ValueError("unexpected pack identity or split policy")
    if pack.name != f"ainglish-training-v{manifest['version']}":
        raise ValueError("pack directory name disagrees with its manifest")
    for name, identity in manifest["files"].items():
        path = pack / name
        if not path.is_file() or sha256(path) != identity["sha256"] or path.stat().st_size != identity["bytes"]:
            raise ValueError(f"manifest file identity mismatch for {name}")

    tables = {
        "register": read_jsonl(pack / "data/register.jsonl"),
        "parallel": read_jsonl(pack / "data/parallel.jsonl"),
        "instruction": read_jsonl(pack / "data/instruction.jsonl"),
        "pretrain_documents": read_jsonl(pack / "data/pretrain_documents.jsonl"),
    }
    expected_counts = manifest["counts"]
    for name, rows in tables.items():
        count_name = "pretrain_documents" if name == "pretrain_documents" else name
        if len(rows) != expected_counts[count_name]:
            raise ValueError(f"row count mismatch for {name}")
        if name != "pretrain_documents" and any(row["split"] != "train" for row in rows):
            raise ValueError(f"non-training split found in {name}")
        ids = [row.get("id", row.get("slug")) for row in rows]
        if len(ids) != len(set(ids)):
            raise ValueError(f"duplicate stable ID in {name}")
        parquet = pq.read_table(pack / f"data/parquet/{name}.parquet").to_pylist()
        comparable = rows
        if name == "pretrain_documents":
            comparable = [
                {**{key: value for key, value in row.items() if key != "metadata"},
                 "metadata_json": json.dumps(row["metadata"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))}
                for row in rows
            ]
        if parquet != comparable:
            raise ValueError(f"Parquet content differs from JSONL for {name}")

    with gzip.open(pack / "data/dolma/documents.jsonl.gz", "rt", encoding="utf-8") as source_file:
        dolma = [json.loads(line) for line in source_file]
    if dolma != tables["pretrain_documents"]:
        raise ValueError("Dolma shard differs from pretraining JSONL")
    for document in dolma:
        if set(document) != {"id", "text", "source", "created", "metadata"}:
            raise ValueError("Dolma document has an unexpected schema")

    source_digest = manifest["source"]["register_digest"]
    for name in ("register", "parallel", "instruction"):
        if any(row["register_digest"] != source_digest for row in tables[name]):
            raise ValueError(f"source digest drift in {name}")
    if source is not None:
        source_manifest = json.loads((source / "MANIFEST.json").read_text(encoding="utf-8"))
        if sha256(source / "MANIFEST.json") != manifest["source"]["manifest_sha256"]:
            raise ValueError("source manifest bytes do not match the pack")
        if source_manifest["register_digest"] != source_digest:
            raise ValueError("source register digest does not match the pack")
        if source_manifest["version"] != manifest["version"]:
            raise ValueError("source release version does not match the pack")
        if source.name != manifest["source"]["bundle"]:
            raise ValueError("source bundle name does not match the pack")
        source_register_version = source_manifest.get("register_version", source_manifest["version"])
        pack_register_version = manifest.get("register_version", manifest["version"])
        if source_register_version != pack_register_version:
            raise ValueError("source register version does not match the pack")
        if manifest["source"].get("register_version", pack_register_version) != pack_register_version:
            raise ValueError("pack source register-version pointer disagrees")

    return {
        "version": manifest["version"],
        "register_version": manifest.get("register_version", manifest["version"]),
        "files": len(sums),
        "counts": manifest["counts"],
        "source_register_digest": source_digest,
        "status": "verified",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=pathlib.Path)
    parser.add_argument("--source", type=pathlib.Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.pack, args.source), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
