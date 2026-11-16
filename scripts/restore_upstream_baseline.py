"""Materialize available immutable baseline blobs into an independent directory.

Doesn't reset/checkout the worktree, doesn't replace existing files, disables
implicit lazy fetching. Missing objects and LFS bodies are reported separately.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "73603f31416de4111f10783f512c1101bd738a97"
GIT = "git"


def restore(output):
    output = Path(output).resolve()
    if output == ROOT or ROOT not in output.parents or ".git" in output.relative_to(ROOT).parts:
        raise ValueError("Use a separate directory inside this project")
    output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "GIT_NO_LAZY_FETCH": "1"}
    entries = subprocess.check_output([GIT, "ls-tree", "-rz", "--full-tree", COMMIT], cwd=ROOT, env=env)
    reader = subprocess.Popen([GIT, "cat-file", "--batch"], cwd=ROOT, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    missing, conflicts, lfs = [], [], []
    restored, preserved = 0, 0
    for row in entries.split(b"\0"):
        if not row:
            continue
        header, relative = row.split(b"\t", 1)
        mode, kind, sha = header.decode().split()
        path = relative.decode()
        dest = output / path
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError(f"Unexpected baseline entry: {mode} {kind} {path}")
        reader.stdin.write(sha.encode()+b"\n"); reader.stdin.flush()
        response = reader.stdout.readline().decode().strip().split()
        if response[-1] == "missing":
            missing.append({"path": path, "oid": sha})
            continue
        size = int(response[2])
        content = reader.stdout.read(size)
        if len(content) != size or reader.stdout.read(1) != b"\n":
            raise ValueError("Incomplete Git object response")
        calculated = hashlib.sha1(f"blob {size}\0".encode()+content).hexdigest()
        if calculated != sha:
            raise ValueError(f"Git object hash mismatch: {path}")
        if content.startswith(b"version https://git-lfs.github.com/spec/v1\n"):
            pointer = content.decode()
            oid = re.search(r"oid sha256:([0-9a-f]{64})", pointer)
            length = re.search(r"size (\d+)", pointer)
            if not oid or not length:
                raise ValueError(f"Invalid LFS pointer: {path}")
            lfs.append({"path": path, "sha256": oid[1], "bytes": int(length[1]), "status": "pointer-only"})
            if dest.exists() and dest.stat().st_size == int(length[1]) and hashlib.sha256(dest.read_bytes()).hexdigest() == oid[1]:
                lfs[-1]["status"] = "verified-body"
                preserved += 1
                continue
        if dest.exists():
            if dest.read_bytes() != content:
                conflicts.append(path)
            else:
                preserved += 1
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation protects files that arrived during inspection.
        with dest.open("xb") as handle:
            handle.write(content)
        if mode == "100755":
            dest.chmod(0o755)
        restored += 1
    reader.stdin.close(); reader.wait()
    report = {"commit": COMMIT, "output": str(output), "restored": restored, "preserved": preserved,
              "missingObjects": missing, "existingConflicts": conflicts, "lfs": lfs,
              "runtimeLfsBytes": sum(r["bytes"] for r in lfs if r["path"].startswith("public/")),
              "status": "incomplete" if missing or conflicts or lfs else "source-ready"}
    audit = ROOT / "docs/hangzhou/audit"
    audit.mkdir(parents=True, exist_ok=True)
    (audit / "baseline-object-inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k not in ("lfs", "missingObjects")}, ensure_ascii=False, indent=2))
    print(f"Missing Git blobs: {len(missing)}; LFS pointers: {len(lfs)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="baseline/upstream")
    restore(parser.parse_args().output)
