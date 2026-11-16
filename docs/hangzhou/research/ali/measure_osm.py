"""Reproduce research measurements from frozen OSM WGS84 geometry.

This does not build runtime assets, select entrance points or infer heights.
Polygon metrics use a WGS84 ECEF -> local ENU tangent projection, metres.
OSM geometry is volunteered mapping, not a cadastral survey.
"""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PARCELS = {645135612: "alibaba-a", 544285896: "alibaba-b",
           645093961: "alibaba-c", 1228913717: "cainiao-headquarters"}


def read(name):
    path = ROOT / "snapshots" / name
    return json.loads(path.read_text()), hashlib.sha256(path.read_bytes()).hexdigest()


def points(geom):
    return [(p["lon"], p["lat"]) for p in geom]


def rings(obj):
    if obj["type"] == "way":
        return [points(obj.get("geometry", []))], [], []
    out, inner, unresolved = [], [], []
    for role, bucket in (("outer", out), ("inner", inner)):
        parts = [points(m["geometry"]) for m in obj.get("members", [])
                 if m.get("role") == role and m.get("geometry")]
        while parts:
            ring = parts.pop(0)
            while ring[0] != ring[-1]:
                found = False
                for i, p in enumerate(parts):
                    if p[0] == ring[-1]:
                        ring.extend(p[1:]); parts.pop(i); found = True; break
                    if p[-1] == ring[-1]:
                        ring.extend(p[-2::-1]); parts.pop(i); found = True; break
                if not found:
                    unresolved.append(ring); break
            if ring[0] == ring[-1]:
                bucket.append(ring)
    return out, inner, unresolved


def inside(point, polygon):
    x, y = point
    hit = False
    for (ax, ay), (bx, by) in zip(polygon, polygon[1:]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            hit = not hit
    return hit


def ecef(lon, lat):
    lon, lat = math.radians(lon), math.radians(lat)
    e2 = 6.6943799901413165e-3
    n = 6378137.0 / math.sqrt(1.0 - e2 * math.sin(lat) ** 2)
    return (n * math.cos(lat) * math.cos(lon),
            n * math.cos(lat) * math.sin(lon),
            n * (1.0 - e2) * math.sin(lat))


def enu(point, origin):
    xyz, ref = ecef(*point), ecef(*origin)
    dx, dy, dz = [a - b for a, b in zip(xyz, ref)]
    lon, lat = map(math.radians, origin)
    return (-math.sin(lon) * dx + math.cos(lon) * dy,
            -math.sin(lat) * math.cos(lon) * dx
            - math.sin(lat) * math.sin(lon) * dy + math.cos(lat) * dz)


def signed_area(poly):
    return sum(ax * by - bx * ay for (ax, ay), (bx, by)
               in zip(poly, poly[1:] + poly[:1])) / 2


def hull(p):
    p = sorted(set(p))
    def cross(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    lo, hi = [], []
    for pt in p:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], pt) <= 0:
            lo.pop()
        lo.append(pt)
    for pt in reversed(p):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], pt) <= 0:
            hi.pop()
        hi.append(pt)
    return lo[:-1] + hi[:-1]


def rect(p):
    h = hull(p)
    candidates = []
    for a, b in zip(h, h[1:] + h[:1]):
        theta = math.atan2(b[1] - a[1], b[0] - a[0])
        c, s = math.cos(theta), math.sin(theta)
        pr = [(x * c + y * s, -x * s + y * c) for x, y in p]
        w = max(x for x, y in pr) - min(x for x, y in pr)
        d = max(y for x, y in pr) - min(y for x, y in pr)
        if w < d:
            w, d, theta = d, w, theta + math.pi / 2
        candidates.append((w * d, w, d, (90 - math.degrees(theta)) % 180))
    _, w, d, bearing = min(candidates)
    return {"lengthM": round(w, 2), "widthM": round(d, 2),
            "longAxisBearingDegreesClockwiseFromNorthModulo180": round(bearing, 2)}


