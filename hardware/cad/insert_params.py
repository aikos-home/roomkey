"""RoomKey wall insert v0.8 (DRAFT / WIP, AI-assisted, not certified) — every dimension of the in-wall part, both variants.

    python3 hardware/cad/insert_params.py          # validate L and S
    python3 hardware/cad/insert_params.py L        # one variant
    python3 hardware/cad/insert_params.py --tbd    # every [TBD] value and what to measure

v0.2 (after review round 1): SELV-only insert; floating plate on 4 tactile switches; light-guide collar; mic carrier;
    cable U-loop; horizontal hub; installation topologies T1–T4 / S1–S3.
v0.3 (after review round 2, see hardware/reviews/insert-v0-review-log.md):
  * No foam gaskets: the mic carrier is bonded to the plate (moves with it); the speaker path is sealed at the speaker
    (face gasket + plenum floor), the plate–deck gap is part of the front volume. Three small soft pads preload the plate.
  * Glow ring = a translucent rim of the plate around the key opening (co-printed, natural PETG), lit from the collar
    behind it → visible from every angle. LEDs centred on the collar's thick (2.6) corners.
  * Nub-gap chain from the flange datum (carrier rests on the flange), explicit tolerance list, per-switch shims.
  * Key: the MX stems are the guide; the key skirt is on the long sides only (free pitch for edge presses), the collar
    limits roll.
  * Frame rims on all four sides; stainless load plates under the box screws; speaker snap hooks; island ribs.
  * Topologies: switch-box inventory first, TN-C precondition, core table, "new cable" outcome, T4 needs its own 12 V,
    power-limited SELV source, labelling, ES75/Kaiser facts corrected.
  * validate(): INFO lines for assumptions (never counted as OK), fit-critical [TBD] rules are hard.
v0.4 (after review round 3):
  * Plate switches: SMD Omron B3FS-1002P (3.1 ± 0.2) on flat-backed carriers (no solder under the datum); 1.4 mm more
    front-zone depth (works down to 7.6 mm rocker-to-wall).
  * Key: MX at (0, +15) / (0, −13) (overhang 8.4 / 10.4 like a keycap edge); no stop bosses, no pitch model (it was not
    physical); end presses are a desk-rig test with a stabiliser fallback.
  * Hub: 250 V entry fuse, eFuse on the hub branch (a hub short no longer collapses the 12 V of the light path), FMEA.
  * Terminal zone = 5 modelled WAGO 221-412; speaker preloaded onto its face gasket; key-back cable channel.
  * CAD checks the key + stems wobbled ±1.5° without the key ↔ housing exemption; one layer height (0.10) for plate,
    chassis and coupon; V-0 chassis mandatory.
v0.5 (after review round 4; NOT reviewed by a fresh round — the loop stopped, see the review log):
  * Q1 threshold derived from the retention (≥ 8.9 mm), not only from the switch stack.
  * Misconnection: matrix per conductor (the entry fuse protects only one case), verification + RCD as preconditions.
  * Hub: RELAY_DRIVE pull-down + qualifier (IO5 floats at reset), eFuse checked against the summed peak with tolerance
    (60 V class, OVLO 17 V, SMBJ24A), bleeder in L and S; SNT61 overload = Q4f.
  * RF spring distance corrected (sign error: 8.1 mm pressed, WARN); thicker speaker hooks; mic wire well with an S-loop;
    key channel along the real header; touch-vs-key and power-cut items with assumption, test and fallback.
v0.6 (the owner's first print and wishes; NOT reviewed):
  * Rocker key: both MX read separately, centre press = both (forks, stop bosses, tapered ends, rock + wobble checks).
  * Wider middle cable slot + header slots for pins / wires straight back from the touch-board header.
  * Real speaker dimensions, LED corner notches (WS2812B-MINI 3535, 2.0 high), push-out removal.
  * §6 practice box and §7 kit (whole RoomKey in one box, bench supply) — prototypes only.
v0.8 (the owner's first kit assembly, 2026-10-04: the rocker key fell out; NOT reviewed):
  * Key catch: a rigid nub on each side skirt in a groove of the collar (open to the back, closed to the room) → the key
    is captive; the collar is no longer glued. Stem fork gap 4.10 → 3.90 (the stem arm is ≈ 4.0: 4.10 clamped nothing).

Tags: [DS] datasheet / norm / vendor drawing (source in SOURCES) · [MEAS] measured on the real part ·
      [FREE] design choice · [TBD] placeholder or assumption until measured (listed by --tbd).
Coordinates: front view, origin = plate centre on the plate FRONT face; x right, y up;
      d = depth into the wall (+). CAD maps (x, y, d) -> (X, Y, Z = -d): +Z points into the room.
Nothing here is certified. All 230 V work: a qualified electrician of a registered installation company (NAV §13,
insert-design.md §9).
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import roomkey_params as R  # noqa: E402

VARIANTS = ("L", "S")
VERSION = "0.10.3"

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
# 1. WALL, FRAME, BOX, FLANGE
# =====================================================================================================
PLATE = R.ROCKER_W                 # 55.0 [MEAS, FROZEN]
HALF = PLATE / 2
WALL_D = 9.0          # [TBD] plate front ↔ wall / box-rim plane. 55-system rockers sit ~8–11 mm proud. MEASURE (Q1).
FRAME_OPEN = 55.6     # [TBD] frame opening (rocker 55.0 [MEAS] + ~0.3 per side). MEASURE (Q2).
FRAME_OUT = 80.5      # [DS] Jung AS 500 1-gang frame 80.5 × 80.5 — owner's series CONFIRMED 2026-10-03 ("Jung AS500");
                      #      vendor lists the inner size as "55 × 55" (nominal) → the real opening still to measure (Q2)
FRAME_BACK_FREE = 3.5  # [TBD] free depth under the frame for support flange + screw heads. MEASURE (Q2).
FRAME_TUNNEL_D = WALL_D - FRAME_BACK_FREE   # [TBD] depth of the frame's opening tunnel (5.5), the rims reach into it
FRAME_RETENTION = None  # [TBD] "ring" (frame clips onto the support ring) or "centre" (held by the rocker). ASK/PHOTO (Q2).
FRAME_MATERIAL = "plastic"   # [DS] Jung AS 500 = plastic program (owner 2026-10-03) → no metal near the antenna or the radar
FRAME_TUNNEL_MARGIN = 0.1  # [FREE] min gap between any fixed part and the frame tunnel wall (the rims locate at this gap)

BOX_OPEN_D = 60.0     # [DS din49073] installation opening Ø60
BOX_OUTER_D = 68.0    # [DS din49073] outer Ø ≈ 68 = hole saw
BOX_USABLE_D = 58.0   # [TBD] usable inside Ø at depth (walls taper, ribs) — assumption. MEASURE (Q5).
BOX_SCREW_PITCH = 60.0  # [DS din49073]
BOX_DOME_ANGLES = (0, 90, 180, 270)  # [DS kaiser1555] 4 screw domes (60 mm both ways)
BOX_DOME_R_IN = 26.0  # [TBD] how far the domes reach inwards (radius). MEASURE (Q5).
BOX_DOME_W = 7.0      # [TBD] dome width, tangential
BOX_DOME_R_OUT = 33.0  # [FREE] modelling extent of a dome
BOX_FLOOR_LOSS = 2.0  # [TBD] nominal depth − usable depth (floor, entries)
BOX_DEPTH = 40.0      # [TBD] the insert is SELV-only → it must fit an old standard 40 mm box
FIT_MARGIN = 0.5      # [FREE] min gap part ↔ box wall / dome
SCREW_USE = "horizontal"   # [FREE] box screws at (±30, 0): steel away from the antenna at the key's bottom end
SCREW_D = 3.2         # [TBD] German device screws ("Geräteschrauben") Ø3.2
SCREW_HEAD_D, SCREW_HEAD_H = 6.0, 1.8   # [TBD] low pan head ≤ 1.8 (the frame's free depth is the limit)
SCREW_L = 15.0        # [FREE]
SCREW_TORQUE = 0.2    # [FREE] N·m, snug
CLAMP_N = 250.0       # [FREE] clamp at 0.2 N·m, 3.2 mm self-tapping into the box dome (K ≈ 0.25) → 250 N. Nothing limits
                      #        over-torque mechanically: snug by hand with a screwdriver, no power tool (doc §7, §11)
LOAD_PLATE = (-4.5, 5.3, 4.4, 0.5)   # [FREE] stainless load plate under each screw head: x from..to (relative to the screw,
                                     #        outward +), half height, thickness; in a 0.5 recess of the flange front face
FLANGE_T = 1.2        # [FREE] printed support flange (option: the program's steel support ring, doc §7)
FLANGE_HALF = 35.5    # [FREE] 71 × 71 like a standard support ring
FLANGE_SLOT_W, FLANGE_SLOT_L = 3.6, 9.0   # [FREE] screw slots 3.6 × 9 (±2.5 mm rotation adjustment)
PETG_CREEP_MPA = 5.0  # [FREE] bearing stress limit for PETG/ASA under a permanent clamp at up to 50 °C (conservative)
RIM_T = 1.0           # [FREE] frame locating rims: thickness
LOC_RIM_SPAN = (4.5, 15.0)   # [FREE] each rim runs |along| 4.5..15 on all four sides (8 rims)
LOC_RIM_D0 = 3.5      # [FREE] rims stand from the flange to d 3.5: 2.0 mm inside the frame tunnel [TBD], behind the plate skin
RIM_OUT = FRAME_OPEN / 2 - FRAME_TUNNEL_MARGIN      # rim outer face (27.7): cut to the MEASURED opening − 0.1 (Q2)


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
ANCHOR = (-11.5, 11.5, -8.4, -7.4, 24.0, 25.2)   # [FREE] bar that clamps the fixed leg (x0,x1,y0,y1,d0,d1)
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
S_PLATE_FIXED = False  # [FREE] S default: plate works like L (plate → ESP only); True adds 4 rest pads → fixed plate
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
SW_POS = ((-20.7, 19.5), (20.7, 19.5), (-20.7, -19.5), (20.7, -19.5))   # [FREE] 4 × Omron B3FS-1002P (SMD), one per wing corner
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
HUB_POSTS = ((-13.2, 4.0), (13.2, 4.0), (-13.2, 20.0), (13.2, 20.0))   # [FREE] from the ledge (lower pair fused to the boss bridges)
HUB_PARTS = {         # [TBD]/[DS] heights behind the hub PCB (mm): must stay inside HUB
    "Traco TSR 1-2450 (SIP-3, standing)": 10.1,   # [DS traco] 11.7 × 7.5 × 10.1
    "2 × 100 µF/25 V polymer (D-case, 7.3 × 4.3)": 3.1,   # [TBD]
    "MAX98357A bare IC (QFN 3 × 3) + passives": 1.0,
    "wire solder pads / JST-SH": 4.3,
    "TVS, PTCs, FETs, AHCT buffer, eFuse": 2.3,
    "entry fuse (SMD 250 V AC)": 3.1,
}
HUB_FOOTPRINTS = {    # [TBD] mm² estimates (body + pads)
    "TSR 1-2450": 88, "2 × polymer caps": 63, "MAX98357A + 6 passives": 40, "SMBJ24A": 17, "plate PTC 1206": 10,
    "2 × P-FET + 2 × NPN + gate Zeners (SOT-23 / SOD-323)": 34, "Schottky VBUS feed": 6, "74AHCT1G125": 9,
    "2 × ESD arrays (SOT-23-6)": 18, "≈ 25 passives 0603": 50,
    "wire pads: 3 pigtail + 14 cable + 8 switch + 3 LED + 2 SPK + 2 MX + 5 mic": 111,
    "eFuse (60 V class, ILIM ≈ 0.43 A ± 7 % [TBD part], 3 × 3) + passives": 20,
    "entry fuse 250 V AC SMD (≈ 10 × 3) + 3 mm creepage keep-out": 45, "470 µF bulk at the amp (5 V)": 40, "series Schottky + S bleeder": 10,
}
HUB_ROUTING = 1.3     # [FREE] layout overhead factor
HUB_FRONT_STRIPS = ((-16.0, -8.3), (8.3, 14.8))   # [FREE] hub FRONT side usable beside the MX1 body (x ranges), height 7.7
SELV_IN = "3 conductors: +12 V, 0 V, PLATE (L) — pigtail H05V-K 0.5 mm², joined with WAGO 221 in the box"   # [FREE]
HUB_VIN = (10.5, 16.0)   # [FREE] accepted input (eFuse OVLO 17 V, TVS SMBJ24A, TSR 6.5–36 V, B3FS ≤ 24 V): a 12 V or 15 V SELV source
ENTRY_FUSE = ("1 A slow-blow, 250 V AC, breaking capacity ≥ 1500 A (SMD, Schurter UMT-H class — verify), ≥ 3 mm creepage "
              "around it and the pigtail pads")   # [TBD part] only in +12 V: PLATE and 0 V are NOT fused (doc §8.1)
EFUSE = (0.43, 0.07, 17.0)   # [TBD part] hub-branch eFuse (60 V class): current limit (A), its tolerance (±), OVLO (V); soft-start
PLATE_PTC = (0.050, 10.0, 30.0)   # [TBD part] PTC in the switch feed: hold (A), R (Ω), V max ≥ 30 V; fed from the pigtail
S_BLEEDER = 4700.0    # [FREE] Ω on PLATE in BOTH variants (≈ 2.5 mA: inside the rated 1–50 mA whatever relay input is fitted)
SW_MIN_LOAD = 10e-6   # [DS b3fs] minimum applicable load 10 µA at 1 V DC (the 1–50 mA is the rating)
WAGO = (13.1, 8.3, 18.6)   # [DS wago221] 221-412 (w, h, d)
WAGO_POS = (               # [FREE] 5 × 221-412 standing (18.6 along d): 3 SELV joints + PE cap + spare-core cap
    (-12.45, -4.15, -24.1, -11.0), (-4.15, 4.15, -24.1, -11.0), (4.15, 12.45, -24.1, -11.0),     # x0, x1, y0, y1 (bottom row)
    (-24.9, -16.6, -13.2, -0.1), (-24.9, -16.6, 0.1, 13.2),                                        # left column
)
WAGO_D = (25.6, 44.2)     # [FREE] depth range of the WAGO bodies (conductors enter from the box floor side)
IO_MAP = {            # [DS ws_sch] header pins used by the insert (firmware change pending for IO3 — WIP)
    "IO4": "SK6812 data (via AHCT buffer)", "IO7": "I²S BCLK", "IO8": "I²S WS (+10k pull-up on the hub: download mode needs IO8 = 1)",
    "IO16": "I²S DOUT → MAX98357A", "IO17": "I²S DIN ← mic", "IO5": "RELAY_DRIVE (reset-low, one-shot on the hub)",
    "IO3": "PLATE_SENSE, active low via NPN (board 10k pull-up); mic L/R moves to the carrier", "SDA/SCL": "only if a TCA9534 is fitted",
    "IO9": "BOOT = key (board 10k + 100 nF)",
}

# =====================================================================================================
# 5. INSTALLATION TOPOLOGIES (230 V only in certified devices, never in the RoomKey chamber)
# =====================================================================================================
TOPOLOGIES = {
    "T0": "none possible without a new cable: the owner decides (new cable in conduit / surface duct, or no RoomKey here)",
    "T1": "remote: relay + 12 V PSU where the switch leg ends. T1a: at the luminaire / ceiling outlet box (canopy or a surface "
          "box); T1b: the leg ends in a wall junction box → a new or larger box (plaster work). The leg's non-PE cores become "
          "SELV (needs ≥ 3, e.g. NYM-J 4×1.5 / 5×1.5); no N at the switch. Relay: ES75 (SELV input; needs ≤ 10 A protection; "
          "LED rating conflicting, Q4b) or T1-LED: Finder 38.51 (DIN rail) + LED-rated ESR61NP in a 1-row surface DIN "
          "enclosure ≥ 95 mm deep",
    "T2": "two-chamber box at the switch (Kaiser 1068-02 or successor, box change + chiselling, front geometry of chamber 2 "
          "Q11): SNT61 + relay in chamber 2 behind the partition; needs N at the switch; relay input must be DECLARED SELV "
          "(ESR61NP only with Eltako's written confirmation, Q4a)",
    "T3": "distribution board: DIN-rail PSU (safety isolating, ≤ 15 W or fused 0.5 A) + reinforced coupling relay + an impulse "
          "relay with an LED rating; needs a spare cable board → switch (SELV) AND a switched-L path board → lamp (usually conduit)",
    "T4": "keep the old switch (light as before) and add the RoomKey in a SEPARATE added box (2-gang frame); needs its own "
          "12 V SELV feed: a new 2-core SELV cable from a PSU elsewhere, or N + a PSU in a partitioned chamber; the added "
          "box must not be coupled openly to the 230 V box",
}
TOPOLOGIES_S = {
    "S1": "two-chamber box at the socket position (Kaiser 1068-02 or successor, box change): SNT61 + WAGO through-terminals "
          "for an onward feed (L, N, PE) in chamber 2; the RoomKey chamber carries only the 12 V pigtail",
    "S2": "remote 12 V: SELV from a PSU elsewhere over a cable of its own; the 230 V cable to this box is disconnected at BOTH "
          "ends, or rerouted if it fed further sockets — never left in the RoomKey chamber",
    "S3": "keep the socket: RoomKey in a SEPARATE added box (not coupled openly to the socket box), 2-gang frame, 12 V per S2",
}
SWITCH_LEG_CORES = {  # usable non-PE cores in the switch leg → what is possible (T2 additionally needs N IN the box)
    2: "NYM-J 3×1.5 (the common case): T1 impossible (needs 3 SELV cores) → T2 (if N in the box), T3 (spare cable), T4, or T0",
    3: "NYM-J 4×1.5: T1 possible (+12 V, 0 V, PLATE)",
    4: "NYM-J 5×1.5: T1 + a 4th SELV core for light-state feedback (option)",
}
SOCKET_H_CM = 30.0      # [DS din18015] default socket height (installation zone); switch height 105 cm
S_MIN_USE_H_CM = 70.0   # [FREE] S only makes sense where the key is readable/reachable: ≥ 70 cm (bedside, desk, worktop)
RELAY_T1 = "Eltako ES75-12..24V UC"   # [DS es75]
RELAY_T1_SIZE = (85.0, 40.0, 28.0)    # [DS es75]
T1_LED_ENCLOSURE = (120.0, 100.0, 100.0)  # [FREE] 1-row surface DIN enclosure: Finder 38.51 is 6.2 × 87.8 × 75.6 + ESR61NP and SNT61
                                         #        (flush-box devices) on a mounting plate — ≥ 95 deep
FINDER38_SIZE = (6.2, 87.8, 75.6)        # [DS finder38]
PSU_REMOTE = "Eltako SNT61-230V/12V DC-0,5A"   # [DS snt61] 45 × 45 × 33, 6 W, Class II, terminals
PSU_W = 6.0           # [DS snt61]
PSU_EFF = 0.81        # [DS snt61] efficiency at full load (lower at light load → standby is a floor)
PSU_V_TOL = 0.01      # [DS snt61] 'Stabilisierte Ausgangsspannung ±1 %' 
SELV_SOURCE_MAX_W = 15.0   # [FREE] SELV source must be ≤ 15 W or fused ≤ 0.5 A at the source (limits fault energy in the wall)
RELAY_CTRL = (12.0, 10.0)   # [DS es75] external control 12–24 V UC, 10 mA at 24 V
RELAY_PULSE_MS = (100, 400)  # [FREE] ESP relay pulse (hardware one-shot) / firmware lock-out (ES75: 20 / 300 ms [DS])
KEY_ARBITRATION_MS = 250     # [FREE] firmware: a key action on Home waits 250 ms and is cancelled by a plate press (palm)
T2_STACK = 33.0 + 18.0      # [DS] SNT61 33 + ESR61NP 18 in chamber 2
T2_DEPTH = 67.0             # [DS kaiser1068]
T2_WIRING = 10.0            # [FREE] depth reserved in chamber 2 for WAGOs and conductor bends
LOADS_W = {             # [TBD]/[DS] estimates at the 5 V rail — measure on the bench (avg, peak)
    "ESP32-C6 + LCD + touch, Wi-Fi on, no power-save (avg)": (0.65, 1.95),   # peak = TX 354 mA [DS esp32c6] + backlight
    "MAX98357A + speaker (chime, volume-capped to 1.1 W, seconds)": (0.05, 1.10),
    "glow ring 4 × SK6812 MINI (firmware 45 %, strobe 100 % red)": (0.12, 0.72),
    "buffers, pull-ups, misc": (0.01, 0.02),
}
AVG_NO_PS_W = 0.65      # [TBD] ESP average with Wi-Fi power-save off — the current firmware sets power_save_mode: none
BUCK_EFF = 0.85         # [TBD] TSR 1-2450 at ~15 % load (94 % only near full load [DS traco])
KEY_AREA_CM2 = 24.0     # [FREE] exposed key surface (front 12.6 + sides 11.8)
H_CONV = 10.0           # [TBD] W/m²K natural convection + radiation, estimate

# acoustics / RF
SPK_SENS_RANGE = (82.0, 88.0)   # [TBD] 2030 sensitivity dB @ 1 W / 10 cm — not published; typical micro-speaker range
SPL_TARGET = (70.0, 75.0)   # [FREE] at 1 m
HALF_SPACE_DB = 3.0         # [FREE] flush in a wall → radiation into half space
C_SOUND = 343000.0          # mm/s
RF_MIN_METAL = 10.0         # [FREE] want ≥ 10 mm chip ↔ significant metal (spring, screws, frame); brass standoffs are given

# optional sensors — deferred to v1 (see doc §6.5)
SENSORS_DEFERRED = ("VEML7700", "SHT31-D", "LD2410C/B")


# =====================================================================================================
# 6. DESK REPLICA (owner 2026-10-03, prototype only): two coupled flush boxes + 2-gang frame, top = the RoomKey
#    insert, bottom = a sensor cover with the real breakouts. Powered by USB 5 V, NEVER in a wall, never on 230 V.
#    Coordinates: top box centre (0, 0), bottom box centre (0, −DESK_PITCH); d as everywhere (wall plane = WALL_D).
# =====================================================================================================
DESK_PITCH = 71.0       # [DS] German multi-gang spacing (switch above socket)
DESK_CUP_IN = 59.0      # [FREE] box replica inner Ø (≥ BOX_USABLE_D 58, which the insert is checked against)
DESK_CUP_WALL = 1.6     # [FREE]
DESK_DEPTH = 47.0       # [FREE] box depth behind the wall plane (the planning default); the back is OPEN (wiring access)
DESK_PLATE = (92.0, 165.0, 2.4, 6.0)   # [FREE] "wall" plate W, H, T, corner R, centred between the boxes
DESK_DOME_R_OUT = 32.6  # [FREE] the 2 screw domes (0°, 180°) bulge out of the cup wall around the screw hole (r 30)
DESK_SCREW_PILOT = (2.7, 20.0)   # [FREE] pilot Ø / depth for 3.2 device screws or M3 self-tapping
DESK_LINK = (9.0, 19.0, WALL_D + 10.0, WALL_D + 20.0)   # [FREE] wire channel between the boxes: x0, x1, d0, d1 (off-centre:
                                                        # the frame screw is reached from behind at x 0)
DESK_FRAME_T = (2.0, 1.6, 1.6)   # [FREE] 2-gang frame: face thickness, opening-tunnel wall, outer skirt (to the wall plane)
DESK_FRAME_R = 4.0      # [FREE] frame outer corner radius
DESK_FRAME_PROFILE = (10.0, 6.0, 1.5)   # Jung AS 500 face profile, heights above the wall plane: at the inner rim [DS: AS 581
                        # depth 10 mm], at the outer edge [TBD est.], width of the flat rim round each opening [TBD est.].
                        # The owner: "the inner side of the frame is a bit higher than the outer side" (2026-10-03)
DESK_FRAME_SCREWS = ((-37.4, 37.4), (37.4, 37.4), (-37.4, -DESK_PITCH - 37.4), (37.4, -DESK_PITCH - 37.4))   # [FREE] 4 × M3
                        # from behind into frame corner posts, outside both 71 × 71 flanges (they meet at y −35.5)
DESK_FRAME_POST = (4.6, 2.6, 3.4)   # [FREE] frame post Ø, its pilot Ø, wall-plate hole Ø
# SHT31-D IN THE FRAME (owner 2026-10-03; practice frame, bottom border): the board lies flat under the bottom border,
# chip side forward (3 × 3 Ø1.0 vents over the chip, 3 air inlets in the bottom skirt); wires under the frame's tunnel
# wall and through a Ø2.5 hole in the chassis flange at (0, −27.0) (rim gap, inside the box opening) into the box.
# The owner (2026-10-04): the vents must sit on the frame's centre line → the board is shifted so its chip is at x = 0.
FRAME_RH = (-(R.RH_W / 2 - R.RH_CHIP_C[1]), 0.6, 0.6, 1.3)   # [FREE] board centre x (chip centred), face recess,
                                                               # skirt left there, chip-pocket depth
FRAME_RH_HOLE = (0.0, -27.0, 2.5) # [FREE] wire hole in the kit chassis flange: x, y, Ø (bottom rim gap |x| < 4.5)


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


def box_floor(v=None):
    return WALL_D + BOX_DEPTH - BOX_FLOOR_LOSS


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
                   y + R.MX_BODY_BELOW / 2, s["plate_back"], s["mx_pins"], tag="[DS]", note="below the plate incl. pins"))
    E.append(B("switch plate", -(WELL_IN_X - SWP_CLEAR), WELL_IN_X - SWP_CLEAR, -(WELL_IN_Y - SWP_CLEAR),
               WELL_IN_Y - SWP_CLEAR, s["plate_front"], s["plate_back"], role="part"))
    e = B("collar", -COLLAR_OUT_X, COLLAR_OUT_X, -COLLAR_OUT_Y, COLLAR_OUT_Y, COLLAR_D0, COLLAR_D1, role="part",
          note="translucent light guide (roll limit for the key)")
    e["kind"], e["r"] = "rrect", COLLAR_OUT_R
    E.append(e)
    E.append(B("plate", -HALF, HALF, -HALF, HALF, 0.0, SNAP_D1, role="part", move="plate"))
    x0, x1, y0, y1, d0, d1 = mic_carrier_box()
    E.append(B("mic carrier", x0, x1, y0, y1, d0, d1, move="plate", tag="[FREE]", note="mic on 8 × 8 carrier, bonded to the plate"))
    for i, (x, y) in enumerate(LED_POS):
        E.append(B(f"LED {i+1}", x - LED_W / 2, x + LED_W / 2, y - LED_W / 2, y + LED_W / 2, LED_D0,
                   LED_D0 + LED_T + LED_CARRIER_T, note="SK6812 MINI on the collar's collector pad"))
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
    E.append(B("hub", HUB[0], HUB[1], HUB[2], HUB[3], HUB[4], HUB[5], tag="[TBD]",
               note="horizontal hub: buck, amp, protection, wire pads"))
    E.append(B("cable loop", -CABLE_W / 2 - 0.4, CABLE_W / 2 + 0.4, LOOP_Y[0], LOOP_Y[1], LOOP_D0, LOOP_D1,
               note="rolling U-loop of the 14-wire bundle"))
    E.append(B("loop anchor", *ANCHOR, role="part"))
    for i, (x0, x1, y0, y1) in enumerate(WAGO_POS):
        E.append(B(f"WAGO {i+1}", x0, x1, y0, y1, WAGO_D[0], WAGO_D[1], tag="[DS]", note="WAGO 221-412 standing"))
    E.append(B("speaker back foam", SPK_X0 - SPK_BACK_FOAM[1], SPK_X0, SPK_Y[0] + 2, SPK_Y[1] - 2, SPK_D0 + 2, SPK_D0 + R.SPK_W - 2,
               note="foam strip, compressed"))
    return E


# =====================================================================================================
# geometry primitives for the checks
# =====================================================================================================
def _corners(e):
    return [(e["x0"], e["y0"]), (e["x1"], e["y0"]), (e["x1"], e["y1"]), (e["x0"], e["y1"])]


def max_radius(e):
    if e["kind"] == "cyl":
        return math.hypot(e["cx"], e["cy"]) + e["r"]
    if e["kind"] == "rrect":     # centred rounded rectangle: farthest point lies on a corner arc
        return math.hypot(e["x1"] - e["r"], e["y1"] - e["r"]) + e["r"]
    return max(math.hypot(x, y) for x, y in _corners(e))


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


def dome_gap(e):
    g = 1e9
    for ang in BOX_DOME_ANGLES:
        a = math.radians(ang)
        ca, sa = round(math.cos(a)), round(math.sin(a))
        r0, r1, w = BOX_DOME_R_IN, BOX_DOME_R_OUT, BOX_DOME_W / 2
        if ca:
            dome = dict(kind="box", x0=min(ca * r0, ca * r1), x1=max(ca * r0, ca * r1), y0=-w, y1=w)
        else:
            dome = dict(kind="box", x0=-w, x1=w, y0=min(sa * r0, sa * r1), y1=max(sa * r0, sa * r1))
        g = min(g, gap2d(e, dome))
    return g


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
    ws_r = max(math.hypot(abs(wire_slot(x, y)[0]) + CARRIER_WIRE_SLOT[0] / 2, abs(wire_slot(x, y)[1]) + CARRIER_WIRE_SLOT[1] / 2)
               for (x, y) in SW_POS)
    ws_in = all(abs(wire_slot(x, y)[0]) - CARRIER_WIRE_SLOT[0] / 2 >= abs(x) - (CARRIER[0] / 2 + 0.2) + 0.1 - 1e-9 and
                abs(wire_slot(x, y)[1]) - CARRIER_WIRE_SLOT[1] / 2 >= abs(y) - (CARRIER[1] / 2 + 0.2) + 0.1 - 1e-9
                for (x, y) in SW_POS)
    rule(ws_in and ws_r <= BOX_USABLE_D / 2 - 0.8, f"switch wires: the flange slots stay ≥ 0.1 inside the carrier pockets and reach r {ws_r:.1f} ≤ box inside "
         f"{BOX_USABLE_D / 2:.1f} − 0.8 [TBD Q5] → the wires drop into the box, not onto its rim; the carrier rests on the flange "
         f"around the slot (no solder under the datum)")
    wx0, wx1, wy0, wy1 = mic_well()
    rule(math.hypot(abs(wx0) + 0.8, abs(wy1)) <= BOX_USABLE_D / 2 - 0.8 and DECK_HALF_X - (abs(wx0) + 0.8) >= 0.8,
         f"mic wire well {MIC_WELL:.0f} × {MIC_WELL:.0f} beside the pocket (x {wx0:.1f}..{wx1:.1f}, y {wy0:.1f}..{wy1:.1f}), walled "
         f"to the flange: {DECK_HALF_X - abs(wx0) - 0.8:.1f} to the deck edge, inside the box; the wires leave the carrier "
         f"sideways in an S-loop (no wire between the carrier and a floor); removable foam plug")
    warn("skirt ↔ deck edge on the PIVOT side: 0.10 at rest, ≈ 0.03 at the RSS stop (CAD 'plate without lips ↔ chassis'); "
         "with ±0.1 print tolerance the skirt may touch the deck edge there, where the relative motion is ≤ 0.1 mm → friction "
         "near the hinge, not a stop → coupon row D: press at the far edge 20 ×, it must click and return without sticking; "
         "fallback: sand the skirt's inner face (the plate location then grows to ±0.15, shadow gap ±0.24 RSS)")
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
    rule(PLATE_T + t_edge <= LOC_RIM_D0 - 0.1, f"frame locating rims (d {LOC_RIM_D0}..{WALL_D - FLANGE_T}) stay behind the "
         f"pressed plate skin (d ≤ {PLATE_T + t_edge:.2f}, RSS)")
    rule(LOC_RIM_SPAN[0] - SKIRT_GAP[0] >= 0.5 and SKIRT_GAP[1] - LOC_RIM_SPAN[1] >= 0.5,
         f"8 frame rims (|along| {LOC_RIM_SPAN[0]}..{LOC_RIM_SPAN[1]}) sit in the skirt/lip gaps (|{SKIRT_GAP[0]}..{SKIRT_GAP[1]}|) "
         f"with ≥ 0.5 to the skirt ends")
    info(f"rim outer faces are made at ±{RIM_OUT:.2f} = frame opening/2 − {FRAME_TUNNEL_MARGIN} [TBD] → recut to the MEASURED "
         f"opening (Q2)")
    eng = FRAME_TUNNEL_D - LOC_RIM_D0
    rule(eng >= 1.0, f"rims reach {eng:.1f} mm into the frame's opening tunnel (depth {FRAME_TUNNEL_D:.1f} [TBD]) → frame located "
         f"±{FRAME_TUNNEL_MARGIN} in x and y; they do NOT hold it forward (FRAME_RETENTION [TBD], Q2)")
    fg = (FRAME_OPEN - PLATE) / 2
    th_edge = t_edge / (HALF + DECK_HALF_Y)                # plate tilt at the stop (band press, pivot at the far lip)
    shift = th_edge * SNAP_D0                              # the pressed edge's front moves outward (pivot ≈ 6.5 behind it)
    gp = fg - FRAME_TUNNEL_MARGIN - clr - shift
    rule(gp >= 0.0, f"plate ↔ frame: {fg:.2f} nominal; at rest ≥ {fg - FRAME_TUNNEL_MARGIN - clr:.2f} (frame on its rims, plate at its "
         f"skirt clearance); pressed at an edge the front edge moves out {shift:.2f} → ≥ {gp:.2f} [TBD Q2, print tolerance not "
         f"included]; if the measured opening is < 55.6: chamfer the plate's front edge 0.2 × 45° and recut the rims", hard=False)
    rule(PLATE_T + t_edge + 0.0 <= DECK_D0, "pressed plate stays in front of the deck (RSS stack)")
    wall_min = max(need_wall, LIP_D1 + t_edge + FLANGE_T + 0.2, SNAP_D1 + t_edge_w + 0.3)
    warn(f"Q1 threshold: this geometry needs a rocker-front ↔ wall distance ≥ {wall_min:.1f} mm (the pressed snap lips must end "
         f"0.3 before the wall at the worst-case press; the switch stack alone would allow {need_wall:.1f}); assumed {WALL_D} "
         f"[TBD Q1]. Above it the chassis is regenerated for the measured value; below it the deck, lips and tongues must be "
         f"made thinner (redesign) — Q1 gates the first print")
    rule(LIP_D1 + t_edge <= WALL_D - FLANGE_T - 0.2, f"pressed top lip (d ≤ {LIP_D1 + t_edge:.2f}) clears the flange "
         f"(d {WALL_D - FLANGE_T:.1f})")
    rule(SNAP_D1 + t_edge_w <= WALL_D - 0.3 and SNAP_RELIEF[0] <= SNAP_X[0] - 0.5 - 0.3 and SNAP_RELIEF[2] <= DECK_HALF_Y - TONGUE_W
         - tm["tip"] - 0.1, f"pressed snap lips (d ≤ {SNAP_D1 + t_edge_w:.2f} worst case) move into the flange windows and end "
         f"{WALL_D - SNAP_D1 - t_edge_w:.2f} before the wall plane")
    rule(SW_LIFE >= 20 * 365 * 30, f"switch life {SW_LIFE:,} per switch ≥ 30 years × 20 presses/day (worst case: every press on "
         f"the same switch)")
    kp = pad_k()
    pre = kp * (PAD_H - (DECK_D0 + PAD_POCKET - PLATE_T)) * len(PAD_POS)
    w = PLATE_MASS_G * 9.81e-3
    rule(pre >= 3 * w, f"anti-rattle preload: {len(PAD_POS)} soft pads ({PAD_SIZE[0]}×{PAD_SIZE[1]}×{PAD_H}, CLD40 {PAD_CLD40} kPa "
         f"[TBD]) give {pre:.2f} N ≥ 3 × plate weight {w:.3f} N; the nubs do not touch the plungers at rest")
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

    # --- D. box zone ----------------------------------------------------------------------------------
    r_allow = BOX_USABLE_D / 2 - FIT_MARGIN
    for e in E:
        if e["d1"] <= WALL_D or e["move"]:
            continue
        rmax = max_radius(e)
        rule(rmax <= r_allow, f"{e['name']}: r max {rmax:.2f} inside the box (usable Ø{BOX_USABLE_D} [TBD] − margin → {r_allow:.2f})")
        dg = dome_gap(e)
        rule(dg >= FIT_MARGIN, f"{e['name']}: {dg:.2f} mm from the screw domes [TBD r_in {BOX_DOME_R_IN}]")
    info("box fallback (Q5): if the measured box is up to 1 mm tighter, narrow the duct channel (3.1 → 2.1) and the hub "
         "(2 mm); if tighter still, this box type needs replacing (electrician)")
    for nm, hgt in HUB_PARTS.items():
        rule(HUB[4] + HUB_PCB_T + hgt <= HUB[5], f"hub part '{nm}' {hgt} tall fits behind the hub PCB")
    area_back = (HUB[1] - HUB[0]) * (HUB[3] - HUB[2]) - len(HUB_POSTS) * math.pi * 1.5 ** 2
    area_front = sum((b_ - a_) for a_, b_ in HUB_FRONT_STRIPS) * (HUB[3] - HUB[2])
    need_a = sum(HUB_FOOTPRINTS.values()) * HUB_ROUTING
    rule(need_a <= area_back + area_front, f"hub area: {sum(HUB_FOOTPRINTS.values())} mm² parts × {HUB_ROUTING} routing = "
         f"{need_a:.0f} mm² ≤ {area_back:.0f} (back) + {area_front:.0f} (front strips beside MX1, ≤ 7.7 tall) [TBD]; fallback: "
         f"a second board level at d {HUB[5]:.1f}–{HUB[5] + 5:.1f} beside the WAGOs (still inside the box)", hard=False)
    back = max(e["d1"] for e in E)
    need = back - WALL_D + BOX_FLOOR_LOSS
    rule(need <= BOX_DEPTH, f"insert depth incl. 5 × WAGO 221-412 (standing, d {WAGO_D[0]}–{WAGO_D[1]}): parts to d {back:.1f} → "
         f"needs a box ≥ {need:.1f} mm; standard {BOX_DEPTH:.0f} mm box: {BOX_DEPTH - need:.1f} mm left")
    warn(f"conductors: the NYM cores (solid 1.5 mm², 11 mm stripped) bend from the box entry to the WAGO entries in the remaining "
         f"{BOX_DEPTH - need:.1f} mm + the gaps beside the WAGOs — check with a real NYM-J 5×1.5 on the wall-fit prototype; fallback: "
         f"a 47 mm deep box, or push-in PCB terminals for 1.5 mm² on the hub")
    lx0, lx1, lhy, lp_t = LOAD_PLATE
    stack = FLANGE_T + SCREW_HEAD_H
    rule(stack <= FRAME_BACK_FREE and lp_t <= FLANGE_T - 0.5, f"flange {FLANGE_T} (stainless load plate {lp_t} recessed in it) + "
         f"screw head {SCREW_HEAD_H} = {stack:.1f} under the frame (free {FRAME_BACK_FREE} [TBD Q2])")
    bearing = (lx1 - lx0) * 2 * lhy - FLANGE_SLOT_W * min(FLANGE_SLOT_L, 2 * lhy)
    rule(CLAMP_N / bearing <= PETG_CREEP_MPA, f"box-screw clamp ≤ {CLAMP_N:.0f} N on the load plate ({lx1 - lx0:.1f}×{2*lhy:.1f}) → "
         f"{CLAMP_N / bearing:.1f} MPa on the flange (≤ {PETG_CREEP_MPA} for permanent load)")
    duct_x = DUCT_X1 + DUCT_WALL
    rule(BOX_SCREW_PITCH / 2 + lx0 - 0.1 >= duct_x + 0.2 and BOX_SCREW_PITCH / 2 + lx1 + 0.1 <= FLANGE_HALF - 0.1,
         f"load plate x {BOX_SCREW_PITCH/2 + lx0:.1f}..{BOX_SCREW_PITCH/2 + lx1:.1f} between the duct wall ({duct_x:.2f}) and the "
         f"flange edge ({FLANGE_HALF}); the screw head (Ø{SCREW_HEAD_D}) stays clear of the rims (|y| ≥ {LOC_RIM_SPAN[0]})")

    # --- E. electrical: SELV-only insert, topologies ------------------------------------------------
    info("insert is SELV-only (class III): no 230 V part in the RoomKey chamber, no barrier, no DIY power supply")
    info(f"spec: hub input {HUB_VIN[0]}–{HUB_VIN[1]} V (12 V or 15 V SELV source; 24 V not allowed: B3FS max {SW_RATING[1]:.0f} V)")
    i_pk = sum(p for _, p in LOADS_W.values()) / BUCK_EFF / 12.0
    i_lo, i_hi = EFUSE[0] * (1 - EFUSE[1]), EFUSE[0] * (1 + EFUSE[1])
    rule(i_lo >= i_pk, f"eFuse limit {EFUSE[0]} A ± {100*EFUSE[1]:.0f} % → {i_lo:.2f}..{i_hi:.2f} A ≥ the hub's summed peak "
         f"{i_pk:.2f} A at 12 V (chime + strobe + Wi-Fi TX at once) [TBD part: 60 V class, OVLO {EFUSE[2]:.0f} V]")
    if v == "L":
        warn(f"light path vs hub short (BLOCKED-ON-DATA): assumption — the SNT61 keeps its 12 V at {i_hi:.2f} A (eFuse max) + "
             f"{RELAY_CTRL[1]:.0f} mA PLATE, i.e. {100*(i_hi + 0.01)/0.5:.0f} % of its 0.5 A rating (its shut-off threshold is not "
             f"published, Q4f); test — hard short on the hub rail, the plate must still toggle the relay 20 ×; fallback — firmware "
             f"never runs chime and strobe at full power together (peak ≈ 0.30 A) and ILIM 0.35 A, or the 10 W SNT61 (0.83 A)")
    info(f"entry: {ENTRY_FUSE} in the pigtail +12 V only. A 230 V misconnection opens it ONLY if L meets +12 V with a "
         f"low-impedance return; L on PLATE or 0 V, L with the lamp as the return (0.02–0.3 A) or L with no return do NOT open "
         f"it — then the whole SELV side, the key cable included, can sit at line potential (doc §8.1 matrix). Protection = "
         f"marking + the verification before connecting (voltage and insulation tests, §9.1) + an RCD on the circuit")
    info(f"light path (L) = pigtail → entry fuse → PTC ({1000*PLATE_PTC[0]:.0f} mA hold, V max ≥ {PLATE_PTC[2]:.0f} V [TBD part]) → 4 "
         f"B3FS → PLATE, plus in parallel the PLATE TVS and the RELAY_DRIVE P-FET (via a series Schottky). FMEA (doc §8.2): a "
         f"short in the TVS or the FET, or an open entry fuse/PTC, stops the light — like any electronic push-button; nothing "
         f"behind the eFuse can. A PLATE short drives the source current through one pressed switch for the PTC trip time (≤ 1 s) "
         f"— contact wear, not a hazard")
    rule(RELAY_CTRL[0] / S_BLEEDER >= SW_RATING[2] >= SW_MIN_LOAD, f"{S_BLEEDER/1000:.1f} kΩ bleeder on PLATE (L and S) → "
         f"{1000*RELAY_CTRL[0]/S_BLEEDER:.1f} mA through the contacts: inside the rated {1000*SW_RATING[2]:.0f}–"
         f"{1000*SW_RATING[3]:.0f} mA whatever relay input is fitted (minimum applicable load {1e6*SW_MIN_LOAD:.0f} µA [DS])")
    rule(PSU_W <= SELV_SOURCE_MAX_W, f"SELV source power: SNT61 {PSU_W:.0f} W (the 10 W variant, now the catalogue part, also ≤ {SELV_SOURCE_MAX_W:.0f} W); any "
         f"other source must be ≤ {SELV_SOURCE_MAX_W:.0f} W or fused ≤ 0.5 A at the source (T3 DIN-rail PSUs)")
    warn("marking (0100-510): every cable converted to SELV is labelled 'SELV 12 V DC — kein 230 V' at both ends and in the "
         "circuit documentation; class III symbol + '12 V DC SELV only, max 15 V' on the insert flange and on the pigtail")
    if v == "L":
        warn("topology per position (doc §9): FIRST inventory the switch box (other circuits / junctions / coupled neighbour boxes "
             "→ move them out, T2, or no RoomKey), TN-C → rewire first; where does the switch leg end (lamp / ceiling box → T1a, "
             "wall junction box → T1b with a new box); usable cores (2 = the common NYM-J 3×1.5 → T1 impossible)")
        warn(f"T1 relay {RELAY_T1} is {RELAY_T1_SIZE[0]:.0f} × {RELAY_T1_SIZE[1]:.0f} × {RELAY_T1_SIZE[2]:.0f} ('für "
             f"Leuchteneinbau', SELV side on a STOCKO plug → adapter leads; −20..+50 °C at the mounting place [DS]) and needs ≤ 10 A "
             f"protection → the usual B16 lighting MCB becomes B10, or a fuse is added. Mounting in a luminaire canopy modifies the "
             f"luminaire (installer's responsibility). LED rating: data sheet none, distributors 200 W → Q4b")
        info(f"T1-LED (arithmetic only, the electrician decides): Finder 38.51 ({FINDER38_SIZE[0]} × {FINDER38_SIZE[1]} × "
             f"{FINDER38_SIZE[2]} [DS]) + ESR61NP + SNT61 in a surface DIN enclosure ≈ {T1_LED_ENCLOSURE[0]:.0f} × "
             f"{T1_LED_ENCLOSURE[1]:.0f} × {T1_LED_ENCLOSURE[2]:.0f} (≥ {FINDER38_SIZE[2] + 15:.0f} deep) at the lamp or ceiling")
        info(f"T2 chamber 2 (depth arithmetic only; layout and cover open, Q11): SNT61 33 + ESR61NP 18 + {T2_WIRING:.0f} wiring = "
             f"{T2_STACK + T2_WIRING:.0f} mm in a {T2_DEPTH:.0f} mm box [DS] (solid wall; hollow-wall variant Q5)")
        warn("T2: ESR61NP A1/A2 (6 mm / 4000 V, 'galvanisch getrennt' [DS]) is NOT declared SELV → Eltako's written confirmation "
             "(Q4a); Kaiser 1068-02 is an 'Auslaufprodukt'; chamber 2 must stay accessible (0100-520); its front / cover, the "
             "partition passage and the side-by-side layout of SNT61 + relay + WAGOs are unverified (Q11)")
        warn("SPD type 2/3 as required by Eltako's data sheets [DS]; RCD 30 mA for new/modified lighting circuits (0100-410 "
             "411.3.4) — older homes may need both retrofitted; registered installation company (NAV §13); test record (0100-600)")
        v_ctrl = RELAY_CTRL[0] * (1 - PSU_V_TOL) - PLATE_PTC[1] * RELAY_CTRL[1] / 1000
        warn(f"ES75 control voltage at the relay ≈ {v_ctrl:.1f} V (SNT61 12 V −{100*PSU_V_TOL:.0f} % [DS], PTC drop) vs its "
             f"12..24 V UC range → Q4d minimum. Fallbacks: (a) T1-LED (coupling relay, 12 V coil); (b) a 15 V DIN-rail "
             f"safety-isolating PSU (T3 only — no flush-mount 15 V part is named); (c) the ES75's internal control voltage needs a "
             f"hub redesign (isolated switches, opto input) — not in v0.4")
        rule(RELAY_PULSE_MS[0] >= 20 and RELAY_PULSE_MS[1] >= 300, f"relay command: ESP one-shot {RELAY_PULSE_MS[0]} ms ≥ 20 ms "
             f"minimum, lock-out {RELAY_PULSE_MS[1]} ms ≥ 300 ms pause [DS es75]")
        warn("RELAY_DRIVE on IO5 = MTDI, which FLOATS at reset, in the bootloader and in a boot loop [DS esp32c6] (IMU INT1 is "
             "high-Z too) → on the hub: 100 k pull-down at the drive input + a 20 ms qualifying RC ahead of the one-shot, so only a "
             "deliberate level fires it; desk-rig test R12: 100 power cycles, 100 resets, a forced boot loop, the board missing — "
             "no relay pulse. Fallback: arm the one-shot from a second line (needs a 15th wire)")
        rule(RELAY_CTRL[0] <= SW_RATING[1] and RELAY_CTRL[1] / 1000 <= SW_RATING[3], f"plate line: 12 V SELV, ≤ "
             f"{RELAY_CTRL[1]:.0f} mA into the ES75 control input (a DC coupling relay: ≈ 15 mA, free-wheel diode in the module) "
             f"— within the B3FS rating")
        warn("light state is not known to the ESP (no relay feedback) → Home cannot show it, 'all lights off' must not include it "
             "(a toggle could switch it on), firmware offers 'toggle' only; a 4th SELV core (NYM-J 5×1.5) keeps a feedback option (Q3c)")
        sb = 1.0 + 0.1 + (sum(a for a, _ in LOADS_W.values()) / BUCK_EFF) / PSU_EFF
        warn(f"standby per room ≈ {sb:.1f} W (ES75 1 W [DS] + SNT61 0.1 W [DS] + insert {sum(a for a, _ in LOADS_W.values()) / BUCK_EFF:.2f} "
             f"W through the SNT61 at {100*PSU_EFF:.0f} % [DS]); the light depends on the 12 V supply")
        warn("power cut (Q4e, BLOCKED-ON-DATA): assumption — the ES75 (bistable) keeps its state or comes up off; it is never "
             "switched ON by the power return, because no PLATE/RELAY_DRIVE pulse occurs at power-up (pull-down + qualifier, test "
             "R12). Pass: 20 power cuts with the light off → it stays off. Fallback: T1-LED/T3 with an impulse relay whose data sheet "
             "states its state after a power cut")
        warn("touch vs key (north star: a tap never acts on Home): the key actuates at ≈ 1.1 N (2 × 0.56 N ± 0.2 [no-name MX]), "
             "swipes on a touchscreen reach 0.8–1.2 N (published study) → a swipe or firm tap may fire the key (Ringing: answer "
             "instead of silence). Desk-rig test R13: 3 people, 100 swipes from each end and the centre, 100 taps → 0 key-downs. "
             "Fallbacks: heavier switches (≥ 1 N each; recheck R1), firmware: a touch that moved > 2 mm suppresses key-down, "
             "Ringing answers on key-up after a still press (WIP, firmware not changed here)")
        info(f"key vs plate (firmware, WIP): a key action on Home waits {KEY_ARBITRATION_MS} ms and is dropped if PLATE_SENSE fires "
             f"(palm/elbow presses hit both — desk-rig test with a flat hand); the ESP never pulses the relay within 1 s after a "
             f"plate press and masks PLATE_SENSE during its own pulse")
    else:
        warn("S: the socket is lost (S1/S2) — check the DIN 18015-2 minimum socket count of the room; supply per position "
             "(doc §9.3): S1 two-chamber box (box change), S2 12 V over a cable of its own (new, or the old one converted to SELV "
             "and marked), S3 keep the socket and add a separate box; onward feeds need S1 or rerouting; socket circuits need an "
             "RCD (0100-410 411.3.3); the socket's centre plate often clamps the frame → frame retention fallback (§7)")
        info("S: no PE connection needed — the insert is SELV/class III; the PE of any 230 V cable stays with that cable, "
             "never cut short or left loose")
        warn(f"S: standard socket height {SOCKET_H_CM:.0f} cm (DIN 18015-3) is too low for the key → only sockets ≥ "
             f"{S_MIN_USE_H_CM:.0f} cm (bedside, desk, worktop) qualify (Q3b)")
        warn("S: the plate goes to the ESP only (PLATE_SENSE) → firmware maps it to the room light via HA; S_PLATE_FIXED=True "
             "makes it a fixed plate instead")
        info(f"S1 chamber 2 (depth arithmetic only; layout open, Q11): SNT61 33 mm + WAGO 221 through-terminals + {T2_WIRING:.0f} wiring "
             f"in a {T2_DEPTH:.0f} mm box [DS]")
    warn("12 V source: SNT61 is class II to EN 60950 [DS] but its data sheet does not say 'SELV' in the sense of VDE 0100-410 "
         "414.3 — confirm with Eltako (Q4c), or use a PSU marked for IEC 61558-2-16 (safety isolating)")
    avg5 = sum(a for a, _ in LOADS_W.values())
    pk5 = sum(p for _, p in LOADS_W.values())
    avg12, pk12 = avg5 / BUCK_EFF, pk5 / BUCK_EFF
    rule(pk12 <= 0.8 * PSU_W, f"power {avg12:.2f} W avg / {pk12:.2f} W peak at 12 V (buck {100*BUCK_EFF:.0f} % [TBD]) vs "
         f"{PSU_W:.0f} W {PSU_REMOTE}")
    warn("start-up: the SNT61 switches off on overload and restarts [DS]; the hub eFuse soft-starts its 2 × 100 µF + TSR load "
         "(assumption: the SNT61 starts into the eFuse limit) → bench-test cold start; fallback: slower dV/dt or less bulk capacitance")
    key_heat = AVG_NO_PS_W
    dT = key_heat / (H_CONV * KEY_AREA_CM2 * 1e-4)
    warn(f"key self-heating: ≈ {key_heat:.2f} W in the key (the firmware runs Wi-Fi without power-save) → ΔT ≤ {dT:.0f} K on the "
         f"key surface (upper bound, no conduction into the chassis); mitigation: backlight dimming (and power-save if the "
         f"intercom allows it) — measure (thermocouple, 1 h)")
    info("firmware requirements (WIP, not changed here): never enable the IMU's INT1 (it shares IO5 = RELAY_DRIVE); never insert a "
         "microSD card (IO3/IO4 are the TF slot's lines); expose the glow ring to HA with its 45 % cap only; mic L/R no longer "
         "on IO3. Hub: MAX98357A SD_MODE via a resistor from 5 V (its internal 100 k pull-down would keep it off); GPIO16 "
         "carries the boot log into DIN, but BCLK/WS are idle then and the amp needs them to play [DS, verify on the rig]")
    heat_box = avg12 * (1 - BUCK_EFF) + 0.05 + LOADS_W["glow ring 4 × SK6812 MINI (firmware 45 %, strobe 100 % red)"][0]
    info(f"heat in the box ≈ {heat_box:.2f} W (buck loss, amp idle, glow LEDs); PSU/relay losses are outside the chamber")

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
    ("WALL_D", WALL_D, "Q1 plate front ↔ wall at the existing switch (rocker surface to wall)"),
    ("FRAME_OPEN", FRAME_OPEN, "Q2 frame opening (inner) — calipers; the rims are cut to it − 0.1"),
    ("FRAME_BACK_FREE", FRAME_BACK_FREE, "Q2 depth free under the frame for flange + screw heads"),
    ("FRAME_TUNNEL_D", FRAME_TUNNEL_D, "Q2 depth of the frame's opening tunnel (the rims reach into it)"),
    ("FRAME_RETENTION", FRAME_RETENTION, "Q2 frame loose once the rocker is off? photo of frame back + old rocker back"),
    ("FRAME_MATERIAL", FRAME_MATERIAL, "Q2 plastic or metal frame? brand/series/colour"),
    ("topology", "?", "Q3 per L position (electrician): other circuits in the box? TN-S? where does the switch leg end? cores?"),
    ("light feedback", "?", "Q3c reserve a 4th SELV core for light-state feedback?"),
    ("Eltako", "?", "Q4a ESR61NP A1/A2 SELV? Q4b ES75 with LED loads? Q4c SNT61 output SELV? Q4d ES75 min control voltage? "
                    "Q4e ES75 state after a power cut?"),
    ("end presses", "?", "desk rig: press the printed key every 5 mm along its length (1000 × at each end) → stabiliser if it binds"),
    ("KEY_WOBBLE_DEG", KEY_WOBBLE_DEG, "desk rig: tilt of the key on its stems under an edge press"),
    ("touch vs key", "?", "desk rig R13: swipes / taps must not fire the key (0 key-downs in 300 gestures)"),
    ("RELAY_DRIVE at reset", "?", "desk rig R12: 100 power cycles / resets / boot loop → no relay pulse"),
    ("SNT61 overload", "?", "Q4f Eltako: SNT61 behaviour at a sustained 0.46 A (eFuse max) — does it keep 12 V? bench: hub short test"),
    ("Q1b box rim", "?", "electrician (circuit isolated): box rim offset / flatness vs the wall, box type (domes or claws)"),
    ("BOX_FLOOR_LOSS", BOX_FLOOR_LOSS, "Q5 floor and entries of the real box (sets the conductor room behind the WAGOs)"),
    ("SCREW_HEAD_H", SCREW_HEAD_H, "Q2 low-head device screws ≤ 1.8 under the frame (stack 3.0 vs 3.5 free)"),
    ("BOX_DOME_W", BOX_DOME_W, "Q5 dome width"),
    ("TB_ANT size", R.TB_ANT[2:], "Q8 chip antenna size (drawing gives the position only)"),
    ("V-0 filament", "?", "Q10 a UL94 V-0 grade rated at ≤ 0.8 mm; its E / σy for the tongues; coupon row D bases in it"),
    ("WAGO conductors", "?", "wall-fit prototype with a real NYM-J 5×1.5: cores to 5 × WAGO 221 in the box"),
    ("mic path", "?", "desk rig: tools/mic_check.py through a printed plate coupon"),
    ("S positions", "?", "Q3b per S position: height, onward feed, room for a two-chamber box, socket count of the room"),
    ("BOX_USABLE_D", BOX_USABLE_D, "Q5 usable Ø inside the boxes at 20 and 35 mm depth; solid or hollow wall"),
    ("BOX_DOME_R_IN", BOX_DOME_R_IN, "Q5 how far the screw domes (or hollow-wall claws) stick in"),
    ("BOX_DEPTH", BOX_DEPTH, "Q5 actual box depth at the planned positions"),
    ("SPK sensitivity", SPK_SENS_RANGE, "Q6 SPL through the printed duct at 1 m — and is ~65–70 dB acceptable?"),
    ("PLATE_CORNER_R", PLATE_CORNER_R, "Q7 rocker corner radius; rocker flat or curved?"),
    ("PLATE_FACE_T", PLATE_FACE_T, "coupon v1 row H: ivory thickness over black next to the real frame"),
    ("AMP size", (R.AMP_W, R.AMP_H), "Q8 MAX98357A clone outline (only for the desk rig; the hub uses the bare IC)"),
    ("TB standoffs", R.TB_STANDOFF_THREAD, "Q8 brass standoffs female M2? (else M2 nuts / glue-in inserts)"),
    ("KEY_BOARD_BACK_H", KEY_BOARD_BACK_H, "Q8 component height on the board back; board without pre-soldered headers"),
    ("MX_POST_D / MX_WINDOW", (R.MX_POST_D, R.MX_WINDOW), "coupon v1 row E"),
    ("NUB_GAP / SW_TRAVEL_TOTAL / SW_MAX_FORCE", (NUB_GAP, SW_TRAVEL_TOTAL, SW_MAX_FORCE), "coupon v1 row D (real carriers)"),
    ("MAT_E / MAT_SIGMA_Y", (MAT_E, MAT_SIGMA_Y), "snap tongues: filament data / coupon v1 row D"),
    ("PAD_CLD40", PAD_CLD40, "preload pad foam data sheet (CLD at 40 %)"),
    ("ENTRY_FUSE / PLATE_PTC", "parts", "Q10: pick a 250 V AC SMD fuse and a ≥ 30 V PTC for the hub"),
    ("MIC_CARRIER", R.MIC_CARRIER, "Q10 8 × 8 mic carrier PCB (INMP441 / ICS-43434 / SPH0645, whichever is available)"),
    ("hub", HUB, "Q10 hub PCB (area check is an estimate)"),
    ("Kaiser 1068-02", "?", "Q11 front geometry of chamber 2 (stays accessible), cover, partition passage for SELV leads, "
                            "side-by-side room for SNT61 + relay + WAGOs, successor product"),
    ("glow look", "?", "Q12 desk rig: glowing gap (as built) or dark gap + lit rim (mask the collar's inner 0.75)? LEDs on/off"),
    ("S front / frame", "?", "Q1-S / Q2-S: socket central-plate height and how the frame is held at a socket (centre screw?)"),
    ("SNT61 start-up", "?", "bench: cold start into the hub (eFuse soft-start), 20 ×"),
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
