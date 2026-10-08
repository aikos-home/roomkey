#!/usr/bin/env python3
"""RoomKey hub: board outline + part placement (draft A), from the schematic's netlist and the kit CAD.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/gen_layout_hub.py

Coordinates below are the kit CAD's (x right, y up, mm; origin = box centre), taken from hardware/cad (insert_params,
kit v0.10.4 sections). KiCad: X = 100 + x, Y = 100 - y.

The hub sits directly behind the switch plate, front face at d 20.3 (MX housing bottom = plate top 15.3 + 5.0); the two
MX switches plug into Kailh hot-swap sockets on its back. ALL parts are on the back (bottom layer): single-sided
assembly, nothing between the board and the switch plate (only 2.5 mm there). The outline avoids
  - the speaker and its cradle (x >= 14.3 for |y| <= 17.2, d 5.6..25),
  - the radar's view (the kit's antenna window x <= -8.0, y -16.1..2.1; the radar sits behind the hub, d 28+),
  - the box's screw domes (|x| >= 26.0 for |y| <= 4.5),
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

R_BOARD = 28.0                      # box inside Ø58 [TBD Q5] - 1 mm
EDGE_CLR = 0.3                      # courtyard ↔ board edge
GAP = 0.15                          # courtyard ↔ courtyard
CUTOUTS = [                         # (x0, x1, y0, y1) removed from the board
    (14.3, 40, -17.2, 17.2),        # speaker + cradle
    (-40, -8.0, -16.1, 2.1),        # radar antenna window (kit carrier window)
    (26.0, 40, -4.5, 4.5), (-40, -26.0, -4.5, 4.5),   # screw domes
]
SLOT = (-6.4, 6.4, 0.2, 2.8)        # key wire slot = the kit's CABLE_SLOT (12.8 x 2.6 at y 1.5)
KEEPOUT = [                         # back side, no parts
    (-7.0, 7.0, -0.2, 3.2),         # slot surroundings
    (-6.5, 6.5, 5.6, 10.0),         # J4 key-wire holes + room for the soldering iron
]
LOOP_TALL = (-7.5, 7.5, 2.8, 12.6)  # the key wires' rolling loop (behind the hub, d 24-36): no connectors under it

# fixed parts: ref -> (x, y, rotation of the PART as seen from the front, special)
FIXED = {
    "SW1": (0.0, 15.0, 180),        # MX1, pins + socket toward +y (away from the slot); KiCad turns a flipped part
    "SW2": (0.0, -13.0, 0),         # MX2, pins + socket toward -y                  differently: checked on the pads
    "H1": (-13.2, 20.0, 0), "H2": (13.2, 20.0, 0),    # kit hub posts (end at the hub's front face, M2 screw)
    "H3": (10.5, -7.9, 0),          # kit anchor post
}
MIC_PORT = (-20.16, 9.6)            # plate mic hole = the kit's sound tube axis (insert_params MIC_PORT)
J4_AT = (0.0, 7.8)                  # key-wire holes ABOVE the slot: the loop rolls up (+y), its fixed leg
                                    # returns here, next to the parts its signals serve (fewer lines
                                    # through the narrow middle between radar window and speaker)

# movable parts: ref -> (target x, target y, connector opening direction in degrees or None)
TARGETS = {
    # power (upper left); J1 = two solder holes for the 5 V pigtail
    "J1": (-23, 17, None), "D1": (-23, 20, None), "Q1": (-21, 14, None), "D2": (-25, 12, None), "R1": (-24, 10, None),
    "C1": (-18, 17, None), "R17": (-16, 14, None), "U1": (-14, 15, None), "R2": (-12, 13, None),
    "D3": (-10, 11, None), "C2": (-9, 9, None), "C3": (-10, 7, None), "C4": (-8, 10, None), "TP1": (-11, 5, None),
    "D4": (-18, 22, None), "TP3": (-20, 24, None), "D5": (-15, 9, None), "C5": (-13, 7, None), "U2": (-16, 6, None),
    "C6": (-18, 5, None), "TP2": (-20, 4, None),
    # mic (U4 fixed at the port)
    "C9": (-22, 7, None), "R5": (-23, 10, None),
    # next to the key-wire holes J4: IO8 strap, key pull-ups, I2C pull-ups (DNP)
    "R6": (-7, 6, None), "R13": (7, 6, None), "R14": (7, 9, None), "R11": (-7, 9, None), "R12": (-7, 11, None),
    "J10": (8, 3, None),             # bottom-key wire hole (its place in the 2 x 8 field was boxed in)
    "J11": (9, -16, None),           # LED data wire hole, near U7
    # amplifier + speaker (upper right, next to the speaker)
    "U3": (10, 9, None), "R3": (12, 6, None), "Q2": (12, 13, None), "R4": (9, 13, None), "C7": (8, 4, None),
    "C8": (13, 9, None), "J2": (12, 22, None),
    # radar cable: above the window
    "J5": (-13.5, 5.5, None),
    # I/O expander: right of the slot, between amp and the bottom half
    "U6": (11, 0, None), "C11": (13, 4, None), "R9": (9, -3, None), "R10": (12, -4, None), "TP4": (13, -5, None),
    # bottom: plate, SHT tail, glow ring
    "J7": (-4, -23, None), "R7": (-8, -21, None), "R8": (-6, -19, None), "C12": (-9, -18, None),
    "J9": (3, -23, None), "C15": (6, -21, None),
    "J8": (-13, -21, None), "U7": (11, -18, None), "R15": (9, -14, None), "R16": (12, -22, None),
    "C13": (13, -12, None), "C14": (-16, -19, None),
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
    for x in (b[0], b[1]):
        for y in (b[2], b[3]):
            if math.hypot(x, y) > R_BOARD - EDGE_CLR:
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

    # outline: circle minus cutouts, as one polygon on Edge.Cuts (+ the FFC slot as an inner cut-out)
    poly = pcbnew.SHAPE_POLY_SET()
    poly.NewOutline()
    for i in range(360):
        a = math.radians(i)
        poly.Append(kc(R_BOARD * math.cos(a), R_BOARD * math.sin(a)))
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
        placed.append((box_cad(courtyard(fp)), ref))

    for ref, (x, y, rot) in FIXED.items():
        fix(ref, x, y, rot)
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
    placed.append((box_cad(courtyard(j4)), "J4"))
    for pd in j4.Pads():                    # hand-soldered GND wires: solid to the planes (no starved thermals)
        pd.SetLocalZoneConnection(pcbnew.ZONE_CONNECTION_FULL)

    keep = [(k, "keepout") for k in KEEPOUT]
    first = ["J5", "J1", "J2", "J7", "J9", "J8", "U1", "U3", "U6", "U2", "U7", "C2", "Q1", "Q2", "D1", "D3", "D4", "D5"]
    rest = sorted(set(TARGETS) - set(first),
                  key=lambda r: -(lambda b: (b[1] - b[0]) * (b[3] - b[2]))(box_cad(courtyard(fps[r]))))
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
                if ref.startswith("J") and ref not in ("J10", "J11") and overlap(b, LOOP_TALL):
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
    for ref in ("SW1", "SW2", "U4", "J4", "J1", "J2", "J5", "J7", "J8", "J9", "U1", "U3", "U6"):
        x, y = cad(fps[ref].GetPosition())
        print("  %-4s at (%6.2f, %6.2f) rot %3.0f" % (ref, x, y, fps[ref].GetOrientationDegrees()))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
