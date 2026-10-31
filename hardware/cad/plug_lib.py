"""RoomKey PLUG-IN HOUSING v0.4 ("Steckdosen-RoomKey", WIP, not certified) — builders, checks, export.

RoomKey is built only as this plug-in device (owner 2026-10-31). The kit (either build) in a 64 × 64 housing that plugs
into a SCHUKO socket, 5 mm above the socket centre; 230 V stays inside an unmodified, certified plug-in USB charger
(insert_params section 8); nothing of the RoomKey touches 230 V.
G1 = resin SKIN (front border + 4 side walls; cast by the resin thread, printed for a first fit) + a printed CARRIER glued
into it: the TUNNEL (the insert's locating rims sit in it, its back end stops the insert's flange) and 4 corner COLUMNS
(M3 heat-set inserts). G2 = back lid (inside the skin, flush with its back edge) + charger sleeve + 4 side walls that press
the flange forward; the humidity sensor lies in a window of its bottom wall, behind vents in the skin.
Assembly: tunnel glued into the skin → the insert in from the back → the columns screwed onto G2, glue on their outer
faces → G2 in: the columns find their place and cure there. G2 comes off again for service, the columns stay.
A TPU grip ring holds the charger in G2's sleeve, a TPU foot ring rests on the socket face. The self-wired build's
key-wire loop rolls down onto the USB plug's place, so its housing is deeper (use_build).
Coordinates as in insert_lib: (x, y, d), d = depth behind the plate front; the socket face is at DP["socket"], the
charger's axis (= the socket's centre) at (0, CY).
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

L, P = K.L, K.P
V, EPS = L.V, L.EPS
box, cyl, rrect, fuse, cut = L.box, L.cyl, L.rrect, L.fuse, L.cut
OW = P.PLUG_HALF                        # 32.0: outer half width
RR = P.PLUG_R                           # 4.0: outer corner radius
RI = RR - P.PLUG_SKIN[1]                # 1.8: the skin's inner corner radius
CY = -P.PLUG_OFFSET                     # the charger's axis
VERSION = "0.4"
PETG, TPU, RESIN = 1.27, 1.21, 1.15     # g/cm³ (RESIN [TBD the resin thread's PU / epoxy])
BUILD, DP, TAG = None, None, None


def use_build(build):
    """point every builder below at a kit build (kit_lib.BUILDS): the depths follow its deepest part on the axis."""
    global BUILD, DP, TAG
    BUILD, DP, TAG = build, P.plug_depths(build), f"plug-{build}-v{VERSION}"


use_build("pcb")
skin_in = P.plug_skin_in


def _rr_wire(h, r, d):
    """closed rounded-square wire (half width h, corner radius r) in the plane at depth d."""
    z = -d
    k = math.sqrt(0.5)
    e = [Part.LineSegment(V(-h + r, -h, z), V(h - r, -h, z)).toShape(),
         Part.Arc(V(h - r, -h, z), V(h - r + r * k, -h + r - r * k, z), V(h, -h + r, z)).toShape(),
         Part.LineSegment(V(h, -h + r, z), V(h, h - r, z)).toShape(),
         Part.Arc(V(h, h - r, z), V(h - r + r * k, h - r + r * k, z), V(h - r, h, z)).toShape(),
         Part.LineSegment(V(h - r, h, z), V(-h + r, h, z)).toShape(),
         Part.Arc(V(-h + r, h, z), V(-h + r - r * k, h - r + r * k, z), V(-h, h - r, z)).toShape(),
         Part.LineSegment(V(-h, h - r, z), V(-h, -h + r, z)).toShape(),
         Part.Arc(V(-h, -h + r, z), V(-h + r - r * k, -h + r - r * k, z), V(-h + r, -h, z)).toShape()]
    return Part.Wire(e)


def _drafted(h0, r0, d0, h1, r1, d1):
    """solid between two rounded squares (half width, corner radius) at d0 and d1: a ruled loft — the draft."""
    return Part.makeLoft([_rr_wire(h0, r0, d0), _rr_wire(h1, r1, d1)], True, True)


def _corner(sx, sy, grow, d0, d1):
    """one corner column's zone (P.PLUG_COLUMN: a corner block with a round inner end), grown by `grow`."""
    c, r = P.PLUG_COLUMN
    return fuse([cyl(sx * c, sy * c, r + grow, d0, d1), box(sx * (c - r - grow), sx * 40.0, sy * c, sy * 40.0, d0, d1),
                 box(sx * c, sx * 40.0, sy * (c - r - grow), sy * 40.0, d0, d1)])


