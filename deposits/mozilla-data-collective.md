# Mozilla Data Collective submission sheet

Prepared for a legal human representative of Starsol Ltd. The uploader must create the account and
make the legal attestations; this document does not do that on their behalf.

## Upload request

**Who are you and which organisation do you represent?**

I am an authorised human representative of Starsol Ltd (England and Wales company number 06002018),
publisher of the Ainglish language releases and this training-data projection. Use the uploader's
full legal name and an organisation-associated email address in the account profile.

**What data do you want to share?**

Ainglish training pack v3: a compact English-language dataset of 27 ratified constructs for
clearer agent-to-agent communication, 63 reviewed Ainglish to careful-English usage pairs, 153
deterministically derived instruction rows, and 27 self-contained pretraining documents. The pack
is source-bound to an immutable official language release and supplied as JSONL, Apache Parquet,
Dolma-compatible compressed JSONL, and MLCommons Croissant metadata.

**Why share it here?**

To make a public-domain controlled-language resource discoverable and directly ingestible by
language-technology researchers, open-corpus maintainers, and model builders, while retaining a
clear datasheet, stable provenance, and honest limits on claims. Publication is not represented as
evidence that any model has adopted or understood Ainglish.

## Listing fields

| Field | Value to enter |
|---|---|
| Dataset name | Ainglish training pack v3 |
| Short description | Train-only JSONL, Parquet, Dolma and Croissant projections of 19 ratified Ainglish agent-communication constructs and 63 reviewed Ainglish to careful-English usage pairs. |
| Task | Select the closest available text-generation and machine-translation or text-to-text tasks; do not select evaluation-only. |
| Locale / language | `en` |
| Main format | `JSONL, PARQUET` |
| License long form | Creative Commons CC0 1.0 Universal Public Domain Dedication |
| License short form | `CC0-1.0` |
| License URL | https://creativecommons.org/publicdomain/zero/1.0/ |
| Access | Public access |
| Exclusive hosting | **No. Opt out of exclusivity.** The same bytes are published at ainglish.org, GitHub and other public repositories. |
| Restrictions / notes | Leave blank. Do not add a restriction that contradicts CC0. |
| Forbidden usage | Leave blank. Do not add a restriction that contradicts CC0. |
| Additional conditions | Leave blank. Do not add a restriction that contradicts CC0. |
| Created by | Starsol Ltd, for the Ainglish Project |
| Point of contact | `[authorised human uploader: full legal name and organisation email]` |
| Legal contact | `[authorised Starsol Ltd contact: full legal name and organisation email]` |
| Source landing page | https://ainglish.org/training |
| Source language release | https://ainglish.org/releases/ainglish-core-v3/MANIFEST.json |
| Source register digest | `ee8978f9ab5adb252aa244dc1a0dbb5abaa81f499758ec18c95caf5dcfa863b8` |
| Upload filename | `ainglish-training-v3.tar.gz` |
| Upload SHA-256 | See `deposits/SHA256SUMS`; verify again immediately before upload. |

If the form offers only one task, choose the closest text-to-text or machine-translation category
and explain the controlled-language use in the description. Do not claim the dataset is parallel
human translation across two natural languages.

## Technical datasheet (paste as Markdown)

### What

Ainglish is a developing dialect of written English that makes selected distinctions explicit for
agent-to-agent communication. This dataset is a train-only projection of version 0.35.0 of the
official frozen language release. It contains:

- 19 normalized rows describing current ratified constructs and their full careful-English mapping;
- 57 reviewed Ainglish and careful-English parallel rows: 15 canonical and 42 explicitly
  non-normative training examples;
- 133 instruction rows: both rewrite directions for every pair, plus one full-definition
  explanation task per construct;
- 27 self-contained pretraining documents, also provided as one Dolma-format gzip shard;
- the same four logical tables as Apache Parquet; and
- MLCommons Croissant 1.1 metadata, a manifest, a datasheet, license text, and checksums.

All logical dataset rows are in a train split. There is deliberately no validation or test split.

### Who, source and provenance

Starsol Ltd publishes the pack for the Ainglish Project. Every language row is copied or
deterministically projected from the immutable `ainglish-core-v3` bundle. The source manifest,
register and examples files are identified by SHA-256 in the training-pack manifest. Each row also
carries stable source IDs, release version, and register digest where applicable.

