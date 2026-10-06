"""RoomKey wall insert (DRAFT, version = insert_params.VERSION) — FreeCAD part builders, reference bodies, checks, export.

Used by make_key_module.py, make_insert_L.py and make_insert_S.py. Geometry comes ONLY from
insert_params.py (which imports roomkey_params.py). Runs headless in FreeCADCmd.

Coordinates: (x, y, d) with d = depth into the wall → FreeCAD (X, Y, Z = −d); +Z points into the room.
Every number below that is not a parameter is a pure modelling detail (fillet, overlap epsilon, visual
thickness of a reference body) and is named where it matters.
"""
import json
import math
import os
import sys

import FreeCAD as App
import Part

try:                      # FreeCADCmd's stdout is ASCII even with PYTHONIOENCODING set
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:         # noqa: BLE001
    pass

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_params as P  # noqa: E402

R = P.R
V = App.Vector
OUT = os.path.join(os.path.dirname(HERE), "models")
SECT = os.path.join(os.path.dirname(HERE), "drawings", "sections")
os.makedirs(OUT, exist_ok=True)
os.makedirs(SECT, exist_ok=True)
EPS = 0.01
WALL = 0.8              # printed pocket wall (2 perimeters at 0.4 nozzle)
TRIM_FAIL_MM3 = 0.5     # the allowed-space trim may only remove slivers


# ============================================================================ primitives
def box(x0, x1, y0, y1, d0, d1):
    x0, x1, y0, y1, d0, d1 = min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(d0, d1), max(d0, d1)
    return Part.makeBox(x1 - x0, y1 - y0, d1 - d0, V(x0, y0, -d1))


def cyl(cx, cy, r, d0, d1):
    return Part.makeCylinder(r, d1 - d0, V(cx, cy, -d1), V(0, 0, 1))


def rrect(hx, hy, r, d0, d1, cx=0.0, cy=0.0):
    """rounded rectangle prism, half sizes hx, hy, corner radius r."""
    r = max(0.0, min(r, hx - 0.01, hy - 0.01))
    if r < 0.05:
        return box(cx - hx, cx + hx, cy - hy, cy + hy, d0, d1)
    z0 = -d1
    x0, x1, y0, y1 = cx - hx, cx + hx, cy - hy, cy + hy
    k = math.sqrt(0.5)
    e = [Part.LineSegment(V(x0 + r, y0, z0), V(x1 - r, y0, z0)).toShape(),
         Part.Arc(V(x1 - r, y0, z0), V(x1 - r + r * k, y0 + r - r * k, z0), V(x1, y0 + r, z0)).toShape(),
         Part.LineSegment(V(x1, y0 + r, z0), V(x1, y1 - r, z0)).toShape(),
         Part.Arc(V(x1, y1 - r, z0), V(x1 - r + r * k, y1 - r + r * k, z0), V(x1 - r, y1, z0)).toShape(),
         Part.LineSegment(V(x1 - r, y1, z0), V(x0 + r, y1, z0)).toShape(),
         Part.Arc(V(x0 + r, y1, z0), V(x0 + r - r * k, y1 - r + r * k, z0), V(x0, y1 - r, z0)).toShape(),
         Part.LineSegment(V(x0, y1 - r, z0), V(x0, y0 + r, z0)).toShape(),
         Part.Arc(V(x0, y0 + r, z0), V(x0 + r - r * k, y0 + r - r * k, z0), V(x0 + r, y0, z0)).toShape()]
    return Part.Face(Part.Wire(e)).extrude(V(0, 0, d1 - d0))


def ring(hx_o, hy_o, r_o, hx_i, hy_i, r_i, d0, d1):
    return rrect(hx_o, hy_o, r_o, d0, d1).cut(rrect(hx_i, hy_i, r_i, d0 - 1, d1 + 1))


def csk_back(cx, cy, d_face, d_through, head_d, hole_d):
    """countersunk hole whose head lies on the REAR face (larger d)."""
    h = (head_d - hole_d) / 2.0
    cone = Part.makeCone(head_d / 2, hole_d / 2, h, V(cx, cy, -d_face - EPS), V(0, 0, 1))
    return cone.fuse(cyl(cx, cy, hole_d / 2, d_through - EPS, d_face + EPS))


def csk_front(cx, cy, d_face, d_through, head_d, hole_d):
    """countersunk hole whose head lies on the FRONT face (smaller d)."""
    h = (head_d - hole_d) / 2.0
    cone = Part.makeCone(hole_d / 2, head_d / 2, h + EPS, V(cx, cy, -d_face - h), V(0, 0, 1))
    return cone.fuse(cyl(cx, cy, hole_d / 2, d_face, d_through + EPS))


def fuse(shapes):
    s = shapes[0]
    if len(shapes) > 1:
        s = s.fuse(shapes[1:])
    return s.removeSplitter()


def cut(shape, tools):
    tools = [t for t in tools if t is not None]
    if not tools:
        return shape
    return shape.cut(tools).removeSplitter()


def lip_prism(x0, x1, sy, y_in, y_out, d0, d1, chamfer=0.0):
    """lip along x (x0..x1) on the edge sy (±1): inner edge |y| = y_in, root |y| = y_out, catch face d0, back d1.
    chamfer = 45° lead-in on the back-inner edge (the edge that meets the tongue first when the plate is pressed on)."""
    pts = [(y_out, d0), (y_in, d0)]
    if chamfer > 0:
        pts += [(y_in, d1 - chamfer), (y_in + chamfer, d1)]
    else:
        pts += [(y_in, d1)]
    pts += [(y_out, d1), (y_out, d0)]
    poly = Part.makePolygon([V(min(x0, x1), sy * yy, -dd) for (yy, dd) in pts])
    return Part.Face(poly).extrude(V(abs(x1 - x0), 0, 0))


def segments(lo, hi):
    """the three segments of an edge run lo..hi (symmetric) that stay outside the rim gaps |SKIRT_GAP|."""
    g0, g1 = P.SKIRT_GAP
    return [(lo, -g1), (-g0, g0), (g1, hi)]


# ============================================================================ allowed space
def allowed_space():
    """Fixed parts may exist: in the frame tunnel in front of the wall, as the flange under the frame, in the box."""
    lim = P.FRAME_OPEN / 2 - P.FRAME_TUNNEL_MARGIN
    fz = box(-lim, lim, -lim, lim, -2.0, P.WALL_D)
    fl = rrect(P.FLANGE_HALF, P.FLANGE_HALF, 3.0, P.WALL_D - P.FLANGE_T, P.WALL_D)
    r = P.BOX_USABLE_D / 2 - P.FIT_MARGIN
    inside = cyl(0, 0, r, P.WALL_D - EPS, P.box_floor())
    inside = inside.cut(domes(P.FIT_MARGIN, P.WALL_D - EPS, 99))
    return fuse([fz, fl, inside])


def domes(grow, d0, d1):
    out = []
    for ang in P.BOX_DOME_ANGLES:
        a = math.radians(ang)
        ca, sa = round(math.cos(a)), round(math.sin(a))
        r0, r1, w = P.BOX_DOME_R_IN - grow, P.BOX_DOME_R_OUT, P.BOX_DOME_W / 2 + grow
        if ca:
            out.append(box(min(ca * r0, ca * r1), max(ca * r0, ca * r1), -w, w, d0, d1))
        else:
            out.append(box(-w, w, min(sa * r0, sa * r1), max(sa * r0, sa * r1), d0, d1))
    return out


