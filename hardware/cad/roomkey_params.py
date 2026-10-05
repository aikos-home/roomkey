"""RoomKey hardware — the ONE source of every part dimension (board, key switch, audio, sensors).

CAD generators, drawings and checks all read this file, so they cannot disagree.
`python3 roomkey_params.py` runs validate(): the quick key-level rules, then ERROR / WARNING / OK.
The wall insert (box, frame, both variants, mains parts) lives in insert_params.py, which imports
this file and adds its own, much longer validate().

Tags: [DS] datasheet or vendor drawing (source named) · [MEAS] measured on the real part ·
      [FREE] design choice · [TBD] placeholder until measured.
Units: mm. Front view: origin = rocker centre, x right, y up, d = depth into the wall (+),
d = 0 on the rocker FRONT face.

Changes 2026-09-30 (insert v0.2 draft, see hardware/docs/insert-design.md):
  * v0.4 (2026-10-01): both MX switches the same brown (same feel at both ends); no key stop bosses (insert doc §3).
  * v0.3 (2026-10-01): MX at (0, +15.0) / (0, −13.0) — smaller overhang for end presses.
  * v0.2: MX switches back on the long axis (0, +13.5) / (0, −10.5) — a diagonal pair leaves a free roll
    axis; the key gets a 3.8 mm skirt that slides in a fixed collar (0.25 clearance) as a linear guide.
    Key socket depth 3.4 = stem engagement, so the stem bottoms at the design position.
    Box values moved to insert_params.py (no duplicates). Antenna chip position read off the drawing.
  * MX key switch: 11.6 mm is PCB -> TOP OF HOUSING in the Cherry drawing, not "stem top above
    plate". Stem top is 10.2 above the plate top. The old key stack (36 mm) was 4.4 mm too deep.
  * MX_BELOW_PLATE 5.0 is measured from the plate TOP (not bottom) -> no extra plate thickness.
  * Keycap shell: wall 1.2 -> 1.0 and a 0.15 fit clearance around the board frame (the old KEY_W had
    zero clearance). Key 26.85 x 46.8, cut-out 28.85 x 48.8, bands stay 3.1 mm.
  * Board: PCB 1.2 and brass M2 standoffs 4.0 read from the side view; the two bottom holes are
    17.00 apart, the top ones 17.78.
"""
import math

# ============================================================== FROZEN
# Values the project owner has confirmed. validate() flags any drift as ERROR.
FROZEN = {
    "ROCKER_W": 55.0,   # [MEAS] 2026-09-29, existing rocker is 55 × 55
    "ROCKER_H": 55.0,
}

# ============================================================== wall / frame
ROCKER_W = 55.0          # [MEAS]
ROCKER_H = 55.0          # [MEAS]
# (box, frame and installation values live in insert_params.py only)

# ============================================================== touch board (target)
# Waveshare ESP32-C6-Touch-LCD-1.47, vendor dimension drawing:
# https://www.waveshare.com/img/devkit/ESP32-C6-Touch-LCD-1.47/ESP32-C6-Touch-LCD-1.47-details-size.jpg
TB_W, TB_H, TB_T = 24.55, 44.50, 10.60   # [DS] outline incl. black frame; total thickness incl. brass standoffs
TB_GLASS_W, TB_GLASS_H = 22.05, 42.00    # [DS]
TB_ACTIVE_W, TB_ACTIVE_H = 17.75, 32.93  # [DS] visible pixels
TB_CORNER_R = 5.75                       # [DS] frame corner radius
TB_FRONT_T = 5.40                        # [DS] black frame (display module) in front of the PCB
TB_PCB_T = 1.20                          # [DS] 6.60 (frame + PCB) − 5.40
TB_STANDOFF = 4.00                       # [DS] 10.60 − 6.60: brass M2 hex standoffs behind the PCB
TB_HOLE_DX, TB_HOLE_DY = 17.78, 39.00    # [DS] M2 holes: top pair 17.78 apart, top↔bottom 39.00
TB_HOLE_DX_BOTTOM = 17.00                # [DS] bottom pair 17.00 apart (3.77 from the frame edge)
TB_HOLE_EDGE = 2.75                      # [DS] bottom hole ↔ frame end; top one inferred by symmetry (2.75 + 39.00 + 2.75 = 44.50)
TB_HEADER_PITCH_X = 17.78                # [DS] 2 × 11 header columns, 7 × 2.54 apart
TB_HEADER_Y = (9.65, -15.75)             # [DS] first / last pin of each column (first pin 9.85 below the top hole), pitch 2.54
TB_STANDOFF_THREAD = None                # [TBD] brass standoffs female M2? (drawing says "M2") — check on arrival
TB_ANT = (0.0, -20.4, 3.2, 1.6, 1.1)     # [DS] ceramic chip antenna ("C3", red) on the PCB BACK, centred at the non-USB end:
                                         #      x, y, length, width [TBD], height [TBD]
