# RoomKey hub PCB set

Three small boards replace the kit's loose breakouts and hand wiring. **Status 2026-10-31: hub rev D routed (rev B after an
independent review; rev C: the 5 V input J1 as a JST PH plug; rev D: fitted to the 64 × 64 plug-in housing — square
outline, radar in the hub plane, J1 side entry), DRC 0/0/0, order files ready, nothing ordered (pre-alpha); the small
boards are schematics only.** Decisions: owner, 2026-10-08 and 2026-10-31.

| Board | Folder | Where it sits | What it carries |
|---|---|---|---|
| **Hub** | `hub/` | static, directly behind the switch plate; the two MX switches plug into it | 5 V input + protection, MX hot-swap sockets, amplifier, I²S mic, 3.3 V regulator, LED data buffer; plugs for radar, speaker and sensor tail; a side-entry JST PH plug for the 5 V lead (J1); solder holes for the key wires and the glow LEDs |
| **Sensor tail** | `sht-tail/` | the frame's bottom border, in room air and light | SHT40 temperature/humidity + VEML6030 light sensor on a 4-pin Qwiic cable |
| **Pogo adapter** | `pogo/` | on the touch board, moves with the key | 15 spring pins on the bare H1 pads → 16-pin FFC to the hub (later; the first order is wired) |
| **Glow LEDs** | — | behind the 4 corners of the clear collar, facing forward | 4 × WS2812B-Mini 3535, hand-wired (owner ordered 50 loose, 2026-10-03), chain from J8. No LED board (owner, 2026-10-12, see Open points) |

**One RoomKey (owner, 2026-10-08):** no variants. The only push-buttons are the two MX switches under the one rigid
key (IO9 top, IO6 bottom; the firmware ORs them). The plate is fixed. So the hub has **no plate input and no I/O
expander**: it uses exactly the kit's ESP pins, and the firmware needs no change for it.

**Power:** only 5 V SELV reaches RoomKey: RoomKey is built as a plug-in device only (owner, 2026-10-31). A
certified, unmodified USB charger (revolt PX-8884, 5 V 2.1 A) sits behind it in the housing; a short lead from a
solder-type USB-A plug in the charger plugs into J1 (JST PH 2-pin, side entry). **No board here ever carries 230 V.**

**Why several KiCad projects:** KiCad has one PCB per project. The one thing they share, the key-wire / FFC order between
hub and pogo adapter, is defined once in `gen_schematics.py` (`FFC_PINS`) and written into both schematics.

## Files

- `gen_schematics.py` — the source of the schematics: parts, values, part numbers (MPN, LCSC), nets. It writes the
  `.kicad_sch` files and `lib/roomkey.kicad_sym`, and checks that no texts overlap, no two nets touch and every named
  net reaches at least two pins.
- `hub/`, `sht-tail/`, `pogo/` — KiCad 10 projects. `hub/roomkey-hub.kicad_pcb` is the routed board.
- `lib/roomkey.kicad_sym`, `lib/roomkey.pretty` — symbols and footprints KiCad does not ship (TPS25200, VEML6030,
  MAX98357A with its exposed pad as a passive pin; Mill-Max 0900 spring pin; Kailh MX hot-swap socket).
- `output/*.pdf` schematics, `output/*-bom.csv` grouped BOMs (MPN + maker), `output/jlcpcb/` the order files,
  `output/roomkey-hub.step` for the kit CAD (exported with `--subst-models --no-dnp`: bare solder holes carry no model), `output/roomkey-hub_overview_de.png` (what is what, German),
  `output/roomkey-hub_soldering-map.png` (where each wire goes).

