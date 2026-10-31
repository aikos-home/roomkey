"""RoomKey PLUG-IN HOUSING ("Steckdosen-RoomKey", v0.3, WIP, not certified) — builders, checks, export.

The unchanged RoomKey (kit, either build) in a housing of the 1-gang frame size that plugs into a SCHUKO socket. 230 V
stays inside an unmodified, certified plug-in USB charger (insert_params section 8); nothing of the RoomKey touches 230 V.
G1 shell = practice frame + side walls; G2 box = back plate + charger sleeve + square cup. The insert's flange is clamped
between G1's lengthened frame tunnel and G2's cup rim (no box screws). A TPU grip ring holds the charger in G2's sleeve,
a TPU foot ring rests on the socket face, the corner screws go into heat-set inserts in G1.
v0.3: the charger as measured (2026-10-31); the grip ring flexes; G1 and G2 for both kit builds (use_build): the
self-wired build's key-wire loop reaches further back, so its housing is deeper. The TPU rings fit both.
Coordinates as in insert_lib: (x, y, d), d = depth behind the plate front; the socket face is at DP["socket"].
"""
import json
import math
import os
import sys

import Part

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402
import wiring_lib as WL  # noqa: E402
import wiring_pcb as W  # noqa: E402

L, D, P = K.L, K.D, K.P
V, EPS = L.V, L.EPS
box, cyl, rrect, fuse, cut = L.box, L.cyl, L.rrect, L.fuse, L.cut
OW = P.FRAME_OUT / 2                    # 40.25: outer half width (frame and shell)
IW = OW - P.PLUG_WALL                   # 38.65: shell inner face
RR = P.DESK_FRAME_R                     # 4.0: outer corner radius (as the frame)
VERSION = "0.3"
PETG, TPU = 1.27, 1.21                  # g/cm³
BUILD, DP, TAG = None, None, None


def use_build(build):
    """point every builder below at a kit build (kit_lib.BUILDS): the depths follow its deepest part on the axis."""
    global BUILD, DP, TAG
    BUILD, DP, TAG = build, P.plug_depths(build), f"plug-{build}-v{VERSION}"


use_build("pcb")


def shell():
    """G1: the practice frame (Jung AS 500 look, SHT31-D under its bottom border) + side walls to the back plate + the
    frame tunnel lengthened to PLUG_STOP_D (the flange's front stop; open at the bottom centre for the SHT31-D and its
    wires) + 4 corner bosses with M3 heat-set inserts (pressed in from the back) for the screws through G2. Printed back
    down, supports inside only."""
    fr = D.frame_2x(((0.0, 0.0),), with_rh=True)
    walls = rrect(OW, OW, RR, P.WALL_D - 0.2, DP["back0"]).cut(
        rrect(IW, IW, RR - P.PLUG_WALL, P.WALL_D - 1, DP["back0"] + 1))
    fo, tw = P.FRAME_OPEN / 2, P.DESK_FRAME_T[1]
    ext = rrect(fo + tw, fo + tw, 1.0 + tw, P.FRAME_TUNNEL_D - 0.2, P.PLUG_STOP_D).cut(
        rrect(fo, fo, 1.0, P.FRAME_TUNNEL_D - 1, P.PLUG_STOP_D + 1))
    ext = ext.cut(box(-P.PLUG_STOP_GAP_X, P.PLUG_STOP_GAP_X, -OW, -fo + 2.0, 0, P.PLUG_STOP_D + 1))
    s, _, _, rel, bd, blen = P.PLUG_SCREW
    ins_d, ins_l = P.PLUG_INSERT
    xy = [(sx * s, sy * s) for sx in (-1, 1) for sy in (-1, 1)]
    bosses = [cyl(x, y, bd / 2, DP["back0"] - blen, DP["back0"]) for x, y in xy]
    body = fuse([fr, walls, ext] + bosses)
    holes = [cyl(x, y, ins_d / 2, DP["back0"] - ins_l, DP["back0"] + 1) for x, y in xy]      # the insert's hole
    holes += [cyl(x, y, rel / 2, DP["back0"] - blen - 0.5, DP["back0"]) for x, y in xy]     # room for the screw tip
    return cut(body, holes)


def _bb_xyd(s):
    """bounding box as (x0, x1, y0, y1, d0, d1)."""
    bb = s.BoundBox
    return bb.XMin, bb.XMax, bb.YMin, bb.YMax, -bb.ZMax, -bb.ZMin