TB_LEDS = "PWR (red, always on) + CHG next to USB-C"   # [DS] must not shine through the white key shell → black out

# ============================================================== PoC board (desk)
PB_W, PB_H = 20.32, 36.37                # [DS] ESP32-C6-LCD-1.47 bare PCB, portrait

# ============================================================== key switch (MX-style, no-name brown)
# Cherry MX1A datasheet drawing (datasheet.octopart.com/MX1A-11NW-Cherry-datasheet-34676.pdf):
#   PCB → top of housing 11.6 · stem above housing 3.6 · PCB → plate top 5.0 · pins 3.3 ·
#   plate cut-out 14.0 ± 0.05 · plate 1.5 ± 0.1 · pretravel 2.0 ± 0.6 · total travel 4.0 − 0.5
MX_CUT = 14.0            # [DS] plate cut-out — coupon tunes this per printer: 13.9 / 14.0 / 14.1
MX_PLATE_T = 1.5         # [DS] plate thickness the clips expect (± 0.15, drawing ± 0.006 in)
MX_TOP_W = 15.6          # [DS] top housing footprint
MX_HOUSING_ABOVE_PLATE = 6.6   # [DS] 11.6 (PCB → housing top) − 5.0 (PCB → plate top)
MX_STEM_ABOVE_HOUSING = 3.6    # [DS] stem top above the housing at rest
MX_ABOVE_PLATE = MX_HOUSING_ABOVE_PLATE + MX_STEM_ABOVE_HOUSING   # = 10.2 stem top above plate top
MX_BELOW_PLATE = 5.0     # [DS] plate TOP → housing bottom (PCB level)
MX_BODY_BELOW = 14.0     # [FREE] envelope of the bottom housing (just inside the cut-out)
MX_PINS = 3.3            # [DS]
MX_TRAVEL = 4.0          # [DS] total travel (tolerance −0.5)
MX_PRETRAVEL = 2.0       # [DS] actuation point ± 0.6
MX_FORCE_N = 0.56        # [DS] soft tactile operating force 2.0 oz (± 0.7 oz); tactile peak 2.3 oz ≈ 0.65 N
MX_POST_D = 5.5          # [TBD] keycap stem post Ø that dips into the housing at bottom-out (typical MX keycap 5.5; coupon v1 row E)
MX_WINDOW = 6.2          # [TBD] opening in the MX top housing the post enters at bottom-out (coupon v1 row E)
MX_STEM_ARM_L = 4.10     # [FREE] keycap socket cross: arm length (coupon: 4.05 / 4.10 / 4.15)
MX_STEM_ARM_W = 1.30     # [FREE] arm width (coupon: 1.25 / 1.30 / 1.35)
MX_STEM_DEPTH = 3.8      # [FREE] coupon v0 socket depth (the drawing gives no engagement value)
KEY_SOCKET_DEPTH = 3.4   # [FREE] key socket depth = stem top ↔ post end, so the stem bottoms at the design position
# v0.9 RIGID KEY (owner 2026-10-05: "Die Idee mit der Wippe ist an sich schlecht" — the v0.6–v0.8 rocker on stem forks
# scraped and did not stay in). Back to the v0.5 full cross sockets on Ø MX_POST_D posts (fit proven, coupon v0 row C), as a
# FIXED / FLOATING pair: the top socket (MX1) holds the stem in x and y; the bottom one (MX2) is slotted along y, so a pitch
# error between the plate cut-outs and the key's sockets cannot strain the two stems against each other (a rigid frame on
# two stems is over-constrained only along the line through them). Both switches are one key (firmware ORs them).
KEY_SOCKET_FLOAT = 0.25      # [FREE] MX2 socket: the y-arm slot runs through the post (open ends) and the x-arm slot is wider
                             #        by 2 × this → the stem floats ± this along y; still clamped in x by its y-arm's 1.30 width
