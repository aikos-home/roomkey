# RoomKey kit — printing and assembly (v0.10.3, WIP)

> **Prototype for the desk. WIP: modelled and CAD-checked; the parts of this exact revision are not all printed and
> tested yet.** The kit is the whole RoomKey in one practice box, powered from a lab supply (5.0 V, about 1 A). It is
> SELV only. Never put it into a wall box, and never connect it to 230 V.

## What you print

Nine parts. Everything is **white PETG** except the light-guide collar, which is **clear PLA**. Every part prints flat
**without supports**, with one exception: the key shell needs supports inside its board pocket.

| # | Part | STL (in [`../models/`](../models/)) | Material | On the bed | Supports |
|---|---|---|---|---|---|
| 1 | Front plate 55 × 55 | `plate_S_print.stl` | PETG white | visible face down | none |
| 2a | Chassis, front part (deck, pockets, frame rims, mic tube) | `kit_chassis_1_front_print.stl` | PETG white | front down | none |
| 2b | Chassis, flange with webs and 2 pins | `kit_chassis_2_flange_print.stl` | PETG white | front down | none |
| 2c | Chassis, rear part (rear wall, ledge, speaker cradle, posts) | `kit_chassis_3_rear_print.stl` | PETG white | front down | none |
| 3 | Key shell (holds the touch board) | `key_shell_print.stl` | PETG white | front edge down | **tree supports in the pocket** |
| 4 | Light-guide collar | `collar_print.stl` | **PLA clear** | back face down | none |
| 5 | Switch plate with cable anchor | `switch_plate_print.stl` | PETG white | front down | none |
| 6 | Back carrier (radar tray, amplifier pins) | `kit_back_carrier_print.stl` | PETG white | flat, tray up | none |

The STL files are already oriented for printing.

## Bambu Lab A1 files (ready to print)

[`bambu/`](bambu/) holds sliced `.gcode.3mf` files for a Bambu Lab A1 with an AMS lite, for a **0.4** and a **0.2**
nozzle. There are three plates per nozzle:

| Plate | Parts | Filaments | Time 0.4 / 0.2 nozzle |
|---|---|---|---|
| `A-petg` | 1, 2a, 2b, 2c, 5, 6 | PETG white | ≈ 3 h 47 / 6 h 42 |
| `B-key` | 3, with supports | PETG white (part + support body), **PLA clear (support contact layers only)** | ≈ 1 h 54 / 3 h 22 |
| `C-collar-pla` | 4 | PLA clear | ≈ 43 min / 58 min |

- **Settings:** precise and slow. Layers 0.10 mm, 3 walls, outer walls 25 mm/s, inner walls 40 mm/s, first layer 15 mm/s,
  bridges 15 mm/s, 20 % gyroid infill. Textured PEI plate. Base presets: *0.12mm Fine @BBL A1* (0.4) and *0.10mm Standard
  @BBL A1 0.2 nozzle* (0.2); filaments *Generic PETG* and *Generic PLA*.
- **Plate B, the key shell:** tree supports from the build plate. The support body is PETG; the **interface (the layers
  that touch the part) is PLA**, with a top Z distance of 0. PLA does not bond to PETG, so the supports come off clean
  without tearing the thin walls. The A1 purges every filament change into its waste chute; there is no prime tower.
- **Before you print:** map the filaments to your AMS slots (white PETG / clear PLA) in Bambu Studio or Bambu Handy.
- **Re-slice:** [`../../tools/bambu_kit.py`](../../tools/bambu_kit.py) rebuilds all six files from the STLs (Windows,
  Bambu Studio installed).
- **Other printers:** use the STLs with the same settings. All parts except 3 need no supports. Short bridges up to
  9 mm print without support.

## Assembly

Glue: **gel cyanoacrylate (CA)**, used sparingly and only on the faces that touch. Roughen the glue faces with fine
sandpaper first.

### 1. Key (part 3)

1. Lay the touch board into the key shell from behind.
2. Screw it in with 4 × M2 × 4 countersunk screws into its brass standoffs.
3. The board sits in the shell with 0.15 mm per side and comes out only when pushed through a screw hole.

### 2. Chassis (parts 2a, 2b, 2c)

1. Put the front part (2a) on the flange (2b). **Push the collar (4) through both openings:** it aligns the two parts.
2. Glue the touching ribs and rims **from the outside**, not at the collar opening. When the glue has set, take the
   collar out again.
3. Put the rear part (2c) onto the two pins of the flange (2b). The holes have a lead-in chamfer. Glue the web tops.
   - If a pin does not go in, drill its hole to 1.5 mm, or cut the pin off and align by eye. The pins only align;
     the glue holds.

### 3. Switch plate (part 5)

1. Clip both MX switches into the switch plate and solder their wires (wiring: see below).
2. Lay the plate onto the ledge in the rear part (2c), from the front through the collar opening.
3. Fix it with 2–3 dots of CA. The MX switches can still be pulled out from the front.

### 4. Front

1. Press the key straight onto both switch stems, like a keycap. The top socket is tight; the bottom one floats a
   little along the key's length, on purpose.
2. Slide the collar (4) over the key from the front. Its grooves take the key's catch nubs from behind. **Do not
   glue the collar.**
3. Snap the front plate (1) on. It holds the collar, and the collar holds the key captive.

### 5. Back carrier (part 6)

1. Put the LD2410C radar into its tray: **antenna side to the front, pin header towards the wall.** It rests on two
   ledges at its short ends. Use a dot of hot glue at two corners.
2. Push the MAX98357A amplifier onto its two pins.
3. Slide the carrier onto the four pins of the chassis posts and glue it.

Microphone: the foam ring between the front plate and the mic tube is **2 mm** thick (1.5 mm compressed).
Speaker: it goes in from behind with its **wire tab pointing up**, into the slot in the upper cradle rib.

**Wiring:** every wire is routed in 3D in the CAD; cut lengths are in
[`../models/kit-v0.10.3_wiring.json`](../models/kit-v0.10.3_wiring.json) and the picture is in the
[hardware README](../README.md).

## Fits found on real prints (A1, PETG, 0.10 mm layers)

| Fit | Value | How it was found |
|---|---|---|
| Touch board in the key shell | 0.15 / side | measured, "extremely perfect" |
| Key in the collar | 0.40 / side | 0.25 scraped |
| Radar in its tray | 0.10 / side | 0.15 fit once, then was loose on the next print |
| Amplifier pins | pitch 13.435, Ø 1.9 | 13.97 too wide, 12.9 too close |
| Chassis pins 2b → 2c | Ø 1.2 in Ø 1.5 + 45° lead-in | 0.1 play closed up on the bed face |

Design background and change log: [`../docs/insert-design.md`](../docs/insert-design.md) (§0 changes, §11 assembly).
