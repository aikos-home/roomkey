"""RoomKey kit, PCB version (v0.11, prototype, WIP): every wire and cable as a 3D route, a wiring table with cut lengths
and a collision check of every wire against the parts (endpoints excepted).

The hub PCB does the "wiring" of the self-wired kit on its copper: mic, amplifier, the 5 V/3.3 V nodes and both MX
switches (Kailh hot-swap sockets) need no wires. What is left are the connections to parts that sit elsewhere:
  key (touch board H1) → hub J4 (16 solder holes), through the slots and the rolling U-loop behind the hub;
  speaker → hub J2 (its own PicoBlade plug); radar → hub J5 (JST-SH 5-pin cable); glow LEDs → hub J8 (3 solder holes)
  and the LED chain; the humidity sensor in the housing's bottom wall → hub J9 (JST-SH 4-pin pigtail); 5 V from the
  slim USB-A plug in the charger → hub J1 (0.5 mm², JST PH). v0.12: the radar sits in the hub plane (wires on its
  cut-short header pins), the sensor and the USB plug where the 64 × 64 plug housing puts them (insert_params §8).
Hub pad positions: KiCad board hardware/pcb/roomkey-hub (2026-10-09 00:28 state, read with pcbnew), kit coordinates.
Coordinates as in insert_lib (front view: x right, y up; d into the wall). All routes are drawn at rest.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402

L, P, R, V = K.L, K.P, K.R, K.V
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
J1 = {"GND": (10.0, -2.75), "5V": (12.0, -2.75)}                                      # v0.12: P.PLUG_J1 (rev D)
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


CORNER = {"TL": 0, "TR": 1, "BL": 2, "BR": 3}      # corner → index in P.LED_POS
LED_CHAIN = ("BR", "TR", "TL", "BL")            # the firmware order, both builds
LED_IN_SIDE = {"BR": "outer", "TR": "inner", "TL": "outer", "BL": "inner"}
# v0.11 LED holder: each LED's legs are on its two x sides — VDD + DOUT on one, DIN + VSS on the other. The DIN/VSS side
# faces where the chain comes in (J8 / the previous LED), so DIN and DOUT need no detour; one power wire per LED crosses
# to the other side in the cross channel at the seat's inner y end.
SLOT_D = P.KS["plate_front"] + 0.15             # wire level in the seat recess (d 15.3–15.8; wire Ø0.6 stands 0.15 proud)
OVER_D = P.KS["plate_front"] - 0.4              # wire level over the ear's front face
LED_LANE_D = {"DATA": 17.15, "5V": 17.75, "GND": 18.35}   # in the back channel (plate back 16.8, walls to 18.4)


def _led_xy(c):
    x, y = P.LED_POS[CORNER[c]]
    return x, y, (1 if x > 0 else -1), (1 if y > 0 else -1)


def led_joint(c, pin):
    """the wire joint on an LED leg (pin DIN / DOUT / 5V / GND), in its leg slot."""
    x, y, sx, _ = _led_xy(c)
    bside = LED_IN_SIDE[c]
    side = bside if pin in ("DIN", "GND") else ("inner" if bside == "outer" else "outer")
    dx = (P.LED_W / 2 + 0.25) * (sx if side == "outer" else -sx)
    return (x + dx, y + (0.875 if pin in ("DIN", "5V") else -0.875), P.KS["plate_front"])


def led_pad(c, pin):
    return led_joint(c, pin)


def led_to_exit(c, pin, exit_):
    """joint → its exit: "inner" (the wire hole, then the back channel), "top" (over the ear to the top lane outside the
    collar wall) or "side" (out of the outer slot, for the feed from J8)."""
    x, y, sx, sy = _led_xy(c)
    j = led_joint(c, pin)
    pts = [j, (j[0], j[1], SLOT_D)]
    side = "outer" if (j[0] - x) * sx > 0 else "inner"
    want = "inner" if exit_ == "inner" else "outer"
    if side != want:                                       # round the seat's inner y end
        yc = y - sy * (P.LED_W / 2 + P.LED_SEAT_FIT + 0.4)
        xo = x + (P.LED_W / 2 + 0.25) * (sx if want == "outer" else -sx)
        pts += [(j[0], yc, SLOT_D), (xo, yc, SLOT_D), (xo, j[1], SLOT_D)]
    if exit_ == "inner":
        hx, hy, _ = P.LED_HOLE
        pts += [(sx * hx, sy * hy, SLOT_D)]
    elif exit_ == "top":
        xo, yo = pts[-1][0], pts[-1][1]
        pts += [(xo, yo, OVER_D), (xo + sx * 0.1, y + sy * (P.LED_W / 2 + 0.4), OVER_D), (sx * 12.6, sy * 25.6, OVER_D)]
    else:
        pts += [(sx * 15.9, pts[-1][1], SLOT_D)]
    return pts


def _side_lane(sx, y_from, y_to, dd):
    """the back channel along one side, past the switch-plate post (±10.5, −7.9) on its inner side."""
    hx = P.LED_HOLE[0]
    lane = [(hx, -17.0), (hx, -10.3), (7.75, -10.0), (7.75, -5.8), (hx, -5.5), (hx, 17.0)]   # jog inside the channel gap
    if y_from > y_to:
        lane = lane[::-1]
    return [(sx * x, y, dd) for (x, y) in lane]


def led_feed_route(pin):
    """J8 (3 holes beside the bottom-right LED; wire in from the hub's front, soldered on its back) → round the ear's
    outer edge → the outer leg slot → the joint."""
    jx, jy = J8[pin]
    t = led_to_exit("BR", {"DATA": "DIN", "5V": "5V", "GND": "GND"}[pin], "side")[::-1]
    return [(jx, jy, HUB_BACK + 0.5), (jx, jy, 19.5), (15.9, jy, 18.5), (15.9, t[0][1], SLOT_D)] + t


def led_hop_route(a, b, pin):
    """LED a → LED b (DOUT → DIN, 5V → 5V, GND → GND). Right and left: through the wire holes and along the back
    channel. Top (TR → TL): over the ears and outside the collar wall."""
    pa_, pb_ = ("DOUT", "DIN") if pin == "DATA" else (pin, pin)
    dd = LED_LANE_D[pin]
    if a[0] == "T" and b[0] == "T":
        ta, tb = led_to_exit(a, pa_, "top"), led_to_exit(b, pb_, "top")
        return ta + [(ta[-1][0], ta[-1][1], dd), (tb[-1][0], tb[-1][1], dd)] + tb[::-1]
    ta, tb = led_to_exit(a, pa_, "inner"), led_to_exit(b, pb_, "inner")
    sx = 1 if ta[-1][0] > 0 else -1
    return (ta + [(ta[-1][0], ta[-1][1], dd)] + _side_lane(sx, ta[-1][1], tb[-1][1], dd) +
            [(tb[-1][0], tb[-1][1], dd)] + tb[::-1])


def radar_pin(nm):
    """v0.12: the radar in the hub plane, its header pins cut short: soldered 0.5 below the cut tip."""
    rx0, _, ry0, ry1, f = P.HUB_RADAR
    yc = (ry0 + ry1) / 2
    k = R.RADAR_PINS.index(nm)
    return (rx0 + 1.3, yc + (k - 2) * 2.54, f + R.RADAR_T + P.RADAR_PINS_CUT - 0.5)


def rh_pin(nm):
    return K.rh_pins()[nm]


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


def radar_route(nm):
    """J5 plug (JST-SH, wires leave it backwards) → just behind it (in front of G2's charger sleeve, d 30) over to the
    radar's header → forward onto the cut-short pins."""
    jx, jy = J5[nm]
    tx, ty, td = radar_pin(nm)
    k = R.RADAR_PINS.index(nm)
    dd = 28.1 + 0.25 * k
    return [(jx, jy, PLUG_TOP), (jx, jy, dd), (tx + 1.5, ty, dd), (tx + 1.5, ty, td), (tx, ty, td)]


def speaker_route(pin):
    """the speaker's own leads leave its tab at the top end (y 15.0–15.5, d 13.6–17.0) and run back in the tab slot of the
    +y cradle rib (y 15.2–15.9, open to the back) → over the hub's back → J2 plug."""
    jx, jy = J2[pin]
    ox = {"SPK+": -0.5, "SPK-": 0.5}[pin]
    return [(17.7 + ox, 15.4, 16.5), (17.7 + ox, 15.55, 17.2), (17.7 + ox, 15.55, 28.0), (jx, jy, 28.0), (jx, jy, PLUG_TOP)]


def rh_route(nm):
    """v0.12: the humidity sensor (in G2's bottom wall, pins on its top face at its back edge) → up off the pins, back
    through the hub's bottom notch, over the hub's parts (in front of G2's charger sleeve, d 30) → down into J9."""
    tx, ty, td = rh_pin(nm)
    k = R.RH_PINS.index(nm)
    ny = P.plug_rh()["y1"] + 0.6
    dz = 28.1 + 0.4 * k
    jx, jy = J9[{"VIN": "3V3", "GND": "GND", "SCL": "SCL", "SDA": "SDA"}[nm]]
    return [(tx, ty, td), (tx, ny, td + 0.5), (tx, ny, dz), (jx, jy, dz), (jx, jy, PLUG_TOP)]


def supply_route(pin):
    """v0.12: 2 × AWG 24 from the slim USB-A plug's solder cups (plug_cups; they face the room) forward to just behind the
    hub, then along the lane the hub keeps free of parts (y −6 … −0.5) into J1's mouth on its −x side (side-entry PH, rev
    D; 5 V on the upper pin). The left cup (5 V) rises to the upper level, the right one (GND) stays low: they never cross."""
    dp = P.plug_depths("pcb")
    cx, cy = P.plug_cups()[pin]
    jx, jy, jl, jw, jt, _ = P.PLUG_J1
    yp = jy + (1.0 if pin == "5V" else -1.0)
    de = HUB_BACK + jt / 2
    return [(cx, cy, dp["usb0"] + 1.0), (cx, cy, de + 0.8), (cx + 1.5, yp, de), (jx - jl / 2 + 1.0, yp, de)]


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
                  ("SHT31-D", "hub")))
        n += 1
    for pin, sig, col, rgb in (("5V", "5 V vom USB-Netzteil", "rot", (0.85, 0.1, 0.1)), ("GND", "GND vom USB-Netzteil", "schwarz", (0.05, 0.05, 0.05))):
        w.append((n, "USB-Stecker", f"Hub J1 {pin}", sig, col, rgb, lambda pin=pin: supply_route(pin), PIGTAIL_D,
                  ("hub", "USB plug")))
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
