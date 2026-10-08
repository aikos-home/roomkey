#!/usr/bin/env python3
"""RoomKey hub: put a single solder hole (from the schematic) onto an already routed track of its net.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/add_wire_hole.py J11

For key wires whose place in the 2 x 8 field J4 could not be routed: the schematic gives the hole its own symbol and
leaves the J4 pin unconnected; this script places the hole where its net's copper already runs (no new routing), takes
nets, fields and the schematic link from the netlist, and refills the zones. It only uses spots clear of other copper,
holes, courtyards and the board edge.
"""
import math
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import complete_route as C        # noqa: E402  (geometry helpers)
import gen_schematics as G        # noqa: E402  (s-expression parser)

FP_DIR = r"C:/Program Files/KiCad/10.0/share/kicad/footprints/"


def main(ref):
    net_file = os.path.join(os.environ.get("TEMP", HERE), "hub_hole.net")
    subprocess.run([C.CLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", net_file,
                    os.path.join(HERE, "hub", "roomkey-hub.kicad_sch")], check=True, capture_output=True)
    root = G.parse(open(net_file, encoding="utf-8").read())[0]
    comp = next(c for c in G.kids(G.kid(root, "components"), "comp") if str(G.kid(c, "ref")[1]) == ref)
    fields = {str(f[1][1]): (str(f[2]) if len(f) > 2 else "") for f in G.kids(G.kid(comp, "fields"), "field")}
    padnet = {}
    for n in G.kids(G.kid(root, "nets"), "net"):
        for node in G.kids(n, "node"):
            padnet[(str(G.kid(node, "ref")[1]), str(G.kid(node, "pin")[1]))] = str(G.kid(n, "name")[1])

    b = pcbnew.LoadBoard(C.PCB)
    if b.FindFootprintByReference(ref):
        raise SystemExit("%s is already on the board" % ref)

    def netobj(name):
        n = b.FindNet(name)
        if n is None:
            n = pcbnew.NETINFO_ITEM(b, name)
            b.Add(n)
        return n
    for p in b.FindFootprintByReference("J4").Pads():      # J4 pins now unconnected in the schematic
        want = padnet.get(("J4", p.GetNumber()))
        if want and p.GetNetname() != want:
            p.SetNet(netobj(want))
    netname = padnet[(ref, "1")]
    net = netobj(netname)

    nick, name = str(G.kid(comp, "footprint")[1]).split(":")
    fp = pcbnew.FootprintLoad(FP_DIR + nick + ".pretty", name)
    fp.SetFPID(pcbnew.LIB_ID(nick, name))
    fp.SetReference(ref)
    fp.SetValue(str(G.kid(comp, "value")[1]))
    fp.SetPath(pcbnew.KIID_PATH("/" + str(G.kid(comp, "tstamps")[1])))
    for k, v in fields.items():
        if k != "Footprint":
            fp.SetField(k, v)
            f = fp.GetField(k)
            if f is not None and k not in ("Reference", "Value"):
                f.SetVisible(False)
    fp.Reference().SetVisible(False)
    fp.SetDNP(True)
    fp.SetExcludedFromBOM(True)
    b.Add(fp)
    fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
    pad = list(fp.Pads())[0]
    pad.SetNet(net)
    pr = C.to_mm(pad.GetSizeX()) / 2
    hr = C.to_mm(pad.GetDrillSizeX()) / 2
    cy = fp.GetCourtyard(pcbnew.B_CrtYd).BBox()
    half = max(C.to_mm(cy.GetWidth()), C.to_mm(cy.GetHeight())) / 2

    cu = C.Copper(b, net.GetNetCode())
    boxes = []
    for f in b.GetFootprints():
        if f.GetReference() == ref:
            continue
        s = f.GetCourtyard(pcbnew.B_CrtYd)
        bb = s.BBox() if s.OutlineCount() else f.GetBoundingBox(False)
        boxes.append((C.to_mm(bb.GetLeft()), C.to_mm(bb.GetTop()), C.to_mm(bb.GetRight()), C.to_mm(bb.GetBottom())))
    edge = next(d for d in b.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_POLY)
    inner = pcbnew.SHAPE_POLY_SET(edge.GetPolyShape())
    inner.Inflate(-C.mm(0.35 + pr), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, C.mm(0.01))
    vias = [(C.to_mm(t.GetPosition().x), C.to_mm(t.GetPosition().y), C.to_mm(t.GetDrillValue()) / 2)
            for t in b.GetTracks() if t.GetClass() == "PCB_VIA"]
    def hole_ok(x, y):
        if not inner.Contains(pcbnew.VECTOR2I(C.mm(x), C.mm(y))):
            return False
        if any(x0 - half - 0.1 < x < x1 + half + 0.1 and y0 - half - 0.1 < y < y1 + half + 0.1
               for x0, y0, x1, y1 in boxes):
            return False
        if min(cu.dist(pcbnew.B_Cu, x, y), cu.dist(pcbnew.F_Cu, x, y)) < pr + 0.15:
            return False
        return not any(math.hypot(x - vx, y - vy) < hr + vr + 0.3 for vx, vy, vr in vias)

    pts = []                                     # the net's routed copper, every 0.1 mm
    for t in b.GetTracks():
        if t.GetClass() == "PCB_TRACK" and t.GetNetCode() == net.GetNetCode() and t.GetLayer() == pcbnew.B_Cu:
            a, e = t.GetStart(), t.GetEnd()
            ax, ay, ex, ey = C.to_mm(a.x), C.to_mm(a.y), C.to_mm(e.x), C.to_mm(e.y)
            n = max(1, int(math.hypot(ex - ax, ey - ay) / 0.1))
            pts += [(ax + (ex - ax) * k / n, ay + (ey - ay) * k / n) for k in range(n + 1)]
    best = None                                  # (stub length, hole x, y, track point)
    for px, py in pts:
        for r in [i * 0.1 for i in range(0, 26)]:
            if best and r >= best[0]:
                break
            for ang in range(0, 360, 15):
                x, y = px + r * math.cos(math.radians(ang)), py + r * math.sin(math.radians(ang))
                if not hole_ok(x, y):
                    continue
                n = max(1, int(r / 0.05))
                if r > 0 and any(cu.dist(pcbnew.B_Cu, px + (x - px) * k / n, py + (y - py) * k / n) < C.W / 2 + C.CLR
                                 for k in range(1, n)):
                    continue
                best = (r, x, y, (px, py))
                break
    if best is None:
        raise SystemExit("no free spot near %s's copper" % netname)
    fp.SetPosition(pcbnew.VECTOR2I(C.mm(best[1]), C.mm(best[2])))
    if best[0] > 0:                              # short B.Cu stub from the track to the hole
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(C.mm(best[3][0]), C.mm(best[3][1])))
        t.SetEnd(pcbnew.VECTOR2I(C.mm(best[1]), C.mm(best[2])))
        t.SetWidth(C.mm(C.W))
        t.SetLayer(pcbnew.B_Cu)
        t.SetNet(net)
        b.Add(t)
    best = (best[0], best[1], best[2])
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(C.PCB, b)
    print("%s placed on %s at (%.2f, %.2f), stub %.2f mm" % (ref, netname, best[1], best[2], best[0]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
