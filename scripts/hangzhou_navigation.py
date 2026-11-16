"""Build an OSM-identity graph; geometric crossings never create junctions.

The browser's noded {nodes, edges} interface and unrestricted arcade driving
remain unchanged. Shared OSM node IDs establish connectivity, including ramp
transitions. Elevated road geometry/collision needs its own acceptance pass.
"""
from __future__ import annotations
import math
from collections import defaultdict, deque


def build_navigation(roads):
    nodes, edges, lookup = [], [], {}
    layers = defaultdict(set)
    edge_keys = set()
    road_nodes = {}
    for road in roads:
        refs, points = road.get("nodeIds"), road["points"]
        if not refs or len(refs) != len(points):
            raise ValueError(f"{road['id']}: source node IDs required; no geometric fallback")
        previous = None
        chain = []
        for ref, point in zip(refs, points):
            if len(point) != 2 or not all(math.isfinite(v) for v in point):
                raise ValueError(f"{road['id']}: invalid point")
            key = str(ref)
            if key not in lookup:
                lookup[key] = len(nodes)
                nodes.append(list(point))
            index = lookup[key]
            if math.dist(nodes[index], point) > 0.02:
                raise ValueError(f"Shared node {ref} has inconsistent coordinates")
            layers[key].add(str(road.get("grade", "0")))
            chain.append(index)
            if previous is not None and previous != index:
                pair = tuple(sorted((previous, index)))
                if pair not in edge_keys:
                    edges.append(list(pair))
                    edge_keys.add(pair)
            previous = index
        road_nodes[road["id"]] = chain
    adjacent = [[] for _ in nodes]
    for a, b in edges:
        adjacent[a].append(b)
        adjacent[b].append(a)
    components = [-1] * len(nodes)
    sizes = []
    for start in range(len(nodes)):
        if components[start] >= 0:
            continue
        component = len(sizes)
        queue, size = deque([start]), 0
        components[start] = component
        while queue:
            index = queue.popleft()
            size += 1
            for other in adjacent[index]:
                if components[other] < 0:
                    components[other] = component
                    queue.append(other)
        sizes.append(size)
    main = max(range(len(sizes)), key=sizes.__getitem__) if sizes else None
    return {
        "nodes": nodes, "edges": edges,
        "sourceNodeIds": list(lookup), "componentIds": components,
        "roadNodes": road_nodes,
        "meta": {"connectivity": "shared OSM node identity; no planar intersection noding",
                 "componentSizes": sizes, "mainComponent": main,
                 "gradeTransitions": {key: sorted(values) for key, values in layers.items() if len(values) > 1},
                 "geometryStatus": "bridge decks, ramps and collision require independent verification"}
    }


def nearest_connected_arrival(point, roads, graph, blocked=None, max_distance=500):
    """Snap to a main-component segment with clearance, never to an isolated road.

    blocked(x,north) must include footprint/water/prop exclusions at integration.
    No usable segment yields a blocker (None), not a fabricated destination.
    """
    main = graph["meta"]["mainComponent"]
    best = None
    for road in roads:
        indices = graph["roadNodes"][road["id"]]
        for n in range(1, len(road["points"])):
            if graph["componentIds"][indices[n]] != main:
                continue
            a, b = road["points"][n - 1:n + 1]
            dx, dz = b[0] - a[0], b[1] - a[1]
            length2 = dx * dx + dz * dz
            if length2 < .01:
                continue
            t = max(0, min(1, ((point[0]-a[0])*dx+(point[1]-a[1])*dz)/length2))
            x, z = a[0] + t * dx, a[1] + t * dz
            distance = math.hypot(point[0] - x, point[1] - z)
            if distance > max_distance or (blocked and blocked(x, z)):
                continue
            if best is None or distance < best["distance"]:
                best = {"arrival": [x, z], "yaw": math.atan2(dx, dz), "distance": distance,
                        "roadId": road["id"], "grade": road.get("grade", "0"),
                        "component": main, "segmentNodes": indices[n - 1:n + 1]}
    return best
