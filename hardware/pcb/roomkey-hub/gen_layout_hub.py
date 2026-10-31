#!/usr/bin/env python3
"""RoomKey hub: board outline + part placement (draft A), from the schematic's netlist and the kit CAD.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/gen_layout_hub.py

Coordinates below are the kit CAD's (x right, y up, mm; origin = box centre), taken from hardware/cad (insert_params,
kit v0.10.4 sections). KiCad: X = 100 + x, Y = 100 - y.

The hub sits directly behind the switch plate, front face at d 20.3 (MX housing bottom = plate top 15.3 + 5.0); the two
MX switches plug into Kailh hot-swap sockets on its back. ALL parts are on the back (bottom layer): single-sided
assembly, nothing between the board and the switch plate (only 2.5 mm there). Rev D (plug-in housing v0.4, 64 x 64,
CAD thread 2026-10-31): the outline is a square of +-28.0 (0.45 to the lid's side walls) that avoids
  - the housing's corner columns: a circle r 3.9 round (+-26.8, +-26.8) and everything beyond it toward the corner,
  - the speaker and its cradle (x >= 14.3 for |y| <= 17.2, d 5.6..25),
  - the radar, which now sits IN the hub plane, in a printed cage: a window open to the left edge, x <= -7.86,
    y -18.4..6.2 (the cage + 0.3),
  - a notch at the bottom edge (x -4.3..9.84, up to y -25.87) that the humidity sensor and its lead pass,
and has a slot for the FFC between the switches (y 1.5, as the kit's cable slot). Placement is target + greedy
legalisation on courtyards; the script prints what it could not place. 4 layers: F.Cu signals,
In1 GND plane, In2 +5V plane, B.Cu parts + signals.
"""
import math
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD = r"C:/Program Files/KiCad/10.0"
FP_DIR = KICAD + "/share/kicad/footprints/"
PCB = os.path.join(HERE, "hub", "roomkey-hub.kicad_pcb")
SCH = os.path.join(HERE, "hub", "roomkey-hub.kicad_sch")

BOARD_HALF = 28.0                   # square outline (rev D): the lid G2's side walls at 28.45
CORNER = (26.8, 3.9)                # the housing's corner columns: centre |x| = |y|, free radius (column r 3.2 + 0.5 air,
                                    # + 0.2 for the router's tolerance; CAD thread 2026-10-31)
EDGE_CLR = 0.3                      # courtyard ↔ board edge
GAP = 0.15                          # courtyard ↔ courtyard
CUTOUTS = [                         # (x0, x1, y0, y1) removed from the board
    (14.3, 40, -17.2, 17.2),        # speaker + cradle
    (-40, -7.86, -18.4, 6.2),       # radar window: the LD2410C (x -24.0..-8.16, y -17.1..4.93) sits in it, antenna face
                                    # flush with the board's front, in a printed cage (insert_params HUB_RADAR_WINDOW)
    (-4.3, 9.84, -40, -25.87),      # bottom notch: the humidity sensor in the lid G2 passes it when G2 slides in, and
                                    # its 4-wire lead to J9 runs through it
]
SLOT = (-6.4, 6.4, 0.2, 2.8)        # key wire slot = the kit's CABLE_SLOT (12.8 x 2.6 at y 1.5)
KEEPOUT = [                         # back side, no parts
    (-7.0, 7.0, -0.2, 3.2),         # slot surroundings
    (-6.4, 6.4, 4.2, 8.5),          # J4 key-wire holes + room for the soldering iron
    (-4.5, 6.5, -6.0, -0.5),        # J1's lane: the 5 V lead comes from the USB plug's solder cups (x -3.3 / 3.7,
                                    # y -5.35) straight forward, then runs at d ~24.8 into J1's mouth at x 6.5
]
LOOP_TALL = (-7.5, 7.5, 2.8, 12.6)  # the key wires' rolling loop (behind the hub, d 24-36): no connectors under it
MX_HOUSING = 14.0                    # MX switch housing (square, on the FRONT face): no through-hole joints under it
USB_PLUG = (-6.8, 7.2, -8.65, -2.05)  # plug-in housing v0.4: the slim USB-A plug in the charger (d 28-31) behind the hub:
                                     # no connectors (their mating plugs) under it; J1 is fixed beside it

