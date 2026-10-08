# RoomKey kit — printing (parts v0.10.4, WIP)

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

The assembly and gluing steps, the bought parts and the first tests are in **[../BUILD.md](../BUILD.md)**.

## Fits found on real prints (A1, PETG, 0.10 mm layers)

**The fits are tuned for a 0.2 nozzle** (the RoomKey parts are printed with one since 2026-10-08). A 0.4 nozzle
prints holes and pockets a little smaller: if the touch board or the radar is too tight, sand the inner walls lightly.


| Fit | Value | How it was found |
|---|---|---|
| Touch board in the key shell | 0.10 / side | 0.15 was "extremely perfect" with a 0.4 nozzle, loose with the 0.2 |
| Key in the collar | 0.40 / side | 0.25 scraped |
| Radar in its tray | 0.10 / side | 0.15 fit once, then was loose on the next print |
| Amplifier pins | pitch 13.435, Ø 1.9 | 13.97 too wide, 12.9 too close |
| Chassis pins 2b → 2c | Ø 1.2 in Ø 1.5 + 45° lead-in | 0.1 play closed up on the bed face |

Design background and change log: [`../docs/insert-design.md`](../docs/insert-design.md) (§0 changes, §11 assembly).
