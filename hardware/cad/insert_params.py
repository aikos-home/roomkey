"""RoomKey front stack + plug-in housing (WIP, AI-assisted, not certified) — every dimension of the RoomKey.

    python3 hardware/cad/insert_params.py          # validate
    python3 hardware/cad/insert_params.py --tbd    # every [TBD] value and what to measure

RoomKey is built ONLY as a plug-in device (owner 2026-10-31, "Nur Steckdose"): the front stack (key on two MX switches,
plate 55 × 55 with its glow rim, collar, switch plate with the LED holder, chassis) and the electronics (hub PCB or
self-wired modules) sit in a 64 × 64 housing that plugs into a SCHUKO socket. 230 V stays inside an unmodified, certified
plug-in USB charger; RoomKey itself takes 5 V SELV. Sections: 2–4 front stack, 5 power / acoustics / RF, 7 kit
(electronics), 8 the plug-in housing. The flush-mounted wall insert of v0.2–v0.11 (box, frame, electrician topologies)
is gone; the git history keeps it, and the names of a few datums (WALL_D, FRAME_OPEN, "insert") come from it.

Tags: [DS] datasheet / norm / vendor drawing (source in SOURCES) · [MEAS] measured on the real part ·
      [FREE] design choice · [TBD] placeholder or assumption until measured (listed by --tbd).
Coordinates: front view, origin = plate centre on the plate FRONT face; x right, y up;
      d = depth behind the plate front (+). CAD maps (x, y, d) -> (X, Y, Z = -d): +Z points into the room.
Nothing here is certified. Nothing of the RoomKey is ever connected to 230 V.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import roomkey_params as R  # noqa: E402

VARIANTS = ("S",)     # v0.11: ONE RoomKey (owner 2026-10-08: "Es soll nur eine Art von RoomKey geben"). The code keeps the
                      # key "S" internally; no Variant L (light switch) any more, the plate is fixed (PLATE_FIXED)
VERSION = "0.12"     # v0.12 (2026-10-31): plug-in only — 64 × 64 housing, flange 59.2, radar in the hub plane

SOURCES = {
    "cherry":   "Cherry MX1A datasheet, datasheet.octopart.com/MX1A-11NW-Cherry-datasheet-34676.pdf",
    "waveshare": "Waveshare ESP32-C6-Touch-LCD-1.47 drawing, waveshare.com/img/devkit/ESP32-C6-Touch-LCD-1.47/ESP32-C6-Touch-LCD-1.47-details-size.jpg",
    "ws_sch":   "Waveshare ESP32-C6-Touch-LCD-1.47 schematic, files.waveshare.com/wiki/ESP32-C6-Touch-LCD-1.47/ESP32-C6-Touch-LCD-1.47-Schematic.pdf: "
                "header IO1/IO2 (LCD SPI + TF lines, 10k), IO3 (10k pull-up), IO4 (10k pull-up), IO5/IO6 (IMU INT1/2), IO7, IO8, "
                "IO16/17 (UART0; 499 Ω R2 in series on IO16), SDA/SCL (10k), ESP_RST, VBAT, USB; "
                "BOOT = IO9 (10k + 100 nF); antenna matching C25 2.7 pF, C2 1 pF, C1 n.f.; PWR LED + charger STAT LED",
    "esp32c6":  "Espressif ESP32-C6 datasheet v1.5 (documentation.espressif.com/esp32-c6_datasheet_en.pdf): V_IH 0.75 × VDD, "
                "TX 354 mA peak, strapping pins MTMS (GPIO4), MTDI (GPIO5), GPIO8, GPIO9, GPIO15 (Tab. 3-1); MTDI = GPIO5 has "
                "no pull at reset ('floating'), GPIO8 floats at reset, GPIO6 weak pull-up at reset",
    "spk":      "Waveshare 2030 speaker outline, waveshare.com/img/devkit/accessories/8ohm-2w-speaker/8ohm-2W-Speaker-details-size.jpg",
    "din49073": "DIN 49073 device box: opening Ø60, screw spacing 60 (via de.wikipedia.org/wiki/Gerätedose, Kaiser data sheets)",
    "kaiser1555": "Kaiser 1555-04 datasheet (66 mm deep, 4 screw domes; listed as discontinued), assets.kaiser-elektro.de",
    "kaiser1068": "Kaiser 1068-02 Electronic-Dose datasheet (Stand 2026-08-02): length 149, depth 67, screw spacing 60, 4 domes, "
                  "2 device screws (ONE device position + an electronics chamber), partition supplied 'für unterschiedliche "
                  "Spannungsarten', IP2X; listed under 'Auslaufprodukte' on kaiser-elektro.de; a distributor lists 147 × 67 × 67 "
                  "and 'Einbauöffnung Ø60' — front geometry of chamber 2 unverified (Q11); "
                  "assets.kaiser-elektro.de/datasheets/de_DE/1/1068-02 (EAN 4013456120310).pdf",
    "es75":     "Eltako data sheet ES75-12..24V UC (eltako.com/fileadmin/downloads/de/datenblatt/Datenblatt_ES75-12_24VUC.pdf, "
                "read 2026-09-30): 'für Leuchteneinbau', 1 NO 10 A/250 V, 85 × 40 × 28, integrated transformer 'galvanische "
                "Trennung ... SELV nach EN 60669-2-2', external control 12..24 V UC 10 mA at 24 V or its internal voltage, SELV side "
                "= 4-pole STOCKO MKF13264 plug (one plug supplied), 230 V side plug-in terminals ≤ 2.5 mm², permanent 230 V supply, "
                "standby 1 W, max 10 A fuse, −20..+50 °C, command min 20 ms / pause 300 ms, loads: incandescent/halogen 500 W, "
                "fluorescent KVG — NO LED rating in this sheet; several distributor pages (elektromax24.de, hardy-schmitz.de, "
                "elektro-wandelt.de) list '230V-LED-Lampen bis 200W' → conflicting, Q4b",
    "esr61np":  "Eltako catalogue ch. 11 p. 11-12 / 11-15: ESR61NP-230V+UC, A1-A2 'galvanisch getrennt', 6 mm / 4000 V to the contact",
    "esr61np_led": "Eltako catalogue ch. 11: ESR61NP-230V+UC LED lamps up to 600 W, 230 V local control input (⊕), 45 × 45 × 18",
    "es61uc":   "Eltako ES61-UC datasheet + manual 61100501 (control ↔ contact 3 mm / 2000 V)",
    "snt61":    "Eltako SNT61-230V/12V DC-0,5A datasheet: 45 × 45 × 33, 6 W, Class II, 0.1 W standby, −10..+50 °C, 'Stabilisierte "
                "Ausgangsspannung ±1 %', 'kurzschlussfest, Überlast- und Übertemperatursicherung durch Abschalten mit automatischem "
                "Zuschalten' (a hub short would switch it off → eFuse on the hub branch; the shut-off threshold is NOT published → "
                "Q4f); the current catalogue lists the 10 W variant (0.83 A, short-term overload 160–200 %) — ≤ 15 W, so "
                "§9.1 is met without a source fuse; "
                "eltako.com/fileadmin/downloads/de/datenblatt/Datenblatt_SNT61-230V_12V_DC_05A.pdf; catalogue ch. 17 p. 17-7: standards "
                "EN 60950 / EN 55022 / EN 61000-6-2, Schutzklasse II, SPD type 2/3 'ist zu installieren'",
    "finder38": "Finder 38.51 relay interface module: 6.2 mm DIN-rail module (≈ 6.2 × 88 × 76), reinforced insulation coil ↔ "
                "contact 6 kV, 8 mm creepage/clearance, 4 kV AC; DC coil versions with polarity/free-wheel protection in the "
                "module (check the ordering code)",
    "b3fs":     "Omron B3FS data sheet (omronfs.omron.com/en_US/ecb/products/pdf/en-b3fs.pdf, Cat. A113-E1-06): B3FS-1002P flat "
                "type, height 3.1 ± 0.2, body 6.0 × 6.3, lead span 8.0, plunger Ø3, PCB pads 9.6 × 5.9 outer / 6.4 inner, OF 1.47 "
                "± 0.49 N, RF ≥ 0.49 N, PT 0.25 +0.2/−0.1, 300 k operations, 1–50 mA at 3–24 V DC, silver contacts, bounce ≤ 5 ms, "
                "dielectric 250 V AC, general tolerance ±0.4",
    "wago221":  "WAGO 221-412 data sheet (wago.com/221-412): 13.1 × 8.3 × 18.6 mm, 2 conductors 0.2–4 mm², 450 V, strip 11 mm",
    "traco":    "Traco TSR 1-2450: 6.5–36 V in, 5 V 1 A, SIP-3 11.7 × 7.5 × 10.1, max capacitive load 1000 µF, eff. up to 94 % at "
                "full load (lower at light load)",
    "sk6812":   "SK6812 MINI datasheet: 3.5 × 3.5 × 1.45 mm, ~12 mA per channel",
    "iec60664": "IEC 60664-1 Tab. F.2/F.5: 230 V, OVC III (4 kV), PD2, material group III",
    "vde0100":  "DIN VDE 0100-410 (411.3.4 RCD for lighting circuits in dwellings; 414.4 SELV: protective separation, 414.4.2 "
                "arrangement of SELV conductors — insulated for the highest voltage present or separated/sheathed), -443/-534 "
                "(SPD), -600 (initial verification), -510 (marking); NAV §13 (registered installer); DIN 18015-2 (minimum "
                "number of sockets per room)",
    "din18015": "DIN 18015-3 installation zones; switch 105 cm, socket 30 cm (downloads.jung.de/public/MKT/Installationszone/JUNG_Installationszonen.pdf)",
    "ld2410":   "Hi-Link HLK-LD2410C manual (manualslib 3299997); LD2410B 7 × 35 (openelab.io LD2410B vs C)",
    "max98357": "Maxim MAX98357A datasheet: 1.4 W into 8 Ω at 5 V and 1 % THD (1.8 W at 10 %)",
    "mics":     "INMP441 (InvenSense, obsolete), ICS-43434 (TDK, not recommended for new designs), SPH0645LM4H-B (Knowles, "
                "I²S, 3.5 × 2.65, bottom port) — whichever is purchasable goes on the 8 × 8 carrier",
}

# =====================================================================================================
# 1. FRONT OPENING AND FLANGE (v0.12: the plug housing's skin border and carrier tunnel frame the plate — section 8)
# =====================================================================================================
PLATE = R.ROCKER_W                 # 55.0 [MEAS, FROZEN]
HALF = PLATE / 2
WALL_D = 9.0          # [FREE] the flange's back face (d); the name stays from the flush-box design (its wall plane)
FRAME_OPEN = 55.6     # [FREE] the opening round the plate (0.3 per side): the skin's border and the carrier's tunnel
FRAME_TUNNEL_MARGIN = 0.1  # [FREE] min gap between any fixed part and the tunnel wall (the rims locate at this gap)
FLANGE_T = 1.2        # [FREE] the chassis flange
FLANGE_HALF = 29.6    # [FREE] v0.12: inside the 64 × 64 skin (its inner face 29.92 at the flange − 0.3); the
                      #        carrier's tunnel end stops it, G2's side walls press it forward
RIM_T = 1.0           # [FREE] locating rims: thickness
LOC_RIM_SPAN = (4.5, 15.0)   # [FREE] each rim runs |along| 4.5..15 on all four sides (8 rims)
LOC_RIM_D0 = 3.5      # [FREE] rims stand from the flange to d 3.5, inside the carrier's tunnel, behind the plate skin
RIM_OUT = FRAME_OPEN / 2 - FRAME_TUNNEL_MARGIN      # rim outer face (27.7)


def loc_rims():
    """(x0, x1, y0, y1) of the 8 frame-locating rims."""
    a, b = LOC_RIM_SPAN
    o, i = RIM_OUT, RIM_OUT - RIM_T
    out = []
    for s in (-1, 1):
        for t in (-1, 1):
            out.append((min(s * i, s * o), max(s * i, s * o), min(t * a, t * b), max(t * a, t * b)))   # left/right
            out.append((min(t * a, t * b), max(t * a, t * b), min(s * i, s * o), max(s * i, s * o)))   # top/bottom
    return out


# =====================================================================================================
# 2. KEY MODULE (shared) — depths from roomkey_params.key_stack()
# =====================================================================================================
KS = R.key_stack()
KEY_W, KEY_H, KEY_R = R.KEY_W, R.KEY_H, R.KEY_R
CUT_W, CUT_H = R.CUT_W, R.CUT_H
CUT_R = KEY_R + R.KEY_GAP
WELL_IN_X = KEY_W / 2 + R.KEY_WELL_CLEAR       # 13.675: collar inner face
WELL_IN_Y = KEY_H / 2 + R.KEY_WELL_CLEAR       # 23.65
WELL_R = KEY_R + R.KEY_WELL_CLEAR
KEY_SKIRT_Y = KEY_H / 2 - KEY_R                # 16.5: the key skirt covers the straight long sides only (free pitch)
COLLAR_T = 1.2        # [FREE] translucent light-guide collar wall (natural PETG, frosted)
COLLAR_IN_EXTRA = 0.15   # [FIT] v0.10.3: the collar's inner face only is set back this much per side (outer unchanged — it
                         #        fits the seat perfectly): the key scraped its inner walls (owner 2026-10-08) → key ↔ collar
                         #        0.25 + 0.15 = 0.40/side; the catch nubs still overlap the inner face by 0.15
COLLAR_D0, COLLAR_D1 = 3.6, 12.5   # [FREE] collar front face (lights the plate's glow rim) / back face (LEDs)
COLLAR_OUT_X, COLLAR_OUT_Y = WELL_IN_X + COLLAR_T, WELL_IN_Y + COLLAR_T
COLLAR_OUT_R = 5.0    # [FREE] outer corner radius smaller than the inner one (8.35 would be parallel) → the collar is 2.6 thick
                      #        along the corner diagonals, where the LEDs sit; the deck seat follows the same contour
COLLAR_FIT = 0.1      # [FREE] collar ↔ deck opening. v0.8: NOT glued (the plate holds it; it must come out for key service)
COLLAR_RELIEF = (0.4, 2.4)   # [FREE] the collar's inner face at the SHORT sides (incl. corner arcs) is set back 0.4 over its
                             #        first 2.4 mm: room for the key ends under wobble (±KEY_WOBBLE_DEG) and an end press [TBD rig]
# v0.8 KEY CATCH (owner, 2026-10-04: the assembled v0.7 rocker key simply fell out — the forks clamped nothing). The key is
# now CAPTIVE: a rigid nub on each side skirt runs in a groove in the collar's inner face. The groove is open to the collar's
# back face (the collar slides over the mounted key from the front) and closed towards the room: pressing and rocking stay
# free, pulling stops at the groove's front wall. The plate keeps the collar in (it overlaps the collar's front face).
# Assembly: key onto the stems → collar over the key → plate. Service: plate off → collar out → key off.
KEY_CATCH_Y, KEY_CATCH_YC = 6.0, 0.0   # [FREE] nub length along y, centre y (between the stems: rocking moves it deeper)
KEY_CATCH_D = 1.0      # [FREE] nub height along d, at the skirt's free end
KEY_CATCH_X = 0.55     # [FREE] nub protrusion beyond the skirt's outer face → catch overlap with the collar = X − KEY_WELL_CLEAR
KEY_CATCH_GAP = 0.45   # [FREE] nub front ↔ groove front wall at rest; > the 0.37 a ±1.5° roll lifts the nub (the MX top stop
                       #        defines rest, not the catch)
GROOVE_CLEAR = (0.25, 0.5)  # [FIT] groove ↔ nub in x (bottom; v0.10.3: 0.1 → 0.25 with the collar's inner face, the key
                            #        scraped) and in y
REAR_WALL = 1.2       # [FREE] chassis well wall behind the collar (d COLLAR_D1 → ledge)
SWP_CLEAR = 0.2       # [FREE] switch plate ↔ well wall
LEDGE = 1.0           # [FREE] ledge under the switch plate
SWP_SCREWS = ()      # v0.10: the switch plate is GLUED onto the ledge (2–3 dots CA; owner 2026-10-07) — the two screw bosses
                     #        hung 4–5 mm free over the switch plate when the rear chassis part prints front down. Was
                     #        ((-10.5, 1.5), (10.5, 1.5)), M2 × 4 countersunk from the front into ledge bosses
SWP_SCREW_L = 4.0     # [FREE]
SWP_BOSS_D, SWP_BOSS_H = 4.6, 3.8   # [FREE] boss 3.8 deep: pilot hole 3.0, 0.8 floor
M2_CSK_D, M2_CSK_H = 3.8, 1.2    # [DS] DIN 965 M2 head
CABLE_ORDER = ("VBUS", "GND", "BOOT KEY1", "IO6 KEY2", "IO4 LED", "IO3 PLATE_SENSE", "IO5 RELAY_DRIVE", "GND", "IO7 BCLK",
               "GND", "IO8 WS", "IO16 DOUT", "GND", "IO17 DIN", "3V3")   # [FREE] ground next to the I²S lines; no I²C.
#              v0.6 rocker: the two MX are read separately → IO6 (IMU INT2 on the board: INT2 must stay disabled)
#              v1 [TBD, Akte §4 B, 2026-10-03]: + SDA, SCL (header pins 12/10) for the light sensor on the mic carrier and the
#              RH/T sensor + an I²C port expander on the hub → 17 wires. NOT in the CAD yet: at 17 × 0.8 the central slot
#              (14.4) would leave only 0.19 to the header slots → v1 needs AWG32 (0.6) or the I²C pair through a header slot.
CABLE_N, CABLE_WIRE_D = len(CABLE_ORDER), 0.8   # [FREE] 15 × AWG30 silicone stranded, laid flat
CABLE_W = CABLE_N * CABLE_WIRE_D   # 12.0
CABLE_Y = 1.5         # [FREE] cable runs between the MX housings at y = +1.5
CABLE_SLOT = (CABLE_W + 0.8, 2.6)   # [FREE] slots in key back and switch plate; 2.6 wide (owner 2026-10-03: "weniger eng",
                                    #        room for thicker prototype wires / jumper leads, was 1.4)
HEADER_SLOT_W = 3.0   # [FREE] owner 2026-10-03: room for pins or wires going straight back from the header holes → a slot through
                      #        the key back under each pin column (x ±8.89 ± 1.5, the old channel strips), first pin − ... last pin
HEADER_SLOT_Y = (R.TB_HEADER_Y[1] - 0.85, R.TB_HEADER_Y[0] + 1.25)   # −16.6 … +10.9: 0.9 web to the bottom screw's countersink
LOOP_R = 4.0          # [FREE] rolling U-loop bend radius behind the MX bodies (5 × wire Ø)
LOOP_Y = (CABLE_Y - 2 * LOOP_R - CABLE_WIRE_D, CABLE_Y + CABLE_WIRE_D / 2 + 0.4)   # loop spans −y from the moving leg
LOOP_D0 = 24.0        # [FREE] loop region starts behind the MX pins (23.6)
LOOP_D1 = 36.5        # [FREE] incl. 2 mm roll + slack
LOOP_LIFE = 250_000   # [FREE] key presses the cable must survive (30 years × 20/day = 219 k); desk-rig test target
ANCHOR = (-11.5, 11.5, -8.4, -7.4, 24.0, 25.2)   # [FREE] bar that clamps the fixed leg (x0,x1,y0,y1,d0,d1) — v0.11: gone
ANCHOR_POSTS = ((-10.5, -7.9), (10.5, -7.9))     # [FREE] posts carrying the anchor bar — v0.10: on the SWITCH PLATE's back
                                                 #        (they grow up from it in print; on the chassis they hung in the air)
KEY_TRAVEL = 3.4     # [FREE] v0.6: the key stops on 4 STOP BOSSES landing on the switch plate (centre press), before MX
                     #        bottom-out (4.0); both switches are past their actuation point (2.0 ± 0.6) by then. v0.9 rigid
                     #        key: the bosses take the press off the stems (a keycap bottoming on the plate, not on the switch)
CH_SPLIT = ("v0.10: the chassis is THREE prints, all front down, no supports (owner 2026-10-07: supports broke it): 1 FRONT "
            "(d < flange front: deck, pockets, rims, mic tube), 2 FLANGE (flange + webs/ribs behind it to the collar's back "
            "face, + the speaker duct to its roof), 3 REAR (rear wall behind the collar, ledge, speaker cradle, hub posts). "
            "Glue: 1→2 with the collar through both openings as the jig; 2→3 on two pins + the web tops")
CH_PIN = (1.2, 2.0, 0.15)      # [FREE] v0.10 chassis pins 2→3: Ø, length, radial play in the hole. v0.10.1: play 0.1 → 0.15
CH_PIN_LEAD = 0.25             #        and a 45° lead-in at the hole mouth + a 0.3 point on the pin: the holes open on part 3's
                               #        BED face, the first layers' squish closed the Ø1.4 mouths (owner 2026-10-08: no fit)
CH_PIN_POS = ((5.7, 26.25), (-5.7, -26.25))   # [FREE] diagonal pair 53 apart, on the island ribs above / below the collar:
                                              #        the only free spots (corners: the plate's tactile switches; +x: the
                                              #        speaker; on the axes: the box's screw domes; box radius 28.5)
CH_PIN_BLOCK = (1.5, 1.2)      # [FREE] pin block half-size x, y (hole walls 0.8 / 0.5 — fine at a 0.2 nozzle)
STOP_X = (11.25, R.KEY_W / 2 - R.KEY_WALL)   # [FREE] |x| of the stop bosses: outside the board screws' heads (≤ 10.9) and
                     #        inside the key wall; they land on the switch plate inside its corner arcs
STOP_W_Y = 2.0       # [FREE] boss length in y
STOP_YS = (18.5, -16.5)   # [FREE] y of the boss pairs (v0.6 rocker geometry, kept: inside the plate's corner arcs)
STOP_END_D = KS["plate_front"] - KEY_TRAVEL   # boss end at rest (lands on the switch plate front after KEY_TRAVEL)


def wobble_travel(deg):
    """deepest straight travel at which the key can still wobble ±deg before a stop boss lands (the wobble check runs there)."""
    ym = (R.MX_SW_POS[0][1] + R.MX_SW_POS[1][1]) / 2
    lever = max(max(abs(y - ym) for y in STOP_YS) + STOP_W_Y / 2, STOP_X[1])
    return KEY_TRAVEL - lever * math.sin(math.radians(deg)) - 0.05
KEY_WOBBLE_DEG = 1.5  # [TBD] tilt of the key on its two stems under an eccentric press (MX stem play ≈ 1–2°); CAD checks ±1.5°
KEY_BACK_CHANNEL = 0.4   # [FREE] recess in the key back's inner face where the 14 wires run (1.2 of the 1.6 wall left)
KEY_PULL_MIN = 10.0   # [FREE] target key pull-off force (stem friction, coupon v1 row E); the key is not a small part
KEY_BOARD_BACK_H = 3.2   # [TBD] component height on the touch board's back (envelope from the drawing); cable routes above it

# =====================================================================================================
# 3. PLATE (shared) and DECK
# =====================================================================================================
PLATE_T = 2.0         # [FREE] front skin: ivory face + black core (AMS colour change) → opaque; glow rim translucent
PLATE_FACE_T = 0.6    # [TBD] ivory layer over black: 0.6 / 0.9 / 1.2 → coupon v1 row H next to the real frame
PLATE_CORNER_R = 2.0  # [TBD] the owner's rocker corners ("rounded") — measure (Q7)
GLOW_RIM_W = 0.8      # [FREE] translucent rim of the plate around the key opening (natural PETG, full skin thickness,
                      #        co-printed with AMS), lit from the collar 1.6 mm behind it → the glow ring, visible at any angle
# v0.12 SPLIT PLATE (resin thread 2026-10-31; the owner chose "gedruckt + angeklebt"): the visible FACE (d 0 … PLATE_T with the
# perforation, the glow rim and the key opening; flat back, the speaker mesh lies flat on it) is cast in resin; all behind it
# is a printed BACK (PETG) glued on: skirts, top lip, snap lips and rest pads joined by one glue flange. The skirts' outer
# faces are the datum the glue jig aligns.
PLATE_BACK = (0.6, 1.0, 2.2)   # [FREE] glue flange thickness; clearance to the perforation fields (+ mesh margin) and to
                               # the glow rim / its light path from the collar; flange width inward from the skirts' outer face
PLATE_SKIRT_T = 1.2   # [FREE] skirt zone: inner face at HALF − 1.2 = 26.3; the wall is 0.8, set back 0.4 from the face edge
SKIRT_D = 4.2         # [FREE] skirts end at d 4.2: they overlap the deck edges (d 3.5..5.0) by 0.7 and LOCATE the plate
SKIRT_GAP = (3.5, 16.0)   # [FREE] every skirt (and the top lip) is open at |along| 3.5..16 → room for the 8 frame rims
# Retention: TOP edge = rigid drawer lip (3 segments: |x| ≤ 3.5 and 16..26.3), hooked behind the deck's rigid top edge by
# a 0.7 mm upward shift; BOTTOM edge = two snap lips at the corners that clip over two flexible deck tongues.
LIP_D0, LIP_D1 = 5.0, 5.6   # [FREE] top lip: catch face on the deck back face (d 5.0)
LIP_IN = 0.7          # [FREE] lips project 0.7 inward → 0.6 overlap (short overhang, prints unsupported; coupon v1 row D)
SNAP_X = (22.5, 25.5)       # [FREE] |x| extent of the two bottom snap lips
SNAP_D0, SNAP_D1 = 6.5, 7.1  # [FREE] bottom snap lip: catch face on the tongue's back face (d 6.5)
SNAP_CHAMFER = 0.45   # [FREE] 45° lead-in on the snap lip's back-inner edge
TONGUE_CHAMFER = 0.25  # [FREE] 45° lead-in on the tongue's front-outer edge (0.55 left for the first layer); sum 0.70 ≥ overlap + 0.1
TONGUE_X = (14.0, 26.2)     # [FREE] bottom deck tongues: slot root |x| → free end at the deck side edge (free 11.55 from the slot's round end; the root
                            #        stays 2.5 clear of the collar seat's corner)
TONGUE_W = 0.8        # [FREE] in-plane width (the tongue flexes in +y, in the layer plane → strong in FDM)
TONGUE_D1 = 6.5       # [FREE] the tongue is the deck (d 3.5..5.0) + a rib to d 6.5: soft in y (snap), stiff in d (pull)
TONGUE_SLOT = 1.3     # [FREE] free slot inboard of each tongue; its root end is a full radius (no sharp corner)
MAT_E = 2000.0        # [TBD] MPa, PETG/ASA printed along the lines (datasheets 1.8–2.2 GPa)
MAT_SIGMA_Y = 45.0    # [TBD] MPa, yield (PETG ≈ 50, ASA ≈ 40–45)
MAT_EPS_SNAP = 0.015  # [FREE] allowed strain for a rarely operated snap (≈ 60 % of the ~2.4 % yield strain)
PULL_MIN = 3.0        # [FREE] min forward pull per tongue before yield (N); the frame covers the plate edges
DECK_HALF_X = 26.2    # [FREE] deck outline (skirt inner faces at 26.3 → 0.1 clearance)
DECK_HALF_Y = 26.2    # [FREE] the lips overlap the deck / tongue by LIP_IN − (26.3 − 26.2) = 0.6
DECK_R = 0.5          # [FREE] deck corner radius (keeps the tongue ends square under the snap lips)
SNAP_RELIEF = (21.5, 27.3, 24.0, 27.8)   # [FREE] flange windows at the bottom corners (|x| from..to, |y| from..to): room
                                        #        for the snap lips at full press
DECK_D0, DECK_D1 = 3.5, 5.0   # [FREE] deck front / back
S_PLATE_FIXED = True   # v0.11 (owner 2026-10-08: "Nur MX, Blende fest"): the plate is fixed on 4 rest pads, never a button
PLATE_FIXED = S_PLATE_FIXED
WING_SECTION = (20.7, -19.5)   # section planes through the wings (x, y) for the drawings (v0.10: the B3FS positions)
S_REST_PADS = ((-10.0, -25.4), (10.0, -25.4), (-10.0, 25.4), (10.0, 25.4))   # [FREE] Ø2.4 pads, 1.5 high (only if fixed)

PERF_D, PERF_PITCH, PERF_COLS, PERF_ROWS = 1.0, 1.6, 4, 13   # [FREE] north star: 4 × 13 fine holes per wing (render Ø~0.7,
                                                             #        FDM minimum Ø1.0 — coupon v1 row F)
WING_X = (CUT_W / 2 + HALF) / 2                   # 20.96 wing centre
PERF_XS = [WING_X + (j - (PERF_COLS - 1) / 2) * PERF_PITCH for j in range(PERF_COLS)]
PERF_YS = [(k - (PERF_ROWS - 1) / 2) * PERF_PITCH for k in range(PERF_ROWS)]
MESH_T = 0.2          # [FREE] black acoustic mesh in a 0.2 recess of the plate back behind both strips (look, dust)
MESH_MARGIN = 0.5     # [FREE] recess = strip ± 0.5

# =====================================================================================================
# 4. FLOATING-PLATE SWITCHES, PRELOAD, MIC, LEDS, SPEAKER, HUB
# =====================================================================================================
SW_POS = ()           # v0.11: no plate switches (fixed plate). v0.2–v0.10: 4 × Omron B3FS-1002P at (±20.7, ±19.5)
SW_W, SW_TOTAL_H, SW_BODY_H, SW_PLUNGER_D = 6.0, 3.1, 2.6, 3.0   # [DS b3fs] body 6.0 × 6.3, 3.1 ± 0.2 incl. plunger, body 2.6
SW_BODY_Y = 6.3       # [DS b3fs]
SW_TERM_W = 8.0       # [DS b3fs] gull-wing lead span (x)
SW_OF, SW_OF_TOL, SW_RF = 1.47, 0.49, 0.49   # [DS b3fs] B3FS-1002P
SW_PT, SW_PT_MIN, SW_PT_MAX = 0.25, 0.15, 0.45   # [DS b3fs]
SW_TRAVEL_TOTAL = 0.45   # [TBD] plunger travel to bottom-out (not published; assumed = PT max) → coupon v1 row D
SW_H_TOL = 0.2        # [DS b3fs] height 3.1 ± 0.2
SW_LIFE = 300_000     # [DS b3fs] operations at OF 1.47 N
SW_MAX_FORCE = 20.0   # [TBD] static load a bottomed B3FS survives — not published; coupon v1 row D (30 N on ONE cell, 1 min)
ABUSE_FORCE = 30.0    # [FREE] palm slap on the plate; worst case on ONE switch (diagonal pivots engage only one)
SW_RATING = (3.0, 24.0, 0.001, 0.050)   # [DS b3fs] V min, V max, I min, I max (resistive, silver contacts → ≥ 1 mA)
CARRIER = (8.8, 6.4, 0.8)   # [FREE] FR4 carrier per switch (x, y, t): B3FS on front pads; feet at ±4.0, pads cut to ±4.4 (Omron land
                            #        pattern to ±4.8 [DS] — the carrier cannot be wider: pocket wall ↔ skirt), so the toe fillet is
                            #        only 0.4 → check the joints on coupon row D. FLAT back → rests on the flange front face (the
                            #        datum), glue dot. Wires: 2 plated holes 2.0 mm off-centre towards the plate centre, 1.2 apart
                            #        along y, under the switch body (≥ 0.7 from the pads, front side tented), soldered from the back
CARRIER_WIRE_SLOT = (1.6, 2.6)   # [FREE] slot (x, y) in the flange behind the 2 wire holes: the joints sit in it, the carrier rests on
                                 #        the flange around it; offset inwards so the wires drop into the box, not onto its rim
CARRIER_WIRE_OFF = 2.0           # [FREE] wire holes / slot offset from the switch centre towards the plate centre (x and y)
SOLDER_H = 0.0        # [FREE] v0.4: SMD switch → nothing on the carrier's back
NUB_GAP = 0.30        # [FREE] nominal nub ↔ plunger gap at rest (coupon v1 row D: 0.2 / 0.3 / 0.4)
NUB_H_MIN = 0.2       # [FREE] smallest printable nub; NUB_H absorbs up to (NUB_H − NUB_H_MIN) of a smaller WALL_D
GAP_CHAIN = (        # ± contributions to the nub gap (mm): the chain from the flange datum to the nub tip
    ("plate: nub tip ↔ lip catch faces (print Z)", 0.10, "[FREE est., Bambu at 0.10 layers]"),
    ("chassis: deck back / tongue back ↔ flange front (print Z)", 0.10, "[FREE est.]"),
    ("FR4 carrier 0.8 ± 10 %", 0.08, "[DS IPC-4101 class]"),
    ("B3FS height 3.1 ± 0.2", 0.20, "[DS b3fs]"),
    ("solder under the SMD switch + glue line under the carrier", 0.05, "[FREE]"),
    ("carrier seat printed as a bridge (sag)", 0.05, "[FREE est., 9 mm bridge at 0.10 layers; one-sided in reality: sag makes "
                                                      "the gap smaller — the shims correct it]"),
    ("plate seating on lips / snaps", 0.05, "[FREE]"),
)
SHIM_STEP = 0.05      # [FREE] per-switch correction: 0.05 mm polyimide tape under the carrier (less gap) or sand the nub (more)
SEAT_ALLOW = 0.1      # [FREE] extra travel allowance at the stop (glue line / carrier seating compliance)

PAD_POS = ((-21.0, -12.9), (21.0, 12.9), (21.0, -12.9))   # [FREE] 3 soft preload pads on the deck (anti-rattle), not seals
PAD_SIZE = (5.0, 3.0)  # [FREE] pad footprint (x, y)
PAD_H = 2.5           # [FREE] free height; sits in a 0.5 pocket in the deck front → 0.5 compressed at rest
PAD_POCKET = 0.5
PAD_CLD40 = 10.0      # [TBD] kPa, compression stress at 40 % of an extra-soft PU foam (range 5–20) — foam data sheet
PLATE_MASS_G = 4.5    # [FREE] plate ≈ 3.6 cm³ PETG

MIC_PORT = (-PERF_XS[1], PERF_YS[-1])   # [FREE] left strip: hole at x −20.16, top row (y +9.6)
MIC_ON_PLATE = True   # [FREE] v0.3: the mic carrier is bonded to the plate back with a PSA ring → no gasket, moves with it
MIC_PSA_T = 0.1       # [FREE] die-cut PSA ring (port sealed)
MIC_FACE_D = PLATE_T + MIC_PSA_T
MIC_POCKET_CLEAR = 0.35  # [FREE] chassis pocket around the moving carrier (xy: plate location ±0.1 + tilt); depth = carrier back + travel + 0.3
MIC_WIRES = ("5 × AWG32 silicone (3V3, GND, SCK, WS, SD; L/R tied low on the carrier), leaving the carrier sideways at its "
             "bottom edge in a flat S-loop into the wire well, 30 mm service loop in the box")   # [FREE]
MIC_WELL = 3.0        # [FREE] square wire well beside the mic pocket (bottom-outer corner), walled to the flange, open into the
                      #        box; sealed with a removable foam plug (it connects the front volume to the box)
_Q = math.sqrt(0.5)
_LI = (WELL_IN_X - WELL_R + WELL_R * _Q, WELL_IN_Y - WELL_R + WELL_R * _Q)                          # inner corner point (45°)
_LO = (COLLAR_OUT_X - COLLAR_OUT_R + COLLAR_OUT_R * _Q, COLLAR_OUT_Y - COLLAR_OUT_R + COLLAR_OUT_R * _Q)   # outer corner point
LED_WALL = math.hypot(_LO[0] - _LI[0], _LO[1] - _LI[1])     # collar wall along the corner diagonal (≈ 2.6)
LED_POS = tuple((sx * (_LI[0] + _LO[0]) / 2, sy * (_LI[1] + _LO[1]) / 2)
                for sy in (1, -1) for sx in (-1, 1))   # [FREE] 4 × SK6812 MINI centred on the thick collar corners, facing forward
LED_W, LED_T, LED_CARRIER_T = 3.5, 2.0, 0.8    # [DS] owner ordered 50 × WS2812B-MINI 3535 (led-stuebchen, 2026-10-03): 3.5 × 3.5 ×
                                                #      2.0 (vendor; the SK6812 MINI was 1.45) / [FREE] carrier (v1; the kit
                                                #      prototype solders wires straight to the pads, ≈ 0.4)
LED_D0 = COLLAR_D1 + 0.1
# v0.11 LED holder IN THE SWITCH PLATE (owner 2026-10-31: "In der Schalterplatte", "Erst löten, dann einkleben"; the
# corner boards were dropped 12.10.). The plate gets an ear at each corner (flush with it, so it still prints front face
# down without supports); the LED sits face forward in a 0.5 seat, its J-leads on the two x sides with the wire joints
# (0.5) in slots; wires go back through a hole and run in a channel on the plate's back along each side.
LED_SEAT_DEPTH = 0.5       # [FREE] seat depth in the plate front: LED bottom d 15.8, top d 13.8 (1.3 behind the collar)
LED_SEAT_FIT = 0.10        # [FIT] per side on the body (0.2 nozzle, as KEY_POCKET_FIT)
LED_LEG_SLOT = (1.45, 1.2)   # [FREE] leg-side slot: half-width along y (both legs ±0.875 + joint), reach beyond the body
LED_EAR = (9.1, 15.4, 19.8, 25.2)   # [FREE] |x0|, |x1|, |y0|, |y1| of each corner ear: MX top housing (|x| 7.8) and the
                                   #        pressed key's stop bosses (y ≤ 19.7) inside, the corner window outside
LED_EAR_R = 28.4           # [FREE] ears trimmed to this radius (box Ø58 − margin)
LED_HOLE = (9.7, 20.3, 2.0)   # [FREE] |x|, |y|, Ø of the wire hole to the back: inside the ledge's inner edge (r 6.15
                              #        about the well corner's centre), clear of the hub posts at (±13.2, 20)
LED_CHANNEL = (8.4, 11.4, 0.6, 1.6, 17.6)   # [FREE] back channel along each side: |x0|, |x1|, wall, height, |y| end
                                            #        (stops before the posts at (±13.2, 20); MX bottom housing |x| ≤ 7.0)
LED_CHANNEL_GAP = (-10.6, -5.2)   # [FREE] no channel beside the switch-plate post (±10.5, −7.9): the wires pass it on its
                                  #        inner side (MX ≤ 7.0, post ≥ 8.5 pcb / 9.3 discrete)


def led_seat_d():
    """(top, bottom) depth of the LED in its seat."""
    floor = KS["plate_front"] + LED_SEAT_DEPTH
    return floor - LED_T, floor

SPK_X0 = COLLAR_OUT_X + 0.55    # [FREE] speaker on its edge right of the collar, grille faces +x into the duct
SPK_Y = (-15.0, 15.0)           # [FREE]
SPK_D0 = DECK_D1 + 0.6          # [FREE] the speaker's front edge rests on the plenum floor (d 5.0..5.6, 0.6 thick)
SPK_FACE_GASKET = (0.8, 0.5, 0.3)   # [FREE] foam frame on the grille face: width, free, compressed thickness → seals the channel
SPK_HOOK_T = 1.2      # [FREE] hook thickness along d (catch face → back face): tip 0.8 after the 0.4 lead-in
SPK_HOOK = 0.4        # [FREE] snap hooks (45° lead-in) on the cradle ribs overlap the speaker's back edge (inserted from behind)
SPK_TAB_END = 1      # [FREE] v0.9.1: the speaker goes in with its wire tab at +y (towards the amplifier)
SPK_TAB_SLOT = (0.5, 0.4, 0.8)   # [FREE] v0.9.1: blind slot for the tab in the +y cradle rib, open to the back (the speaker
                                 #        and its wires come from behind), closed to the front: play per side along d, play
                                 #        beyond the tab, wall left behind the slot (the rib is thickened for it → no fork)
SPK_BACK_FOAM = (0.8, 0.55)   # [FREE] foam strip on the speaker's −x face (free, compressed): pushes it +x onto the face gasket
DUCT_X1 = max(SPK_X0 + R.SPK_T + SPK_FACE_GASKET[2] + 3.1,   # [FREE] ≥ 3.1 mm air channel between the gasket and the duct wall,
              PERF_XS[-1] + PERF_D / 2 + 0.3)               # and never inside the deck mouth (v0.6: the measured, thinner
                                                            # speaker would leave a 0.03 sliver of duct wall beside the mouth)
DUCT_WALL = 0.8

HUB = (-16.0, 14.8, 3.0, 22.0, 25.5, 37.5)   # [FREE] horizontal hub board (x0,x1,y0,y1, PCB front d, component back d)
HUB_PCB_T = 1.6
# v0.11 (branch kit-pcb, owner 2026-10-08): the REAL hub PCB (hardware/pcb/roomkey-hub, KiCad, routed for JLCPCB) replaces
# the placeholder hub above for the kit AND the wall insert; HUB stays only as the speaker cradle's reference numbers.
# It carries the amplifier, the mic, the light sensor, the I/O expander and the MX hot-swap sockets; the radar stays a
# module on a cable, in its own tray behind the hub's radar window.
HUB_PCB_D0 = KS["mx_bottom"]          # 20.3: the board's front face = the MX housings' bottom; MX pins → sockets on its back
HUB_PCB_STEP = ("hardware", "pcb", "roomkey-hub", "output", "roomkey-hub.step")
HUB_PCB_STEP_XY = (-100.0, 100.0)     # KiCad X = 100 + x, Y = 100 − y (gen_layout_hub.py); its STEP has y = −Y
HUB_PCB_STEP_TOP = 1.51               # [STEP] z of the board's front face; all parts sit on the back (z < 0)
HUB_PCB_BACK = HUB_PCB_D0 + 1.51 + 4.79   # 26.6: deepest part behind the board [STEP]
HUB_PCB_POSTS = ((-13.2, 20.0, True), (13.2, 20.0, True), (13.2, 4.0, False))   # (x, y, M2 screw?) ledge → hub face
HUB_POST_R = (2.0, 1.5)               # [FREE] screw post / plain support radius
HUB_ANCHOR_POST = (10.5, -7.9)        # third M2 screw: a post on the switch plate (was the cable-anchor post)
M2_PILOT = (1.7, 3.5)                 # [FREE] pilot hole for an M2 self-tapping screw in PETG: Ø, depth
HUB_WINDOW = (-40.0, -8.0, -16.1, 2.1)   # the hub's cut-out for the radar's view (gen_layout_hub.py)
# v0.12 (plug-in only, package B, owner 2026-10-31): the radar moves INTO the hub plane. Its board sits in the hub's radar
# window (a bigger cut-out → PCB rev D) with its antenna face on the hub's front plane, held in a CAGE: walls on three
# sides, a back plate behind the board (a slot for the header pins, cut short) and front lips at its short ends; the
# board slides in from the open +x side. The cage's ear sits on the chassis' blade (2 pins), as the old tray's did.
HUB_RADAR = (-24.0, -24.0 + R.RADAR_W, -17.1, -17.1 + R.RADAR_H, HUB_PCB_D0)   # [FREE] x0, x1, y0, y1, antenna face d:
                                     #        x1 −8.16 stays clear of MX2 (|x| ≤ 7.8); y as the self-wired build's radar
RADAR_CAGE = (0.9, 0.10, 1.2, 0.6, 1.0)   # [FREE] wall, play per side, back plate, front lip depth (d), lip width (inward)
RADAR_PINS_CUT = 2.0                 # [FREE] the header pins cut to this length behind the board; J5's wires soldered on
HUB_RADAR_WINDOW = (-40.0, -7.86, -18.4, 6.2)   # [→ PCB rev D] the hub's radar cut-out (open to its −x edge): the cage
                                     #        + 0.3; the CAD cuts it into the rev C board until rev D exists
RADAR_EAR = (-27.9, -25.0, -10.6, -5.4)  # [FREE] ear on the cage's −x side at its back plate (x0, x1, y0, y1)
RADAR_BLADE = (-27.7, -25.2, -10.4, -5.6)   # [FREE] support blade of the chassis flange part: flange back → the ear
RADAR_PINS = ((-26.45, -9.08), (-26.45, -6.88))  # [FREE] 2 pins on the blade top into the ear (lead-in holes, 0.8 webs)
RADAR_PIN = (1.0, 2.0, 0.15)         # [FREE] Ø, length, radial play — thinner than CH_PIN so the ear keeps 0.8 webs
HUB_J5 = (-15.3, -11.7, 7.0, 14.0, 26.22)   # [STEP] the radar's plug socket on the hub back (x0, x1, y0, y1, back d):
                                     #        the tray's top end gets a notch round it
HUB_POSTS = ((-13.2, 4.0), (13.2, 4.0), (-13.2, 20.0), (13.2, 20.0))   # [FREE] from the ledge (lower pair fused to the boss bridges)
IO_MAP = {            # [DS ws_sch] header pins used by the insert (firmware change pending for IO3 — WIP)
    "IO4": "SK6812 data (via AHCT buffer)", "IO7": "I²S BCLK", "IO8": "I²S WS (+10k pull-up on the hub: download mode needs IO8 = 1)",
    "IO16": "I²S DOUT → MAX98357A", "IO17": "I²S DIN ← mic", "IO5": "RELAY_DRIVE (reset-low, one-shot on the hub)",
    "IO3": "PLATE_SENSE, active low via NPN (board 10k pull-up); mic L/R moves to the carrier", "SDA/SCL": "only if a TCA9534 is fitted",
    "IO9": "BOOT = key (board 10k + 100 nF)",
}

# =====================================================================================================
# 5. POWER, ACOUSTICS, RF (v0.12: 5 V SELV only, from the certified plug-in charger in the housing — section 8)
# =====================================================================================================
CHARGER_A = 2.1       # [DS pearl] revolt PX-8884: 5 V, 2.1 A
LOADS_W = {             # [TBD]/[DS] estimates at the 5 V rail — measure on the bench (avg, peak)
    "ESP32-C6 + LCD + touch, Wi-Fi on, no power-save (avg)": (0.65, 1.95),   # peak = TX 354 mA [DS esp32c6] + backlight
    "MAX98357A + speaker (chime, volume-capped to 1.1 W, seconds)": (0.05, 1.10),
    "glow ring 4 × SK6812 MINI (firmware 45 %, strobe 100 % red)": (0.12, 0.72),
    "buffers, pull-ups, misc": (0.01, 0.02),
}
AVG_NO_PS_W = 0.65      # [TBD] ESP average with Wi-Fi power-save off — the current firmware sets power_save_mode: none
KEY_AREA_CM2 = 24.0     # [FREE] exposed key surface (front 12.6 + sides 11.8)
H_CONV = 10.0           # [TBD] W/m²K natural convection + radiation, estimate

# acoustics / RF
SPK_SENS_RANGE = (82.0, 88.0)   # [TBD] 2030 sensitivity dB @ 1 W / 10 cm — not published; typical micro-speaker range
SPL_TARGET = (70.0, 75.0)   # [FREE] at 1 m
HALF_SPACE_DB = 3.0         # [FREE] flat against a wall → radiation into half space
C_SOUND = 343000.0          # mm/s
RF_MIN_METAL = 10.0         # [FREE] want ≥ 10 mm chip ↔ significant metal (spring, screws, frame); brass standoffs are given

# optional sensors — deferred to v1 (see doc §6.5)
SENSORS_DEFERRED = ("VEML7700", "SHT31-D", "LD2410C/B")


# =====================================================================================================
# 7. KIT v0.7 (owner 2026-10-03, prototype): the WHOLE RoomKey in ONE box (supply separate, bench = lab supply 5 V).
#    Presence radar, mic and speaker are non-negotiable. The owner's breakouts: LD2410C, round INMP441 (Ø13.14, no
#    flats), MAX98357A. Speaker stays in the right wing. Light / humidity sensors: later (small chips).
# =====================================================================================================
KIT_MIC_PORT = MIC_PORT           # the plate's mic hole (left strip) stays where the design has it
KIT_MIC_TUBE = (1.6, 1.0)         # [FREE] sound tube bore Ø, wall: plate back → INMP441 port, through deck and flange
KIT_MIC_FOAM = (0.8, 0.5)         # [FREE] foam seal ring at the module end of the tube: free / compressed thickness
KIT_MIC_FOAM_FRONT = (2.0, 1.5)   # [FREE] v0.10: foam ring at the PLATE end, 1.5 compressed (was 0.5) so the tube's front is
                                  #        flush with the deck front (d 3.5): it stood 1.0 proud and was the only thing on the
                                  #        print bed — the whole deck floated on supports
KIT_MIC_D0 = 17.9                 # [FREE] INMP441 front (port side) d: behind the ledge (17.8), clear of the switch plate
KIT_MIC_PORT_OFF = 0.8            # [PHOTO] port ≈ 0.8 off the module centre towards the L/R–GND row
KIT_MIC_C = (-19.36, 9.65)        # [FREE] module centre: 0.8 from the port, optimised → 0.29 inside the box margin (0.79 to a
                                  # Ø58 wall) and 0.29 to the hub post; the L/R–GND row points OUTWARDS (−x). Decided
                                  # 2026-10-03: the module does not fit the touch-board back (4.0 gap, crowded, antenna)
KIT_RADAR = (-22.5, -22.5 + R.RADAR_W, -17.1, -17.1 + R.RADAR_H, 27.0)   # [FREE] LD2410C outline x0, x1, y0, y1 (long side along y), FRONT d
                                  # (antenna side forward, resting on the carrier's back face); patch antennas at the
                                  # OUTER (−x) edge next to the header → they look forward through the left wing only
KIT_CARRIER_D = (25.5, 27.0)      # [FREE] back carrier plate d0, d1: on the 4 hub posts (+ pins), radar behind its window
KIT_AMP_C = (3.2, 12.4)           # [FREE] MAX98357A centre on the carrier back (components to the open back), clear of the radar
KIT_POST_PIN = (2.0, 1.5, 2.3)    # [FREE] pins on the hub posts: Ø, length; carrier hole Ø
KIT_PAD_WALL = 1.2                # [FREE] round pad round each carrier hole (≥ 3 lines of a 0.4 nozzle). The first print
                                  # (2026-10-04) had 0.25–0.35 between hole and edge → the slicer dropped it, holes opened
                                  # over the edge. Checked now in build_kit (carrier webs ≥ KIT_MIN_WEB).
KIT_MIN_WEB = 0.8                 # [FREE] thinnest web the carrier may have anywhere (2 lines of a 0.4 nozzle)
KIT_RADAR_EDGE = (4.2, 1.1)       # [PHOTO 2026-10-06 ±0.5] SMD parts on the antenna face along the WHOLE long edge opposite
                                  #        the header, corners included (LED, R row, caps; the chip reaches 2.3 from that edge):
                                  #        band width from the edge, height [TBD: tallest part ≈ QFN 0.9 / SOT 1.1]
KIT_RADAR_STUBS = 1.0             # [TBD] header pin stubs on the antenna face (photo: pins 5.0–17.0 along the long edge)
KIT_RADAR_RAISE = 1.3             # [FREE] v0.9.2: the board sits on two LEDGES this high at its short ends (parts-free, header
                                  #        side only) → every part on the antenna face floats above the plate (≥ 0.2), so the
                                  #        plate under the parts edge stays and the tray is a CLOSED frame again (v0.9.1 had
                                  #        cut it open: full-width window + the cable-loop keep-out took the +x wall → a "C")
KIT_RADAR_LEDGE_X = 11.0          # [FREE] ledge length from the header edge (parts band starts 15.84 − 4.2 = 11.6 from it)
KIT_RADAR_TRAY = (1.0, 0.10)      # [FIT] play/side: 0.2 just too loose (10-06); 0.15 fit once, then loose on the next print of the
                                  # SAME geometry (10-08: print-to-print variance ≈ 0.05/side) → 0.10; too tight = sand the wall
                                  # v0.8 radar TRAY: a closed perimeter wall round the board (thickness, play), from the
                                  # plate's front to 0.3 behind the board. The first carrier print (2026-10-04) was a floppy U of
                                  # 1.2–2.1 mm strips, open on the header side; the wall closes and stiffens the ring and
                                  # replaces the corner brackets. The window (antennas) stays open.


# =====================================================================================================
# 8. PLUG-IN HOUSING v0.4 ("Steckdosen-RoomKey", WIP, not certified). RoomKey is built ONLY as this plug-in device (owner
#    2026-10-31, "Nur Steckdose"). 230 V stays inside an UNMODIFIED, certified plug-in USB charger; its USB-A port feeds
#    5 V SELV to hub J1 (PCB build) or to the carrier's splice points (self-wired build).
#    v0.4 (owner 2026-10-31): 64 × 64 ("so klein wie möglich": a power strip's neighbours stay free; the plate stays
#    55 × 55) and depth package B: the device 5 mm above the socket centre, a slim bare USB-A plug, the radar's header pins
#    cut short and (PCB build) the radar in the hub plane.
#    G1 = resin SKIN (front border + 4 side walls; for casting: nothing hangs from the border's underside, ≥ 1° draft inside
#         towards the open back, the back edge is the free casting face, no inserts) + printed CARRIER glued into it (the
#         frame tunnel, whose back end stops the insert's flange; 4 corner columns with M3 heat-set inserts).
#    G2 = back lid (invisible: inside the skin, flush with its back edge) + charger sleeve + 4 side walls that press the
#         flange forward; the humidity sensor lies in a window of its bottom wall, behind vents in the skin.
# =====================================================================================================
PLUG_HALF = 32.0    # [FREE] outline 64 × 64 (owner 2026-10-31: as small as possible, ≤ 75 × 75)
PLUG_R = 4.0        # [FREE] outer corner radius (plan)
PLUG_FRONT_D = -1.0  # [FREE] the skin's front face: 1.0 proud of the plate face, as the Jung frame's inner rim was
PLUG_SKIN = (2.0, 2.2, 1.0)   # [FREE → resin thread] front border thickness, side wall at the front, inner draft (°)
PLUG_EDGE = 0.8     # [FREE] 45° chamfer round the front's outer edge
PLUG_OPEN_R = 2.3   # [FREE] the front opening's corner radius (the plate's 2.0 + its 0.3 gap → an even gap all round)
PLUG_GLUE = 0.15    # [FREE] carrier ↔ skin, per side (glue gap)
PLUG_OFFSET = 5.0   # [FREE] package B: the device sits this far ABOVE the socket centre → the charger axis is at y = −5.0
PLUG_COLUMN = (26.8, 3.2)   # [FREE] the carrier's corner columns: centre |x| = |y|, radius (an M3 insert in each)
PLUG_CUP_WALL = 1.2  # [FREE] G2's side walls
PLUG_CUP_FIT = 0.3   # [FREE] G2's side walls ↔ the skin's inner face where they reach it narrowest (the flange's back)
PLUG_IN_CLEAR = 0.45  # [FREE] hub / insert ↔ G2's side walls (→ plug_in_half(), the interior behind the flange)
PLUG_LOOP_CLEAR = 0.2   # [FREE] PCB build: the key wires' U-loop envelope ↔ the charger's face (the slim plug sits below
                        #        the loop's deep end, which turns UP)
PLUG_CHARGER = dict(d=39.25, d_in=36.17, cap=13.0, l=32.3, out=16.0, pin=(4.8, 19.0, 19.0), port=(14.0, 5.95, 14.0),
                    port_c=(0.18, -0.35))
                    # [MEAS] revolt PX-8884 (Pearl, EAN 4022107346085; 5 V 2.1 A USB-A, contour plug, class II, REV4 2024),
                    # owner's calipers 2026-10-31 (sheet A–H): front part Ø39.25 (A), the part in the recess Ø36.17 (B),
                    # body 32.3 (C), 16.0 out of the owner's socket (H) → 16.3 in the recess; the step between the two
                    # sits `cap` behind the face [PHOTO ±0.5; the thin part has earth-clip grooves at 12/6 o'clock, small
                    # rails at 3/9]; USB-A opening 14 × 5.95 (D, E) on the front face, horizontal, its centre from F 17 /
                    # G 12.8 (= centred within what calipers read on a round rim); pins Ø4.8 × 19, 19 apart [DS CEE 7/17].
                    # port_c is relative to the charger's axis.
PLUG_USB = (12.0, 4.5, 14.0, 6.6, 3.0)   # [TBD the plug bought] bare solder-type USB-A plug (no overmould): shell w, h (12 deep
                    # in the port); in front of the charger face: body w, h, length (solder cups + the wires' bend)
PLUG_CLEAR = 0.5    # [FREE] self-wired build: USB plug ↔ the key wires' U-loop envelope (there the loop rolls DOWN onto it)
PLUG_WALL = 1.6     # [FREE] charger sleeve (4 lines of a 0.4 nozzle)
PLUG_BACK_T = 2.0   # [FREE] G2 back plate (on the socket face); the M3 countersunk heads sit flush in it
PLUG_FIT = 0.3      # [FREE] G2's back plate ↔ the skin's inner face, per side
PLUG_STOP_D = 7.7   # [FREE] the carrier's tunnel ends here: 0.1 in front of the flange (d 7.8) → flange play 0.1
PLUG_SLEEVE = (0.5, 2.0, 1.0)   # [FREE] charger sleeve: play per side in the back plate's hole (the step that holds the grip
                    # ring), front lip width and thickness (the charger's face rests on it)
PLUG_GRIP = dict(t=1.6, n=12, w=1.5, gap=0.3, stand=1.0, play=0.1, setback=0.4, inter=0.5, coupons=(0.3, 0.5, 0.7))
                    # [FREE] TPU 95A grip ring in the sleeve (owner 2026-10-27 "bestellt"). A FLEX ring: n inner ribs press
                    # on the charger's thick front part, n outer standoffs between them carry the tube in the sleeve's
                    # seat, so the tube wall bends between the standoffs (ribs on a tube backed all round could only
                    # compress: TPU 95A at 0.2 mm is far too stiff to push in by hand). Wall, rib count, rib width, wall ↔
                    # charger, standoff height, standoff ↔ seat, set back from the charger face, rib interference
                    # [TBD → coupons: 1/2/3 notches = 0.3/0.5/0.7]
PLUG_FOOT = (0.6, 21.0, 25.0, 1.0, 0.4)   # [FREE] the housing's back face stands this far off the socket face (the housing
                    # never holds the charger out of the socket); TPU 95A foot ring round the charger axis (inner r, outer
                    # r: on any central plate, clear of the recess; thickness; groove depth → it just touches the socket)
PLUG_SCREW = (3.4, 6.4, 3.2)   # [FREE] 4 × M3 × 10 (or × 12) countersunk (ISO 10642) at the corner columns: clearance hole,
                    # countersink Ø, relief Ø in front of the insert (the screw tip)
PLUG_INSERT = (4.0, 6.5)   # [TBD the inserts bought] M3 heat-set insert in each column, pressed in from the back: hole Ø,
                    # depth (Ruthex / CNC Kitchen M3 × 5.7: hole Ø4.0; +0.8 for the displaced melt)
PLUG_RH = (3.3, 9.6, 1.0)   # [FREE] humidity sensor in G2's bottom wall, chip side DOWN behind the skin's vents: chip centre
                    # x, the board's front edge d (its long side along x, its pins at the back edge), window inset from
                    # the board's x ends (the board rests there on G2's wall; its parts hang into the window, the skin
                    # 0.4 below them; a dot of hot glue holds it). PCB build: the sensor tail (SHT40 + VEML6030, layout
                    # open) takes the same place and outline (≤ 13.4 × 10.5 × 2.6)
PLUG_VENT = (1.5, 2.6)   # [FREE → resin thread] vents through the skin's bottom wall round the chip: Ø, pitch (2 × 2)
PLUG_LIGHT = (-1.0, 2.0)  # [FREE → resin thread] light window through the skin's bottom wall (a smooth cylindrical hole ⟂ the
                    # wall, filled clear by the resin thread) at the chip's d: x, Ø. The sensor tail's VEML6030 sits over it
PLUG_SOCKET = (10.0, 39.5, 55.0)   # [TBD] reference Jung AS 500 SCHUKO socket: face ↔ wall (the frame's inner rim height),
                    # recess Ø [DS CEE 7/3 ≈ 39–40], central plate; recess depth = body − out (16.3 in the owner's socket)
PLUG_WIRE = 1.2     # [DS JST PH: AWG 32–24] 2 × AWG 24 (Ø ≈ 1.2), USB plug → hub J1's PHR plug / the carrier's splice points
PLUG_J1 = (10.3, -2.5, 7.6, 5.9, 4.8, 12.75)   # [PCB rev D 2026-10-31] J1 = S2B-PH-K-S, a SIDE-entry JST PH, its mouth
                    # towards −x at x 6.5: centre x, y, length along x (the plug's way), width along y, height behind the
                    # board [DS ≈ 4.8], the THT pins' x (pin 2 = +5 V at y −1.5, pin 1 = GND at y −3.5; tails on the
                    # front ≤ 1.0). Clear of H3's screw head (y ≤ −5.9) and the speaker foam (x 14.6); the lead comes
                    # along a lane the hub keeps free of parts (x −4.5 … 6.5, y −6.0 … −0.5). With the charger face at
                    # d 31 a top-entry PH + plug (≈ 13 deep) would not fit inside the charger's circle
PLUG_MOMENT_MAX = 0.25   # [DS IEC 60950-1 §4.3.6 / IEC 62368-1 §4.7: direct plug-in equipment ≤ 0.25 N·m on the socket]
PLUG_MASS_G = {"touch board": 9.0, "hub": 7.0, "MAX98357A": 2.0, "INMP441": 1.0, "speaker 2030": 4.0, "LD2410C": 2.0,
               "MX switch 1": 3.5, "MX switch 2": 3.5, "USB plug": 2.0, "charger": 39.0}
                    # [TBD] g, those of the build present; the charger [DS pearl]; printed and cast parts by volume


def plug_skin_in(d):
    """the skin's inner half width at depth d (its inner faces open towards the back by the draft)."""
    t, w, a = PLUG_SKIN
    return PLUG_HALF - w + math.tan(math.radians(a)) * (d - (PLUG_FRONT_D + t))