Scripts (run in this order with KiCad's Python, `"C:/Program Files/KiCad/10.0/bin/python.exe"`):
1. `gen_schematics.py` — schematics + project library; then `kicad-cli sch erc` on each.
2. `gen_layout_hub.py` — outline from the kit CAD and placement (all parts on the back).
3. `route_hub.py` — re-runs 2, GND/+5V fan-out vias, Freerouting (Java 25 + freerouting-2.5.0.jar in `~/tools` or
   `$ROOMKEY_TOOLS`, downloaded with the owner's OK; it opens a window while it works), keeps the best round, GND pours.
   Freerouting is randomised, so the routed `.kicad_pcb` is the artifact.
4. `complete_route.py` — rip-up-and-reroute where it helps, then closes leftovers on F.Cu/B.Cu by grid search.
5. `export_jlc.py` — Gerbers + drill zip, BOM and CPL in JLCPCB's format into `output/jlcpcb/`.
6. `overview_map.py`, `soldering_map.py` — the two pictures. `add_wire_hole.py` — only if a key wire ever has to leave
   the 2 × 8 field: a single hole on its net's routed copper.

## What the hub does

1. **Power.** JST PH plug J1 for the 5 V lead from the USB charger (side entry, through-hole, 2 A; pin 2 = +5 V; the
   lead is AWG 24 at most, PH crimps take no thicker wire — 1.5 A over 10 cm drops ≈ 13 mV) → bidirectional TVS (ESD/surge) → P-FET Q1 (reverse polarity)
   → eFuse TPS25200 (current limit 1.5 A typ via R2 = 64.9 k; output clamp 5.25–5.55 V for 5.4–7.6 V in, output off
   above 6.8 V, so a 12 V supply by mistake is harmless; IN rated to 20 V; soft start; thermal cut-out) → **+5V node**
   (TVS, 100 µF) for amplifier, radar and LED ring. +5V → Schottky D4 → **VBUS_KEY** → the touch board's VBUS pad.
   D4 keeps the touch board's USB power out of the hub. The 3.3 V regulator (mic, key pull-ups, sensor tail) is fed from
   either side through the dual diode D5, so I²C and the IO8 pull-up are live whenever the key has power.
2. **Audio.** MAX98357A as on the kit's breakout (1 MΩ on SD_MODE = mono mix, gain 9 dB; standby whenever BCLK stops)
   + an ICS-43434 I²S MEMS mic on the same bus (half duplex, as today). Bottom port, through a 0.5 mm hole in the board
   at the sound tube's axis (−20.16, 9.6). IO8 (I²S WS) has its 10 k pull-up for the strapping.
3. **I²C** only goes on to the sensor tail plug J9 (Qwiic order GND, 3V3, SDA, SCL). The touch board already pulls the
   bus up (10 k); the hub's pull-ups R11/R12 are not fitted. Addresses: VEML6030 0x10, SHT40 0x44 (or the kit's SHT31
   0x44), touch 0x63, IMU 0x6B — no clashes.
4. **Switches and plugs.** The MX switches plug straight into Kailh hot-swap sockets (10 k pull-ups to 3.3 V). Radar
   on a cable (JST SH 5-pin in the module's silkscreen order TX, RX, OUT, GND, VCC; OUT is not used — presence comes over
   the UART — but keeps the cable 1:1). Glow LEDs through a 3.3 → 5 V buffer + 330 Ω, with 100 nF + 10 µF for the chain start, into three solder holes J8
   near the bottom-right corner (see layout). Speaker: 2-pin 1.25 mm.

## First order (owner, 2026-10-08): 7 hubs at JLCPCB, key wired

- **JLCPCB** (PCBWay's per-design setup made a first run ≈ €650). Order 10 bare hubs, **7 assembled**.
- **Standard PCBA, not Economic:** the ICS-43434 mic (C5656610) is "Standard Only" at JLCPCB (leadless, X-ray). All
  other parts allow both. Rough total ≈ €170–240 incl. shipping and VAT (Standard adds ≈ €25 of setup and stencil);
  the exact figure comes from JLCPCB's quote.
- **Only the hub** in this order. The kit's SHT31-D breakout plugs into J9 with a ready-made JST SH cable (pigtail
  soldered to the breakout); the radar with a ready-made JST SH 5-pin ↔ 2.54 mm Dupont cable (order kept 1:1). The
  glow LEDs are hand-wired as in the kit, their chain start into J8. Sensor tail and pogo link later.
- **Key wired, as in the kit:** all key wires go into one 2 × 8 field of 1.27 mm solder holes (J4, same order as a later
  FFC). J4 is not assembled. J1 is a JST PH plug that JLCPCB solders (through-hole): the 5 V lead plugs in.

**Ordering** (the owner orders; nothing is uploaded from here):
1. jlcpcb.com → upload `output/jlcpcb/roomkey-hub_gerbers.zip` (4 layers, 1.6 mm), quantity 10, ENIG or HASL lead-free.
2. PCB Assembly on → **Standard** → **assembly side: bottom** → 7 boards → "Confirm parts placement": yes. If JLCPCB
   wants edge rails or tooling holes, accept them on the rails (not in the board).
3. Upload `roomkey-hub_bom.csv` and `roomkey-hub_cpl.csv`.
4. **Placement preview — send screenshots before paying.** Every part must sit on its pads, and every polarised part
   with pin 1 on its pin-1 pad: U1, U2, U3, U4, U7, Q1, D2, D3, D4, D5, J1, J2, J5, J9, SW1, SW2. Rotate in the preview
   where needed. The CPL already mirrors bottom-side rotations (`180 − rot`) and places the MX sockets by their body
   centre, but package zero orientations differ between KiCad's and JLCPCB's libraries, so this check is mandatory.

**Independent review, 2026-10-08** (read-only agent, every IC pin by pin against the data sheet, every LCSC number
against its footprint, strapping, JLCPCB rules): **no wrong pin, part or value found.** Fixed after it: Standard PCBA
for the mic; CPL bottom rotations and MX socket positions; BOM without "C11-C13" ranges; J4 moved clear of MX1's
housing (solder fillets under a switch that sits flat on the board). Notes kept:
- With J1 powered, the touch board's USB-C VBUS carries ≈ 4.7 V (the board has no diode there). To flash over USB,
  unplug the supply; never plug into a switched-off PC while J1 has power.
- On the touch board, the IMU's interrupt outputs share IO5 (radar RX) and IO6 (bottom key) — as in the kit. The
  firmware must keep the QMI8658 interrupts disabled.

## Hub layout

- **Where:** directly behind the switch plate, front face at d 20.3 (MX housing bottom); 1.6 mm, **4 layers**: F.Cu
  signals, In1 GND plane, In2 +5V plane, B.Cu parts + signals. All parts on the back (single-sided assembly). The
  front is bare except the switch holes.
- **Outline, rev D** (kit CAD, `hardware/cad/insert_params.py`, branch `kit-pcb`, plug-in housing v0.4, 64 × 64):
  square ±28.0 (0.45 to the lid's side walls) minus
  - the housing's corner columns: a circle r 3.9 round (±26.8, ±26.8) and everything beyond it toward the corner
    (column r 3.2 + 0.5 air + 0.2 for the router's tolerance);
  - the speaker + cradle (x ≥ 14.3 for |y| ≤ 17.2);
  - the radar window (x ≤ −7.86, y −18.4…6.2, open to the left edge): the LD2410C now sits **in** the hub plane, its
    antenna face flush with the board's front, in a printed cage;
  - a bottom notch (x −4.3…9.84, up to y −25.87) that the humidity sensor and its lead pass.

  A slot 12.8 × 2.6 at y 1.5 takes the key wires. M2 screws at (−13.2, 20), (13.2, 20), (10.5, −7.9); a plain support
  post at (13.2, 4). The window's inner corners come out rounded (r ≈ 0.5, the router bit).
- **Fixed by the CAD:** mic port at (−20.16, 9.6); J4 centred at (0, 6.35), both rows below MX1's housing (y < 8.0) and
  inside the wire loop's zone (x ±7, y 0.2–11; only flat passives ≤ 1.3 mm under the loop); radar plug J5 at
  (−13.5, 10.5), body y 7…14, its wires soldered to the radar's header pins (cut to 2 mm, x −22.7); speaker plug J2
  at its rev C place (11.5, 12.5); 5 V plug J1 (side entry): pins at x 12.75 (pin 2 = +5 V at y −1.5, pin 1 = GND
  at y −3.5), body x 6.5…14.1, y −5.45…0.45, 0.45 mm above the head of H3's M2 screw and 0.5 mm left of the
  speaker foam. Its mouth faces the axis: the lead comes from the USB plug's solder cups (x −3.3 / 3.7, y −5.35)
  through a lane kept free of parts (x −4.5…6.5, y −6.0…−0.5). The mouth faces −x and not down because the plug would
  have to slide in over H3's screw head. Through-hole pins stay outside both MX housings (`gen_layout_hub.py` checks
  that no through-hole joint lies under a 14 × 14 housing). **Clip J1's two pin tails on the front to ≤ 1.0 mm**
  (side cutter): wave-soldered tails can be longer, and the front is only 2.5 mm from the switch plate. The input
  protection (D1, Q1, U1 …) sits below J1's lane, between it and MX2's socket; glow LED holes J8 at x 15.3, y −19.2…−21.8 (just outside the collar seat wall / switch-plate ledge, so the wires
  enter straight): the LEDs sit in FRONT of the hub
  (d 12.6–15.4), so their wires come from the bottom-right LED (12.5, −22.47) through the switch-plate notch into the
  3.5 mm gap in front of the hub and into these holes (a plug on the back could not be reached; an SH plug on the
  front is 4.25 tall).
- **Rules:** tracks 0.15 / gaps 0.125 mm (JLCPCB 4-layer allows 0.09), supply and speaker 0.3, vias 0.6/0.3, copper
  ≥ 0.3 mm from the edge. `hub/roomkey-hub.kicad_dru` has one rule: J1's and H3's courtyards may overlap (the stock
  mounting-hole courtyard is bigger than the M2 head; J1's body stays 0.45 mm clear of it). DRC leaves two silkscreen
  warnings: J1's outline touches the slot's end, and the board house clips it there.

**Soldering the wires** — map: `output/roomkey-hub_soldering-map.png` (seen from the back, holes at their real
positions). Touch board pad (silkscreen name) → hub hole:

| Touch pad | Hub hole | | Touch pad | Hub hole |
|---|---|---|---|---|
| VBUS | J4-1 (J4-2 spare) | | SDA | J4-9 |
| GND (×3) | J4-3, J4-11, J4-14 | | SCL | J4-10 |
| 9 (key top) | J4-4 | | TXD | J4-12 |
| 6 (key bottom) | J4-5 | | 7 | J4-13 |
| 4 (LED data) | J4-6 | | 8 | J4-15 |
| 5 | J4-7 | | RXD | J4-16 |
| 3 | J4-8 | | 5 V lead + / − | J1 plug pin 2 / pin 1 (plugs in, no soldering) |
| glow LED chain: data (DIN of the BR LED) | J8-3 | | glow LED chain: +5 V / GND | J8-2 / J8-1 |

The square hole is J4-1. Never connect the touch board's 3V3, VBAT, RST, IO1, IO2, IO12, IO13 pads.

The 5 V lead: solder it to the USB-A plug (VBUS = +5 V, GND) and crimp or buy it with a JST PHR-2 housing so that
+5 V lands on J1's pin 2 — the contact toward the board's top edge (toward the amplifier) when the hub is upright.
The plug only fits one way round; check the wire colours against the soldering map before the first power-up.

## Open points

Only the owner can check (part in hand):
- [x] LD2410C pin order (J5): TX, RX, OUT, GND, VCC — owner's photo, 2026-10-08.
- [ ] Speaker plug (J2): 2-pin 1.25 mm ("PH1.25 2P", owner); the CJT A1251WV-S-2P is a PicoBlade-size part — check
      the fit when the boards arrive.

Design / later boards:
- [ ] Sensor tail layout, after hub rev D. The CAD's frame (2026-10-31): flat in the lid G2's bottom wall, parts facing
      down (−y) to the vents; ≤ 13.4 (x) × 10.5 (depth) × 2.6 overall, board x −3.9…9.44, d 9.6…20.1, parts only in
      x −2.9…8.44 (the 1 mm ends rest on G2's wall); SHT40 over the vents at x 3.3, VEML6030 over the light window at
      x −1.0 (both d 13.35); solder pads for the 4 wires at the back edge (d ≈ 18.5), on the top (+y).
- [x] Glow LEDs stay **hand-wired, no LED board** (owner, 2026-10-12). A closed ring does not fit (CAD 2026-10-09);
      4 corner boards were laid out and dropped: they don't save any soldering (4 wires per LED either way) and
      the 0.6 mm board forces JLCPCB's Standard assembly (≈ €45–60). Chain BR → TR → TL → BL from J8 (CAD thread,
      both builds). Don't resurface.
- [ ] Pogo adapter + FFC (replaces the key wires in a later order).
- [ ] Firmware (later): VEML6030 via the `veml7700` platform and SHT4x once the sensor tail exists; nothing else changes.

Parts considered and not used: PTC fuse (the eFuse does more), SPH0645 mic (non-standard I²S → firmware change),
OPT3001 (0x44 = SHT clash), TCA9534 I/O expander and plate input (no plate button, owner 2026-10-08).

## Sources

- Pins: `docs/wiring-touch-board.md`, `esphome/packages/board_c6_touch_lcd_147.yaml`, Waveshare
  ESP32-C6-Touch-LCD-1.47 schematic
- TPS25200 (TI SLVSCJ0F: pinout, ILIM, EN ≥ 300 k, OVP 7.4.3/7.4.4), TPS7A20, MAX98357A (SD_MODE table, standby),
  ICS-43434 (TDK DS-000069), SN74AHCT1G125, AO3401A, PMEG3020EH, BAT54C — maker data sheets
- JLCPCB part pages (PCBA type per part), JLCPCB assembly price article, KiBot notes on JLCPCB bottom rotation
- LD2410C: Hi-Link serial protocol document, table 1
