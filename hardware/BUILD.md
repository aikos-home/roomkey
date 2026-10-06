# Build guide: RoomKey desk prototype (kit v0.8)

> **WIP prototype, for the desk only.** Never put it in a wall and never connect it to 230 V. Power comes from a lab
> supply. Nothing here is certified or reviewed. The in-wall product is designed in [docs/insert-design.md](docs/insert-design.md).

The kit is the whole RoomKey in **one** flush box: touch key, speaker, microphone, presence radar, amplifier and a
humidity sensor in the frame. It goes into a printed **practice box**, a flush-box replica with a 1-gang frame, so it can
be built and tested on the bench.

![Kit in the practice box](docs/img/kit_front.png)

## Status (2026-10-06)

| Part | State |
|---|---|
| Practice box + frame | printed and fitted ✓. Frame vents centred (v0.8) |
| Chassis, plate, switch plate | printed ✓. The touch board fits its pocket with 0.15 mm per side ✓ |
| Back carrier with radar tray (v0.8) | printed, **fits perfectly** ✓ |
| **Key (touch board on two MX switches)** | **WIP. The rocker concept is dropped**; a replacement key is being designed. The v0.8 key shell and collar are interim parts (catch nubs keep the key in; not print-tested) |
| Radar range through the plate | not tested yet; this is the key test |
| Audio (mic, speaker loudness), glow ring | not tested yet |

## 1. What you need

**Bought parts:**

| Part | Notes |
|---|---|
| Waveshare ESP32-C6-Touch-LCD-1.47 (touch board) | the key's face. 24.55 × 44.50 × 10.6 |
| 2 × MX-style key switch, plate mount (3-pin) | under the key. A single switch on BOOT also works with today's firmware |
| HLK-LD2410C presence radar | 15.84 × 22.26; header soldered |
| MAX98357A I²S amplifier breakout | solder the speaker to its pads, not the screw terminal |
| Waveshare 2030 cavity speaker | 19.3 × 29.8 × 4.6 (sold as a pair on one plug) |
| INMP441 microphone module (round) | Ø13.1 |
| SHT31-D humidity/temperature breakout | sits in the frame's bottom border |
| 4 × WS2812B-MINI 3535 LEDs | glow ring |
| VEML7700 light sensor | optional. It does not fit the kit yet (a smaller chip is planned) |

Every measured dimension and its source are in [`cad/roomkey_params.py`](cad/roomkey_params.py).

**Small parts:**
- 4 × M3 × 8 for the frame;
- 2 × device screws 3.2 × 15 (or M3 × 16) for the insert;
- 2 foam rings for the mic tube: about 0.8 thick, 3.5 outside, 1.5 inside;
- hot glue;
- 0.05 mm² silicone wire, plus thicker wire for the 5 V node (see the wiring doc);
- a lab supply.

## 2. Print

Bambu Lab A1, 0.4 nozzle, **PETG**. The files are already oriented for printing; don't rotate them. Arrange all parts on
one bed, with about 10 mm free around the two parts that need supports.

| File in [`models/`](models/) | Part | Supports | Layer |
|---|---|---|---|
| `practice_box_print.stl` | practice box (box + "wall" plate) | none | 0.20 |
| `practice_frame_1x_print.stl` | 1-gang frame, AS 500 size, with the sensor pocket | none | 0.20 |
| `plate_S_print.stl` | plate 55 × 55 | none | 0.10 |
| `kit_chassis_print.stl` | chassis with the mic tube and carrier pins | tree (auto), Top Z distance 0.3 | 0.10 |
| `key_shell_print.stl` | key shell (**interim**, see Status) | tree, only in the pocket, Top Z distance 0.3 | 0.10 |
| `collar_print.stl` | glow collar (**interim**) | none | 0.10 |
| `switch_plate_print.stl` | switch plate | none | 0.10 |
| `kit_back_carrier_print.stl` | back carrier with the radar tray | none | 0.10 |

PETG supports stick hard. With an AMS, use PLA as the support interface.

## 3. Assemble

1. **Frame:**
   - Lay the SHT31-D flat into the pocket behind the frame's bottom border: chip side forward, pins to the left (front
     view). Fix it with a dot of hot glue, not on the chip.
   - Screw the frame to the practice box with 4 × M3 × 8 from behind.
2. **Switches:** clip both MX switches into the switch plate (wire them first). Screw the switch plate into the chassis.
3. **Key** (interim v0.8 order):
   - push the key shell with the touch board onto the switch stems;
   - slide the collar over the key from the front. Do **not** glue it;
   - put the plate on. The plate holds the collar, and the collar holds the key.
4. **Mic:** put a foam ring on each end of the sound tube. Press the INMP441 into its holder (upper left, behind the
   ledge): labelled side forward, port on the tube.
5. **Back carrier:**
   - Lay the radar into the tray: antenna side forward, header towards the box wall.
   - Push the amplifier onto its two pins, components to the back.
   - Push the carrier onto the four pins and fix it with a drop of glue.
6. **Wiring:** follow [`../docs/wiring-touch-board.md`](../docs/wiring-touch-board.md). It has every pin, the shared
   lines, wire gauges and the **5 V node** for bench power, and it is checked against the firmware.
   [`models/kit_wiring.json`](models/kit_wiring.json) holds 3D-routed lengths from an earlier per-part plan; use them only
   as length estimates.
7. **Into the box:** slide the insert into the practice box and fix it with the 2 device screws.

**Service:** the plate comes off first, then the collar, then the key. The touch board comes out of the key shell by
pushing it through a screw hole.

## 4. Power and first tests

- **Power:** set the supply as described in "Power without USB" in the wiring doc. That is 5.0 V, with the current limit
  raised once the amp and LEDs are on. The 5 V goes into the node at the parts; the board's VBUS gets it through a
  Schottky diode. Never apply 12 V to the 5 V node.
- **Tests:**
  - **Key:** press it; it must be free and must not fall out.
  - **Touch:** taps and swipes must not trigger the key.
  - **Radar:** compare the range with and without the insert in front.
  - **Speaker:** compare a chime at full volume with your doorbell, using a level app at 1 m.
  - **Mic:** check the level.
  - **Humidity:** check that the reading follows the room.

## Regenerate the files

All parts come from Python scripts; see [README.md](README.md). Run headless, from the repo root:

```bash
FC=/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd
for f in make_key_module make_insert_S make_practice_box make_kit; do
  PYTHONIOENCODING=utf-8 $FC -c "exec(open('hardware/cad/$f.py', encoding='utf-8').read())"; done
```

Each run prints its collision and clearance checks. They must report 0 collisions, and the key check must report
"CAPTIVE".
