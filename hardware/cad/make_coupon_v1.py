"""Tolerance coupon v1 (insert v0.5): the fits of the wall-insert mechanics that no data sheet gives.

Run headless (from the repo root):
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_coupon_v1.py', encoding='utf-8').read())"
Writes hardware/models/coupon-v1_print.stl (all parts in print orientation, one plate) and coupon-v1.step.
Print in the material of the real parts — row D bases in the chassis' V-0 filament (its tongue strain, pull and bridge sag
are what row D measures), the rest in PETG/ASA, never PLA — 0.4 nozzle, at 0.10 mm layers — the layer height of the
real chassis and plate (the nub steps are 0.1 mm; 0.2 mm layers would merge them). No supports: if the slicer adds any,
put a support blocker over the carrier pockets (the seat is a 9 mm bridge, like on the chassis — that sag is in the chain).
Dots = variant (1 dot = smallest value). Print coupon v0 first and put its winners into roomkey_params.py.

  row D  floating-plate cell × 3: a base (a piece of the real chassis: deck, rigid top edge, one bottom snap tongue with
         the real length/width/depth/slot/lead-in, the REAL switch seat — carrier pocket 9.2 × 6.8 with the carrier
         resting on the flat flange face, a 1.6 × 2.6 wire slot 2.0 off-centre — and one preload-pad pocket 5 × 3 × 0.5)
         and a mini plate (skin 2.0, top drawer lip, bottom snap lip, locating skirts, nub). The three plates have nubs
         1.7 / 1.6 / 1.5 tall = nub gap 0.2 / 0.3 / 0.4.
         Solder an Omron B3FS-1002P (SMD) on a real FR4 carrier (8.8 × 6.4 × 0.8, flat back, 2 plated wire holes 2.0
         off-centre, front side tented), solder 2 wires from the back, drop it into the seat (glue dot). Check the
         B3FS toe fillets (the pads end at ±4.4, 0.4 short of Omron's land pattern). Stick a 5 × 3
         foam pad (PAD_H 2.5, the candidate foam) into the pad pocket.
         Mount the plate like the real one: tilt it, hook the top lip behind the top edge (shift it up ~0.7), press the
         bottom edge on until the snap lip clicks over the tongue. The switch must NOT click by itself (plate up or
         down); press the centre: one clean click; press the top edge: it must still click; with and without the pad. Pick the SMALLEST gap that
         never pre-clicks → NUB_GAP [MEAS]; if one switch is off, shim its carrier with 0.05 mm polyimide tape.
         Calipers: plunger free height and pressed-to-stop height → SW_TRAVEL_TOTAL [MEAS]; press ONE cell with 30 N
         (3 kg, ABUSE_FORCE) for 1 min: nothing may crack, the switch must still click at the same force → SW_MAX_FORCE. Snap: must go on without whitening the
         tongue; hang 0.5 kg on the bottom edge (≈ 5 N, one tongue): must hold → tongue [MEAS]; release: slide a 0.5 mm
         feeler gauge in sideways under the skirt and push the tongue inward.
  row E  key stem posts Ø 5.3 / 5.5 / 5.7 with the key socket (KEY_SOCKET_DEPTH, cross from coupon v0 row C).
         Press each onto an MX switch and push to the bottom: the post must enter the housing window without rubbing
         → MX_POST_D / MX_WINDOW; pull it off with a spring scale: ≥ 10 N (KEY_PULL_MIN) with the chosen cross.
  row F  plate skin 2.0 with 4 × 6 holes Ø 0.9 / 1.0 / 1.1, pitch 1.6, printed face down like the plate.
         Hold against light: every hole open and round. Pick the smallest that is reliably open → PERF_D.
  row H  colour patches 20 × 20 × 2.0, face down: in the slicer give each patch a height-range modifier ivory 0 →
         0.6 / 0.9 / 1.2 mm, black above. Hold them against the real frame in daylight → PLATE_FACE_T.
  Glow/light test (desk rig): print the REAL collar (collar_print.stl, back down, natural PETG) and one real plate
  (plate_L_body + plate_L_glowrim as one multi-material object) and light the collar with 4 SK6812 MINI.
"""
import os
import sys

import FreeCAD as App  # noqa: F401  (FreeCAD runtime)
import Part
from FreeCAD import Vector as V

try:                      # FreeCADCmd's stdout is ASCII even with PYTHONIOENCODING set
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:         # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_params as P  # noqa: E402