CORNERS = ((1, 1), (-1, 1), (-1, -1), (1, -1))


def skin_holes():
    """the vents (2 × 2 round the humidity sensor's chip) and the light window through the skin's bottom wall, each a
    smooth cylinder ⟂ to the wall (the resin thread forms them with silicone pins and fills the window clear)."""
    cx, cd = P.plug_rh()["chip"]
    vd, vp = P.PLUG_VENT
    lx, ld = P.PLUG_LIGHT
    pts = [(cx + i * vp / 2, cd + j * vp / 2, vd) for i in (-1, 1) for j in (-1, 1)] + [(lx, cd, ld)]
    return [Part.makeCylinder(dd / 2, 5.0, V(x, -OW - 1.0, -d), V(0, 1, 0)) for x, d, dd in pts]


def skin():
    """G1 SKIN (resin; PETG for a first fit, printed front down): the front border round the plate (1.0 proud of it, a
    45° edge outside) and the 4 side walls back to the housing's back face. Cast in an open cup + a loose core pulled out
    to the back (resin thread, mould roomkey-form-gehaeuse-v1; one mould for both builds: the PCB skin is the self-wired
    one poured to 47.4): nothing hangs from the border's underside, the inner faces open by the draft towards the back,
    the back edge is the free casting face, no inserts."""
    t, w, a = P.PLUG_SKIN
    f0, f1, b = P.PLUG_FRONT_D, P.PLUG_FRONT_D + t, DP["back"]
    e = P.PLUG_EDGE
    outer = fuse([_drafted(OW - e, RR - e, f0, OW, RR, f0 + e), rrect(OW, OW, RR, f0 + e - EPS, b)])
    core = _drafted(skin_in(f1), RI, f1, skin_in(b + 1.0), RI, b + 1.0)
    fo = P.FRAME_OPEN / 2
    return cut(outer, [core, rrect(fo, fo, P.PLUG_OPEN_R, f0 - 1.0, f1 + 1.0)] + skin_holes())


def tunnel():
    """G1 carrier, part 1 (PETG, printed front down): the frame tunnel, glued into the skin against its front border. The
    insert's locating rims sit in it (0.1), its back end (PLUG_STOP_D) stops the insert's flange."""
    t, w, a = P.PLUG_SKIN
    f1, g, s0 = P.PLUG_FRONT_D + t, P.PLUG_GLUE, P.PLUG_STOP_D
    fo = P.FRAME_OPEN / 2
    ring = _drafted(skin_in(f1) - g, RI - g, f1, skin_in(s0) - g, RI - g, s0)
    return ring.cut(rrect(fo, fo, 1.0, f1 - 1.0, s0 + 1.0))       # R 1.0 as the frame tunnel: the plate's skirts end square


def column(sx=1, sy=1):
    """G1 carrier, part 2 (PETG, 4 ×, printed back down): a corner column from just behind the flange to G2's back plate,
    glued into the skin's inner corner; an M3 heat-set insert pressed in from the back, room for the screw's tip."""
    c = P.PLUG_COLUMN[0]
    g = P.PLUG_GLUE
    d0, d1 = P.WALL_D + 0.1, DP["back0"]
    inside = _drafted(skin_in(d0) - g, RI - g, d0, skin_in(d1) - g, RI - g, d1)
    col = _corner(sx, sy, 0.0, d0, d1).common(inside)
    ins_d, ins_l = P.PLUG_INSERT
    rel = P.PLUG_SCREW[2]
    return cut(col, [cyl(sx * c, sy * c, ins_d / 2, d1 - ins_l, d1 + 1.0),
                     cyl(sx * c, sy * c, rel / 2, d1 - ins_l - 4.0, d1)])


def seat_r():
    """the grip ring's seat in G2's sleeve: charger + wall gap + tube + standoffs + play."""
    g = P.PLUG_GRIP
    return P.PLUG_CHARGER["d"] / 2 + g["gap"] + g["t"] + g["stand"] + g["play"]


