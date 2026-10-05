# RoomKey Touch — wiring (prototype)

Every wire from the board to each part of the RoomKey Touch prototype: microphone, amplifier and speaker, sensors, keys and
glow ring. It is checked against the firmware (`esphome/roomkey_touch.yaml` and its packages, `main` 2026-10-05).

Scope: **prototype on the bench and the desk replica** ("table A" in the insert's file, `features/roomkey-einsatz.md` §4).
The wall insert v1 differs: IO3 and IO5 go to the plate and the relay there, and the radar has no place yet.

**SELV only:** 5 V from USB-C. Nothing here ever touches 230 V.

## The board: Waveshare ESP32-C6-Touch-LCD-1.47

Header H1: 2 × 11 bare pads, 2.54 mm pitch. The silkscreen names the pads by GPIO number. The view is from the **back**
(components side), USB-C at the top. **From the front (display side) the two columns are mirrored.**

```
                 USB-C
     left column          right column
   VBUS  ● H1-1      H1-2  ●  VBAT   (not used: no battery in aikos)
   GND   ● H1-3      H1-4  ●  GND
   TXD   ● H1-5      H1-6  ●  GND
   RXD   ● H1-7      H1-8  ●  3V3
   RST   ● H1-9      H1-10 ●  SCL
   1     ● H1-11     H1-12 ●  SDA
   2     ● H1-13     H1-14 ●  13     (USB D+, don't use)
   3     ● H1-15     H1-16 ●  12     (USB D−, don't use)
   4     ● H1-17     H1-18 ●  9      (BOOT)
   5     ● H1-19     H1-20 ●  8
   6     ● H1-21     H1-22 ●  7
```

| Pad (silkscreen) | H1 | GPIO | Used for |
|---|---|---|---|
| VBUS | 1 | — | **5 V** (from USB-C): amplifier, radar, LEDs |
| GND | 3, 4, 6 | — | ground for every part |
| TXD | 5 | GPIO16 | I²S data **out** → amplifier DIN |
| RXD | 7 | GPIO17 | I²S data **in** ← microphone SD |
| 3V3 | 8 | — | **3.3 V** (on-board regulator, 800 mA): microphone, SHT31-D, VEML7700 |
| SCL | 10 | GPIO19 | I²C clock: SHT31-D, VEML7700 (shared with the board's touch and IMU) |
| SDA | 12 | GPIO18 | I²C data: SHT31-D, VEML7700 (shared with the board's touch and IMU) |
| 3 | 15 | GPIO3 | radar TX → ESP (UART RX) |
| 4 | 17 | GPIO4 | glow ring data → first LED's DIN |
| 5 | 19 | GPIO5 | ESP (UART TX) → radar RX |
| 6 | 21 | GPIO6 | key bottom (MX 2) |
| 7 | 22 | GPIO7 | I²S bit clock (BCLK/SCK): microphone **and** amplifier |
| 8 | 20 | GPIO8 | I²S word select (WS/LRC): microphone **and** amplifier |
| 9 | 18 | GPIO9 | key top (MX 1); also the board's BOOT button |
| RST, 1, 2, 12, 13, VBAT | 9, 11, 13, 16, 14, 2 | — | **don't connect**: reset, display bus, USB, battery |

## Every wire, by part

### Microphone INMP441 (I²S)
| INMP441 | → board pad | Note |
|---|---|---|
| VDD | 3V3 | **3.3 V only** |
| GND | GND | |
| L/R | GND | left channel (the firmware reads the left slot) |
| SCK | 7 | shared with the amplifier's BCLK |
| WS | 8 | shared with the amplifier's LRC |
| SD | RXD | |

### Amplifier MAX98357A (I²S) and speaker
| MAX98357A | → board pad | Note |
|---|---|---|
| VIN | VBUS | 5 V |
| GND | GND | |
| BCLK | 7 | shared with the microphone's SCK |
| LRC | 8 | shared with the microphone's WS |
| DIN | TXD | |
| GAIN | — | leave open (9 dB) |
| SD | — | leave open |
| OUT + / OUT − | speaker + / − | 8 Ω, never to ground |

Microphone and amplifier share one I²S bus, so the key works half-duplex: the speaker stops while you hold the key.

### Temperature and humidity SHT31-D (I²C, address 0x44)
| SHT31-D | → board pad | Note |
|---|---|---|
| VIN | 3V3 | |
| GND | GND | |
| SCL | SCL | |
| SDA | SDA | |
| ADR | — | open = 0x44 |
| ALR | — | open |

Place it in room air, away from the ESP and the amplifier, which heat up.

### Light VEML7700 (I²C, address 0x10) — optional
| VEML7700 | → board pad | Note |
|---|---|---|
| VIN | 3V3 | |
| GND | GND | |
| SCL | SCL | |
| SDA | SDA | |
| 3Vo | — | don't use |

It needs a window to the room.

### Presence radar HLK-LD2410C (UART 256000 baud)
| LD2410C | → board pad | Note |
|---|---|---|
| VCC | VBUS | **5 V** |
| GND | GND | |
| TX | 3 | radar sends, ESP receives |
| RX | 5 | ESP sends, radar receives |
| OUT | — | not used (the firmware reads the UART) |

It looks through plastic, but not through metal.

### Keys: two MX switches (the rocker, read separately)
| Switch | Leg 1 → pad | Leg 2 → pad | In HA |
|---|---|---|---|
| top (KEY1) | 9 | GND | "Key top" |
| bottom (KEY2) | 6 | GND | "Key bottom" |

Don't wire them in parallel. Holding the top key while power comes on starts the board in download mode: release it and
power-cycle.

### Glow ring: 4 × WS2812B-MINI 3535 (one chain)
| From | → to | Note |
|---|---|---|
| pad 4 | LED 1 DIN | data, 3.3 V level |
| LED 1 DOUT | LED 2 DIN | the chain continues: LED 2 → 3 → 4 |
| VBUS | VDD of every LED | 5 V |
| GND | GND of every LED | |

The chain order is bottom right → top right → top left → bottom left. The firmware drives 4 × WS2812 with GRB colour
order on GPIO4.

3.3 V data into LEDs that run on 5 V is at the edge of their spec, though it usually works on a short wire. If the first
LED flickers, add a level shifter (74AHCT1G125), or feed that LED's VDD through a diode (about 4.3 V).

## Shared lines at a glance

| Line | Pad | Goes to |
|---|---|---|
| 5 V | VBUS | amplifier VIN, radar VCC, LED VDD |
| 3.3 V | 3V3 | microphone VDD, SHT31-D VIN, VEML7700 VIN |
| GND | GND (3 pads) | every part, the microphone's L/R, both keys |
| I²C | SCL, SDA | SHT31-D (0x44), VEML7700 (0x10); on the board: touch 0x63, IMU 0x6B |
| I²S clock | 7 | microphone SCK, amplifier BCLK |
| I²S word select | 8 | microphone WS, amplifier LRC |

Where several parts share a pad, use a small breadboard as a hub on the bench, or solder two thin wires into the same hole.
The insert design specifies AWG 30 fine-stranded silicone wire.

## Rules
- Unplug USB before you solder or re-plug anything.
- **Never connect 5 V (VBUS) to a 3.3 V part:** microphone, SHT31-D, VEML7700.
- After a flash, leave the board powered for one minute. Otherwise ESPHome rolls back to the previous firmware.

## Where this lives in the firmware
- Pins: `esphome/packages/board_c6_touch_lcd_147.yaml` (substitutions `i2s_*`, `radar_*`, I²C, keys, glow ring)
- Microphone: `roomkey_mic.yaml` + `roomkey_voice_mic.yaml` (gain in HA: "Mic gain")
- Amplifier: `roomkey_voice_speaker.yaml`
- Sensors: `roomkey_sensors.yaml`
- Device: `esphome/roomkey_touch.yaml`
