"""RoomKey DESK REPLICA (prototype only: never in a wall, never on 230 V, powered by USB 5 V) — builders, checks, export.

Two coupled flush-box replicas + a 2-gang frame. Top position = the RoomKey wall insert (insert_lib, unchanged), bottom
position = a sensor cover carrying the owner's breakout boards (LD2410C radar, VEML7700, SHT31-D, INMP441) with the
MAX98357A on a tray behind them. Geometry: insert_params.py section 6 + roomkey_params.py (owner-measured breakouts).
Coordinates as in insert_lib: (x, y, d), d = depth behind the plate front; top box centre (0, 0), bottom box (0, −PITCH).
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
    """tunnel wall thinned, skirt thinned, 3 × 3 Ø1.0 vents over the chip, 3 air inlets in the bottom skirt."""
    g = frame_rh_geometry()
    x0, x1 = g["cx"] - g["l"] / 2 - 0.3, g["cx"] + g["l"] / 2 + 0.3
    fo, yo = P.FRAME_OPEN / 2, P.FRAME_OUT / 2
    tools = [box(x0, x1, -(fo + P.DESK_FRAME_T[1]) - 0.01, -(fo + 0.7), 3.2, P.FRAME_TUNNEL_D + 0.1),   # tunnel wall → 0.7
             box(x0, x1, -(yo - g["sk"]), -(yo - P.DESK_FRAME_T[2]) + 0.01, 3.2, P.WALL_D + 0.1)]      # skirt → 0.6
    ccx, ccy = g["chip"]
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            tools.append(cyl(ccx + 1.6 * i, ccy + 1.6 * j, 0.5, -3.0, g["d_front"] - 0.2))
    for k in (-1, 0, 1):
        tools.append(box(g["cx"] + 4.0 * k - 0.6, g["cx"] + 4.0 * k + 0.6, -yo - 1, -(yo - 3), 5.1, 6.1))
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
def _board(c, w, h):
    return c[0] - w / 2, c[0] + w / 2, c[1] - h / 2, c[1] + h / 2


def _cradle(x0, x1, y0, y1, d_face, standoff, pcb_t, leg=3.0, wall=1.0, clr=0.2, pad=1.6):
    """4 corner L-brackets (board edge + clr) from the face back to 0.6 behind the board, and 4 corner pads that hold the
    board `standoff` off the face (boards are pressed in and fixed with a dab of hot glue)."""
    d_b = d_face + standoff
    d1 = d_b + pcb_t + 0.6
    out = []
    X0, X1, Y0, Y1 = x0 - clr, x1 + clr, y0 - clr, y1 + clr
    for (cx, sx) in ((X0, -1), (X1, 1)):
        for (cy, sy) in ((Y0, -1), (Y1, 1)):
            out.append(box(cx, cx + sx * wall, cy - sy * leg, cy + sy * wall, d_face - EPS, d1))   # leg along y
            out.append(box(cx - sx * leg, cx + sx * wall, cy, cy + sy * wall, d_face - EPS, d1))   # leg along x
            px = x0 if sx < 0 else x1 - pad
            py = y0 if sy < 0 else y1 - pad
            out.append(box(px, px + pad, py, py + pad, d_face - EPS, d_b))                         # pad
    return out


def sensor_layout():
    """board outlines (front view: x right, y up, chip/port side facing the room) and their window positions."""
    lay = {}
    rx = _board(P.SENS_RADAR_POS, R.RADAR_H, R.RADAR_W)          # long side along x
    lay["radar"] = dict(box=rx, pcb=R.RADAR_T, standoff=P.SENS_STANDOFF["radar"], back=R.RADAR_T_PINS - R.RADAR_T)
    ax = _board(P.SENS_ALS_POS, R.ALS_W, R.ALS_H)
    lay["als"] = dict(box=ax, pcb=R.ALS_PCB_T, standoff=P.SENS_STANDOFF["als"],
                      chip=(ax[0] + R.ALS_CHIP_C[0], ax[3] - R.ALS_CHIP_C[1]))
    hx = _board(P.SENS_RH_POS, R.RH_H, R.RH_W)                   # 10.5 wide (x) × 13.34 tall (y)
    lay["rh"] = dict(box=hx, pcb=R.RH_PCB_T, standoff=P.SENS_STANDOFF["rh"],
                     chip=(hx[0] + R.RH_CHIP_C[0], hx[3] - R.RH_CHIP_C[1]))
    mx, my = P.SENS_MIC_POS
    lay["mic"] = dict(c=(mx, my), d=R.MIC_D, pcb=1.0, standoff=P.SENS_STANDOFF["mic"], port=(mx, my + 0.8))
    return lay


def sensor_face():
    """55 × 55 cover (like the plate) with the windows; cradles on its back; a spigot ring into the carrier collar."""
    t = P.SENS_FACE_T
    h = P.HALF
    sp_d, sp_c = P.SENS_SPIGOT
    so = h - P.SENS_COLLAR_T - sp_c                     # spigot outer half size
    lay = sensor_layout()
    parts = [rrect(h, h, P.PLATE_CORNER_R, 0.0, t),
             rrect(so, so, 1.0, t - EPS, t + sp_d).cut(rrect(so - 1.2, so - 1.2, 0.5, t - 1, t + sp_d + 1))]
    # heat wall between the radar (warm, top) and the RH / light / mic boards below
    parts.append(box(-(so - 0.6), so - 0.6, 1.0, 2.2, t - EPS, t + 6.0))
    for k in ("radar", "als", "rh"):
        x0, x1, y0, y1 = lay[k]["box"]
        parts += _cradle(x0, x1, y0, y1, t, lay[k]["standoff"], lay[k]["pcb"])
    m = lay["mic"]
    mx, my = m["c"]
    ring_in = m["d"] / 2 + 0.2
    parts.append(cyl(mx, my, ring_in + 1.0, t - EPS, t + m["standoff"] + m["pcb"] + 0.6).cut(
        cyl(mx, my, ring_in, t - 1, t + 9)))
    px, py = m["port"]
    parts.append(cyl(px, py, 2.0, t - EPS, t + m["standoff"]).cut(cyl(px, py, 0.8, t - 1, t + 9)))   # port seal ring
    for sy in (-1, 1):                                                                           # 2 rest pads
        parts.append(cyl(mx, my + sy * 5.5, 0.8, t - EPS, t + m["standoff"]))
    body = fuse(parts)
    x0, x1, y0, y1 = lay["radar"]["box"]
    tools = [box(x0 + 2.0, x1 - 2.0, y0 + 2.0, y1 - 2.0, 1.2, t + EPS)]   # radar window: 1.2 skin, corners stay full (pads)
    cx, cy = lay["als"]["chip"]
    tools.append(cyl(cx, cy, 1.25, -1.0, t + 0.5))                                               # light hole Ø2.5
    cx, cy = lay["rh"]["chip"]
    for i in (-1, 0, 1):                                                                         # vent grid 3 × 3 Ø1.0
        for j in (-1, 0, 1):
            tools.append(cyl(cx + 1.6 * i, cy + 1.6 * j, 0.5, -1.0, t + 0.5))
    tools.append(cyl(px, py, 0.5, -1.0, t + 0.5))                                                # mic port Ø1.0
    return cut(body, tools)


def sensor_carrier():
    """flange like the chassis (screw slots at ±30, sits on the box rim) + a square collar forward to the face back.
    Printed flange (back) down, no supports."""
    fl0, fl1 = P.WALL_D - P.FLANGE_T, P.WALL_D
    t = P.SENS_FACE_T
    h, ct = P.HALF, P.SENS_COLLAR_T
    flange = rrect(P.FLANGE_HALF, P.FLANGE_HALF, 3.0, fl0, fl1)
    collar = rrect(h, h, P.PLATE_CORNER_R, t, fl1).cut(rrect(h - ct, h - ct, 0.5, t - 1, fl1 + 1))
    body = fuse([flange, collar])
    tools = [rrect(h - ct, h - ct, 0.5, fl0 - 1, fl1 + 1)]
    for sx in (-1, 1):
        cx = sx * P.BOX_SCREW_PITCH / 2
        tools.append(box(cx - P.FLANGE_SLOT_W / 2, cx + P.FLANGE_SLOT_W / 2, -P.FLANGE_SLOT_L / 2, P.FLANGE_SLOT_L / 2,
                         fl0 - 1, fl1 + 1))
        tools.append(box(sx * 18.0, sx * 22.0, -31.5, -29.5, fl0 - 1, fl1 + 1))                  # cable-tie slots
    return cut(body, tools)


def amp_tray():
    """MAX98357A tray (bottom box, local coords): slid in from the open back between the two domes onto their ledges;
    the amp sits on its back face on 2 pins (its mounting holes). Printed flat, pins up, no supports."""
    ax, ay, ad = P.SENS_AMP
    hw, hh, tt = P.DESK_AMP_TRAY
    plate = box(-hw, hw, -hh, hh, ad, ad + tt)
    hy = ay + R.AMP_H / 2 - R.AMP_HOLE_C[1]
    pins = [cyl(ax + sx * (R.AMP_W / 2 - R.AMP_HOLE_C[0]), hy, 1.0, ad + tt - EPS, ad + tt + 3.0) for sx in (-1, 1)]
    return fuse([plate] + pins)


def dome_ledges(cy):
    """a ledge on the inner face of each dome of the box at y = cy: top face at the tray front d, 45° underside."""
    _, _, ad = P.SENS_AMP
    out = []
    for sx in (-1, 1):
        r0, r1 = P.BOX_DOME_R_IN, P.BOX_DOME_R_IN - P.DESK_LEDGE
        pts = [(r0, ad - P.DESK_LEDGE), (r0, ad), (r1, ad), (r1, ad - 0.01), (r0, ad - P.DESK_LEDGE)]
        poly = Part.makePolygon([V(sx * xx, cy - P.BOX_DOME_W / 2, -dd) for (xx, dd) in pts])
        out.append(Part.Face(poly).extrude(V(0, P.BOX_DOME_W, 0)))
    return out


def sensor_refs():
    """the boards as simple bodies (front view placement, chip side to the room) for the fit check."""
    t = P.SENS_FACE_T
    lay = sensor_layout()
    refs = {}
    for k, nm in (("radar", "LD2410C"), ("als", "VEML7700"), ("rh", "SHT31-D")):
        x0, x1, y0, y1 = lay[k]["box"]
        d_b = t + lay[k]["standoff"]
        refs[nm] = box(x0, x1, y0, y1, d_b, d_b + lay[k]["pcb"])
    x0, x1, y0, y1 = lay["radar"]["box"]
    d_b = t + lay["radar"]["standoff"] + R.RADAR_T
    refs["LD2410C header"] = box(x0 + 3.0, x1 - 3.0, y1 - 2.8, y1 - 0.2, d_b, d_b + lay["radar"]["back"])   # pins backwards
    m = lay["mic"]
    refs["INMP441"] = cyl(m["c"][0], m["c"][1], m["d"] / 2, t + m["standoff"], t + m["standoff"] + R.MIC_T)
    ax, ay, ad = P.SENS_AMP
    tt = P.DESK_AMP_TRAY[2]
    refs["MAX98357A"] = box(ax - R.AMP_W / 2, ax + R.AMP_W / 2, ay - R.AMP_H / 2, ay + R.AMP_H / 2, ad + tt, ad + tt + R.AMP_T)
    return refs


def moved(shape, dy):
    s = shape.copy()
    s.translate(V(0, dy, 0))
    return s


# ============================================================================ build + check + export
def build():
    print(f"\n==================== RoomKey DESK REPLICA (prototype, USB 5 V, never in a wall) — insert v{P.VERSION} ====")
    wb, fr, sc, sf, at = wall_block(), frame_2x(), sensor_carrier(), sensor_face(), amp_tray()
    own = {"wall block": wb, "frame 2-gang": fr, "sensor carrier": moved(sc, -PITCH), "sensor face": moved(sf, -PITCH),
           "amp tray": moved(at, -PITCH)}
    for nm, shp in own.items():
        bb = shp.BoundBox
        print(f"  {nm:15s} valid {shp.isValid()} | solids {len(shp.Solids)} | {bb.XLength:.1f} × {bb.YLength:.1f} × "
              f"{bb.ZLength:.1f} | {shp.Volume/1000:.1f} cm³ ≈ {shp.Volume/1000*1.27:.0f} g PETG")
    # the insert (Variant S) in the top box, exactly as insert_lib builds it
    pbody, prim = L.plate_parts("S")
    ins = {"key shell": L.key_shell(), "switch plate": L.switch_plate(), "collar": L.collar(), "plate": fuse([pbody, prim])}
    ins["chassis"], _ = L.chassis("S")
    refs = L.ref_bodies("S")
    keep = ("touch board", "MX switch 1", "MX switch 2", "speaker 2030", "LED 1", "LED 2", "LED 3", "LED 4", "box screw L",
            "box screw R", "load plate L", "load plate R", "cable loop")
    bodies = dict(own)
    bodies.update(ins)
    bodies.update({k: refs[k] for k in keep})
    bodies.update({k: moved(v, -PITCH) for k, v in sensor_refs().items()})
    # designed contacts: flanges rest on the wall plate, screws in their dome holes, the face spigot in the collar,
    # boards on their pads, the amp on its pins, the frame on the wall plate
    ex = {frozenset(("box screw L", "wall block")), frozenset(("box screw R", "wall block")),
          frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate")),
          frozenset(("MAX98357A", "amp tray"))}                # the amp's holes on the tray pins
    col = L.check_state(bodies, "desk replica, rest", ex)
    report = {"collisions": col, "gaps": {}}

    def g(a, b):
        return round(L.min_gap(bodies[a], bodies[b]), 3)
    for a, b in (("chassis", "wall block"), ("chassis", "frame 2-gang"), ("plate", "frame 2-gang"),
                 ("sensor carrier", "wall block"), ("sensor face", "frame 2-gang"), ("sensor carrier", "frame 2-gang"),
                 ("frame 2-gang", "wall block"), ("MAX98357A", "wall block"), ("amp tray", "wall block"), ("LD2410C header", "sensor carrier"),
                 ("SHT31-D", "sensor face"), ("VEML7700", "sensor face"), ("LD2410C", "sensor face"), ("INMP441", "sensor face")):
        report["gaps"][f"{a} ↔ {b}"] = g(a, b)
    # the insert's moving states against the replica (plate pressed, key rocked) — only the replica parts are new here
    for case in ("left wing", "top band", "bottom band"):
        pp = L.plate_pressed(bodies["plate"], case)
        report["gaps"][f"plate pressed ({case}) ↔ frame 2-gang"] = round(L.min_gap(pp, fr), 3)
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    for k, v in report["gaps"].items():
        print(f"    gap {k:55s} {v}")
    L.export(wb, "desk_wall_block", "front_down")
    L.export(fr, "desk_frame_2x", "front_down")
    L.export(sc, "desk_sensor_carrier", "back_down")
    L.export(sf, "desk_sensor_face", "front_down")
    L.export(at, "desk_amp_tray", "front_down")
    Part.makeCompound(list(bodies.values())).exportStep(os.path.join(L.OUT, "desk-replica_assembly.step"))
    L.write_stl(Part.makeCompound(list(own.values()) + list(ins.values())), os.path.join(L.OUT, "desk-replica_printed-assembly.stl"),
                0.05, 0.4)
    with open(os.path.join(L.OUT, "desk-replica_check.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    return report


# ============================================================================ practice box (1 box + 1-gang frame)
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