def box_g2():
    """G2: back plate (inside the skin, flush with its back edge, PLUG_FOOT[0] in front of the socket face, a groove for the
    TPU foot ring; 4 countersunk M3 into the columns) + charger sleeve round the charger's axis (front lip; the grip
    ring's seat between a front step and the back plate) + 4 side walls from the back plate to the insert's flange, which
    they press forward (corners cut round the columns; in the bottom wall the humidity sensor's window, open to the
    front: the board rests on the wall at its two ends, its parts hang into the window over the skin's vents). Printed
    back down; on a two-nozzle printer (X2D) together with the grip ring in TPU (caught in its seat: no bond needed)."""
    b0, b1, face = DP["back0"], DP["back"], DP["face"]
    hb = skin_in(b0) - P.PLUG_FIT
    back = rrect(hb, hb, RI, b0, b1)
    co = skin_in(P.WALL_D) - P.PLUG_CUP_FIT
    ci = co - P.PLUG_CUP_WALL
    cup = rrect(co, co, RI, P.WALL_D, b0 + EPS).cut(rrect(ci, ci, max(RI - P.PLUG_CUP_WALL, 0.3), P.WALL_D - 1.0, b0 + 1.0))
    g = P.plug_rh()
    ins = g["inset"]
    cup = cut(cup, [_corner(sx, sy, 0.3, P.WALL_D - 1.0, b0 + 1.0) for sx, sy in CORNERS] +
              [box(g["x0"] + ins, g["x1"] - ins, -co - 1.0, -ci + 1.0, P.WALL_D - 1.0, g["d1"] + 0.3)])
    cd = P.PLUG_CHARGER["d"]
    play, lip_w, lip_t = P.PLUG_SLEEVE
    rb = cd / 2 + play                                     # the charger's passage (the back plate's hole = the ring's step)
    rs = seat_r()
    sleeve = cyl(0, CY, rs + P.PLUG_WALL, face - lip_t, b0 + EPS)
    body = fuse([back, cup, sleeve])
    _, fri, fro, _, fgd = P.PLUG_FOOT
    tools = [cyl(0, CY, rb, face - EPS, b1 + 1.0),                         # the charger's passage
             cyl(0, CY, rs, face + P.PLUG_GRIP["setback"], b0),            # the grip ring's seat (front step … back plate)
             cyl(0, CY, cd / 2 - lip_w, face - lip_t - 1.0, face + 0.1),   # the lip's opening (USB plug + wires pass)
             cyl(0, CY, fro, b1 - fgd, b1 + 1.0).cut(cyl(0, CY, fri, b1 - fgd - 1.0, b1 + 2.0))]   # the foot ring's groove
    c = P.PLUG_COLUMN[0]
    ho, cs, _ = P.PLUG_SCREW
    k = (cs - ho) / 2                                                       # 90° countersink in the back face
    for sx, sy in CORNERS:
        tools.append(cyl(sx * c, sy * c, ho / 2, b0 - 1.0, b1 + 1.0))
        tools.append(Part.makeCone(ho / 2, ho / 2 + k + 0.1, k + 0.1, V(sx * c, sy * c, -b1 + k), V(0, 0, -1)))
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
    ring = cut(ring, notches) if notches else ring
    ring.translate(V(0, CY, 0))
    return ring


def foot_ring():
    """TPU 95A: flat ring in the back face's groove round the charger's axis, just touching the socket face: the housing
    cannot wobble or scratch the socket, and being soft it never holds the charger out of the socket. Printed flat."""
    gap, ri, ro, t, gd = P.PLUG_FOOT
    d0 = DP["back"] - gd
    return cyl(0, CY, ro, d0, d0 + t).cut(cyl(0, CY, ri, d0 - 1, d0 + t + 1))


def charger():
    """revolt PX-8884 as measured: the thick front part (its face on the sleeve lip, the grip ring on it), the thin part
    that goes into the socket recess, the USB-A opening on the front face, contour-plug pins Ø4.8 × 19, 19 apart
    (horizontal, as in a German socket)."""
    c = P.PLUG_CHARGER
    face = DP["face"]
    body = fuse([cyl(0, CY, c["d"] / 2, face, face + c["cap"]),
                 cyl(0, CY, c["d_in"] / 2, face + c["cap"] - EPS, face + c["l"])])
    pw, ph, pdp = c["port"]
    px, py = P.plug_port()
    body = body.cut(box(px - pw / 2, px + pw / 2, py - ph / 2, py + ph / 2, face - 1, face + pdp))
    pd_, pl_, pp_ = c["pin"]
    pins = [cyl(sx * pp_ / 2, CY, pd_ / 2, face + c["l"] - EPS, face + c["l"] + pl_) for sx in (-1, 1)]
    return fuse([body] + pins)