def summarize(obj):
    outer, inner, unresolved = rings(obj)
    if not outer:
        return None
    p = [pt for ring in outer for pt in ring[:-1]]
    xmin, xmax = min(x for x, y in p), max(x for x, y in p)
    ymin, ymax = min(y for x, y in p), max(y for x, y in p)
    origin = ((xmin + xmax) / 2, (ymin + ymax) / 2)
    local = [enu(pt, origin) for pt in p]
    area = sum(abs(signed_area([enu(pt, origin) for pt in r])) for r in outer)
    area -= sum(abs(signed_area([enu(pt, origin) for pt in r])) for r in inner)
    return {"osmType": obj["type"], "osmId": obj["id"],
            "osmVersion": obj.get("version"), "osmTimestamp": obj.get("timestamp"),
            "tags": obj.get("tags", {}), "crs": "EPSG:4326",
            "bboxCenterWgs84": list(origin), "boundsWgs84": [xmin, ymin, xmax, ymax],
            "areaM2": round(area, 2), "minimumRotatedEnvelope": rect(local),
            "outerRingsWgs84": outer, "innerRingsWgs84": inner,
            "unjoinedRings": unresolved,
            "relationMemberWayIds": [m["ref"] for m in obj.get("members", []) if m["type"] == "way"],
            "measurementBasis": "measured-from-osm-geometry",
            "uncertainty": "OSM source plan accuracy unknown; ENU projection numerical error is negligible at these parcel extents. Envelope dimensions describe mapped outlines, not surveyed building dimensions; bearing modulo 180 does not identify an entrance or facade direction."}


def main():
    parcels_json, parcels_hash = read("overpass-site-geometries.json")
    buildings_json, buildings_hash = read("overpass-alibaba-buildings.json")
    p_objs = {e["id"]: e for e in parcels_json["elements"] if e["id"] in PARCELS}
    sites = {PARCELS[k]: {"parcel": summarize(v), "mappedBuildings": []}
             for k, v in p_objs.items()}
    member_ids = {m["ref"] for e in buildings_json["elements"] if e["type"] == "relation"
                  for m in e.get("members", []) if m["type"] == "way"}
    for obj in buildings_json["elements"]:
        if obj["type"] == "way" and obj["id"] in member_ids:
            continue
        record = summarize(obj)
        if record is None:
            continue
        p = [pt for ring in record["outerRingsWgs84"] for pt in ring[:-1]]
        matched = []
        for osm_id, parcel_obj in p_objs.items():
            parcel = points(parcel_obj["geometry"])
            fraction = sum(inside(pt, parcel) for pt in p) / len(p)
            if fraction >= 0.8:
                matched.append((PARCELS[osm_id], fraction))
        for site_id, fraction in matched:
            tagged = dict(record)
            tagged["parcelMatch"] = {"method": "at-least-80-percent-outer-vertices-inside-parcel",
                                    "fraction": fraction, "multipleMatches": len(matched) > 1}
            sites[site_id]["mappedBuildings"].append(tagged)
    for e in parcels_json["elements"]:
        if e["id"] == 1355173307:
            sites["cainiao-headquarters"]["mappedBuildings"].append(summarize(e))
    out = {"schemaVersion": 1, "generatedAt": "2026-10-12", "scale": "real metres, unscaled",
           "projectionMethod": "WGS84 ellipsoid ECEF to local east/north tangent at each footprint bbox center",
           "sourceHashes": {"snapshots/overpass-site-geometries.json": parcels_hash,
                            "snapshots/overpass-alibaba-buildings.json": buildings_hash},
           "notes": ["Mapped OSM entities are not necessarily building units.",
                     "No absent height tag is converted to an invented height.",
                     "Parcel containment is a research association, not a cadastral/legal boundary assertion.",
                     "Do not use bboxCenterWgs84 as a spawn or arrival point; many centers lie inside buildings/water."],
           "sites": sites}
    (ROOT / "site-footprints.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    for id, site in sites.items():
        print(id, "parcel", site["parcel"]["areaM2"], "mapped entities", len(site["mappedBuildings"]))
        for b in site["mappedBuildings"]:
            print(b["osmType"], b["osmId"], b["tags"], b["minimumRotatedEnvelope"])


if __name__ == "__main__":
    main()
