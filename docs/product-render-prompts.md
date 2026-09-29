# Product render prompts (Gemini)

Concept: RoomKey as a **wall insert** that replaces the rocker of a German flush-mount
switch or socket position and keeps the existing frame. Key-cap with display, mic pinhole
above, micro-perforated speaker grille below. Bedroom secondary chime / intercom, not the
main house bell.

Design notes
- Speaker cannot be fully sealed (muffled, big volume loss). A micro-perforation (~40 × 0.8 mm
  holes) reads as texture from 1 m; alternatives are the shadow gap / bottom-edge slot or a plate
  exciter (invisible but weak for voice).
- Mic pinhole at the top, as far from the speaker as possible.
- Light-switch boxes in older German installs often have **no neutral** → a 230 V→5 V supply needs N
  (sockets have it). Replacing a light switch means a relay must switch the lamp (bonus: works
  without HA). Mains work = electrician, deep flush box.
- Check the frame's brand/system: the insert opening is system-specific (many use 55 mm).

## 1 · Edit the real photo (attach the wall-switch photo)

```
Edit the attached photo. Keep everything else exactly as it is: the textured off-white plaster wall, the glossy white square switch frame, the camera angle, the soft indoor light and shadows. Replace ONLY the square rocker inside the frame with a new smart wall insert.

The insert: a flat, glossy white square faceplate that fills the frame opening exactly and matches the frame's plastic, colour and gloss, so it looks like part of the same switch range.

On the faceplate, slightly above centre: a tall rounded-rectangle key shaped like a mechanical-keyboard keycap, about 24 mm wide and 42 mm tall (portrait), standing about 8 mm proud of the faceplate. Gently sculpted sides with soft rounded corners, same glossy white plastic. Its top face is a flush pane of black glass holding a small portrait colour display (visible area about 17 × 32 mm, thin black border). A crisp 1 mm shadow gap runs around the base of the key, showing it is a real key that presses in. A very faint warm amber glow comes out of that gap, like a night-light status ring.

Screen content (keep it minimal and sharp, no other text): near-black background; a small white "21:47" in the top-left corner; in the centre a softly glowing amber circle outline containing a filled amber lightbulb icon; below it "Lights on" in amber and a smaller grey "Bedroom"; at the very bottom a small dark rounded pill with two short lines of tiny grey text.

Microphone: one tiny 1 mm pinhole centred on the faceplate above the key.
Speaker: below the key, a neat rounded-rectangle field (about 20 × 9 mm) of roughly 40 tiny laser-drilled holes (0.8 mm) in an even grid, subtle enough to read as fine texture from a distance.

Style: photorealistic, like a real installed premium German smart-home product. Realistic reflections on the glossy plastic and a slight reflection on the display glass, sharp focus on the insert. No logos, no brand names, no visible cables, no extra buttons, no text anywhere except the screen content described.
```

## 2 · Studio hero shot

```
Studio product photograph of a smart wall insert for a German flush-mounted switch frame, shown installed in a glossy white square frame on a small piece of white textured wall, three-quarter view from slightly below so the depth of the key is visible. Seamless light grey background, soft diffused key light, gentle floor reflection, shallow depth of field.

Design: glossy white square faceplate; slightly above centre a tall portrait keycap-style key (about 24 × 42 mm, 8 mm proud, softly sculpted sides) with a flush black glass top containing a small portrait colour display; 1 mm shadow gap around the key with a soft cyan glow leaking out; a 1 mm microphone pinhole above the key; a subtle grid of about 40 tiny speaker holes below the key.

Screen shows an incoming doorbell (minimal, no other text): near-black background, a glowing cyan circle with a filled cyan bell icon and two faint concentric ripple rings, the word "Doorbell" below in white, a small grey "21:47" under it.

Photorealistic, premium, minimal German design. No logos, no brand names, no cables, no additional text.
```

## 3 · Exploded view (optional)

```
Clean technical exploded-view render of a smart wall insert, parts floating in a straight line along one axis on a pure white background, soft shadows, isometric three-quarter view, no text labels. From front to back: a glossy white keycap-shaped key with a black glass top and a small portrait display; a mechanical keyboard switch with a clear housing and a 2-unit stabilizer wire; a glossy white square faceplate with a microphone pinhole above the key opening and a small speaker-hole grid below it; a small black microcontroller board with the display attached; a tiny round microphone board and a small blue audio amplifier board; a round 28 mm speaker; a small relay module and a compact 230 V to 5 V power module; a deep round grey flush-mounted wall box at the back. Photorealistic materials, precise, product-design presentation style.
```