def _chamfer_ring(h_top, r_top, h_bot, r_bot, d_top, d_bot):
    """planar 45° skirt under a rounded-square rim (no loft: exact bounding box): the rim's outline at d_top, the cup's
    outer outline at d_bot, built as a stack of thin prisms (0.2 steps ≈ one print layer). Solid: hollow it afterwards."""
    n = max(1, int(round((d_bot - d_top) / 0.2)))
    parts = []
    for i in range(n):
        f = (i + 0.5) / n
        h, r = h_top + (h_bot - h_top) * f, r_top + (r_bot - r_top) * f
        parts.append(rrect(h, h, r, d_top + (d_bot - d_top) * i / n, d_top + (d_bot - d_top) * (i + 1) / n + EPS))
    return fuse(parts)


def seat_r():
    """the grip ring's seat in G2's sleeve: charger + wall gap + tube + standoffs + play."""
    g = P.PLUG_GRIP
    return P.PLUG_CHARGER["d"] / 2 + g["gap"] + g["t"] + g["stand"] + g["play"]


def box_g2(notch=True):
    """G2: back plate (PLUG_FOOT[0] in front of the socket face, a groove for the TPU foot ring; 4 countersunk M3 into
    G1) + charger sleeve (front lip; the TPU grip ring's seat between a front step and the back plate) + square cup from
    the back plate to the flange (its front rim backs the flange, a 45° skirt carries the rim). Printed back down; on a
    two-nozzle printer (X2D) together with the grip ring in TPU (the ring is caught in its seat: no bond needed)."""
    b0, b1, face = DP["back0"], DP["back"], DP["face"]
    cd = P.PLUG_CHARGER["d"]
    play, lip_w, lip_t = P.PLUG_SLEEVE
    rb = cd / 2 + play                                     # the charger's passage (the back plate's hole = the ring's step)
    rs = seat_r()                                          # the grip ring's seat
    ro = rs + P.PLUG_WALL
    ci, cr, crim = P.PLUG_CUP
    co = ci + P.PLUG_WALL
    rim_t = 2.0
    back = rrect(OW, OW, RR, b0, b1)
    cup = fuse([rrect(co, co, cr + P.PLUG_WALL, P.WALL_D, b0 + EPS),
                rrect(crim, crim, cr + (crim - ci), P.WALL_D, P.WALL_D + rim_t),
                _chamfer_ring(crim, cr + (crim - ci), co, cr + P.PLUG_WALL, P.WALL_D + rim_t - EPS,
                              P.WALL_D + rim_t + (crim - co))])
    cup = cup.cut(rrect(ci, ci, cr, P.WALL_D - 1, b0 - EPS))                 # the cup's inside (the insert's room)
    sleeve = cyl(0, 0, ro, face - lip_t, b0 + EPS)
    body = fuse([back, cup, sleeve])
    _, fri, fro, _, fgd = P.PLUG_FOOT
    tools = [cyl(0, 0, rb, face - EPS, b1 + 1),                             # the charger's passage through sleeve + back plate
             cyl(0, 0, rs, face + P.PLUG_GRIP["setback"], b0),              # the grip ring's seat (front step … back plate)
             cyl(0, 0, cd / 2 - lip_w, face - lip_t - 1, face + 0.1),       # the lip's opening (USB plug + wires pass)
             cyl(0, 0, fro, b1 - fgd, b1 + 1).cut(cyl(0, 0, fri, b1 - fgd - 1, b1 + 2))]    # the foot ring's groove
    if BUILD == "pcb" and notch:   # the radar's plug reaches back to d 38.1 right beside the charger's front edge (r 19.7–22.2)
        hx0, hx1, hy0, hy1, _, hd1 = _bb_xyd(L.ref_bodies("S", "pcb")["LD2410C header"])
        tools.append(box(hx0 - 0.5, hx1 + 0.5, hy0 - 0.5, hy1 + 0.5, face - lip_t - 1, hd1 + 0.5))
    s, ho, cs, _, _, _ = P.PLUG_SCREW
    k = (cs - ho) / 2                                                        # 90° countersink in the back face
    for sx in (-1, 1):
        for sy in (-1, 1):
            tools.append(cyl(sx * s, sy * s, ho / 2, b0 - 1, b1 + 1))
            tools.append(Part.makeCone(ho / 2, ho / 2 + k + 0.1, k + 0.1, V(sx * s, sy * s, -b1 + k), V(0, 0, -1)))
    return cut(body, tools)


