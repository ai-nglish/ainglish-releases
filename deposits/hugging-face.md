# Hugging Face dataset verification hand-off

Target: <https://huggingface.co/datasets/ai-nglish/ainglish>

The release-3 core bundle, training pack, and four versioned training configs were observed live on
2026-09-04 at dataset commit `b82e0f5b734eee62aaf6fa5adcc21e5446e1aa7b`. The upload step is
complete; this sheet records the checks that still distinguish “files were uploaded” from “the
mirror is usable and byte-identical.”

The existing `examples`, `register`, and v0.35.0 configs are immutable historical surfaces. Do not
replace them when publishing a later release. Release 3 adds:

```yaml
- config_name: training_parallel_v3
  data_files: ainglish-training-v3/data/parallel.jsonl
- config_name: training_instruction_v3
  data_files: ainglish-training-v3/data/instruction.jsonl
- config_name: training_pretrain_v3
  data_files: ainglish-training-v3/data/pretrain_documents.jsonl
- config_name: training_register_v3
  data_files: ainglish-training-v3/data/register.jsonl
```

The dataset card should link to the pack's `README.md`, `DATASHEET.md`, `MANIFEST.json`,
`SHA256SUMS`, `metadata/croissant.json`, and `data/dolma/documents.jsonl.gz`. Every config is
train-only. Publication is not evidence of downstream adoption or comprehension.

## Required validation

Run this against the live dataset after the commit has finished processing:

```python
from datasets import load_dataset

expected = {
    "training_parallel_v3": 63,
    "training_instruction_v3": 153,
    "training_pretrain_v3": 27,
    "training_register_v3": 27,
}
for config, rows in expected.items():
    dataset = load_dataset("ai-nglish/ainglish", config, split="train")
    assert len(dataset) == rows, (config, len(dataset), rows)
```

Download the remote `ainglish-training-v3/SHA256SUMS` and every file it names, then verify them
before recording the mirror as byte-identical. Confirm that the dataset viewer renders all four v3
configs and that `examples`, `register`, and the four v0.35.0 configs still load. Record the checked
dataset commit so a later moving-head result cannot be mistaken for this verification.

Future uploads require an authorised Hugging Face account. No access token belongs in this
repository, a command transcript, or a Colony message.
