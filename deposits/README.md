# Deposit hand-off

This directory contains the files and copy-paste metadata a legal human representative of Starsol
Ltd needs to submit Ainglish training pack v0.35.0 to external catalogues.

- `ainglish-training-v0.35.0.tar.gz` is a deterministic single-file copy of the complete pack.
- `SHA256SUMS` identifies the upload bytes.
- `mozilla-data-collective.md` is the prepared uploader form and technical datasheet.
- `clarin-vlo.md` maps the same record to CLARIN discovery routes without inventing a repository
  identifier or CMDI profile.
- `hugging-face.md` is the exact update hand-off for the existing `ai-nglish/ainglish` dataset.
- `common-pile.md` records the current synthetic-data constraint and a candid issue draft to use
  only after the release has a stable public URL.

The archive is a transport copy, not another release identity. Its unpacked `MANIFEST.json` and
`SHA256SUMS` remain authoritative. Rebuild or check it from the repository root:

```sh
python3 tools/build_training_archive.py \
  ainglish-training-v0.35.0 \
  deposits/ainglish-training-v0.35.0.tar.gz --check
```

External submission must be performed by a legal owner using their own full legal identity. Before
submitting, they must read the platform's current provider terms and confirm that the selected
access and non-exclusivity settings preserve the public CC0 distribution already offered elsewhere.
