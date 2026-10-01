#!/usr/bin/env python3
"""Minimum wall thickness of the printed insert parts, measured on dense CAD section slices.

    python3 tools/insert_wallcheck.py            # needs numpy + matplotlib (e.g. FreeCAD's bundled python)
Reads hardware/drawings/sections/insert-{L,S}-printed_sections.json (written by make_insert_*.py).
Every plane has a twin 0.3 mm away; a thin spot must show on both (grazing cuts of curved walls do not).
For every closed section loop of a printed part it samples the boundary every 0.1 mm and, for each sample,
finds the nearest boundary point that is not its own neighbourhood (> 1.2 mm away along the contour) and whose
mid-point lies inside the material. That distance is the local wall thickness in the slice plane.

Rules:
  * in-plane walls: ≥ 0.8 (2 perimeters at 0.4 nozzle) → OK; 0.55–0.8 → WARN; < 0.55 → FAIL.
  * thin by design is allowed only INSIDE a declared 3D zone (INTENDED_ZONES: part → [(reason, x0, x1, y0, y1, d0, d1)],
    |x| / |y| mirrored); such spots still FAIL below 0.55. A thin spot outside every zone is judged normally, so an
    exemption never covers a whole part.
  * direction: every printed part is printed with its layers normal to d (front or back face on the bed), so in the x- and
    y-slices a thickness measured ALONG d is a stack of layers, not a row of perimeters. Those "vertical" spots
    (|Δd| ≥ 0.7 × thickness) are reported separately and need ≥ 0.40 mm (≥ 2 layers + margin).
"""
import json
import os
import sys

import numpy as np
from matplotlib.path import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECT = os.path.join(ROOT, "hardware", "drawings", "sections")
sys.path.insert(0, os.path.join(ROOT, "hardware", "cad"))
import insert_params as IP  # noqa: E402

WARN, FAIL = 0.8, 0.55
VFAIL = 0.40            # vertical (layer-stack) thickness
_c0, _c1 = IP.cols_span()
_r0, _r1 = IP.rows_span()
_sk = IP.HALF - IP.PLATE_SKIRT_T
INTENDED_ZONES = {   # part → [(reason, |x| from..to, |y| from..to, d from..to)] (mirrored in x and y)
    "plate": [
        ("perforation webs 0.6 (coupon v1 row F)", _c0 - 0.1, _c1 + 0.1, 0.0, _r1 + 0.1, -0.1, IP.PLATE_T + 0.1),
        ("top drawer lip 0.6 thick", 0.0, _sk + 0.1, _sk - IP.LIP_IN - 0.1, _sk + 0.9, IP.LIP_D0 - 0.2, IP.LIP_D1 + 0.1),
        ("snap lips 0.6 thick with a 45° lead-in", IP.SNAP_X[0] - 0.6, IP.SNAP_X[1] + 0.1, _sk - IP.LIP_IN - 0.1, _sk + 0.9,
         IP.SNAP_D0 - 0.2, IP.SNAP_D1 + 0.1),
    ],
    "chassis": [
        ("snap tongues 0.8 wide (2 perimeters), 0.25 lead-in at the bed edge (coupon v1 row D)", IP.TONGUE_X[0] - 0.2,
         IP.TONGUE_X[1] + 0.1, IP.DECK_HALF_Y - IP.TONGUE_W - 0.2, IP.DECK_HALF_Y + 0.1, IP.DECK_D0 - 0.1, IP.TONGUE_D1 + 0.1),
    ],
    "key shell": [
        ("stem posts: standard MX keycap geometry (Ø5.5 post around a 4.1 × 1.3 cross → 0.7 walls; coupon v0 row C / v1 row E)",
         0.0, 3.0, min(abs(y) for _, y in IP.R.MX_SW_POS) - 3.0, max(abs(y) for _, y in IP.R.MX_SW_POS) + 3.0,
         IP.KS["key_back"] - 0.1, IP.KS["post_end"] + 0.1),
    ],
    "switch plate": [
        ("countersink floors 0.8 (1.5 plate, DIN 965 M2)", 8.3, 12.7, 0.0, 3.8, IP.KS["plate_front"] - 0.1, IP.KS["plate_back"] + 0.1),
    ],
}


def to3d(axis, value, u, w):
    """plane coordinates (u, w) of a slice → (x, y, d)."""
    if axis == "x":
        return value, u, w
    if axis == "y":
        return u, value, w
    return u, w, value


def zone_of(part, p3):
    x, y, d = abs(p3[0]), abs(p3[1]), p3[2]
    for z in INTENDED_ZONES.get(part, []):
        reason, x0, x1, y0, y1, d0, d1 = z
        if x0 <= x <= x1 and y0 <= y <= y1 and d0 <= d <= d1:
            return reason
    return None


def resample(loop, step=0.1):
    p = np.array(loop + [loop[0]], dtype=float)
    seg = np.diff(p, axis=0)
    ln = np.hypot(seg[:, 0], seg[:, 1])
    s = np.concatenate([[0], np.cumsum(ln)])
    n = max(int(s[-1] / step), 8)
    t = np.linspace(0, s[-1], n, endpoint=False)
    x = np.interp(t, s, p[:, 0])
    y = np.interp(t, s, p[:, 1])
    return np.stack([x, y], 1), t, s[-1]


