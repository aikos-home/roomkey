"""RoomKey PRACTICE BOX (prototype only: never in a wall, never on 230 V; bench power) — builders, checks, export.

One flush-box replica on a "wall" plate + a 1-gang frame in the Jung AS 500 size (with the SHT31-D in its bottom border).
The kit (kit_lib) goes into it. Geometry: insert_params.py section 6. The earlier 2-box desk replica with a sensor cover
in the second box was retired (owner, 2026-10-03: "everything in ONE box") and removed on 2026-10-06; wall_block() and
frame_2x() still take several box centres.
Coordinates as in insert_lib: (x, y, d), d = depth behind the plate front.
"""
import json
import os
import sys

import Part

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_lib as L  # noqa: E402

P, R, V, EPS = L.P, L.R, L.V, L.EPS
box, cyl, rrect, fuse, cut = L.box, L.cyl, L.rrect, L.fuse, L.cut
PITCH = P.DESK_PITCH
CENTRES = ((0.0, 0.0), (0.0, -PITCH))
D_BACK = P.WALL_D + P.DESK_DEPTH


# ============================================================================ wall block (two boxes + "wall" plate)
def wall_block(centres=CENTRES):
    """the "wall": a plate at the wall plane with the box openings, open-backed cups (Ø DESK_CUP_IN), two screw domes per
    box at (±30, 0) and (2 boxes) a wire channel between them. Printed face down, no supports."""
    w0 = P.WALL_D
    W, H, T, Rc = P.DESK_PLATE
    n = len(centres)
    H = H - (2 - n) * PITCH
    yc = -(n - 1) * PITCH / 2
    r_in, r_out = P.DESK_CUP_IN / 2, P.DESK_CUP_IN / 2 + P.DESK_CUP_WALL
    parts = [rrect(W / 2, H / 2, Rc, w0, w0 + T, cy=yc)]
    for (cx, cy) in centres:
        parts.append(cyl(cx, cy, r_out, w0, D_BACK).cut(cyl(cx, cy, r_in, w0 - 1, D_BACK + 1)))
    x0, x1, ld0, ld1 = P.DESK_LINK
    wl = P.DESK_CUP_WALL
    if n == 2:
        parts.append(box(x0 - wl, x1 + wl, -PITCH + r_in - 2.0, -r_in + 2.0, ld0 - wl, ld1 + wl))  # channel shell
    body = fuse(parts)
    tools = [cyl(cx, cy, r_in, w0 - 1, D_BACK + 1) for (cx, cy) in centres]                        # openings + cups
    if n == 2:
        tools.append(box(x0, x1, -PITCH + 2.0, -2.0, ld0, ld1))                                  # channel bore
    body = cut(body, tools)
    domes = []
    for (cx, cy) in centres:
        for sx in (-1, 1):
            domes.append(box(cx + sx * P.BOX_DOME_R_IN, cx + sx * P.DESK_DOME_R_OUT, cy - P.BOX_DOME_W / 2,
                             cy + P.BOX_DOME_W / 2, w0 + 1.0, D_BACK))
    body = fuse([body] + domes + (dome_ledges(-PITCH) if n == 2 else []))
    pd, pl = P.DESK_SCREW_PILOT
    holes = [cyl(cx + sx * P.BOX_SCREW_PITCH / 2, cy, pd / 2, w0 - 1, w0 + pl) for (cx, cy) in centres for sx in (-1, 1)]
    holes += [cyl(fx, fy, P.DESK_FRAME_POST[2] / 2, w0 - 1, w0 + T + 1) for (fx, fy) in frame_screws(centres)]
    return cut(body, holes)


# ============================================================================ 2-gang frame
def frame_screws(centres):
    """4 × M3 from behind into the frame's corner posts, outside the 71 × 71 flanges."""
    cx, cy = P.DESK_FRAME_SCREWS[1]
    top, bot = centres[0][1], centres[-1][1]
    return ((-cx, top + cy), (cx, top + cy), (-cx, bot - cy), (cx, bot - cy))