def plug_in_half():
    """the interior's half width behind the flange (hub, radar cage, insert): inside G2's side walls with clearance."""
    return plug_skin_in(WALL_D) - PLUG_CUP_FIT - PLUG_CUP_WALL - PLUG_IN_CLEAR


def plug_port():
    """the charger's USB-A port centre in device coordinates (the charger's axis sits PLUG_OFFSET below the device's)."""
    return PLUG_CHARGER["port_c"][0], PLUG_CHARGER["port_c"][1] - PLUG_OFFSET


def plug_cups():
    """the slim USB plug's two solder cups in use (x, y): VBUS left, GND right, looking from the room [TBD: the plug
    bought] — so neither build's two supply wires cross."""
    px, py = plug_port()
    return {"5V": (px - 3.5, py), "GND": (px + 3.5, py)}


def plug_rh():
    """the humidity sensor in G2's bottom wall: board x0, x1, PCB y0 (on G2's wall), y1, d0, d1, chip (x, d), and the hub's
    notch it passes when G2 goes in (x0, x1, y up to)."""
    cx, d0, inset = PLUG_RH
    x0 = cx - R.RH_CHIP_C[0]
    y0 = -(plug_skin_in(WALL_D) - PLUG_CUP_FIT - PLUG_CUP_WALL)
    y1 = y0 + R.RH_PCB_T
    return dict(x0=x0, x1=x0 + R.RH_W, y0=y0, y1=y1, d0=d0, d1=d0 + R.RH_H, chip=(cx, d0 + R.RH_CHIP_C[1]), inset=inset,
                notch=(x0 - 0.4, x0 + R.RH_W + 0.4, y1 + 1.1))