# ============================================================================ key module
def key_shell():
    s = P.KS
    fit = R.KEY_FIT
    outer = rrect(P.KEY_W / 2, P.KEY_H / 2, P.KEY_R, s["glass"], s["key_back"])
    pocket = rrect(R.TB_W / 2 + fit, R.TB_H / 2 + fit, R.TB_CORNER_R + fit, s["glass"] - 1.0, s["standoff_end"])
    tools = [pocket]
    holes = [(-R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2), (R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2),
             (-R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2), (R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2)]
    for (x, y) in holes:
        tools.append(csk_back(x, y, s["key_back"], s["standoff_end"] - 0.5, P.M2_CSK_D + 0.2, 2.2))
    tools.append(box(-P.CABLE_SLOT[0] / 2, P.CABLE_SLOT[0] / 2, P.CABLE_Y - P.CABLE_SLOT[1] / 2, P.CABLE_Y + P.CABLE_SLOT[1] / 2,
                     s["standoff_end"] - 0.5, s["key_back"] + 0.5))
    tools += key_end_taper()
    tools += key_header_slots()
    shell = cut(outer, tools)
    # side skirts only (straight long sides): they limit roll in the collar, the short sides stay free → free pitch
    skirts = [box(sx * (P.KEY_W / 2 - R.KEY_WALL), sx * P.KEY_W / 2, -P.KEY_SKIRT_Y, P.KEY_SKIRT_Y, s["key_back"] - EPS,
                  s["skirt_end"]) for sx in (-1, 1)]
    # v0.9 rigid key: stem posts with cross sockets (fixed on MX1, floating along y on MX2) + 4 stop bosses that land on
    # the switch plate after KEY_TRAVEL (the press ends on the plate, not on the stems)
    stops = [box(sx * P.STOP_X[0], sx * (P.STOP_X[1] + EPS), y - P.STOP_W_Y / 2, y + P.STOP_W_Y / 2, s["key_back"] - EPS,
                 P.STOP_END_D) for sx in (-1, 1) for y in P.STOP_YS]
    # v0.8 key catch: a rigid nub at the free end of each side skirt (runs in the collar's groove; see collar())
    yc, yl = P.KEY_CATCH_YC, P.KEY_CATCH_Y / 2
    nubs = [box(sx * (P.KEY_W / 2 - EPS), sx * (P.KEY_W / 2 + P.KEY_CATCH_X), yc - yl, yc + yl, s["skirt_end"] - P.KEY_CATCH_D,
                s["skirt_end"]) for sx in (-1, 1)]
    # cable strain relief: two lugs beside the slot (a cable tie / glue point)
    lug_x1 = min(P.CABLE_SLOT[0] / 2 + 1.2, R.TB_HEADER_PITCH_X / 2 - P.HEADER_SLOT_W / 2 - 0.1)
    relief = [box(sx * P.CABLE_SLOT[0] / 2, sx * lug_x1, P.CABLE_Y - 3.0, P.CABLE_Y + 3.0,
                  s["key_back"] - EPS, s["key_back"] + 1.2) for sx in (-1, 1)]
    # wire channel: a KEY_BACK_CHANNEL recess in the back's inner face between the header columns and the cable slot
    return cut(fuse([shell] + skirts + nubs + [key_posts()] + stops + relief), [key_channel()] + key_sockets())


def key_posts():
    s = P.KS
    return fuse([cyl(x, y, R.MX_POST_D / 2, s["key_back"] - EPS, s["post_end"]) for (x, y) in R.MX_SW_POS])


def key_sockets():
    """v0.9: the v0.5 cross sockets (coupon v0 row C fit). MX1 (top) = FIXED: full cross. MX2 (bottom) = FLOATING: the
    y-arm slot runs through the post (the halves clamp the arm's width → held in x) and the x-arm slot is 2 ×
    KEY_SOCKET_FLOAT wider → the stem floats along y, so a pitch error cannot strain the two stems against each other."""
    s = P.KS
    d_top = s["post_end"] - R.KEY_SOCKET_DEPTH
    L, W, f = R.MX_STEM_ARM_L, R.MX_STEM_ARM_W, R.KEY_SOCKET_FLOAT
    out = []
    for i, (x, y) in enumerate(R.MX_SW_POS):
        ly = L if i == 0 else R.MX_POST_D + 1.0
        wy = W if i == 0 else W + 2 * f
        out.append(box(x - L / 2, x + L / 2, y - wy / 2, y + wy / 2, d_top, s["post_end"] + EPS))      # x-arm
        out.append(box(x - W / 2, x + W / 2, y - ly / 2, y + ly / 2, d_top, s["post_end"] + EPS))      # y-arm
    return out


def key_end_taper():
    """the "funnel": the short-end walls are set back by KEY_END_TAPER, rising linearly over KEY_END_TAPER_RUN behind the
    glass — room under the plate edge for the dipping end when the key rocks."""
    s = P.KS
    h, t, run = P.KEY_H / 2, R.KEY_END_TAPER, R.KEY_END_TAPER_RUN
    g0, back = s["glass"], s["skirt_end"] + 1.0
    out = []
    for sy in (-1, 1):
        pts = [(h, g0 - 1.0), (h, g0), (h - t, g0 + run), (h - t, back), (h + 5.0, back), (h + 5.0, g0 - 1.0), (h, g0 - 1.0)]
        x0 = -P.KEY_W / 2 - 1.0
        poly = Part.makePolygon([V(x0, sy * yy, -dd) for (yy, dd) in pts])
        out.append(Part.Face(poly).extrude(V(P.KEY_W + 2.0, 0, 0)))
    return out


def key_channel():
    """the wire channel in the key back's inner face: a band across both header columns (y clear of the stem posts by
    ≥ 2) to the cable slot (pins y +9.65 … −15.75 [DS drawing: first pin 9.85 below the top hole])."""
    s = P.KS
    hx = R.TB_HEADER_PITCH_X / 2 + 1.5
    d0, d1 = s["standoff_end"] - EPS, s["standoff_end"] + P.KEY_BACK_CHANNEL
    return box(-hx, hx, P.CABLE_Y - 8.0, P.CABLE_Y + 8.0, d0, d1)    # the strips along the columns are now through-slots


def key_header_slots():
    """owner 2026-10-03: pins or wires may leave the header holes straight back → one slot through the key back under each
    pin column (it replaces the old channel strip there)."""
    s = P.KS
    w = P.HEADER_SLOT_W / 2
    y0, y1 = P.HEADER_SLOT_Y
    return [box(sx * (R.TB_HEADER_PITCH_X / 2 - w), sx * (R.TB_HEADER_PITCH_X / 2 + w), y0, y1, s["standoff_end"] - 0.5,
                s["key_back"] + 0.5) for sx in (-1, 1)]


def switch_plate():
    s = P.KS
    hx, hy = P.WELL_IN_X - P.SWP_CLEAR, P.WELL_IN_Y - P.SWP_CLEAR
    plate = rrect(hx, hy, P.WELL_R - P.SWP_CLEAR, s["plate_front"], s["plate_back"])
    tools = []
    for (x, y) in R.MX_SW_POS:
        c = R.MX_CUT
        tools.append(box(x - c / 2, x + c / 2, y - c / 2, y + c / 2, s["plate_front"] - EPS, s["plate_back"] + EPS))
    tools.append(box(-(P.CABLE_SLOT[0] / 2 + 0.2), P.CABLE_SLOT[0] / 2 + 0.2, P.CABLE_Y - P.CABLE_SLOT[1] / 2 - 0.1,
                     P.CABLE_Y + P.CABLE_SLOT[1] / 2 + 0.1, s["plate_front"] - EPS, s["plate_back"] + EPS))
    for (x, y) in P.SWP_SCREWS:
        tools.append(csk_front(x, y, s["plate_front"], s["plate_back"], P.M2_CSK_D + 0.2, 2.2))
    for (x, y) in P.LED_POS:          # v0.6: corner notches for the glow LEDs (WS2812B-MINI 3535 is 2.0 tall + joints/carrier)
        h = P.LED_W / 2 + 0.4
        tools.append(box(x - h, x + h, y - h, y + h, s["plate_front"] - 1, s["plate_back"] + 1))
    return cut(plate, tools)


def collar():
    """translucent light guide around the key; thick (2.6) along the corner diagonals where the LEDs sit; the inner face
    at the short sides is set back over the first mm (room for the key's end when it is pressed at an end)."""
    c = ring(P.COLLAR_OUT_X, P.COLLAR_OUT_Y, P.COLLAR_OUT_R, P.WELL_IN_X, P.WELL_IN_Y, P.WELL_R, P.COLLAR_D0, P.COLLAR_D1)
    rl, rd = P.COLLAR_RELIEF
    # v0.8: a groove for the key's catch nub on each long side, open to the back face, closed towards the room
    s = P.KS
    gx = P.KEY_W / 2 + P.KEY_CATCH_X + P.GROOVE_CLEAR[0]
    gy = P.KEY_CATCH_Y / 2 + P.GROOVE_CLEAR[1]
    g0 = s["skirt_end"] - P.KEY_CATCH_D - P.KEY_CATCH_GAP
    grooves = [box(sx * (P.WELL_IN_X - 0.5), sx * gx, P.KEY_CATCH_YC - gy, P.KEY_CATCH_YC + gy, g0, P.COLLAR_D1 + 1)
               for sx in (-1, 1)]
    return cut(c, [rrect(P.WELL_IN_X, P.WELL_IN_Y + rl, P.WELL_R, P.COLLAR_D0 - 1, P.COLLAR_D0 + rd)] + grooves)


# ============================================================================ plate (L and S)
def glow_rim():
    return ring(P.CUT_W / 2 + P.GLOW_RIM_W, P.CUT_H / 2 + P.GLOW_RIM_W, P.CUT_R + P.GLOW_RIM_W,
                P.CUT_W / 2, P.CUT_H / 2, P.CUT_R, 0.0, P.PLATE_T)


