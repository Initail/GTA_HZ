"""Install verified LFS bodies only over their exact baseline pointers.

Refuses to replace a modified asset. Operates on the independent baseline and
optional root copy; does not checkout, delete, synthesize or fetch any asset.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024*1024): sha.update(chunk)
    return sha.hexdigest()


def hydrate(output, inventory):
    output = Path(output).resolve()
    if output != ROOT and ROOT not in output.parents:
        raise ValueError("Expected output inside this project")
    report = {"output": str(output), "verified": [], "pending": [], "conflicts": []}
    for entry in inventory["lfs"]:
        if not entry["path"].startswith("public/"):
            continue
        sha = entry["sha256"]
        source = ROOT / ".git/lfs/objects" / sha[:2] / sha[2:4] / sha
        dest = output / entry["path"]
        if dest.exists() and dest.stat().st_size == entry["bytes"] and digest(dest) == sha:
            report["verified"].append(entry["path"])
            continue
        if not source.is_file():
            report["pending"].append(entry["path"])
            continue
        if source.stat().st_size != entry["bytes"] or digest(source) != sha:
            raise ValueError(f"LFS cache integrity failure: {entry['path']}")
        if dest.exists():
            content = dest.read_bytes() if dest.stat().st_size < 1024 else b""
            if not content.startswith(b"version https://git-lfs.github.com/spec/v1\n") or f"oid sha256:{sha}\n".encode() not in content:
                report["conflicts"].append(entry["path"])
                continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".hydrate-part")
        if part.exists():
            raise ValueError(f"Existing install temporary file preserved: {part}")
        with part.open("xb") as writer, source.open("rb") as reader:
            shutil.copyfileobj(reader, writer)
        # Sole integration writer; output comparison above protects prior edits.
        os.replace(part, dest)
        report["verified"].append(entry["path"])
    report["status"] = "runtime-lfs-ready" if not report["pending"] and not report["conflicts"] else "incomplete"
    report["verifiedBytes"] = sum(e["bytes"] for e in inventory["lfs"] if e["path"] in report["verified"])
    target = ROOT / "docs/hangzhou/audit" / ("root-lfs-integrity.json" if output == ROOT else "baseline-lfs-integrity.json")
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({k:len(v) if isinstance(v,list) else v for k,v in report.items()},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="baseline/upstream")
    args = parser.parse_args()
    hydrate(args.output,json.loads((ROOT / "docs/hangzhou/audit/baseline-object-inventory.json").read_text()))
