#!/usr/bin/env python3
"""RoomKey hub: soldering map for the hand-soldered wires (key board → hub, 5 V in), drawn from the board itself.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/soldering_map.py

Writes output/roomkey-hub_soldering-map.svg and .png: the hub seen from the BACK (the side with the parts, where the
wires come in), every solder hole at its real position, the 2 x 8 key-wire field enlarged, and for each hole the pad on
the touch board's H1 header (its silkscreen name) the wire comes from.
"""
import math
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "hub", "roomkey-hub.kicad_pcb")
OUT = os.path.join(HERE, "output", "roomkey-hub_soldering-map")

# hub net -> (touch-board pad as printed on its silkscreen, H1 pad, group)
SOURCE = {
    "/VBUS_KEY": ("VBUS", 1, "power"), "GND": ("GND", "3/4/6", "gnd"),
    "/I2S_DOUT_IO16": ("TXD", 5, "i2s"), "/I2S_DIN_IO17": ("RXD", 7, "i2s"), "/I2S_BCLK_IO7": ("7", 22, "i2s"),
    "/I2S_WS_IO8": ("8", 20, "i2s"), "/I2C_SDA_IO18": ("SDA", 12, "i2c"), "/I2C_SCL_IO19": ("SCL", 10, "i2c"),
    "/RADAR_TO_ESP_IO3": ("3", 15, "radar"), "/ESP_TO_RADAR_IO5": ("5", 19, "radar"),
    "/KEY_TOP_IO9": ("9", 18, "key"), "/KEY_BOT_IO6": ("6", 21, "key"), "/GLOW_IO4": ("4", 17, "glow"),
}
COL = {"power": "#c0392b", "gnd": "#222222", "i2s": "#2e6fd8", "i2c": "#1e9e6a", "radar": "#8e44ad", "key": "#d35400",
       "glow": "#0f9fb0", "none": "#aaaaaa", "psu": "#c0392b"}
S = 9.0          # px per mm, whole board
Z = 26.0         # px per mm, enlarged field


def cad(v):
    return pcbnew.ToMM(v.x) - 100, 100 - pcbnew.ToMM(v.y)


