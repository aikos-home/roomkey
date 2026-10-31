# Build guide: RoomKey (plug-in device, WIP)

> **WIP prototype.** Nothing here is certified or reviewed, and this revision is not printed or tested yet.
> RoomKey takes only 5 V SELV. In the finished device that comes from an unmodified, certified plug-in USB charger,
> which the housing holds; nothing of the RoomKey is ever wired to 230 V. On the bench, power it from a lab supply
> (5.0 V, current-limited) before it goes into the housing.

RoomKey is built **only as a plug-in device** (owner, 2026-10-31): the front stack (key on two MX switches, plate
55 × 55 with its glow ring, collar, switch plate with the LED holder, chassis) and the electronics sit in a **64 × 64
housing that plugs into a SCHUKO socket**. Housing details: [docs/plug-in-housing.md](docs/plug-in-housing.md).

There are **two builds of the electronics from one set of CAD scripts** (every fit fix goes into both):

| build | electronics | glass → socket face |
|---|---|---|
| `pcb` | the hub PCB behind the switch plate (rev D for this housing is in progress, not published yet); the radar in a cage in the hub plane | 55.0 mm |
| `discrete` | self-wired modules: a back carrier with radar and amplifier, the round mic, every wire by hand | 64.0 mm |

## 1. What you need

**Bought parts (both builds):**

| Part | Notes |
|---|---|
| Waveshare ESP32-C6-Touch-LCD-1.47 | the key's face |
| 2 × MX-style key switch, plate mount | under the key; both are one key in the firmware |
| HLK-LD2410C presence radar | header pins cut to 2 mm (or the header removed); wires soldered on |
| Waveshare 2030 cavity speaker | |
| 4 × WS2812B-MINI 3535 LEDs | glow ring, in the switch plate's LED holder |
| SHT31-D humidity/temperature breakout | in the housing's bottom wall (PCB build later: the sensor tail) |
| revolt PX-8884 USB charger (5 V 2.1 A) | unmodified; the housing holds it |
| bare solder-type USB-A plug (no overmould) | in the charger's port |
| 4 × M3 heat-set inserts (Ø4.0 hole), 4 × M3 × 10 countersunk | housing |
| TPU 95A filament | grip ring + foot ring |

**PCB build in addition:** the hub PCB (not ordered yet), a JST PH 2-pin lead for J1.
**Self-wired build in addition:** MAX98357A breakout, INMP441 mic (round), 0.05 mm² silicone wire.

## 2. Print

Part list, orientation and ready-to-print Bambu files: **[print/README.md](print/README.md)**. The housing's visible
skin is cast in resin; for a first fit it prints in PETG, front down.

## 3. Assemble

Glue with gel CA, sparingly and only on faces that touch.

1. **Chassis (2a front, 2b flange, 2c rear):** put 2a on 2b and push the collar through both openings to align them;
   glue the ribs and rims from the outside; take the collar out again. Put 2c onto the two pins of 2b and glue.
2. **Switch plate:** solder the four LEDs to their wires first, then press them into the corner seats (lens forward)
   and glue them; wires through the holes into the back channels. Clip both MX switches in. Then the switch plate goes
   into 2c from the front (the LED corners are wider than the collar opening) and is fixed with 2–3 dots of CA.
3. **Key:** touch board into the key shell (4 × M2 × 4), key onto both stems, collar over the key (not glued). The
   plate holds the collar, the collar holds the key.
4. **Speaker** from behind, wire tab up, into the slot of the upper cradle rib.
5. **Electronics:**
   - PCB build: radar into its cage (from the +x side), cage onto the chassis blade; hub onto its posts (3 × M2).
   - Self-wired build: radar and amplifier onto the back carrier, carrier onto the four pins; mic into its holder.
6. **Wiring:** PCB build — the hub's soldering map comes with the hub PCB rev D;
   self-wired build — every wire with its cut length in `models/kit-discrete-v0.12_wiring.json`. Pins and lines:
   [`../docs/wiring-touch-board.md`](../docs/wiring-touch-board.md).
7. **Bench test** (lab supply 5.0 V into J1 / the splice points) before the housing.
8. **Housing:** see [docs/plug-in-housing.md](docs/plug-in-housing.md) § Assembly.

**Service:** unscrew G2 (4 screws) and take it off backwards; the insert comes out to the back. The plate comes off to
the front, then the collar, then the key.

## 4. First tests

- **Key:** press it every 5 mm along its length and many times at both ends. Every press must click and come back.
- **Touch:** taps and swipes must not trigger the key.
- **Radar:** range through the plate, with and without the housing.
- **Speaker / mic:** chime at full volume vs. your doorbell (level app at 1 m); mic level.
- **Humidity / temperature:** compare with a reference for a day (the charger warms the housing).

## Regenerate the files

All parts come from Python scripts. Run headless from the repo root (Windows: `C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe`):

```bash
FC=/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd
for f in make_key_module make_front make_kit make_plug; do
  PYTHONIOENCODING=utf-8 $FC -c "exec(open('hardware/cad/$f.py', encoding='utf-8').read())"; done
```

Each run prints its checks: 0 collisions, the key "CAPTIVE", the wiring with 0 hits (PCB build), G2's way in "free".
`python3 hardware/cad/insert_params.py` must show 0 errors, `tools/insert_wallcheck.py` reports the thinnest walls.
`python tools/bambu_kit.py pcb|discrete` rebuilds the Bambu files of the kit (Windows, Bambu Studio installed).
