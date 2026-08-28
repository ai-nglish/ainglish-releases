#!/usr/bin/env python3
"""Exercise the supported local ingestion paths without downloading a model."""

from __future__ import annotations

import argparse
import gzip
import importlib.metadata
import json
import pathlib
import tempfile

import mlcroissant as mlc
from datasets import load_dataset


def validate(pack: pathlib.Path) -> dict:
    pack = pathlib.Path(pack).resolve()
    manifest = json.loads((pack / "MANIFEST.json").read_text(encoding="utf-8"))
    tables = ("register", "parallel", "instruction", "pretrain_documents")
    counts = {}
    with tempfile.TemporaryDirectory(prefix="ainglish-loader-cache-") as cache:
        for name in tables:
            json_rows = load_dataset(
                "json",
                data_files=str(pack / f"data/{name}.jsonl"),
                split="train",
                cache_dir=cache,
            )
            parquet_rows = load_dataset(
                "parquet",
                data_files=str(pack / f"data/parquet/{name}.parquet"),
                split="train",
                cache_dir=cache,
            )
            if len(json_rows) != len(parquet_rows):
                raise ValueError(f"Hugging Face JSON/Parquet row mismatch for {name}")
            expected = manifest["counts"][name]
            if len(json_rows) != expected:
                raise ValueError(f"Hugging Face loader count mismatch for {name}")
            counts[name] = len(json_rows)

    croissant = mlc.Dataset(
        jsonld=json.loads((pack / "metadata/croissant.json").read_text(encoding="utf-8"))
    )
    record_sets = sorted(record_set.uuid for record_set in croissant.metadata.record_sets)
    if record_sets != sorted(tables):
        raise ValueError("Croissant record sets do not cover every training table")

    with gzip.open(pack / "data/dolma/documents.jsonl.gz", "rt", encoding="utf-8") as source:
        dolma = [json.loads(line) for line in source]
    if len(dolma) != manifest["counts"]["dolma_documents"]:
        raise ValueError("Dolma loader count mismatch")
    if any(not row.get("id") or not row.get("text") or row.get("source") != "ainglish" for row in dolma):
        raise ValueError("Dolma loader found a malformed document")

    return {
        "status": "validated",
        "pack_version": manifest["version"],
        "rows": counts,
        "croissant_record_sets": record_sets,
        "dolma_documents": len(dolma),
        "libraries": {
            name: importlib.metadata.version(name)
            for name in ("datasets", "mlcroissant", "pyarrow")
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=pathlib.Path)
    args = parser.parse_args(argv)
    print(json.dumps(validate(args.pack), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
