"""RoomKey KIT v0.7 WIRING (prototype, WIP): every wire as a 3D route (0.05 mm² / AWG30 silicone, Ø0.6) + a wiring table
with cut lengths. Pin assignment = Akte roomkey-einsatz §4 table A (prototype); owned by the RoomKey firmware and
confirmed against it on 2026-10-04 (IO4 data at 3.3 V is marginal for 5 V WS2812B — level shifter if LED 1 flickers).

Coordinates as in insert_lib (front view: x right, y up; d into the wall). Touch-board header from the Waveshare
schematic: odd pins (VBUS, GND, IO16 TXD, IO17 RXD, RST, IO1, IO2, IO3, IO4, IO5, IO6) are the column at x +8.89 in the
FRONT view (the vendor's back view shows it on the left), even pins (VBAT, GND, GND, 3V3, SCL, SDA, USB_P, USB_N, BOOT,
IO8, IO7) at x −8.89; first row at y +9.65 (USB end), pitch 2.54. Pre-soldered headers: the long pins end at d 7.1.
Routes: pin tip → beside the MX housings to the switch-plate cable slot (y +1.5) → rolling U-loop behind it → target.
All routes are drawn at rest; the loop gives the key its 3.4 travel / rocking.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402

L, P, R, V = K.L, K.P, K.R, K.V
WIRE_D = 0.6          # [DS] 0.05 mm² silicone stranded, outer Ø ≈ 0.6 (owner ordered 0.05 mm², 2026-10-03)
RESERVE = 20.0        # [FREE] mm added to every cut length (stripping, solder, slack)
PIN_TIP_D = P.KS["pcb_back"] + 2.5 + 6.0      # pre-soldered 2.54 header: spacer 2.5 + 6 mm pin → d 7.1

ODD = ("VBUS", "GND", "IO16", "IO17", "RST", "IO1", "IO2", "IO3", "IO4", "IO5", "IO6")
EVEN = ("VBAT", "GND2", "GND3", "3V3", "IO19", "IO18", "IO13", "IO12", "BOOT", "IO8", "IO7")


def header_pin(name):
    """(x, y) of a touch-board header pin, front view."""
    y0 = R.TB_HEADER_Y[0]
    if name in ODD:
        return R.TB_HEADER_PITCH_X / 2, y0 - 2.54 * ODD.index(name)
    return -R.TB_HEADER_PITCH_X / 2, y0 - 2.54 * EVEN.index(name)


def targets():
    """end points of the wires at the parts in the box (approximate pin positions, [PHOTO]/[DS])."""
    t = {}
    # MX switches (plate mount, pins at the bottom, d mx_pins): Cherry pin offsets (−3.81, +2.54) and (+2.54, +5.08)
    for i, (x, y) in enumerate(R.MX_SW_POS):
        t[f"MX{i+1}a"] = (x - 3.81, y + 2.54, P.KS["mx_pins"])
        t[f"MX{i+1}b"] = (x + 2.54, y + 5.08, P.KS["mx_pins"])
    # LD2410C header at the outer (−x) edge, pins backwards; TX … VCC along y (order from the owner's photo)
    rx0, rx1, ry0, ry1, _ = P.KIT_RADAR
    c1 = P.KIT_CARRIER_D[1]
    yc = (ry0 + ry1) / 2
    for k, nm in enumerate(R.RADAR_PINS):
        t[f"radar {nm}"] = (rx0 + 1.3, yc + (k - 2) * 2.54, c1 + R.RADAR_T_PINS)
    # MAX98357A on the carrier back, components backwards: 7 pins along its lower edge, speaker pads at the top
    ax, ay = P.KIT_AMP_C
    py = ay - R.AMP_H / 2 + 1.9
    for k, nm in enumerate(R.AMP_PINS):
        t[f"amp {nm}"] = (ax + (k - 3) * 2.54, py, c1 + R.AMP_PCB_T + 0.5)
    sy = ay + R.AMP_H / 2 - R.AMP_SPK_PADS[1]
    t["amp SPK-"] = (ax - R.AMP_SPK_PADS[0] / 2, sy, c1 + R.AMP_PCB_T + 0.5)
    t["amp SPK+"] = (ax + R.AMP_SPK_PADS[0] / 2, sy, c1 + R.AMP_PCB_T + 0.5)
    # INMP441 behind the ledge: 2 columns × 3 at 2.54, columns 7.6 apart; its L/R–GND row points outwards (−x)
    mx, my = P.KIT_MIC_C
    md = P.KIT_MIC_D0 + R.MIC_T
    rows = {"L/R": -2.54, "GND": -2.54, "WS": 0.0, "VDD": 0.0, "SCK": 2.54, "SD": 2.54}   # along x (−x = outwards)
    side = {"SCK": 3.8, "WS": 3.8, "L/R": 3.8, "SD": -3.8, "VDD": -3.8, "GND": -3.8}       # along y
    for nm in ("SCK", "WS", "L/R", "SD", "VDD", "GND"):
        t[f"mic {nm}"] = (mx + rows[nm], my + side[nm], md)
    # speaker: wire tab at the centre of its top short end
    t["speaker"] = ((P.SPK_X0 + P.grille_x()) / 2, 14.0, P.SPK_D0 + R.SPK_W)   # its wires, led to the back edge [approx]
    # lab supply comes in through the open back; splice point on the carrier next to the amp's Vin
    t["splice 5V"] = (ax + 9.0, ay - R.AMP_H / 2 - 1.5, c1 + 2.0)
    t["splice GND"] = (ax + 11.0, ay - R.AMP_H / 2 - 1.5, c1 + 2.0)
    t["lab supply"] = (16.0, -18.0, P.WALL_D + P.DESK_DEPTH + 10.0)
    # SHT31-D in the frame's bottom border (pins on its back)
    for nm, pt in K.D.rh_pins().items():
        t[f"RH {nm}"] = pt
    # glow LEDs (WS2812B-MINI 3535) in the rear-wall windows at the collar corners; pads on their back
    d_led = P.LED_D0 + P.LED_T
    for nm, (x, y) in LED_NAMES.items():
        for pin, (ox, oy) in {"DIN": (-0.9, 0.0), "DOUT": (0.9, 0.0), "5V": (0.0, 0.9), "GND": (0.0, -0.9)}.items():
            t[f"LED {nm} {pin}"] = (x + ox, y + oy, d_led)
    return t


LED_NAMES = {"BR": P.LED_POS[3], "TR": P.LED_POS[1], "TL": P.LED_POS[0], "BL": P.LED_POS[2]}   # chain order
LED_LANE = {"DIN": (12.5, 24.6), "DOUT": (12.5, 24.6), "5V": (13.4, 24.0), "GND": (11.6, 25.0)}   # |x|, |y| outside
                                                    # the rear-wall ring, inside the box (r ≤ 27.6), straight back free
LED_RING_D = 32.0     # the LED wires run round behind the carrier and the amplifier


# (no., from, to, signal, colour, rgb) — "pin:" = touch-board header, everything else = targets()
WIRES = [
    (1, "pin:VBUS", "splice 5V", "5 V → board", "rot", (0.85, 0.1, 0.1)),
    (2, "pin:GND", "splice GND", "GND → board", "schwarz", (0.05, 0.05, 0.05)),
    (3, "pin:BOOT", "MX1a", "KEY1 (Taste oben)", "weiß", (0.95, 0.95, 0.95)),
    (4, "pin:IO6", "MX2a", "KEY2 (Taste unten)", "grau", (0.55, 0.55, 0.55)),
    (5, "pin:GND3", "MX1b", "GND Taste oben", "schwarz", (0.05, 0.05, 0.05)),
    (6, "MX1b", "MX2b", "GND Taste unten (Brücke)", "schwarz", (0.05, 0.05, 0.05)),
    (7, "pin:IO3", "radar TX", "Radar TX → ESP RX", "gelb", (0.95, 0.85, 0.1)),
    (8, "pin:IO5", "radar RX", "ESP TX → Radar RX", "grün", (0.1, 0.65, 0.2)),
    (9, "splice 5V", "radar VCC", "5 V Radar", "rot", (0.85, 0.1, 0.1)),
    (10, "splice GND", "radar GND", "GND Radar", "schwarz", (0.05, 0.05, 0.05)),
    (11, "pin:IO7", "amp BCLK", "I²S BCLK (Verstärker)", "blau", (0.1, 0.3, 0.9)),
    (12, "pin:IO8", "amp LRC", "I²S WS (Verstärker)", "violett", (0.55, 0.2, 0.75)),
    (13, "pin:IO16", "amp DIN", "I²S Daten → Verstärker", "braun", (0.5, 0.3, 0.1)),
    (14, "splice 5V", "amp Vin", "5 V Verstärker", "rot", (0.85, 0.1, 0.1)),
    (15, "splice GND", "amp GND", "GND Verstärker", "schwarz", (0.05, 0.05, 0.05)),
    (16, "amp SPK+", "speaker", "Lautsprecher +", "rot", (0.85, 0.1, 0.1)),
    (17, "amp SPK-", "speaker", "Lautsprecher −", "schwarz", (0.05, 0.05, 0.05)),
    (18, "amp BCLK", "mic SCK", "I²S BCLK (Mikrofon, vom Verstärker weiter)", "blau", (0.1, 0.3, 0.9)),
    (19, "amp LRC", "mic WS", "I²S WS (Mikrofon, vom Verstärker weiter)", "violett", (0.55, 0.2, 0.75)),
    (20, "pin:IO17", "mic SD", "I²S Daten ← Mikrofon", "rosa", (0.95, 0.5, 0.7)),
    (21, "pin:3V3", "mic VDD", "3,3 V Mikrofon", "orange", (1.0, 0.55, 0.1)),
    (22, "mic GND", "mic L/R", "L/R auf GND (linker Kanal)", "schwarz", (0.05, 0.05, 0.05)),
    (23, "splice GND", "mic GND", "GND Mikrofon", "schwarz", (0.05, 0.05, 0.05)),
    (24, "lab supply", "splice 5V", "Labornetzteil +5,0 V", "rot", (0.85, 0.1, 0.1)),
    (25, "lab supply", "splice GND", "Labornetzteil GND", "schwarz", (0.05, 0.05, 0.05)),
    (26, "pin:IO4", "LED BR DIN", "LED-Daten → LED unten rechts", "gelb-grün", (0.6, 0.85, 0.1)),
    (27, "LED BR DOUT", "LED TR DIN", "LED-Daten → oben rechts", "gelb-grün", (0.6, 0.85, 0.1)),
    (28, "LED TR DOUT", "LED TL DIN", "LED-Daten → oben links", "gelb-grün", (0.6, 0.85, 0.1)),
    (29, "LED TL DOUT", "LED BL DIN", "LED-Daten → unten links", "gelb-grün", (0.6, 0.85, 0.1)),
    (30, "splice 5V", "LED BR 5V", "5 V LED unten rechts", "rot", (0.85, 0.1, 0.1)),
    (31, "LED BR 5V", "LED TR 5V", "5 V LED oben rechts", "rot", (0.85, 0.1, 0.1)),
    (32, "LED TR 5V", "LED TL 5V", "5 V LED oben links", "rot", (0.85, 0.1, 0.1)),
    (33, "LED TL 5V", "LED BL 5V", "5 V LED unten links", "rot", (0.85, 0.1, 0.1)),
    (34, "splice GND", "LED BR GND", "GND LED unten rechts", "schwarz", (0.05, 0.05, 0.05)),
    (35, "LED BR GND", "LED TR GND", "GND LED oben rechts", "schwarz", (0.05, 0.05, 0.05)),
    (36, "LED TR GND", "LED TL GND", "GND LED oben links", "schwarz", (0.05, 0.05, 0.05)),
    (37, "LED TL GND", "LED BL GND", "GND LED unten links", "schwarz", (0.05, 0.05, 0.05)),
    (38, "pin:3V3", "RH VIN", "3,3 V Feuchtesensor (2. Draht an Pin 8)", "orange", (1.0, 0.55, 0.1)),
    (39, "pin:GND2", "RH GND", "GND Feuchtesensor", "schwarz", (0.05, 0.05, 0.05)),
    (40, "pin:IO19", "RH SCL", "I²C SCL Feuchtesensor", "hellblau", (0.4, 0.75, 1.0)),
    (41, "pin:IO18", "RH SDA", "I²C SDA Feuchtesensor", "türkis", (0.1, 0.75, 0.7)),
]


def _led_exit(name, pin):
    """the lane point behind an LED's corner, outside the rear-wall ring (wires go straight back from there)."""
    x, y = LED_NAMES[name]
    lx, ly = LED_LANE[pin]
    return (math.copysign(lx, x), math.copysign(ly, y))


