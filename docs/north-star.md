# North star (v2, 2026-09-29)

![North star render](north-star.jpg)

*AI-generated concept render (Google Gemini, prompt in `product-render-prompts.md` "Realistic A · portrait key") — not a photo of a built device. Chosen as the design target.
v1 (first render, too-large plate): `north-star-v1.jpg`.*

**Decisions from v2**
- 55 × 55 mm rocker (measured), **portrait key** ≈ 27 × 47 mm → the current portrait UI stays.
- White rocker = side wings (~13 mm) + thin bands; it is the dumb room-light push-button.
- Symmetric perforation strips in both wings: **speaker behind one, mic hidden behind the other**.
- **Glow ring** around the key base = status light. The touch board has no RGB LED → 4 × SK6812-mini
  around the cut-out on IO4 (WIP, in `board_c6_touch_lcd_147.yaml`).
- Speaker must fit behind a ~13 mm wing: rectangular micro-speaker (~11 × 15 mm, phone style) or a
  small cavity module, or a larger speaker deeper in the box with a duct to the wing. (PoC: any speaker.)
- UI safe area: small round-cornered panels clip corners — keep the clock and icons ≥ 10 px from
  the corners (to verify on the real panel).

RoomKey replaces the rocker of an existing German flush-mount light-switch position and keeps
the frame. One per bedroom (secondary chime + intercom + lights + alarm), not the main bell.

## Inputs

| Screen | Tap | Swipe ↑ | Swipe ↓ | Key press | Key hold |
|---|---|---|---|---|---|
| Home | wake + hint only (never an action) | menu | — | all lights (HA) | menu · **disarm** when armed |
| Menu | select item | — | close | next item | select |
| Ringing | answer | — | silence here | answer | answer + talk |
| Call | tap-and-hold disc = talk | — | hang up | hang up | push-to-talk |
| Alarm | — | — | — | hint | **disarm** (1.5 s) |
| White rocker (around the key) | switches **this room's light**, no software involved | | | | |

Why tap never acts on Home: the light rocker surrounds the key, so fingers brush the
screen constantly. Key-down cancels any touch in progress (one press never fires twice).

Needs the **ESP32-C6-Touch-LCD-1.47** (the PoC board has no touch). Its framed size
(24.6 × 44.5 mm) is almost exactly the key in the render.

## Light switch — keep it dumb

The original switch mechanism sits exactly where the key must go, so it can't stay
physically. Its *behaviour* can stay 100 % non-smart:

* **Recommended:** the white rocker becomes a push-button (Taster) around the key, wired to a
  flush-mount **impulse relay** (Stromstoßschalter / -relais). Works with no HA, no Wi-Fi, even
  with a crashed ESP32. Optional later: the ESP32 reads the room-light state (opto input) and
  can pulse the relay too.
* **Alternative:** two-gang frame, old switch untouched, RoomKey next to it.

> **Update 2026-10-01 (wall insert draft v0.5, [`../hardware/docs/insert-design.md`](../hardware/docs/insert-design.md)):**
> the RoomKey insert is **SELV-only (12 V in)** — no power supply, no relay and no 230 V in the RoomKey box. The 12 V
> supply and the impulse relay are certified devices placed by the electrician elsewhere (where the switch leg ends, a
> two-chamber box, or the distribution board; design doc §9). The paragraph below is the original v2 idea and is
> superseded on this point. Also: this room's relay-switched light cannot be part of the key's "all lights" action, and
> Home cannot show its state, unless a feedback path is added (design doc §8.2, Q3c).

Blocking checks (electrician): **neutral wire in the switch box?** (older light-switch boxes
often have only L + switched L; the 5 V supply and relay coil need N) · deep box (61 mm) for
supply + relay + audio · all mains work by an electrician, certified modules only.

## Space budget (rocker measured: 55 × 55 mm)

Assuming a ~55 × 55 mm rocker and a ~27 × 47 mm key shell around the touch board, there is
only ~4 mm above/below the key but ~14 mm left/right. So the mic pinhole and speaker
perforation move to the side strips, or the speaker vents through the ~1 mm shadow gap
around the key (invisible acoustic port). The render's hole above and grille below need a
taller plate than the standard rocker.
