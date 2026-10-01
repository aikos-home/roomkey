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
MX_PINCOUNT = 3          # [MEAS] 2 metal pins + centre post, no side pegs → plate mount (needs the 1.5 mm plate)

# ============================================================== audio
MIC_D, MIC_T = 13.14, 2.83               # [MEAS] INMP441 round module (2026-09-29) — desk rig only, 0.07 mm wider than a wing
MIC_CARRIER = (8.0, 8.0, 2.6)            # [FREE] v0.2: INMP441 (4.72 × 3.76 [DS]) on an 8 × 8 × 0.8 carrier PCB, bottom port;
                                         #        2.6 = PCB + mic + solder [TBD] — custom part
SPK_W, SPK_H, SPK_T = 20.0, 30.0, 5.5    # [DS] Waveshare 2030 cavity speaker (the "4PIN" item is a PAIR)
SPK_PORT_FACE = "large"                  # [DS] vendor outline: mesh grille on one 20 × 30 face
SPK_PORT_W, SPK_PORT_H = 13.0, 18.5      # [TBD] grille scaled off the vendor outline drawing (±1 mm) — measure
AMP_W, AMP_H, AMP_T = 18.0, 18.0, 3.0    # [TBD] MAX98357A clone — measure

# ============================================================== optional sensors (bought 2026-09-29)
ALS_W, ALS_H = 14.0, 14.0                # [TBD] VEML7700 breakout, I²C 0x10 — measure; window = one grille hole
RH_W, RH_H = 14.0, 11.0                  # [TBD] SHT31-D breakout, I²C 0x44 — measure; needs room air, away from heat
RADAR_W, RADAR_H, RADAR_T = 16.0, 22.0, 3.5   # [DS] HLK-LD2410C 16 × 22 (manual); 5 V; sees through thin plastic, not metal
RADAR_B_W, RADAR_B_H = 7.0, 35.0         # [DS] HLK-LD2410B 7 × 35 (the slim version, 1.27 mm pin pitch)

# ============================================================== design choices
KEY_WALL = 1.0           # [FREE] keycap shell wall around the touch board
KEY_FIT = 0.15           # [FREE] clearance board frame ↔ shell pocket, per side (tune on the first print)
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
MX_GUIDE = ("2 × the same brown (tactile) switch, wired in parallel: an end press acts on one switch and feels the same at "
            "both ends; a centre press gives two simultaneous bumps (felt as one) — desk rig")   # [FREE] v0.4
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
