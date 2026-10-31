# RoomKey — printing (v0.12, WIP)

> **WIP: modelled and CAD-checked; this revision is not printed or tested yet.** RoomKey is a plug-in device that takes
> 5 V SELV only. The housing holds an unmodified, certified USB charger; nothing printed here touches 230 V.

Two builds share every printed front part; they differ behind the switch plate (`pcb`: hub PCB + radar cage,
`discrete`: back carrier) and in the housing's length. Bought parts and assembly: [../BUILD.md](../BUILD.md).

## Front stack and electronics (STLs in [`../models/`](../models/), already oriented for printing)

| # | Part | STL | Material | On the bed | Supports |
|---|---|---|---|---|---|
| 1 | Plate 55 × 55 (glow rim in a second colour) | `plate_print.stl` (or `plate_body_print.stl` + `plate_glowrim_print.stl`) | PETG ivory + natural | visible face down | none |
| 1r | Plate, resin version: the face is **cast** (resin thread), the back printed and glued on (skirts, lips, rest pads on a 0.6 glue flange; the skirts' outer faces are the datum) | `plate_face_print.stl` (master), `plate_back_print.stl` | resin / PETG | flange down | none |
| 2a | Chassis, front part | `kit-<build>_chassis_1_front_print.stl` | PETG V-0 | front down | none |
| 2b | Chassis, flange (+ radar blade, PCB) | `kit-<build>_chassis_2_flange_print.stl` | PETG V-0 | front down | none |
| 2c | Chassis, rear part | `kit-<build>_chassis_3_rear_print.stl` | PETG V-0 | front down | none |
| 3 | Key shell | `key_shell_print.stl` | PETG | front edge down | **tree supports in the pocket** |
| 4 | Light-guide collar | `collar_print.stl` | PLA clear / PCTG | back face down | none |
| 5 | Switch plate with the LED holder | `kit-<build>_switch_plate_print.stl` | PETG V-0 | front down | none |
| 6p | Radar cage (PCB build) | `kit-pcb_radar_cage_print.stl` | PETG V-0 | back down | none |
| 7p | Hub stand-in for a fit test (PCB build) | `kit-pcb_hub_dummy_print.stl` | any | front down | none |
| 6d | Back carrier (self-wired build) | `kit-discrete_back_carrier_print.stl` | PETG V-0 | front down | none |

## Plug-in housing (details: [../docs/plug-in-housing.md](../docs/plug-in-housing.md))

| Part | STL | Material | On the bed |
|---|---|---|---|
| G1 skin — **cast in resin** (the resin thread's moulds); this STL is for a first fit only | `plug-<build>_skin_print.stl` | PETG | front down |
| G1 tunnel | `plug-<build>_tunnel_print.stl` | PETG V-0 | front down |
| G1 column (print 4) | `plug-<build>_column_print.stl` | PETG V-0 | back down |
| G2 lid with charger sleeve | `plug-<build>_box_print.stl` | PETG V-0 | back down |
| grip-ring coupons 1–3, probe sleeve | `plug_grip_1…3_print.stl`, `plug_probe_print.stl` | TPU 95A / PETG | back down |
| foot ring | `plug_foot_print.stl` | TPU 95A | flat |

G2, the probe and the grip rings share one print frame: loaded together as one object of several parts, a grip ring
sits in its seat (two-nozzle print on the X2D).

## Bambu Lab A1 files

[`bambu/`](bambu/) holds sliced `.gcode.3mf` files of the kit (parts 1–7) for a Bambu Lab A1 with an AMS lite, for a
**0.4** and a **0.2** nozzle, per build: `A-petg` (plate, chassis, switch plate, radar cage + hub stand-in / back
carrier), `B-key` (key shell; PETG with PLA support interface), `C-collar-pla`.

- **Settings:** layers 0.10 mm, 3 walls, outer walls 25 mm/s, first layer 15 mm/s, bridges 15 mm/s, 20 % gyroid.
  Textured PEI plate.
- **Re-slice:** [`../../tools/bambu_kit.py`](../../tools/bambu_kit.py) `pcb` / `discrete` (Windows, Bambu Studio installed).
- **Other printers:** use the STLs with the same settings.

## Fits found on real prints (A1, PETG, 0.10 mm layers, 0.2 nozzle)

| Fit | Value | How it was found |
|---|---|---|
| Touch board in the key shell | 0.10 / side | 0.15 was perfect with a 0.4 nozzle, loose with the 0.2 |
| Key in the collar | 0.40 / side | 0.25 scraped |
| Radar in its tray / cage | 0.10 / side | 0.15 fit once, then was loose on the next print |
| Amplifier pins | pitch 13.435, Ø 1.9 | 13.97 too wide, 12.9 too close |
| Chassis pins 2b → 2c | Ø 1.2 in Ø 1.5 + 45° lead-in | 0.1 play closed up on the bed face |

A 0.4 nozzle prints holes and pockets a little smaller: if the touch board or the radar is too tight, sand lightly.