def plug_depths(build="pcb"):
    """the plug-in housing's depths (d) along the axis, from the deepest insert part to the socket face. PCB build: the
    charger face sits just behind the key wires' U-loop (it turns UP, the slim plug sits below it, package B). Self-wired
    build: the loop rolls DOWN behind the back carrier onto the plug's place, so the plug sits behind it."""
    if build == "pcb":
        loop = loop_up()[5]
        face = loop + PLUG_LOOP_CLEAR
    else:
        loop = LOOP_D1
        face = loop + PLUG_CLEAR + PLUG_USB[4]
    sock = face + PLUG_CHARGER["out"]                    # socket face (the charger sits fully in the socket)
    back = sock - PLUG_FOOT[0]                           # the housing's back face, the TPU foot ring bridges the gap
    return dict(loop=loop, usb0=face - PLUG_USB[4], face=face, socket=sock, back=back, back0=back - PLUG_BACK_T,
                wall=sock + PLUG_SOCKET[0], recess=PLUG_CHARGER["l"] - PLUG_CHARGER["out"])


# =====================================================================================================
# helpers
# =====================================================================================================
def B(name, x0, x1, y0, y1, d0, d1, zone="SELV", role="ref", note="", tag="[FREE]", move=None):
    return dict(name=name, kind="box", x0=min(x0, x1), x1=max(x0, x1), y0=min(y0, y1), y1=max(y0, y1),
                d0=d0, d1=d1, zone=zone, role=role, note=note, tag=tag, move=move)