def plate_parts(v):
    """(ivory/black body, translucent glow rim) — co-printed as one multi-part object (AMS)."""
    half, t = P.HALF, P.PLATE_T
    sk_in, sk_out = half - P.PLATE_SKIRT_T, half - 0.4       # skirt inner face 26.3, outer face 27.1 (0.4 step behind the edge)
    parts = [rrect(half, half, P.PLATE_CORNER_R, 0.0, t)]
    # side and bottom skirts: short (d 4.2), they hug the deck edges → locate x and y; open where the frame rims stand
    for sx in (-1, 1):
        for (a, b) in segments(-half + 1.0, half - 1.0):
            parts.append(box(sx * sk_in, sx * sk_out, a, b, t - EPS, P.SKIRT_D))
    for (a, b) in segments(-sk_out, sk_out):
        parts.append(box(a, b, -sk_out, -sk_in, t - EPS, P.SKIRT_D))
    # top skirt + rigid drawer lip (three segments)
    for (a, b) in segments(-sk_out, sk_out):
        parts.append(box(a, b, sk_in, sk_out, t - EPS, P.LIP_D1))
        parts.append(lip_prism(max(a, -sk_in), min(b, sk_in), +1, sk_in - P.LIP_IN, sk_in + EPS, P.LIP_D0, P.LIP_D1))
    # bottom corners: deep skirt segments carrying the two snap lips (chamfered lead-in)
    x0, x1 = P.SNAP_X
    for sx in (-1, 1):
        parts.append(box(sx * (x0 - 0.5), sx * sk_out, -sk_out, -sk_in, t - EPS, P.SNAP_D1))
        parts.append(lip_prism(sx * x0, sx * x1, -1, sk_in - P.LIP_IN, sk_in + EPS, P.SNAP_D0, P.SNAP_D1, P.SNAP_CHAMFER))
    for (x, y) in P.SW_POS:
        parts.append(cyl(x, y, 1.25, t - EPS, t + P.NUB_H))
    if v == "S" and P.S_PLATE_FIXED:
        for (x, y) in P.S_REST_PADS:
            parts.append(cyl(x, y, 1.2, t - EPS, P.DECK_D0))
    body = fuse(parts)
    tools = [rrect(P.CUT_W / 2, P.CUT_H / 2, P.CUT_R, -1.0, P.SNAP_D1 + 1.0)]
    for sx in (-1, 1):
        for x in P.PERF_XS:
            for y in P.PERF_YS:
                tools.append(cyl(sx * x, y, P.PERF_D / 2, -1.0, t + 0.2))
    # mesh recesses (0.2) behind both strips; on the left the mic carrier is bonded directly to the plate above the recess
    c0, c1 = P.cols_span()
    r0, r1 = P.rows_span()
    mm = P.MESH_MARGIN
    mx0, mx1, my0, my1, _, _ = P.mic_carrier_box()
    tools.append(box(c0 - mm, c1 + mm, r0 - mm, r1 + mm, t - P.MESH_T, t + EPS))
    tools.append(box(-(c1 + mm), -(c0 - mm), r0 - mm, my0 - 0.3, t - P.MESH_T, t + EPS))
    body = cut(body, tools)
    rim = glow_rim()
    return cut(body, [rim]), rim


def plate(v):
    b, r = plate_parts(v)
    return fuse([b, r])


# ============================================================================ chassis
def spk_tab_slot():
    """v0.9.1: blind slot in the SPK_TAB_END cradle rib for the speaker's wire tab: from the speaker's end face out to the
    tab + play, along d from in front of the tab to behind the rib (open to the back: the speaker goes in from behind and
    the wires leave there), across the speaker's thickness. Returns box() arguments (x0, x1, y0, y1, d0, d1)."""
    sy = P.SPK_TAB_END
    gx = P.SPK_X0 + R.SPK_T
    w, ov = R.SPK_TAB
    pw, pd, _ = P.SPK_TAB_SLOT
    dc = P.SPK_D0 + R.SPK_W / 2
    ya, yb = sy * (P.SPK_Y[1] + 0.2 - EPS), sy * (P.SPK_Y[1] + ov + pd)
    return (P.SPK_X0 - 0.2, gx + 0.2, min(ya, yb), max(ya, yb), dc - w / 2 - pw,
            P.SPK_D0 + R.SPK_W + 0.1 + P.SPK_HOOK_T + 1.0)