# fixed parts: ref -> (x, y, rotation of the PART as seen from the front, special)
FIXED = {
    "SW1": (0.0, 15.0, 180),        # MX1, pins + socket toward +y (away from the slot); KiCad turns a flipped part
    "SW2": (0.0, -13.0, 0),         # MX2, pins + socket toward -y                  differently: checked on the pads
    "H1": (-13.2, 20.0, 0), "H2": (13.2, 20.0, 0),    # kit hub posts (end at the hub's front face, M2 screw)
    "H3": (10.5, -7.9, 0),          # kit anchor post (M2 screw: its head sits on the back, up to y -5.9)
    "J1": (12.75, -3.5, 90),        # 5 V in, JST PH SIDE entry (rev D, CAD thread 2026-10-31): pin 1 (GND) here, pin 2
                                    # (+5 V) above it at y -1.5; body x 6.5..14.1 (7.6 deep), y -5.45..0.45: 0.45 above
                                    # H3's screw head, 0.5 left of the speaker foam (x 14.6); mouth at x 6.5 toward
                                    # the axis, where the lead comes from the USB plug through J1's lane (KEEPOUT)
    "J5": (-13.5, 10.5, 90),        # radar plug: body y 7..14; wires to the radar's pins (cut to 2 mm, x -22.7)
    "J2": (11.5, 12.5, 90),         # speaker plug, at its rev C place: the CAD's speaker lead is routed to it
    "J8": (15.3, -20.5, 0),         # glow LED solder holes (centre): the wires come from the BR LED (12.5, -22.47)
                                    # through the switch-plate notch into the gap in FRONT of the hub (CAD thread
                                    # 2026-10-09). x 15.3 = fully outside the collar seat wall / switch-plate ledge
                                    # (x 13.5..14.88, d 16.8..17.8), so the wires enter straight
}
CENTRED = {"J8"}                    # FIXED parts whose (x, y) is the centre of their pads, not the footprint origin
MIC_PORT = (-20.16, 9.6)            # plate mic hole = the kit's sound tube axis (insert_params MIC_PORT)
J4_AT = (0.0, 6.35)                 # CENTRE of the key-wire holes, ABOVE the slot: the loop rolls up (+y), its
                                    # fixed leg returns here. Both rows stay clear of MX1's 14 x 14 housing
                                    # (y >= 8.0), which sits flat on the front face over solder fillets otherwise

# movable parts: ref -> (target x, target y, connector opening direction in degrees or None)
TARGETS = {
    # power in: the protection chain (TVS, reverse FET, eFuse) below J1's lane, between it and MX2's socket; VIN_RAW
    # from J1 crosses under the lane. Behind the eFuse, +5V is the In2 plane.
    "D1": (-2, -8, None), "Q1": (1, -8.5, None), "D2": (-5, -8, None), "R1": (2.5, -10, None),
    "C1": (5.5, -7, None), "R17": (3, -10.2, None), "U1": (4.5, -8.5, None), "R2": (6.5, -9.5, None),
    # +5V side (upper left, as before; rev D: the radar window reaches up to y 6.2, so the LDO group moves out to the
    # left edge, where the square outline has room)
    "D3": (-10, 11, None), "C2": (-9, 9, None), "C3": (-8.5, 7, None), "C4": (-8, 10, None), "TP1": (-12, 16, None),
    "D4": (-9, 14, None), "TP3": (-9, 17, None), "D5": (-17, 9, None), "C5": (-21.3, 15, None), "U2": (-24.5, 15, None),
    "C6": (-25, 11.5, None), "TP2": (-26, 19, None),
    # mic (U4 fixed at the port)
    "C9": (-17.8, 9.5, None), "R5": (-23, 10, None),
    # next to the key-wire holes J4: IO8 strap, key pull-ups, I2C pull-ups (DNP)
    "R6": (-7, 6, None), "R13": (7, 6, None), "R14": (-6, -3, None), "R11": (-8, 4, None), "R12": (-8, 5.5, None),
    # amplifier + speaker (right, between the slot and the speaker plug; the expander's old place below it is free)
    "U3": (10, 3, None), "C7": (12.5, 8, None),
    "R3": (7.12, 4.4, None),         # beside U3's SD_MODE pin (left): on the right its track walled in the speaker pins
    "C8": (10.3, 6.3, None),         # over U3's VDD pins; not further right: SPK_P/N run straight up from U3's right side
                                     # to J2 (x 11.4..13)
    # bottom: SHT tail, glow ring (LED buffer right of the slot, where the data wire comes down)
    "J9": (-10, -22.5, None), "C15": (-7, -20.5, None),
    "U7": (11, -16, None), "R15": (8, -14, None), "R16": (12, -19, None),
    "C13": (13, -13, None), "C14": (11, -21, None),
}


