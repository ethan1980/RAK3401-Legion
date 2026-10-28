#!/usr/bin/env python3
"""Verify the published release stage, source commit and uploaded asset digests."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

from prepare_release import prepare_release


def verify_published_release(directory, commit, published):
    directory = Path(directory)
    expected = prepare_release(directory, commit)
    if (
        published.get("draft") is not False
        or published.get("prerelease") is not expected["prerelease"]
        or published.get("tag_name") != expected["tag"]
        or published.get("target_commitish") != commit
    ):
        raise ValueError("Published release must match the build commit and tag")
    files = {path.name: path for path in directory.iterdir() if path.is_file()}
    assets = published.get("assets", [])
    by_name = {asset["name"]: asset for asset in assets}
    if len(by_name) != len(assets) or set(by_name) != set(files):
        raise ValueError("Published release has missing, extra or duplicate assets")
    for name, path in files.items():
        asset = by_name[name]
        digest = f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
        if (
            asset.get("state") != "uploaded"
            or asset.get("size") != path.stat().st_size
            or asset.get("digest") != digest
        ):
            raise ValueError(f"Published asset does not match the build: {name}")
    return expected["tag"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    args = parser.parse_args()
    tag = verify_published_release(args.directory, args.commit, json.load(sys.stdin))
    print(f"Verified published assets and source provenance: {tag}")


if __name__ == "__main__":
    main()
