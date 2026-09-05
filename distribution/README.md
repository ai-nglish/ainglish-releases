# Distribution verification

`release-3.json` is a durable map from each frozen release artifact to the places that claim to
carry it. It separates four facts that are easy to blur together:

1. the artifact is internally valid;
2. a distribution channel carries byte-identical files;
3. a catalogue makes the artifact discoverable; and
4. a corpus or model actually adopts it.

Only the first two are verified here. Catalogue status is recorded as a bounded hand-off, and no
publication event is treated as evidence of adoption, comprehension, or tokenizer efficiency.

## Run the audit

From the repository root:

```sh
# No network: ledger schema, local checksum trees, source binding, transport archive.
python3 tools/audit_distribution.py

# Download every automated channel tree and compare every file with frozen SHA256SUMS.
python3 tools/audit_distribution.py --online

# Release-manager gate: also fail while any required channel is still declared pending.
python3 tools/audit_distribution.py --online --require-complete
```

The JSON receipt distinguishes `verified`, `pending`, `ready_to_promote`, `failed`, and
`manual_receipt`. A pending URL that starts passing is reported as `ready_to_promote`; the program
does not edit its own ledger or turn a transient network result into a durable claim.

## Status discipline

- `verified`: every file named by the local `SHA256SUMS` was checked remotely, or a bounded manual
  preservation receipt is present.
- `pending`: the destination is intended but has not yet passed byte verification.
- catalogue states describe an external human workflow, not a byte mirror.
- `required` says whether the project's release checklist treats the channel as part of complete
  distribution. It does not make a third-party service authoritative.

Never stage a future release merely to populate this ledger. Create or update a release ledger only
after a conscious decision to publish that release. Record what was actually observed, pin moving
repositories to a commit where possible, and keep later releases in new ledger files rather than
rewriting old receipts.

## Release-3 distribution status

At the 2026-09-04T20:59:21Z observation, every required automated release-3 channel passed its
complete SHA256 tree audit. The release-3 training pack is byte-identical on ainglish.org, the
tagged GitHub tree, and the pinned Hugging Face commit. Catalogue submission and downstream
adoption remain separate work and are not implied by this distribution result.