def kc(x, y):
    return pcbnew.VECTOR2I_MM(100 + x, 100 - y)


def cad(v):
    return pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y)


# ── netlist ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def netlist():
    out = os.path.join(os.environ.get("TEMP", HERE), "roomkey-hub.net")
    subprocess.run([KICAD + "/bin/kicad-cli.exe", "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, SCH],
                   check=True, capture_output=True)
    sys.path.insert(0, HERE)
    import gen_schematics as G
    root = G.parse(open(out, encoding="utf-8").read())[0]
    comps = {}
    for c in G.kids(G.kid(root, "components"), "comp"):
        ref = str(G.kid(c, "ref")[1])
        props = {str(p[1][1]) for p in G.kids(c, "property")}
        fields = {str(f[1][1]): (str(f[2]) if len(f) > 2 else "") for f in G.kids(G.kid(c, "fields"), "field")}
        comps[ref] = dict(value=str(G.kid(c, "value")[1]), fp=str(G.kid(c, "footprint")[1]), fields=fields,
                          uuid=str(G.kid(c, "tstamps")[1]), dnp="dnp" in props,
                          nobom="exclude_from_bom" in props)
    pads = {}
    for n in G.kids(G.kid(root, "nets"), "net"):
        name = str(G.kid(n, "name")[1])
        for node in G.kids(n, "node"):
            pads[(str(G.kid(node, "ref")[1]), str(G.kid(node, "pin")[1]))] = name
    return comps, pads


def load_fp(fpid):
    nick, name = fpid.split(":")
    path = os.path.join(HERE, "lib", "roomkey.pretty") if nick == "roomkey" else FP_DIR + nick + ".pretty"
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit("footprint not found: " + fpid)
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    return fp


# ── geometry helpers (CAD coordinates) ───────────────────────────────────────────────────────────────────────────────
def courtyard(fp):
    try:
        bb = fp.GetCourtyard(pcbnew.B_CrtYd).BBox()
        if bb.GetWidth() > 0:
            return bb
    except Exception:
        pass
    return fp.GetBoundingBox(False)


def box_cad(bb):
    x0, y1 = cad(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop()))
    x1, y0 = cad(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
    return (x0, x1, y0, y1)


def overlap(a, b, gap=0.0):
    return a[0] < b[1] + gap and b[0] < a[1] + gap and a[2] < b[3] + gap and b[2] < a[3] + gap


def inside_board(b):
    lim = BOARD_HALF - EDGE_CLR
    if b[0] < -lim or b[1] > lim or b[2] < -lim or b[3] > lim:
        return False
    for sx in (-1, 1):                      # corner columns: the box's nearest point stays outside the free circle
        for sy in (-1, 1):
            cx, cy = sx * CORNER[0], sy * CORNER[0]
            px, py = min(max(cx, b[0]), b[1]), min(max(cy, b[2]), b[3])
            if math.hypot(px - cx, py - cy) < CORNER[1] + EDGE_CLR:
                return False
    for c in CUTOUTS + [SLOT]:
        if overlap(b, c, EDGE_CLR):
            return False
    return True


def put(fp, x, y, rot):
    """bottom side: flip, then turn; rot = angle as seen from the FRONT (CAD view through the board)."""
    fp.SetPosition(kc(x, y))
    if not fp.IsFlipped():
        fp.Flip(kc(x, y), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetOrientationDegrees(rot)


def opening_dir(fp):
    """direction (deg, CAD) from the signal pads toward the courtyard centre = a horizontal connector's mouth."""
    sig = [p for p in fp.Pads() if p.GetNumber() not in ("", "MP")]
    sx = sum(cad(p.GetPosition())[0] for p in sig) / len(sig)
    sy = sum(cad(p.GetPosition())[1] for p in sig) / len(sig)
    b = box_cad(courtyard(fp))
    return math.degrees(math.atan2((b[2] + b[3]) / 2 - sy, (b[0] + b[1]) / 2 - sx)) % 360


def main():
    comps, padnets = netlist()
    board = pcbnew.NewBoard(PCB)      # fresh each run: this script owns the placement until routing starts
    board.SetCopperLayerCount(4)          # In1 = GND plane, In2 = +5V plane (route_hub.py pours them)
    board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    board.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
    try:
        board.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.6))
    except AttributeError:
        pass

    # outline: square minus the corner columns and the cutouts, as one polygon on Edge.Cuts (+ the FFC slot as an inner
    # cut-out)
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for x, y in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        poly.Append(kc(x * BOARD_HALF, y * BOARD_HALF))
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx, cy = sx * CORNER[0], sy * CORNER[0]
            r = CORNER[1] / math.cos(math.pi / 90)          # 90-gon round the circle: the polygon's edges stay outside it
            c = pcbnew.SHAPE_POLY_SET()
            c.NewOutline()
            for i in range(90):
                a = 2 * math.pi * i / 90
                c.Append(kc(cx + r * math.cos(a), cy + r * math.sin(a)))
            poly.BooleanSubtract(c)
    for x0, x1, y0, y1 in CUTOUTS:
        r = pcbnew.SHAPE_POLY_SET()
        r.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            r.Append(kc(x, y))
        poly.BooleanSubtract(r)
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_POLY)
    edge.SetPolyShape(poly)
    edge.SetFilled(False)
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(pcbnew.FromMM(0.1))
    board.Add(edge)
    slot = pcbnew.PCB_SHAPE(board)
    slot.SetShape(pcbnew.SHAPE_T_RECT)
    slot.SetStart(kc(SLOT[0], SLOT[3]))
    slot.SetEnd(kc(SLOT[1], SLOT[2]))
    slot.SetLayer(pcbnew.Edge_Cuts)
    slot.SetWidth(pcbnew.FromMM(0.1))
    board.Add(slot)

    nets = {}
    for name in sorted(set(padnets.values())):
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n

    placed = []      # (box, ref)
    fps = {}
    for ref, c in comps.items():
        fp = load_fp(c["fp"])
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        fp.SetPath(pcbnew.KIID_PATH("/" + c["uuid"]))
        for p in fp.Pads():
            net = padnets.get((ref, p.GetNumber()))
            if net:
                p.SetNet(nets[net])
        for k, v in c["fields"].items():
            if k != "Footprint":
                fp.SetField(k, v)
                f = fp.GetField(k)
                if f is not None and k not in ("Reference", "Value"):
                    f.SetVisible(False)     # MPN, maker, notes: data only, never on the silkscreen
        fp.Reference().SetVisible(False)        # dense board: references on the fab layer only (PCBWay places by file)
        if c["dnp"]:
            fp.SetDNP(True)
        if c["nobom"]:
            fp.SetExcludedFromBOM(True)
        board.Add(fp)
        fps[ref] = fp

    missing = set(fps) - set(FIXED) - set(TARGETS) - {"U4", "J4"}
    if missing:
        raise SystemExit("no position for: %s" % sorted(missing))

    def fix(ref, x, y, rot):
        fp = fps[ref]
        put(fp, x, y, rot)
        if ref in CENTRED:                  # move the pad field's centre (not pin 1) onto (x, y)
            px = [cad(p.GetPosition()) for p in fp.Pads()]
            cx = (min(a for a, _ in px) + max(a for a, _ in px)) / 2
            cy = (min(b for _, b in px) + max(b for _, b in px)) / 2
            put(fp, 2 * x - cx, 2 * y - cy, rot)
        placed.append((box_cad(courtyard(fp)), ref))

    for ref, (x, y, rot) in FIXED.items():
        fix(ref, x, y, rot)
    j1 = {p.GetNumber(): cad(p.GetPosition()) for p in fps["J1"].Pads()}
    assert j1["2"][1] > j1["1"][1] and box_cad(courtyard(fps["J1"]))[0] < j1["1"][0] - 5, \
        "J1: pin 2 (+5 V) must sit above pin 1, the mouth toward -x (CAD thread 2026-10-31)"
    for pd in fps["J8"].Pads():             # hand-soldered LED wires: solid to the planes, like J4
        pd.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)
    # mic: its port hole (the footprint's NPTH) onto the sound tube axis
    mic = fps["U4"]
    put(mic, *MIC_PORT, 0)
    hole = next(p for p in mic.Pads() if p.GetNumber() == "")
    hx, hy = cad(hole.GetPosition())
    put(mic, 2 * MIC_PORT[0] - hx, 2 * MIC_PORT[1] - hy, 0)
    placed.append((box_cad(courtyard(mic)), "U4"))
    # J4: 2 x 8 solder holes for the key wires, long side along x, under the slot (the wire loop returns here)
    j4 = fps["J4"]
    for rot in (0, 90):
        put(j4, *J4_AT, rot)
        b = box_cad(courtyard(j4))
        if b[1] - b[0] > b[3] - b[2]:
            break
    px = [cad(p.GetPosition()) for p in j4.Pads()]          # the footprint origin is pin 1: centre the hole field
    cx = (min(x for x, _ in px) + max(x for x, _ in px)) / 2
    cy = (min(y for _, y in px) + max(y for _, y in px)) / 2
    put(j4, 2 * J4_AT[0] - cx, 2 * J4_AT[1] - cy, rot)
    placed.append((box_cad(courtyard(j4)), "J4"))
    for pd in j4.Pads():                    # hand-soldered GND wires: solid to the planes (no starved thermals)
        pd.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    keep = [(k, "keepout") for k in KEEPOUT]
    first = ["J9", "U1", "U3", "U2", "U7", "C13", "C2", "Q1", "D1", "D3", "D4", "D5"]   # C13 = U7's decoupling
    rest = sorted(set(TARGETS) - set(first),       # big parts first; the name breaks ties (a set's order is random)
                  key=lambda r: (-(lambda b: (b[1] - b[0]) * (b[3] - b[2]))(box_cad(courtyard(fps[r]))), r))
    order = first + rest
    cand = sorted(((dx * 0.25, dy * 0.25) for dx in range(-100, 101) for dy in range(-100, 101)),
                  key=lambda v: v[0] ** 2 + v[1] ** 2)
    failed = []
    for ref in order:
        tx, ty, want = TARGETS[ref]
        fp = fps[ref]
        rots = [0, 90, 180, 270] if want is None else []
        if want is not None:
            for rot in (0, 90, 180, 270):
                put(fp, tx, ty, rot)
                if abs((opening_dir(fp) - want + 180) % 360 - 180) < 30:
                    rots = [rot]
                    break
        shapes = {}
        for rot in rots[:2] if want is None else rots:
            put(fp, 0, 0, rot)
            shapes[rot] = box_cad(courtyard(fp))
        done = False
        for dx, dy in cand:
            for rot, b0 in shapes.items():
                b = (b0[0] + tx + dx, b0[1] + tx + dx, b0[2] + ty + dy, b0[3] + ty + dy)
                if not inside_board(b):
                    continue
                if any(overlap(b, p, GAP) for p, _ in placed + keep):
                    continue
                if ref.startswith("J") and ref not in ("J10", "J11") and (overlap(b, LOOP_TALL) or overlap(b, USB_PLUG)):
                    continue
                put(fp, tx + dx, ty + dy, rot)
                placed.append((box_cad(courtyard(fp)), ref))
                done = True
                break
            if done:
                break
        if not done:
            failed.append(ref)
            put(fp, 0, -40, 0)
    pcbnew.SaveBoard(PCB, board)
    used = sum((b[1] - b[0]) * (b[3] - b[2]) for b, _ in placed)
    print("placed %d parts, courtyards %.0f mm2; not placed: %s" % (len(placed), used, failed or "none"))
    for ref in ("SW1", "SW2", "U4", "J4", "J1", "J2", "J5", "J8", "J9", "U1", "U3", "D4"):
        x, y = cad(fps[ref].GetPosition())
        print("  %-4s at (%6.2f, %6.2f) rot %3.0f" % (ref, x, y, fps[ref].GetOrientationDegrees()))
    # the MX housings sit flat on the FRONT face: no through-hole solder joint (pin tail, fillet) may lie under them
    under_mx = []
    for ref, fp in fps.items():
        if ref in ("SW1", "SW2"):
            continue
        for pd in fp.Pads():
            if pd.GetAttribute() != pcbnew.PAD_ATTRIB_PTH:
                continue
            x, y = cad(pd.GetPosition())
            sz = pd.GetSize(pcbnew.B_Cu)
            hx, hy = pcbnew.ToMM(sz.x) / 2, pcbnew.ToMM(sz.y) / 2
            for sw in ("SW1", "SW2"):
                mx, my = cad(fps[sw].GetPosition())
                if abs(x - mx) < MX_HOUSING / 2 + hx and abs(y - my) < MX_HOUSING / 2 + hy:
                    under_mx.append("%s.%s under %s" % (ref, pd.GetNumber(), sw))
    if under_mx:
        print("THROUGH-HOLE PADS UNDER AN MX HOUSING: %s" % under_mx)
    return 1 if failed or under_mx else 0


if __name__ == "__main__":
    sys.exit(main())