def C(name, cx, cy, r, d0, d1, **kw):
    e = B(name, cx - r, cx + r, cy - r, cy + r, d0, d1, **kw)
    e.update(kind="cyl", cx=cx, cy=cy, r=r)
    return e


def rows_span():
    return PERF_YS[0] - PERF_D / 2, PERF_YS[-1] + PERF_D / 2


def cols_span():
    return PERF_XS[0] - PERF_D / 2, PERF_XS[-1] + PERF_D / 2


def sw_depths():
    """Switch stack from the datum: the carrier rests on the flange front face.
    Returns (plunger tip, body front, body back, carrier back) as d."""
    cback = WALL_D - FLANGE_T
    back = cback - CARRIER[2]
    tip = back - SW_TOTAL_H
    front = tip + (SW_TOTAL_H - SW_BODY_H)
    return tip, front, back, cback


def nub_h():
    """nub height that gives NUB_GAP with the flange datum."""
    return sw_depths()[0] - PLATE_T - NUB_GAP


NUB_H = nub_h()           # 0.4 with the assumed WALL_D


def wire_slot(x, y):
    """centre of the carrier wire slot for the switch at (x, y)."""
    return x - math.copysign(CARRIER_WIRE_OFF, x), y - math.copysign(CARRIER_WIRE_OFF, y)