def chassis(v):
    s = P.KS
    d0, d1 = P.DECK_D0, P.DECK_D1
    fl0, fl1 = P.WALL_D - P.FLANGE_T, P.WALL_D
    ledge0, ledge1 = s["plate_back"], s["plate_back"] + P.LEDGE
    tip, front, back, cback = P.sw_depths()
    gx = P.grille_x()
    g = P.SPK_FACE_GASKET[2]
    add, tools = [], []
    # deck; the two bottom tongues get a rib to TONGUE_D1 (tall thin section: soft in y for the snap, stiff in d)
    add.append(rrect(P.DECK_HALF_X, P.DECK_HALF_Y, P.DECK_R, d0, d1))
    for sx in (-1, 1):
        add.append(box(sx * (P.TONGUE_X[0] - 1.0), sx * (P.TONGUE_X[1] - P.DECK_R), -P.DECK_HALF_Y, -(P.DECK_HALF_Y - P.TONGUE_W),
                       d1 - EPS, P.TONGUE_D1))
    # rear well wall behind the collar + ledge + switch-plate bosses
    add.append(ring(P.COLLAR_OUT_X, P.COLLAR_OUT_Y, P.COLLAR_OUT_R, P.WELL_IN_X, P.WELL_IN_Y, P.WELL_R, P.COLLAR_D1, ledge1))
    add.append(ring(P.WELL_IN_X + 0.1, P.WELL_IN_Y + 0.1, P.WELL_R + 0.1, P.WELL_IN_X - P.LEDGE, P.WELL_IN_Y - P.LEDGE,
                    P.WELL_R - P.LEDGE, ledge0, ledge1))
    for (x, y) in P.SWP_SCREWS:
        add.append(cyl(x, y, P.SWP_BOSS_D / 2, ledge0, ledge0 + P.SWP_BOSS_H))
        add.append(box(x, math.copysign(P.WELL_IN_X, x), y - 1.5, y + 1.5, ledge0, ledge0 + P.SWP_BOSS_H))
    # webs carrying the rear wall: clear of the collar (0.1) in front of its back face, fused to the rear wall behind it.
    cx0 = P.COLLAR_OUT_X + 0.1
    for sx in (-1, 1):
        for sy in (-1, 1):
            yy0, yy1 = sorted((sy * 16.2, sy * 17.5))
            add.append(box(sx * (cx0 + 0.35), sx * 16.2, yy0, yy1, fl0 - EPS, P.COLLAR_D1 + EPS))
            add.append(box(sx * (P.WELL_IN_X + 0.2), sx * 16.2, yy0, yy1, P.COLLAR_D1 - EPS, P.COLLAR_D1 + 1.0))
    add.append(box(-16.2, -cx0, -10.0, 3.5, d1 - EPS, P.COLLAR_D1 + EPS))
    add.append(box(-16.2, -P.WELL_IN_X - 0.2, -10.0, 3.5, P.COLLAR_D1 - EPS, P.COLLAR_D1 + 1.0))
    # island ribs: tie the top and bottom rear-wall segments (between the LED windows) to the flange → printable
    for sx in (-1, 1):
        for sy in (-1, 1):
            xa, xb = sorted((sx * 4.5, sx * 7.0))
            ya, yb = sorted((sy * (P.COLLAR_OUT_Y + P.COLLAR_FIT), sy * (P.COLLAR_OUT_Y + P.COLLAR_FIT + 0.8)))
            add.append(box(xa, xb, ya, yb, fl0 - EPS, P.COLLAR_D1 + 1.0))
            ya, yb = sorted((sy * P.WELL_IN_Y, sy * (P.COLLAR_OUT_Y + P.COLLAR_FIT + 0.8)))
            add.append(box(xa, xb, ya, yb, P.COLLAR_D1 - EPS, P.COLLAR_D1 + 1.0))
    # flange with screw slots, load-plate recesses and openings
    flange = rrect(P.FLANGE_HALF, P.FLANGE_HALF, 3.0, fl0, fl1)
    fl_tools = [rrect(P.COLLAR_OUT_X + P.COLLAR_FIT, P.COLLAR_OUT_Y + P.COLLAR_FIT, P.COLLAR_OUT_R + P.COLLAR_FIT, fl0 - 1, fl1 + 1)]
    lx0, lx1, lhy, lpt = P.LOAD_PLATE
    for sx in (-1, 1):
        cx = sx * P.BOX_SCREW_PITCH / 2
        fl_tools.append(box(cx - P.FLANGE_SLOT_W / 2, cx + P.FLANGE_SLOT_W / 2, -P.FLANGE_SLOT_L / 2, P.FLANGE_SLOT_L / 2, fl0 - 1, fl1 + 1))
        fl_tools.append(box(cx + sx * (lx0 - 0.1), sx * (P.FLANGE_HALF + 1.0), -lhy - 0.1, lhy + 0.1, fl0 - 1, fl0 + lpt))
    fl_tools.append(box(P.COLLAR_OUT_X + P.COLLAR_FIT - 0.5, P.DUCT_X1 + P.DUCT_WALL - 0.3, P.SPK_Y[0] - 0.2,
                        P.SPK_Y[1] + 0.2, fl0 - 1, fl1 + 1))                              # speaker/duct passage
    mx, my = P.MIC_PORT
    for (x, y) in P.SW_POS:
        wx, wy = P.wire_slot(x, y)
        fl_tools.append(box(wx - P.CARRIER_WIRE_SLOT[0] / 2, wx + P.CARRIER_WIRE_SLOT[0] / 2, wy - P.CARRIER_WIRE_SLOT[1] / 2,
                            wy + P.CARRIER_WIRE_SLOT[1] / 2, fl0 - 1, fl1 + 1))     # 2 wires + their joints (carrier back)
    rx0, rx1, ry0, ry1 = P.SNAP_RELIEF
    for sx in (-1, 1):                                                                     # snap-lip windows
        fl_tools.append(box(sx * rx0, sx * rx1, -ry0, -ry1, fl0 - 1, fl1 + 1))
    add.append(cut(flange, fl_tools))
    # frame locating rims on all four sides, standing in the gaps of the plate skirts
    for (a0, a1, b0, b1) in P.loc_rims():
        add.append(box(a0, a1, b0, b1, P.LOC_RIM_D0, fl0 + EPS))
    # switch pockets: walls around each carrier from the deck to the flange (the carrier rests on the flange front face)
    for (x, y) in P.SW_POS:
        hx, hy = P.CARRIER[0] / 2 + 0.2, P.CARRIER[1] / 2 + 0.2
        add.append(box(x - hx - WALL, x + hx + WALL, y - hy - WALL, y + hy + WALL, d1 - EPS, fl0 + EPS))
    # mic pocket: clearance around the carrier that moves with the plate; walls + floor with a wire hole
    x0, x1, y0, y1, md0, md1 = P.mic_carrier_box()
    mc = P.MIC_POCKET_CLEAR
    t_mic = 1.4                                               # carrier travel allowance (plate travel at the mic ≤ 1.3)
    mic_floor = md1 + t_mic + 0.3
    add.append(box(x0 - mc - WALL, x1 + mc + WALL, y0 - mc - WALL, y1 + mc + WALL, d1 - EPS, mic_floor + WALL))
    wx0, wx1, wy0, wy1 = P.mic_well()
    add.append(box(wx0 - WALL, wx1 + WALL, wy0 - WALL, wy1, d1 - EPS, fl0 + EPS))     # walled wire well (chimney) to the flange
    # duct: plenum floor (d DECK_D1..SPK_D0) over the speaker's front edge + channel from the face gasket to the duct wall
    m0, m1, n0, n1 = P.mouth()
    pd0, pd1 = P.port_d()
    w = P.DUCT_WALL
    add.append(box(m0 - w, P.DUCT_X1 + w, n0 - w, n1 + w, d1 - EPS, P.SPK_D0))
    add.append(box(gx + g, P.DUCT_X1 + w, n0 - w, n1 + w, P.SPK_D0 - EPS, pd1 + w))
    # speaker cradle ribs: clear of the collar in front of its back face, fused to the rear wall behind it; snap hooks at
    # the back that catch the speaker's back edge (the speaker goes in from behind)
    for sy in (-1, 1):
        y0_, y1_ = sorted((sy * (P.SPK_Y[1] + 0.2), sy * (P.SPK_Y[1] + 1.2)))
        add.append(box(P.COLLAR_OUT_X + P.COLLAR_FIT, gx + 1.0, y0_, y1_, d1 - EPS, P.SPK_D0 + R.SPK_W))
        add.append(box(P.WELL_IN_X + 0.2, gx + 1.0, y0_, y1_, P.COLLAR_D1 - EPS, P.HUB[4] - 0.2))
        add.append(box(P.HUB[1] + 0.5, gx + 1.0, y0_, y1_, P.HUB[4] - 0.2 - EPS, P.SPK_D0 + R.SPK_W + 0.1 + P.SPK_HOOK_T))
        # hook: catch face 0.1 behind the speaker's back edge, 45° lead-in on its back face (the speaker comes from behind).
        # v0.9.1: not on the tab end — the tab slot cut its root and left the tip loose (2nd solid); at the speaker's round
        # end it caught nothing anyway (SPK_END_R)
        if sy != P.SPK_TAB_END:
            add.append(lip_prism(P.HUB[1] + 0.5, gx - 0.5, sy, P.SPK_Y[1] - P.SPK_HOOK, P.SPK_Y[1] + 0.2 + EPS,
                                 P.SPK_D0 + R.SPK_W + 0.1, P.SPK_D0 + R.SPK_W + 0.1 + P.SPK_HOOK_T, chamfer=P.SPK_HOOK))
        if sy == P.SPK_TAB_END:      # v0.9.1: the rib is thickened outward where the tab slot runs (wall stays ≥ 0.8)
            sd0 = spk_tab_slot()[4]
            outer = P.SPK_Y[1] + R.SPK_TAB[1] + P.SPK_TAB_SLOT[1] + P.SPK_TAB_SLOT[2]
            ty0, ty1 = sorted((sy * (P.SPK_Y[1] + 1.2 - EPS), sy * outer))
            add.append(box(P.COLLAR_OUT_X + P.COLLAR_FIT, gx + 1.0, ty0, ty1, sd0 - P.SPK_TAB_SLOT[2],
                           P.SPK_D0 + R.SPK_W + 0.1 + P.SPK_HOOK_T))
    # hub posts from the ledge, anchor posts + bar for the cable loop
    for (x, y) in P.HUB_POSTS:
        add.append(cyl(x, y, 1.5, ledge1 - EPS, P.HUB[4]))
    for (x, y) in P.ANCHOR_POSTS:
        add.append(cyl(x, y, 1.2, ledge0, P.ANCHOR[5]))
        add.append(box(x, math.copysign(P.WELL_IN_X, x), y - 1.0, y + 1.0, ledge0, ledge1))
    ax0, ax1, ay0, ay1, ad0, ad1 = P.ANCHOR
    add.append(box(ax0, ax1, ay0, ay1, ad0, ad1))
    body = fuse(add)

    # ---------------- cuts
    tools.append(rrect(P.COLLAR_OUT_X + P.COLLAR_FIT, P.COLLAR_OUT_Y + P.COLLAR_FIT, P.COLLAR_OUT_R + P.COLLAR_FIT,
                       d0 - 1, P.COLLAR_D1))                                       # collar seat through the deck
    tools.append(rrect(P.WELL_IN_X, P.WELL_IN_Y, P.WELL_R, d0 - 1, ledge0))        # well behind the collar
    tools.append(box(x0 - mc, x1 + mc, y0 - mc, y1 + mc, d0 - 1, mic_floor))           # mic pocket (moving carrier)
    tools.append(box(wx0, wx1, wy0, wy1 + EPS, d0 - 1, fl1 + 1))                       # mic wire well: beside the pocket,
    #                                                                                   through deck, chimney and flange
    for (x, y) in P.SW_POS:
        tools.append(box(x - P.CARRIER[0] / 2 - 0.2, x + P.CARRIER[0] / 2 + 0.2, y - P.CARRIER[1] / 2 - 0.2,
                         y + P.CARRIER[1] / 2 + 0.2, d0 - 1, fl0 + 2 * EPS))                # carrier pocket, open to the front
    tools.append(box(m0, m1, n0, n1, d0 - 1, d1))                                               # mouth: a recess in the deck
    tools.append(box(gx + g - EPS, P.DUCT_X1, n0, n1, d1 - 2 * EPS, pd1))                        # channel (opens the floor)
    tools.append(box(P.SPK_X0 - 0.2, gx + g, P.SPK_Y[0] - 0.2, P.SPK_Y[1] + 0.2, P.SPK_D0,
                     P.SPK_D0 + R.SPK_W + 0.1))                                                  # speaker + face gasket
    tools.append(box(*spk_tab_slot()))                                                           # v0.9.1 tab slot
    for (x, y) in P.PAD_POS:                                                                     # preload pad pockets
        tools.append(box(x - P.PAD_SIZE[0] / 2 - 0.1, x + P.PAD_SIZE[0] / 2 + 0.1, y - P.PAD_SIZE[1] / 2 - 0.1,
                         y + P.PAD_SIZE[1] / 2 + 0.1, d0 - 1, d0 + P.PAD_POCKET))
    # LED windows: the rear wall is opened at each corner over the LED depth (cuts perpendicular to the straight runs)
    ax0 = P.KEY_W / 2 - P.KEY_R + 1.0
    ay0 = P.KEY_H / 2 - P.KEY_R + 1.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            xx0, xx1 = sorted((sx * ax0, sx * (P.COLLAR_OUT_X + 1.0)))
            yy0, yy1 = sorted((sy * ay0, sy * (P.COLLAR_OUT_Y + 1.0)))
            tools.append(box(xx0, xx1, yy0, yy1, P.COLLAR_D1 - EPS, P.LED_D0 + P.LED_T + P.LED_CARRIER_T + 0.35))
    for (x, y) in P.SWP_SCREWS:
        tools.append(cyl(x, y, 0.85, ledge0 - 1, ledge0 + P.SWP_BOSS_H - 0.8))
    # bottom tongues: slot inboard of each tongue (through deck + rib, round root end) and a lead-in on the front-outer edge
    ty_in = P.DECK_HALF_Y - P.TONGUE_W
    rs = P.TONGUE_SLOT / 2
    c = P.TONGUE_CHAMFER
    for sx in (-1, 1):
        tools.append(box(sx * (P.TONGUE_X[0] + rs), sx * (P.DECK_HALF_X + 1.0), -ty_in, -(ty_in - P.TONGUE_SLOT), d0 - 1,
                         P.TONGUE_D1 + EPS))
        tools.append(cyl(sx * (P.TONGUE_X[0] + rs), -(ty_in - rs), rs, d0 - 1, P.TONGUE_D1 + EPS))
        tri = Part.makePolygon([V(0, -(P.DECK_HALF_Y - c), -(d0 - EPS)), V(0, -(P.DECK_HALF_Y + EPS), -(d0 - EPS)),
                                V(0, -(P.DECK_HALF_Y + EPS), -(d0 + c)), V(0, -(P.DECK_HALF_Y - c), -(d0 - EPS))])
        x_a, x_b = sorted((sx * P.TONGUE_X[0], sx * (P.DECK_HALF_X + 1.0)))
        pr = Part.Face(tri).extrude(V(x_b - x_a, 0, 0))
        pr.translate(V(x_a, 0, 0))
        tools.append(pr)
    body = cut(body, tools)
    allowed = allowed_space()
    trimmed = body.common(allowed).removeSplitter()
    lost = body.Volume - trimmed.Volume
    return trimmed, lost