def _key_leg(x, y, lane):
    """from a header pin tip, beside the MX housings to the switch-plate cable slot and through it."""
    sx = 1 if x > 0 else -1
    return [(x, y, PIN_TIP_D), (x, y, PIN_TIP_D + 1.5), (sx * 8.4, P.CABLE_Y, 11.0), (lane, P.CABLE_Y, 14.0),
            (lane, P.CABLE_Y, 18.5)]


def _lanes():
    key_wires = [w for w in WIRES if w[1].startswith("pin:")]
    return {w[0]: -5.4 + i * (10.8 / max(len(key_wires) - 1, 1)) for i, w in enumerate(key_wires)}


def route(no, a, b):
    t = targets()
    if a.startswith("pin:"):
        x, y = header_pin(a[4:])
        xs = _lanes()[no]
        pts = _key_leg(x, y, xs)
        tx, ty, td = t[b]
        if b.startswith("RH"):                      # U-loop, down to the flange hole, out under the frame to the board
            hx, hy, _ = P.FRAME_RH_HOLE
            lane = {"VIN": -0.6, "GND": -0.2, "SCL": 0.2, "SDA": 0.6}[b.split()[1]]
            pts += [(xs, P.LOOP_Y[0] + 1.0, 27.0), (xs, P.LOOP_Y[0] + 2.0, 33.0), (xs, P.CABLE_Y - 1.0, 35.5),
                    (hx + lane, hy, 35.5), (hx + lane, hy, 7.35), (hx + lane, ty, 7.35), (tx, ty, td)]
        elif b.startswith("LED"):                   # through the U-loop, round to the first LED's corner, forward to it
            _, nm, pin = b.split()
            ex, ey = _led_exit(nm, pin)
            pts += [(xs, P.LOOP_Y[0] + 1.0, 27.0), (xs, P.LOOP_Y[0] + 2.0, 33.0), (xs, P.CABLE_Y - 1.0, 35.5),
                    (ex, P.CABLE_Y - 1.0, LED_RING_D), (ex, ey, LED_RING_D), (ex, ey, td + 0.6), (tx, ty, td)]
        elif b.startswith("MX"):                    # in front of the carrier, behind the MX bodies (d 20.3)
            wx = tx + (2.0 if tx >= 0 else -2.0)     # detour clear of the MX centre post (Ø4 below the housing)
            pts += [(xs, P.CABLE_Y, 22.0), (wx, (P.CABLE_Y + ty) / 2, 22.0), (tx, ty, 22.0), (tx, ty, td)]
        elif b.startswith("mic"):                   # round the hub post (−13.2, 4.0) to the module back
            pts += [(xs, P.CABLE_Y, 22.5), (xs, -1.0, 22.5), (-16.5, -1.0, 22.5), (tx, ty, 22.5), (tx, ty, td)]
        else:                                       # the rolling U-loop behind the switch plate, then behind the carrier
            pts += [(xs, P.LOOP_Y[0] + 1.0, 27.0), (xs, P.LOOP_Y[0] + 2.0, 33.0), (xs, P.CABLE_Y - 1.0, 35.5),
                    (tx, ty, max(35.5, td + 1.5)), (tx, ty, td)]
    else:
        p0, p1 = t[a], t[b]
        if b.startswith("LED"):                               # LED chain / bus: back from the corner, round, forward
            _, nb, pb = b.split()
            e1 = _led_exit(nb, pb)
            if a.startswith("LED"):
                _, na, pa = a.split()
                e0 = _led_exit(na, pa)
                pts = [p0, (e0[0], e0[1], p0[2] + 0.6), (e0[0], e0[1], LED_RING_D)]
                if e0[0] != e1[0] and e0[1] != e1[1]:
                    pts.append((e1[0], e0[1], LED_RING_D))
            else:
                pts = [p0, (p0[0], p0[1], LED_RING_D), (e1[0], p0[1], LED_RING_D)]
            pts += [(e1[0], e1[1], LED_RING_D), (e1[0], e1[1], p1[2] + 0.6), p1]
        elif a.startswith("MX") and b.startswith("MX"):        # stay in front of the carrier, behind the MX bodies
            pts = [p0, (p0[0], p0[1], 22.0), (p1[0], p1[1], 22.0), p1]
        elif b.startswith("mic") and p0[2] > 25.0:            # from behind the carrier: pass it beside its radar area
            dd = max(p0[2], p1[2]) + 2.0
            pts = [p0, (p0[0], p0[1], dd), (p1[0], p1[1] + 1.2, dd), (p1[0], p1[1] + 1.2, 24.0), (p1[0], p1[1], 24.0), p1]
        else:
            dd = max(p0[2], p1[2]) + 2.0
            pts = [p0, (p0[0], p0[1], dd), (p1[0], p1[1], dd), p1]
    clean = [pts[0]]
    for p in pts[1:]:
        if math.dist(p, clean[-1]) > 0.05:
            clean.append(p)
    return clean