def gap_tol():
    rss = math.sqrt(sum(t ** 2 for _, t, _ in GAP_CHAIN))
    worst = sum(t for _, t, _ in GAP_CHAIN)
    return rss, worst


def mouth():
    c0, c1 = cols_span()
    r0, r1 = rows_span()
    return c0 - 0.3, c1 + 0.3, r0 - 0.3, r1 + 0.3


def port_d():
    c = SPK_D0 + R.SPK_W / 2
    return c - R.SPK_PORT_W / 2, c + R.SPK_PORT_W / 2


def grille_x():
    return SPK_X0 + R.SPK_T


def mic_well():
    """x0, x1, y0, y1 of the mic wire well: below the pocket's bottom edge, at its outer (−x) side."""
    x0, x1, y0, y1, _, _ = mic_carrier_box()
    c = MIC_POCKET_CLEAR
    return x0 - c, x0 - c + MIC_WELL, y0 - c - MIC_WELL, y0 - c


def loop_up():
    """v0.11: the key wires' keep-out: through the hub slot (y 0.2..2.8), then a rolling loop behind the hub that turns UP
    (+y) to the solder holes J4 (y ≈ 7.8) — (x0, x1, y0, y1, d0, d1)."""
    d0 = HUB_PCB_D0 + HUB_PCB_STEP_TOP
    return (-CABLE_W / 2 - 1.0, CABLE_W / 2 + 1.0, CABLE_Y - 1.3, CABLE_Y + 2 * LOOP_R + 1.5, d0, d0 + 2 * LOOP_R + 1.0)


def mic_carrier_box():
    mx, my = MIC_PORT
    cw, ch, ct = R.MIC_CARRIER
    return mx - cw / 2, mx + cw / 2, my - ch / 2, my + ch / 2, MIC_FACE_D, MIC_FACE_D + ct


# =====================================================================================================
# layout: every part / reference body as an envelope (the same in L and S)
# =====================================================================================================
def layout(v):
    assert v in VARIANTS
    s = KS
    E = []
    E.append(B("key shell", -KEY_W / 2, KEY_W / 2, -KEY_H / 2, KEY_H / 2, s["glass"], s["skirt_end"],
               role="part", move="key", note="white keycap shell + side skirts"))
    E.append(B("touch board", -R.TB_W / 2, R.TB_W / 2, -R.TB_H / 2, R.TB_H / 2, s["glass"], s["standoff_end"],
               role="ref", move="key", tag="[DS]", note="Waveshare ESP32-C6-Touch-LCD-1.47"))
    ax, ay, al, aw, ah = R.TB_ANT
    E.append(B("antenna chip", ax - al / 2, ax + al / 2, ay - aw / 2, ay + aw / 2, s["pcb_back"], s["pcb_back"] + ah,
               role="ref", move="key", tag="[DS]", note="ceramic chip antenna on the PCB back"))
    for i, (x, y) in enumerate(R.MX_SW_POS):
        E.append(B(f"MX switch {i+1}", x - R.MX_TOP_W / 2, x + R.MX_TOP_W / 2, y - R.MX_TOP_W / 2, y + R.MX_TOP_W / 2,
                   s["mx_top"], s["plate_front"], tag="[DS]", note="housing above the plate"))
        E.append(B(f"MX body {i+1}", x - R.MX_BODY_BELOW / 2, x + R.MX_BODY_BELOW / 2, y - R.MX_BODY_BELOW / 2,
                   y + R.MX_BODY_BELOW / 2, s["plate_back"], HUB_PCB_D0, tag="[DS]",
                   note="below the plate; v0.11: the pins go on into the hub's hot-swap sockets (checked in the CAD)"))
    E.append(B("switch plate", -(WELL_IN_X - SWP_CLEAR), WELL_IN_X - SWP_CLEAR, -(WELL_IN_Y - SWP_CLEAR),
               WELL_IN_Y - SWP_CLEAR, s["plate_front"], s["plate_back"], role="part"))
    e = B("collar", -COLLAR_OUT_X, COLLAR_OUT_X, -COLLAR_OUT_Y, COLLAR_OUT_Y, COLLAR_D0, COLLAR_D1, role="part",
          note="translucent light guide (roll limit for the key)")
    e["kind"], e["r"] = "rrect", COLLAR_OUT_R
    E.append(e)
    E.append(B("plate", -HALF, HALF, -HALF, HALF, 0.0, SNAP_D1, role="part", move="plate"))
    # v0.11: no mic carrier on the plate — the mic sits on the hub PCB, a sound tube leads from the plate hole to it
    for i, (x, y) in enumerate(LED_POS):
        E.append(B(f"LED {i+1}", x - LED_W / 2, x + LED_W / 2, y - LED_W / 2, y + LED_W / 2, led_seat_d()[0],
                   led_seat_d()[1], note="WS2812B-MINI 3535 in its seat in the switch plate (v0.11)"))
    tip, front, back, cback = sw_depths()
    for (x, y) in SW_POS:
        nm = "switch " + ("T" if y > 0 else "B") + ("L" if x < 0 else "R")
        E.append(B(nm, x - CARRIER[0] / 2, x + CARRIER[0] / 2, y - CARRIER[1] / 2, y + CARRIER[1] / 2, tip, cback,
                   tag="[DS]", note="B3FS-1002P (SMD) on a flat-backed FR4 carrier"))
    for i, (x, y) in enumerate(PAD_POS):
        E.append(B(f"preload pad {i+1}", x - PAD_SIZE[0] / 2, x + PAD_SIZE[0] / 2, y - PAD_SIZE[1] / 2, y + PAD_SIZE[1] / 2,
                   DECK_D0 + PAD_POCKET - PAD_H, DECK_D0 + PAD_POCKET, tag="[TBD]", note="soft PU pad (compressed by the plate)"))
    m0, m1, n0, n1 = mouth()
    pd0, pd1 = port_d()
    gx = grille_x()
    E.append(B("duct", gx + SPK_FACE_GASKET[2], DUCT_X1 + DUCT_WALL, n0 - DUCT_WALL, n1 + DUCT_WALL, DECK_D1, pd1 + DUCT_WALL,
               role="part", note="printed 90° duct, grille → right strip"))
    E.append(B("speaker 2030", SPK_X0, gx, SPK_Y[0], SPK_Y[1], SPK_D0, SPK_D0 + R.SPK_W,
               tag="[DS]", note="on edge, grille faces +x"))
    E.append(B("speaker face gasket", gx, gx + SPK_FACE_GASKET[2], n0 - DUCT_WALL, n1 + DUCT_WALL, SPK_D0, pd1 + DUCT_WALL,
               note="foam frame, compressed"))
    # v0.11: the hub PCB is checked as its real STEP in the CAD (insert_lib.hub_pcb), not as an envelope here
    lx0, lx1, ly0, ly1, ld0, ld1 = loop_up()
    E.append(B("cable loop", lx0, lx1, ly0, ly1, ld0, ld1, note="key wires: hub slot, rolling loop behind the hub, UP to J4"))
    E.append(B("speaker back foam", SPK_X0 - SPK_BACK_FOAM[1], SPK_X0, SPK_Y[0] + 2, SPK_Y[1] - 2, SPK_D0 + 2, SPK_D0 + R.SPK_W - 2,
               note="foam strip, compressed"))
    return E


# =====================================================================================================
# geometry primitives for the checks
# =====================================================================================================
def _corners(e):
    return [(e["x0"], e["y0"]), (e["x1"], e["y0"]), (e["x1"], e["y1"]), (e["x0"], e["y1"])]


def gap2d(a, b):
    """Signed 2D gap between two footprints (negative = overlap)."""
    if a["kind"] == "cyl" and b["kind"] == "cyl":
        return math.hypot(a["cx"] - b["cx"], a["cy"] - b["cy"]) - a["r"] - b["r"]
    if a["kind"] == "cyl" or b["kind"] == "cyl":
        c, bx = (a, b) if a["kind"] == "cyl" else (b, a)
        dx = max(bx["x0"] - c["cx"], 0.0, c["cx"] - bx["x1"])
        dy = max(bx["y0"] - c["cy"], 0.0, c["cy"] - bx["y1"])
        if dx == 0 and dy == 0:
            return -min(c["cx"] - bx["x0"], bx["x1"] - c["cx"], c["cy"] - bx["y0"], bx["y1"] - c["cy"]) - c["r"]
        return math.hypot(dx, dy) - c["r"]
    dx = max(a["x0"] - b["x1"], b["x0"] - a["x1"])
    dy = max(a["y0"] - b["y1"], b["y0"] - a["y1"])
    if dx < 0 and dy < 0:
        return max(dx, dy)
    return math.hypot(max(dx, 0), max(dy, 0))


def rrect_inside(px, py, hx, hy, r):
    """distance of a point inside a rounded rectangle (half sizes hx, hy, corner r) to its boundary (neg = outside)."""
    qx, qy = abs(px) - (hx - r), abs(py) - (hy - r)
    if qx > 0 and qy > 0:
        return r - math.hypot(qx, qy)
    return min(hx - abs(px), hy - abs(py))


# The lips only stop FORWARD motion. A press can only tip the plate about a SUPPORTING line of the contact regions
# (every contact on the line or on the pressed side, else a lip would have to move forward): the edges of their convex
# hull and every line through one hull corner between those edges (sampled every ~10°). Contact regions: top lip on the
# deck edge (|x| ≤ 26.2 incl. the deck corner radius, y 25.6..26.2), snap lips on the tongues (|x| 22.5..25.5,
# y −26.2..−25.6). When the plate tips, a lip bears on the OUTER edge of its overlap → the hull corners below.
_YI = HALF - PLATE_SKIRT_T - LIP_IN          # 25.6 lip inner edge
_C = DECK_HALF_X - DECK_R                     # deck corner arc centre (|x| = |y| = 25.7)
_A = _C + DECK_R * math.sqrt(0.5)             # arc mid-point
SUPPORTS = ((-SNAP_X[1], -DECK_HALF_Y, SNAP_D0), (SNAP_X[1], -DECK_HALF_Y, SNAP_D0),
            (DECK_HALF_X, _YI, LIP_D0), (_A, _A, LIP_D0), (_C, DECK_HALF_Y, LIP_D0),
            (-_C, DECK_HALF_Y, LIP_D0), (-_A, _A, LIP_D0), (-DECK_HALF_X, _YI, LIP_D0))
#            0 bottom-left snap, 1 bottom-right snap, 2..4 right end of the top lip (deck corner), 5..7 left end (x, y, d; CCW)


def pivot_lines(steps=9):
    """(label, (x0, y0), (tx, ty) unit direction, inward normal) for every sampled supporting line."""
    out = []
    n = len(SUPPORTS)
    for i in range(n):
        p = SUPPORTS[i]
        prv, nxt = SUPPORTS[i - 1], SUPPORTS[(i + 1) % n]
        a0 = math.atan2(p[1] - prv[1], p[0] - prv[0])
        a1 = math.atan2(nxt[1] - p[1], nxt[0] - p[0])
        while a1 < a0:
            a1 += 2 * math.pi
        for k in range(steps + 1):
            a = a0 + (a1 - a0) * k / steps
            tx, ty = math.cos(a), math.sin(a)
            out.append((f"support {i} @ {math.degrees(a) % 360:.0f}°", (p[0], p[1]), (tx, ty), (-ty, tx)))
    return out


PIVOT_LINES = pivot_lines()


def pad_k():
    """linearised pad stiffness (N/mm): stress ≈ CLD40 × strain / 0.4."""
    return PAD_SIZE[0] * PAD_SIZE[1] * 1e-6 * PAD_CLD40 * 1e3 / (0.4 * PAD_H)


def press_force(px, py, of=None, pads=True):
    """Click force at press point (px, py) on the floating plate. The plate tips about a supporting line of the lip
    contacts; the switch farthest from the line touches first, every switch within SW_PT of it clicks together:
    force = (Σ OF·r_i + Σ pad force·r_pad) / r_P. The plate takes the pivot with the smallest force.
    Returns (force N, n switches clicking, pivot label). Switches touched but not yet clicked add their rising pretravel
    force (linear 0 → OF). Assumes equal nub gaps (the spread → §5.1)."""
    of = SW_OF if of is None else of
    best = None
    kp = pad_k()
    for lab, (x0, y0), _, (nx, ny) in PIVOT_LINES:
        def dist(x, y):
            return (x - x0) * nx + (y - y0) * ny
        if min(dist(s[0], s[1]) for s in SUPPORTS) < -1e-6:
            continue                       # not a supporting line (numerical guard)
        rp = dist(px, py)
        if rp < 1.0:
            continue
        rs = [dist(x, y) for (x, y) in SW_POS]
        rs = [r for r in rs if r > 1.0]
        if not rs:
            continue
        rmax = max(rs)
        th_click = (NUB_GAP + SW_PT) / rmax          # the first switch clicks at this plate angle
        m, eng = 0.0, []
        for r in rs:                                 # each switch: rising force over its pretravel, OF when it clicks
            trav = th_click * r - NUB_GAP
            if trav >= SW_PT - 1e-9:
                eng.append(r)
                m += of * r
            elif trav > 0:
                m += of * trav / SW_PT * r
        if pads:                                     # pads compress by th·r (+ their preload moment about the line)
            pre_f = kp * (PAD_H - (DECK_D0 + PAD_POCKET - PLATE_T))
            for (x, y) in PAD_POS:
                r = dist(x, y)
                if r > 0:
                    m += (pre_f + kp * th_click * r) * r
        f = m / rp
        if best is None or f < best[0]:
            best = (f, len(eng), lab)
    return best


