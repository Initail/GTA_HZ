"""Conforming, closed foundation mesh; ENU coordinates are already game units."""
import math
from collections import Counter

def edge(a, b):
    return tuple(sorted((a, b)))

def closed_foundation(triangles, ground, floor):
    triangles = [tuple(tuple(p) for p in t) for t in triangles]
    heights = {}
    def y(p):
        if p not in heights:
            heights[p] = ground(*p)
        return heights[p]
    def midpoint(a, b):
        return ((a[0]+b[0])/2, (a[1]+b[1])/2)
    worst = 0
    for iteration in range(40):
        split = set(); worst = 0
        for t in triangles:
            lengths = [math.dist(t[i], t[(i+1)%3]) for i in range(3)]
            j = max(range(3), key=lengths.__getitem__)
            error = max(abs(y(midpoint(t[i], t[(i+1)%3]))-(y(t[i])+y(t[(i+1)%3]))/2) for i in range(3))
            center = (sum(p[0] for p in t)/3, sum(p[1] for p in t)/3)
            error = max(error, abs(y(center)-sum(y(p) for p in t)/3)); worst = max(worst, error)
            if lengths[j] > 2 or error > .01 and lengths[j] > .03:
                split.add(edge(t[j], t[(j+1)%3]))
        if not split:
            break
        fresh = []
        for t in triangles:
            flags = [edge(t[i], t[(i+1)%3]) in split for i in range(3)]
            count = sum(flags)
            if not count:
                fresh.append(t); continue
            if count == 1:
                i = flags.index(True); a,b,c = t[i],t[(i+1)%3],t[(i+2)%3]; m = midpoint(a,b)
                fresh.extend([(a,m,c),(m,b,c)])
            elif count == 2:
                i = next(i for i in range(3) if flags[i] and flags[(i+1)%3])
                a,b,c = t[i],t[(i+1)%3],t[(i+2)%3]; m,n = midpoint(a,b),midpoint(b,c)
                fresh.extend([(b,n,m),(a,m,c),(m,n,c)])
            else:
                a,b,c = t; m,n,o = midpoint(a,b),midpoint(b,c),midpoint(c,a)
                fresh.extend([(a,m,o),(m,b,n),(o,n,c),(m,n,o)])
        triangles = fresh
    else:
        raise ValueError('Foundation conforming refinement did not converge')
    if worst > .01:
        raise ValueError('Foundation bottom height approximation failed')
    counts = Counter(edge(t[i],t[(i+1)%3]) for t in triangles for i in range(3))
    if any(v not in (1,2) for v in counts.values()):
        raise ValueError('Nonmanifold foundation planar mesh')
    faces = []
    for t in triangles:
        faces.append([(x,z,floor) for x,z in t])
        faces.append([(x,z,y((x,z))) for x,z in reversed(t)])
        for i in range(3):
            a,b = t[i],t[(i+1)%3]
            if counts[edge(a,b)] != 1:
                continue
            aa,bb = (*a,y(a)),(*b,y(b)); at,bt = (*a,floor),(*b,floor)
            faces.extend([(aa,bb,bt),(aa,bt,at)])
    return faces, worst, min(heights.values())
