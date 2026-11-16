"""Extract fixed-snapshot WGS84 geometry, including authoritative OSM road refs.

No inferred heights/facades and no commercial coordinates. Full intersecting
features are retained for later clipping; OSM areas preserve courtyard holes.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import osmium
from shapely import wkb
from shapely.geometry import box, mapping, Point, LineString
from city_config import ROOT, load_city


class HangzhouExtractor(osmium.SimpleHandler):
    def __init__(self, bbox):
        super().__init__()
        self.bounds = box(*bbox)
        self.layers = {key: [] for key in ("roads", "buildings", "green", "water", "pois", "places", "elevation")}
        self.factory = osmium.geom.WKBFactory()
        self.failures = Counter()

    def store(self, layer, typ, ident, tags, geometry, extra=None):
        if geometry.is_empty or not geometry.intersects(self.bounds):
            return
        if not geometry.is_valid:
            self.failures[f"{layer}:invalid"] += 1
            return
        self.layers[layer].append({"type": "Feature", "id": f"{typ}/{ident}",
            "properties": {"osm_type": typ, "osm_id": ident, "tags": tags,
                           "name": tags.get("name:zh", tags.get("name", "")),
                           "source": "OpenStreetMap", "crs": "EPSG:4326", "license": "ODbL-1.0", **(extra or {})},
            "geometry": mapping(geometry)})

    def node(self, node):
        if not node.location.valid():
            return
        lon, lat = node.location.lon, node.location.lat
        b = self.bounds.bounds
        if not (b[0] <= lon <= b[2] and b[1] <= lat <= b[3]):
            return
        tags = dict(node.tags)
        if not tags:
            return
        point = Point(lon, lat)
        if "ele" in tags:
            self.store("elevation", "node", node.id, tags, point, {"elevationStatus": "tagged-unverified; not a DEM"})
        if any(key in tags for key in ("name", "name:zh", "amenity", "shop", "tourism", "railway")) or tags.get("highway") in ("traffic_signals", "bus_stop"):
            self.store("pois", "node", node.id, tags, point)

    def way(self, way):
        tags = dict(way.tags)
        if "highway" not in tags and "waterway" not in tags:
            return
        if any(not node.location.valid() for node in way.nodes):
            self.failures["way:missing-nodes"] += 1
            return
        coords = [(node.lon, node.lat) for node in way.nodes]
        if len(coords) < 2:
            return
        xs, ys = zip(*coords); b = self.bounds.bounds
        if max(xs) < b[0] or min(xs) > b[2] or max(ys) < b[1] or min(ys) > b[3]:
            return
        if "highway" in tags:
            self.store("roads", "way", way.id, tags, LineString(coords),
                       {"nodeIds": [str(node.ref) for node in way.nodes],
                        "grade": tags.get("layer", "0"), "bridge": tags.get("bridge", "no"),
                        "tunnel": tags.get("tunnel", "no")})
        if "waterway" in tags:
            self.store("water", "way", way.id, tags, LineString(coords), {"representation": "centerline"})

    def area(self, area):
        tags = dict(area.tags)
        layer = ("buildings" if "building" in tags or "building:part" in tags else
                 "water" if tags.get("natural") == "water" or tags.get("landuse") in ("reservoir", "basin") or tags.get("waterway") == "riverbank" else
                 "green" if tags.get("leisure") in ("park", "garden", "nature_reserve", "pitch") or tags.get("landuse") in ("forest", "grass", "meadow", "recreation_ground") or tags.get("natural") in ("wood", "scrub", "grassland") else None)
        named = bool(tags.get("name:zh") or tags.get("name"))
        if not layer and not named:
            return
        try:
            geometry = wkb.loads(self.factory.create_multipolygon(area), hex=True)
            typ = "way" if area.from_way() else "relation"
            if layer:
                self.store(layer, typ, area.orig_id(), tags, geometry,
                           {"heightStatus": "tagged-unverified" if "height" in tags else "levels-only-unverified" if "building:levels" in tags else "unknown"} if layer == "buildings" else {"representation": "area"})
            if named:
                self.store("places", typ, area.orig_id(), tags, geometry)
        except (RuntimeError, ValueError):
            self.failures[f"{layer}:assembly"] += 1


def extract(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    manifest_path = source.parent / "source-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("status") != "source-verified" or not manifest.get("checksumVerified"):
        raise ValueError("A verified full Geofabrik snapshot is required")
    sha = hashlib.sha256()
    with source.open("rb") as stream:
        while chunk := stream.read(1024*1024): sha.update(chunk)
    if sha.hexdigest() != manifest["sha256"] or source.stat().st_size != manifest["bytes"]:
        raise ValueError("Source snapshot differs from its manifest")
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a fresh candidate extraction directory; existing data is preserved")
    output.mkdir(parents=True, exist_ok=True)
    city = load_city("hangzhou")
    handler = HangzhouExtractor(city["geography"]["bboxWGS84"])
    handler.apply_file(str(source), locations=True, idx="flex_mem")
    hashes = {}
    for layer, features in handler.layers.items():
        target = output / f"{layer}.geojson"
        target.write_text(json.dumps({"type": "FeatureCollection", "features": features},ensure_ascii=False,separators=(",",":")))
        hashes[layer] = hashlib.sha256(target.read_bytes()).hexdigest()
    report = {"cityId": "hangzhou", "source": manifest, "bboxWGS84": city["geography"]["bboxWGS84"],
              "crs": "EPSG:4326", "license": "ODbL-1.0", "attribution": "© OpenStreetMap contributors",
              "counts": {key: len(value) for key,value in handler.layers.items()}, "failures": dict(handler.failures),
              "sha256": hashes, "roadConnectivity": "original OSM nodeIds; geometry intersections are not junctions",
              "terrainStatus": "DEM required; OSM elevation nodes are not a continuous terrain source"}
    (output / "extraction-manifest.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps({"counts":report["counts"],"failures":report["failures"],"output":str(output)},ensure_ascii=False,indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="data/raw/hangzhou/zhejiang-261011.osm.pbf")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    extract(args.source, args.output)