def tongue_mech():
    """Bottom snap tongue as a cantilever (root at TONGUE_X[0]) loaded at the lip end NEAREST the root (conservative).
    In-plane (y): deflection needed there = overlap + 0.1 → root strain, tip deflection.
    Out of plane (d, forward pull on the plate): stiffness at the lip and the pull at yield."""
    root = TONGUE_X[0] + TONGUE_SLOT / 2              # the slot's round end: the tongue is free from its tangent point
    L = TONGUE_X[1] - root
    a0 = SNAP_X[0] - root
    overlap = LIP_IN - (HALF - PLATE_SKIRT_T - DECK_HALF_Y)
    need = overlap + 0.1
    k = need * 3 / a0 ** 3                              # P/(EI) for a point load at a0 giving 'need' there
    eps = k * a0 * TONGUE_W / 2
    th = k * a0 ** 2 / 2

    def defl(a):                                        # deflection at distance a from the root
        a = max(0.0, min(a, L))
        return k * a ** 2 * (3 * a0 - a) / 6 if a <= a0 else need + th * (a - a0)
    h = TONGUE_D1 - DECK_D0
    inertia = TONGUE_W * h ** 3 / 12
    ac = (SNAP_X[0] + SNAP_X[1]) / 2 - root
    k_d = 3 * MAT_E * inertia / ac ** 3
    p_yield = MAT_SIGMA_Y * inertia / (h / 2) / ac
    return dict(L=L, overlap=overlap, need=need, eps=eps, tip=defl(L), defl=defl, k_d=k_d, p_yield=p_yield, h=h)


PRESS_POINTS = {"left wing centre": (-21.0, 0.0), "left wing, near key": (-15.5, 0.0), "left wing outer edge": (-26.5, 0.0),
                "right wing centre": (21.0, 0.0), "top band centre": (0.0, 26.0), "bottom band centre": (0.0, -26.0),
                "top-left corner": (-24.0, 24.0), "right wing top": (21.0, 15.0), "right wing bottom": (21.0, -15.0)}


def edge_travel(t_stop):
    """largest plate travel at a plate corner when the farthest engaged switch has travelled t_stop."""
    corners = [(sx * HALF, sy * HALF) for sx in (-1, 1) for sy in (-1, 1)]
    t = 0.0
    for _, (x0, y0), _, (nx, ny) in PIVOT_LINES:
        rs = [(x - x0) * nx + (y - y0) * ny for (x, y) in SW_POS]
        rc = [(x - x0) * nx + (y - y0) * ny for (x, y) in corners]
        if max(rs) > 1.0:
            t = max(t, t_stop * max(rc) / max(rs))
    return t