# ============================================================================ reference bodies
def ref_bodies(v):
    s = P.KS
    refs = {}
    fr = rrect(R.TB_W / 2, R.TB_H / 2, R.TB_CORNER_R, s["glass"], s["pcb_front"])
    pcb = rrect(R.TB_W / 2 - 0.6, R.TB_H / 2 - 0.6, 5.0, s["pcb_front"], s["pcb_back"])
    offs = [cyl(x, y, 1.6, s["pcb_back"] - EPS, s["standoff_end"]) for (x, y) in
            [(-R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2), (R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2),
             (-R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2), (R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2)]]
    comps = box(-9.0, 9.0, -14.0, 20.0, s["pcb_back"] - EPS, s["pcb_back"] + P.KEY_BOARD_BACK_H)
    refs["touch board"] = fuse([fr, pcb] + offs + [comps])
    ax, ay, al, aw, ah = R.TB_ANT
    refs["antenna chip"] = box(ax - al / 2, ax + al / 2, ay - aw / 2, ay + aw / 2, s["pcb_back"], s["pcb_back"] + ah)
    for i, (x, y) in enumerate(R.MX_SW_POS):
        top = box(x - R.MX_TOP_W / 2, x + R.MX_TOP_W / 2, y - R.MX_TOP_W / 2, y + R.MX_TOP_W / 2, s["mx_top"], s["plate_front"])
        top = top.cut(box(x - R.MX_WINDOW / 2, x + R.MX_WINDOW / 2, y - R.MX_WINDOW / 2, y + R.MX_WINDOW / 2,
                          s["mx_top"] - 1, s["mx_top"] + R.MX_TRAVEL + 0.5))
        body = box(x - R.MX_BODY_BELOW / 2, x + R.MX_BODY_BELOW / 2, y - R.MX_BODY_BELOW / 2, y + R.MX_BODY_BELOW / 2,
                   s["plate_front"], s["mx_bottom"])
        pins = cyl(x, y, 2.0, s["mx_bottom"] - EPS, s["mx_pins"])
        refs[f"MX switch {i+1}"] = fuse([top, body, pins])
        refs[f"MX stem {i+1}"] = box(x - R.MX_STEM_ARM_L / 2, x + R.MX_STEM_ARM_L / 2, y - R.MX_STEM_ARM_W / 2,
                                     y + R.MX_STEM_ARM_W / 2, s["stem_top"], s["mx_top"] - 0.1).fuse(
            box(x - R.MX_STEM_ARM_W / 2, x + R.MX_STEM_ARM_W / 2, y - R.MX_STEM_ARM_L / 2, y + R.MX_STEM_ARM_L / 2,
                s["stem_top"], s["mx_top"] - 0.1))
    x0, x1, y0, y1, md0, md1 = P.mic_carrier_box()
    refs["mic carrier"] = box(x0, x1, y0, y1, md0, md1)
    for i, (x, y) in enumerate(P.LED_POS):
        refs[f"LED {i+1}"] = fuse([box(x - P.LED_W / 2, x + P.LED_W / 2, y - P.LED_W / 2, y + P.LED_W / 2, P.LED_D0, P.LED_D0 + P.LED_T),
                                   box(x - P.LED_W / 2, x + P.LED_W / 2, y - P.LED_W / 2, y + P.LED_W / 2,
                                       P.LED_D0 + P.LED_T - EPS, P.LED_D0 + P.LED_T + P.LED_CARRIER_T)])
    tip, front, back, cback = P.sw_depths()
    for (x, y) in P.SW_POS:
        nm = ("T" if y > 0 else "B") + ("L" if x < 0 else "R")
        body = box(x - P.SW_W / 2, x + P.SW_W / 2, y - P.SW_BODY_Y / 2, y + P.SW_BODY_Y / 2, front, back)
        terms = box(x - P.SW_TERM_W / 2, x + P.SW_TERM_W / 2, y - 2.6, y + 2.6, back - 0.6, back)   # gull-wing SMD leads
        carrier = box(x - P.CARRIER[0] / 2, x + P.CARRIER[0] / 2, y - P.CARRIER[1] / 2, y + P.CARRIER[1] / 2, back, cback)
        ws = P.CARRIER_WIRE_SLOT
        wx, wy = P.wire_slot(x, y)
        joints = box(wx - ws[0] / 2 + 0.3, wx + ws[0] / 2 - 0.3, wy - ws[1] / 2 + 0.3, wy + ws[1] / 2 - 0.3, cback - EPS,
                     cback + P.FLANGE_T + 0.5)                                         # wire joints + wires in the flange slot
        refs[f"switch {nm}"] = fuse([body, terms, carrier, joints])
        refs[f"plunger {nm}"] = cyl(x, y, P.SW_PLUNGER_D / 2, tip, front + EPS)
    for i, (x, y) in enumerate(P.PAD_POS):
        refs[f"preload pad {i+1}"] = box(x - P.PAD_SIZE[0] / 2, x + P.PAD_SIZE[0] / 2, y - P.PAD_SIZE[1] / 2, y + P.PAD_SIZE[1] / 2,
                                         P.PLATE_T, P.DECK_D0 + P.PAD_POCKET)          # drawn compressed (rest)
    gx = P.grille_x()
    g = P.SPK_FACE_GASKET[2]
    m0, m1, n0, n1 = P.mouth()
    pd0, pd1 = P.port_d()
    w = P.DUCT_WALL
    dc, sy = P.SPK_D0 + R.SPK_W / 2, P.SPK_TAB_END
    tab = box(P.SPK_X0 + 0.5, gx - 0.5, min(sy * (P.SPK_Y[1] - EPS), sy * (P.SPK_Y[1] + R.SPK_TAB[1])),
              max(sy * (P.SPK_Y[1] - EPS), sy * (P.SPK_Y[1] + R.SPK_TAB[1])), dc - R.SPK_TAB[0] / 2, dc + R.SPK_TAB[0] / 2)
    refs["speaker 2030"] = fuse([box(P.SPK_X0, gx, P.SPK_Y[0], P.SPK_Y[1], P.SPK_D0, P.SPK_D0 + R.SPK_W), tab])   # v0.9.1 tab
    refs["speaker face gasket"] = box(gx, gx + g, n0 - w, n1 + w, P.SPK_D0, pd1 + w).cut(
        box(gx - 1, gx + g + 1, n0, n1, P.SPK_D0 - 1, pd1))
    h = P.HUB
    refs["hub"] = fuse([box(h[0], h[1], h[2], h[3], h[4], h[4] + P.HUB_PCB_T),
                        box(h[0] + 1.0, h[1] - 1.0, h[2] + 1.0, h[3] - 1.0, h[4] + P.HUB_PCB_T - EPS, h[5])])
    refs["cable loop"] = box(-P.CABLE_W / 2, P.CABLE_W / 2, P.LOOP_Y[0], P.LOOP_Y[1], P.LOOP_D0 + 0.2, P.LOOP_D1)
    for i, (x0, x1, y0, y1) in enumerate(P.WAGO_POS):
        refs[f"WAGO {i+1}"] = box(x0, x1, y0, y1, P.WAGO_D[0], P.WAGO_D[1])
    fb = P.SPK_BACK_FOAM
    refs["speaker back foam"] = box(P.SPK_X0 - fb[1], P.SPK_X0, P.SPK_Y[0] + 2, P.SPK_Y[1] - 2, P.SPK_D0 + 2,
                                    P.SPK_D0 + R.SPK_W - 2)                          # drawn compressed
    fl0 = P.WALL_D - P.FLANGE_T
    lx0, lx1, lhy, lpt = P.LOAD_PLATE
    for sx in (-1, 1):
        cx = sx * P.BOX_SCREW_PITCH / 2
        lab = "L" if sx < 0 else "R"
        refs[f"load plate {lab}"] = box(cx + sx * lx0, cx + sx * lx1, -lhy, lhy, fl0, fl0 + lpt).cut(
            cyl(cx, 0, 1.7, fl0 - 1, fl0 + 1))
        head0 = fl0 - P.SCREW_HEAD_H
        refs[f"box screw {lab}"] = fuse([
            cyl(cx, 0, P.SCREW_HEAD_D / 2, head0, fl0),
            cyl(cx, 0, P.SCREW_D / 2, fl0 - EPS, fl0 + P.SCREW_L)])
    return refs


