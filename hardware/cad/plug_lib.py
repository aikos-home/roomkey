"""RoomKey PLUG-IN HOUSING ("Steckdosen-RoomKey", CONCEPT v0.2, WIP, not certified) — builders, checks, export.

The unchanged RoomKey (kit, PCB build) in a housing of the 1-gang frame size that plugs into a SCHUKO socket. 230 V
stays inside an unmodified, certified plug-in USB charger (insert_params section 8); nothing of the RoomKey touches 230 V.
G1 shell = practice frame + side walls; G2 box = back plate + charger sleeve + square cup. The insert's flange is clamped
between G1's lengthened frame tunnel and G2's cup rim (no box screws). v0.2: a TPU grip ring holds the charger in G2's
sleeve, a TPU foot ring rests on the socket face, the corner screws go into heat-set inserts in G1.
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
import wiring_pcb as W  # noqa: E402

L, D, P = K.L, K.D, K.P
V, EPS = L.V, L.EPS
box, cyl, rrect, fuse, cut = L.box, L.cyl, L.rrect, L.fuse, L.cut
DP = P.plug_depths()
OW = P.FRAME_OUT / 2                    # 40.25: outer half width (frame and shell)
IW = OW - P.PLUG_WALL                   # 38.65: shell inner face
RR = P.DESK_FRAME_R                     # 4.0: outer corner radius (as the frame)
TAG = "plug-v0.2"
PETG, TPU = 1.27, 1.21                  # g/cm³


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


def box_g2():
    """G2: back plate (PLUG_FOOT[0] in front of the socket face, a groove for the TPU foot ring; 4 countersunk M3 into
    G1) + charger sleeve (front lip; the TPU grip ring's seat between a front step and the back plate) + square cup from
    the back plate to the flange (its front rim backs the flange, a 45° skirt carries the rim). Printed back down."""
    b0, b1, face = DP["back0"], DP["back"], DP["face"]
    cd = P.PLUG_CHARGER["d"]
    play, lip_w, lip_t = P.PLUG_SLEEVE
    gw, _, _, _, setback = P.PLUG_GRIP
    rb = cd / 2 + play                                     # the charger's passage (the back plate's hole = the ring's step)
    rs = rb + gw                                           # the grip ring's seat
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
    hx0, hx1, hy0, hy1, _, hd1 = _bb_xyd(L.ref_bodies("S", "pcb")["LD2410C header"])
    _, fri, fro, _, fgd = P.PLUG_FOOT
    tools = [cyl(0, 0, rb, face - EPS, b1 + 1),                             # the charger's passage through sleeve + back plate
             cyl(0, 0, rs, face + setback, b0),                             # the grip ring's seat (front step … back plate)
             cyl(0, 0, cd / 2 - lip_w, face - lip_t - 1, face + 0.1),       # the lip's opening (USB plug + wires pass)
             box(hx0 - 0.5, hx1 + 0.5, hy0 - 0.5, hy1 + 0.5, face - lip_t - 1, hd1 + 0.5),   # notch: the radar's plug
             #   reaches back to d 38.1 right beside the charger's front edge (r 19.7–22.2)
             cyl(0, 0, fro, b1 - fgd, b1 + 1).cut(cyl(0, 0, fri, b1 - fgd - 1, b1 + 2))]    # the foot ring's groove
    s, ho, cs, _, _, _ = P.PLUG_SCREW
    k = (cs - ho) / 2                                                        # 90° countersink in the back face
    for sx in (-1, 1):
        for sy in (-1, 1):
            tools.append(cyl(sx * s, sy * s, ho / 2, b0 - 1, b1 + 1))
            tools.append(Part.makeCone(ho / 2, ho / 2 + k + 0.1, k + 0.1, V(sx * s, sy * s, -b1 + k), V(0, 0, -1)))
    return cut(body, tools)


def grip_ring():
    """v0.2, TPU 95A: a thin tube in G2's sleeve, caught between the front step and the back plate (squeezed in through
    the back plate's hole), its axial ribs press on the charger body: holds it by spring force, takes up the charger's
    tolerance. Printed standing."""
    face, b0 = DP["face"], DP["back0"]
    cd = P.PLUG_CHARGER["d"]
    gw, n, w, inter, setback = P.PLUG_GRIP
    ri = cd / 2 + P.PLUG_SLEEVE[0]
    d0 = face + setback
    tube = cyl(0, 0, ri + gw, d0, b0).cut(cyl(0, 0, ri, d0 - 1, b0 + 1))
    ribs = []
    for i in range(n):
        rib = box(cd / 2 - inter, ri + 0.2, -w / 2, w / 2, d0, b0)
        rib.rotate(V(0, 0, 0), V(0, 0, 1), 360.0 * (i + 0.5) / n)
        ribs.append(rib)
    return fuse([tube] + ribs)


def foot_ring():
    """v0.2, TPU 95A: flat ring in the back face's groove, just touching the socket face: the housing cannot wobble or
    scratch the socket, and being soft it never holds the charger out of the socket. Printed flat."""
    gap, ri, ro, t, gd = P.PLUG_FOOT
    d0 = DP["back"] - gd
    return cyl(0, 0, ro, d0, d0 + t).cut(cyl(0, 0, ri, d0 - 1, d0 + t + 1))


def charger():
    """revolt PX-8884 envelope: Ø39 body (front face on the sleeve lip, the rest in the socket recess), USB-A port centred
    on the front face, contour-plug pins Ø4.8 × 19, 19 apart (horizontal, as in a German socket)."""
    c = P.PLUG_CHARGER
    face = DP["face"]
    body = cyl(0, 0, c["d"] / 2, face, face + c["l"])
    pw, ph, pdp = c["port"]
    body = body.cut(box(-pw / 2, pw / 2, -ph / 2, ph / 2, face - 1, face + pdp))
    pd_, pl_, pp_ = c["pin"]
    pins = [cyl(sx * pp_ / 2, 0, pd_ / 2, face + c["l"] - EPS, face + c["l"] + pl_) for sx in (-1, 1)]
    return fuse([body] + pins)


def usb_plug():
    """solder-type USB-A plug in the charger's port: shell (12 deep in the port) + body in front of the charger face."""
    sw, sh, bw, bh, bl = P.PLUG_USB
    face = DP["face"]
    return fuse([box(-sw / 2, sw / 2, -sh / 2, sh / 2, face - EPS, face + 12.0),
                 box(-bw / 2, bw / 2, -bh / 2, bh / 2, face - bl, face)])


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
    orientation]) over the plug body, just behind the key wires' U-loop, to hub J1, then straight forward onto its holes.
    VBUS takes the upper hole, so the two never cross."""
    jx, jy = W.J1[pin]
    x0 = 3.5 if pin == "5V" else -3.5
    dz = DP["usb0"] + P.PLUG_WIRE / 2 + 0.3
    yb = P.PLUG_USB[3] / 2 + P.PLUG_WIRE / 2 + 0.3
    return [(x0, 0.0, DP["usb0"] + 1.5), (x0, yb, dz), (jx + 6.0, jy, dz), (jx, jy, dz), (jx, jy, W.HUB_BACK)]


def plug_bodies():
    """the kit (PCB build) without the practice box, its frame and the box screws + G1, G2, charger, USB plug, the two
    supply wires and the reference socket."""
    b = K.kit_bodies("pcb")
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
               "chassis (kit)", "radar tray")
    m, md, rows = 0.0, 0.0, []
    for nm in printed:
        s = bodies[nm]
        g = s.Volume / 1000 * (TPU if nm in ("grip ring", "foot ring") else PETG)
        d = -s.Solids[0].CenterOfMass.z if len(s.Solids) == 1 else -s.BoundBox.Center.z
        m, md = m + g, md + g * d
        rows.append((nm, round(g, 1), round(d, 1)))
    for nm, g in P.PLUG_MASS_G.items():
        d = -bodies[nm].BoundBox.Center.z
        m, md = m + g, md + g * d
        rows.append((nm, g, round(d, 1)))
    return m, md / m, rows


def build_plug():
    print(f"\n==================== RoomKey PLUG-IN HOUSING {TAG} (concept, WIP) — insert v{P.VERSION} ====================")
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
          frozenset(("USB plug", "wire 5V")), frozenset(("USB plug", "wire GND")),   # soldered to its cups
          frozenset(("hub", "wire 5V")), frozenset(("hub", "wire GND"))} | L.HUB_EXEMPT
    col = L.check_state(bodies, "plug, rest", ex)
    kb = dict(bodies)
    for nm in ("key shell", "touch board", "antenna chip"):
        kb[nm] = L.key_pressed(bodies[nm])
    col += L.check_state(kb, "plug, key pressed", ex, only=("key shell", "touch board", "antenna chip"))
    press = L.overlap(bodies["charger"], bodies["grip ring"])
    pairs = (("USB plug", "cable loop"), ("USB plug", "radar tray"), ("USB plug", "hub"), ("USB plug", "LD2410C header"),
             ("charger", "cable loop"), ("charger", "hub"), ("charger", "LD2410C header"), ("wire 5V", "wire GND"), ("wire 5V", "cable loop"), ("wire GND", "cable loop"),
             ("wire 5V", "radar tray"), ("wire GND", "LD2410C header"),
             ("G1 shell", "chassis (kit)"), ("G2 box", "chassis (kit)"), ("G2 box", "hub"), ("G2 box", "radar tray"),
             ("G2 box", "speaker 2030"), ("G2 box", "LD2410C header"), ("G1 shell", "G2 box"), ("G1 shell", "plate"),
             ("G1 shell", "SHT31-D"), ("G2 box", "socket (ref)"), ("charger", "socket (ref)"), ("charger", "G2 box"),
             ("grip ring", "G2 box"), ("grip ring", "LD2410C header"), ("foot ring", "G2 box"),
             ("foot ring", "socket (ref)"), ("foot ring", "charger"))
    gaps = {f"{a} ↔ {b}": round(L.min_gap(bodies[a], bodies[b]), 3) for a, b in pairs}
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    print(f"  charger ↔ grip ring: {press:.1f} mm³ overlap (press fit, {P.PLUG_GRIP[1]} TPU ribs, "
          f"{P.PLUG_GRIP[3]} into the body)")
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
    L.ceilings(bodies["G1 shell"], "plug_shell", "back_down", supports=True)
    L.ceilings(bodies["G2 box"], "plug_box", "back_down")
    L.ceilings(bodies["grip ring"], "plug_grip", "back_down")
    L.ceilings(bodies["foot ring"], "plug_foot", "back_down")
    L.export(bodies["G1 shell"], "plug_shell", "back_down")
    L.export(bodies["G2 box"], "plug_box", "back_down")
    L.export(bodies["grip ring"], "plug_grip", "back_down")
    L.export(bodies["foot ring"], "plug_foot", "back_down")
    Part.makeCompound(list(bodies.values())).exportStep(os.path.join(L.OUT, f"{TAG}_assembly.step"))
    with open(os.path.join(L.OUT, f"{TAG}_check.json"), "w", encoding="utf-8") as f:
        json.dump({"depths": DP, "collisions": col, "gaps": gaps, "press_fit_mm3": round(press, 1), "dims": dims,
                   "mass_rows": rows}, f, indent=1, ensure_ascii=False)
    return bodies