KEY_END_TAPER = 0.2          # [FREE] the "funnel": the short-end walls are set back by this much from 5.6 behind the glass on
KEY_END_TAPER_RUN = 5.6      #        (linear from 0 at the glass); v0.6 rocker room, kept for the ±KEY_WOBBLE_DEG pitch
MX_PINCOUNT = 3          # [MEAS] 2 metal pins + centre post, no side pegs → plate mount (needs the 1.5 mm plate)

# ============================================================== audio
MIC_D, MIC_T = 13.14, 2.83               # [MEAS] INMP441 round module (2026-09-29) — desk rig only, 0.07 mm wider than a wing
MIC_MODULE = ("round black module with two flats; the LABELLED side carries the sound hole (≈ centre, ≈ 0.8 towards the "
              "L/R–GND row) → that side faces the room; mic chip on the back (bottom port). Pins: 2 columns × 3 at 2.54, "
              "columns ≈ 7.6 apart: SCK, WS, L/R | SD, VDD, GND")   # [PHOTO 2026-10-03]
LED_STRIP = ("owner's strip: black PCB, 5 V, pads +5V / Din / DO / GND, one cap per LED, ≈ 60 LED/m (≈ 16.7 pitch), 5050 "
             "LEDs with a white phosphor spot → most likely SK6812 RGBW (32-bit GRBW: tell the firmware). 5.0 × 5.0 LEDs do "
             "NOT fit the collar's LED windows (made for the 3.5 mm SK6812 MINI)")   # [PHOTO 2026-10-03]
MIC_CARRIER = (8.0, 8.0, 2.6)            # [FREE] v0.2: INMP441 (4.72 × 3.76 [DS]) on an 8 × 8 × 0.8 carrier PCB, bottom port;
                                         #        2.6 = PCB + mic + solder [TBD] — custom part
SPK_W, SPK_H, SPK_T = 19.32, 29.81, 4.57 # [MEAS] Waveshare 2030 cavity speaker, owner's calipers 2026-10-02 (vendor drawing:
                                         #        20 × 30 × 5.5). The "4PIN" item is a PAIR on one PH1.25 4-pin plug [DS].
                                         #        4.57 INCLUDES the white face ring (owner, 2026-10-02)
SPK_END_R = SPK_W / 2                    # [MEAS] "almost oval": near-semicircular ends (photo) → straight sides ≈ 10.5 long.
                                         #        v0.6: the hooks at the box corners catch nothing → move them onto the straight part
SPK_RING = (1.4, 0.1)                    # [TBD] white ring on the grille face: width (photo), thickness ("paper-thin", owner) →
                                         #        NOT a compressible gasket. Possibly the release liner of an adhesive ring [TBD]
SPK_TAB = (3.4, 1.8)                     # [TBD] wire-exit tab at the CENTRE of one short end: width, overhang (from the photo, ±0.5)
SPK_PORT_FACE = "large"                  # [DS] vendor outline: mesh grille on one 20 × 30 face
SPK_PORT_W, SPK_PORT_H = 16.5, 27.0      # [TBD] mesh inside the white ring, from the photo (±1); diaphragm behind it ≈ 8.6 × 12.6
AMP_W, AMP_H, AMP_T = 18.77, 17.7, 3.0   # [MEAS] MAX98357A breakout, owner's calipers 2026-10-03; 3.0 = PCB + tallest part
AMP_PCB_T = 1.56                         # [MEAS]
AMP_PARTS = ("7 pin holes (gold rings), header NOT soldered yet; a green 2-pin screw terminal for the speaker, loose — "
             "for a compact box, solder the wires straight to the pads instead (saves the terminal's height)")   # [MEAS]
