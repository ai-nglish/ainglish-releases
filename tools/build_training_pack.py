#!/usr/bin/env python3
"""Build a deterministic, ingestion-ready companion to a frozen Ainglish release."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
import gzip
import hashlib
import json
import pathlib
import re
import shutil
import tempfile

import pyarrow as pa
import pyarrow.parquet as pq


PACK_KIND = "ainglish.language.training-pack"
VERSION_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.(?:0|[1-9][0-9]*)){0,2}")


@dataclass(frozen=True)
class BuildContext:
    release_version: str
    register_version: str
    generated_at: str
    source_bundle: str
    legacy_versioning: bool

    @property
    def base_url(self) -> str:
        return f"https://ainglish.org/training/ainglish-training-v{self.release_version}"


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value) + "\n", encoding="utf-8")


def write_jsonl(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(canonical_json(row) + "\n" for row in rows), encoding="utf-8")


def valid_version(value: object, field: str) -> str:
    if not isinstance(value, str) or not VERSION_PATTERN.fullmatch(value):
        raise ValueError(f"{field} is not a safe release version")
    return value


def valid_generated_at(value: object) -> str:
    if not isinstance(value, str):
        raise ValueError("generated_at must be an explicit UTC timestamp")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("generated_at must use YYYY-MM-DDTHH:MM:SSZ") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("generated_at is not canonical UTC")
    return value


def verify_source_bundle(source: pathlib.Path) -> tuple[dict, dict, dict, str, str, bool]:
    sums = {}
    for line in (source / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        path = source / name
        if not path.is_file() or sha256(path) != digest:
            raise ValueError(f"source bundle checksum mismatch for {name}")
        sums[name] = digest
    manifest = json.loads((source / "MANIFEST.json").read_text(encoding="utf-8"))
    register = json.loads((source / "register.json").read_text(encoding="utf-8"))
    examples = json.loads((source / "examples.json").read_text(encoding="utf-8"))
    release_version = valid_version(manifest.get("version"), "manifest.version")
    register_version = valid_version(register.get("version"), "register.version")
    legacy_versioning = "register_version" not in manifest
    if source.name != f"ainglish-core-v{release_version}":
        raise ValueError("source directory name disagrees with manifest.version")
    if legacy_versioning:
        if register_version != release_version or examples.get("version") != release_version:
            raise ValueError("legacy source versions disagree")
        if "release_version" in register or "release_version" in examples:
            raise ValueError("partially migrated source version contract")
    else:
        if valid_version(manifest.get("register_version"), "manifest.register_version") != register_version:
            raise ValueError("source manifest and register versions disagree")
        if examples.get("version") != register_version:
            raise ValueError("source examples register version disagrees")
        if register.get("release_version") != release_version:
            raise ValueError("source register release pointer disagrees")
        if examples.get("release_version") != release_version:
            raise ValueError("source examples release pointer disagrees")
    if manifest["register_digest"] != register["register_digest"]:
        raise ValueError("source register digest disagrees with its manifest")
    if examples.get("register_digest") != register["register_digest"]:
        raise ValueError("source examples register digest disagrees")
    return manifest, register, examples, release_version, register_version, legacy_versioning


def parallel_rows(examples: dict, register_digest: str, release_version: str) -> list[dict]:
    rows = []
    for example in examples["canonical"]:
        rows.append({
            "id": f"canonical/{example['slug']}",
            "slug": example["slug"],
            "ainglish": example["ainglish"],
            "english": example["english"],
            "normative": True,
            "source": "canonical-release-example",
            "source_batch": None,
            "source_release_version": release_version,
            "register_digest": register_digest,
            "split": "train",
        })
    for batch in examples["non_normative_training"]["batches"]:
        for example in batch["examples"]:
            rows.append({
                "id": example["id"],
                "slug": example["slug"],
                "ainglish": example["ainglish"],
                "english": example["english"],
                "normative": False,
                "source": "reviewed-non-normative-training-example",
                "source_batch": batch["batch"],
                "source_release_version": release_version,
                "register_digest": register_digest,
                "split": "train",
            })
    return sorted(rows, key=lambda row: (row["slug"], not row["normative"], row["id"]))


def register_rows(register: dict, release_version: str) -> list[dict]:
    rows = []
    for entry in register["entries"]:
        rows.append({
            "slug": entry["slug"],
            "title": entry["title"],
            "form": entry["form"],
            "english_mapping": entry["english_mapping"],
            "kind": entry["kind"],
            "status": entry["status"],
            "ratified_at": entry["ratified_at"],
            "ratified_version": entry["ratified_version"],
            "content_digest": entry["content_digest"],
            "rights_basis": entry["rights_basis"],
            "supersedes": entry["supersedes"],
            "slot_json": canonical_json(entry["slot"]),
            "form_constraints_json": (
                canonical_json(entry["form_constraints"])
                if entry["form_constraints"] is not None
                else None
            ),
            "source_release_version": release_version,
            "register_digest": register["register_digest"],
            "split": "train",
        })
    return sorted(rows, key=lambda row: row["slug"])


def instruction_rows(parallel: list[dict], register: list[dict], release_version: str) -> list[dict]:
    rows = []
    for pair in parallel:
        common = {
            "slug": pair["slug"],
            "source_example_id": pair["id"],
            "normative": pair["normative"],
            "source_release_version": release_version,
            "register_digest": pair["register_digest"],
            "split": "train",
        }
        rows.append({
            "id": f"instruction/{pair['id']}/ainglish-to-english",
            "task": "ainglish-to-careful-english",
            "prompt": (
                "Rewrite this Ainglish passage in careful English without weakening, "
                f"strengthening, or adding claims:\n\n{pair['ainglish']}"
            ),
            "response": pair["english"],
            **common,
        })
        rows.append({
            "id": f"instruction/{pair['id']}/english-to-ainglish",
            "task": "careful-english-to-ainglish",
            "prompt": (
                "Rewrite this careful-English passage in Ainglish while preserving its "
                f"meaning and scope:\n\n{pair['english']}"
            ),
            "response": pair["ainglish"],
            **common,
        })
    for entry in register:
        rows.append({
            "id": f"instruction/{entry['slug']}/explain",
            "task": "explain-registered-construct",
            "prompt": (
                "Explain the registered Ainglish form below in careful English. State its "
                f"scope and safeguards, not merely a gloss.\n\n{entry['form']}"
            ),
            "response": entry["english_mapping"],
            "slug": entry["slug"],
            "source_example_id": None,
            "normative": True,
            "source_release_version": release_version,
            "register_digest": entry["register_digest"],
            "split": "train",
        })
    return sorted(rows, key=lambda row: row["id"])


def pretrain_rows(parallel: list[dict], register: list[dict], context: BuildContext) -> list[dict]:
    by_slug: dict[str, list[dict]] = {}
    for pair in parallel:
        by_slug.setdefault(pair["slug"], []).append(pair)
    rows = []
    for entry in register:
        sections = [
            f"Ainglish registered construct: {entry['title']}",
            f"Registered form: {entry['form']}",
            f"Status: ratified; source release {context.release_version}.",
            "Careful-English definition:\n" + entry["english_mapping"],
        ]
        pairs = by_slug.get(entry["slug"], [])
        if pairs:
            lines = ["Reviewed usage pairs:"]
            for pair in pairs:
                label = "canonical" if pair["normative"] else "non-normative training"
                lines.extend([
                    f"- Ainglish ({label}): {pair['ainglish']}",
                    f"  Careful English: {pair['english']}",
                ])
            sections.append("\n".join(lines))
        rows.append({
            "id": f"ainglish-v{context.release_version}/{entry['slug']}",
            "text": "\n\n".join(sections),
            "source": "ainglish",
            "created": entry["ratified_at"],
            "metadata": {
                "content_digest": entry["content_digest"],
                "license": "CC0-1.0",
                "register_digest": entry["register_digest"],
                "release_version": context.release_version,
                "slug": entry["slug"],
                "url": f"https://ainglish.org/register/{entry['slug']}",
            },
        })
    return sorted(rows, key=lambda row: row["id"])


def parquet_rows(pretrain: list[dict]) -> list[dict]:
    rows = []
    for document in pretrain:
        row = {key: value for key, value in document.items() if key != "metadata"}
        row["metadata_json"] = canonical_json(document["metadata"])
        rows.append(row)
    return rows


def write_parquet(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    pq.write_table(
        table,
        path,
        compression="zstd",
        data_page_version="2.0",
        use_dictionary=False,
        version="2.6",
    )


def write_dolma(path: pathlib.Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(canonical_json(row) + "\n" for row in rows).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(payload)


def croissant_metadata(files: dict[str, str], context: BuildContext) -> dict:
    jsonld_context = {
        "@language": "en",
        "@vocab": "https://schema.org/",
        "arrayShape": "cr:arrayShape",
        "citeAs": "cr:citeAs",
        "column": "cr:column",
        "conformsTo": "dct:conformsTo",
        "containedIn": "cr:containedIn",
        "cr": "http://mlcommons.org/croissant/",
        "data": {"@id": "cr:data", "@type": "@json"},
        "dataType": {"@id": "cr:dataType", "@type": "@vocab"},
        "dct": "http://purl.org/dc/terms/",
        "description": {"@container": "@language"},
        "equivalentProperty": "cr:equivalentProperty",
        "examples": {"@id": "cr:examples", "@type": "@json"},
        "extract": "cr:extract",
        "field": "cr:field",
        "fileObject": "cr:fileObject",
        "fileProperty": "cr:fileProperty",
        "fileSet": "cr:fileSet",
        "format": "cr:format",
        "includes": "cr:includes",
        "isArray": "cr:isArray",
        "isLiveDataset": "cr:isLiveDataset",
        "jsonPath": "cr:jsonPath",
        "key": "cr:key",
        "md5": "cr:md5",
        "name": {"@container": "@language"},
        "parentField": "cr:parentField",
        "path": "cr:path",
        "rai": "http://mlcommons.org/croissant/RAI/",
        "recordSet": "cr:recordSet",
        "references": "cr:references",
        "regex": "cr:regex",
        "repeated": "cr:repeated",
        "replace": "cr:replace",
        "samplingRate": "cr:samplingRate",
        "sc": "https://schema.org/",
        "separator": "cr:separator",
        "source": "cr:source",
        "subField": "cr:subField",
        "transform": "cr:transform",
    }
    distributions = []
    record_sets = []
    schemas = {
        "parallel": [
            ("id", "sc:Text"), ("slug", "sc:Text"), ("ainglish", "sc:Text"),
            ("english", "sc:Text"), ("normative", "sc:Boolean"),
            ("source", "sc:Text"), ("source_batch", "sc:Integer"),
            ("source_release_version", "sc:Text"), ("register_digest", "sc:Text"),
            ("split", "sc:Text"),
        ],
        "instruction": [
            ("id", "sc:Text"), ("task", "sc:Text"), ("prompt", "sc:Text"),
            ("response", "sc:Text"), ("slug", "sc:Text"),
            ("source_example_id", "sc:Text"), ("normative", "sc:Boolean"),
            ("source_release_version", "sc:Text"), ("register_digest", "sc:Text"),
            ("split", "sc:Text"),
        ],
        "pretrain_documents": [
            ("id", "sc:Text"), ("text", "sc:Text"), ("source", "sc:Text"),
            ("created", "sc:DateTime"), ("metadata_json", "sc:Text"),
        ],
        "register": [
            ("slug", "sc:Text"), ("title", "sc:Text"), ("form", "sc:Text"),
            ("english_mapping", "sc:Text"), ("kind", "sc:Text"),
            ("status", "sc:Text"), ("ratified_at", "sc:DateTime"),
            ("ratified_version", "sc:Text"), ("content_digest", "sc:Text"),
            ("rights_basis", "sc:Text"), ("supersedes", "sc:Text"),
            ("slot_json", "sc:Text"), ("form_constraints_json", "sc:Text"),
            ("source_release_version", "sc:Text"), ("register_digest", "sc:Text"),
            ("split", "sc:Text"),
        ],
    }
    for name, fields in schemas.items():
        path = f"data/parquet/{name}.parquet"
        file_id = f"{name}-parquet"
        distributions.append({
            "@type": "cr:FileObject",
            "@id": file_id,
            "name": path,
            "contentUrl": f"{context.base_url}/{path}",
            "encodingFormat": "application/vnd.apache.parquet",
            "sha256": files[path],
        })
        record_sets.append({
            "@type": "cr:RecordSet",
            "@id": name,
            "name": name,
            "field": [
                {
                    "@type": "cr:Field",
                    "@id": f"{name}/{field}",
                    "dataType": data_type,
                    "source": {
                        "fileObject": {"@id": file_id},
                        "extract": {"column": field},
                    },
                }
                for field, data_type in fields
            ],
        })
    return {
        "@context": jsonld_context,
        "@type": "sc:Dataset",
        "conformsTo": "http://mlcommons.org/croissant/1.1",
        "name": f"Ainglish training pack v{context.release_version}",
        "description": (
            f"Train-only, ingestion-ready projections of the frozen Ainglish v{context.register_version} public-domain "
            "register and its reviewed usage pairs. No measurement or evaluation answers are included."
        ),
        "url": f"{context.base_url}/",
        "version": context.release_version,
        "datePublished": context.generated_at[:10],
        "citeAs": f"Ainglish training pack v{context.release_version}, Starsol Ltd ({context.generated_at[:4]})",
        "license": "https://creativecommons.org/publicdomain/zero/1.0/",
        "creator": {"@type": "Organization", "name": "Starsol Ltd", "url": "https://ainglish.org"},
        "keywords": ["Ainglish", "agent communication", "controlled language", "English", "CC0"],
        "distribution": distributions,
        "recordSet": record_sets,
    }


def readme(manifest: dict, context: BuildContext) -> str:
    counts = manifest["counts"]
    source_verification = "" if context.legacy_versioning else (
        " " + "\\" + f"\n  --source ainglish-core-v{context.release_version}"
    )
    return f"""# Ainglish training pack v{context.release_version}