def main():
    b = pcbnew.LoadBoard(PCB)
    W, H = 1500, 1040
    ox, oy = 500, 470                   # board centre on the page (left part)

    def px(x, y):                       # back view: mirror x
        return ox - x * S, oy - y * S
    el = ['<rect width="100%" height="100%" fill="white"/>']
    el.append('<text x="30" y="44" font-size="28" font-weight="bold" fill="#111">RoomKey hub — soldering map '
              '(seen from the BACK, the side with the parts)</text>')
    el.append('<text x="30" y="76" font-size="18" fill="#444">Each wire runs from the touch board\'s H1 pad '
              '(name as printed on the board) to the hub hole shown. Push it in from this side, solder, trim.</text>')
    # outline + slot
    for d in b.GetDrawings():
        if d.GetLayer() != pcbnew.Edge_Cuts:
            continue
        if d.GetShape() == pcbnew.SHAPE_T_POLY:
            ol = d.GetPolyShape().Outline(0)
            pts = " ".join("%.1f,%.1f" % px(*cad(ol.CPoint(i))) for i in range(ol.PointCount()))
            el.append('<polygon points="%s" fill="#e9f2e4" stroke="#3a7d2c" stroke-width="2.5"/>' % pts)
        else:
            (x0, y0), (x1, y1) = cad(d.GetStart()), cad(d.GetEnd())
            a, c = px(x0, y0), px(x1, y1)
            el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="white" stroke="#3a7d2c" '
                      'stroke-width="2"/>' % (min(a[0], c[0]), min(a[1], c[1]), abs(c[0] - a[0]), abs(c[1] - a[1])))
            mx, my = (a[0] + c[0]) / 2, (a[1] + c[1]) / 2
            el.append('<text x="%.1f" y="%.1f" font-size="13" fill="#3a7d2c" text-anchor="middle">wire slot</text>'
                      % (mx, my + 5))
    # landmarks: switch sockets, plugs
    for ref, name in (("SW1", "MX top"), ("SW2", "MX bottom"), ("J2", "speaker"), ("J5", "radar"),
                      ("J9", "SHT"), ("U3", "amp")):
        f = b.FindFootprintByReference(ref)
        bb = f.GetCourtyard(pcbnew.B_CrtYd).BBox()
        (x0, y0), (x1, y1) = cad(pcbnew.VECTOR2I(bb.GetLeft(), bb.GetTop())), cad(pcbnew.VECTOR2I(bb.GetRight(), bb.GetBottom()))
        a, c = px(x0, y0), px(x1, y1)
        el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#f7f7f7" stroke="#999" stroke-dasharray="4 3"/>'
                  % (min(a[0], c[0]), min(a[1], c[1]), abs(c[0] - a[0]), abs(c[1] - a[1])))
        el.append('<text x="%.1f" y="%.1f" font-size="13" fill="#777" text-anchor="middle">%s</text>'
                  % ((a[0] + c[0]) / 2, (a[1] + c[1]) / 2 + 4, name))
    # J1 (5 V in, a JST PH plug since 2026-10-31: its two pins as markers), and J10/J11 if a key wire had to leave the
    # 2 x 8 field
    def hole(x, y, col, r=5.5):
        cx, cy = px(x, y)
        el.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="#000" stroke-width="1"/>' % (cx, cy, r, col))
        return cx, cy
    labels = []
    j1 = b.FindFootprintByReference("J1")
    for p in j1.Pads():
        if p.GetNumber() not in ("1", "2"):         # the plug's mounting pads
            continue
        x, y = cad(p.GetPosition())
        plus = p.GetNetname() == "/VIN_RAW"
        cx, cy = hole(x, y, "#c0392b" if plus else "#222")
        labels.append((cx, cy, "J1 pin 2: +5 V (red)" if plus else "J1 pin 1: GND (black)",
                       "#c0392b" if plus else "#222"))
    led = {"/GLOW_DATA": ("LEDs: data (DIN)", "#0f9fb0"), "+5V": ("LEDs: +5 V", "#c0392b"), "GND": ("LEDs: GND", "#222")}
    for p in b.FindFootprintByReference("J8").Pads():      # the glow LED wires come in from the FRONT
        x, y = cad(p.GetPosition())
        txt, col = led[p.GetNetname()]
        cx, cy = hole(x, y, col, 4.5)
        labels.append((cx, cy, txt, col))
    extra = [ref for ref in ("J10", "J11") if b.FindFootprintByReference(ref)]
    for ref in extra:
        p = list(b.FindFootprintByReference(ref).Pads())[0]
        x, y = cad(p.GetPosition())
        name, h1, grp = SOURCE[p.GetNetname()]
        cx, cy = hole(x, y, COL[grp])
        labels.append((cx, cy, "%s ← touch pad \u201c%s\u201d" % (ref, name), COL[grp]))
    # single-hole labels: radially outside the board edge, next to their hole (no lines across the board)
    used = []
    for cx, cy, txt, col in labels:
        dx, dy = cx - ox, cy - oy
        d = math.hypot(dx, dy) or 1
        r = 28 * S + 28
        tx, ty = ox + dx / d * r, oy + dy / d * r
        while any(abs(ty - u) < 24 and (tx > ox) == (ux > ox) for ux, u in used):
            ty += 26 if dy >= 0 else -26
        used.append((tx, ty))
        el.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="1.5"/>' % (cx, cy, tx, ty, col))
        anchor = "start" if tx >= ox else "end"
        el.append('<text x="%.1f" y="%.1f" font-size="17" fill="%s" font-weight="bold" text-anchor="%s">%s</text>'
                  % (tx + (6 if anchor == "start" else -6), ty + 6, col, anchor, txt))
    # J4 field: mark on the board + enlarged view on the right
    j4 = b.FindFootprintByReference("J4")
    pads = [(p.GetNumber(), p.GetNetname(), cad(p.GetPosition())) for p in j4.Pads()]
    xs = [q[2][0] for q in pads]
    ys = [q[2][1] for q in pads]
    a, c = px(min(xs) - 1, max(ys) + 1), px(max(xs) + 1, min(ys) - 1)
    bx0, by0, bx1, by1 = min(a[0], c[0]), min(a[1], c[1]), max(a[0], c[0]), max(a[1], c[1])
    el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="none" stroke="#b8860b" stroke-width="3"/>'
              % (bx0, by0, bx1 - bx0, by1 - by0))
    for num, net, (x, y) in pads:
        hole(x, y, "#d4a017", 4)
    # enlarged view
    ex, ey = 1110, 560
    cxm, cym = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    def pz(x, y):
        return ex - (x - cxm) * Z, ey - (y - cym) * Z
    zx0, zy0 = pz(max(xs) + 1.2, max(ys) + 1.2)
    zx1, zy1 = pz(min(xs) - 1.2, min(ys) - 1.2)
    el.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" fill="#fbf6e6" stroke="#b8860b" stroke-width="3"/>'
              % (zx0, zy0, zx1 - zx0, zy1 - zy0))
    el.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#b8860b" stroke-width="2" stroke-dasharray="6 4"/>'
              % (bx1, by0, zx0, zy0))
    el.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="#b8860b" stroke-width="2" stroke-dasharray="6 4"/>'
              % (bx1, by1, zx0, zy1))
    el.append('<text x="%.1f" y="%.1f" font-size="20" font-weight="bold" fill="#8a6508" text-anchor="middle">'
              'key-wire field J4 (enlarged)</text>' % ((zx0 + zx1) / 2, zy0 - 150))
    rows = sorted({round(q[2][1], 2) for q in pads}, reverse=True)       # upper row first (CAD y up)
    for num, net, (x, y) in pads:
        cx, cy = pz(x, y)
        upper = round(y, 2) == rows[0]
        if net.startswith("unconnected") or net == "":
            name, grp, txt2 = "—", "none", "empty"
        else:
            name, h1, grp = SOURCE[net]
            txt2 = "\u201c%s\u201d" % name
        col = COL[grp]
        sq = num == "1"
        if sq:
            el.append('<rect x="%.1f" y="%.1f" width="22" height="22" fill="%s" stroke="#000" stroke-width="1.5"/>'
                      % (cx - 11, cy - 11, col))
        else:
            el.append('<circle cx="%.1f" cy="%.1f" r="11" fill="%s" stroke="#000" stroke-width="1.5"/>' % (cx, cy, col))
        el.append('<text x="%.1f" y="%.1f" font-size="12" fill="white" text-anchor="middle" font-weight="bold">%s</text>'
                  % (cx, cy + 4, num))
        ty = cy - 30 if upper else cy + 30
        ang = -60 if upper else 60
        el.append('<text x="%.1f" y="%.1f" font-size="17" fill="%s" font-weight="bold" '
                  'transform="rotate(%d %.1f %.1f)" text-anchor="%s">%s</text>'
                  % (cx, ty, col, ang, cx, ty, "start" if upper else "start", txt2))
    # legend
    ly = 870
    el.append('<text x="30" y="%d" font-size="18" font-weight="bold" fill="#111">Notes</text>' % ly)
    notes = ["“GND”: the touch board has three GND pads — one wire from each, into any GND hole.",
             "“VBUS”: one wire is enough (the second VBUS hole is a spare). Square hole = position 1.",
             *(["Positions 5 and 6 stay empty: the bottom key (“6”) goes to J10, the LED data (“4”) to J11."]
               if extra else []),
             "LEDs: 3 wires from the first LED (bottom right, its DIN, +5 V, GND) through the switch-plate notch, in from the FRONT.",
             "J1 is a plug, not a hole: the 5 V lead from the USB-A plug (VBUS red, GND black) ends in a JST PH housing.",
             "Never connect anything to the touch board's 3V3, VBAT, RST, 1, 2, 12, 13 pads.",
             "Where each named pad sits on the touch board: docs/wiring-touch-board.md (the kit uses the same pads)."]
    for i, n in enumerate(notes):
        el.append('<text x="30" y="%d" font-size="16" fill="#333">%s</text>' % (ly + 28 + i * 25, n))
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" ' \
          'font-family="Segoe UI, Arial, sans-serif">%s</svg>' % (W, H, W, H, "".join(el))
    with open(OUT + ".svg", "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    import pymupdf
    pymupdf.open(OUT + ".svg")[0].get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(OUT + ".png")
    print("wrote", OUT + ".svg/.png")
    for num, net, _ in sorted(pads, key=lambda q: int(q[0])):
        print("  J4-%-2s %-20s %s" % (num, net, SOURCE.get(net, ("empty",))[0]))


if __name__ == "__main__":
    sys.exit(main())
