# Hardware

Parametric FreeCAD scripts, the same method as [Klingelbox](https://github.com/aikos-home/intercom):
one file holds every dimension, generators read it, `validate()` checks the fit before anything is
printed. Licence: [CERN-OHL-P-2.0](../LICENSES/CERN-OHL-P-2.0.txt).

| File | What |
|---|---|
| [`cad/roomkey_params.py`](cad/roomkey_params.py) | every dimension, tagged [DS] datasheet · [MEAS] measured · [FREE] design choice · [TBD] placeholder; `python3 cad/roomkey_params.py` runs the fit check |
| [`cad/make_coupon_v0.py`](cad/make_coupon_v0.py) | tolerance coupon — print this first |
| [`cad/insert_params.py`](cad/insert_params.py) | **wall insert v0.5 (draft)**: box, frame, both variants, installation topologies; `python3 cad/insert_params.py` validates L and S |
| [`cad/insert_lib.py`](cad/insert_lib.py), [`make_key_module.py`](cad/make_key_module.py), [`make_insert_L.py`](cad/make_insert_L.py), [`make_insert_S.py`](cad/make_insert_S.py) | FreeCAD generators + collision/clearance checks (rest, key pressed and wobbled with its stems, plate pressed at five points) |
| [`docs/insert-design.md`](docs/insert-design.md) | **design of the wall insert (v0.5 DRAFT)**: concept, stack-up, installation topologies (electrician), BOM, printing, open questions, risks |
| [`drawings/`](drawings/) | to-scale front views and sections cut from the CAD solids (`tools/insert_drawings.py`) |
| [`reviews/insert-v0-review-log.md`](reviews/insert-v0-review-log.md) | pre-mortems, independent adversarial reviews, scores, resolutions |
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

## Wall insert v0.5 (DRAFT / WIP, 2026-10-01)

**AI-assisted draft — nothing built, nothing certified, not approved for mains. All 230 V work only by a
qualified electrician of a registered installation company (NAV §13).** Two variants of the in-wall part with the same printed parts, key module and look —
see [docs/insert-design.md](docs/insert-design.md):

* **The insert is SELV-only (12 V in).** No 230 V, no power supply, no relay in the RoomKey chamber; the
  230 V side is certified devices placed by the electrician (where the switch leg ends, behind the partition of a
  two-chamber box, or in the distribution board — decision procedure in the design doc §9). At the common 2-core
  switch leg this usually means a new cable.
* **Variant L — light-switch replacement.** The ivory plate floats on four SMD tactile switches (B3FS) and is a
  push-button: 12 V SELV pulse → certified impulse relay → the light works without Wi-Fi, HA or ESP (and with any
  fault behind the hub's eFuse; FMEA in the design doc §8.2). The glow lights the gap around the key and a
  translucent rim of the plate.
* **Variant S — socket replacement.** Same parts; the plate goes to the ESP only; the socket at that
  position is lost; only sensible at a usable height.

Status: **WIP — the adversarial review gate was NOT passed** (4 rounds, scores ≈ 7/10; the remaining MAJOR items need
real parts, a desk rig and measurements — see the review log). CAD closes in all checked states (0 collisions at rest, key pressed, key + stems wobbled ±1.5°,
plate pressed at five points to the nominal and worst-case stop), `validate()` 0 errors, wall check passes. Blocked on
measurements (rocker-to-wall distance ≥ 8.9 mm, frame retention, box interior, conductors behind 5 WAGOs — plan with a
47 mm box), desk-rig tests (key end presses, touch vs key, glow look, mic path, start-up, relay drive at reset) and six
questions to Eltako — list in the design doc §10 and §13. Print
[`make_coupon_v1.py`](cad/make_coupon_v1.py) (switch seat and snap tongues, stem posts, perforation, colour) and the
key shell + switch plate for the end-press test before any other real part.

| More files | |
|---|---|
| [`cad/make_coupon_v1.py`](cad/make_coupon_v1.py) | coupon v1 for the insert mechanics (rows D, E, F, H) |
| [`../tools/insert_drawings.py`](../tools/insert_drawings.py), [`../tools/insert_wallcheck.py`](../tools/insert_wallcheck.py) | drawings and minimum-wall check (any python with numpy + matplotlib, e.g. FreeCAD's bundled one) |

![Variant L front](drawings/insert-L_front.png)

## Plan

1. **Coupon v0** — fits for this printer (now)
2. **Desk rig v0** — 55 × 55 rocker face, touch board as the key on two identical MX switches wired in
   parallel (end-press test first, design doc §10), a switch under the rocker as the room-light stand-in (logs only, no mains), speaker on
   its edge with a sound duct, mic, amp, glow LEDs, USB power
3. **Wall fit v1** — same parts inside the real limits (Ø58 box, depth) + a printed dummy flush box
4. **Mounting v2** — screw holes at 60 mm; supply and relay stay outside the RoomKey chamber (SELV-only
   insert) — then the electrician (the v0.5 insert draft models this: [docs/insert-design.md](docs/insert-design.md))