This is an ingestion-ready, **train-only** companion to the frozen
[`ainglish-core-v{context.release_version}`](../ainglish-core-v{context.release_version}/) language release. It projects
the same {counts['constructs']} ratified constructs and {counts['parallel']} reviewed usage pairs
into common training-data shapes without changing their language content.

The pack is CC0-1.0. It contains no user conversations, contributor identities, private data,
measurement prompts, grader answers, vote records, or evaluation holdouts. It must not be used to
claim independent evidence for Ainglish: publication as training material and observed downstream
adoption are separate facts.

## Contents

- `data/register.jsonl` — {counts['register']} normalized register rows
- `data/parallel.jsonl` — {counts['parallel']} reviewed Ainglish ↔ careful-English pairs
- `data/instruction.jsonl` — {counts['instruction']} bidirectional rewrite and explanation rows
- `data/pretrain_documents.jsonl` — {counts['pretrain_documents']} self-contained plain-text documents
- `data/parquet/*.parquet` — the same four tables in Apache Parquet
- `data/dolma/documents.jsonl.gz` — {counts['dolma_documents']} pretraining documents in Dolma JSONL
- `metadata/croissant.json` — MLCommons Croissant 1.1 discovery metadata
- `DATASHEET.md` — scope, provenance, limitations, and recommended uses
- `MANIFEST.json` and `SHA256SUMS` — source binding and byte-level verification

