"""Tolerance coupon v0 — find the fits for THIS printer and THESE parts before printing real parts.

Run headless (from the repo root):
    /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_coupon_v0.py', encoding='utf-8').read())"
Writes hardware/models/coupon-v0_print.stl and coupon-v0.step. Print flat, PLA, 0.2 mm layers,
no supports. About 10 minutes.

Engraved dots = variant (1 dot = left, 3 dots = right):
  row A  key-switch plate cut-outs 13.9 / 14.0 / 14.1 in a 1.5 mm plate
         → press a switch in: pick the one that clicks in firmly and does not wobble
  row B  INMP441 seats Ø13.25 / 13.35 / 13.45, 3.0 deep, on a Ø11 lip
         → the module should drop in and stay without force
  row C  keycap stem sockets, cross arms (length × width) 4.05×1.25 / 4.10×1.30 / 4.15×1.35
         → press onto a switch stem: snug, no cracking, no wobble
Report the three winners; they go into roomkey_params.py as [MEAS].
"""
import os
import sys

import FreeCAD as App  # noqa: F401  (FreeCAD runtime)
import Part
from FreeCAD import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import roomkey_params as P  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "models")
os.makedirs(OUT, exist_ok=True)

W, H = 66.0, 64.0
X = [13.0, 33.0, 53.0]                      # variant columns (left → right = 1 → 3 dots)
MX_VARIANTS = [P.MX_CUT - 0.1, P.MX_CUT, P.MX_CUT + 0.1]
MIC_VARIANTS = [P.MIC_D + 0.11, P.MIC_D + 0.21, P.MIC_D + 0.31]
STEM_VARIANTS = [(4.05, 1.25), (4.10, 1.30), (4.15, 1.35)]
MIC_LIP_D, MIC_SEAT_T, MIC_LIP_T = 11.0, 3.0, 0.8
STEM_CYL_D, STEM_CYL_H = 8.0, 6.0
DOT_D, DOT_DEPTH = 1.3, 0.5


def dots(n, x, y, top_z):
    """n engraved dots in a row, centred at (x, y) on the surface at top_z."""
    out = []
    for i in range(n):
        dx = (i - (n - 1) / 2) * 2.2
        out.append(Part.makeCylinder(DOT_D / 2, DOT_DEPTH + 0.01, V(x + dx, y, top_z - DOT_DEPTH)))
    return out


def build():
    plate = Part.makeBox(W, H, P.MX_PLATE_T)
    cuts = []
    # row A — switch cut-outs
    ya = 12.0
    for i, (x, c) in enumerate(zip(X, MX_VARIANTS)):
        cuts.append(Part.makeBox(c, c, P.MX_PLATE_T + 0.02, V(x - c / 2, ya - c / 2, -0.01)))
        cuts += dots(i + 1, x, ya + 9.2, P.MX_PLATE_T)
    # row B — INMP441 seats on a raised block (lip at the bed side, seat open to the top)
    yb, blk_h = 35.0, MIC_LIP_T + MIC_SEAT_T
    block = Part.makeBox(W - 4, 20.0, blk_h, V(2, yb - 10.0, 0))
    solid = plate.fuse(block)
    for i, (x, d) in enumerate(zip(X, MIC_VARIANTS)):
        cuts.append(Part.makeCylinder(MIC_LIP_D / 2, blk_h + 0.02, V(x, yb, -0.01)))
        cuts.append(Part.makeCylinder(d / 2, MIC_SEAT_T + 0.01, V(x, yb, MIC_LIP_T)))
        cuts += dots(i + 1, x, yb - 8.3, blk_h)
    # row C — stem sockets on small posts
    yc = 54.0
    for i, (x, (arm_l, arm_w)) in enumerate(zip(X, STEM_VARIANTS)):
        post = Part.makeCylinder(STEM_CYL_D / 2, STEM_CYL_H, V(x, yc, P.MX_PLATE_T))
        solid = solid.fuse(post)
        top = P.MX_PLATE_T + STEM_CYL_H
        cuts.append(Part.makeBox(arm_l, arm_w, P.MX_STEM_DEPTH + 0.01, V(x - arm_l / 2, yc - arm_w / 2, top - P.MX_STEM_DEPTH)))
        cuts.append(Part.makeBox(arm_w, arm_l, P.MX_STEM_DEPTH + 0.01, V(x - arm_w / 2, yc - arm_l / 2, top - P.MX_STEM_DEPTH)))
        cuts += dots(i + 1, x + 7.0, yc - 5.0, P.MX_PLATE_T)
    for c in cuts:
        solid = solid.cut(c)
    return solid.removeSplitter()


def check(shape):
    assert shape.isValid(), "invalid solid"
    bb = shape.BoundBox
    print(f"coupon {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} mm, volume {shape.Volume/1000:.2f} cm³, "
          f"≈ {shape.Volume/1000*1.24:.1f} g PLA")


def export(shape):
    stl = os.path.join(OUT, "coupon-v0_print.stl")
    step = os.path.join(OUT, "coupon-v0.step")
    shape.exportStl(stl)
    shape.exportStep(step)
    print("wrote", stl)
    print("wrote", step)


shape = build()
check(shape)
export(shape)
