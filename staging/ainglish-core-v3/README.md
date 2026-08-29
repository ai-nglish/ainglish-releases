# Staging: Ainglish language release sequence 3

This directory is a readiness receipt, **not a release bundle**. Official release names are now sequence identifiers, so the next core and training artifacts will be `ainglish-core-v3` and `ainglish-training-v3`; their manifests will separately bind the live register version.

The 2026-08-29 authenticated public-register comparison found no language delta from `ainglish-core-v0.35.0`: the live register is still `0.35.0` at the same digest, with the same 19 visible non-protocol language entries. Its 16 protocol entries are deliberately outside the language bundle. Cutting sequence 3 now would duplicate normative language bytes under a new identity, so staging correctly says to wait.

Once a visible ratified language addition, removal, or immutable-entry change exists, rerun:

```sh
python3 tools/audit_next_language_release.py ainglish-core-v0.35.0 \
  --next-release-sequence 3 \
  --captured-at YYYY-MM-DDTHH:MM:SSZ \
  --output staging/ainglish-core-v3/READINESS.json
```

An observed delta opens core compilation; it does not make a release publication-ready. The official server compiler must still validate contribution rights and produce the core bytes, after which this repository verifies the core and builds the digest-bound train-only companion. Proposed or measured research candidates remain outside both artifacts. They may be published in a separately lifecycle-labelled research catalogue, never mixed into normative pretraining rows.