def usb_plug():
    """the slim bare USB-A plug in the charger's port: shell (12 deep in the port) + body (solder cups) in front of the
    charger face."""
    sw, sh, bw, bh, bl = P.PLUG_USB
    px, py = P.plug_port()
    face = DP["face"]
    return fuse([box(px - sw / 2, px + sw / 2, py - sh / 2, py + sh / 2, face - EPS, face + 12.0),
                 box(px - bw / 2, px + bw / 2, py - bh / 2, py + bh / 2, face - bl, face)])


def j1_ref():
    """PCB build: hub J1 of rev D — a side-entry JST PH, its mouth towards −x (the lead comes along the lane), and its pins'
    tails on the hub's front (≤ 1.0)."""
    jx, jy, jl, jw, jt, px = P.PLUG_J1
    tails = [box(px - 0.4, px + 0.4, y - 0.4, y + 0.4, P.HUB_PCB_D0 - 1.0, P.HUB_PCB_D0) for y in (-1.5, -3.5)]
    return fuse([box(jx - jl / 2, jx + jl / 2, jy - jw / 2, jy + jw / 2, W.HUB_BACK, W.HUB_BACK + jt)] + tails)


def socket_ref():
    """reference Jung AS 500 SCHUKO socket round the charger's axis (renders + checks only): its frame (80.5, 1 mm behind
    the socket face) and central plate with the recess and the two contact holes; the face at DP["socket"]."""
    fw, rd, cp = P.PLUG_SOCKET
    fr = rrect(40.25, 40.25, 4.0, DP["socket"] + 1.0, DP["wall"], cy=CY).cut(
        rrect(cp / 2 + 0.3, cp / 2 + 0.3, 2.3, DP["socket"], DP["wall"] + 1.0, cy=CY))
    plate = rrect(cp / 2, cp / 2, 2.0, DP["socket"], DP["wall"] + 20.0, cy=CY)
    recess = cyl(0, CY, rd / 2, DP["socket"] - 1, DP["socket"] + DP["recess"])
    pp = P.PLUG_CHARGER["pin"][2] / 2
    holes = [cyl(sx * pp, CY, 2.6, DP["socket"], DP["socket"] + DP["recess"] + 21.0) for sx in (-1, 1)]
    return cut(fuse([fr, plate]), [recess] + holes)


def wall_ref():
    """a piece of wall round the socket (renders only): 170 × 170, 10 thick, the flush box opening Ø68."""
    w = box(-85, 85, CY - 85, CY + 85, DP["wall"], DP["wall"] + 10.0)
    return w.cut(cyl(0, CY, 34.0, DP["wall"] - 1, DP["wall"] + 11.0))


def supply_route(pin):
    """2 × 0.5 mm² from the USB plug's solder cups: PCB build → hub J1 (wiring_pcb), self-wired → the splice points
    beside the amplifier (wiring_lib)."""
    return W.supply_route(pin) if BUILD == "pcb" else WL.supply_route(pin)


def plug_bodies():
    """the kit (BUILD) + G1 (skin, tunnel, columns), G2, the TPU rings, charger, USB plug, the two supply wires, (PCB) J1
    as asked of rev D and the reference socket."""
    b = K.kit_bodies(BUILD)
    b["G1 skin"] = skin()
    b["G1 tunnel"] = tunnel()
    b["G1 columns"] = Part.makeCompound([column(sx, sy) for sx, sy in CORNERS])
    b["G2 box"] = box_g2()
    b["grip ring"] = grip_ring()
    b["foot ring"] = foot_ring()
    b["charger"] = charger()
    b["USB plug"] = usb_plug()
    if BUILD == "pcb":
        b["J1 (rev D)"] = j1_ref()
    for pin in ("5V", "GND"):
        b[f"wire {pin}"] = W.wire_solid(supply_route(pin), P.PLUG_WIRE)
    b["socket (ref)"] = socket_ref()
    return b


