#!/usr/bin/env python3
"""Build the single deterministic tar.gz required for a dataset deposit."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import pathlib
import tarfile
import tempfile


def build(pack: pathlib.Path, output: pathlib.Path) -> str:
    pack = pack.resolve()
    if not pack.is_dir() or not (pack / "MANIFEST.json").is_file():
        raise ValueError("pack must be a built Ainglish training pack")
    output.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        root = tarfile.TarInfo(pack.name)
        root.type = tarfile.DIRTYPE
        root.mode = 0o755
        root.mtime = root.uid = root.gid = 0
        archive.addfile(root)
        for path in sorted(pack.rglob("*")):
            relative = pathlib.PurePosixPath(pack.name) / path.relative_to(pack)
            info = tarfile.TarInfo(relative.as_posix())
            info.uid = info.gid = info.mtime = 0
            info.uname = info.gname = ""
            if path.is_dir():
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                archive.addfile(info)
            elif path.is_file():
                data = path.read_bytes()
                info.mode = 0o644
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            else:
                raise ValueError(f"unsupported pack member: {path}")
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(buffer.getvalue())
    return hashlib.sha256(output.read_bytes()).hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        if not args.output.is_file():
            raise FileNotFoundError(args.output)
        with tempfile.TemporaryDirectory() as tmp:
            rebuilt = pathlib.Path(tmp) / args.output.name
            digest = build(args.pack, rebuilt)
            if rebuilt.read_bytes() != args.output.read_bytes():
                raise ValueError("deposit archive is not reproducible")
        print(f"{digest}  {args.output.name}")
    else:
        print(f"{build(args.pack, args.output)}  {args.output.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