AMP_BOARD = "purple MAX98357A 'I2S Amp' breakout (Adafruit 3006 layout); parts on the front only, back flat"   # [PHOTO]
AMP_PINS = ("LRC", "BCLK", "DIN", "GAIN", "SD", "GND", "Vin")   # [PHOTO] 2.54 pitch, row centred, ≈ 1.9 from the bottom edge
AMP_HOLE_D, AMP_HOLE_C = 2.5, (2.4, 1.9)   # [PHOTO ±0.5] 2 mounting holes in the top corners: Ø, centre ↔ side / top edge
AMP_SPK_PADS = (3.5, 3.1)                  # [PHOTO ±0.5] speaker pads (−/+) pitch, centred, centre ↔ top edge

# ============================================================== optional sensors (bought 2026-09-29)
ALS_W, ALS_H = 16.36, 16.37              # [MEAS] VEML7700 breakout, owner's calipers 2026-10-03; I²C 0x10
ALS_PCB_T, ALS_T = 1.41, 3.85            # [MEAS] PCB thickness / total height at the tallest part
ALS_BOARD = "Adafruit VEML7700 breakout, product 4162 (silkscreen; vendor: 16.6 × 16.5 × 4.0)"   # [DS]
ALS_HOLE_D = 2.54                        # [DS] Adafruit 0.1" mounting holes (M2 / M2.5); 2 in the top corners
ALS_HOLE_C = (2.5, 2.0)                  # [PHOTO ±0.5] hole centre ↔ side edge, ↔ top edge (owner's photo on the mat, 2026-10-03)
ALS_PINS = ("VIN", "3Vo", "GND", "SCL", "SDA")   # [MEAS] pitch 2.54, row centred, ≈ 2.1 from the bottom edge [PHOTO ±0.5]
ALS_CHIP_C = (7.8, 8.5)                  # [PHOTO ±0.5] sensor window centre ↔ left edge, ↔ top edge; chip ≈ 2.1 × 7.1, long side
                                         #        top-bottom, same side as the 3.85 height → the light window goes there
RH_W, RH_H = 13.34, 10.5                 # [MEAS] SHT31-D breakout, owner's calipers 2026-10-03; I²C 0x44; needs room air, away
                                         #        from heat (ESP, amp, LDO)
RH_PCB_T, RH_T = 1.47, 2.57              # [MEAS] PCB thickness / total height at the tallest part
RH_PARTS = "6 pin holes (a 6-pin header comes loose) + 1 large hole"   # [MEAS]
RH_BOARD = "purple 'SHT3X' breakout (GY-SHT31-D style); the sensor chip side = front"   # [PHOTO 2026-10-03]
RH_PINS = ("VIN", "GND", "SCL", "SDA")   # [PHOTO] 4 pins at 2.54 along the bottom short edge, ≈ 1.6 from it; the two small
                                         #        holes at the top (AD = address, AL = alert) are not needed (0x44 default)
RH_HOLE_D, RH_HOLE_C = 2.3, (2.5, 2.9)   # [PHOTO ±0.5] the one large hole (top left, front view): Ø, centre ↔ left / top edge
RH_CHIP_C = (7.2, 3.75)                  # [PHOTO ±0.5] SHT31 chip (≈ 2.5 × 2.5) centre ↔ left / top edge (front view): it needs
                                         #        room air → vents in front of it, low in the box, walled off from ESP and amp heat
RADAR_W, RADAR_H, RADAR_T = 15.84, 22.26, 1.56   # [MEAS] HLK-LD2410C, owner's calipers 2026-10-03 (manual: 16 × 22); 5 V;
                                         #        sees through thin plastic, not metal