def _rib(r0, r1, d0, d1, w, lead):
    """an axial rib from r0 (its tip) to r1, w wide, centred on +x; the tip tapers lead outward over 1.5 mm at both ends
    so the charger slides on instead of catching the rib's end."""
    pts = [(r0 + lead, d0), (r0, d0 + 1.5), (r0, d1 - 1.5), (r0 + lead, d1), (r1, d1), (r1, d0), (r0 + lead, d0)]
    face = Part.Face(Part.makePolygon([V(x, -w / 2, -d) for x, d in pts]))
    return face.extrude(V(0, w, 0))


def grip_ring(inter=None, marks=0):
    """TPU 95A flex ring in G2's sleeve, caught between the front step and the back plate (squeezed in through the back
    plate's hole). Its inner ribs press on the charger's thick front part; the outer standoffs, halfway between the ribs,
    carry the tube in the seat, so the tube wall bends outward between them: a soft grip that takes up the charger's and
    the print's tolerance. inter = the ribs' interference (default: the nominal one); marks = notches in its back end
    that tell the coupons apart. Printed standing, back end down."""
    g = P.PLUG_GRIP
    inter = g["inter"] if inter is None else inter
    face, b0 = DP["face"], DP["back0"]
    rc = P.PLUG_CHARGER["d"] / 2
    ri = rc + g["gap"]
    ro = ri + g["t"]
    d0 = face + g["setback"]
    parts = [cyl(0, 0, ro, d0, b0).cut(cyl(0, 0, ri, d0 - 1, b0 + 1))]
    for i in range(g["n"]):
        rib = _rib(rc - inter, ri + 0.2, d0, b0, g["w"], inter + 0.15)
        rib.rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * (i + 0.5) / g["n"])
        stand = box(ro - 0.2, ro + g["stand"], -g["w"] / 2, g["w"] / 2, d0, b0)
        stand.rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * i / g["n"])
        parts += [rib, stand]
    ring = fuse(parts)
    notches = []
    for k in range(marks):                           # at the standoffs from 12 o'clock on, 0.8 deep
        n_ = box(rc - 1.0, ro + g["stand"] + 1.0, -0.6, 0.6, b0 - 0.8, b0 + 1)
        n_.rotate(V(0, 0, 0), V(0, 0, 1), 90.0 + 360.0 * k / g["n"])
        notches.append(n_)
    return cut(ring, notches) if notches else ring


def foot_ring():
    """TPU 95A: flat ring in the back face's groove, just touching the socket face: the housing cannot wobble or
    scratch the socket, and being soft it never holds the charger out of the socket. Printed flat."""
    gap, ri, ro, t, gd = P.PLUG_FOOT
    d0 = DP["back"] - gd
    return cyl(0, 0, ro, d0, d0 + t).cut(cyl(0, 0, ri, d0 - 1, d0 + t + 1))


def charger():
    """revolt PX-8884 as measured: the thick front part (its face on the sleeve lip, the grip ring on it), the thin part
    that goes into the socket recess, the USB-A opening on the front face, contour-plug pins Ø4.8 × 19, 19 apart
    (horizontal, as in a German socket)."""
    c = P.PLUG_CHARGER
    face = DP["face"]
    body = fuse([cyl(0, 0, c["d"] / 2, face, face + c["cap"]),
                 cyl(0, 0, c["d_in"] / 2, face + c["cap"] - EPS, face + c["l"])])
    pw, ph, pdp = c["port"]
    px, py = c["port_c"]
    body = body.cut(box(px - pw / 2, px + pw / 2, py - ph / 2, py + ph / 2, face - 1, face + pdp))
    pd_, pl_, pp_ = c["pin"]
    pins = [cyl(sx * pp_ / 2, 0, pd_ / 2, face + c["l"] - EPS, face + c["l"] + pl_) for sx in (-1, 1)]
    return fuse([body] + pins)


def usb_plug():
    """solder-type USB-A plug in the charger's port: shell (12 deep in the port) + body in front of the charger face."""
    sw, sh, bw, bh, bl = P.PLUG_USB
    px, py = P.PLUG_CHARGER["port_c"]
    face = DP["face"]
    return fuse([box(px - sw / 2, px + sw / 2, py - sh / 2, py + sh / 2, face - EPS, face + 12.0),
                 box(px - bw / 2, px + bw / 2, py - bh / 2, py + bh / 2, face - bl, face)])


