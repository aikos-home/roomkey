#!/usr/bin/env python3
"""RoomKey hub: autoroute the placed board with Freerouting (inner GND/+5V planes), then pour GND outside.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/route_hub.py

Needs Java 25+ and freerouting-2.5.0.jar (owner allowed the download 2026-10-08; both in ~/tools or $ROOMKEY_TOOLS, override
with JAVA / FREEROUTING). It re-runs gen_layout_hub.py first, so it always routes a fresh placement.
Track widths and clearances come from the project's net classes (Default 0.15/0.13 — JLCPCB 4-layer allows 0.09 —,
Plane 0.3/0.15 for GND/+5V, Power 0.3/0.2 for the supply path and the speaker).
"""
import glob
import math
import os
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "hub", "roomkey-hub.kicad_pcb")
TOOLS = os.environ.get("ROOMKEY_TOOLS", os.path.expanduser("~/tools"))   # Java 25 + Freerouting jar
JAVA = os.environ.get("JAVA") or (glob.glob(TOOLS + "/jdk-25*/bin/java.exe") or ["java"])[0]
JAR = os.environ.get("FREEROUTING", TOOLS + "/freerouting-2.5.0.jar")
WORK = os.path.join(os.environ.get("TEMP", HERE), "roomkey-hub-route")


def gnd_zone(board, layer, net):
    """a GND pour over the whole board on one layer (the outline's polygon)."""
    edge = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_POLY)
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(net)
    ol = edge.GetPolyShape().Outline(0)
    z.AddPolygon(pcbnew.VECTOR_VECTOR2I([ol.CPoint(i) for i in range(ol.PointCount())]))
    z.SetLocalClearance(pcbnew.FromMM(0.25))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(pcbnew.FromMM(0.25))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.3))
    board.Add(z)
    return z