All rows are in the `train` split. `normative=true` identifies canonical release examples;
`normative=false` identifies reviewed, non-normative training examples. Non-normative examples
illustrate an already-ratified construct but do not extend or amend its definition.

## Loading

```python
from datasets import load_dataset

parallel = load_dataset("json", data_files="data/parallel.jsonl", split="train")
parallel_parquet = load_dataset("parquet", data_files="data/parquet/parallel.parquet", split="train")
```

```python
import gzip, json

with gzip.open("data/dolma/documents.jsonl.gz", "rt", encoding="utf-8") as source:
    documents = [json.loads(line) for line in source]
```

Verify the complete pack from the repository root:

```sh
python3 tools/verify_training_pack.py ainglish-training-v{context.release_version}{source_verification}
python3 tools/validate_training_loaders.py ainglish-training-v{context.release_version}
```

The authoritative identity is source register digest
`{manifest['source']['register_digest']}`. Stable row IDs, release version, register digest, and
per-file SHA-256 values make later ingestion and deduplication auditable.
"""


def datasheet(manifest: dict, context: BuildContext) -> str:
    counts = manifest["counts"]
    return f"""# Datasheet: Ainglish training pack v{context.release_version}

## Motivation

This pack makes the ratified Ainglish language release easy to discover and ingest in standard
language-model data pipelines. It is a faithful projection, not a new language release and not an
evaluation result.

