# Ainglish training pack v4

This is an ingestion-ready, **train-only** companion to the frozen
[`ainglish-core-v4`](../ainglish-core-v4/) language release. It projects
the same 32 ratified constructs and 66 reviewed usage pairs
into common training-data shapes without changing their language content.

The pack is CC0-1.0. It contains no user conversations, contributor identities, private data,
measurement prompts, grader answers, vote records, or evaluation holdouts. It must not be used to
claim independent evidence for Ainglish: publication as training material and observed downstream
adoption are separate facts.

## Contents

- `data/register.jsonl` — 32 normalized register rows
- `data/parallel.jsonl` — 66 reviewed Ainglish ↔ careful-English pairs
- `data/instruction.jsonl` — 164 bidirectional rewrite and explanation rows
- `data/pretrain_documents.jsonl` — 32 self-contained plain-text documents
- `data/parquet/*.parquet` — the same four tables in Apache Parquet
- `data/dolma/documents.jsonl.gz` — 32 pretraining documents in Dolma JSONL
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
python3 tools/verify_training_pack.py ainglish-training-v4 \
  --source ainglish-core-v4
python3 tools/validate_training_loaders.py ainglish-training-v4
```

The authoritative identity is source register digest
`964ea4c3478be1755dcc6dfa82830131112c7ddd0262c30cc628af3f071d6489`. Stable row IDs, release version, register digest, and
per-file SHA-256 values make later ingestion and deduplication auditable.