def env_bodies():
    floor = P.box_floor()
    wallbox = cyl(0, 0, P.BOX_OUTER_D / 2, P.WALL_D, floor + 2.0).cut(cyl(0, 0, P.BOX_USABLE_D / 2, P.WALL_D - 1, floor))
    ds = []
    for d, ang in zip(domes(0.0, P.WALL_D + 0.5, floor), P.BOX_DOME_ANGLES):
        a = math.radians(ang)
        d = d.cut(cyl(round(math.cos(a)) * P.BOX_SCREW_PITCH / 2, round(math.sin(a)) * P.BOX_SCREW_PITCH / 2, 1.7, P.WALL_D, floor + 1))
        ds.append(d.common(cyl(0, 0, P.BOX_OUTER_D / 2, P.WALL_D, floor)))
    boxbody = fuse([wallbox] + ds)
    lim, fo = P.FRAME_OPEN / 2, P.FRAME_OUT / 2
    frame = rrect(fo, fo, 4.0, 0.0, P.FRAME_TUNNEL_D).cut(rrect(lim, lim, 1.0, -1, P.WALL_D))
    frame = frame.fuse(rrect(fo, fo, 4.0, P.FRAME_TUNNEL_D - EPS, P.WALL_D).cut(rrect(fo - 1.5, fo - 1.5, 3.0, 0, P.WALL_D + 1)))
    return {f"box ({P.BOX_DEPTH:.0f} mm)": boxbody, "frame (TBD)": frame.removeSplitter()}


# ============================================================================ motion
KEY_MOVERS = ("key shell", "touch board", "antenna chip", "MX stem 1", "MX stem 2")
PLATE_MOVERS = ("plate", "mic carrier")
_S = P.SUPPORTS      # (x, y, d) hull corners of the lip contacts (see insert_params.SUPPORTS), CCW from bottom-left
PLATE_CASES = {      # press location → pivot line through lip contacts (3D: the catch faces are at different depths)
    "left wing": (_S[1], _S[2], (-21.0, 0.0)),
    "right wing": (_S[7], _S[0], (21.0, 0.0)),
    "top band": (_S[0], _S[1], (0.0, 26.0)),
    "bottom band": (_S[4], _S[5], (0.0, -26.0)),
    "top-left corner": (_S[1], (_S[1][0] + 10.0, _S[1][1] + 10.0, _S[1][2]), (-24.0, 24.0)),
}


def stop_travel():
    """plate travel at the farthest engaged switch at the stop (RSS gap max + bottom-out + seating allowance)."""
    rss, _ = P.gap_tol()
    return P.NUB_GAP + rss + P.SW_TRAVEL_TOTAL + P.SEAT_ALLOW


def key_pressed(shape):
    s = shape.copy()
    s.translate(V(0, 0, -P.KEY_TRAVEL))
    return s


def key_wobbled(shape, axis, deg, travel=0.0):
    """key tilted on its stems by `deg` about the x- or y-axis through the stem tops' mid-point (stem play under an
    eccentric press; KEY_WOBBLE_DEG [TBD]), optionally after `travel` straight down."""
    s = shape.copy()
    s.translate(V(0, 0, -travel))
    ym = (R.MX_SW_POS[0][1] + R.MX_SW_POS[1][1]) / 2
    s.rotate(V(0, ym, -(P.KS["stem_top"] + travel)), V(1, 0, 0) if axis == "x" else V(0, 1, 0), deg)
    return s


def plate_pressed(shape, case, travel=None):
    """tip the plate about the pivot line until the farthest switch has travelled `travel` (default: RSS stop)."""
    travel = stop_travel() if travel is None else travel
    a, b, press = PLATE_CASES[case]
    pa, pb = V(a[0], a[1], -a[2]), V(b[0], b[1], -b[2])
    ax = pb.sub(pa)
    ax.normalize()

    def dist(x, y):                     # in-plane distance from the pivot line (xy projection)
        tx, ty = b[0] - a[0], b[1] - a[1]
        n = math.hypot(tx, ty)
        return abs((x - a[0]) * ty / n - (y - a[1]) * tx / n)
    tx, ty = b[0] - a[0], b[1] - a[1]
    side = lambda x, y: (x - a[0]) * ty - (y - a[1]) * tx   # noqa: E731
    sp = side(*press)
    r = max(dist(x, y) for (x, y) in P.SW_POS if side(x, y) * sp > 0)
    theta = math.degrees(travel / r)
    s = shape.copy()
    for sg in (1, -1):                  # the rotation sense that moves the press point into the wall (−Z)
        t = shape.copy()
        t.rotate(pa, ax, sg * theta)
        probe = Part.Vertex(V(press[0], press[1], 0.0))
        probe.rotate(pa, ax, sg * theta)
        if probe.Point.z < 0:
            s = t
            break
    return s


# ============================================================================ checks
def overlap(a, b):
    if not a.BoundBox.intersect(b.BoundBox):
        return 0.0
    try:
        return a.common(b).Volume
    except Exception:   # noqa: BLE001
        return -1.0


def check_state(bodies, label, exempt=(), only=None):
    names = list(bodies)
    res = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            if only and not (a in only or b in only):
                continue
            if frozenset((a, b)) in exempt:
                continue
            vol = overlap(bodies[a], bodies[b])
            if vol > 0.01 or vol < 0:
                res.append((label, a, b, round(vol, 3)))
    return res


def min_gap(a, b):
    try:
        return a.distToShape(b)[0]
    except Exception:   # noqa: BLE001
        return -1.0


# ============================================================================ export
def rot_to_print(shape, how):
    s = shape.copy()
    if how == "front_down":          # front face (max Z) onto the bed
        s.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    bb = s.BoundBox
    s.translate(V(-bb.Center.x, -bb.Center.y, -bb.ZMin))
    return s


def write_stl(shape, path, lin=0.02, ang=0.25):
    """binary STL, 0.02 mm chordal deviation."""
    import MeshPart
    mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=lin, AngularDeflection=ang, Relative=False)
    mesh.write(path)


def export(shape, name, print_how):
    step = os.path.join(OUT, f"{name}.step")
    stl = os.path.join(OUT, f"{name}_print.stl")
    shape.exportStep(step)
    write_stl(rot_to_print(shape, print_how), stl)
    return step, stl


