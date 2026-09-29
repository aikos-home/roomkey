# Hardware

Parametric FreeCAD scripts, the same method as [Klingelbox](https://github.com/martinkadauke/intercom):
one file holds every dimension, generators read it, `validate()` checks the fit before anything is
printed. Licence: [CERN-OHL-P-2.0](../LICENSES/CERN-OHL-P-2.0.txt).

| File | What |
|---|---|
| [`cad/roomkey_params.py`](cad/roomkey_params.py) | every dimension, tagged [DS] datasheet · [MEAS] measured · [FREE] design choice · [TBD] placeholder; `python3 cad/roomkey_params.py` runs the fit check |
| [`cad/make_coupon_v0.py`](cad/make_coupon_v0.py) | tolerance coupon — print this first |
| `models/*_print.stl` | ready to slice · `models/*.step` for editing |

Generate (headless, from the repo root):

```bash
PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_coupon_v0.py', encoding='utf-8').read())"
```

## Coupon v0 — find the fits first

Print flat, PLA, 0.2 mm layers, no supports (≈ 10 min, 9 g). Dots = variant, 1 dot = left.

| Row | Test | Variants (1 / 2 / 3 dots) | Pick |
|---|---|---|---|
| A (switch cut-outs) | press a key switch into the 1.5 mm plate | 13.9 / 14.0 / 14.1 mm | clicks in firmly, no wobble |
| B (mic seats) | drop the INMP441 in | Ø 13.25 / 13.35 / 13.45 mm | goes in without force, doesn't fall out |
| C (stem sockets) | press onto a switch stem | 4.05×1.25 / 4.10×1.30 / 4.15×1.35 mm | snug, no cracking |

The winners go into `roomkey_params.py` as [MEAS]. Repeat in ABS/PETG before the final parts —
they shrink differently.

## Plan

1. **Coupon v0** — fits for this printer (now)
2. **Desk rig v0** — 55 × 55 rocker face, touch board as the key on two switches (one wired, one
   as guide), a switch under the rocker as the room-light stand-in (logs only, no mains), speaker on
   its edge with a sound duct, mic, amp, glow LEDs, USB power
3. **Wall fit v1** — same parts inside the real limits (Ø58 box, depth) + a printed dummy flush box
4. **Mounting v2** — screw holes at 60 mm, room for supply and relay — then the electrician
