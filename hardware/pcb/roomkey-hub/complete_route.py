#!/usr/bin/env python3
"""RoomKey hub: close the connections Freerouting left open, on the (nearly empty) front layer F.Cu.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/complete_route.py

Reads KiCad's DRC report for "unconnected_items", and for each pair: a via next to each end (unless the end is already
on F.Cu), a grid search (0.1 mm, 8 directions) on F.Cu between them clear of all other copper, holes and the edge, then
tracks + vias + short B.Cu stubs. Also widens Freerouting's neck-downs below 0.15 mm. Refills the zones, saves.
"""
import collections
import math
import os
import re
import subprocess
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "hub", "roomkey-hub.kicad_pcb")
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
mm, to_mm = pcbnew.FromMM, pcbnew.ToMM
W, CLR, VIA, DRILL, STEP = 0.15, 0.15, 0.6, 0.3, 0.05     # track, clearance (+ margin), via, drill, grid (mm)


def drc_unconnected():
    rpt = os.path.join(os.environ.get("TEMP", HERE), "roomkey-hub-complete.rpt")
    subprocess.run([CLI, "pcb", "drc", "-o", rpt, PCB], capture_output=True)
    text = open(rpt, encoding="utf-8").read()
    pairs = []
    for block in text.split("\n[")[1:]:
        if not block.startswith("unconnected_items]"):
            continue
        pts = re.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (PTH pad|Pad|Track|Via) (?:(\S+) )?\[([^\]]+)\]"
                         r"(?: of (\S+))?(?: on ([A-Za-z0-9.]+Cu))?", block)
        if len(pts) >= 2:
            pairs.append(pts[:2])
    return pairs


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


class Copper:
    """other-net copper per layer as primitives in mm: ("seg", ax, ay, bx, by, half) / ("box", x0, y0, x1, y1)."""

    def __init__(self, board, net):
        self.items = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
        self.holes = []
        for t in board.GetTracks():
            if t.GetNetCode() == net:
                continue
            if t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                for L in self.items:
                    self.items[L].append(("seg", to_mm(p.x), to_mm(p.y), to_mm(p.x), to_mm(p.y), to_mm(t.GetWidth(pcbnew.F_Cu)) / 2))   # KiCad 10: a via width is per layer
            elif t.GetLayer() in self.items:
                a, b = t.GetStart(), t.GetEnd()
                self.items[t.GetLayer()].append(("seg", to_mm(a.x), to_mm(a.y), to_mm(b.x), to_mm(b.y),
                                                 to_mm(t.GetWidth()) / 2))
        for f in board.GetFootprints():
            for p in f.Pads():
                bb = p.GetBoundingBox()
                box = ("box", to_mm(bb.GetLeft()), to_mm(bb.GetTop()), to_mm(bb.GetRight()), to_mm(bb.GetBottom()))
                if p.GetDrillSizeX() > 0:
                    c = p.GetPosition()
                    self.holes.append((to_mm(c.x), to_mm(c.y), to_mm(p.GetDrillSizeX()) / 2))
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH or p.GetNetCode() == net:
                    continue
                for L in self.items:
                    if p.IsOnLayer(L):
                        self.items[L].append(box)

    def dist(self, L, x, y):
        d = 1e9
        for it in self.items[L]:
            if it[0] == "seg":
                d = min(d, seg_dist(x, y, it[1], it[2], it[3], it[4]) - it[5])
            else:
                dx = max(it[1] - x, 0, x - it[3])
                dy = max(it[2] - y, 0, y - it[4])
                d = min(d, math.hypot(dx, dy))
        for hx, hy, hr in self.holes:
            d = min(d, math.hypot(x - hx, y - hy) - hr - 0.1)      # hole clearance 0.25 vs copper 0.15
        return d


