#!/usr/bin/env python3
"""Verify one frozen Ainglish language bundle, including its canonical agent reference."""

import argparse
import hashlib
import json
import pathlib
import re

FORMAT = "ainglish.agent-reference.v1"


def verify(bundle):
    bundle = pathlib.Path(bundle)
    sums = {}
    for line in (bundle / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or name in sums or "/" in name:
            raise ValueError("invalid SHA256SUMS row")
        path = bundle / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError("checksum mismatch for %s" % name)
        sums[name] = digest
    manifest = json.loads((bundle / "MANIFEST.json").read_text(encoding="utf-8"))
    reference = manifest.get("agent_reference")
    if reference is None:
        return {"version": manifest["version"], "files": len(sums),
                "agent_reference": "legacy_not_present"}
    if reference != {
        "file": "AGENT-REFERENCE.md",
        "format": FORMAT,
        "media_type": "text/markdown; charset=UTF-8",
        "sha256": reference.get("sha256"),
    }:
        raise ValueError("manifest agent_reference contract is malformed")
    if "AGENT-REFERENCE.md" not in sums:
        raise ValueError("agent reference is absent from SHA256SUMS")
    data = (bundle / "AGENT-REFERENCE.md").read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if digest != reference["sha256"] or digest != sums["AGENT-REFERENCE.md"]:
        raise ValueError("agent reference digest mismatch")
    text = data.decode("utf-8")
    register_version = manifest.get("register_version", manifest["version"])
    expected = (
        "> Format: `%s`" % FORMAT,
        "> Register version: `%s`" % register_version,
        "> Register SHA-256: `%s`" % manifest["register_digest"],
    )
    for marker in expected:
        if marker not in text.splitlines():
            raise ValueError("agent reference identity disagrees with MANIFEST.json")
    return {"version": manifest["version"], "register_version": register_version, "files": len(sums),
            "agent_reference": "verified", "agent_reference_sha256": digest}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=pathlib.Path)
    args = parser.parse_args(argv)
    print(json.dumps(verify(args.bundle), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