def socket_ref():
    """reference Jung AS 500 SCHUKO socket (renders + checks only): its frame (the practice frame shape) and central
    plate with the recess and the two contact holes; the face at DP["socket"], the wall plane at DP["wall"]."""
    fw, rd, cp = P.PLUG_SOCKET
    fr = D.frame_2x(((0.0, 0.0),))
    fr.translate(V(0, 0, -(DP["wall"] - P.WALL_D)))
    plate = rrect(cp / 2, cp / 2, 2.0, DP["socket"], DP["wall"] + 20.0)
    recess = cyl(0, 0, rd / 2, DP["socket"] - 1, DP["socket"] + DP["recess"])
    pp = P.PLUG_CHARGER["pin"][2] / 2
    holes = [cyl(sx * pp, 0, 2.6, DP["socket"], DP["socket"] + DP["recess"] + 21.0) for sx in (-1, 1)]
    return cut(fuse([fr, plate]), [recess] + holes)


def wall_ref():
    """a piece of wall round the socket (renders only): 170 × 170, 10 thick, the flush box opening Ø68."""
    w = box(-85, 85, -85, 85, DP["wall"], DP["wall"] + 10.0)
    return w.cut(cyl(0, 0, P.BOX_OUTER_D / 2, DP["wall"] - 1, DP["wall"] + 11.0))


def supply_route(pin):
    """2 × 0.5 mm² from the USB plug's solder cups (VBUS right, GND left, looking from the room [TBD: the real plug's
    orientation]) up over the plug body, just behind the key wires' U-loop. PCB build: to hub J1, then straight forward
    onto its holes (VBUS takes the upper hole, so the two never cross). Self-wired build: sideways past the plug body to
    the splice points beside the amplifier (WL.targets), then forward onto them; GND one wire deeper, so it passes
    behind the 5 V wire's way down."""
    px, py = P.PLUG_CHARGER["port_c"]
    x0 = px + (3.5 if pin == "5V" else -3.5)
    dz = DP["usb0"] + P.PLUG_WIRE / 2 + 0.3
    yb = py + P.PLUG_USB[3] / 2 + P.PLUG_WIRE / 2 + 0.3
    if BUILD == "pcb":
        jx, jy = W.J1[pin]
        return [(x0, py, DP["usb0"] + 1.5), (x0, yb, dz), (jx + 6.0, jy, dz), (jx, jy, dz), (jx, jy, W.HUB_BACK)]
    tx, ty, td = WL.targets()[f"splice {pin}"]
    if pin == "GND":
        dz += P.PLUG_WIRE + 0.3
    xs = px + P.PLUG_USB[2] / 2 + P.PLUG_WIRE / 2 + 0.7
    return [(x0, py, DP["usb0"] + 1.5), (x0, yb, dz), (xs, yb, dz), (tx, ty, dz), (tx, ty, td)]


def plug_bodies():
    """the kit (BUILD) without the practice box, its frame and the box screws + G1, G2, the TPU rings, charger, USB plug,
    the two supply wires and the reference socket."""
    b = K.kit_bodies(BUILD)
    for k in ("practice box", "frame 1-gang", "box screw L", "box screw R", "load plate L", "load plate R"):
        b.pop(k, None)
    b["G1 shell"] = shell()
    b["G2 box"] = box_g2()
    b["grip ring"] = grip_ring()
    b["foot ring"] = foot_ring()
    b["charger"] = charger()
    b["USB plug"] = usb_plug()
    for pin in ("5V", "GND"):
        b[f"wire {pin}"] = W.wire_solid(supply_route(pin), P.PLUG_WIRE)
    b["socket (ref)"] = socket_ref()
    return b


def _com(bodies):
    """mass (g) and centre-of-mass depth (d) of what hangs on the socket: printed parts by volume (PETG, the two rings
    TPU), electronics by PLUG_MASS_G at their envelope centres. The reference socket and the wires are left out."""
    printed = ("G1 shell", "G2 box", "grip ring", "foot ring", "key shell", "switch plate", "collar", "plate",
               "chassis (kit)", "radar tray", "back carrier")
    m, md, rows = 0.0, 0.0, []
    for nm in printed:
        if nm not in bodies:
            continue
        s = bodies[nm]
        g = s.Volume / 1000 * (TPU if nm in ("grip ring", "foot ring") else PETG)
        d = -s.Solids[0].CenterOfMass.z if len(s.Solids) == 1 else -s.BoundBox.Center.z
        m, md = m + g, md + g * d
        rows.append((nm, round(g, 1), round(d, 1)))
    for nm, g in P.PLUG_MASS_G.items():
        if nm not in bodies:
            continue
        d = -bodies[nm].BoundBox.Center.z
        m, md = m + g, md + g * d
        rows.append((nm, g, round(d, 1)))
    return m, md / m, rows


