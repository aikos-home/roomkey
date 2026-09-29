#!/usr/bin/env python3
"""Render an STL to a PNG (isometric, flat-shaded) — a quick look before printing.

    python3 tools/cad_preview.py hardware/models/coupon-v0_print.stl out.png [--elev 35 --azim -60]
Needs numpy + matplotlib.
"""
import argparse
import struct

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402


def load_stl(path):
    data = open(path, "rb").read()
    if data[:5] == b"solid" and b"facet" in data[:400]:
        tris, cur = [], []
        for line in data.decode("ascii", "ignore").splitlines():
            p = line.split()
            if p and p[0] == "vertex":
                cur.append([float(v) for v in p[1:4]])
                if len(cur) == 3:
                    tris.append(cur)
                    cur = []
        return np.array(tris)
    n = struct.unpack("<I", data[80:84])[0]
    rec = np.frombuffer(data[84:84 + 50 * n], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))
    return rec["v"].reshape(-1, 3, 3).astype(float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stl")
    ap.add_argument("png")
    ap.add_argument("--elev", type=float, default=38)
    ap.add_argument("--azim", type=float, default=-58)
    ap.add_argument("--color", default="#E8E4DC")
    a = ap.parse_args()
    t = load_stl(a.stl)
    nrm = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-12
    light = np.array([0.3, -0.5, 0.8]); light /= np.linalg.norm(light)
    shade = 0.35 + 0.65 * np.clip(nrm @ light, 0, 1)
    base = np.array(matplotlib.colors.to_rgb(a.color))
    fig = plt.figure(figsize=(7, 6), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(t, facecolors=np.clip(base * shade[:, None], 0, 1), edgecolor="none"))
    mn, mx = t.reshape(-1, 3).min(0), t.reshape(-1, 3).max(0)
    c, r = (mn + mx) / 2, (mx - mn).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(a.elev, a.azim); ax.axis("off")
    plt.savefig(a.png, bbox_inches="tight", facecolor="white")
    print(f"{len(t)} triangles → {a.png}")


if __name__ == "__main__":
    main()