# =====================================================================================================
# validate
# =====================================================================================================
def validate(v, verbose=True):
    errs, warns, oks, infos = [], [], [], []

    def rule(ok, msg, hard=True):
        (oks if ok else (errs if hard else warns)).append(msg)

    def warn(msg):
        warns.append(msg)

    def info(msg):
        infos.append(msg)

    s = KS
    E = layout(v)
    byname = {e["name"]: e for e in E}

    # --- A. frozen + plate ---------------------------------------------------------------------------
    for k, want in R.FROZEN.items():
        rule(abs(getattr(R, k) - want) < 1e-9, f"frozen {k} = {getattr(R, k)}")
    wing = HALF - CUT_W / 2
    band = HALF - CUT_H / 2
    rule(band >= 3.0, f"bands above/below the key {band:.2f} mm (≥ 3.0; skirts + lip make them L-sections)")
    rule(wing >= 12.5, f"wings {wing:.2f} mm (north star ~13)")
    rule(PLATE <= FRAME_OPEN - 2 * 0.2, f"plate {PLATE} in frame opening {FRAME_OPEN} [TBD]: {(FRAME_OPEN - PLATE)/2:.2f} mm per side")
    web = PERF_PITCH - PERF_D
    rule(web >= 0.6, f"perforation web {web:.2f} mm between Ø{PERF_D} holes (≥ 0.6 for FDM, coupon v1 row F)")
    c0, c1 = cols_span()
    r0, r1 = rows_span()
    rule(c0 - CUT_W / 2 - GLOW_RIM_W >= 2.0, f"strip starts {c0 - CUT_W/2:.2f} mm from the cut-out edge ({c0 - CUT_W/2 - GLOW_RIM_W:.2f} "
         f"outside the glow rim); strip {c1 - c0:.1f} × {r1 - r0:.1f} ({PERF_COLS} × {PERF_ROWS} holes; render ≈ 4.5 × 18, 4 × 13 plus one centred hole at each strip end — omitted)")
    rule(HALF - c1 >= 3.0, f"strip ends {HALF - c1:.2f} mm from the plate edge")
    for (x, y) in SW_POS:
        on_hole = (c0 - 1.25 < abs(x) < c1 + 1.25) and (r0 - 1.25 < abs(y) < r1 + 1.25)
        rule(not on_hole, f"nub at ({x:+.1f}, {y:+.1f}) sits on solid plate (not over the strip)")
    rule(PLATE_FACE_T >= 0.5 and PLATE_T - PLATE_FACE_T >= 1.0, f"plate: {PLATE_FACE_T} ivory [TBD row H] over a "
         f"{PLATE_T - PLATE_FACE_T:.1f} black core (opaque); {GLOW_RIM_W} translucent glow rim at the cut-out")
    lit = COLLAR_OUT_X - CUT_W / 2
    rule(lit >= 0.3, f"glow rim (x {CUT_W/2:.2f}..{CUT_W/2 + GLOW_RIM_W:.2f}) lies {lit:.2f} mm over the lit collar face, "
         f"{COLLAR_D0 - PLATE_T:.1f} mm behind it — the rim face is flush with the plate → visible at any angle")

    # --- B. key module ---------------------------------------------------------------------------------
    rule(s["skirt_end"] + KEY_TRAVEL <= COLLAR_D1 - 0.3, f"key side skirts pressed end at d {s['skirt_end'] + KEY_TRAVEL:.1f}, "
         f"inside the collar (back face {COLLAR_D1})")
    play = R.KEY_WELL_CLEAR + COLLAR_IN_EXTRA
    ov = KEY_CATCH_X - play
    gw = COLLAR_OUT_X - (KEY_W / 2 + KEY_CATCH_X + GROOVE_CLEAR[0])
    rule(ov >= 0.15 and gw >= 0.6 - 1e-9, f"v0.8 key catch: nub overlaps the collar's inner face by {ov:.2f} at the key's "
         f"side play {play:.2f} (≥ 0.15 for print tolerance; shifted sideways, the far nub catches by {ov + play:.2f} — one side "
         f"always holds), collar wall behind the groove {gw:.2f} (≥ 0.6: 3 lines of the 0.2 nozzle)")
    rule(KEY_W / 2 + KEY_CATCH_X <= COLLAR_OUT_X + COLLAR_FIT - 0.5, "v0.8 key catch: the key with its nubs passes the empty "
         f"deck opening (nubs to {KEY_W / 2 + KEY_CATCH_X:.2f}, opening {COLLAR_OUT_X + COLLAR_FIT:.2f})")
    rule(KEY_CATCH_GAP >= 0.37, f"v0.8 key catch: {KEY_CATCH_GAP} play to the groove's front wall at rest (≥ 0.37: a "
         f"±{KEY_WOBBLE_DEG}° roll lifts the nub that much)")
    (_, y1), (_, y2) = R.MX_SW_POS
    over_t, over_b = KEY_H / 2 - y1, KEY_H / 2 + y2
    info(f"key overhangs its two MX stems by {over_t:.1f} (top) / {over_b:.1f} (bottom); the side skirts in the collar "
         f"({R.KEY_WELL_CLEAR}/side) limit roll. This says nothing about binding (next line)")
    # v0.9 rigid key (owner 2026-10-05, replaces the v0.6–v0.8 rocker): full cross sockets, fixed (MX1) + floating (MX2)
    act_max = R.MX_PRETRAVEL + 0.6
    rule(KEY_TRAVEL >= act_max + 0.3 and KEY_TRAVEL <= R.MX_TRAVEL - 0.2, f"centre press: the key stops on the 4 bosses after "
         f"{KEY_TRAVEL} (both switches past {act_max:.1f}, MX bottom-out {R.MX_TRAVEL} not reached)")
    warn(f"rigid key: every press moves both springs (≈ {2 * R.MX_FORCE_N:.1f} N + guide friction). An end press "
         f"({over_t:.1f} / {over_b:.1f} beyond the stems) tilts the key within the stem play and loads the guides (a drawer: "
         f"friction ≈ 1.2·F estimated) → binding is desk-rig test R1 [TBD]. Fallback (not modelled): one centre MX + a 2u "
         f"plate-mount stabiliser")
    warn(f"rigid key: held on the stems by socket friction — MX1 full cross, MX2 clamped in x only (floats "
         f"±{R.KEY_SOCKET_FLOAT} in y) — pull-off ≥ {KEY_PULL_MIN:.0f} N target → coupon [TBD]; the v0.8 catch (collar grooves) "
         f"is the geometric backup")
    info("firmware (RoomKey software): KEY1 on BOOT, KEY2 on IO6 stay wired separately and are ORed (key_raw) — one key; "
         "top / bottom, if ever wanted, from the touch point at the click (AXS5106L), not from the mechanics")
    rule(s["mx_top"] - (s["key_back"] + KEY_TRAVEL) >= 0.45, f"key stops on its bosses ({KEY_TRAVEL}); key back ↔ MX housing "
         f"top {s['mx_top'] - (s['key_back'] + KEY_TRAVEL):.2f} mm then (the real housing top is tapered → more)")
    pitch_err = math.sqrt(0.05 ** 2 + 0.05 ** 2 + 0.1 ** 2)   # MX cut-out, socket, print: MX2's post off its housing centre
    dip = s["key_back"] + KEY_TRAVEL - s["mx_top"] + (s["post_end"] - s["key_back"])
    sweep = dip * math.sin(math.radians(KEY_WOBBLE_DEG))
    pc = R.MX_WINDOW / 2 - R.MX_POST_D / 2 - pitch_err - sweep
    rule(pc >= 0.1, f"stem posts Ø{R.MX_POST_D} dip {dip:.1f} into the MX housing window {R.MX_WINDOW} [TBD] at the stop; MX2's "
         f"post sits off centre by the pitch error (≈ {pitch_err:.2f} RSS, its socket floats up to ±{R.KEY_SOCKET_FLOAT}) + "
         f"{KEY_WOBBLE_DEG}° sweep {sweep:.2f} → {pc:.2f} radial clearance left (≥ 0.1)", hard=False)
    half = (R.MX_POST_D - R.MX_STEM_ARM_W) / 2
    rule(half >= 1.6 and R.KEY_SOCKET_FLOAT >= pitch_err, f"MX2 floating socket: its y-arm slot runs through the "
         f"Ø{R.MX_POST_D} post (no thin end walls; two {half:.2f} halves clamp the arm's {R.MX_STEM_ARM_W} width), the x-arm "
         f"slot is {R.MX_STEM_ARM_W + 2 * R.KEY_SOCKET_FLOAT:.2f} wide → float ±{R.KEY_SOCKET_FLOAT} ≥ pitch error {pitch_err:.2f}")
    loc = [0.1, 0.1, 0.1, 0.05, 0.1, 0.05]   # plate skirt clr, plate print, switch-plate screw play, MX cut-out, MX stem, socket
    rss = math.sqrt(sum(t * t for t in loc))
    hard = CUT_W / 2 - WELL_IN_X
    rule(1.0 - rss >= hard, f"shadow gap 1.0 ± {rss:.2f} RSS (plate skirt 0.1, print 0.1, switch-plate screws 0.1, MX cut-out "
         f"0.05, stem 0.1, socket 0.05) → ≥ {1.0 - rss:.2f}, above the {hard:.2f} where the key skirt touches the collar; worst "
         f"case (sum {sum(loc):.2f}) the skirt rides on the collar (rub, not a jam)", hard=False)
    rule(M2_CSK_H <= R.KEY_BACK_T - 0.3, f"M2 countersunk head {M2_CSK_H} flush in the {R.KEY_BACK_T} key back")
    kc = R.TB_STANDOFF - KEY_BOARD_BACK_H + KEY_BACK_CHANNEL
    rule(kc >= CABLE_WIRE_D + 0.3 and R.KEY_BACK_T - KEY_BACK_CHANNEL >= 1.0, f"key-internal wiring: a {KEY_BACK_CHANNEL} recess in "
         f"the key back gives {kc:.1f} mm above the board-back parts ({KEY_BOARD_BACK_H} [TBD]) for one layer of {CABLE_WIRE_D} "
         f"wires ({R.KEY_BACK_T - KEY_BACK_CHANNEL:.1f} of the back left); fallback AWG32 (0.6) or a flex jumper; board without "
         f"pre-soldered headers")
    for (hx, hy) in [(-R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2), (R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2),
                     (-R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2), (R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2)]:
        g = min(math.hypot(hx - x, hy - y) - R.MX_POST_D / 2 - M2_CSK_D / 2 for (x, y) in R.MX_SW_POS)
        gs = min(math.hypot(max(STOP_X[0] - abs(hx), 0.0), max(abs(hy - sy) - STOP_W_Y / 2, 0.0)) for sy in STOP_YS) - M2_CSK_D / 2 - 0.1
        rule(g >= 0.8 and gs >= 0.2, f"board screw ({hx:+.2f}, {hy:+.2f}) clears the stem posts by {g:.2f} mm and the stop "
             f"bosses by {gs:.2f} mm")
    hx0, hx1 = R.TB_HEADER_PITCH_X / 2 - HEADER_SLOT_W / 2, R.TB_HEADER_PITCH_X / 2 + HEADER_SLOT_W / 2
    web_c = hx0 - CABLE_SLOT[0] / 2
    web_s = min(math.hypot(max(hx0 - abs(hx), abs(hx) - hx1, 0.0), max(HEADER_SLOT_Y[0] - hy, hy - HEADER_SLOT_Y[1], 0.0))
                for (hx, hy) in [(R.TB_HOLE_DX / 2, R.TB_HOLE_DY / 2), (R.TB_HOLE_DX_BOTTOM / 2, -R.TB_HOLE_DY / 2)]) - (M2_CSK_D + 0.2) / 2
    web_w = R.KEY_W / 2 - R.KEY_WALL - hx1
    rule(min(web_c, web_s, web_w) >= 0.8, f"key back with the header slots ({HEADER_SLOT_W} × {HEADER_SLOT_Y[1] - HEADER_SLOT_Y[0]:.1f} "
         f"at x ±{R.TB_HEADER_PITCH_X / 2:.2f}, owner 2026-10-03): webs {web_c:.2f} to the cable slot, {web_s:.2f} to the nearest "
         f"screw countersink, {web_w:.2f} to the wall; the centre strip with the forks stays tied to both solid end regions")
    for (x, y) in SWP_SCREWS:
        edge = rrect_inside(x, y, WELL_IN_X - SWP_CLEAR, WELL_IN_Y - SWP_CLEAR, WELL_R - SWP_CLEAR) - M2_CSK_D / 2
        cut = min(max(abs(x - mx) - R.MX_CUT / 2, abs(y - my) - R.MX_CUT / 2) for (mx, my) in R.MX_SW_POS) - M2_CSK_D / 2
        hous = min(max(abs(x - mx) - R.MX_TOP_W / 2, abs(y - my) - R.MX_TOP_W / 2) for (mx, my) in R.MX_SW_POS) - M2_CSK_D / 2
        slot = max(abs(x) - CABLE_SLOT[0] / 2, abs(y - CABLE_Y) - CABLE_SLOT[1] / 2) - M2_CSK_D / 2
        rule(min(edge, cut, slot) >= 0.8 and hous >= 0.3,
             f"switch-plate screw ({x:+.1f}, {y:+.1f}): web {edge:.2f} to edge, {cut:.2f} to MX cut-out, {slot:.2f} to cable slot, "
             f"{hous:.2f} clear of the MX housing")
    ledge0 = s["plate_back"]
    info("v0.10: switch plate glued onto the ledge (no screws, no bosses)") if not SWP_SCREWS else None
    rule(not SWP_SCREWS or s["plate_front"] + SWP_SCREW_L <= ledge0 + SWP_BOSS_H - 0.3,
         f"switch-plate screw tip d {s['plate_front'] + SWP_SCREW_L:.1f} inside its boss (ends {ledge0 + SWP_BOSS_H:.1f})")
    mx_gap_y = min(abs(y - CABLE_Y) for (_, y) in R.MX_SW_POS) - R.MX_TOP_W / 2
    rule(CABLE_WIRE_D / 2 + 0.5 <= mx_gap_y, f"cable (flat, {CABLE_W:.1f} × {CABLE_WIRE_D}) at y {CABLE_Y} between the MX "
         f"housings ({mx_gap_y:.2f} free each side)")
    rule(LOOP_R >= 5 * CABLE_WIRE_D, f"cable loop bend radius {LOOP_R} = {LOOP_R / CABLE_WIRE_D:.0f} × wire Ø "
         f"(fine-stranded silicone, dynamic ≥ 5×); life target {LOOP_LIFE:,} presses (desk rig) — fallback flex-PCB jumper")
    rule(LOOP_D1 - LOOP_D0 >= 2 * LOOP_R + KEY_TRAVEL / 2 + 2.0, f"loop region {LOOP_D1 - LOOP_D0:.1f} deep for R {LOOP_R} + "
         f"{KEY_TRAVEL / 2:.1f} roll")
    rule(LOOP_D0 >= s["mx_pins"] + 0.3, f"loop starts behind the MX pins (d {LOOP_D0} vs {s['mx_pins']:.1f})")

    # --- C. front zone: frame tunnel, overlaps, depths ------------------------------------------------
    lim = FRAME_OPEN / 2 - FRAME_TUNNEL_MARGIN
    for e in E:
        if e["zone"] != "SELV" or e["d0"] >= WALL_D or e["move"] or e["name"] in ("plate",) or e["name"].startswith("preload"):
            continue
        ext = max(abs(e["x0"]), abs(e["x1"]), abs(e["y0"]), abs(e["y1"]))
        rule(ext <= lim - 0.1, f"{e['name']}: reaches ±{ext:.2f} in front of the wall (frame tunnel ±{lim + FRAME_TUNNEL_MARGIN:.2f} [TBD])")
    fixed = [e for e in E if not e["move"] and e["name"] not in ("switch plate", "collar")]
    near_ok = {frozenset(("duct", "speaker face gasket")), frozenset(("speaker 2030", "speaker face gasket")),
               frozenset(("duct", "speaker 2030")), frozenset(("loop anchor", "cable loop")),
               frozenset(("speaker 2030", "speaker back foam"))} | \
              {frozenset((f"WAGO {i}", f"WAGO {j}")) for i in range(1, 6) for j in range(1, 6) if i != j}   # contacts / gaskets
    for i in range(len(fixed)):
        for j in range(i + 1, len(fixed)):
            a, b = fixed[i], fixed[j]
            if a["name"].startswith("MX") and b["name"].startswith("MX"):
                continue
            dz = min(a["d1"], b["d1"]) - max(a["d0"], b["d0"])
            if dz <= 0:
                continue
            g = gap2d(a, b)
            need = 0.0 if frozenset((a["name"], b["name"])) in near_ok else 0.6
            if g < need - 1e-9:
                rule(False, f"{a['name']} ↔ {b['name']}: {g:+.2f} mm apart in the same depth band "
                     f"d {max(a['d0'], b['d0']):.1f}..{min(a['d1'], b['d1']):.1f} (need ≥ {need})")
    info(f"{len(fixed)} fixed envelopes were checked pairwise above (≥ 0.6 mm wall in the same depth band; errors listed)")
    col = B("collar zone", -COLLAR_OUT_X, COLLAR_OUT_X, -COLLAR_OUT_Y, COLLAR_OUT_Y, 0, 99)
    for e in fixed:
        if e["name"].startswith(("MX", "LED", "hub", "cable", "loop", "WAGO", "speaker back")) or e["d0"] >= s["plate_back"]:
            continue
        rule(gap2d(e, col) >= 0.5, f"{e['name']} stays {gap2d(e, col):.2f} mm outside the collar")
    tip, front, back, cback = sw_depths()
    need_wall = PLATE_T + NUB_H_MIN + NUB_GAP + SW_TOTAL_H + CARRIER[2] + FLANGE_T
    if SW_POS:                                        # v0.11: fixed plate, no plate switches
        ws_r = max(math.hypot(abs(wire_slot(x, y)[0]) + CARRIER_WIRE_SLOT[0] / 2, abs(wire_slot(x, y)[1]) + CARRIER_WIRE_SLOT[1] / 2)
                   for (x, y) in SW_POS)
        ws_in = all(abs(wire_slot(x, y)[0]) - CARRIER_WIRE_SLOT[0] / 2 >= abs(x) - (CARRIER[0] / 2 + 0.2) + 0.1 - 1e-9 and
                    abs(wire_slot(x, y)[1]) - CARRIER_WIRE_SLOT[1] / 2 >= abs(y) - (CARRIER[1] / 2 + 0.2) + 0.1 - 1e-9
                    for (x, y) in SW_POS)
        rule(ws_in and ws_r <= plug_in_half() - 0.8, f"switch wires: the flange slots stay ≥ 0.1 inside the carrier pockets "
             f"and reach r {ws_r:.1f} ≤ the housing's interior − 0.8; the carrier rests on the flange round the slot")
    wx0, wx1, wy0, wy1 = mic_well()
    rule(max(abs(wx0) + 0.8, abs(wy1)) <= plug_in_half() - 0.8 and DECK_HALF_X - (abs(wx0) + 0.8) >= 0.8,
         f"mic wire well {MIC_WELL:.0f} × {MIC_WELL:.0f} beside the pocket (x {wx0:.1f}..{wx1:.1f}, y {wy0:.1f}..{wy1:.1f}), walled "
         f"to the flange: {DECK_HALF_X - abs(wx0) - 0.8:.1f} to the deck edge, inside the housing; the wires leave the carrier "
         f"sideways in an S-loop (no wire between the carrier and a floor); removable foam plug")
    warn("skirt ↔ deck edge on the PIVOT side: 0.10 at rest, ≈ 0.03 at the RSS stop (CAD 'plate without lips ↔ chassis'); "
         "with ±0.1 print tolerance the skirt may touch the deck edge there, where the relative motion is ≤ 0.1 mm → friction "
         "near the hinge, not a stop → coupon row D: press at the far edge 20 ×, it must click and return without sticking; "
         "fallback: sand the skirt's inner face (the plate location then grows to ±0.15, shadow gap ±0.24 RSS)")
    if SW_POS:                                        # v0.11: fixed plate, no plate switches
        rule(NUB_H >= NUB_H_MIN - 1e-9 and WALL_D >= need_wall, f"switch stack from the flange datum (carrier on the flange front "
             f"d {cback:.1f}): plunger tip d {tip:.2f}, nub {NUB_H:.2f} → gap {NUB_GAP}; with the smallest nub {NUB_H_MIN} the "
             f"rocker-front ↔ wall distance may drop to {need_wall:.2f} (assumed {WALL_D} [TBD Q1])")

    # --- C2. floating plate: retention, location, stops, tolerance, forces --------------------------------
    lip_ov = LIP_IN - (HALF - PLATE_SKIRT_T - DECK_HALF_Y)
    rule(lip_ov >= 0.5, f"top drawer lip and bottom snap lips overlap the deck / tongues by {lip_ov:.2f} mm (forward stops)")
    rule(LIP_D0 == DECK_D1 and SNAP_D0 == TONGUE_D1, f"catch faces: top lip d {LIP_D0} = deck back, snap lips d {SNAP_D0} = "
         f"tongue back → plate front at d 0 at rest")
    shift = lip_ov + 0.1
    rule(HALF - PLATE_SKIRT_T - LIP_IN + shift >= DECK_HALF_Y + 0.05, f"top lip hooks behind the rigid top deck edge after a "
         f"{shift:.1f} mm upward shift (plate tilted, bottom edge forward), then the bottom snaps are pressed on")
    clr = HALF - PLATE_SKIRT_T - DECK_HALF_Y
    rule(SKIRT_D - DECK_D0 >= 0.5 and clr <= 0.15, f"skirts overlap the deck edges by {SKIRT_D - DECK_D0:.1f} mm with {clr:.2f} "
         f"clearance → plate located ±{clr:.2f} in x and y (+ print tolerance)")
    tm = tongue_mech()
    rule(tm["eps"] <= MAT_EPS_SNAP, f"bottom tongue ({tm['L']:.1f} × {TONGUE_W} in-plane × {tm['h']:.1f} deep): snap needs "
         f"{tm['need']:.1f} at the lip end nearest the root → root strain {100*tm['eps']:.2f} % (≤ {100*MAT_EPS_SNAP:.1f} %, "
         f"E {MAT_E:.0f} [TBD]); slot root is a full radius")
    rule(SNAP_CHAMFER + TONGUE_CHAMFER >= tm["need"], f"lead-in {SNAP_CHAMFER} (lip) + {TONGUE_CHAMFER} (tongue) = "
         f"{SNAP_CHAMFER + TONGUE_CHAMFER:.2f} ≥ {tm['need']:.1f} needed; tongue first layer {TONGUE_W - TONGUE_CHAMFER:.2f} wide")
    rule(tm["tip"] + 0.1 <= TONGUE_SLOT, f"tongue tip deflects {tm['tip']:.2f} into a {TONGUE_SLOT} slot")
    for (x, y) in SW_POS:
        if y > 0:
            continue
        wall_y = abs(y) + CARRIER[1] / 2 + 0.2 + 0.8
        xa = min(abs(x) + CARRIER[0] / 2 + 0.2 + 0.8, TONGUE_X[1]) - (TONGUE_X[0] + TONGUE_SLOT / 2)
        inner = DECK_HALF_Y - TONGUE_W - tm["defl"](xa)
        rule(inner - wall_y >= 0.2, f"deflected tongue ({inner:.2f}) clears the switch pocket wall at ({x:+.1f}, {y:+.1f}) "
             f"({wall_y:.2f}) by {inner - wall_y:.2f} (d 5.0..{TONGUE_D1})")
    rule(tm["p_yield"] >= PULL_MIN, f"forward pull on the bottom edge: {tm['p_yield']:.1f} N per tongue at yield "
         f"({2 * tm['p_yield']:.0f} N both, ≥ {PULL_MIN} each; MAT_SIGMA_Y {MAT_SIGMA_Y} [TBD]) — top lip is rigid; coupon row D")
    rel0, rel1 = LOC_RIM_SPAN[1] + 0.5, SNAP_X[0] - 0.5 - 0.5
    rule(rel1 - rel0 >= 4.0 and TONGUE_D1 - SKIRT_D >= 1.5, f"release: with the insert out, a 0.5 mm blade slides in sideways "
         f"between the bottom skirt (ends d {SKIRT_D}) and the flange at |x| {rel0:.1f}..{rel1:.1f} and pushes the tongue in "
         f"(window {rel1 - rel0:.1f} × {TONGUE_D1 - SKIRT_D:.1f} mm on the tongue's outer face)")

    if SW_POS:                                        # nub gap and stops (v0.2–v0.10 floating plate)
        # nub gap and stops
        rss_t, worst_t = gap_tol()
        gmin, gmax = NUB_GAP - rss_t, NUB_GAP + rss_t
        chain = "; ".join(f"{n} ±{t}" for n, t, _ in GAP_CHAIN)
        rule(gmin >= -SW_PT_MIN + 0.1, f"nub gap {NUB_GAP} ± {rss_t:.2f} RSS → {gmin:.2f}..{gmax:.2f}: never pre-actuated at rest "
             f"(needs > −{SW_PT_MIN}); chain: {chain}")
        warn(f"nub gap worst-case sum ±{worst_t:.2f} → {NUB_GAP - worst_t:.2f}..{NUB_GAP + worst_t:.2f}: a single switch can pre-click "
             f"or click late → assembly check per switch; correct with {SHIM_STEP} mm polyimide shims under the carrier or by "
             f"sanding the nub; coupon v1 row D at ≤ 0.1 mm layers with real carriers")
        info(f"switch bottom-out travel {SW_TRAVEL_TOTAL} is an ASSUMPTION (= PT max {SW_PT_MAX} [DS]); coupon v1 row D measures it")
        t_click = gmax + SW_PT_MAX
        t_stop = gmax + SW_TRAVEL_TOTAL + SEAT_ALLOW
        t_edge = edge_travel(t_stop)
        t_edge_w = min(edge_travel(NUB_GAP + worst_t + SW_TRAVEL_TOTAL + SEAT_ALLOW), DECK_D0 - PLATE_T)   # the deck stops it
        rule(PLATE_T + t_edge < DECK_D0 - 0.1, f"switches are the travel stop: plate travels ≤ {t_stop:.2f} at a switch (RSS; click "
             f"≤ {t_click:.2f}; {SEAT_ALLOW} seating allowance), ≤ {t_edge:.2f} at a plate corner; plate back {DECK_D0 - PLATE_T - t_edge:.2f} "
             f"off the deck")
        warn(f"worst-case stack: a late switch clicks only after {NUB_GAP + worst_t + SW_PT_MAX:.2f}, while the plate corner lands on "
             f"the deck after {DECK_D0 - PLATE_T:.2f} (corner/switch travel ratio ≈ {edge_travel(t_stop) / t_stop:.2f}) → that switch may NOT click when pressed at "
             f"the corner; the per-switch assembly check finds it and a shim fixes it (§11)")
        rule(ABUSE_FORCE <= SW_MAX_FORCE, f"abuse: {ABUSE_FORCE:.0f} N palm slap, worst case on ONE switch (diagonal pivots) vs "
             f"{SW_MAX_FORCE:.0f} N [TBD — Omron publishes no static load] → coupon row D: 30 N on one cell for 1 min; fallback: a "
             f"printed stop ring around each nub, sanded to land 0.1 after the click", hard=False)
    else:
        t_edge = t_edge_w = 0.0
        info(f"v0.11 fixed plate (owner 2026-10-08: 'Nur MX, Blende fest'): it rests on {len(S_REST_PADS)} Ø2.4 pads on the deck "
             f"front (d {DECK_D0}) and is held forward by the top lip and the bottom snap lips; no plate travel, no plate "
             f"switches. The only buttons are the 2 MX under the key")
    rule(PLATE_T + t_edge <= LOC_RIM_D0 - 0.1, f"frame locating rims (d {LOC_RIM_D0}..{WALL_D - FLANGE_T}) stay behind the "
         f"pressed plate skin (d ≤ {PLATE_T + t_edge:.2f}, RSS)")
    rule(LOC_RIM_SPAN[0] - SKIRT_GAP[0] >= 0.5 and SKIRT_GAP[1] - LOC_RIM_SPAN[1] >= 0.5,
         f"8 frame rims (|along| {LOC_RIM_SPAN[0]}..{LOC_RIM_SPAN[1]}) sit in the skirt/lip gaps (|{SKIRT_GAP[0]}..{SKIRT_GAP[1]}|) "
         f"with ≥ 0.5 to the skirt ends")
    eng = PLUG_STOP_D - LOC_RIM_D0
    rule(eng >= 1.0, f"rims (outer faces ±{RIM_OUT:.2f}) reach {eng:.1f} mm into the carrier's tunnel (to d {PLUG_STOP_D}) → "
         f"the insert is located ±{FRAME_TUNNEL_MARGIN} in x and y")
    fg = (FRAME_OPEN - PLATE) / 2
    th_edge = t_edge / (HALF + DECK_HALF_Y)                # plate tilt at the stop (band press, pivot at the far lip)
    shift = th_edge * SNAP_D0                              # the pressed edge's front moves outward (pivot ≈ 6.5 behind it)
    gp = fg - FRAME_TUNNEL_MARGIN - clr - shift
    rule(gp >= 0.0, f"plate ↔ frame: {fg:.2f} nominal; at rest ≥ {fg - FRAME_TUNNEL_MARGIN - clr:.2f} (frame on its rims, plate at its "
         f"skirt clearance); pressed at an edge the front edge moves out {shift:.2f} → ≥ {gp:.2f} [TBD Q2, print tolerance not "
         f"included]; if the measured opening is < 55.6: chamfer the plate's front edge 0.2 × 45° and recut the rims", hard=False)
    rule(PLATE_T + t_edge + 0.0 <= DECK_D0, "pressed plate stays in front of the deck (RSS stack)")
    wall_min = max(need_wall if SW_POS else 0.0, LIP_D1 + t_edge + FLANGE_T + 0.2, SNAP_D1 + t_edge_w + 0.3)
    warn(f"Q1 threshold: this geometry needs a plate-front ↔ wall distance ≥ {wall_min:.1f} mm (the snap lips must end "
         f"0.3 before the wall{' at the worst-case press' if SW_POS else ''}); assumed {WALL_D} "
         f"[TBD Q1]. Above it the chassis is regenerated for the measured value; below it the deck, lips and tongues must be "
         f"made thinner (redesign) — Q1 gates the first print")
    rule(LIP_D1 + t_edge <= WALL_D - FLANGE_T - 0.2, f"pressed top lip (d ≤ {LIP_D1 + t_edge:.2f}) clears the flange "
         f"(d {WALL_D - FLANGE_T:.1f})")
    rule(SNAP_D1 + t_edge_w <= WALL_D - 0.3 and SNAP_RELIEF[0] <= SNAP_X[0] - 0.5 - 0.3 and SNAP_RELIEF[2] <= DECK_HALF_Y - TONGUE_W
         - tm["tip"] - 0.1, f"pressed snap lips (d ≤ {SNAP_D1 + t_edge_w:.2f} worst case) move into the flange windows and end "
         f"{WALL_D - SNAP_D1 - t_edge_w:.2f} before the wall plane")
    if SW_POS:
        rule(SW_LIFE >= 20 * 365 * 30, f"switch life {SW_LIFE:,} per switch ≥ 30 years × 20 presses/day (worst case: every press on "
             f"the same switch)")
    kp = pad_k()
    pre = kp * (PAD_H - (DECK_D0 + PAD_POCKET - PLATE_T)) * len(PAD_POS)
    w = PLATE_MASS_G * 9.81e-3
    rule(pre >= 3 * w, f"anti-rattle preload: {len(PAD_POS)} soft pads ({PAD_SIZE[0]}×{PAD_SIZE[1]}×{PAD_H}, CLD40 {PAD_CLD40} kPa "
         f"[TBD]) give {pre:.2f} N ≥ 3 × plate weight {w:.3f} N; the nubs do not touch the plungers at rest")
    if SW_POS:
        fmap = {k: press_force(*p) for k, p in PRESS_POINTS.items()}
        fs = [f[0] for f in fmap.values() if f]
        txt = "; ".join(f"{k} {f[0]:.1f} N ({f[1]} sw)" for k, f in fmap.items() if f)
        fmax_tol = max(press_force(*p, of=SW_OF + SW_OF_TOL)[0] for p in PRESS_POINTS.values())
        rule(len(fs) == len(PRESS_POINTS) and 1.2 <= min(fs) and fmax_tol <= 5.0, f"press force {min(fs):.1f}–{max(fs):.1f} N "
             f"nominal incl. pads, ≤ {fmax_tol:.1f} N at OF max (limit 5): {txt}")
        info("press feel (model): the plate tips about its easiest supporting line — at every tested point a diagonal or edge "
             "line on which ONE switch clicks (even at a band centre, where two lines tie); pressing on to the stop may click a "
             "second switch. The 4 B3FS are in parallel, so PLATE sees one closure either way (bounce ≤ 5 ms [DS] < the ES75's "
             "20 ms minimum command)")
    info("no gaskets between plate and chassis: the plate–deck gap is part of the speaker's front volume; it opens to the room "
         "(strip holes 41 mm², shadow gap ≈ 140 mm², frame gap) and, through small slots (key/collar 0.25, switch-plate cable slot, "
         "the foam-plugged mic wire well), to the box; the speaker's back is its own sealed cavity, so the box leak costs little — measure")

    # --- D. plug-in housing (v0.12: RoomKey is built only as the plug-in device, owner 2026-10-31) -------------------
    h_in = plug_in_half()
    for e in E:
        if e["d1"] <= WALL_D or e["move"]:
            continue
        rmax = max(abs(e["x0"]), abs(e["x1"]), abs(e["y0"]), abs(e["y1"]))
        rule(rmax <= h_in, f"{e['name']}: |x|, |y| ≤ {rmax:.2f} inside the housing's interior behind the flange (±{h_in:.2f})")
    info(f"v0.11 hub: the real PCB (hardware/pcb/roomkey-hub, routed, DRC 0) at d {HUB_PCB_D0:.1f}–{HUB_PCB_BACK:.1f}, "
         f"screwed (M2) to 2 chassis posts + 1 switch-plate post; parts and outline are checked in the CAD as its STEP")
    sk = plug_skin_in(WALL_D - FLANGE_T)
    rule(FLANGE_HALF <= sk - 0.25 and FLANGE_HALF - FRAME_OPEN / 2 >= 1.5,
         f"flange ±{FLANGE_HALF}: inside the skin (±{sk:.2f} there) and on the tunnel's back end over "
         f"{FLANGE_HALF - FRAME_OPEN / 2:.1f} mm all round")
    for b_ in ("pcb", "discrete"):
        dp = plug_depths(b_)
        info(f"{b_} build: glass → socket {dp['socket'] - KS['glass']:.1f} mm, the device {PLUG_OFFSET} mm above the "
             f"socket centre, outline {2 * PLUG_HALF:.0f} × {2 * PLUG_HALF:.0f}")

    # --- E. electrical: 5 V SELV only ------------------------------------------------------------------------------
    info("RoomKey takes only 5 V SELV from an unmodified, certified plug-in USB charger (class II) held in the housing; no "
         "230 V part is designed, modified or wired by this project, nothing of the RoomKey touches 230 V")
    avg5 = sum(a for a, _ in LOADS_W.values())
    pk5 = sum(p for _, p in LOADS_W.values())
    rule(pk5 / 5.0 <= 0.8 * CHARGER_A, f"power {avg5:.2f} W avg / {pk5:.2f} W peak at 5 V → {pk5 / 5.0:.2f} A ≤ 80 % of the "
         f"charger's {CHARGER_A} A")
    key_heat = AVG_NO_PS_W
    dT = key_heat / (H_CONV * KEY_AREA_CM2 * 1e-4)
    warn(f"key self-heating: ≈ {key_heat:.2f} W in the key (the firmware runs Wi-Fi without power-save) → ΔT ≤ {dT:.0f} K on the "
         f"key surface (upper bound, no conduction into the chassis); mitigation: backlight dimming (and power-save if the "
         f"intercom allows it) — measure (thermocouple, 1 h)")
    warn(f"the charger warms the housing (≈ {0.25 * avg5:.2f} W loss at {avg5:.2f} W): the humidity sensor sits at the front of "
         f"the bottom wall, as far from it as the housing allows, its vents draw room air from below — compare against a "
         f"reference sensor for a day")

    # --- F. acoustics, RF, sensors -------------------------------------------------------------------
    n_holes = PERF_COLS * PERF_ROWS
    area = n_holes * math.pi * PERF_D ** 2 / 4
    m0, m1, n0, n1 = mouth()
    pd0, pd1 = port_d()
    gx = grille_x()
    path = (pd1 - DECK_D1) + (m1 - gx) / 2 + (DECK_D1 - DECK_D0) + PLATE_T
    f_q = C_SOUND / (4 * path)
    info(f"speaker path: grille → foam face gasket (pressed by the {SPK_BACK_FOAM[0]} foam strip behind the speaker) → channel → "
         f"plenum (mouth in the deck, floor d {DECK_D1}–{SPK_D0} over the speaker edge) → {n_holes} × Ø{PERF_D} = {area:.0f} mm²")
    warn("mic path: Ø1.0 × 2 mm port + 0.1 PSA ring on an FDM surface — desk-rig test with tools/mic_check.py through a printed "
         "plate coupon (target: ≤ 6 dB below the bare mic, no peak > 6 dB below 4 kHz); fallbacks: ironed seal land, 0.5 mm "
         "die-cut gasket, port Ø1.2")
    warn(f"acoustic: quarter-wave of the ≈ {path:.0f} mm path ≈ {f_q/1000:.1f} kHz lies in the chime band (2.5–4 kHz) → measure the "
         f"response through the printed duct + plate + mesh, not the bare speaker")
    pw = LOADS_W["MAX98357A + speaker (chime, volume-capped to 1.1 W, seconds)"][1] * 0.9
    lo = SPK_SENS_RANGE[0] + 10 * math.log10(pw) - 20 + HALF_SPACE_DB
    hi = SPK_SENS_RANGE[1] + 10 * math.log10(pw) - 20 + HALF_SPACE_DB
    warn(f"SPL at 1 m ≈ {lo:.0f}–{hi:.0f} dB ({pw:.1f} W, +{HALF_SPACE_DB:.0f} dB wall, sensitivity {SPK_SENS_RANGE[0]:.0f}–"
         f"{SPK_SENS_RANGE[1]:.0f} dB/1 W/10 cm [TBD]) vs target {SPL_TARGET[0]:.0f}–{SPL_TARGET[1]:.0f} (Q6). Fallback: the "
         f"RoomKey is the secondary chime — the main bell / HA media players carry the loud signal")
    ant = byname["antenna chip"]
    rule(ant["d1"] < 0, f"antenna chip at d {ant['d0']:.1f}..{ant['d1']:.1f} ({-ant['d1']:.1f} mm in front of the plate at rest; "
         f"pressed {ant['d0'] + KEY_TRAVEL:.1f}..{ant['d1'] + KEY_TRAVEL:.1f}, inside the plate aperture)")
    mx2 = R.MX_SW_POS[1]
    ay0 = R.TB_ANT[1] + R.TB_ANT[3] / 2
    inplane = abs(ay0) - (abs(mx2[1]) + 2.5)          # antenna edge ↔ spring edge in plan (≥ 0: the spring is beside it)
    d_spring_rest = math.hypot(max(inplane, 0.0), (s["mx_top"] + 2.0) - ant["d1"])
    d_spring_pr = math.hypot(max(inplane, 0.0), (s["mx_top"] + 2.0) - (ant["d1"] + KEY_TRAVEL))
    d_frame = FRAME_OPEN / 2 - abs(R.TB_ANT[1] - R.TB_ANT[3] / 2)
    rule(d_spring_pr >= RF_MIN_METAL, f"antenna chip ↔ MX2 spring ≈ {d_spring_rest:.1f} mm rest / {d_spring_pr:.1f} pressed "
         f"(≥ {RF_MIN_METAL:.0f} wanted; in plan the spring is {inplane:.1f} beside the chip); closer metal: the MX2 contact "
         f"leaves and pins (housing 5.0 pressed, check JSON), the 14 cable wires at the header (≈ 6–7 mm), the board's brass "
         f"standoffs (5 mm, given); farther: speaker ≈ 15, LED carriers ≈ 13, box screws ≈ 32. Fallbacks: MX2 rotated so its "
         f"leaves face +y (away), RSSI test R7 with the cable wired, retune, access point", hard=False)
    rule(d_frame >= RF_MIN_METAL, f"a METAL frame edge would be {d_frame:.1f} mm from the chip in-plane [TBD Q2 frame material]",
         hard=False)
    warn("RF acceptance (bench): RSSI bare board vs in key vs in wall, rest/pressed, with a hand: ≤ 6 dB loss and ≥ −70 dBm at "
         "the position; fallbacks: retune the board's π-network (C25/C2/C1 [DS ws_sch]), access point / mesh node in the room")
    info(f"optional sensors deferred to v1 ({', '.join(SENSORS_DEFERRED)}): wings are full; LD2410C 16 mm > {wing:.1f} mm wing")

    if verbose:
        print(f"\n=== Variant {v} (insert v{VERSION}) " + "=" * 60)
        for m in errs:
            print("ERROR   ", m)
        for m in warns:
            print("WARNING ", m)
        for m in infos:
            print("INFO    ", m)
        for m in oks:
            print("OK      ", m)
        print(f"\nVariant {v}: {len(errs)} error(s), {len(warns)} warning(s), {len(oks)} ok, {len(infos)} info (assumptions, "
              f"not counted as checks)")
    return errs, warns, oks