RADAR_T_PINS = 11.4                      # [MEAS] total height with the soldered pin header (thickest point)
RADAR_PINS = ("TX", "RX", "OUT", "GND", "VCC")   # [PHOTO] 5 pins at 2.54 along one LONG edge, ≈ 1.3 from it, roughly centred
RADAR_FRONT = ("antenna side = the two gold patch antennas (TX/RX) + the radar chip + a status LED → faces the room through "
               "thin plastic, nothing metal in front; the header's plastic body and pins are on the OTHER (component) side, "
               "pointing away from the room")   # [PHOTO 2026-10-03]
RADAR_B_W, RADAR_B_H = 7.0, 35.0         # [DS] HLK-LD2410B 7 × 35 (the slim version, 1.27 mm pin pitch)

# ============================================================== design choices
KEY_WALL = 1.0           # [FREE] keycap shell wall around the touch board
KEY_FIT = 0.15           # [MEAS] clearance board frame ↔ shell pocket, per side: real touch board in the PETG print
                         #        (A1, 0.10 layers) fits "extremely perfect" (owner, 2026-10-02); hard to get out → §11
KEY_GAP = 1.0            # [FREE] shadow gap key ⇄ rocker cut-out
KEY_PROUD = 8.0          # [FREE] key top above rocker front
KEY_W = TB_W + 2 * (KEY_FIT + KEY_WALL)      # 26.85
KEY_H = TB_H + 2 * (KEY_FIT + KEY_WALL)      # 46.80
KEY_R = TB_CORNER_R + KEY_FIT + KEY_WALL     # 6.90
CUT_W = KEY_W + 2 * KEY_GAP                  # 28.85
CUT_H = KEY_H + 2 * KEY_GAP                  # 48.80
KEY_BACK_T = 1.6         # [FREE] shell back wall; DIN 965 M2 countersunk heads (1.2) sit flush
KEY_BOTTOM_CLEAR = 0.5   # [FREE] shell back ↔ MX housing top at full travel
KEY_WELL_CLEAR = 0.25    # [FREE] key skirt ↔ fixed light-guide collar, per side (linear guide)
KEY_SKIRT = 3.8          # [FREE] skirt behind the key back (shell wall continued) — guided in the collar over the whole stroke
MX_SW_POS = ((0.0, 15.0), (0.0, -13.0))      # [FREE] two switches on the long axis, pitch 28: the key overhangs them by only
                                             #        8.4 (top) / 10.4 (bottom) — about a 1u keycap's stem-to-edge — so end
                                             #        presses act like edge presses on a keycap (desk-rig test, insert doc §3);
                                             #        MX2's spring stays ≈ 8 mm from the antenna chip (RF test)
MX_GUIDE = ("2 × the same brown (tactile) switch under one rigid key (v0.9): fixed socket on MX1, floating on MX2; wired on "
            "their own pins and ORed in firmware (key_raw) — end-press binding: desk rig R1")
SWITCH_PITCH_Y = MX_SW_POS[0][1] - MX_SW_POS[1][1]
SPK_ON_EDGE = True       # [FREE] speaker stands on its 5.5 mm edge behind the right wing
CLEAR = 0.5              # [FREE] minimum clearance between parts

# printer / material
XY_COMP = {"PLA": 0.10, "PETG": 0.12, "ABS": 0.20}   # [FREE] hole oversize, tuned by the coupon


def key_stack():
    """Depths (d, mm into the wall) of the key module at rest. Positive d = behind the rocker front."""
    s = {}
    s["glass"] = -KEY_PROUD
    s["pcb_front"] = s["glass"] + TB_FRONT_T
    s["pcb_back"] = s["pcb_front"] + TB_PCB_T
    s["standoff_end"] = s["pcb_back"] + TB_STANDOFF
    s["key_back"] = s["standoff_end"] + KEY_BACK_T
    s["mx_top"] = s["key_back"] + MX_TRAVEL + KEY_BOTTOM_CLEAR
    s["stem_top"] = s["mx_top"] - MX_STEM_ABOVE_HOUSING
    s["post_end"] = s["mx_top"] - 0.2
    s["skirt_end"] = s["key_back"] + KEY_SKIRT
    s["plate_front"] = s["mx_top"] + MX_HOUSING_ABOVE_PLATE
    s["plate_back"] = s["plate_front"] + MX_PLATE_T
    s["mx_bottom"] = s["plate_front"] + MX_BELOW_PLATE
    s["mx_pins"] = s["mx_bottom"] + MX_PINS
    return s