def _com(bodies):
    """mass (g) and centre-of-mass depth (d) of what hangs on the socket: printed / cast parts by volume (PETG, the rings
    TPU, the skin resin), electronics by PLUG_MASS_G at their envelope centres. The reference socket and the wires are
    left out."""
    dens = {"G1 skin": RESIN, "grip ring": TPU, "foot ring": TPU}
    printed = ("G1 skin", "G1 tunnel", "G1 columns", "G2 box", "grip ring", "foot ring", "key shell", "switch plate",
               "collar", "plate", "chassis (kit)", "radar cage", "back carrier")
    m, md, rows = 0.0, 0.0, []
    for nm in printed:
        if nm not in bodies:
            continue
        s = bodies[nm]
        g = s.Volume / 1000 * dens.get(nm, PETG)
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
    col1 = column()
    for nm, mat, rho in (("G1 skin", "resin", RESIN), ("G1 tunnel", "PETG", PETG), ("G2 box", "PETG", PETG),
                         ("grip ring", "TPU", TPU), ("foot ring", "TPU", TPU)):
        s = bodies[nm]
        bb = s.BoundBox
        print(f"  {nm:9s} valid {s.isValid()} | solids {len(s.Solids)} | {bb.XLength:.1f} × {bb.YLength:.1f} × {bb.ZLength:.1f} | "
              f"{s.Volume / 1000:.1f} cm³ ≈ {s.Volume / 1000 * rho:.0f} g {mat}")
        assert len(s.Solids) == 1, f"{nm} is not ONE solid"
    assert len(col1.Solids) == 1, "a column is not ONE solid"
    print(f"  G1 column valid {col1.isValid()} | 4 × {col1.Volume / 1000:.2f} cm³ PETG, {col1.BoundBox.ZLength:.1f} long")
    ex = {frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate")),
          frozenset(("speaker 2030", "speaker back foam")), frozenset(("chassis (kit)", "speaker back foam")),
          frozenset(("charger", "grip ring")),                     # TPU ribs: press fit by design (checked below)
          frozenset(("USB plug", "wire 5V")), frozenset(("USB plug", "wire GND"))}   # soldered to its cups
    if build == "pcb":
        ex |= {frozenset(("hub", "wire 5V")), frozenset(("hub", "wire GND")), frozenset(("J1 (rev D)", "wire 5V")),
               frozenset(("J1 (rev D)", "wire GND")), frozenset(("J1 (rev D)", "hub"))} | L.HUB_EXEMPT
        inner = (("USB plug", "hub"), ("USB plug", "J1 (rev D)"), ("charger", "hub"), ("charger", "J1 (rev D)"),
                 ("charger", "LD2410C header"), ("G2 box", "hub"), ("G2 box", "radar cage"), ("grip ring", "hub"),
                 ("G1 columns", "hub"), ("G1 columns", "radar cage"), ("wire 5V", "hub"))
    else:
        ex |= {frozenset(("MAX98357A", "back carrier"))}             # the amp's holes on the carrier pins
        inner = (("USB plug", "back carrier"), ("USB plug", "MAX98357A"), ("charger", "MAX98357A"),
                 ("charger", "LD2410C header"), ("wire 5V", "MAX98357A"), ("wire GND", "MAX98357A"),
                 ("G2 box", "back carrier"), ("G2 box", "LD2410C header"), ("G2 box", "INMP441"),
                 ("G1 columns", "back carrier"))
    col = L.check_state(bodies, "plug, rest", ex)
    kb = dict(bodies)
    for nm in ("key shell", "touch board", "antenna chip"):
        kb[nm] = L.key_pressed(bodies[nm])
    col += L.check_state(kb, "plug, key pressed", ex, only=("key shell", "touch board", "antenna chip"))
    press = L.overlap(bodies["charger"], bodies["grip ring"])
    # G2 goes in from the back with the sensor on it: its path back to the back face must be free
    g = P.plug_rh()
    path = box(g["x0"], g["x1"], g["y0"] - 1.1, g["y1"] + 0.3, g["d0"], DP["back"])
    in_way = {k: round(L.overlap(path, bodies[k]), 2) for k in ("hub", "radar cage", "chassis (kit)", "back carrier",
                                                                "LD2410C", "speaker 2030", "cable loop") if k in bodies}
    in_way = {k: v for k, v in in_way.items() if v > 0.01}
    pairs = (("USB plug", "cable loop"), ("charger", "cable loop"), ("wire 5V", "wire GND"), ("wire 5V", "cable loop"),
             ("wire GND", "cable loop")) + inner + (
             ("G1 tunnel", "chassis (kit)"), ("G1 tunnel", "plate"), ("G1 skin", "plate"), ("G1 skin", "G1 tunnel"),
             ("G1 skin", "G1 columns"), ("G2 box", "G1 columns"), ("G2 box", "G1 skin"), ("G2 box", "chassis (kit)"),
             ("G1 columns", "chassis (kit)"), ("G2 box", "speaker 2030"), ("SHT31-D", "G2 box"), ("SHT31-D", "G1 skin"),
             ("SHT31-D", "chassis (kit)"), ("G2 box", "socket (ref)"), ("G1 skin", "socket (ref)"),
             ("charger", "socket (ref)"), ("charger", "G2 box"), ("grip ring", "G2 box"), ("foot ring", "G2 box"),
             ("foot ring", "socket (ref)"), ("foot ring", "charger"))
    gaps = {f"{a} ↔ {b}": round(L.min_gap(bodies[a], bodies[b]), 3) for a, b in pairs}
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    print(f"  G2's way in (the sensor on it): {'free' if not in_way else 'BLOCKED ' + str(in_way)}")
    gp = P.PLUG_GRIP
    print(f"  charger ↔ grip ring: {press:.1f} mm³ overlap (flex fit, {gp['n']} TPU ribs, {gp['inter']} into the body)")
    for k, val in gaps.items():
        print(f"    gap {k:34s} {val}")
    m, d_com, rows = _com(bodies)
    lever = DP["socket"] - d_com
    moment = m / 1000 * 9.81 * lever / 1000
    glass = P.KS["glass"]
    dims = {"outline": f"{2 * OW:.0f} × {2 * OW:.0f}", "device above the socket centre": P.PLUG_OFFSET,
            "glass → socket face": round(DP["socket"] - glass, 2), "glass → back face": round(DP["back"] - glass, 2),
            "skin front → back face": round(DP["back"] - P.PLUG_FRONT_D, 2),
            "glass → wall (Jung AS 500 socket)": round(DP["wall"] - glass, 2),
            "interior behind the flange (half)": round(P.plug_in_half(), 2),
            "mass g": round(m), "centre of mass in front of the socket face": round(lever, 1),
            "moment on the socket N·m": round(moment, 3), "moment limit N·m": P.PLUG_MOMENT_MAX}
    for k, val in dims.items():
        print(f"    {k:42s} {val}")
    assert moment <= P.PLUG_MOMENT_MAX, "too heavy / too far out for a socket"
    assert not in_way, "G2 cannot go in: the sensor's path is blocked"
    L.ceilings(bodies["G1 skin"], f"plug-{build}_skin", "front_down")
    L.ceilings(bodies["G1 tunnel"], f"plug-{build}_tunnel", "front_down")
    L.ceilings(col1, f"plug-{build}_column", "back_down")
    L.ceilings(bodies["G2 box"], f"plug-{build}_box", "back_down")
    L.export(bodies["G1 skin"], f"plug-{build}_skin", "front_down")
    L.export(bodies["G1 tunnel"], f"plug-{build}_tunnel", "front_down")
    L.export(col1, f"plug-{build}_column", "back_down")
    _export_back_frame(bodies["G2 box"], f"plug-{build}_box")
    Part.makeCompound(list(bodies.values())).exportStep(os.path.join(L.OUT, f"{TAG}_assembly.step"))
    cuts = {pin: math.ceil((WL.length(supply_route(pin)) + WL.RESERVE) / 5.0) * 5 for pin in ("5V", "GND")}
    print(f"  supply wires (cut length incl. {WL.RESERVE:.0f} mm reserve): " + ", ".join(f"{k} {v} mm" for k, v in cuts.items()))
    with open(os.path.join(L.OUT, f"{TAG}_check.json"), "w", encoding="utf-8") as f:
        json.dump({"build": build, "depths": DP, "collisions": col, "gaps": gaps, "press_fit_mm3": round(press, 1),
                   "g2_way_in": in_way, "dims": dims, "mass_rows": rows, "supply_cut_mm": cuts}, f, indent=1,
                  ensure_ascii=False)
    return bodies


def probe_sleeve():
    """coupon: G2's charger sleeve (lip, front step, the grip ring's seat) on a Ø52 disc of its back plate with the foot
    ring's groove — try the three grip rings with the charger before printing G2. The same for both builds."""
    _, lip_w, lip_t = P.PLUG_SLEEVE
    return box_g2().common(cyl(0, CY, 26.0, DP["face"] - lip_t - 1, DP["back"] + 1))


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
