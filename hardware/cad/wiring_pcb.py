"""RoomKey kit, PCB version (v0.11, prototype, WIP): every wire and cable as a 3D route, a wiring table with cut lengths
and a collision check of every wire against the parts (endpoints excepted).

The hub PCB does the "wiring" of the self-wired kit on its copper: mic, amplifier, the 5 V/3.3 V nodes and both MX
switches (Kailh hot-swap sockets) need no wires. What is left are the connections to parts that sit elsewhere:
  key (touch board H1) → hub J4 (16 solder holes), through the slots and the rolling U-loop behind the hub;
  speaker → hub J2 (its own PicoBlade plug); radar → hub J5 (JST-SH 5-pin cable); glow LEDs → hub J8 (3 solder holes)
  and the LED chain; SHT31-D in the frame → hub J9 (JST-SH 4-pin pigtail); 5 V supply → hub J1 (0.5 mm² pigtail).
Hub pad positions: KiCad board hardware/pcb/roomkey-hub (2026-10-09 00:28 state, read with pcbnew), kit coordinates.
Coordinates as in insert_lib (front view: x right, y up; d into the wall). All routes are drawn at rest.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402

L, P, R, D, V = K.L, K.P, K.R, K.D, K.V
WIRE_D = 0.6           # [DS] 0.05 mm² silicone stranded, outer Ø ≈ 0.6 (owner ordered 0.05 mm², 2026-10-03)
PIGTAIL_D = 1.6        # [DS] 0.5 mm² H05V-K / silicone, outer Ø ≈ 1.6 (5 V supply into J1)
RESERVE = 20.0         # [FREE] mm added to every cut length (stripping, solder, slack)
PIN_TIP_D = P.KS["pcb_back"] + 2.5 + 6.0       # touch board: pre-soldered 2.54 header, spacer 2.5 + 6 mm pin → d 7.1
HUB_BACK = P.HUB_PCB_D0 + P.HUB_PCB_STEP_TOP    # 21.81
PLUG_TOP = HUB_BACK + 5.8                       # [DS approx] SH / PicoBlade vertical header 4.25–4.4 + plug ≈ 1.5

ODD = ("VBUS", "GND", "IO16", "IO17", "RST", "IO1", "IO2", "IO3", "IO4", "IO5", "IO6")
EVEN = ("VBAT", "GND2", "GND3", "3V3", "IO19", "IO18", "IO13", "IO12", "BOOT", "IO8", "IO7")

# hub J4: 2 × 8 solder holes, 1.27 pitch (pin: touch-board pad, x, y); wires come in from the BACK (the U-loop)
J4 = {1: ("VBUS", 4.44, 5.72), 2: ("VBUS", 4.44, 6.98), 3: ("GND", 3.17, 5.72), 4: ("BOOT", 3.17, 6.98),
      5: ("IO6", 1.91, 5.72), 6: ("IO4", 1.91, 6.98), 7: ("IO5", 0.64, 5.72), 8: ("IO3", 0.64, 6.98),
      9: ("IO18", -0.64, 5.72), 10: ("IO19", -0.64, 6.98), 11: ("GND2", -1.91, 5.72), 12: ("IO16", -1.91, 6.98),
      13: ("IO7", -3.17, 5.72), 14: ("GND3", -3.17, 6.98), 15: ("IO8", -4.44, 5.72), 16: ("IO17", -4.44, 6.98)}
SIG = {"VBUS": ("5 V → Touch-Board (VBUS)", "rot", (0.85, 0.1, 0.1)), "GND": ("GND", "schwarz", (0.05, 0.05, 0.05)),
       "GND2": ("GND", "schwarz", (0.05, 0.05, 0.05)), "GND3": ("GND", "schwarz", (0.05, 0.05, 0.05)),
       "BOOT": ("Taste oben (IO9)", "weiß", (0.95, 0.95, 0.95)), "IO6": ("Taste unten (IO6)", "grau", (0.55, 0.55, 0.55)),
       "IO4": ("LED-Daten (IO4)", "gelb-grün", (0.6, 0.85, 0.1)), "IO5": ("ESP → Radar RX (IO5)", "grün", (0.1, 0.65, 0.2)),
       "IO3": ("Radar TX → ESP (IO3)", "gelb", (0.95, 0.85, 0.1)), "IO18": ("I²C SDA (IO18)", "türkis", (0.1, 0.75, 0.7)),
       "IO19": ("I²C SCL (IO19)", "hellblau", (0.4, 0.75, 1.0)), "IO16": ("I²S Daten → Verstärker (IO16)", "braun", (0.5, 0.3, 0.1)),
       "IO7": ("I²S BCLK (IO7)", "blau", (0.1, 0.3, 0.9)), "IO8": ("I²S WS (IO8)", "violett", (0.55, 0.2, 0.75)),
       "IO17": ("I²S Daten ← Mikrofon (IO17)", "rosa", (0.95, 0.5, 0.7))}
J1 = {"GND": (-18.0, 13.0), "5V": (-18.0, 17.6)}                                     # solder holes, 0.5 mm² pigtail
J2 = {"SPK+": (11.5, 11.88), "SPK-": (11.5, 13.12)}                                  # PicoBlade 1.25 vertical, wire exits
J5 = {"TX": (-13.5, 8.5), "RX": (-13.5, 9.5), "OUT": (-13.5, 10.5), "GND": (-13.5, 11.5), "VCC": (-13.5, 12.5)}   # JST-SH 1.0
J8 = {"GND": (15.3, -21.77), "5V": (15.3, -20.5), "DATA": (15.3, -19.23)}           # solder holes, wires from the FRONT
J9 = {"GND": (-13.25, -20.0), "3V3": (-12.25, -20.0), "SDA": (-11.25, -20.0), "SCL": (-10.25, -20.0)}   # JST-SH 1.0


def header_pin(name):
    """(x, y) of a touch-board header pin, front view (Waveshare schematic; see the discrete kit's wiring)."""
    y0 = R.TB_HEADER_Y[0]
    if name in ODD:
        return R.TB_HEADER_PITCH_X / 2, y0 - 2.54 * ODD.index(name)
    return -R.TB_HEADER_PITCH_X / 2, y0 - 2.54 * EVEN.index(name)


LED_CHAIN = ("BR", "TR", "TL", "BL")   # v0.11 corner boards: the firmware order (hub schematic) in both builds; with the
# boards' rotations DOUT and the next DIN sit on the same side (PCB thread, 2026-10-12)


def led_pad(name, pin):
    """a corner board's back pad (its solder joint, d 15.5); DIN/DOUT/5V/GND (5V and GND take 2 wires each)."""
    return P.led_board_pad(name, pin)


def radar_pin(nm):
    rx0, _, ry0, ry1, _ = P.KIT_RADAR
    c1 = P.KIT_CARRIER_D[1] + P.KIT_RADAR_RAISE
    yc = (ry0 + ry1) / 2
    k = R.RADAR_PINS.index(nm)
    return (rx0 + 1.3, yc + (k - 2) * 2.54, c1 + R.RADAR_T_PINS - 1.0)        # soldered 1 mm below the pin tip


def rh_pin(nm):
    return D.rh_pins()[nm]


# ------------------------------------------------------------------ routes
def key_route(no):
    """touch-board pin tip → beside the MX housings → key-back + switch-plate + hub slots (y 1.5) → U-loop up → J4."""
    pin, hx, hy = J4[no]
    x, y = header_pin(pin)
    lane = -6.0 + (no - 1) * 0.8                                  # 16 lanes across the 12.8 slot
    sx = 1 if x > 0 else -1
    loop = [(lane, P.CABLE_Y, 25.0), (lane, P.CABLE_Y + 0.8, 27.4), (0.5 * (lane + hx), P.CABLE_Y + 2.5, 28.6),
            (hx, hy - 0.6, 27.6), (hx, hy, 25.5), (hx, hy, HUB_BACK)]
    return [(x, y, PIN_TIP_D), (x, y, PIN_TIP_D + 1.5), (sx * 8.4, P.CABLE_Y, 11.0), (lane, P.CABLE_Y, 14.0),
            (lane, P.CABLE_Y, 18.5), (lane, P.CABLE_Y, 22.5)] + loop


def led_feed_route(pin):
    """J8 (3 holes beside the bottom-right board, wires from the hub's front) → forward beside the collar wall → across
    the board's back (d 16, in the corner window / switch-plate notch) → its pad."""
    jx, jy = J8[pin]
    px, py, pd = led_pad("BR", {"DATA": "DIN", "5V": "5V", "GND": "GND"}[pin])
    return [(jx, jy, HUB_BACK + 0.5), (jx, jy, 16.0), (px, py, 16.0), (px, py, pd)]


LED_LANE_D = {"DATA": 18.3, "5V": 18.9, "GND": 19.5}   # [FREE] hop depths: behind the switch plate and the ledge (17.8),
                                                       # in front of the hub (20.3)
LED_IN = (10.6, 20.3)          # [FREE] |x|, |y| where the hop wires pass the switch-plate notch, inside the ledge
LED_SIDE = [(10.4, 17.5), (10.4, -4.8), (13.0, -5.5), (13.0, -10.3), (10.4, -11.0)]   # [FREE] side lane top → bottom,
#        |x| between the MX housings (7.8) and the hub posts at (13.2, 4/20); the jog passes the switch-plate post
#        (10.5, −7.9) on its outside (pcb r 2.0, discrete anchor post r 1.2)
LED_TOP_Y = 25.3               # [FREE] the top hop runs outside the collar wall (MX1 fills the well up to y 22.8)


def led_hop_route(a, b, pin):
    """LED board a → board b (DOUT → DIN, 5V → 5V, GND → GND). Right and left: in through the notch, along the side
    lane behind the switch plate. Top: out of the window, round the collar wall."""
    pa = led_pad(a, "DOUT" if pin == "DATA" else pin)
    pb = led_pad(b, "DIN" if pin == "DATA" else pin)
    dd = LED_LANE_D[pin]
    sx = 1 if pa[0] > 0 else -1
    if a[0] == "T" and b[0] == "T":                                 # TR → TL over the top
        return [pa, (pa[0], pa[1], 16.0), (pa[0], LED_TOP_Y, 16.0), (pa[0], LED_TOP_Y, dd), (pb[0], LED_TOP_Y, dd),
                (pb[0], LED_TOP_Y, 16.0), (pb[0], pb[1], 16.0), pb]
    ya, yb = (1 if pa[1] > 0 else -1), (1 if pb[1] > 0 else -1)
    lane = [(sx * x, y) for (x, y) in LED_SIDE]
    if ya < 0:                                                      # bottom → top: walk the lane upwards
        lane = lane[::-1]
    ia, ib = (sx * LED_IN[0], ya * LED_IN[1]), (sx * LED_IN[0], yb * LED_IN[1])
    return ([pa, (pa[0], pa[1], 16.0), (ia[0], ia[1], 16.0), (ia[0], ia[1], dd)] + [(x, y, dd) for (x, y) in lane] +
            [(ib[0], ib[1], dd), (ib[0], ib[1], 16.0), (pb[0], pb[1], 16.0), pb])


def radar_route(nm):
    """J5 plug (JST-SH, wires leave it backwards) → behind the radar → solder joints on the module's header pins."""
    jx, jy = J5[nm]
    tx, ty, td = radar_pin(nm)
    k = R.RADAR_PINS.index(nm)
    dd = 40.0 + 0.7 * k
    return [(jx, jy, PLUG_TOP), (jx, jy, dd), (tx + 1.5, ty, dd), (tx + 1.5, ty, td), (tx, ty, td)]


def speaker_route(pin):
    """the speaker's own leads leave its tab at the top end (y 15.0–15.5, d 13.6–17.0) and run back in the tab slot of the
    +y cradle rib (y 15.2–15.9, open to the back) → over the hub's back → J2 plug."""
    jx, jy = J2[pin]
    ox = {"SPK+": -0.5, "SPK-": 0.5}[pin]
    return [(17.7 + ox, 15.4, 16.5), (17.7 + ox, 15.55, 17.2), (17.7 + ox, 15.55, 28.0), (jx, jy, 28.0), (jx, jy, PLUG_TOP)]


def rh_route(nm):
    """SHT31-D pins (in the frame's bottom border) → under the frame to the flange hole (0, −27) → back to d 18–20 →
    along the box wall outside the collar wall to the bottom-left → back past the hub's rim (r 27.7 → box r 29.5) → J9."""
    tx, ty, td = rh_pin(nm)
    hx, hy, _ = P.FRAME_RH_HOLE
    lane = {"VIN": -0.6, "GND": -0.2, "SCL": 0.2, "SDA": 0.6}[nm]
    dd = {"VIN": 18.1, "GND": 18.7, "SCL": 19.3, "SDA": 19.9}[nm] - 0.1
    j = {"VIN": "3V3", "GND": "GND", "SCL": "SCL", "SDA": "SDA"}[nm]
    jx, jy = J9[j]
    t = 1.5 * lane                                     # tangential spread where the bundle passes the hub's rim
    cx, cy = -20.25 - 0.7 * t, -20.35 + 0.7 * t        # r ≈ 28.7
    return [(tx, ty, td), (hx + lane, ty, 7.35), (hx + lane, hy, 7.35), (hx + lane, hy, dd),
            (-8.0, -26.3, dd), (-14.6, -24.1, dd), (cx, cy, dd), (cx, cy, 29.0), (jx, jy - 0.4, 29.0), (jx, jy, PLUG_TOP)]


def supply_route(pin):
    """5 V pigtail (0.5 mm²) from the lab supply through the practice box's open back → J1."""
    jx, jy = J1[pin]
    return [(jx, jy, HUB_BACK), (jx, jy, 34.0), (jx, jy, P.WALL_D + P.DESK_DEPTH + 10.0)]


# (no, label from, label to, signal, colour, rgb, route builder, diameter, exempt bodies)
def wires():
    w = []
    for no in range(1, 17):
        pin = J4[no][0]
        sig, col, rgb = SIG[pin]
        w.append((no, f"Touch-Board {pin}", f"Hub J4-{no}", sig, col, rgb, lambda no=no: key_route(no), WIRE_D,
                  ("touch board", "key shell", "cable loop", "hub")))
    n = 17
    for pin, sig, col, rgb in (("DATA", "LED-Daten", "gelb-grün", (0.6, 0.85, 0.1)), ("5V", "5 V LEDs", "rot", (0.85, 0.1, 0.1)),
                               ("GND", "GND LEDs", "schwarz", (0.05, 0.05, 0.05))):
        w.append((n, f"Hub J8 {pin}", "LED unten rechts", sig, col, rgb, lambda pin=pin: led_feed_route(pin), WIRE_D,
                  ("hub", "LED 4")))
        n += 1
    for a, b, la, lb in (("BR", "TR", "LED 4", "LED 2"), ("TR", "TL", "LED 2", "LED 1"), ("TL", "BL", "LED 1", "LED 3")):
        for pin, sig, col, rgb in (("DATA", "LED-Daten", "gelb-grün", (0.6, 0.85, 0.1)), ("5V", "5 V LEDs", "rot", (0.85, 0.1, 0.1)),
                                   ("GND", "GND LEDs", "schwarz", (0.05, 0.05, 0.05))):
            w.append((n, f"LED {a}", f"LED {b}", sig, col, rgb, lambda a=a, b=b, pin=pin: led_hop_route(a, b, pin), WIRE_D,
                      (la, lb)))
            n += 1
    for nm, sig, col, rgb in (("TX", "Radar TX → ESP", "gelb", (0.95, 0.85, 0.1)), ("RX", "ESP → Radar RX", "grün", (0.1, 0.65, 0.2)),
                              ("OUT", "Radar OUT (nicht benutzt)", "weiß", (0.95, 0.95, 0.95)),
                              ("GND", "GND Radar", "schwarz", (0.05, 0.05, 0.05)), ("VCC", "5 V Radar", "rot", (0.85, 0.1, 0.1))):
        w.append((n, f"Hub J5 {nm}", f"Radar {nm}", sig, col, rgb, lambda nm=nm: radar_route(nm), WIRE_D,
                  ("hub", "LD2410C header")))
        n += 1
    for pin, sig, col, rgb in (("SPK+", "Lautsprecher +", "rot", (0.85, 0.1, 0.1)), ("SPK-", "Lautsprecher −", "schwarz", (0.05, 0.05, 0.05))):
        w.append((n, "Lautsprecher", f"Hub J2 {pin}", sig, col, rgb, lambda pin=pin: speaker_route(pin), WIRE_D,
                  ("speaker 2030", "hub")))
        n += 1
    for nm, sig, col, rgb in (("VIN", "3,3 V Feuchtesensor", "orange", (1.0, 0.55, 0.1)), ("GND", "GND Feuchtesensor", "schwarz", (0.05, 0.05, 0.05)),
                              ("SCL", "I²C SCL", "hellblau", (0.4, 0.75, 1.0)), ("SDA", "I²C SDA", "türkis", (0.1, 0.75, 0.7))):
        w.append((n, f"SHT31-D {nm}", f"Hub J9 {nm if nm != 'VIN' else '3V3'}", sig, col, rgb, lambda nm=nm: rh_route(nm), WIRE_D,
                  ("SHT31-D", "hub", "frame 1-gang")))
        n += 1
    for pin, sig, col, rgb in (("5V", "Labornetzteil +5,0 V", "rot", (0.85, 0.1, 0.1)), ("GND", "Labornetzteil GND", "schwarz", (0.05, 0.05, 0.05))):
        w.append((n, "Labornetzteil", f"Hub J1 {pin}", sig, col, rgb, lambda pin=pin: supply_route(pin), PIGTAIL_D,
                  ("hub", "practice box")))
        n += 1
    return w


def wire_solid(pts, dia=WIRE_D):
    segs = []
    r = dia / 2
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


def cut_len(pts):
    return math.ceil((length(pts) + RESERVE) / 5.0) * 5


def check(bodies=None, verbose=True):
    """every wire against every body (its own endpoints' bodies excepted); returns {wire no: {body: mm³}}."""
    bodies = bodies or K.kit_bodies()
    hits = {}
    for no, a, b, sig, col, rgb, rt, dia, ex in wires():
        s = wire_solid(rt(), dia)
        for k, body in bodies.items():
            if k in ex or not s.BoundBox.intersect(body.BoundBox):
                continue
            v = s.common(body).Volume
            if v > 0.002:
                bb = s.common(body).BoundBox
                hits.setdefault(no, {})[k] = (round(v, 3), "x %.1f..%.1f y %.1f..%.1f d %.1f..%.1f" % (
                    bb.XMin, bb.XMax, bb.YMin, bb.YMax, -bb.ZMax, -bb.ZMin))
    if verbose:
        print(f"  wiring (PCB version): {len(wires())} wires, {len(hits)} with hits")
        for no, h in hits.items():
            for k, (v, where) in h.items():
                print(f"    wire {no:2d} ↔ {k}: {v} mm³ at {where}")
    return hits


def table_md():
    rows = ["| Nr | von | nach | Signal | Farbe (Vorschlag) | Zuschnitt ca. |", "|---|---|---|---|---|---|"]
    for no, a, b, sig, col, rgb, rt, dia, ex in wires():
        rows.append(f"| {no} | {a} | {b} | {sig} | {col} | {cut_len(rt())} mm |")
    return "\n".join(rows)