---

# Realistic north star — 55 × 55 mm rocker (measured 2026-09-29)

Geometry: touch board in its frame 24.6 × 44.5 mm → key shell ≈ 27 × 47 mm.
Portrait: ~4 mm left above/below the key, ~14 mm left/right → mic + speaker move into the
side wings (symmetric perforation strips; mic hidden in one of them). Landscape: 14 mm bands
top/bottom → mic above, grille below, rocker pressed top/bottom — but the UI must be redesigned
for 320×172. Attach the ORIGINAL wall photo, not the first render.

## A · Portrait key (current UI)

```
Edit the attached photo. Keep the textured off-white plaster wall, the glossy ivory-white square switch frame, the camera angle and the soft indoor lighting exactly as they are. Replace ONLY the square rocker inside the frame. The new part must be exactly the same size as the original rocker and sit in the frame the same way, with the same thin gap between rocker and frame. Do not enlarge the frame or the rocker.

New rocker: a flat, glossy white square push-plate matching the frame's plastic and colour.

Through a cut-out in its centre rises a tall, portrait-oriented key, like an oversized mechanical-keyboard keycap. Proportions matter: the key is about half as wide as the rocker and almost as tall as it. Only a very thin white band (about one-fifteenth of the rocker's height) remains above and below the key, while generous white "wings" remain to its left and right. The key stands about 8 mm proud of the rocker, with gently rounded corners and edges and slim glossy white side walls visible in this perspective. A crisp, even 1 mm shadow gap separates the key from the rocker; the key is a separate part that presses in on its own.

Top of the key: a flush pane of black glass with rounded corners, containing a small portrait colour display. The black glass border is thin at the left and right and noticeably thicker at the top and bottom, like a real small display module.

Screen content (sharp, minimal, only this text): near-black background; small white "21:47" top-left; centred, a softly glowing amber circle outline with a filled amber lightbulb icon; below it "Lights on" in amber and a smaller grey "Bedroom"; at the bottom a small dark rounded bar with two thin grey placeholder lines, no readable text in it.

In each white side wing, vertically centred: a slim vertical strip of tiny laser-drilled holes (about 3 columns by 10 rows, 0.8 mm holes), identical on both sides so they read as a deliberate design detail. (Speaker behind one strip, the microphone hidden behind the other.) No other holes.

A very faint warm amber glow leaks from the gap around the key, like a night-light.

Photorealistic, premium German smart-home product quality, realistic reflections on glossy plastic and glass, sharp focus on the insert. No logos, no brand names, no cables, no extra buttons, no text anywhere except the screen content described.
```

## B · Landscape key (needs UI redesign)

```
Edit the attached photo. Keep the textured off-white plaster wall, the glossy ivory-white square switch frame, the camera angle and the soft indoor lighting exactly as they are. Replace ONLY the square rocker inside the frame. The new part must be exactly the same size as the original rocker and sit in the frame the same way. Do not enlarge the frame or the rocker.

New rocker: a flat, glossy white square rocker plate matching the frame's plastic and colour. It still works as the room's normal light switch: press the upper or lower white band.

Centred on it, through a cut-out, rises a wide, landscape-oriented key, like an oversized mechanical-keyboard keycap. Proportions matter: the key is almost as wide as the rocker (only a very thin white margin left and right) and about half as tall as it, leaving generous white bands above and below. The key stands about 8 mm proud, with gently rounded corners and slim glossy white side walls visible in this perspective, and a crisp 1 mm shadow gap all around.

Top of the key: a flush pane of black glass with rounded corners, containing a small landscape colour display. Its black border is thin at the top and bottom and thicker at the left and right ends.

Screen content (sharp, minimal, only this text): near-black background; on the left half a softly glowing amber circle outline with a filled amber lightbulb icon; on the right half "Lights on" in amber, "Bedroom" in grey below it, and a small white "21:47" above.

Upper white band: one tiny 1 mm microphone pinhole, centred.
Lower white band: a neat centred speaker grille of tiny laser-drilled 0.8 mm holes, about 3 rows by 14 columns.
A very faint warm amber glow leaks from the gap around the key.

Photorealistic, premium German smart-home product quality, realistic reflections on glossy plastic and glass, sharp focus on the insert. No logos, no brand names, no cables, no extra buttons, no text anywhere except the screen content described.
```