The source register was shaped through Ainglish's public propose, second, measure and vote process.
The canonical examples form part of the ratified release. The 42 additional examples were authored
and reviewed for training use, remain explicitly non-normative, and do not amend a construct's
definition. No web crawl or model-generated augmentation was added while making this pack.

### Where and when

The source language release has cut-off 2026-08-25T08:00:00Z. This companion training pack was
generated on 2026-08-28 and is versioned 0.35.0 to bind it to that source. The authoritative landing
page is https://ainglish.org/training and the source-release repository is
https://github.com/ai-nglish/ainglish-releases.

### Language, orthography and domain

Language: English (`en`). Modality: written text. Script: Latin, UTF-8. Domain: controlled language,
natural-language processing, AI-agent communication, task coordination, evidence and lifecycle
reporting.

Ainglish uses ordinary English orthography plus registered ASCII-friendly markers such as
`we-including-you`, `not-both`, `start-by(...)`, brackets, digits and punctuation. Some illustrative
text contains ordinary Unicode punctuation or symbols. There is no separate fixed alphabet: the
complete Unicode strings are preserved in UTF-8, and the registered form and constraints in each
row are authoritative.

### Size and structure

The unpacked pack is under 500 KB. Relevant row counts are 19 register rows, 57 parallel rows, 133
instruction rows and 19 pretraining/Dolma documents. Formats are newline-delimited JSON, Apache
Parquet, gzip-compressed Dolma JSONL, Markdown, JSON and plain-text checksums. See `MANIFEST.json`
for byte sizes and per-file digests.

Key parallel fields are `id`, `slug`, `ainglish`, `english`, `normative`, `source`,
`source_release_version`, `register_digest`, and `split`. Instruction fields add `task`, `prompt`
and `response`. Dolma rows contain `id`, `text`, `source`, `created`, and `metadata`.

### Samples

1. Ainglish: `we-including-you will verify the anchors before Friday.`
   Careful English: `We — and that includes you — will verify the anchors before Friday.`
2. Ainglish: `we-excluding-you froze the panel item set; nothing is needed from you.`
   Careful English: `We froze the panel item set (not you — no action needed from you).`
3. Ainglish: `retry or escalate, not-both.`
   Careful English: `Retry or escalate — but not both.`
4. Ainglish: `read or write access, or-both.`
   Careful English: `You may have read access, write access, or both.`
5. Ainglish: `choice-not-made — which region the board will select`
   Careful English: `The board has not yet selected a region.`

### Intended uses

- pretraining or continued pretraining on explicit agent-communication distinctions;
- supervised text-to-text rewriting between Ainglish and careful English;
- retrieval, documentation, tokenizer, parser and controlled-language experiments; and
- public-domain corpus aggregation and linguistic research.

### Limitations and prohibited inferences

The pack is compact and deliberately unbalanced across constructs. Derived instruction rows are
not independent samples. A short usage pair does not replace the full registered definition. The
pack is not an evaluation set and does not contain held-out comprehension answers. Its publication,
listing or download count does not establish adoption, effectiveness, safety or comprehension.

### Personal data, ethics and safety

The pack contains no contributor identities, user conversations, private records, or intentionally
collected personal data. Illustrative names, paths, dates, identifiers and incident scenarios are
fictional or generic examples. No human subjects were recruited or profiled, so no institutional
human-subjects review was sought. The preparation review checked provenance, rights, personal-data
exclusion, stable identifiers, format integrity, and separation from evaluation material.

### Rights and maintenance

The identified training pack is dedicated under CC0 1.0 Universal. It can be used and redistributed,
including commercially, without an attribution requirement. The Ainglish name does not make a
derivative an official release. This directory is immutable once published; corrections and future
language releases receive a new versioned pack.

## Human submission checklist

1. Verify the archive with `sha256sum -c deposits/SHA256SUMS`.
2. Create or use the account of the legal data owner with a full human legal name and organisation
   email, then request uploader access.
3. Read the provider terms current on the day of submission. Select public, non-exclusive hosting.
4. Copy the fields and technical datasheet above. Replace both bracketed contact placeholders.
5. Upload the one `.tar.gz` archive, preview the listing, and compare counts, licence and source
   digest against this sheet.
6. Submit for manual review. Record the resulting listing URL and any requested edits in the PR or
   release log.
7. After publication, verify that the listing is discoverable in CLARIN VLO; do not claim it until
   an actual VLO record is observed.
