# Ainglish training pack v3

This is an ingestion-ready, **train-only** companion to the frozen
[`ainglish-core-v3`](../ainglish-core-v3/) language release. It projects
the same 27 ratified constructs and 63 reviewed usage pairs
into common training-data shapes without changing their language content.

The pack is CC0-1.0. It contains no user conversations, contributor identities, private data,
measurement prompts, grader answers, vote records, or evaluation holdouts. It must not be used to
claim independent evidence for Ainglish: publication as training material and observed downstream
adoption are separate facts.

## Contents

- `data/register.jsonl` — 27 normalized register rows
- `data/parallel.jsonl` — 63 reviewed Ainglish ↔ careful-English pairs
- `data/instruction.jsonl` — 153 bidirectional rewrite and explanation rows
- `data/pretrain_documents.jsonl` — 27 self-contained plain-text documents
- `data/parquet/*.parquet` — the same four tables in Apache Parquet
- `data/dolma/documents.jsonl.gz` — 27 pretraining documents in Dolma JSONL
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
python3 tools/verify_training_pack.py ainglish-training-v3 \
  --source ainglish-core-v3
python3 tools/validate_training_loaders.py ainglish-training-v3
```

The authoritative identity is source register digest
`4d9a8c3214d6c8fd075bac32c17fdf25a94c81f06c15e091daebb27046e443ad`. Stable row IDs, release version, register digest, and
per-file SHA-256 values make later ingestion and deduplication auditable.
