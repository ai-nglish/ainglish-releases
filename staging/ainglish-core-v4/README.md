# Staging: Ainglish language release sequence 4

This directory is a readiness receipt, **not a release bundle**. It compares published
`ainglish-core-v3` with a timestamped view of the live ratified register.

The 2026-09-03 comparison found two new visible, ratified language entries:

- `falsum-ref-ref-mark-a-claim-dead-when-its-falsifier-fires-3`
- `vs-baseline-the-baseline-anchor-batch-four-filed-by-rosetta-3`

That delta is sufficient to begin compilation and editorial review. It is not permission to publish
immediately. Release 3 was generated at 2026-09-02T08:00:00Z, so the standing seven-day rule makes
2026-09-09T08:00:00Z the earliest ordinary publication time. An earlier publication would need a
documented exceptional circumstance.

## Editorial hand-off

`falsum-ref` already has a clear canonical pair. `vs(<baseline>)` has complete normative semantics
but no canonical example pair. Before release compilation, the editor should add a concise pair to
the canonical source and verify it against the mapping. A suitable **non-canonical draft** is:

- Ainglish: `latency Δ -18 ms vs(previous-release)`
- English: `Latency decreased by 18 ms, measured against the previous release.`

The draft above is explicitly editorial material, not an alteration of the ratified mapping and not
canonical until accepted into the source register.

Refresh the receipt with:

```sh
python3 tools/audit_next_language_release.py ainglish-core-v3 \
  --next-release-sequence 4 \
  --captured-at YYYY-MM-DDTHH:MM:SSZ \
  --output staging/ainglish-core-v4/READINESS.json
```

After the cadence gate opens, the normal compiler, checksum, example, training-pack, archive, and
catalogue checks still apply. Proposed or merely measured research candidates remain outside the
normative release.
