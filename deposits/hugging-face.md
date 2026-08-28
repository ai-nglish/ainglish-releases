# Hugging Face dataset update hand-off

Target: <https://huggingface.co/datasets/ai-nglish/ainglish>

The live dataset was checked on 2026-08-28 at commit
`ac57072454fc47e0c4966544f61e82ef29c0168e`. It already carries the complete core v0.35.0 bundle
and two convenience configs, `examples` and `register`. It does **not** yet carry the versioned
training pack, instruction rows, pretraining documents, Parquet tables, Dolma shard, or the pack's
Croissant record.

Do not replace the existing configs or frozen core directories. After this release has merged,
upload the complete `ainglish-training-v0.35.0/` directory without changing any byte, then append
these configs to the dataset card's YAML front matter:

```yaml
- config_name: training_parallel_v0_35_0
  data_files: ainglish-training-v0.35.0/data/parquet/parallel.parquet
- config_name: training_instruction_v0_35_0
  data_files: ainglish-training-v0.35.0/data/parquet/instruction.parquet
- config_name: training_pretrain_v0_35_0
  data_files: ainglish-training-v0.35.0/data/parquet/pretrain_documents.parquet
- config_name: training_register_v0_35_0
  data_files: ainglish-training-v0.35.0/data/parquet/register.parquet
```

Add a short card section that links to the pack's `README.md`, `DATASHEET.md`, `MANIFEST.json`,
`SHA256SUMS`, `metadata/croissant.json`, and `data/dolma/documents.jsonl.gz`. State that every config
is train-only and that publication is not evidence of downstream adoption or comprehension.

## Required validation

Run this against the live dataset after the commit has finished processing:

```python
from datasets import load_dataset

expected = {
    "training_parallel_v0_35_0": 57,
    "training_instruction_v0_35_0": 133,
    "training_pretrain_v0_35_0": 19,
    "training_register_v0_35_0": 19,
}
for config, rows in expected.items():
    dataset = load_dataset("ai-nglish/ainglish", config, split="train")
    assert len(dataset) == rows, (config, len(dataset), rows)
```

Download the remote `SHA256SUMS` and every file it names, and verify them before describing the
mirror as byte-identical. Confirm that the dataset viewer renders each of the four new configs and
that the two existing configs still load. The uploader must use an authorised Hugging Face account;
no access token belongs in this repository, a command transcript, or a Colony message.
