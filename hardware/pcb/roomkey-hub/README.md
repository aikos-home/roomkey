# RoomKey hub PCB set — schematics (draft A)

Four small boards replace the kit's loose breakouts and hand wiring. **Status: schematic draft for review. No layout,
nothing ordered.** Decisions so far: owner, 2026-10-08.

| Board | Folder | Where it sits | What it carries |
|---|---|---|---|
| **Hub** | `hub/` | static, directly behind the switch plate; the two MX switches plug into it | 5 V input + protection, MX hot-swap sockets, amplifier, I²S mic, light sensor, I/O expander, 3.3 V regulator, connectors |
| **SHT tail** | `sht-tail/` | the frame's bottom border, in room air | SHT40 temperature/humidity sensor on a 4-pin plug-in cable |
| **Pogo adapter** | `pogo/` | on the touch board, moves with the key | 15 spring pins on the bare H1 pads → 16-pin FFC to the hub |
| **Glow ring** | `glow-ring/` | thin frame around the key collar, where the kit's LED carriers sit | 4 × WS2812B-Mini, one 100 nF each, 3-pin cable to the hub's J8 (owner chose assembled LEDs, 2026-10-08) |

**Why four KiCad projects:** KiCad has one PCB per project, and these are four separate PCBs (different size,
maybe different thickness). The one thing they share, the FFC conductor order between hub and pogo adapter, is defined
once in `gen_schematics.py` (`FFC_PINS`) and written into both schematics, so the two ends cannot drift apart.

**Power (Variant S, decided 2026-10-08):** only 5 V SELV reaches RoomKey, from a certified 230 V → 5 V supply in the
neighbouring flush box. **No board here ever carries 230 V.**

## Files

- `gen_schematics.py` — the source while drafting: parts, values, part numbers, nets, positions. It writes the three
  `.kicad_sch` files and `lib/roomkey.kicad_sym`, and checks that no texts overlap, no two nets touch and every named
  net reaches at least two pins. Once the layout starts, the KiCad files become the source.
- `hub/`, `sht-tail/`, `pogo/`, `glow-ring/` — KiCad 10 projects.
- `lib/roomkey.kicad_sym` — symbols KiCad does not ship: TPS25200, VEML6030, and the MAX98357A with its exposed pad as
  a passive pin. `lib/roomkey.pretty` — footprints KiCad does not ship: VEML6030 (data-sheet land pattern), Mill-Max
  0900 spring pin, Kailh MX hot-swap socket (placed flipped on the bottom).
- `output/*.pdf` — the schematics to read; `output/*-bom.csv` — grouped BOMs (MPN + maker for every part).

Regenerate and check:

```bash
"C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/gen_schematics.py
"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe" sch erc hardware/pcb/roomkey-hub/hub/roomkey-hub.kicad_sch
```

## What the hub does, block by block

1. **Power.** Push-in terminal (Phoenix PTSM 0,5, 0.14–0.5 mm²) → bidirectional TVS (ESD/surge) → P-FET Q1 (reverse
   polarity, ~50 mΩ) → eFuse TPS25200 (current limit 1.5 A typ via R2 = 64.9 k; output clamp 5.25–5.55 V if a 12 V
   supply is connected by mistake, IN rated to 20 V; soft start; thermal cut-out with auto-retry) → **+5V node** (TVS,
   470 µF polymer) for the amplifier, radar and glow ring. +5V → Schottky D4 → **VBUS_KEY** → FFC → the touch board's
   VBUS. The touch board's USB-C stays usable: D4 keeps USB power out of the hub. The 3.3 V regulator (mic, light sensor,
   expander, SHT) is fed from either side through the dual diode D5, so the I²C bus and the IO8 pull-up are live
   whenever the key has power (a dead 3.3 V rail would clamp the shared I²C bus and block touch).
2. **Audio.** MAX98357A as on the kit's breakout (1 MΩ on SD_MODE = mono mix, gain 9 dB) + an I²S MEMS mic on the same
   bus (half duplex, as today). New: Q2 lets the expander switch the amplifier hard off; untouched, the amp behaves
   exactly like the breakout. IO8 (I²S WS) has its 10 k pull-up for the strapping.
