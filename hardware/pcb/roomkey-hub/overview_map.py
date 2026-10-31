#!/usr/bin/env python3
"""RoomKey hub: overview picture "what is what" (German labels for the owner), drawn from the board itself.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/overview_map.py

Writes output/roomkey-hub_overview_de.svg/.png: the back of the hub (where all parts sit), every part's outline at its
real position, coloured by what it does, with plain-language callouts.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "hub", "roomkey-hub.kicad_pcb")
OUT = os.path.join(HERE, "output", "roomkey-hub_overview_de")

# group: (colour, callout title, callout line 2, parts)
GROUPS = [
    ("#c0392b", "5 V Eingang + Schutz", "Stecker fürs USB-Kabel + Schutzschaltung",
     "J1 D1 Q1 D2 R1 C1 U1 R2 R17 D3 C2 C3 C4 TP1"),
    ("#e67e22", "3,3 V für die Sensoren", "kleiner Spannungsregler",
     "D5 U2 C5 C6 TP2"),
    ("#b9770e", "5 V zum Tasten-Board", "Einbahn-Diode: USB bleibt nutzbar",
     "D4 TP3"),
    ("#2e6fd8", "Ton: Verstärker", "treibt den Lautsprecher",
     "U3 R3 C7 C8"),
    ("#8e44ad", "Mikrofon", "hört durch das Loch in der Platte",
     "U4 C9 R5"),
    ("#555555", "Steckplatz obere MX-Taste", "Taste steckt von vorn hier ein (IO9)",
     "SW1 R13"),
    ("#555555", "Steckplatz untere MX-Taste", "Taste steckt von vorn hier ein (IO6)",
     "SW2 R14"),
    ("#0f9fb0", "LED-Treiber", "macht 5-V-Signal für die LEDs",
     "U7 R15 R16 C13 C14"),
    ("#0f9fb0", "Lötlöcher für die LEDs", "3 Drähte von der LED-Kette (siehe Lötplan)",
     "J8"),
    ("#b8860b", "Lötfeld für die Kabel vom Tasten-Board", "2 x 8 Löcher (siehe Lötplan)",
     "J4"),
    ("#b8860b", "", "", "R6 R11 R12 C15"),
]
PLUGS = {"J2": "Lautsprecher", "J5": "Radar", "J9": "Sensoren (Temperatur, Licht)"}
S = 11.0


def cad(v):
    return pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y)


def main():
    b = pcbnew.LoadBoard(PCB)
    W, H = 1660, 1000
    ox, oy = 800, 520

    def px(x, y):                    # back view: mirror x
        return ox - x * S, oy - y * S
    el = ['<rect width="100%" height="100%" fill="white"/>',
          '<text x="30" y="46" font-size="30" font-weight="bold" fill="#111">RoomKey-Hub: was ist was</text>',
          '<text x="30" y="80" font-size="19" fill="#444">Rückseite (hier sitzen alle Bauteile), maßstäblich. '
          'Die Vorderseite ist leer bis auf die Löcher für die Tasten.</text>']
    for d in b.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if d.GetShape() == pcbnew.SHAPE_T_POLY:
            ol = d.GetPolyShape().Outline(0)
            pts = " ".join("%.1f,%.1f" % px(*cad(ol.CPoint(i))) for i in range(ol.PointCount()))
            el.append('<polygon points="%s" fill="#eef4e8" stroke="#3a7d2c" stroke-width="3"/>' % pts)
        else:
            (x0, y0), (x1, y1) = cad(d.GetStart()), cad(d.GetEnd())
            a, c = px(x0, y0), px(x1, y1)
            el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="white" stroke="#3a7d2c" stroke-width="2"/>'
                      % (min(a[0], c[0]), min(a[1], c[1]), abs(c[0] - a[0]), abs(c[1] - a[1])))
            el.append('<text x="%.1f" y="%.1f" font-size="15" fill="#3a7d2c" text-anchor="middle">Schlitz für die '
                      'Kabel</text>' % ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2 + 5))
    group_of = {}
    for gi, g in enumerate(GROUPS):
        for r in g[3].split():
            group_of[r] = gi

    def fbox(f):
        s = f.GetCourtyard(pcbnew.B_CrtYd)
        bb = s.BBox() if s.OutlineCount() else f.GetBoundingBox(False)
        (x0, y0), (x1, y1) = cad(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop())), cad(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
        a, c = px(x0, y0), px(x1, y1)
        return min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])
    centres = {i: [] for i in range(len(GROUPS))}
    for f in b.GetFootprints():
        ref = f.GetReference()
        x0, y0, x1, y1 = fbox(f)
        if ref.startswith("H"):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            el.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#bbb" stroke="#777"/>' % (cx, cy, 1.1 * S))
            el.append('<text x="%.1f" y="%.1f" font-size="13" fill="#666" text-anchor="middle">Schraube</text>'
                      % (cx, cy + 2.6 * S))
            continue
        if ref in PLUGS:
            el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="3" fill="#fdebd0" stroke="#8a5a00" '
                      'stroke-width="2"/>' % (x0, y0, x1 - x0, y1 - y0))
            continue
        gi = group_of.get(ref)
        col = GROUPS[gi][0] if gi is not None else "#999"
        el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="2" fill="%s" fill-opacity="0.35" stroke="%s" '
                  'stroke-width="1.5"/>' % (x0, y0, x1 - x0, y1 - y0, col, col))
        if gi is not None:
            centres[gi].append(((x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * (y1 - y0)))
    # MX switch holes for orientation
    for ref in ("SW1", "SW2"):
        for p in b.FindFootprintByReference(ref).Pads():
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH and pcbnew.ToMM(p.GetDrillSizeX()) > 3.5:
                cx, cy = px(*cad(p.GetPosition()))
                el.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="white" stroke="#555" stroke-width="1.5"/>'
                          % (cx, cy, 2 * S))
    # callouts: left or right of the board, stacked, leader to the group's weighted centre
    items = []
    for gi, g in enumerate(GROUPS):
        pts = centres[gi]
        if not pts:
            continue
        if not g[1]:
            continue
        gx, gy, _ = max(pts, key=lambda q: q[2])
        items.append((gx, gy, g[1], g[2], g[0]))
    for ref, name in PLUGS.items():
        x0, y0, x1, y1 = fbox(b.FindFootprintByReference(ref))
        items.append(((x0 + x1) / 2, (y0 + y1) / 2, "Stecker: " + name, "", "#8a5a00"))
    left = sorted([i for i in items if i[0] < ox], key=lambda i: i[1])
    right = sorted([i for i in items if i[0] >= ox], key=lambda i: i[1])
    for side, lst in (("L", left), ("R", right)):
        ys = [gy for _, gy, *_ in lst]               # wanted: level with the part
        for _ in range(500):                         # push overlapping neighbours apart, both ways
            moved = False
            for i in range(len(ys) - 1):
                gap = ys[i + 1] - ys[i]
                if gap < 56:
                    ys[i] -= (56 - gap) / 2
                    ys[i + 1] += (56 - gap) / 2
                    moved = True
            ys = [min(max(y, 130), H - 60) for y in ys]
            if not moved:
                break
        for (gx, gy, t1, t2, col), y in zip(lst, ys):
            tx = 330 if side == "L" else 1270
            el.append('<line x1="%.1f" y1="%.1f" x2="%d" y2="%.1f" stroke="%s" stroke-width="1.6"/>'
                      % (gx, gy, tx + (8 if side == "L" else -8), y - 6, col))
            el.append('<circle cx="%.1f" cy="%.1f" r="4.5" fill="%s"/>' % (gx, gy, col))
            anchor = "end" if side == "L" else "start"
            el.append('<text x="%d" y="%.1f" font-size="19" font-weight="bold" fill="%s" text-anchor="%s">%s</text>'
                      % (tx, y, col, anchor, t1))
            if t2:
                el.append('<text x="%d" y="%.1f" font-size="15" fill="#444" text-anchor="%s">%s</text>'
                          % (tx, y + 20, anchor, t2))
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" '
           'font-family="Segoe UI, Arial, sans-serif">%s</svg>' % (W, H, W, H, "".join(el)))
    with open(OUT + ".svg", "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    import pymupdf
    pymupdf.open(OUT + ".svg")[0].get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(OUT + ".png")
    print("wrote", OUT + ".svg/.png")


if __name__ == "__main__":
    sys.exit(main())
