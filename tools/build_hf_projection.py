#!/usr/bin/env python3
"""Project a frozen core bundle into the two Hugging Face configs served from data/*.jsonl.

The `ai-nglish/ainglish` dataset carries every core bundle as a frozen directory and two projection
configs, `examples` and `register`, read from `data/register.jsonl` and `data/examples.jsonl`. Until
release 3 (2026-09-02) those two files had no generator; this is it, so the mapping is code, not a
paragraph. The mapping is deliberately trivial and must stay byte-stable:

  register.jsonl  one line per entry of register.json -> entries, fields verbatim, in bundle order
  examples.jsonl  {slug, ainglish, english, normative, source}:
                  every canonical item            -> normative true,  source "canonical"
                  every non_normative_training.batches[*].examples[*] -> normative false,
                                                     source "training-batch-<batch>"

Usage:  python3 tools/build_hf_projection.py ainglish-core-vN <out-dir>
        writes <out-dir>/register.jsonl and <out-dir>/examples.jsonl, prints counts as JSON.
"""
import json
import pathlib
import sys

REGISTER_FIELDS = ("slug", "title", "kind", "form", "english_mapping", "slot", "form_constraints",
                   "ratified_version", "ratified_at", "status", "rights_basis", "content_digest", "supersedes")


def project(bundle: pathlib.Path):
    register = json.loads((bundle / "register.json").read_text(encoding="utf-8"))
    examples = json.loads((bundle / "examples.json").read_text(encoding="utf-8"))
    entries = register["entries"]
    for e in entries:
        missing = set(REGISTER_FIELDS) - set(e)
        if missing:
            raise SystemExit(f"register entry {e.get('slug')} lacks {sorted(missing)}")
    rows = [{"slug": i["slug"], "ainglish": i["ainglish"], "english": i["english"], "normative": True,
             "source": "canonical"} for i in examples["canonical"]]
    for batch in examples["non_normative_training"]["batches"]:
        for i in batch["examples"]:
            rows.append({"slug": i["slug"], "ainglish": i["ainglish"], "english": i["english"],
                         "normative": False, "source": f"training-batch-{batch['batch']}"})
    return entries, rows


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    bundle, out = pathlib.Path(argv[1]), pathlib.Path(argv[2])
    entries, rows = project(bundle)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "register.jsonl").open("w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with (out / "examples.jsonl").open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(json.dumps({"bundle": bundle.name, "register_rows": len(entries), "example_rows": len(rows),
                      "canonical": sum(r["normative"] for r in rows),
                      "non_normative": sum(not r["normative"] for r in rows)}))


if __name__ == "__main__":
    main(sys.argv)