def fanout(board, netnames=("GND", "+5V"), via=(0.6, 0.3), width=0.3, clr=0.2):
    """a via next to every SMD pad of a plane net, with a short stub: the pad reaches its inner plane directly.
    Candidates around the pad (8 directions, 2 distances); the first one clear of every other pad, via, hole and the
    board edge wins. Returns the pads it could not fan out."""
    mm = pcbnew.FromMM
    vr = mm(via[0]) / 2
    pads = [p for f in board.GetFootprints() for p in f.Pads()]
    obst = []                                   # (x0, y0, x1, y1, netcode) in nm, inflated by clearance + via radius
    for p in pads:
        bb = p.GetBoundingBox()
        g = mm(clr) + vr
        obst.append((bb.GetLeft() - g, bb.GetTop() - g, bb.GetRight() + g, bb.GetBottom() + g,
                     p.GetNetCode() if p.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH else -1))
    edge_poly = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts
                     and d.GetShape() == pcbnew.SHAPE_T_POLY).GetPolyShape()
    slot = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_RECT)
    sb = slot.GetBoundingBox()
    vias = []
    failed = []

    def seg_hits(ax, ay, bx, by, box):
        """does the segment a-b pass through the box (x0, y0, x1, y1)? (sampled every 0.05 mm)"""
        n = max(2, int(math.hypot(bx - ax, by - ay) / mm(0.05)))
        for i in range(n + 1):
            t = i / n
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            if box[0] < x < box[2] and box[1] < y < box[3]:
                return True
        return False

    def stub_ok(c, x, y, net):
        g = mm(clr) + mm(width) / 2
        for p2 in pads:
            if p2.GetNetCode() == net and p2.GetAttribute() != pcbnew.PAD_ATTRIB_NPTH:
                continue
            bb = p2.GetBoundingBox()
            box = (bb.GetLeft() - g, bb.GetTop() - g, bb.GetRight() + g, bb.GetBottom() + g)
            if not (min(c.x, x) > box[2] or max(c.x, x) < box[0] or min(c.y, y) > box[3] or max(c.y, y) < box[1]):
                if seg_hits(c.x, c.y, x, y, box):
                    return False
        return True

    def free(x, y, net):
        if not edge_poly.Contains(pcbnew.VECTOR2I(int(x), int(y))):
            return False
        for a in range(0, 360, 20):                          # via edge ≥ 0.4 mm from the outline
            r = vr + mm(0.4)
            if not edge_poly.Contains(pcbnew.VECTOR2I(int(x + r * math.cos(math.radians(a))),
                                                      int(y + r * math.sin(math.radians(a))))):
                return False
        g = mm(0.5) + vr                                     # the slot's keep-out (0.5 round it, main()) + the via
        if sb.GetLeft() - g < x < sb.GetRight() + g and sb.GetTop() - g < y < sb.GetBottom() + g:
            return False
        for x0, y0, x1, y1, n in obst:
            if n != net and x0 < x < x1 and y0 < y < y1:
                return False
        for vx, vy in vias:
            if math.hypot(vx - x, vy - y) < 2 * vr + mm(clr):
                return False
        return True

    for p in pads:
        net = p.GetNetname()
        if net not in netnames or p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        c = p.GetPosition()
        bb = p.GetBoundingBox()
        hw, hh = bb.GetWidth() / 2, bb.GetHeight() / 2
        if (p.GetParentFootprint().GetReference(), p.GetNumber()) in (("U3", "17"), ("U1", "7")):   # exposed pads
            v = pcbnew.PCB_VIA(board)                  # exposed pad: one via in the pad (thermal + plane)
            v.SetPosition(c)
            v.SetWidth(mm(via[0]))
            v.SetDrill(mm(via[1]))
            v.SetNet(p.GetNet())
            board.Add(v)
            vias.append((c.x, c.y))
            continue
        done = False
        for extra in (0.15, 0.6, 1.2):
            for ang in range(0, 360, 45):
                ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                # from the pad centre out past its edge (box), then a via radius + gap further
                t = min(hw / abs(ux) if abs(ux) > 1e-6 else 1e18, hh / abs(uy) if abs(uy) > 1e-6 else 1e18)
                r = t + vr + mm(extra)
                x, y = c.x + ux * r, c.y + uy * r
                if free(x, y, p.GetNetCode()) and stub_ok(c, x, y, p.GetNetCode()):
                    v = pcbnew.PCB_VIA(board)
                    v.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
                    v.SetWidth(mm(via[0]))
                    v.SetDrill(mm(via[1]))
                    v.SetNet(p.GetNet())
                    board.Add(v)
                    t_ = pcbnew.PCB_TRACK(board)
                    t_.SetStart(c)
                    t_.SetEnd(pcbnew.VECTOR2I(int(x), int(y)))
                    t_.SetWidth(mm(width))
                    t_.SetLayer(pcbnew.B_Cu)
                    t_.SetNet(p.GetNet())
                    board.Add(t_)
                    vias.append((x, y))
                    obst.append((x - vr - mm(clr) - vr, y - vr - mm(clr) - vr, x + vr + mm(clr) + vr,
                                 y + vr + mm(clr) + vr, p.GetNetCode()))
                    done = True
                    break
            if done:
                break
        if not done:      # fine-pitch pin next to a same-net exposed pad of its own part: a stub into that pad
            ep = [q for q in p.GetParentFootprint().Pads() if q is not p and q.GetNetCode() == p.GetNetCode()
                  and q.GetBoundingBox().GetWidth() > mm(1.0) and q.GetBoundingBox().GetHeight() > mm(1.0)]
            for q in ep:
                e = q.GetPosition()
                if stub_ok(c, e.x, e.y, p.GetNetCode()):
                    t_ = pcbnew.PCB_TRACK(board)
                    t_.SetStart(c)
                    t_.SetEnd(e)
                    t_.SetWidth(mm(0.25))
                    t_.SetLayer(pcbnew.B_Cu)
                    t_.SetNet(p.GetNet())
                    board.Add(t_)
                    done = True
                    break
        if not done:
            failed.append("%s.%s" % (p.GetParentFootprint().GetReference(), p.GetNumber()))
    return failed