def ripup_reroute(board, pairs, radius=1.6):
    """remove the open nets' tracks and every other signal track/via within `radius` of their pins, then let
    Freerouting lay just those again on the otherwise finished board (it keeps the rest). Runs in its own process:
    KiCad's Python returns a broken board object when a board is loaded twice in one process."""
    sys.path.insert(0, HERE)
    import route_hub
    nets = {a[4] for a, _ in pairs}
    spots = [(float(it[0]), float(it[1])) for pr in pairs for it in pr if it[2] in ("Pad", "PTH pad")]
    for t in list(board.GetTracks()):
        n = t.GetNetname()
        if n in ("GND", "+5V"):
            continue
        if n in nets:
            board.Remove(t)
            continue
        a, e = t.GetStart(), t.GetEnd()
        if any(seg_dist(x, y, to_mm(a.x), to_mm(a.y), to_mm(e.x), to_mm(e.y)) < radius for x, y in spots):
            board.Remove(t)
    dsn = os.path.join(route_hub.WORK, "repair.dsn")
    ses = os.path.join(route_hub.WORK, "repair.ses")
    pcbnew.ExportSpecctraDSN(board, dsn)
    if os.path.exists(ses):
        os.remove(ses)
    r = subprocess.run([route_hub.JAVA, "-jar", route_hub.JAR, "-de", dsn, "-do", ses, "-mp", "100", "-l", "en"],
                       capture_output=True, text=True, timeout=1800)
    done = [l for l in (r.stdout + r.stderr).splitlines() if "Auto-routing stage completed" in l]
    print("rip-up + reroute of %s: %s" % (sorted(nets), done[-1].split("final score:")[-1].strip() if done else "?"))
    if os.path.exists(ses) and pcbnew.ImportSpecctraSES(board, ses):
        pcbnew.ZONE_FILLER(board).Fill(board.Zones())
        pcbnew.SaveBoard(PCB, board)


