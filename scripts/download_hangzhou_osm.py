"""Resumable, fixed-snapshot Zhejiang download. Never accepts a partial as data."""
from __future__ import annotations
import hashlib
import json
import re
import time
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from scripts.city_config import ROOT, load_city


def open_source(url, headers=None):
    return urlopen(Request(url, headers={"User-Agent": "GTA_HZ-data-preparation/0.1", **(headers or {})}), timeout=60)


def download_ranges(url, part, connections):
    """Bounded independent range files; only a fully assembled checksum can pass."""
    with open_source(url, {"Range": "bytes=0-0", "Accept-Encoding": "identity"}) as response:
        match = re.fullmatch(r"bytes 0-0/(\d+)", response.headers.get("Content-Range", ""))
        if response.status != 206 or not match:
            raise ValueError("Server does not support verified byte ranges")
        total = int(match[1]); headers = dict(response.headers)
        if response.read() == b"":
            raise ValueError("Empty source range")
    if total > 200 * 1024 * 1024:
        raise ValueError("Snapshot exceeds budget")
    assembled = part.with_name(part.name+".assembled")
    if assembled.exists():
        if assembled.stat().st_size != total:
            raise ValueError("Existing incomplete assembly preserved; inspect before retry")
        return assembled, total, headers
    prefix = part.stat().st_size if part.exists() else 0
    if prefix > total:
        raise ValueError("Partial exceeds snapshot length")
    chunks = part.parent / (part.name + ".chunks")
    chunks.mkdir(exist_ok=True)
    ranges = [(start, min(total-1,start+2*1024*1024-1)) for start in range(prefix,total,2*1024*1024)]

    def piece(bounds):
        start, end = bounds
        path = chunks / f"{start}-{end}.part"
        expected = end-start+1
        for attempt in range(5):
            current = path.stat().st_size if path.exists() else 0
            if current == expected:
                return path
            if current > expected:
                raise ValueError(f"Range {start} exceeds expected bytes")
            position = start+current
            try:
                with open_source(url, {"Range": f"bytes={position}-{end}", "Accept-Encoding":"identity"}) as response:
                    wanted = f"bytes {position}-{end}/{total}"
                    if response.status != 206 or response.headers.get("Content-Range") != wanted:
                        raise ValueError("Source range mismatch; chunks preserved")
                    with path.open("ab" if current else "wb") as writer:
                        while chunk := response.read(128*1024):
                            writer.write(chunk); current += len(chunk)
                            if current > expected:
                                raise ValueError("Source sent excess range bytes")
                if current != expected:
                    raise OSError("Incomplete range")
                return path
            except (OSError, TimeoutError) as error:
                if attempt == 4:
                    raise
                print(f"Range {start} retry {attempt+1}: {error}",flush=True)
                time.sleep(min(5*(attempt+1),20))
    print(f"Resuming {prefix}/{total} with {connections} connections, {len(ranges)} ranges",flush=True)
    with ThreadPoolExecutor(max_workers=connections) as pool:
        futures = [pool.submit(piece,bounds) for bounds in ranges]
        done = 0
        for future in as_completed(futures):
            future.result(); done += 1
            print(f"Ranges complete {done}/{len(ranges)}",flush=True)
    with assembled.open("xb") as writer:
        if part.exists():
            with part.open("rb") as reader: shutil.copyfileobj(reader,writer)
        for start,end in ranges:
            with (chunks/f"{start}-{end}.part").open("rb") as reader: shutil.copyfileobj(reader,writer)
    if assembled.stat().st_size != total:
        raise ValueError("Assembly length mismatch")
    return assembled, total, headers


def download(snapshot="261011", connections=1):
    if not re.fullmatch(r"\d{6}", snapshot):
        raise ValueError("Use a fixed YYMMDD snapshot, not latest")
    folder = ROOT / "data/raw/hangzhou"
    folder.mkdir(parents=True, exist_ok=True)
    url = f"https://download.geofabrik.de/asia/china/zhejiang-{snapshot}.osm.pbf"
    target = folder / f"zhejiang-{snapshot}.osm.pbf"
    part = target.with_suffix(target.suffix + ".part")
    with open_source(url + ".md5") as response:
        checksum = response.read(4096).decode().strip()
    expected = checksum.split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{32}", expected):
        raise ValueError("Invalid source MD5")
    total_length, headers = None, {}
    if not 1 <= connections <= 16:
        raise ValueError("connections must be between 1 and 16")
    if not target.exists() and connections > 1:
        candidate, total_length, headers = download_ranges(url,part,connections)
    elif not target.exists():
        for attempt in range(5):
            offset = part.stat().st_size if part.exists() else 0
            try:
                with open_source(url, {"Range": f"bytes={offset}-"} if offset else {}) as response:
                    headers = dict(response.headers)
                    if offset:
                        match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
                        if response.status != 206 or not match or int(match[1]) != offset:
                            raise ValueError("Server did not confirm resume range; partial preserved")
                        total_length = int(match[3])
                    else:
                        total_length = int(response.headers["Content-Length"])
                    if total_length > 200 * 1024 * 1024:
                        raise ValueError("Snapshot exceeds configured download budget")
                    with part.open("ab" if offset else "wb") as output:
                        next_report = offset + 5 * 1024 * 1024
                        while chunk := response.read(256 * 1024):
                            output.write(chunk)
                            offset += len(chunk)
                            if offset > total_length:
                                raise ValueError("Response exceeded expected length")
                            if offset >= next_report:
                                print(f"Downloaded {offset}/{total_length} bytes", flush=True)
                                next_report = offset + 5 * 1024 * 1024
                if offset != total_length:
                    raise OSError("Incomplete response")
                break
            except (OSError, TimeoutError) as error:
                print(f"Attempt {attempt+1}: {error}; partial retained", flush=True)
                if attempt == 4:
                    raise
                time.sleep(min(5 * (attempt + 1), 20))
        candidate = part
    else:
        candidate = target
    md5, sha = hashlib.md5(), hashlib.sha256()
    with candidate.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            md5.update(chunk); sha.update(chunk)
    if md5.hexdigest() != expected:
        raise ValueError("Snapshot MD5 mismatch; file retained, no manifest accepted")
    # PBF header comes from the downloaded file, never inferred from URL/date.
    import osmium
    with osmium.io.Reader(osmium.io.File(str(candidate), "pbf")) as reader:
        header = reader.header()
        timestamp = header.get("osmosis_replication_timestamp")
        generator = header.get("generator")
    if candidate != target:
        candidate.replace(target)
    city = load_city("hangzhou")
    manifest = {"sourceUrl": url, "sourcePage": "https://download.geofabrik.de/asia/china/zhejiang.html",
                "downloadedAtUTC": datetime.now(timezone.utc).isoformat(), "snapshot": snapshot,
                "sourceLastModified": headers.get("Last-Modified"), "osmReplicationTimestamp": timestamp,
                "generator": generator, "bytes": target.stat().st_size, "md5": expected,
                "sha256": sha.hexdigest(), "checksumVerified": True, "crs": "EPSG:4326",
                "license": "ODbL-1.0", "attribution": "© OpenStreetMap contributors",
                "licenseUrl": "https://www.openstreetmap.org/copyright",
                "bboxWGS84": city["geography"]["bboxWGS84"], "status": "source-verified"}
    (folder / "source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+"\n")
    (folder / f"zhejiang-{snapshot}.osm.pbf.md5").write_text(checksum+"\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", default="261011")
    parser.add_argument("--connections", type=int, default=1)
    args = parser.parse_args()
    download(args.snapshot,args.connections)