def main():
    os.makedirs(WORK, exist_ok=True)
    dsn, ses = os.path.join(WORK, "hub.dsn"), os.path.join(WORK, "hub.ses")
    sys.path.insert(0, HERE)
    import gen_layout_hub                       # start clean: a fresh placement (deterministic), no tracks, no zones
    if gen_layout_hub.main():
        raise SystemExit("placement incomplete")
    board = pcbnew.LoadBoard(PCB)
    # inner planes first: Freerouting connects GND and +5V pads to them with vias
    gnd_zone(board, pcbnew.In1_Cu, board.FindNet("GND"))
    gnd_zone(board, pcbnew.In2_Cu, board.FindNet("+5V"))
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ko.SetDoNotAllowZoneFills(False)
    ko.SetDoNotAllowPads(False)
    ko.SetDoNotAllowFootprints(False)
    ko.SetLayerSet(pcbnew.LSET.AllCuMask())
    sl = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_RECT)
    sb = sl.GetBoundingBox()
    g = pcbnew.FromMM(0.5)
    ko.AddPolygon(pcbnew.VECTOR_VECTOR2I([pcbnew.VECTOR2I(sb.GetLeft() - g, sb.GetTop() - g),
                                          pcbnew.VECTOR2I(sb.GetRight() + g, sb.GetTop() - g),
                                          pcbnew.VECTOR2I(sb.GetRight() + g, sb.GetBottom() + g),
                                          pcbnew.VECTOR2I(sb.GetLeft() - g, sb.GetBottom() + g)]))
    board.Add(ko)
    # keep-out strip along the outline: Freerouting does not hold the 0.3 mm copper-to-edge rule by itself
    edge = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_POLY)
    ring = pcbnew.SHAPE_POLY_SET(edge.GetPolyShape())
    inner = pcbnew.SHAPE_POLY_SET(edge.GetPolyShape())
    inner.Inflate(-pcbnew.FromMM(0.35), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcbnew.FromMM(0.01))
    ring.BooleanSubtract(inner)
    for i in range(ring.OutlineCount()):
        kz = pcbnew.ZONE(board)
        kz.SetIsRuleArea(True)
        kz.SetDoNotAllowTracks(True)
        kz.SetDoNotAllowVias(True)
        kz.SetDoNotAllowZoneFills(False)
        kz.SetDoNotAllowPads(False)
        kz.SetDoNotAllowFootprints(False)
        kz.SetLayerSet(pcbnew.LSET.AllCuMask())
        one = pcbnew.SHAPE_POLY_SET()
        one.AddOutline(ring.Outline(i))
        for h in range(ring.HoleCount(i)):
            one.AddHole(ring.Hole(i, h))
        kz.SetOutline(one)
        board.Add(kz)
    missed = fanout(board)
    print("fan-out: %d vias; no spot for %s" % (sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA"),
                                                  missed or "none"))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    best = None                                 # (unrouted, session file): later rounds can be worse — keep the best
    for rnd in range(3):
        if not pcbnew.ExportSpecctraDSN(board, dsn):
            raise SystemExit("DSN export failed")
        ses_r = ses.replace(".ses", "_%d.ses" % rnd)
        if os.path.exists(ses_r):
            os.remove(ses_r)
        r = subprocess.run([JAVA, "-jar", JAR, "-de", dsn, "-do", ses_r, "-mp", "200", "-l", "en"] +
                           os.environ.get("FR_ARGS", "").split(),
                           capture_output=True, text=True, timeout=1800)
        log = (r.stdout + r.stderr).splitlines()
        if not os.path.exists(ses_r):
            raise SystemExit("Freerouting wrote no session file")
        if not pcbnew.ImportSpecctraSES(board, ses_r):
            raise SystemExit("SES import failed")
        left = [l for l in log if "Auto-routing stage completed" in l]
        txt = left[-1].split("final score:")[-1].strip() if left else "? (999 unrouted"
        print("round %d: %s" % (rnd + 1, txt))
        try:
            n = int(txt.split("(")[1].split()[0])
        except (IndexError, ValueError):
            n = 999
        if best is None or n < best[0]:
            best = (n, ses_r)
        if n == 0 or n > best[0]:
            break
    if not pcbnew.ImportSpecctraSES(board, best[1]):
        raise SystemExit("SES import failed")
    print("kept the round with %d unrouted" % best[0])
    gnd = board.FindNet("GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):        # outer GND pours round the routing
        gnd_zone(board, layer, gnd)
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print("tracks/vias:", len(board.GetTracks()))


if __name__ == "__main__":
    sys.exit(main())