def min_wall(loops, part, axis, value):
    """(free in-plane min, zoned in-plane min, vertical min); each (thickness, (p, q), zone reason)."""
    vertical = axis in ("x", "y")
    pts, arc, lid, lens = [], [], [], []
    for i, lp in enumerate(loops):
        q, t, L = resample(lp)
        pts.append(q)
        arc.append(t)
        lid.append(np.full(len(q), i))
        lens.append(np.full(len(q), L))
    P = np.concatenate(pts)
    A = np.concatenate(arc)
    I = np.concatenate(lid)
    Ls = np.concatenate(lens)
    if len(P) > 6000:
        k = len(P) // 6000 + 1
        P, A, I, Ls = P[::k], A[::k], I[::k], Ls[::k]
    paths = [Path(np.array(lp + [lp[0]])) for lp in loops]
    free, zoned, vert_ = (1e9, None, None), (1e9, None, None), (1e9, None, None)
    for j in range(len(P)):
        d = np.hypot(P[:, 0] - P[j, 0], P[:, 1] - P[j, 1])
        same = I == I[j]
        da = np.abs(A - A[j])
        da = np.minimum(da, Ls - da)
        mask = ~(same & (da < 1.2)) & (d > 1e-6)
        if not mask.any():
            continue
        cand = np.where(mask)[0]
        order = cand[np.argsort(d[cand])][:6]
        for k in order:
            mid = (P[j] + P[k]) / 2
            if sum(1 for pa in paths if pa.contains_point(mid)) % 2 != 1:
                continue
            is_v = vertical and abs(P[k, 1] - P[j, 1]) >= 0.7 * d[k]
            hit_pts = (tuple(np.round(P[j], 2)), tuple(np.round(P[k], 2)))
            if is_v:
                if d[k] < vert_[0]:
                    vert_ = (d[k], hit_pts, None)
            else:
                z = zone_of(part, to3d(axis, value, mid[0], mid[1]))
                if z:
                    if d[k] < zoned[0]:
                        zoned = (d[k], hit_pts, z)
                elif d[k] < free[0]:
                    free = (d[k], hit_pts, None)
            break
    return free, zoned, vert_


def main():
    bad = 0
    for v in ("L", "S"):
        fn = os.path.join(SECT, f"insert-{v}-printed_sections.json")
        if not os.path.exists(fn):
            print("missing", fn)
            continue
        data = json.load(open(fn, encoding="utf-8"))
        res = {}
        for key, sec in data.items():
            for part, loops in sec["bodies"].items():
                res[(key, part)] = min_wall(loops, part, sec["axis"], sec["value"])
        parts = sorted({p for (_, p) in res})
        print(f"\n=== Variant {v}: minimum wall per printed part (slice plane, points in plane coords)")
        for part in parts:
            # free (not in an intended zone) in-plane thin spots, confirmed on the twin plane
            best_free, thin = (9.9, None, None), []
            best_zone, best_vert = (9.9, None, None), (9.9, None, None)
            for (key, p), (fr, zo, ve) in res.items():
                if p != part or key.endswith("+"):
                    continue
                tw = res.get((key + "+", part))
                if fr[0] < WARN:
                    twin = tw[0] if tw else (9.9, None, None)
                    ok_twin = twin[0] < WARN and twin[1] and fr[1] and \
                        abs(twin[1][0][0] - fr[1][0][0]) + abs(twin[1][0][1] - fr[1][0][1]) < 1.5
                    if ok_twin:
                        thin.append((round(fr[0], 2), key, fr[1]))
                        if fr[0] < best_free[0]:
                            best_free = (fr[0], key, fr[1])
                if zo[0] < best_zone[0]:
                    best_zone = (zo[0], key, zo[1], zo[2])
                if ve[0] < best_vert[0]:
                    best_vert = (ve[0], key, ve[1])
            w = best_free[0]
            state = "OK" if w >= WARN else ("WARN" if w >= FAIL else "FAIL")
            if state == "FAIL":
                bad += 1
            if best_free[1]:
                print(f"  {state:5s} {part:13s} free walls min {w:.2f} mm at {best_free[1]} {best_free[2]}")
            else:
                print(f"  {state:5s} {part:13s} free walls: no spot below {WARN} mm (confirmed on the twin plane)")
            for t in sorted(set(thin))[:5]:
                print(f"         thin {t[0]:.2f} mm at {t[1]} {t[2]}")
            if best_zone[1]:
                zs = "OK" if best_zone[0] >= FAIL else "FAIL"
                if zs == "FAIL":
                    bad += 1
                print(f"         {zs} intended zone min {best_zone[0]:.2f} mm at {best_zone[1]} {best_zone[2]} — {best_zone[3]}")
            if best_vert[1]:
                vs = "OK" if best_vert[0] >= VFAIL else "FAIL"
                if vs == "FAIL":
                    bad += 1
                print(f"         {vs} vertical (layer stack) min {best_vert[0]:.2f} mm at {best_vert[1]} {best_vert[2]} "
                      f"(needs ≥ {VFAIL})")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