def build_plug(build="pcb"):
    use_build(build)
    print(f"\n==================== RoomKey PLUG-IN HOUSING {TAG} (WIP) — kit {build} build, insert v{P.VERSION} "
          "====================")
    print("  depths: " + ", ".join(f"{k} {v:.2f}" for k, v in DP.items()))
    bodies = plug_bodies()
    for nm, mat, rho in (("G1 shell", "PETG", PETG), ("G2 box", "PETG", PETG), ("grip ring", "TPU", TPU),
                         ("foot ring", "TPU", TPU)):
        s = bodies[nm]
        bb = s.BoundBox
        print(f"  {nm:9s} valid {s.isValid()} | solids {len(s.Solids)} | {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} | "
              f"{s.Volume / 1000:.1f} cm³ ≈ {s.Volume / 1000 * rho:.0f} g {mat}")
        assert len(s.Solids) == 1, f"{nm} is not ONE solid"
    ex = {frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate")),
          frozenset(("speaker 2030", "speaker back foam")), frozenset(("chassis (kit)", "speaker back foam")),
          frozenset(("charger", "grip ring")),                     # TPU ribs: press fit by design (checked below)
          frozenset(("USB plug", "wire 5V")), frozenset(("USB plug", "wire GND"))}   # soldered to its cups
    if build == "pcb":
        ex |= {frozenset(("hub", "wire 5V")), frozenset(("hub", "wire GND"))} | L.HUB_EXEMPT
        inner = (("USB plug", "radar tray"), ("USB plug", "hub"), ("USB plug", "LD2410C header"), ("charger", "hub"),
                 ("charger", "LD2410C header"), ("wire 5V", "radar tray"), ("wire GND", "LD2410C header"),
                 ("G2 box", "hub"), ("G2 box", "radar tray"), ("G2 box", "LD2410C header"),
                 ("grip ring", "LD2410C header"))
    else:
        ex |= {frozenset(("MAX98357A", "back carrier"))}             # the amp's holes on the carrier pins
        inner = (("USB plug", "back carrier"), ("USB plug", "MAX98357A"), ("charger", "MAX98357A"),
                 ("wire 5V", "MAX98357A"), ("wire GND", "MAX98357A"), ("wire 5V", "back carrier"),
                 ("wire GND", "back carrier"), ("G2 box", "back carrier"), ("G2 box", "MAX98357A"),
                 ("G2 box", "LD2410C header"), ("G2 box", "INMP441"))
    col = L.check_state(bodies, "plug, rest", ex)
    kb = dict(bodies)
    for nm in ("key shell", "touch board", "antenna chip"):
        kb[nm] = L.key_pressed(bodies[nm])
    col += L.check_state(kb, "plug, key pressed", ex, only=("key shell", "touch board", "antenna chip"))
    press = L.overlap(bodies["charger"], bodies["grip ring"])
    pairs = (("USB plug", "cable loop"), ("charger", "cable loop"), ("wire 5V", "wire GND"), ("wire 5V", "cable loop"),
             ("wire GND", "cable loop")) + inner + (
             ("G1 shell", "chassis (kit)"), ("G2 box", "chassis (kit)"), ("G2 box", "speaker 2030"),
             ("G1 shell", "G2 box"), ("G1 shell", "plate"), ("G1 shell", "SHT31-D"), ("G2 box", "socket (ref)"),
             ("charger", "socket (ref)"), ("charger", "G2 box"), ("grip ring", "G2 box"), ("foot ring", "G2 box"),
             ("foot ring", "socket (ref)"), ("foot ring", "charger"))
    gaps = {f"{a} ↔ {b}": round(L.min_gap(bodies[a], bodies[b]), 3) for a, b in pairs}
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    g = P.PLUG_GRIP
    print(f"  charger ↔ grip ring: {press:.1f} mm³ overlap (flex fit, {g['n']} TPU ribs, {g['inter']} into the body)")
    for k, val in gaps.items():
        print(f"    gap {k:34s} {val}")
    m, d_com, rows = _com(bodies)
    lever = DP["socket"] - d_com
    moment = m / 1000 * 9.81 * lever / 1000
    glass = P.KS["glass"]
    dims = {"outline": f"{P.FRAME_OUT} × {P.FRAME_OUT}", "glass → socket face": round(DP["socket"] - glass, 2),
            "glass → back face": round(DP["back"] - glass, 2),
            "frame rim → back face": round(DP["back"] - (P.WALL_D - P.DESK_FRAME_PROFILE[0]), 2),
            "glass → wall (Jung AS 500 socket)": round(DP["wall"] - glass, 2),
            "mass g": round(m), "centre of mass in front of the socket face": round(lever, 1),
            "moment on the socket N·m": round(moment, 3), "moment limit N·m": P.PLUG_MOMENT_MAX}
    for k, val in dims.items():
        print(f"    {k:42s} {val}")
    assert moment <= P.PLUG_MOMENT_MAX, "too heavy / too far out for a socket"
    L.ceilings(bodies["G1 shell"], f"plug-{build}_shell", "back_down", supports=True)
    L.ceilings(bodies["G2 box"], f"plug-{build}_box", "back_down")
    L.export(bodies["G1 shell"], f"plug-{build}_shell", "back_down")
    _export_back_frame(bodies["G2 box"], f"plug-{build}_box")
    Part.makeCompound(list(bodies.values())).exportStep(os.path.join(L.OUT, f"{TAG}_assembly.step"))
    cuts = {pin: math.ceil((WL.length(supply_route(pin)) + WL.RESERVE) / 5.0) * 5 for pin in ("5V", "GND")}
    print(f"  supply wires (cut length incl. {WL.RESERVE:.0f} mm reserve): " + ", ".join(f"{k} {v} mm" for k, v in cuts.items()))
    with open(os.path.join(L.OUT, f"{TAG}_check.json"), "w", encoding="utf-8") as f:
        json.dump({"build": build, "depths": DP, "collisions": col, "gaps": gaps, "press_fit_mm3": round(press, 1),
                   "dims": dims, "mass_rows": rows, "supply_cut_mm": cuts}, f, indent=1, ensure_ascii=False)
    return bodies