def validate(verbose=True):
    errs, warns, oks = [], [], []
    g = globals()
    for k, v in FROZEN.items():
        (errs if abs(g[k] - v) > 1e-9 else oks).append(f"frozen {k} = {g[k]}")

    wing = (ROCKER_W - CUT_W) / 2
    band = (ROCKER_H - CUT_H) / 2
    (errs if CUT_W >= ROCKER_W or CUT_H >= ROCKER_H else oks).append(
        f"key cut-out {CUT_W:.2f} × {CUT_H:.2f} inside the {ROCKER_W:.0f} × {ROCKER_H:.0f} rocker")
    (warns if band < 3.0 else oks).append(f"rocker band above/below the key {band:.2f} mm (≥ 3 for strength)")
    (oks if wing >= 10 else warns).append(f"side wing {wing:.2f} mm (room for perforation + a thumb)")


    for (x, y) in MX_SW_POS:
        mx_x = KEY_W / 2 + KEY_WELL_CLEAR - (abs(x) + MX_TOP_W / 2)
        mx_y = KEY_H / 2 + KEY_WELL_CLEAR - (abs(y) + MX_TOP_W / 2)
        post = KEY_W / 2 - KEY_WALL - (abs(x) + MX_POST_D / 2)
        ok = min(mx_x, mx_y) >= 0.3 and post >= 1.0
        (oks if ok else errs).append(
            f"switch at ({x:+.1f}, {y:+.1f}): housing {min(mx_x, mx_y):.2f} mm inside the key well, "
            f"stem post {post:.1f} mm inside the key back")
    gap_y = SWITCH_PITCH_Y - MX_TOP_W
    (oks if gap_y >= 6.0 else warns).append(
        f"{gap_y:.1f} mm between the two switch housings (ribbon cable passes there, needs ≥ 6)")

    s = key_stack()
    (oks if abs((s["post_end"] - s["stem_top"]) - KEY_SOCKET_DEPTH) < 1e-6 else errs).append(
        f"key socket {KEY_SOCKET_DEPTH} deep = stem engagement {s['post_end'] - s['stem_top']:.1f} → stem bottoms at the design depth")
    (oks if s["skirt_end"] + MX_TRAVEL <= s["plate_front"] - 1.0 else errs).append(
        f"key skirt ends at d {s['skirt_end']:.1f} ({s['skirt_end'] + MX_TRAVEL:.1f} pressed), switch plate at {s['plate_front']:.1f}")
    total = s["mx_pins"] - s["glass"]
    oks.append(f"key stack {total:.1f} mm total, {s['mx_pins']:.1f} mm behind the rocker front "
               f"(was 36.0 / 28.0 with the misread MX height)")

    if SPK_PORT_FACE is None:
        warns.append("speaker sound-port face unknown → duct design pending (measure when it arrives)")
    if AMP_W == 18.0:
        warns.append("MAX98357A board size is a placeholder → measure")
    if TB_STANDOFF_THREAD is None:
        warns.append("touch-board brass standoffs assumed female M2 (key shell screws into them) → check")
    warns.append("LD2410C 16 × 22 does not fit a 13 mm wing — see insert_params.py (radar deferred)")
    warns.append(f"INMP441 round module Ø{MIC_D} is wider than the wing → wall insert uses an 8 × 8 carrier (custom)")
    if MX_PINCOUNT == 3:
        oks.append("key switch is plate mount (3-pin) → 1.5 mm switch plate")

    if verbose:
        for m in errs:
            print("ERROR   ", m)
        for m in warns:
            print("WARNING ", m)
        for m in oks:
            print("OK      ", m)
        print(f"\n{len(errs)} error(s), {len(warns)} warning(s), {len(oks)} ok")
    return not errs


if __name__ == "__main__":
    raise SystemExit(0 if validate() else 1)