R = P.R
OUT = os.path.join(os.path.dirname(HERE), "models")
os.makedirs(OUT, exist_ok=True)
EPS = 0.01
DOT_D, DOT_DEPTH = 1.3, 0.4

NUB_GAPS = (0.2, 0.3, 0.4)
POST_DS = (5.3, 5.5, 5.7)
PERF_DS = (0.9, 1.0, 1.1)
X = (14.0, 40.0, 66.0)                    # variant columns (1 → 3 dots)


def box(x0, x1, y0, y1, z0, z1):
    return Part.makeBox(x1 - x0, y1 - y0, z1 - z0, V(x0, y0, z0))


def cyl(x, y, r, z0, z1):
    return Part.makeCylinder(r, z1 - z0, V(x, y, z0))


def rrect(cx, cy, hx, hy, r, z0, z1):
    """Rounded rectangle prism centred at (cx, cy), half sizes hx, hy, corner radius r."""
    core = [box(cx - hx + r, cx + hx - r, cy - hy, cy + hy, z0, z1), box(cx - hx, cx + hx, cy - hy + r, cy + hy - r, z0, z1)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            core.append(cyl(cx + sx * (hx - r), cy + sy * (hy - r), r, z0, z1))
    s = core[0]
    for c in core[1:]:
        s = s.fuse(c)
    return s.removeSplitter()


def dots(n, x, y, z_top, into=True):
    """n engraved dots at (x, y) on a face at z_top (into = engrave downward, else upward from a bed face)."""
    out = []
    for i in range(n):
        dx = (i - (n - 1) / 2) * 2.2
        z0 = z_top - DOT_DEPTH if into else z_top - EPS
        out.append(cyl(x + dx, y, DOT_D / 2, z0, z0 + DOT_DEPTH + EPS))
    return out


def cut_all(s, tools):
    for t in tools:
        s = s.cut(t)
    return s.removeSplitter()


# ------------------------------------------------------------------ row D: floating-plate cells
# A cell = a piece of the real chassis edge: rigid TOP edge (drawer lip) + one BOTTOM snap tongue exactly as on the
# chassis (length, width, depth, slot, lead-in), a real switch seat (carrier on the flange face) in the middle, and a
# mini plate (skin, nub, top lip, snap lip, locating skirts). Depths d as in insert_params (d = 0 at the plate front).
# The base prints DECK FRONT DOWN like the chassis (z = d − DECK_D0); the mini plate prints FACE DOWN (z = d).
CELL_HX, CELL_HY = 10.0, 9.0              # base deck half sizes (deck edges at y = ±9 play the role of ±26.2)
CLR = P.HALF - P.PLATE_SKIRT_T - P.DECK_HALF_Y                         # 0.1 skirt ↔ deck edge
T_ROOT = CELL_HX - (P.TONGUE_X[1] - P.TONGUE_X[0])                     # tongue root x (tip at the cell's right edge)
SNAP0, SNAP1 = T_ROOT + (P.SNAP_X[0] - P.TONGUE_X[0]), T_ROOT + (P.SNAP_X[1] - P.TONGUE_X[0])
FL0 = P.WALL_D - P.FLANGE_T                                            # flange front = the carrier seat (datum)


def d_base(cx, cy, n):
    z = lambda d: d - P.DECK_D0          # noqa: E731
    hx, hy = P.CARRIER[0] / 2 + 0.2, P.CARRIER[1] / 2 + 0.2
    parts = [box(cx - CELL_HX, cx + CELL_HX, cy - CELL_HY, cy + CELL_HY, z(P.DECK_D0), z(P.DECK_D1))]           # deck
    parts.append(box(cx - hx - 0.8, cx + hx + 0.8, cy - hy - 0.8, cy + hy + 0.8, z(P.DECK_D1) - EPS, z(FL0)))     # pocket walls
    parts.append(box(cx - CELL_HX, cx + CELL_HX, cy - 6.4, cy + 6.4, z(FL0) - EPS, z(P.WALL_D)))                 # flange slab
    for sx in (-1, 1):
        x0, x1 = sorted((cx + sx * (CELL_HX - 1.0), cx + sx * CELL_HX))
        parts.append(box(x0, x1, cy - 6.4, cy + 6.4, z(P.DECK_D1) - EPS, z(FL0)))
    parts.append(box(cx + T_ROOT - 1.0, cx + CELL_HX - P.DECK_R, cy - CELL_HY, cy - CELL_HY + P.TONGUE_W,
                     z(P.DECK_D1) - EPS, z(P.TONGUE_D1)))                                                        # tongue rib
    s = parts[0]
    for p_ in parts[1:]:
        s = s.fuse(p_)
    rs = P.TONGUE_SLOT / 2
    ty = cy - CELL_HY + P.TONGUE_W
    tools = [box(cx + T_ROOT + rs, cx + CELL_HX + 1, ty, ty + P.TONGUE_SLOT, z(P.DECK_D0) - 1, z(P.TONGUE_D1) + EPS),
             cyl(cx + T_ROOT + rs, ty + rs, rs, z(P.DECK_D0) - 1, z(P.TONGUE_D1) + EPS)]                         # tongue slot
    c = P.TONGUE_CHAMFER
    tri = Part.makePolygon([V(0, cy - CELL_HY + c, -EPS), V(0, cy - CELL_HY - EPS, -EPS), V(0, cy - CELL_HY - EPS, c),
                            V(0, cy - CELL_HY + c, -EPS)])
    pr = Part.Face(tri).extrude(V(CELL_HX + 1 - T_ROOT, 0, 0))
    pr.translate(V(cx + T_ROOT, 0, 0))
    tools.append(pr)                                                                                             # lead-in
    tools.append(box(cx - hx, cx + hx, cy - hy, cy + hy, z(P.DECK_D0) - 1, z(FL0)))                             # carrier pocket
    ws, wo = P.CARRIER_WIRE_SLOT, P.CARRIER_WIRE_OFF
    tools.append(box(cx - wo - ws[0] / 2, cx - wo + ws[0] / 2, cy - wo - ws[1] / 2, cy - wo + ws[1] / 2,
                     z(FL0) - EPS, z(P.WALL_D) + 1))                                                            # wire slot
    px, py = cx - 7.2, cy + 5.5
    tools.append(box(px - P.PAD_SIZE[0] / 2, px + P.PAD_SIZE[0] / 2, py - P.PAD_SIZE[1] / 2, py + P.PAD_SIZE[1] / 2,
                     z(P.DECK_D0) - 1, z(P.DECK_D0) + P.PAD_POCKET))                                            # pad pocket
    tools += dots(n, cx - 5.5, cy + 3.5, z(P.WALL_D))
    return cut_all(s, tools)


def d_plate(cx, cy, n, nub_h):
    sk_in = CELL_HY + CLR                       # skirt inner face (y), like 26.3
    sk_out = sk_in + 0.8
    sx_in = CELL_HX + CLR                       # side skirts hug the base's side edges
    parts = [box(cx - sx_in - 0.8, cx + sx_in + 0.8, cy - sk_out, cy + sk_out, 0.0, P.PLATE_T)]
    for sx in (-1, 1):
        x0, x1 = sorted((cx + sx * sx_in, cx + sx * (sx_in + 0.8)))
        parts.append(box(x0, x1, cy - sk_out, cy + sk_out, P.PLATE_T - EPS, P.SKIRT_D))                       # side skirts
    parts.append(box(cx - sx_in, cx + sx_in, cy + sk_in, cy + sk_out, P.PLATE_T - EPS, P.LIP_D1))               # top skirt
    parts.append(box(cx - sx_in, cx + sx_in, cy + sk_in - P.LIP_IN, cy + sk_in + EPS, P.LIP_D0, P.LIP_D1))      # top lip
    parts.append(box(cx - sx_in, cx + sx_in, cy - sk_out, cy - sk_in, P.PLATE_T - EPS, P.SKIRT_D))              # bottom skirt
    parts.append(box(cx + SNAP0 - 0.5, cx + sx_in, cy - sk_out, cy - sk_in, P.PLATE_T - EPS, P.SNAP_D1))        # deep segment
    ch = P.SNAP_CHAMFER
    yi = sk_in - P.LIP_IN
    pts = [(sk_in + EPS, P.SNAP_D0), (yi, P.SNAP_D0), (yi, P.SNAP_D1 - ch), (yi + ch, P.SNAP_D1), (sk_in + EPS, P.SNAP_D1),
           (sk_in + EPS, P.SNAP_D0)]
    lip = Part.Face(Part.makePolygon([V(cx + SNAP0, cy - yy, dd) for (yy, dd) in pts])).extrude(V(SNAP1 - SNAP0, 0, 0))
    parts.append(lip)                                                                                           # snap lip
    parts.append(cyl(cx, cy, 1.25, P.PLATE_T - EPS, P.PLATE_T + nub_h))                                          # nub
    s = parts[0]
    for p_ in parts[1:]:
        s = s.fuse(p_)
    tools = dots(n, cx - 5.5, cy + 5.0, P.PLATE_T)
    return cut_all(s, tools)


# ------------------------------------------------------------------ row E: stem posts
def e_row(y):
    base = box(X[0] - 10, X[-1] + 10, y - 5, y + 5, 0.0, 1.5)
    tools = []
    post_len = P.KS["post_end"] - P.KS["key_back"]
    for i, (x, dpost) in enumerate(zip(X, POST_DS)):
        base = base.fuse(cyl(x, y, dpost / 2, 1.5 - EPS, 1.5 + post_len + 3.0))
        top = 1.5 + post_len + 3.0
        tools.append(box(x - R.MX_STEM_ARM_L / 2, x + R.MX_STEM_ARM_L / 2, y - R.MX_STEM_ARM_W / 2, y + R.MX_STEM_ARM_W / 2,
                         top - R.KEY_SOCKET_DEPTH, top + EPS))
        tools.append(box(x - R.MX_STEM_ARM_W / 2, x + R.MX_STEM_ARM_W / 2, y - R.MX_STEM_ARM_L / 2, y + R.MX_STEM_ARM_L / 2,
                         top - R.KEY_SOCKET_DEPTH, top + EPS))
        tools += dots(i + 1, x + 7.0, y, 1.5)
    return cut_all(base, tools)


# ------------------------------------------------------------------ row F: perforation patches (face down)
def f_row(y):
    cols, rows = 4, 6
    s = box(X[0] - 11, X[-1] + 11, y - 7, y + 7, 0.0, P.PLATE_T)
    tools = []
    for i, (x, dh) in enumerate(zip(X, PERF_DS)):
        for c in range(cols):
            for r in range(rows):
                px = x - 4 + (c - (cols - 1) / 2) * P.PERF_PITCH
                py = y + (r - (rows - 1) / 2) * P.PERF_PITCH
                tools.append(cyl(px, py, dh / 2, -EPS, P.PLATE_T + EPS))
        tools += dots(i + 1, x + 5.5, y, P.PLATE_T)
    return cut_all(s, tools)


# ------------------------------------------------------------------ row H: colour patches (face down)
def h_patch(cx, cy, n):
    s = box(cx - 10, cx + 10, cy - 10, cy + 10, 0.0, P.PLATE_T)
    return cut_all(s, dots(n, cx, cy + 6.0, P.PLATE_T))


def build():
    solids, info = [], []
    tip = P.sw_depths()[0]
    for i, (x, g) in enumerate(zip(X, NUB_GAPS)):
        nub_h = tip - P.PLATE_T - g
        solids += [d_base(x, 12.0, i + 1), d_plate(x, 36.0, i + 1, nub_h)]
        info.append(f"row D{i+1}: nub {nub_h:.2f} tall → gap {g:.2f} to the plunger (tip d {tip:.2f} with the carrier on the flange "
                    f"face), click after {g + P.SW_PT:.2f}, stop after {g + P.SW_TRAVEL_TOTAL:.2f} [TBD]")
    solids.append(e_row(56.0))
    solids.append(f_row(71.0))
    for i, x in enumerate((100.0, 124.0, 100.0)):
        solids.append(h_patch(x if i < 2 else 124.0, 22.0 if i < 2 else 46.0, i + 1))
    info.append("row H: colour patches — set the ivory height per patch in the slicer (0.6 / 0.9 / 1.2)")
    return solids, info


def check(solids, info):
    for s in solids:
        assert s.isValid(), "invalid solid"
    comp = Part.makeCompound(solids)
    bb = comp.BoundBox
    vol = sum(s.Volume for s in solids)
    print(f"coupon v1: {len(solids)} parts on {bb.XLength:.0f} × {bb.YLength:.0f} mm, height {bb.ZLength:.1f} mm, "
          f"{vol/1000:.1f} cm³ ≈ {vol/1000*1.27:.0f} g PETG")
    for s in info:
        print("  ", s)
    return comp


def export(comp):
    import MeshPart
    stl = os.path.join(OUT, "coupon-v1_print.stl")
    step = os.path.join(OUT, "coupon-v1.step")
    mesh = MeshPart.meshFromShape(Shape=comp, LinearDeflection=0.02, AngularDeflection=0.2)
    mesh.write(stl)
    comp.exportStep(step)
    print("wrote", os.path.relpath(stl, os.path.dirname(os.path.dirname(HERE))))
    print("wrote", os.path.relpath(step, os.path.dirname(os.path.dirname(HERE))))


solids, info = build()
export(check(solids, info))
