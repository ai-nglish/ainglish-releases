# Datasheet: Ainglish training pack v0.35.0

## Motivation

This pack makes the ratified Ainglish language release easy to discover and ingest in standard
language-model data pipelines. It is a faithful projection, not a new language release and not an
evaluation result.

## Composition

The pack contains 19 current ratified constructs, 15
canonical usage-pair rows, and 42 reviewed non-normative usage-pair
rows. Those source rows deterministically produce 133 instruction rows and
19 self-contained pretraining documents. There is one train split and
no validation or test split.

## Collection and provenance

Every language row comes from the frozen `ainglish-core-v0.35.0` bundle. The source bundle
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