def wire_solid(pts):
    segs = []
    r = WIRE_D / 2
    for p, q in zip(pts[:-1], pts[1:]):
        a, b = V(p[0], p[1], -p[2]), V(q[0], q[1], -q[2])
        d = b.sub(a)
        if d.Length < 1e-3:
            continue
        segs.append(L.Part.makeCylinder(r, d.Length, a, d))
    for p in pts[1:-1]:
        segs.append(L.Part.makeSphere(r, V(p[0], p[1], -p[2])))
    s = segs[0]
    return s.fuse(segs[1:]) if len(segs) > 1 else s


def length(pts):
    return sum(math.dist(p, q) for p, q in zip(pts[:-1], pts[1:]))


def table_md():
    rows = ["| Nr | von | nach | Signal | Farbe (Vorschlag) | Zuschnitt ca. |", "|---|---|---|---|---|---|"]
    for no, a, b, sig, col, _ in WIRES:
        pts = route(no, a, b)
        cut_mm = math.ceil((length(pts) + RESERVE) / 5.0) * 5
        rows.append(f"| {no} | {a.replace('pin:', 'Board ')} | {b.replace('pin:', 'Board ')} | {sig} | {col} | {cut_mm} mm |")
    return "\n".join(rows)


def build_wiring():
    """wire solids + collision report against the kit's fixed parts + the wiring table (Markdown)."""
    import json
    one = ((0.0, 0.0),)
    fixed = {"practice box": K.D.wall_block(one), "chassis (kit)": K.kit_chassis("S"), "back carrier": K.back_carrier(),
             "frame 1-gang": K.D.frame_2x(one, with_rh=True), "plate": L.fuse(list(L.plate_parts("S"))),
             "switch plate": L.switch_plate(), "collar": L.collar()}
    refs = L.ref_bodies("S")
    for k in ("MX switch 1", "MX switch 2", "speaker 2030"):
        fixed[k] = refs[k]
    kr = K.kit_refs()
    for k in ("LD2410C", "MAX98357A", "INMP441"):
        fixed[k] = kr[k]
    wires, hits = {}, []
    for no, a, b, sig, col, rgb in WIRES:
        w = wire_solid(route(no, a, b))
        wires[no] = w
        for nm, shp in fixed.items():
            v = L.overlap(w, shp)
            if v > 0.05:
                hits.append((no, sig, nm, round(v, 2)))
    print(f"  wires: {len(wires)}, overlaps with parts > 0.05 mm³: {len(hits)} (ends on pins/pads are expected)")
    for h in hits:
        print("    TOUCH", h)
    with open(os.path.join(L.OUT, "kit-v0.7_wiring.json"), "w", encoding="utf-8") as f:
        json.dump({"overlaps": hits, "table": table_md()}, f, indent=1, ensure_ascii=False)
    return wires, hits