def export_sections(bodies, v, planes):
    out = {}
    for key, (axis, value) in planes.items():
        sec = {}
        for nm, shp in bodies.items():
            try:
                if axis == "x":
                    wires = shp.slice(V(1, 0, 0), value)
                    conv = lambda p: (p.y, -p.z)     # noqa: E731
                elif axis == "y":
                    wires = shp.slice(V(0, 1, 0), value)
                    conv = lambda p: (p.x, -p.z)     # noqa: E731
                else:
                    wires = shp.slice(V(0, 0, 1), -value)
                    conv = lambda p: (p.x, p.y)      # noqa: E731
            except Exception:   # noqa: BLE001
                wires = []
            loops = []
            for w in wires:
                pts = [conv(p) for p in w.discretize(Deflection=0.02)]
                if len(pts) > 2:
                    loops.append([(round(a, 3), round(b, 3)) for a, b in pts])
            if loops:
                sec[nm] = loops
        out[key] = {"axis": axis, "value": value, "bodies": sec}
    path = os.path.join(SECT, f"insert-{v}_sections.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return path


# ============================================================================ drivers
PRINTED_HOW = {"key_shell": "front_down", "switch_plate": "front_down", "collar": "back_down", "plate": "front_down",
               "chassis": "front_down"}


def build_key_module():
    ks, sp, co = key_shell(), switch_plate(), collar()
    for nm, shp in (("key_shell", ks), ("switch_plate", sp), ("collar", co)):
        assert shp.isValid(), f"{nm} invalid"
        step, stl = export(shp, nm, PRINTED_HOW[nm])
        bb = shp.BoundBox
        print(f"{nm:14s} valid {shp.isValid()} | {bb.XLength:.2f} × {bb.YLength:.2f} × {bb.ZLength:.2f} mm | "
              f"{shp.Volume/1000:.2f} cm³ ≈ {shp.Volume/1000*1.27:.1f} g PETG | {os.path.basename(stl)}")
    return ks, sp, co


def build_variant(v):
    print(f"\n==================== RoomKey insert v{P.VERSION} — Variant {v} ====================")
    pbody, prim = plate_parts(v)
    printed = {"key shell": key_shell(), "switch plate": switch_plate(), "collar": collar(), "plate": fuse([pbody, prim])}
    ch, lost = chassis(v)
    printed["chassis"] = ch
    refs = ref_bodies(v)
    env = env_bodies()
    report = {"variant": v, "version": P.VERSION, "parts": {}, "collisions": [], "gaps": {}, "trimmed_mm3": round(lost, 2),
              "states": {}}
    for nm, shp in printed.items():
        bb = shp.BoundBox
        ok = shp.isValid()
        report["parts"][nm] = dict(valid=ok, solids=len(shp.Solids), volume_cm3=round(shp.Volume / 1000, 2),
                                   size=[round(bb.XLength, 2), round(bb.YLength, 2), round(bb.ZLength, 2)])
        print(f"  {nm:13s} valid {ok} | solids {len(shp.Solids)} | {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} | "
              f"{shp.Volume/1000:.2f} cm³ ≈ {shp.Volume/1000*1.27:.1f} g PETG")
        assert len(shp.Solids) == 1, f"{nm}: {len(shp.Solids)} solids — a cut left a piece loose (v0.9.1 lesson)"
    assert lost <= TRIM_FAIL_MM3, f"allowed-space trim removed {lost:.2f} mm³ of chassis — a feature leaves the frame tunnel/box"
    print(f"  chassis trimmed to the allowed space: {lost:.2f} mm³ (fails above {TRIM_FAIL_MM3})")

    bodies = {}
    bodies.update(printed)
    bodies.update(refs)
    bodies.update(env)
    boxname = [k for k in env if k.startswith("box")][0]
    # exempt only designed contacts: screws in domes, MX bodies in their cut-outs, stems in their sockets, switch
    # plungers in their own switch, the compressible preload pads against the plate
    exempt = {frozenset(("box screw L", boxname)), frozenset(("box screw R", boxname)),
              frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate")),
              frozenset(("MX stem 1", "key shell")), frozenset(("MX stem 2", "key shell")),
              frozenset(("MX stem 1", "MX switch 1")), frozenset(("MX stem 2", "MX switch 2"))}
    exempt |= {frozenset((f"switch {n}", f"plunger {n}")) for n in ("TL", "TR", "BL", "BR")}
    exempt |= {frozenset(("plate", f"preload pad {i+1}")) for i in range(len(P.PAD_POS))}
    col = check_state(bodies, "rest", exempt)
    report["states"]["rest"] = "all pairs"
    kb = dict(bodies)
    for nm in KEY_MOVERS:
        kb[nm] = key_pressed(bodies[nm])
    col += check_state(kb, "key pressed", exempt, only=KEY_MOVERS)
    report["states"]["key pressed"] = f"key + stems + board translated {P.KEY_TRAVEL} (to the stop bosses); base exemptions only"
    report["states"]["key wobble"] = (f"key + stems + board tilted ±{P.KEY_WOBBLE_DEG}° about x and y (through the stem tops' "
                                      f"mid-point), at rest and pressed {P.wobble_travel(P.KEY_WOBBLE_DEG):.2f} (deepest travel before a stop boss lands); base exemptions only "
                                      f"(stems in their housings and sockets) — end presses beyond the stem play: desk rig")
    # wobble: the key AND its stems tilted ±KEY_WOBBLE_DEG (stem play in the housings; pitch about x, roll about y), at
    # rest and pressed. Only the base exemptions apply (stems in their housings and sockets): the stem posts must clear
    # the MX housing windows, the key must clear collar, plate and switch plate.
    wob = P.KEY_WOBBLE_DEG
    kpb = None
    for axis_ in ("x", "y"):
        for sg in (1, -1):
            for trv, lab in ((0.0, "rest"), (P.wobble_travel(P.KEY_WOBBLE_DEG), "pressed")):
                kpx = dict(bodies)
                for nm in KEY_MOVERS:
                    kpx[nm] = key_wobbled(bodies[nm], axis_, sg * wob, trv)
                col += check_state(kpx, f"key wobble {sg * wob:+.1f}° about {axis_} ({lab})", exempt, only=KEY_MOVERS)
                if axis_ == "x" and sg == 1 and lab == "pressed":
                    kpb = kpx
    # v0.9 floating socket: MX2 (housing + stem) off its nominal y by the full float (a pitch error the socket absorbs),
    # at rest and pressed — MX2's post must still clear the housing window, the key the housing top
    float_bodies = {}
    for dy in (R.KEY_SOCKET_FLOAT, -R.KEY_SOCKET_FLOAT):
        for trv, lab in ((0.0, "rest"), (P.KEY_TRAVEL, "pressed")):
            kf = dict(kb) if trv else dict(bodies)
            for nm in ("MX switch 2", "MX stem 2"):
                m = kf[nm].copy()
                m.translate(V(0, dy, 0))
                kf[nm] = m
            col += check_state(kf, f"MX2 off by {dy:+.2f} in y ({lab})", exempt, only=("MX switch 2", "MX stem 2"))
            float_bodies[(dy, lab)] = kf
    # v0.8 key catch: the key pulled towards the room must hit the collar (groove front wall) — also when shifted sideways
    # by its full side play; and it must NOT hit it before the catch play is used up
    pulled = {}
    for dx in (0.0, R.KEY_WELL_CLEAR, -R.KEY_WELL_CLEAR):
        k = bodies["key shell"].copy()
        k.translate(V(dx, 0, P.KEY_CATCH_GAP + 0.15))
        pulled[dx] = overlap(k, bodies["collar"])
    k = bodies["key shell"].copy()
    k.translate(V(0, 0, P.KEY_CATCH_GAP - 0.05))
    free = overlap(k, bodies["collar"])
    ok = all(v > 0.01 for v in pulled.values()) and free < 0.01
    report["states"]["key pulled (catch)"] = (f"v0.8: key pulled {P.KEY_CATCH_GAP + 0.15:.2f} towards the room (centred and "
                                              f"shifted ±{R.KEY_WELL_CLEAR}) → collar hit {', '.join(f'{v:.2f}' for v in pulled.values())} mm³ "
                                              f"(must be > 0); pulled {P.KEY_CATCH_GAP - 0.05:.2f} → {free:.2f} mm³ (must be 0) → "
                                              f"{'CAPTIVE' if ok else 'NOT CAPTIVE'}")
    print("  " + report["states"]["key pulled (catch)"])
    if not ok:
        col.append(("key catch", "fails", 0.0))
    report["states"]["MX2 floating"] = (f"v0.9: MX2 housing + stem shifted ±{R.KEY_SOCKET_FLOAT} in y against the key (the "
                                        f"floating socket's full float), at rest and pressed {P.KEY_TRAVEL}; base exemptions")
    t_stop = stop_travel()
    t_nom = P.NUB_GAP + P.SW_TRAVEL_TOTAL
    report["states"]["plate pressed"] = (f"five press points; nominal stop (travel {t_nom:.2f} at the farthest engaged switch, "
                                         f"all pairs) and RSS worst stop ({t_stop:.2f}; switch bodies exempt: in the real "
                                         f"stack a deeper stop means a deeper switch)")
    pb_all = {}
    for case in PLATE_CASES:
        ex = exempt | {frozenset(("plate", f"plunger {n}")) for n in ("TL", "TR", "BL", "BR")}
        ex |= {frozenset(("mic carrier", f"preload pad {i+1}")) for i in range(len(P.PAD_POS))}
        pbn = dict(bodies)
        for nm in PLATE_MOVERS:
            pbn[nm] = plate_pressed(bodies[nm], case, t_nom)
        col += check_state(pbn, f"plate pressed, nominal stop ({case})", ex, only=PLATE_MOVERS)
        pb = dict(bodies)
        for nm in PLATE_MOVERS:
            pb[nm] = plate_pressed(bodies[nm], case)
        exw = ex | {frozenset(("plate", f"switch {n}")) for n in ("TL", "TR", "BL", "BR")}
        col += check_state(pb, f"plate pressed, RSS stop ({case})", exw, only=PLATE_MOVERS)
        pb_all[case] = pb
    report["collisions"] = col

    def g(a, b, bs=bodies):
        return round(min_gap(bs[a], bs[b]), 3)
    report["gaps"]["key shell ↔ plate (rest)"] = g("key shell", "plate")
    report["gaps"]["key shell ↔ collar (rest, side skirts: roll limit)"] = g("key shell", "collar")
    report["gaps"]["key shell ↔ collar (key pressed)"] = g("key shell", "collar", kb)
    posts = key_posts()
    grow = fuse([cyl(x, y, R.MX_POST_D / 2 + 0.05, P.KS["key_back"] + EPS, P.KS["post_end"] + 1) for (x, y) in R.MX_SW_POS])
    report["gaps"]["stem posts ↔ MX housing 2 window (key pressed)"] = round(min_gap(key_pressed(posts), bodies["MX switch 2"]), 3)
    for dy in (R.KEY_SOCKET_FLOAT, -R.KEY_SOCKET_FLOAT):
        report["gaps"][f"stem post 2 ↔ MX housing 2 window (pressed, MX2 off {dy:+.2f})"] = round(
            min_gap(key_pressed(posts), float_bodies[(dy, "pressed")]["MX switch 2"]), 3)
    report["gaps"]["key back (without posts) ↔ MX housing 2 top (key pressed to its stop bosses)"] = round(
        min_gap(kb["key shell"].cut(key_pressed(grow)), bodies["MX switch 2"]), 3)
    report["gaps"]["stop bosses ↔ switch plate (key pressed; 0 = landed, by design)"] = g("key shell", "switch plate", kb)
    report["gaps"]["key shell ↔ switch plate (key pressed)"] = g("key shell", "switch plate", kb)
    for axis_ in ("x", "y"):
        for trv, lab in ((0.0, "rest"), (P.wobble_travel(P.KEY_WOBBLE_DEG), "pressed")):
            kw = {nm: key_wobbled(bodies[nm], axis_, P.KEY_WOBBLE_DEG, trv) for nm in ("key shell",)}
            kw2 = {nm: key_wobbled(bodies[nm], axis_, -P.KEY_WOBBLE_DEG, trv) for nm in ("key shell",)}
            for other in ("plate", "collar", "MX switch 1", "MX switch 2"):
                gg = min(min_gap(kw["key shell"], bodies[other]), min_gap(kw2["key shell"], bodies[other]))
                report["gaps"][f"key shell ↔ {other} (wobble ±{P.KEY_WOBBLE_DEG}° about {axis_}, {lab})"] = round(gg, 3)
    # the lips on the pivot line stay on their catch faces (0.0 = designed contact); the gap that matters is the rest
    # of the plate (lip regions |y| > 25.3, d > LIP_D0 − 0.1 removed) to the chassis
    no_lips = box(-40, 40, -(P.HALF - P.PLATE_SKIRT_T - P.LIP_IN - 0.3), P.HALF - P.PLATE_SKIRT_T - P.LIP_IN - 0.3, -2, 40).fuse(
        box(-40, 40, -40, 40, -2, P.LIP_D0 - 0.1))
    for case, pb in pb_all.items():
        report["gaps"][f"plate ↔ chassis ({case}; 0 = lip on its catch face, by design)"] = g("plate", "chassis", pb)
        report["gaps"][f"plate without lips ↔ chassis ({case})"] = round(min_gap(pb["plate"].common(no_lips), pb["chassis"]), 3)
        report["gaps"][f"plate ↔ key shell ({case})"] = g("plate", "key shell", pb)
        report["gaps"][f"mic carrier ↔ chassis ({case})"] = g("mic carrier", "chassis", pb)
    report["gaps"]["mic carrier ↔ chassis (rest)"] = g("mic carrier", "chassis")
    report["gaps"]["plate ↔ frame (rest)"] = g("plate", "frame (TBD)")
    for case, pb in pb_all.items():
        report["gaps"][f"plate ↔ frame ({case}, RSS stop)"] = g("plate", "frame (TBD)", pb)
    report["gaps"]["chassis rims ↔ frame (rest, locating clearance)"] = g("chassis", "frame (TBD)")
    report["gaps"]["chassis ↔ box (radial; flange sits on the rim)"] = round(min_gap(ch.common(cyl(0, 0, 40, P.WALL_D + 0.2, 90)),
                                                                                   env[boxname]), 3)
    report["gaps"]["collar ↔ chassis (rest; glued seat, back face on the rear wall = 0 by design)"] = g("collar", "chassis")
    report["gaps"]["speaker ↔ chassis (rest; front edge on the plenum floor = 0 by design)"] = g("speaker 2030", "chassis")
    for m in ("MX switch 2", "LED 3", "LED 4", "speaker 2030", "hub", "box screw L", "switch BL"):
        report["gaps"][f"antenna chip ↔ {m} (rest)"] = g("antenna chip", m)
        report["gaps"][f"antenna chip ↔ {m} (key pressed)"] = round(min_gap(kb["antenna chip"], bodies[m]), 3)
    for case, pb in pb_all.items():                        # nub travel into each plunger in each plate case
        for n in ("TL", "TR", "BL", "BR"):
            ov = pb["plate"].common(bodies[f"plunger {n}"]).Volume
            if ov > 0.001:
                report["gaps"][f"nub pushes plunger {n} ({case}), mm³"] = round(ov, 3)
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    for k, val in report["gaps"].items():
        print(f"    gap {k:60s} {val}")

    export(printed["plate"], f"plate_{v}", PRINTED_HOW["plate"])
    write_stl(rot_to_print(pbody, "front_down").copy(), os.path.join(OUT, f"plate_{v}_body_print.stl"))
    pr = pbody.fuse(prim)
    rim_p = prim.copy()
    rim_p.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    bbp = pr.copy()
    bbp.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    bb = bbp.BoundBox
    rim_p.translate(V(-bb.Center.x, -bb.Center.y, -bb.ZMin))
    write_stl(rim_p, os.path.join(OUT, f"plate_{v}_glowrim_print.stl"))
    export(printed["chassis"], f"chassis_{v}", PRINTED_HOW["chassis"])
    comp = Part.makeCompound([printed[k] for k in printed] + [refs[k] for k in refs])
    comp.exportStep(os.path.join(OUT, f"insert-{v}_assembly.step"))
    Part.makeCompound(list(env.values())).exportStep(os.path.join(OUT, f"insert-{v}_wall-reference.step"))
    write_stl(Part.makeCompound([printed[k] for k in printed]), os.path.join(OUT, f"insert-{v}_printed-assembly.stl"), 0.05, 0.4)
    xs = (P.SNAP_X[0] + P.SNAP_X[1]) / 2
    planes = {"AA_x0": ("x", 0.0), "DD_xsw": ("x", P.SW_POS[1][0]), "EE_xmic": ("x", P.MIC_PORT[0]),
              "BB_y0": ("y", 0.0), "CC_ymic": ("y", P.MIC_PORT[1]), "GG_ysw": ("y", P.SW_POS[2][1]),
              "HH_xsnap": ("x", xs), "KK_ypad": ("y", P.PAD_POS[1][1]), "F_d575": ("d", 5.75),
              "F_d1": ("d", 1.0), "F_d6": ("d", 6.3), "F_d14": ("d", 13.5), "F_d30": ("d", 30.0)}
    bodies_sec = dict(bodies)
    bodies_sec["plate glow rim"] = prim
    export_sections(bodies_sec, v, planes)
    pp = {"plate (left wing pressed)": pb_all["left wing"]["plate"], "plate (top band pressed)": pb_all["top band"]["plate"],
          "plate (bottom band pressed)": pb_all["bottom band"]["plate"],
          "key shell (pressed)": kb["key shell"], "touch board (pressed)": kb["touch board"],
          "key shell (wobble, pressed)": kpb["key shell"], "touch board (wobble, pressed)": kpb["touch board"]}
    export_sections(pp, f"{v}-pressed", {"DD_xsw": ("x", P.SW_POS[1][0]), "AA_x0": ("x", 0.0), "GG_ysw": ("y", P.SW_POS[2][1]),
                                         "HH_xsnap": ("x", xs)})
    # dense slices of the printed parts for tools/insert_wallcheck.py (minimum wall thickness)
    wplanes = {}
    # sampling planes are offset by odd amounts so that none coincides with a design face (degenerate slices)
    for dd in (0.61, 1.53, 2.23, 3.07, 3.83, 4.43, 5.33, 6.31, 7.37, 8.41, 10.03, 12.07, 14.03, 16.07, 17.37, 19.03, 21.07, 23.03, 24.63, 25.43, 26.07, 26.53):
        wplanes[f"d{dd}"] = ("d", dd)
    for xx in (0.03, 4.03, 5.73, 8.07, 10.53, 12.53, 13.07, 14.33, 15.07, 17.03, 19.07, 21.53, 23.07, 25.43, 27.03):
        wplanes[f"x{xx}"] = ("x", xx)
        wplanes[f"x-{xx}"] = ("x", -xx)
    for yy in (0.03, 1.53, 3.73, 5.07, 9.63, 12.93, 13.53, 14.73, 16.07, 19.53, 21.07, 23.03, 24.53, 25.93, 26.83):
        wplanes[f"y{yy}"] = ("y", yy)
        wplanes[f"y-{yy}"] = ("y", -yy)
    for k, (ax_, val) in list(wplanes.items()):           # confirmation twin 0.3 mm away (filters grazing cuts)
        wplanes[k + "+"] = (ax_, val + 0.3)
    export_sections({k: printed[k] for k in printed}, f"{v}-printed", wplanes)
    path = os.path.join(OUT, f"insert-{v}_check.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    print(f"  wrote models/plate_{v} (+ body/glowrim STLs), chassis_{v} (.step + _print.stl), insert-{v}_assembly.step, "
          f"{os.path.basename(path)}")
    return report
