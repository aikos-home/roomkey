"""RoomKey hardware — the ONE source of every dimension.

CAD generators, drawings and checks all read this file, so they cannot disagree.
`python3 roomkey_params.py` runs validate(): every geometric rule, then ERROR / WARNING / OK.

Tags: [DS] datasheet or vendor drawing · [MEAS] measured on the real part ·
      [FREE] design choice · [TBD] placeholder until measured.
Units: mm. Front view: origin = rocker centre, x right, y up, z = depth into the wall (+).
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
BOX_D_INNER = 58.0       # [DS] German flush box (UP-Dose), Ø60 bore, ≈58 usable inside
BOX_DEPTH_STD = 40.0     # [DS] standard box
BOX_DEPTH_DEEP = 61.0    # [DS] deep "Elektronikdose" — the plan for RoomKey
BOX_SCREW_PITCH = 60.0   # [DS] support-ring screws

# ============================================================== touch board (target)
# Waveshare ESP32-C6-Touch-LCD-1.47, vendor dimension drawing
TB_W, TB_H, TB_T = 24.55, 44.50, 10.60   # [DS] outline incl. black frame, total thickness
TB_GLASS_W, TB_GLASS_H = 22.05, 42.00    # [DS]
TB_ACTIVE_W, TB_ACTIVE_H = 17.75, 32.93  # [DS] visible pixels
TB_FRONT_T = 5.40                        # [DS] frame part in front of the PCB
TB_HOLE_DX, TB_HOLE_DY = 17.78, 39.00    # [DS] M2 mounting holes (PCB side)

# ============================================================== PoC board (desk)
PB_W, PB_H = 20.32, 36.37                # [DS] ESP32-C6-LCD-1.47 bare PCB, portrait

# ============================================================== key switch (MX-style, no-name brown)
MX_CUT = 14.0            # [DS] plate cut-out — coupon tunes this per printer: 13.9 / 14.0 / 14.1
MX_PLATE_T = 1.5         # [DS] plate thickness the clips expect
MX_TOP_W = 15.6          # [DS] top housing footprint
MX_ABOVE_PLATE = 11.6    # [DS] stem top above plate at rest
MX_BELOW_PLATE = 5.0     # [DS] housing below plate (+ 3.3 pins)
MX_PINS = 3.3            # [DS]
MX_TRAVEL = 4.0          # [DS]
MX_STEM_ARM_L = 4.10     # [FREE] keycap socket cross: arm length (coupon: 4.05 / 4.10 / 4.15)
MX_STEM_ARM_W = 1.30     # [FREE] arm width (coupon: 1.25 / 1.30 / 1.35)
MX_STEM_DEPTH = 3.8      # [DS] stem engagement ≈ 3.6–4.0
MX_PINCOUNT = 3          # [MEAS] 2 metal pins + centre post, no side pegs → plate mount (needs the 1.5 mm plate)

# ============================================================== audio
MIC_D, MIC_T = 13.14, 2.83               # [MEAS] INMP441 round module (2026-09-29)
MIC_PORT_D = 1.0                         # [FREE] pinhole in the rocker
SPK_W, SPK_H, SPK_T = 20.0, 30.0, 5.5    # [DS] Waveshare 2030 cavity speaker
SPK_PORT_FACE = None                     # [TBD] which face has the sound opening
AMP_W, AMP_H, AMP_T = 18.0, 18.0, 3.0    # [TBD] MAX98357A clone — measure

# ============================================================== optional sensors (bought 2026-09-29)
ALS_W, ALS_H = 14.0, 14.0                # [TBD] VEML7700 breakout, I²C 0x10 — measure; window = one grille hole
RH_W, RH_H = 14.0, 11.0                  # [TBD] SHT31-D breakout, I²C 0x44 — measure; needs room air, away from heat
RADAR_W, RADAR_H, RADAR_T = 16.0, 22.0, 3.5   # [DS] HLK-LD2410C ≈ 22 × 16 mm, 5 V; sees through thin plastic, not metal

# ============================================================== design choices
KEY_WALL = 1.2           # [FREE] keycap shell wall around the touch board
KEY_GAP = 1.0            # [FREE] shadow gap key ⇄ rocker cut-out
KEY_PROUD = 8.0          # [FREE] key top above rocker front
KEY_W = TB_W + 2 * KEY_WALL
KEY_H = TB_H + 2 * KEY_WALL
CUT_W = KEY_W + 2 * KEY_GAP
CUT_H = KEY_H + 2 * KEY_GAP
SWITCH_PITCH_Y = 24.0    # [FREE] two switches under the key: one wired, one as guide
SPK_ON_EDGE = True       # [FREE] speaker stands on its 5.5 mm edge behind the right wing
CLEAR = 0.5              # [FREE] minimum clearance between parts

# printer / material
XY_COMP = {"PLA": 0.10, "PETG": 0.12, "ABS": 0.20}   # [FREE] hole oversize, tuned by the coupon


def validate(verbose=True):
    errs, warns, oks = [], [], []
    g = globals()
    for k, v in FROZEN.items():
        (errs if abs(g[k] - v) > 1e-9 else oks).append(f"frozen {k} = {g[k]}")

    wing = (ROCKER_W - CUT_W) / 2
    band = (ROCKER_H - CUT_H) / 2
    (errs if CUT_W >= ROCKER_W or CUT_H >= ROCKER_H else oks).append(
        f"key cut-out {CUT_W:.1f} × {CUT_H:.1f} inside the {ROCKER_W:.0f} × {ROCKER_H:.0f} rocker")
    (warns if band < 3.0 else oks).append(f"rocker band above/below the key {band:.1f} mm (≥ 3 for strength)")
    (oks if wing >= 10 else warns).append(f"side wing {wing:.1f} mm (room for perforation + a thumb)")

    r = BOX_D_INNER / 2
    cx, cy = KEY_W / 2, KEY_H / 2
    (errs if math.hypot(cx, cy) > r else oks).append(
        f"key corners at r = {math.hypot(cx, cy):.1f} mm inside the Ø{BOX_D_INNER:.0f} box")

    if SPK_ON_EDGE:
        x0 = CUT_W / 2 + CLEAR
        x1 = x0 + SPK_T
        half_h_avail = math.sqrt(max(0.0, r * r - x1 * x1))
        ok = half_h_avail >= SPK_H / 2 + CLEAR
        (oks if ok else errs).append(
            f"speaker on edge x {x0:.1f}…{x1:.1f}: needs ±{SPK_H/2:.1f}, box allows ±{half_h_avail:.1f}")
        (oks if SPK_W + CLEAR <= BOX_DEPTH_STD else errs).append(
            f"speaker depth {SPK_W:.0f} mm into the box (standard box {BOX_DEPTH_STD:.0f})")
    if SPK_PORT_FACE is None:
        warns.append("speaker sound-port face unknown → duct design pending (measure when it arrives)")

    mic_cx = -(CUT_W / 2 + CLEAR + MIC_D / 2)
    (oks if abs(mic_cx) + MIC_D / 2 <= r - CLEAR else errs).append(
        f"INMP441 Ø{MIC_D} behind the left wing, outer edge at {abs(mic_cx) + MIC_D/2:.1f} (box r {r:.1f})")

    span = SWITCH_PITCH_Y + MX_TOP_W
    (oks if span <= KEY_H else errs).append(
        f"two switches under the key span {span:.1f} mm of the {KEY_H:.1f} mm key")
    (oks if MX_TOP_W <= KEY_W else errs).append(f"switch {MX_TOP_W} fits the key width {KEY_W:.1f}")

    stack = KEY_PROUD + TB_T + MX_ABOVE_PLATE - MX_TRAVEL + MX_PLATE_T + MX_BELOW_PLATE + MX_PINS
    (oks if stack - KEY_PROUD <= BOX_DEPTH_DEEP else errs).append(
        f"key stack {stack:.1f} mm total, {stack - KEY_PROUD:.1f} mm behind the rocker front (deep box {BOX_DEPTH_DEEP:.0f})")
    # radar: antenna must face the room with only plastic in front → behind a wing, not behind the key
    rx0 = CUT_W / 2 + CLEAR
    need_x = rx0 + RADAR_W
    half_h = math.sqrt(max(0.0, r * r - need_x * need_x)) if need_x < r else 0.0
    if need_x <= ROCKER_W / 2 and half_h >= RADAR_H / 2:
        oks.append(f"LD2410C {RADAR_W:.0f}×{RADAR_H:.0f} fits behind a wing inside the box")
    else:
        warns.append(f"LD2410C {RADAR_W:.0f}×{RADAR_H:.0f} does NOT fit behind a {wing:.0f} mm wing inside the Ø{BOX_D_INNER:.0f} box "
                     f"(needs x to {need_x:.1f}, rocker edge {ROCKER_W/2:.1f}) → place it upright/edge-on, in the few mm between "
                     f"rocker and wall outside the box, or use a slimmer radar — decide in the fit model")
    if AMP_W == 18.0:
        warns.append("MAX98357A board size is a placeholder → measure")
    if MX_PINCOUNT == 3:
        oks.append("key switch is plate mount (3-pin) → 1.5 mm switch plate in the key carrier")

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
