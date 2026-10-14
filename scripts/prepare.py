#!/usr/bin/env python3
"""Prepare the pinned upstream checkout without overwriting local changes."""

import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = Path("variants/nrf52840/rak3401_legion/platformio.ini")


def run(*args, cwd=None, capture=False):
    return subprocess.run(
        args, cwd=cwd, check=True, text=True, capture_output=capture
    ).stdout


def load_config():
    config = json.loads((ROOT / "upstream.json").read_text())
    if not re.fullmatch(r"[0-9a-f]{40}", config["commit"]):
        raise ValueError("upstream.commit must be a complete commit SHA")
    if config["repository"] != "https://github.com/meshtastic/firmware.git":
        raise ValueError("Unexpected upstream repository")
    return config


def check_checkout(dest, config, patch):
    actual = run("git", "rev-parse", "HEAD", cwd=dest, capture=True).strip()
    if actual != config["commit"]:
        raise ValueError(f"Unexpected upstream HEAD: {actual}; use a new destination")
    diff = run("git", "diff", "HEAD", "--", cwd=dest, capture=True)
    if diff not in ("", patch):
        raise ValueError("Checkout has local changes outside the exact Legion patch")
    untracked = run(
        "git", "ls-files", "--others", "--exclude-standard", cwd=dest, capture=True
    ).splitlines()
    if set(untracked) - {PROFILE_PATH.as_posix()}:
        raise ValueError("Checkout has unexpected untracked files")
    profile = dest / PROFILE_PATH
    if (
        profile.exists()
        and profile.read_bytes() != (ROOT / "profiles/platformio.ini").read_bytes()
    ):
        raise ValueError("Legion profile has local changes")
    return bool(diff)


def prepare(dest, *, submodules=True):
    config = load_config()
    patches = [ROOT / name for name in config["patches"]]
    patch = "".join(path.read_text() for path in patches)
    dest = Path(dest).resolve()
    if not dest.exists():
        dest.mkdir(parents=True)
        run("git", "init", str(dest))
        run("git", "remote", "add", "origin", config["repository"], cwd=dest)
        run("git", "fetch", "--depth=1", "origin", config["commit"], cwd=dest)
        run("git", "checkout", "--detach", "FETCH_HEAD", cwd=dest)
    elif not (dest / ".git").exists():
        raise ValueError("Destination exists and is not a Git checkout")

    already_applied = check_checkout(dest, config, patch)
    if not already_applied:
        run("git", "apply", "--check", *(str(p) for p in patches), cwd=dest)
        run("git", "apply", *(str(p) for p in patches), cwd=dest)
    profile = dest / PROFILE_PATH
    profile.parent.mkdir(parents=True, exist_ok=True)
    profile.write_bytes((ROOT / "profiles/platformio.ini").read_bytes())
    if submodules:
        run("git", "submodule", "update", "--init", "--recursive", cwd=dest)
    check_checkout(dest, config, patch)
    print(f"Prepared Legion {config['legion_version']} on {config['commit']}")
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=ROOT / ".work/firmware")
    parser.add_argument("--no-submodules", action="store_true")
    args = parser.parse_args()
    prepare(args.dest, submodules=not args.no_submodules)


if __name__ == "__main__":
    main()