def _rr_wire(hx, hy, r, d, cy=0.0):
    """closed rounded-rectangle wire in the plane at depth d."""
    import math
    z = -d
    x0, x1, y0, y1 = -hx, hx, cy - hy, cy + hy
    k = math.sqrt(0.5)
    e = [Part.LineSegment(V(x0 + r, y0, z), V(x1 - r, y0, z)).toShape(),
         Part.Arc(V(x1 - r, y0, z), V(x1 - r + r * k, y0 + r - r * k, z), V(x1, y0 + r, z)).toShape(),
         Part.LineSegment(V(x1, y0 + r, z), V(x1, y1 - r, z)).toShape(),
         Part.Arc(V(x1, y1 - r, z), V(x1 - r + r * k, y1 - r + r * k, z), V(x1 - r, y1, z)).toShape(),
         Part.LineSegment(V(x1 - r, y1, z), V(x0 + r, y1, z)).toShape(),
         Part.Arc(V(x0 + r, y1, z), V(x0 + r - r * k, y1 - r + r * k, z), V(x0, y1 - r, z)).toShape(),
         Part.LineSegment(V(x0, y1 - r, z), V(x0, y0 + r, z)).toShape(),
         Part.Arc(V(x0, y0 + r, z), V(x0 + r - r * k, y0 + r - r * k, z), V(x0 + r, y0, z)).toShape()]
    return Part.Wire(e)


def frame_rh_geometry():
    """SHT31-D under the bottom border of a 1-gang frame, lying FLAT (parallel to the wall), chip side forward. Along the
    slope it does not fit (the tilted board's thickness takes the room). The tunnel wall is thinned to 0.7 and the skirt
    to 0.6 over the board's length. Its own top edge (holes, chip) points +x, its left edge to the rim side."""
    cx, tw_left, sk, _ = P.FRAME_RH
    y_rim = P.FRAME_OPEN / 2 + 0.7 + 0.2                 # board's inner edge: thinned tunnel wall + clearance
    l, w = R.RH_W, R.RH_H
    d_front = 5.3                                       # [FREE] board front d (chip 1.1 tall → 0.8 air below the face)
    chip = (cx + l / 2 - R.RH_CHIP_C[1], -(y_rim + R.RH_CHIP_C[0]))
    return dict(cx=cx, y0=-(y_rim + w), y1=-y_rim, l=l, w=w, d_front=d_front, sk=sk, chip=chip)


def frame_rh_tools_and_parts():
    """tunnel wall thinned, skirt thinned, 3 × 3 Ø1.0 vents over the chip, 3 air inlets in the bottom skirt (all centred
    on x = 0 with the chip)."""
    g = frame_rh_geometry()
    x0, x1 = g["cx"] - g["l"] / 2 - 0.3, g["cx"] + g["l"] / 2 + 0.3
    fo, yo = P.FRAME_OPEN / 2, P.FRAME_OUT / 2
    tools = [box(x0, x1, -(fo + P.DESK_FRAME_T[1]) - 0.01, -(fo + 0.7), 3.2, P.FRAME_TUNNEL_D + 0.1),   # tunnel wall → 0.7
             box(x0, x1, -(yo - g["sk"]), -(yo - P.DESK_FRAME_T[2]) + 0.01, 3.2, P.WALL_D + 0.1)]      # skirt → 0.6
    ccx, ccy = g["chip"]
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            tools.append(cyl(ccx + 1.6 * i, ccy + 1.6 * j, 0.5, -3.0, g["d_front"] - 0.2))
    for k in (-1, 0, 1):                                # inlets centred under the chip = on the frame's centre line
        tools.append(box(ccx + 4.0 * k - 0.6, ccx + 4.0 * k + 0.6, -yo - 1, -(yo - 3), 5.1, 6.1))
    return tools


def rh_ref():
    """the SHT31-D board + chip in place (flat, chip side forward)."""
    g = frame_rh_geometry()
    df = g["d_front"]
    board = box(g["cx"] - g["l"] / 2, g["cx"] + g["l"] / 2, g["y0"], g["y1"], df, df + R.RH_PCB_T)
    ccx, ccy = g["chip"]
    return board.fuse(box(ccx - 1.25, ccx + 1.25, ccy - 1.25, ccy + 1.25, df - 1.1, df + 0.01))


def rh_pins():
    """VIN, GND, SCL, SDA at the board's −x end (its bottom edge), on its back."""
    g = frame_rh_geometry()
    yc = (g["y0"] + g["y1"]) / 2
    return {nm: (g["cx"] - g["l"] / 2 + 1.6, yc + (1.5 - k) * 2.54, g["d_front"] + R.RH_PCB_T + 0.3)
            for k, nm in enumerate(R.RH_PINS)}


