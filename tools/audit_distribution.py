#!/usr/bin/env python3
"""Audit frozen Ainglish artifacts across declared publication channels.

Offline mode validates the ledger, local checksum trees, source binding, and deterministic deposit
archive. ``--online`` additionally downloads each declared checksum tree. Verified channels must
match; pending channels are probed and reported without silently promoting their durable status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
import tarfile
import urllib.error
import urllib.parse
import urllib.request


KIND = "ainglish.distribution-ledger.v1"
CHANNEL_STATES = {"verified", "pending"}
CATALOGUE_STATES = {
    "verified",
    "pending_human_submission",
    "blocked_on_mozilla_listing",
    "policy_gated",
}
HEX64 = re.compile(r"[0-9a-f]{64}")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: pathlib.Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def parse_sums(data: bytes, source: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in data.decode("utf-8").splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"{source}: malformed SHA256SUMS row")
        sha, name = parts
        name = name.lstrip("* ")
        pure = pathlib.PurePosixPath(name)
        if (
            not HEX64.fullmatch(sha)
            or name in rows
            or pure.is_absolute()
            or ".." in pure.parts
            or name in {"", "."}
        ):
            raise ValueError(f"{source}: unsafe or duplicate SHA256SUMS row")
        rows[name] = sha
    if not rows:
        raise ValueError(f"{source}: empty SHA256SUMS")
    return rows


def verify_local_tree(root: pathlib.Path, artifact: dict) -> dict:
    directory = root / artifact["directory"]
    if not directory.is_dir():
        raise ValueError(f"missing artifact directory {artifact['directory']}")
    manifest = directory / "MANIFEST.json"
    observed_manifest = digest(manifest.read_bytes())
    if observed_manifest != artifact["manifest_sha256"]:
        raise ValueError(f"{artifact['id']}: manifest digest disagrees with ledger")
    sums_data = (directory / "SHA256SUMS").read_bytes()
    if digest(sums_data) != artifact["sha256sums_sha256"]:
        raise ValueError(f"{artifact['id']}: SHA256SUMS digest disagrees with ledger")
    sums = parse_sums(sums_data, f"{artifact['id']}/SHA256SUMS")
    for name, expected in sums.items():
        path = directory / pathlib.PurePosixPath(name)
        if not path.is_file() or digest(path.read_bytes()) != expected:
            raise ValueError(f"{artifact['id']}: local checksum mismatch for {name}")
    manifest_data = load_json(manifest)
    return {
        "manifest_sha256": observed_manifest,
        "sha256sums_sha256": digest(sums_data),
        "files": len(sums),
        "version": str(manifest_data["version"]),
        "manifest": manifest_data,
        "sums": sums,
    }


def verify_transport(root: pathlib.Path, artifact: dict, local: dict) -> dict | None:
    transport = artifact.get("transport")
    if transport is None:
        return None
    archive = root / transport["path"]
    if digest(archive.read_bytes()) != transport["sha256"]:
        raise ValueError(f"{artifact['id']}: transport archive digest disagrees with ledger")
    expected: dict[str, str] = {}
    directory = root / artifact["directory"]
    for path in directory.rglob("*"):
        if path.is_file():
            expected[f"{directory.name}/{path.relative_to(directory).as_posix()}"] = digest(path.read_bytes())
    with tarfile.open(archive, "r:gz") as source:
        members = {member.name: member for member in source.getmembers() if member.isfile()}
        if set(members) != set(expected):
            raise ValueError(f"{artifact['id']}: transport archive file set differs from pack")
        for name, expected_digest in expected.items():
            stream = source.extractfile(members[name])
            if stream is None or digest(stream.read()) != expected_digest:
                raise ValueError(f"{artifact['id']}: transport archive mismatch for {name}")
    return {"path": transport["path"], "sha256": transport["sha256"], "files": len(expected)}


def fetch(url: str, timeout: float) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "ainglish-distribution-audit/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def remote_url(template: str, path: str) -> str:
    return template.replace("{path}", urllib.parse.quote(path, safe="/"))


def verify_remote_tree(channel: dict, local: dict, timeout: float) -> dict:
    verification = channel["verification"]
    template = verification["file_url"]
    remote_sums = fetch(remote_url(template, "SHA256SUMS"), timeout)
    if digest(remote_sums) != local["sha256sums_sha256"]:
        raise ValueError("remote SHA256SUMS bytes differ from the frozen artifact")
    rows = parse_sums(remote_sums, f"{channel['id']}/SHA256SUMS")
    if rows != local["sums"]:
        raise ValueError("remote SHA256SUMS content differs from the frozen artifact")
    for name, expected in rows.items():
        if digest(fetch(remote_url(template, name), timeout)) != expected:
            raise ValueError(f"remote checksum mismatch for {name}")
    return {"files": len(rows), "sha256sums_sha256": digest(remote_sums)}


def validate_ledger(root: pathlib.Path, ledger: dict) -> None:
    if ledger.get("kind") != KIND or not str(ledger.get("release", "")):
        raise ValueError("unexpected ledger identity")
    artifacts = ledger.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("ledger must declare artifacts")
    ids: set[str] = set()
    for artifact in artifacts:
        if artifact.get("id") in ids or not artifact.get("id"):
            raise ValueError("artifact IDs must be non-empty and unique")
        ids.add(artifact["id"])
        if not HEX64.fullmatch(artifact.get("manifest_sha256", "")):
            raise ValueError(f"{artifact['id']}: invalid manifest_sha256")
        if not HEX64.fullmatch(artifact.get("sha256sums_sha256", "")):
            raise ValueError(f"{artifact['id']}: invalid sha256sums_sha256")
        channels = artifact.get("channels")
        if not isinstance(channels, list) or not channels:
            raise ValueError(f"{artifact['id']}: no distribution channels")
        channel_ids: set[str] = set()
        for channel in channels:
            channel_id = channel.get("id")
            if not channel_id or channel_id in channel_ids:
                raise ValueError(f"{artifact['id']}: channel IDs must be unique")
            channel_ids.add(channel_id)
            if channel.get("status") not in CHANNEL_STATES:
                raise ValueError(f"{artifact['id']}/{channel_id}: invalid status")
            verification = channel.get("verification", {})
            if verification.get("type") == "sha256_tree" and "{path}" not in verification.get("file_url", ""):
                raise ValueError(f"{artifact['id']}/{channel_id}: sha256_tree needs a file URL template")
            if channel.get("status") == "verified" and verification.get("type") not in {"sha256_tree", "manual_receipt"}:
                raise ValueError(f"{artifact['id']}/{channel_id}: verified has no usable receipt")
            if verification.get("type") == "manual_receipt" and not all(
                verification.get(key) for key in ("observed_at", "receipt")
            ):
                raise ValueError(f"{artifact['id']}/{channel_id}: incomplete manual receipt")
    for catalogue in ledger.get("catalogues", []):
        if catalogue.get("artifact") not in ids or catalogue.get("status") not in CATALOGUE_STATES:
            raise ValueError(f"invalid catalogue declaration: {catalogue.get('id')}")
        handoff = root / catalogue.get("handoff", "")
        if not handoff.is_file():
            raise ValueError(f"{catalogue['id']}: missing hand-off {catalogue.get('handoff')}")


def audit(root: pathlib.Path, ledger_path: pathlib.Path, online: bool, timeout: float) -> dict:
    ledger = load_json(ledger_path)
    validate_ledger(root, ledger)
    local: dict[str, dict] = {}
    artifacts: list[dict] = []
    for artifact in ledger["artifacts"]:
        receipt = verify_local_tree(root, artifact)
        local[artifact["id"]] = receipt
        transport = verify_transport(root, artifact, receipt)
        artifacts.append({
            "id": artifact["id"],
            "directory": artifact["directory"],
            "local": {key: value for key, value in receipt.items() if key not in {"manifest", "sums"}},
            "transport": transport,
            "channels": [],
        })
    by_id = {item["id"]: item for item in artifacts}
    for artifact in ledger["artifacts"]:
        source_id = artifact.get("source_artifact")
        if source_id is not None:
            source = local.get(source_id)
            pointer = local[artifact["id"]]["manifest"].get("source", {})
            if source is None or pointer.get("manifest_sha256") != source["manifest_sha256"]:
                raise ValueError(f"{artifact['id']}: source-artifact manifest binding disagrees")
        for channel in artifact["channels"]:
            result = {
                "id": channel["id"],
                "required": bool(channel.get("required")),
                "declared_status": channel["status"],
                "check": channel["verification"]["type"],
                "result": "not_checked" if not online else "manual_receipt",
            }
            if online and channel["verification"]["type"] == "sha256_tree":
                try:
                    result["receipt"] = verify_remote_tree(channel, local[artifact["id"]], timeout)
                    result["result"] = "verified" if channel["status"] == "verified" else "ready_to_promote"
                except (OSError, ValueError, UnicodeError, urllib.error.URLError) as error:
                    result["result"] = "failed" if channel["status"] == "verified" else "pending"
                    result["error"] = str(error)
            by_id[artifact["id"]]["channels"].append(result)
    return {
        "kind": "ainglish.distribution-audit.v1",
        "ledger": str(ledger_path.relative_to(root)),
        "release": ledger["release"],
        "mode": "online" if online else "offline",
        "artifacts": artifacts,
        "catalogues": ledger.get("catalogues", []),
    }


def incomplete(report: dict) -> list[str]:
    problems: list[str] = []
    for artifact in report["artifacts"]:
        for channel in artifact["channels"]:
            if channel["declared_status"] == "verified" and channel["result"] == "failed":
                problems.append(f"{artifact['id']}/{channel['id']}: verified channel failed")
            if channel["required"] and channel["declared_status"] != "verified":
                problems.append(f"{artifact['id']}/{channel['id']}: required channel is not declared verified")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=pathlib.Path, default=pathlib.Path("distribution/release-3.json"))
    parser.add_argument("--online", action="store_true", help="download and verify automated channel trees")
    parser.add_argument("--require-complete", action="store_true", help="fail when any required channel remains pending")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args(argv)
    root = pathlib.Path(__file__).resolve().parent.parent
    ledger_path = args.ledger if args.ledger.is_absolute() else root / args.ledger
    try:
        report = audit(root, ledger_path, args.online, args.timeout)
        problems = incomplete(report)
        report["complete"] = not problems
        report["problems"] = problems
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1 if problems and (args.require_complete or any("failed" in item for item in problems)) else 0
    except Exception as error:
        print(json.dumps({"kind": "ainglish.distribution-audit.v1", "fatal": str(error)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