3. **I²C.** VEML6030 light sensor (0x10) and TCA9534 I/O expander (0x20; ESPHome `pca9554`). The expander exists because
   the plate must stay a push-button and both MX keys stay separate (owner, 2026-10-08), and no ESP pin is left. Its pins:
   P0 plate, P1 amp mute, P2 radar OUT, P3 eFuse fault, P4–P7 spare (DNP pads J3). No free ESP pin for its INT → polled.
4. **Switches and connectors.** The two MX switches plug straight into Kailh hot-swap sockets on the hub (owner,
   2026-10-08; IO9 top, IO6 bottom), so the hub sits directly behind the switch plate, keyboard style. FFC to the key;
   radar on a cable (owner: its position matters, so it stays free; order = the module's silkscreen TX, RX, OUT, GND,
   VCC, confirmed by photo); plate, glow ring (3.3 → 5 V buffer + 330 Ω), speaker (4-pin 1.25 mm, fits the owner's speaker pair), SHT tail
   (Qwiic/STEMMA QT pinout, so a ready-made JST SH cable fits).

I²C addresses: VEML6030 0x10, TCA9534 0x20, SHT40 0x44, touch 0x63, IMU 0x6B — no clashes.

**Pogo adapter:** 15 Mill-Max 0900 SMT spring pins (one part each, so the assembly BOM counts 15) on the used H1 pads.
Seen from the pin side, the odd H1 pads are on the **right**: the adapter faces the board's back, so its layout is the
mirror of the board-back view in `docs/wiring-touch-board.md`.

**FFC:** Hirose FH12-16S-0.5SH(55) at both ends (bottom contact, 0.5 A per contact; VBUS and GND use 2 and 3
conductors). Cable for a straight run: same-side contacts, e.g. Molex 15166-0167 (102 mm) or Würth 687616100002
(100 mm); a U-turn needs opposite-side contacts and `FFC_MIRROR`. Checked: all 16 conductors carry the same net at
both ends (netlist compare).

## First order (owner, 2026-10-08): 7 hubs at JLCPCB, key wired

- **JLCPCB, not PCBWay** (PCBWay's per-design setup made a first run ≈ €650). Order: 10 bare hubs, **7 assembled**.
  Every assembled part has an LCSC number (field `LCSC`); passives are JLCPCB "basic" parts, 19 lines are "extended"
  (≈ $3 loading fee each). Rough total ≈ €150–210 incl. shipping and VAT — the exact figure from JLCPCB's quote.
- **Only the hub** in this order. The kit's LED carriers and SHT31 plug into the hub's connectors; the sensor tail,
  LED ring and pogo/flex link stay drafted for later.
- **Key wired, as in the kit:** the FFC socket became a 2 × 8 field of 1.27 mm solder holes (J4, same order as a later
  FFC) plus one extra hole J10 for the bottom-key wire (its place in the field could not be routed). The 5 V input is two
  solder holes for a 0.5 mm² pigtail (J1). Nothing on these is assembled.
- Changed for stock/cost: C2 = 100 µF X5R 1206 (basic), R17 = 1 MΩ (basic; ≥ 300 k needed), speaker plug CJT
  A1251WV-S-2P (PicoBlade 53398 equivalent), MX socket CPG151101S11-2 (the Kailh original is out of stock) —
  **check both footprints in JLCPCB's assembly preview.**

## Hub layout

**Status 2026-10-08: routed, KiCad DRC with schematic parity 0 violations / 0 unconnected / 0 footprint errors.**
Order files in `output/jlcpcb/` (Gerber + drill zip, `roomkey-hub_bom.csv`, `roomkey-hub_cpl.csv`); pictures
`output/roomkey-hub_back_3d.png`, `_front_3d.png`, `_placement_front-view.png`; `output/roomkey-hub.step` for the kit.
Freerouting is randomised, so `hub/roomkey-hub.kicad_pcb` is the artifact: a rerun gives a different routing.
Two key wires got their own holes because their place in the 2 × 8 field could not be routed: **J10 = bottom key
(IO6)**, **J11 = LED data (IO4)**; J4 positions 5 and 6 stay empty. `add_wire_hole.py` places such a hole on its
net's routed copper.

**Ordering at JLCPCB** (the owner orders; nothing uploaded from here):
1. jlcpcb.com → upload `roomkey-hub_gerbers.zip` (4 layers, 1.6 mm detected), quantity 10, surface finish ENIG or
   HASL lead-free.
2. PCB Assembly on → Economic → **assembly side: bottom** → 7 boards → "Confirm parts placement": yes.
3. Upload `roomkey-hub_bom.csv` and `roomkey-hub_cpl.csv`; in the placement preview check every part sits on its
   pads, rotation included (parts are on the bottom; the speaker plug C225104 and the MX sockets C49352235 are
   stand-ins for the drawn footprints). If JLCPCB wants tooling holes, they go on added edge rails, not into the board.


Scripts (run in this order; KiCad's Python):
1. `gen_schematics.py` — schematics + project library.
2. `gen_layout_hub.py` — outline from the kit CAD and placement (all parts on the back).
3. `route_hub.py` — GND/+5V fan-out vias, Freerouting (Java 25 + freerouting-2.5.0.jar in `~/tools` (or `$ROOMKEY_TOOLS`),
   downloaded with the owner's OK), keeps the best round, GND pours. Freerouting is randomised (`FR_ARGS=-is random`).
4. `complete_route.py` — rip-up-and-reroute where it helps, then closes leftovers on F.Cu/B.Cu by grid search.
5. `export_jlc.py` — Gerbers + drill zip, BOM and CPL in JLCPCB's format into `output/jlcpcb/`.
6. `add_wire_hole.py` — a single wire hole onto its net's routed copper; `soldering_map.py` — the map.

- **Where:** directly behind the switch plate, front face at d 20.3 (MX housing bottom = plate top 15.3 + 5.0);
  the two MX switches plug into hot-swap sockets on its back. 1.6 mm, **4 layers**: F.Cu signals, In1 GND plane,
  In2 +5V plane, B.Cu parts + signals. All parts on the back (single-sided assembly).
- **Outline:** circle r 28 (box inside Ø58 [TBD Q5] − 1 mm) minus the speaker + cradle (x ≥ 14.3 for |y| ≤ 17.2), the
  radar's view (x ≤ −8.0, y −16.1…2.1 — the radar stays behind the hub on its cable), the screw domes (|x| ≥ 26 for
  |y| ≤ 4.5); slot 12.8 × 2.6 at y 1.5 for the key wires (the kit's CABLE_SLOT).
- **Rules:** tracks 0.15 / gaps 0.125 mm (JLCPCB 4-layer allows 0.09), supply and speaker 0.3, vias 0.6/0.3, copper
  ≥ 0.3 mm from the edge.
- The middle of the board is narrow (radar window left, speaker right, wire slot centre): the parts are grouped so few
  lines cross it — key-wire holes, amplifier, mic, radar plug, power and expander in the top half; plate, LED ring and
  SHT plugs at the bottom.

**Soldering the wires** — map: `output/roomkey-hub_soldering-map.png` (from `soldering_map.py`, seen from the back,
holes at their real positions). Touch board pad (silkscreen name) → hub hole:

| Touch pad | Hub hole | | Touch pad | Hub hole |
|---|---|---|---|---|
| VBUS | J4-1 (J4-2 spare) | | SDA | J4-9 |
| GND (×3) | J4-3, J4-11, J4-14 | | SCL | J4-10 |
| 9 (key top) | J4-4 | | TXD | J4-12 |
| 5 | J4-7 | | 7 | J4-13 |
| 3 | J4-8 | | 8 | J4-15 |
| 6 (key bottom) | **J10** | | RXD | J4-16 |
| 4 (LED data) | **J11** | | 5 V supply + / − | J1 (red / black) |

J4-5 and J4-6 stay empty; the square hole is J4-1.

**Kit CAD changes the hub needs** (for the CAD session; nothing changed in `hardware/cad` here):
1. Remove the back carrier; the hub takes its place, 5 mm further forward (d 20.3–21.9, parts on the back to ≈ d 27).
2. Hub posts end at d 20.3: (−13.2, 20), (13.2, 20) with M2 pilot holes; (13.2, 4) as a plain support; (−13.2, 4) sits
   in the radar window (may go).
3. Anchor bar removed; anchor post (10.5, −7.9) ends at d 20.3 with an M2 pilot hole; (−10.5, −7.9) removed.
4. Mic holder ring removed; the sound tube runs from the plate hole straight to the hub's front face at d 20.3 with a
   foam seal around the PCB's port hole (the ICS-43434 sits on the back, bottom port through the board).
5. **Key wires:** through the key back and switch plate slots (as today), through the hub slot (y 1.5); the rolling loop
   behind the hub now turns **upward** (+y): its fixed leg comes back to the solder holes J4 at y ≈ 7.8 (and J10).
6. Radar stays behind the hub at the kit spot (d 28.3+), cable to J5 at the window's top edge.
7. LED ring board and sensor tail outlines (later orders): from the collar region (d 12.6–15.4) and the frame's
   bottom border.

## Open points [TBD]

Only the owner can check (part in hand):
- [x] **LD2410C pin order (J5):** TX, RX, OUT, GND, VCC — owner's photo of the silkscreen, 2026-10-08.
- [ ] **Speaker plug (J2).** Waveshare calls it "PH1.25"; drawn as Molex PicoBlade 4-pin, 1 A+, 2 A−, 3 B−, 4 B+
      (read from a photo). Check the housing and the pinout by continuity.
- [ ] **5 V feed wire size** (terminal takes 0.14–0.5 mm²; WAGO 2060-452/998-404 if the electrician wants 0.75 mm²).

Design / sourcing:
- [ ] Mic: ICS-43434 is **obsolete** but stocked (Digi-Key ~90 k). Alternative MEMSensing MSM261S3526Z0CM (same size,
      standard I²S, other pinout, stock unconfirmed). Any other part must stay standard I²S, else the firmware changes.
- [ ] Stock not confirmed: KEMET T598X477M010ATE025 (C2), Phoenix 1814702 (J1), MSM261S3526Z0CM.
- [ ] Pogo pins: Mill-Max 0900-0-15-20-76-14-11-0 (working height 3.0 mm, ~0.6 N each → ~9 N for 15): tip shape,
      height vs. the stack, how the adapter is clamped to the board; pad Ø2.0 vs. Mill-Max's recommended land.
- [ ] FFC cable type and length from the CAD (straight → same-side; U-turn → opposite-side + `FFC_MIRROR`).
- [ ] Hub outline (layout): fills the box behind the switch plate around the two sockets; cut-out for the speaker
      (x 15.4–20.9 down to d 25.6); a window if the radar sits behind the hub (it cannot see through copper).
- [ ] Hot-swap socket pads: check against the Kailh CPG151101S11 drawing; the owner's MX are 3-pin (plate mount), so
      the printed switch plate stays.
- [x] Glow ring LEDs: an assembled ring board (owner, 2026-10-08). [ ] Its outline and LED positions from the CAD;
      WS2812B-Mini exact suffix / stock.
- [ ] Acoustic path to the hub mic (bottom port → hole in the PCB) and light path to the VEML6030 — both now sit on
      the hub, deep in the box.
- [ ] ESD arrays on the FFC lines: not drawn (all lines stay inside the insert); add if wanted.
- [ ] Firmware (later): `pca9554` expander (plate on P0, mute P1, radar OUT P2, fault P3, P4–P7 as outputs), VEML6030
      via the `veml7700` platform, SHT4x; unchanged pins otherwise.
- [ ] Repo docs still say 12 V / "no light sensor" (insert-design §8.2/§9, README, wiring doc, BUILD.md): update after
      the owner's review.

Parts considered and not used: PTC fuse (Bourns MF-MSMF150-2) — the eFuse does more (OV clamp, soft start);
WAGO 2060 terminal (bigger); SPH0645 mic (non-standard I²S → firmware change); OPT3001 (address 0x44 = SHT clash).

## Sources

- Pins: `docs/wiring-touch-board.md`, `esphome/packages/board_c6_touch_lcd_147.yaml`
- Hub ideas and power: `hardware/docs/insert-design.md` §6, §8.2 (still says 12 V; update after review)
- MAX98357A SD_MODE: internal 100 k pull-down, 1 MΩ to 5 V = (L+R)/2 —
  [Adafruit pinouts](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/pinouts)
- TPS25200: TI data sheet SLVSC71 (pinout DRV, ILIM formula, EN pull-up >= 300 k, clamp 5.25–5.55 V, IN 20 V abs max)
- VEML6030: Vishay data sheet 84366 rev 1.8, p.10 (pinout, land pattern)
- LD2410C: Hi-Link serial protocol document, table 1
- Mill-Max 0900 series, Hirose FH12, Molex Premo-Flex 15166: distributor/maker pages (parts research 2026-10-08)