def probe_sleeve():
    """coupon: G2's charger sleeve (lip, front step, the grip ring's seat) on a Ø52 disc of its back plate with the foot
    ring's groove — try the three grip rings with the charger before printing G2. The same for both builds."""
    _, lip_w, lip_t = P.PLUG_SLEEVE
    return box_g2(notch=False).common(cyl(0, 0, 26.0, DP["face"] - lip_t - 1, DP["back"] + 1))


def _export_back_frame(shape, name):
    """STEP (model coordinates) + _print.stl in the print frame shared by G2, the probe sleeve and the grip rings: the
    back face (d = DP["back"]) on the bed, x/y as in the model. Loaded together as one object of several parts, a
    grip ring keeps its place in the seat (two-nozzle print); loaded alone, the slicer drops it onto the bed."""
    shape.exportStep(os.path.join(L.OUT, f"{name}.step"))
    s = shape.copy()
    s.translate(V(0, 0, DP["back"]))
    L.write_stl(s, os.path.join(L.OUT, f"{name}_print.stl"))


def export_rings():
    """the parts the same for both builds: the grip ring coupons (1/2/3 notches = PLUG_GRIP coupons) and the probe
    sleeve in G2's print frame, the foot ring."""
    print(f"\n==================== RoomKey PLUG-IN HOUSING v{VERSION}: TPU rings + probe sleeve (both builds) "
          "====================")
    for k, inter in enumerate(P.PLUG_GRIP["coupons"], 1):
        r = grip_ring(inter, k)
        assert len(r.Solids) == 1, f"grip ring {k} is not ONE solid"
        print(f"  grip ring {k}: ribs {inter} into the charger, {k} notch(es) | {r.Volume / 1000:.2f} cm³ ≈ "
              f"{r.Volume / 1000 * TPU:.1f} g TPU")
        L.ceilings(r, f"plug_grip_{k}", "back_down")
        _export_back_frame(r, f"plug_grip_{k}")
    pr = probe_sleeve()
    assert len(pr.Solids) == 1, "probe sleeve is not ONE solid"
    print(f"  probe sleeve: {pr.Volume / 1000:.1f} cm³ ≈ {pr.Volume / 1000 * PETG:.0f} g PETG | gap to grip ring 2 "
          f"{L.min_gap(pr, grip_ring()):.2f}")
    L.ceilings(pr, "plug_probe", "back_down")
    _export_back_frame(pr, "plug_probe")
    f = foot_ring()
    L.ceilings(f, "plug_foot", "back_down")
    L.export(f, "plug_foot", "back_down")