## Composition

The pack contains {counts['constructs']} current ratified constructs, {counts['canonical_parallel']}
canonical usage-pair rows, and {counts['non_normative_parallel']} reviewed non-normative usage-pair
rows. Those source rows deterministically produce {counts['instruction']} instruction rows and
{counts['pretrain_documents']} self-contained pretraining documents. There is one train split and
no validation or test split.

## Collection and provenance

Every language row comes from the frozen `ainglish-core-v{context.release_version}` bundle. The source bundle
is bound by its `MANIFEST.json`, `SHA256SUMS`, register digest, content digests, release versions,
ratification timestamps, and recorded rights basis. No web crawl, model generation, personal
conversation, or post-release augmentation was added while building this pack.

The canonical examples are part of the ratified language release. The additional examples were
authored and reviewed for training use and are explicitly non-normative. Both are covered by the
source release's CC0 rights manifest.

## Intended uses

- pretraining or continued pretraining on explicit agent-communication distinctions;
- supervised rewriting between Ainglish and careful English;
- retrieval, documentation, tokenizer, and parser experiments;
- public-domain corpus aggregation and linguistic research.

## Out-of-scope uses and limitations

- Do not treat these rows as an evaluation set or as evidence that a model comprehends Ainglish.
- Do not infer adoption, effectiveness, or safety from the pack's publication or a download count.
- The corpus is small and deliberately unbalanced: constructs have differing numbers of reviewed
  examples, and some have only a canonical pair.