TBD_LIST = [
    ("end presses", "?", "desk rig: press the printed key every 5 mm along its length (1000 × at each end) → stabiliser?"),
    ("KEY_WOBBLE_DEG", KEY_WOBBLE_DEG, "desk rig: tilt of the key on its stems under an edge press"),
    ("touch vs key", "?", "desk rig R13: swipes / taps must not fire the key (0 key-downs in 300 gestures)"),
    ("TB_ANT size", R.TB_ANT[2:], "Q8 chip antenna size (drawing gives the position only)"),
    ("mic path", "?", "desk rig: tools/mic_check.py through a printed plate coupon"),
    ("SPK sensitivity", SPK_SENS_RANGE, "Q6 SPL through the printed duct at 1 m — and is ~65–70 dB acceptable?"),
    ("PLATE_CORNER_R", PLATE_CORNER_R, "Q7 rocker corner radius; rocker flat or curved?"),
    ("TB standoffs", R.TB_STANDOFF_THREAD, "Q8 brass standoffs female M2? (else M2 nuts / glue-in inserts)"),
    ("KEY_BOARD_BACK_H", KEY_BOARD_BACK_H, "Q8 component height on the board back; board without pre-soldered headers"),
    ("MX_POST_D / MX_WINDOW", (R.MX_POST_D, R.MX_WINDOW), "coupon: stem posts in the MX housing window"),
    ("glow look", "?", "Q12 desk rig: glowing gap (as built) or dark gap + lit rim (mask the collar's inner 0.75)?"),
    ("PLUG_GRIP inter", PLUG_GRIP["inter"], "grip-ring coupons 1/2/3 on the real charger: which holds it without forcing"),
    ("PLUG_USB", PLUG_USB, "the bare solder-type USB-A plug bought: shell, cups, which cup is VBUS"),
    ("PLUG_INSERT", PLUG_INSERT, "the M3 heat-set inserts bought: hole Ø and depth"),
    ("PLUG_SKIN", PLUG_SKIN, "resin thread: wall thickness and draft the mould and the resin need"),
    ("PLUG_J1", PLUG_J1, "PCB rev D: J1 side-entry part and place; sensor tail outline"),
]


def print_tbd():
    print("[TBD] values and what to measure/decide:")
    for k, val, q in TBD_LIST:
        print(f"  {k:36s} = {val!s:22s} {q}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    if "--tbd" in args:
        print_tbd()
        raise SystemExit(0)
    vs = [a for a in args if a in VARIANTS] or list(VARIANTS)
    bad = 0
    for vv in vs:
        e, _, _ = validate(vv)
        bad += len(e)
    raise SystemExit(1 if bad else 0)