def frame_2x(centres=CENTRES, with_rh=False):
    """frame replica (1- or 2-gang), Jung AS 500 style: the face slopes from a flat rim round the openings (highest, 10 mm
    above the wall) down to the outer edge; 2 mm face shell, an outer skirt to the wall, a tunnel wall round each opening
    down to FRAME_TUNNEL_D (the insert's locating rims sit in it), 4 corner posts for M3 screws from behind."""
    ft, tw, sk = P.DESK_FRAME_T
    h_in, h_out, rim = P.DESK_FRAME_PROFILE
    n = len(centres)
    yc = -(n - 1) * PITCH / 2
    ow, oh, rr = P.FRAME_OUT / 2, (P.FRAME_OUT + (n - 1) * PITCH) / 2, P.DESK_FRAME_R
    fo = P.FRAME_OPEN / 2
    d_out, d_in = P.WALL_D - h_out, P.WALL_D - h_in
    iw, ih = fo + rim, fo + rim + (n - 1) * PITCH / 2
    top = Part.makeLoft([_rr_wire(ow, oh, rr, d_out, yc), _rr_wire(iw, ih, 1.0 + rim, d_in, yc)], True)
    full = fuse([top, rrect(ow, oh, rr, d_out - EPS, P.WALL_D, cy=yc)])
    hollow = full.copy()
    hollow.translate(V(0, 0, -ft))                                   # the same surface 2 mm deeper …
    hollow = hollow.common(rrect(ow - sk, oh - sk, rr - sk, d_in - 1, P.WALL_D + 1, cy=yc))   # … inside the skirt
    parts = [full.cut(hollow)]
    for (cx, cy) in centres:
        parts.append(rrect(fo + tw, fo + tw, 1.0 + tw, d_in, P.FRAME_TUNNEL_D, cx, cy))
    pdia, pil, _ = P.DESK_FRAME_POST
    parts += [cyl(fx, fy, pdia / 2, d_out - 0.5, P.WALL_D) for (fx, fy) in frame_screws(centres)]   # inside the face shell
    body = fuse(parts).common(rrect(ow, oh, rr, d_in - 1, P.WALL_D, cy=yc))
    tools = [rrect(fo, fo, 1.0, d_in - 1.0, P.WALL_D + 1, cx, cy) for (cx, cy) in centres]
    tools += [cyl(fx, fy, pil / 2, P.WALL_D - 6.0, P.WALL_D + 1) for (fx, fy) in frame_screws(centres)]
    if with_rh:
        tools += frame_rh_tools_and_parts()
    return cut(body, tools)


# ============================================================================ bottom position: sensor cover
def build_practice():
    """owner 2026-10-03: ONE practice box (replica, open back) + 1-gang frame; the RoomKey kit slides in. Bench power from
    a lab supply. Checked against the insert (Variant S) at rest and with the plate pressed."""
    print(f"\n==================== RoomKey PRACTICE BOX (prototype, lab supply, never in a wall) — insert v{P.VERSION} ====")
    one = ((0.0, 0.0),)
    wb, fr = wall_block(one), frame_2x(one, with_rh=True)
    pbody, prim = L.plate_parts("S")
    bodies = {"practice box": wb, "frame 1-gang": fr, "key shell": L.key_shell(), "switch plate": L.switch_plate(),
              "collar": L.collar(), "plate": fuse([pbody, prim])}
    bodies["chassis"], _ = L.chassis("S")
    refs = L.ref_bodies("S")
    for k in ("touch board", "MX switch 1", "MX switch 2", "speaker 2030", "LED 1", "LED 2", "LED 3", "LED 4", "box screw L",
              "box screw R", "load plate L", "load plate R", "cable loop"):
        bodies[k] = refs[k]
    for nm in ("practice box", "frame 1-gang"):
        bb = bodies[nm].BoundBox
        print(f"  {nm:15s} valid {bodies[nm].isValid()} | {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} | "
              f"{bodies[nm].Volume/1000:.1f} cm³ ≈ {bodies[nm].Volume/1000*1.27:.0f} g PETG")
    ex = {frozenset(("box screw L", "practice box")), frozenset(("box screw R", "practice box")),
          frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate"))}
    col = L.check_state(bodies, "practice box, rest", ex)
    gaps = {f"{a} ↔ {b}": round(L.min_gap(bodies[a], bodies[b]), 3) for (a, b) in
            (("chassis", "practice box"), ("chassis", "frame 1-gang"), ("plate", "frame 1-gang"), ("frame 1-gang", "practice box"))}
    for case in ("left wing", "top band", "bottom band"):
        gaps[f"plate pressed ({case}) ↔ frame 1-gang"] = round(L.min_gap(L.plate_pressed(bodies["plate"], case), fr), 3)
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    for k, v in gaps.items():
        print(f"    gap {k:50s} {v}")
    L.export(wb, "practice_box", "front_down")
    L.export(fr, "practice_frame_1x", "front_down")
    with open(os.path.join(L.OUT, "practice-box_check.json"), "w", encoding="utf-8") as f:
        json.dump({"collisions": col, "gaps": gaps}, f, indent=1, ensure_ascii=False)