- The material is English-language and focused on agent communication; it is not representative
  of ordinary English or human populations.
- Instruction rows are deterministic transformations of the source rows, not independent samples.
- A construct's complete semantics live in `english_mapping`; a short example alone is not the
  specification.

## Personal and sensitive information

The pack contains no contributor identity fields, user conversations, or intentionally collected
personal data. Illustrative names, paths, dates, identifiers, and incident scenarios are fictional
or generic examples. The source release expressly excludes contributor identity data.

## Licensing and maintenance

The identified pack is dedicated under CC0 1.0 Universal. Starsol Ltd publishes the official
release and training projection. A future Ainglish release should receive a new versioned companion
pack; this directory remains immutable once published. Corrections require a new pack version.

Contact and governance: https://ainglish.org · Source releases:
https://github.com/ai-nglish/ainglish-releases
"""


def build(source: pathlib.Path, output: pathlib.Path, generated_at: str) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to replace existing output: {output}")
    (
        source_manifest,
        register_source,
        examples_source,
        release_version,
        register_version,
        legacy_versioning,
    ) = verify_source_bundle(source)
    context = BuildContext(
        release_version=release_version,
        register_version=register_version,
        generated_at=valid_generated_at(generated_at),
        source_bundle=source.name,
        legacy_versioning=legacy_versioning,
    )
    if output.name != f"ainglish-training-v{context.release_version}":
        raise ValueError("output directory name disagrees with source release version")
    register = register_rows(register_source, context.release_version)
    parallel = parallel_rows(
        examples_source,
        register_source["register_digest"],
        context.release_version,
    )
    instructions = instruction_rows(parallel, register, context.release_version)
    pretrain = pretrain_rows(parallel, register, context)

    output.mkdir(parents=True)
    shutil.copyfile(source / "LICENSE-CC0-1.0.txt", output / "LICENSE-CC0-1.0.txt")
    write_jsonl(output / "data/register.jsonl", register)
    write_jsonl(output / "data/parallel.jsonl", parallel)
    write_jsonl(output / "data/instruction.jsonl", instructions)
    write_jsonl(output / "data/pretrain_documents.jsonl", pretrain)
    write_dolma(output / "data/dolma/documents.jsonl.gz", pretrain)
    parquet = {
        "register": register,
        "parallel": parallel,
        "instruction": instructions,
        "pretrain_documents": parquet_rows(pretrain),
    }
    for name, rows in parquet.items():
        write_parquet(output / f"data/parquet/{name}.parquet", rows)

    parquet_hashes = {
        f"data/parquet/{name}.parquet": sha256(output / f"data/parquet/{name}.parquet")
        for name in parquet
    }
    write_json(output / "metadata/croissant.json", croissant_metadata(parquet_hashes, context))

    manifest = {
        "kind": PACK_KIND,
        "version": context.release_version,
        "generated_at": context.generated_at,
        "license": "CC0-1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "publisher": source_manifest["publisher"],
        "scope": "train-only-projection-of-frozen-language-release",
        "source": {
            "bundle": context.source_bundle,
            "manifest_sha256": sha256(source / "MANIFEST.json"),
            "register_sha256": sha256(source / "register.json"),
            "examples_sha256": sha256(source / "examples.json"),
            "register_digest": register_source["register_digest"],
            "release_generated_at": source_manifest["generated_at"],
        },
        "counts": {
            "constructs": len(register),
            "register": len(register),
            "parallel": len(parallel),
            "canonical_parallel": sum(row["normative"] for row in parallel),
            "non_normative_parallel": sum(not row["normative"] for row in parallel),
            "instruction": len(instructions),
            "pretrain_documents": len(pretrain),
            "dolma_documents": len(pretrain),
        },
        "splits": ["train"],
        "exclusions": [
            "measurement prompts and answers",
            "evaluation and holdout data",
            "proposal, ballot, and vote records",
            "contributor identity data",
            "private conversations",
        ],
        "formats": ["JSONL", "Apache Parquet", "Dolma JSONL gzip", "MLCommons Croissant 1.1"],
    }
    if not context.legacy_versioning:
        manifest["register_version"] = context.register_version
        manifest["source"]["register_version"] = context.register_version
    (output / "README.md").write_text(readme(manifest, context), encoding="utf-8")
    (output / "DATASHEET.md").write_text(datasheet(manifest, context), encoding="utf-8")

    payload_files = {}
    for path in sorted(file for file in output.rglob("*") if file.is_file()):
        relative = path.relative_to(output).as_posix()
        payload_files[relative] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
    manifest["files"] = payload_files
    write_json(output / "MANIFEST.json", manifest)

    checksum_files = sorted(file for file in output.rglob("*") if file.is_file())
    (output / "SHA256SUMS").write_text(
        "".join(f"{sha256(path)}  {path.relative_to(output).as_posix()}\n" for path in checksum_files),
        encoding="utf-8",
    )
    return manifest


def compare(expected: pathlib.Path, actual: pathlib.Path) -> None:
    expected_files = {path.relative_to(expected) for path in expected.rglob("*") if path.is_file()}
    actual_files = {path.relative_to(actual) for path in actual.rglob("*") if path.is_file()}
    if expected_files != actual_files:
        raise ValueError("training pack file set is not reproducible")
    for relative in sorted(expected_files):
        if (expected / relative).read_bytes() != (actual / relative).read_bytes():
            raise ValueError(f"training pack differs from deterministic build: {relative}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument(
        "--generated-at",
        help=(
            "canonical UTC pack-generation timestamp (YYYY-MM-DDTHH:MM:SSZ); required for a "
            "new build and inferred from the existing pack manifest during --check"
        ),
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        if not args.output.is_dir():
            raise FileNotFoundError(args.output)
        existing_manifest = json.loads((args.output / "MANIFEST.json").read_text(encoding="utf-8"))
        generated_at = valid_generated_at(args.generated_at or existing_manifest.get("generated_at"))
        if args.generated_at and existing_manifest.get("generated_at") != generated_at:
            raise ValueError("--generated-at disagrees with the existing pack manifest")
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = pathlib.Path(tmp) / args.output.name
            manifest = build(args.source, rebuilt, generated_at)
            compare(args.output, rebuilt)
        print(canonical_json({"status": "reproducible", "version": manifest["version"]}))
    else:
        if args.generated_at is None:
            parser.error("--generated-at is required when building a new pack")
        manifest = build(args.source, args.output, args.generated_at)
        print(canonical_json({"counts": manifest["counts"], "status": "built", "version": manifest["version"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