def main():
    pairs = drc_unconnected()
    if "--ripup-only" in sys.argv:
        ripup_reroute(pcbnew.LoadBoard(PCB), pairs)
        return
    if pairs and "--no-ripup" not in sys.argv:
        import shutil
        shutil.copy(PCB, PCB + ".before-ripup")
        subprocess.run([sys.executable, os.path.abspath(__file__), "--ripup-only"])
        after = drc_unconnected()
        if len(after) > len(pairs):
            shutil.copy(PCB + ".before-ripup", PCB)
            print("rip-up left %d open (was %d): reverted" % (len(after), len(pairs)))
        else:
            print("rip-up: %d open (was %d)" % (len(after), len(pairs)))
            pairs = after
        os.remove(PCB + ".before-ripup")
    board = pcbnew.LoadBoard(PCB)
    for t in board.GetTracks():                       # Freerouting's neck-downs → 0.12 mm (JLCPCB 4-layer: 0.09)
        if t.GetClass() == "PCB_TRACK" and t.GetWidth() < mm(0.12):
            t.SetWidth(mm(0.12))
    edge = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_POLY)
    inner = pcbnew.SHAPE_POLY_SET(edge.GetPolyShape())
    inner.Inflate(-mm(0.35 + W / 2), pcbnew.CORNER_STRATEGY_ROUND_ALL_CORNERS, mm(0.01))
    slot = next(d for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts and d.GetShape() == pcbnew.SHAPE_T_RECT)
    sb = slot.GetBoundingBox()
    sx0, sy0, sx1, sy1 = (to_mm(sb.GetLeft()) - 0.6, to_mm(sb.GetTop()) - 0.6, to_mm(sb.GetRight()) + 0.6,
                          to_mm(sb.GetBottom()) + 0.6)
    ebb = edge.GetBoundingBox()
    X0, Y0 = to_mm(ebb.GetLeft()), to_mm(ebb.GetTop())
    NX, NY = int(to_mm(ebb.GetWidth()) / STEP) + 1, int(to_mm(ebb.GetHeight()) / STEP) + 1

    def ok_edge(x, y):
        return inner.Contains(pcbnew.VECTOR2I(mm(x), mm(y))) and not (sx0 < x < sx1 and sy0 < y < sy1)

    print("open:", [(p[0][4], p[1][4]) for p in pairs])
    for a, b in pairs:
        netname = a[4]
        net = board.FindNet(netname)
        cu = Copper(board, net.GetNetCode())

        def end_point(item, other):
            """(x, y, needs_via): pads and B.Cu tracks get a via; an F.Cu track starts the search directly."""
            x, y, kind, _, _, ref, layer = item
            x, y = float(x), float(y)
            if kind == "Track":       # use the track's end nearest to the other item
                best = None
                for t in board.GetTracks():
                    if t.GetClass() == "PCB_TRACK" and t.GetNetCode() == net.GetNetCode() and \
                            board.GetLayerName(t.GetLayer()) == layer:
                        for e in (t.GetStart(), t.GetEnd()):
                            d0 = math.hypot(to_mm(e.x) - x, to_mm(e.y) - y)
                            if d0 < 3.0:
                                dd = math.hypot(to_mm(e.x) - float(other[0]), to_mm(e.y) - float(other[1]))
                                if best is None or dd < best[0]:
                                    best = (dd, to_mm(e.x), to_mm(e.y))
                if best:
                    x, y = best[1], best[2]
            if kind == "PTH pad":     # through-hole: already on F.Cu
                return x, y, False
            return x, y, layer != "F.Cu"

        def layer_map(L):
            """obstacle map for this net on one copper layer (track centreline may not enter a 1)."""
            m = bytearray(NX * NY)
            for i in range(NX):
                for j in range(NY):
                    if not ok_edge(X0 + i * STEP, Y0 + j * STEP):
                        m[i * NY + j] = 1

            def mark(x0, y0, x1, y1, test):
                for i in range(max(0, int((x0 - X0) / STEP)), min(NX, int((x1 - X0) / STEP) + 2)):
                    for j in range(max(0, int((y0 - Y0) / STEP)), min(NY, int((y1 - Y0) / STEP) + 2)):
                        if test(X0 + i * STEP, Y0 + j * STEP):
                            m[i * NY + j] = 1
            g = W / 2 + CLR
            for it in cu.items[L]:
                if it[0] == "seg":
                    _, ax, ay, bx, by, h = it
                    r = h + g
                    mark(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r,
                         lambda x, y, ax=ax, ay=ay, bx=bx, by=by, r=r: seg_dist(x, y, ax, ay, bx, by) < r)
                else:
                    _, bx0, by0, bx1, by1 = it
                    mark(bx0 - g, by0 - g, bx1 + g, by1 + g, lambda x, y: True)
            for hx, hy, hr in cu.holes:
                r = hr + 0.1 + g
                mark(hx - r, hy - r, hx + r, hy + r, lambda x, y, hx=hx, hy=hy, r=r: math.hypot(x - hx, y - hy) < r)
            return m
        bmap = layer_map(pcbnew.B_Cu)
        all_vias = [(to_mm(t.GetPosition().x), to_mm(t.GetPosition().y)) for t in board.GetTracks()
                    if t.GetClass() == "PCB_VIA"]          # any net: never drill on top of another hole
        via_ok = {}

        def via_spot(x, y):
            """B.Cu escape: grid search from the pin to the nearest cell where a via fits on both layers.
            Returns (via_xy, B.Cu polyline from the pin) or None."""
            s0 = (int(round((x - X0) / STEP)), int(round((y - Y0) / STEP)))
            prev = {s0: None}
            q = collections.deque([s0])
            while q:
                c = q.popleft()
                cx, cy = X0 + c[0] * STEP, Y0 + c[1] * STEP
                if math.hypot(cx - x, cy - y) > 0.5:
                    if c not in via_ok:
                        via_ok[c] = ok_edge(cx, cy) and cu.dist(pcbnew.B_Cu, cx, cy) >= VIA / 2 + CLR and                             cu.dist(pcbnew.F_Cu, cx, cy) >= VIA / 2 + CLR and                             all(math.hypot(cx - vx, cy - vy) >= VIA + 0.3 for vx, vy in all_vias)
                    if via_ok[c]:
                        path = []
                        while c is not None:
                            path.append((X0 + c[0] * STEP, Y0 + c[1] * STEP))
                            c = prev[c]
                        path.reverse()
                        path[0] = (x, y)
                        return path[-1], path
                if math.hypot(cx - x, cy - y) > 4.0:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    n2 = (c[0] + dx, c[1] + dy)
                    if n2 in prev or not (0 <= n2[0] < NX and 0 <= n2[1] < NY):
                        continue
                    nx_, ny_ = X0 + n2[0] * STEP, Y0 + n2[1] * STEP
                    # inside the pin's own pad the map is free (same net); elsewhere obey the B.Cu map
                    if bmap[n2[0] * NY + n2[1]] and math.hypot(nx_ - x, ny_ - y) > 0.15:
                        continue
                    prev[n2] = c
                    q.append(n2)
            return None

        # both ends reachable on B.Cu (SMD pad there, a through-hole pad, or a B.Cu track): try a direct B.Cu path first
        if all(it[2] == "PTH pad" or it[6] == "B.Cu" for it in (a, b)):
            pa = end_point(a, b)[:2]
            pb = end_point(b, a)[:2]
            ca = (int(round((pa[0] - X0) / STEP)), int(round((pa[1] - Y0) / STEP)))
            cb = (int(round((pb[0] - X0) / STEP)), int(round((pb[1] - Y0) / STEP)))
            prev = {ca: None}
            q = collections.deque([ca])
            while q:
                c = q.popleft()
                if c == cb:
                    break
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                    n2 = (c[0] + dx, c[1] + dy)
                    if n2 in prev or not (0 <= n2[0] < NX and 0 <= n2[1] < NY):
                        continue
                    nx_, ny_ = X0 + n2[0] * STEP, Y0 + n2[1] * STEP
                    near_end = math.hypot(nx_ - pa[0], ny_ - pa[1]) < 0.5 or math.hypot(nx_ - pb[0], ny_ - pb[1]) < 0.5
                    if bmap[n2[0] * NY + n2[1]] and not near_end:
                        continue
                    prev[n2] = c
                    q.append(n2)
            if cb in prev:
                path = []
                c = cb
                while c is not None:
                    path.append((X0 + c[0] * STEP, Y0 + c[1] * STEP))
                    c = prev[c]
                path.reverse()
                path[0], path[-1] = pa, pb
                corners = [path[0]] + [path[i] for i in range(1, len(path) - 1)
                                       if (round(path[i][0] - path[i - 1][0], 3), round(path[i][1] - path[i - 1][1], 3)) !=
                                       (round(path[i + 1][0] - path[i][0], 3), round(path[i + 1][1] - path[i][1], 3))] + [path[-1]]
                for p0, p1 in zip(corners, corners[1:]):
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(pcbnew.VECTOR2I(mm(p0[0]), mm(p0[1])))
                    t.SetEnd(pcbnew.VECTOR2I(mm(p1[0]), mm(p1[1])))
                    t.SetWidth(mm(W))
                    t.SetLayer(pcbnew.B_Cu)
                    t.SetNet(net)
                    board.Add(t)
                print("  %s: routed on B.Cu, %d segments" % (netname, len(corners) - 1))
                continue
        ends = []
        for it, other in ((a, b), (b, a)):
            x, y, needs = end_point(it, other)
            if needs:
                found = via_spot(x, y)
                if found is None:
                    print("  %s: no via spot near (%.2f, %.2f)" % (netname, x, y))
                    break
                ends.append((x, y, found[0], found[1]))
            else:
                ends.append((x, y, None, None))
        if len(ends) < 2:
            continue
        # grid search on F.Cu
        def cell(x, y):
            return int(round((x - X0) / STEP)), int(round((y - Y0) / STEP))

        def xy(c):
            return X0 + c[0] * STEP, Y0 + c[1] * STEP
        start = cell(*(ends[0][2] or ends[0][:2]))
        goal = cell(*(ends[1][2] or ends[1][:2]))
        blocked = bytearray(NX * NY)                      # obstacle map for this net on F.Cu
        for i in range(NX):
            for j in range(NY):
                if not ok_edge(X0 + i * STEP, Y0 + j * STEP):
                    blocked[i * NY + j] = 1

        def mark(x0, y0, x1, y1, test):
            for i in range(max(0, int((x0 - X0) / STEP)), min(NX, int((x1 - X0) / STEP) + 2)):
                for j in range(max(0, int((y0 - Y0) / STEP)), min(NY, int((y1 - Y0) / STEP) + 2)):
                    if test(X0 + i * STEP, Y0 + j * STEP):
                        blocked[i * NY + j] = 1
        g = W / 2 + CLR
        for it in cu.items[pcbnew.F_Cu]:
            if it[0] == "seg":
                _, ax, ay, bx, by, h = it
                r = h + g
                mark(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r,
                     lambda x, y, ax=ax, ay=ay, bx=bx, by=by, r=r: seg_dist(x, y, ax, ay, bx, by) < r)
            else:
                _, bx0, by0, bx1, by1 = it
                mark(bx0 - g, by0 - g, bx1 + g, by1 + g, lambda x, y: True)
        for hx, hy, hr in cu.holes:
            r = hr + 0.1 + g
            mark(hx - r, hy - r, hx + r, hy + r, lambda x, y, hx=hx, hy=hy, r=r: math.hypot(x - hx, y - hy) < r)

        def free(c):
            return 0 <= c[0] < NX and 0 <= c[1] < NY and not blocked[c[0] * NY + c[1]]
        prev = {start: None}
        q = collections.deque([start])
        while q:
            c = q.popleft()
            if c == goal:
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
                n2 = (c[0] + dx, c[1] + dy)
                if n2 not in prev and (n2 == goal or free(n2)):
                    prev[n2] = c
                    q.append(n2)
        if goal not in prev:
            print("  %s: no path on F.Cu" % netname)
            continue
        path = []
        c = goal
        while c is not None:
            path.append(c)
            c = prev[c]
        path.reverse()
        pts = [path[0]]                                   # keep only the corners
        for i in range(1, len(path) - 1):
            d1 = (path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1])
            d2 = (path[i + 1][0] - path[i][0], path[i + 1][1] - path[i][1])
            if d1 != d2:
                pts.append(path[i])
        pts.append(path[-1])

        def add_track(p0, p1, layer, width=W):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(pcbnew.VECTOR2I(mm(p0[0]), mm(p0[1])))
            t.SetEnd(pcbnew.VECTOR2I(mm(p1[0]), mm(p1[1])))
            t.SetWidth(mm(width))
            t.SetLayer(layer)
            t.SetNet(net)
            board.Add(t)
        coords = [xy(c) for c in pts]
        coords[0] = ends[0][2] or ends[0][:2]
        coords[-1] = ends[1][2] or ends[1][:2]
        for p0, p1 in zip(coords, coords[1:]):
            add_track(p0, p1, pcbnew.F_Cu)
        for x, y, v, stub in ends:
            if v:
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(pcbnew.VECTOR2I(mm(v[0]), mm(v[1])))
                via.SetWidth(mm(VIA))
                via.SetDrill(mm(DRILL))
                via.SetNet(net)
                board.Add(via)
                corners = [stub[0]] + [stub[i] for i in range(1, len(stub) - 1)
                                       if (stub[i][0] - stub[i - 1][0], stub[i][1] - stub[i - 1][1]) !=
                                       (stub[i + 1][0] - stub[i][0], stub[i + 1][1] - stub[i][1])] + [stub[-1]]
                for p0, p1 in zip(corners, corners[1:]):
                    add_track(p0, p1, pcbnew.B_Cu)
        print("  %s: routed on F.Cu, %d segments, %.1f mm" % (
            netname, len(coords) - 1, sum(math.hypot(q1[0] - q0[0], q1[1] - q0[1]) for q0, q1 in zip(coords, coords[1:]))))
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)


if __name__ == "__main__":
    sys.exit(main())
