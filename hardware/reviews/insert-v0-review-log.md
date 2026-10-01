# Insert v0 — adversarial review log

Design: [`../docs/insert-design.md`](../docs/insert-design.md). Gate (from the brief): every criterion
≥ 8/10 from every reviewer, mean ≥ 8.5, zero open BLOCKER/MAJOR, in **two consecutive rounds by
fresh reviewers**; at most 6 rounds. Items blocked on real-world data count as resolved only if the
design handles them explicitly (assumption + fallback + question for the owner).

Criteria (0–10): **G** geometric correctness & fit · **E** electrical safety & installability ·
**M** manufacturability (FDM) & assembly · **I** electronics / RF / acoustic / thermal integration ·
**N** north-star fidelity & ergonomics · **T** traceability of dimensions to sources ·
**D** clarity of documentation & open questions.

Reviewers (fresh agents each round, given only the artefacts, never the designer's reasoning):
R1 German electrician / VDE · R2 mechanical / FDM · R3 electronics integration · R4 product /
north-star & ergonomics · R5 red-team auditor.

---

## Round 1

### Pre-mortem (written before the round)

It is spring 2027 and the insert failed. Most likely reasons:

1. **Fit — the frame does not hold.** the owner's frame turns out to be clamped by the rocker; the
   printed flange has no clip edge and the plate is screwed to the chassis → the frame wobbles.
2. **Fit — the plate sits closer to the wall than 9 mm** (e.g. 7.5). The flange then lands on
   the tactile-switch tongues and the mic cup; Variant S no longer fits a 40 mm box.
3. **Safety — SELV claim collapses.** Eltako will not confirm that A1/A2 of the ESR61NP is a
   protective separation; the 12 V loop, the plate switches and the ESP ground can no longer be
   treated as SELV.
4. **Installability — no neutral / shallow boxes.** The bedrooms have 2-core switch legs and 40 mm
   boxes; Variant L cannot go in without chiselling and new cable.
5. **Printing — the chassis needs supports in awkward places** or the 0.8 mm walls and 1.0 mm
   flexure tongues warp in ABS; the 1.5 mm switch plate bows and MX switches pop out.
6. **Assembly — the plate switches never click reliably.** The nub/plunger stack (FDM ± 0.2,
   B3F pretravel +0.2) leaves no margin; some units click only when pressed low on the wing, some
   are pre-pressed.
7. **Acoustics — the chime is too quiet.** 15 % grille area, unknown speaker sensitivity: ~65 dB
   at 1 m does not wake anyone in the next room.
8. **RF — Wi-Fi drops** because the antenna is not where assumed, or the user's hand + the key
   shell detune it; the speaker magnet and hub sit right behind.
9. **Heat — 1.1 W in a sealed box** in a warm bedroom: relay and PSU run near 50 °C, SHT31 reads
   +3 K, the ESP's display heats the key front.
10. **Maintenance / look — the key comes off in a child's hand** (only stem friction), the ribbon
    breaks after a year of presses, the plate's white does not match the ivory frame, and the
    mic (wider than the wing) makes the left wing look different from the right.

Mitigations already in v0: 1 → question 2 + foam-tape fallback; 2 → `validate()` computes the
minimum WALL_D (8.9 L / 8.5 S) and question 1; 3 → explicit question + fallback in §4.3;
4 → decision tree §4.4; 5 → print table, flange-only supports; 6 → coupon row D, validate window;
7 → warning + fallbacks; 8 → antenna in front of the plate, printed flange, far screws;
9 → heat estimate + measurement plan; 10 → ribbon replaceable, risk list.

### Artefacts given to the reviewers

`hardware/docs/insert-design.md`, `hardware/cad/insert_params.py` (+ `roomkey_params.py`),
`python3 hardware/cad/insert_params.py` output, `hardware/models/insert-{L,S}_check.json`,
drawings in `hardware/drawings/`, generator sources (`insert_lib.py`), `docs/north-star.jpg`
(AI-generated render), vendor drawings (URLs in `SOURCES`).

### Scores (round 1)

| Reviewer | G | E | M | I | N | T | D | mean | BLOCKER | MAJOR |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 electrician / VDE | 6 | 3 | 6 | 6 | 7 | 7 | 7 | 6.0 | 2 | 6 |
| R2 mechanical / FDM | 3 | 5 | 2 | 5 | 6 | 6 | 6 | 4.7 | 4 | 8 |
| R3 electronics integration | 6 | 6 | 6 | 4 | 6 | 7 | 7 | 6.0 | 0 | 8 |
| R4 product / north star | 7 | 5 | 6 | 6 | 4 | 7 | 7 | 6.0 | 0 | 6 |
| R5 red-team auditor | 4 | 4 | 3 | 4 | 5 | 5 | 6 | 4.4 | 1 | 12 |

**Gate: FAILED** (every criterion < 8 somewhere; 7 BLOCKERs, ~40 MAJORs).

### Findings (condensed; full reviewer texts were read in full) and resolutions

| # | Sev | Reviewer(s) | Finding | Resolution in v0.2 |
|---|---|---|---|---|
| 1 | BLOCKER | R1 | Variant S barrier has an open Ø6.5 hole; grommets are bare holes | **Barrier removed**: the insert is now SELV-only (no 230 V in the RoomKey chamber) |
| 2 | BLOCKER | R1 | no path for mains cables through/around the barrier; relay covers floor entries; S not installable in real 40 mm boxes | 230 V only in certified devices in a separate place: remote (luminaire/junction box), two-chamber box (certified partition) or distribution board — topology table T1–T4 |
| 3 | BLOCKER | R2, R5 | hinge knuckles with 0.2 mm walls, pins not retained | hinge removed; **floating plate** retained by two sliding "drawer" lips (top/bottom edge), front-removable |
| 4 | BLOCKER | R2 | flexure tongue unprintable (cantilever over air), real k ≠ model | flexure removed; switches rigidly mounted on FR4 carriers, the switches are the travel stops |
| 5 | BLOCKER | R2 | B3F (7.7 mm across terminals) does not fit its 6.4 pocket; pins in the slot | carriers + true envelope incl. terminals in the model |
| 6 | BLOCKER | R2 | mic cannot be inserted, not retained; foam lifts it; trim removed its outer wall | round module (Ø13.14 > 13.07 wing) replaced by an **8 × 8 mm mic carrier**; pocket open to the back + retaining cap; trim rule now fails > 0.5 mm³ |
| 7 | MAJOR | R1 | SELV relies on an undeclared ESR61NP input; fallback not designed | relay must have a **declared** SELV input: ES75-12..24V UC (EN 60669-2-2, remote/luminaire) or DIN-rail types; ESR61NP only with Eltako's written confirmation (T2) |
| 8 | MAJOR | R1 | DIY PSU pod would be refused | pod dropped; certified 12 V PSU with terminals (Eltako SNT61 or DIN-rail) outside the RoomKey chamber |
| 9 | MAJOR | R1 | printed barrier as the only separation in one chamber | no longer used (see 1, 2) |
| 10 | MAJOR | R1 | no-N tree incomplete; SELV in a NYM is allowed if insulated for the highest voltage (0100-410 414.4.2); TN-C; two-way switching | rewritten as topologies T1–T4 with a core-count table; the whole switch leg becomes SELV in T1 |
| 11 | MAJOR | R1, R5 | conductors pinched by the skirt; no wiring space; SELV connector location | moot for 230 V (none in the chamber); SELV pigtail + connector position defined |
| 12 | MAJOR | R1 | S in a 40 mm box not installable | S: insert fits 40 mm, the PSU needs its own chamber or a remote supply — stated |
| 13 | MAJOR | R2, R4, R5 | press force model counts one switch (4.7 N, not 2.3); dead top 40 %; wing hard to reach | floating plate on **4 corner switches**: every point of the plate actuates, force modelled per press location |
| 14 | MAJOR | R2, R5 | actuation window negative with real tolerances; pre-pressed switch kills the plate | rigid switches, nominal gap 0.3, switch = stop → clicks for any gap ≥ −PT min; RSS table |
| 15 | MAJOR | R2, R4 | two diagonal MX: free roll axis; 0.7 mm guide engagement | switches on the long axis + **key skirt** sliding 3.8 mm in the collar (0.25 clearance) |
| 16 | MAJOR | R2, R5 | switch-plate countersinks under MX housings / 0.08 mm webs | screws moved to (±10.5, 1.5); web rules in `validate()` |
| 17 | MAJOR | R2 | 1.2 mm printed flange crushed by box-screw heads | steel slot washer under each head; option: original steel support ring |
| 18 | MAJOR | R2 | nothing fixed locates the frame | segmented locating rim on the flange at the frame opening |
| 19 | MAJOR | R2, R5 | plate screw length pierces the face; clamp stack wrong | plate screws removed (drawer lips) |
| 20 | MAJOR | R2, R5 | CAD checks prove little (trim, blanket exemptions, no terminals, no min-wall) | moving MX stem, targeted exemptions, true envelopes, trim-fail rule, wall rules |
| 21 | MAJOR | R2 | assembly order impossible (closed bays, barrier before plugging) | sensor bays deferred; assembly order rewritten; SELV-only insert can be pulled safely |
| 22 | MAJOR | R3 | antenna geometry wrong (chip on the PCB back), wrong metal considered, no RF test | chip body modelled, distances to real metal reported, frame-material question, RSSI acceptance test |
| 23 | MAJOR | R3, R2 | ribbon flex zone undesigned (buckles R 0.75) | **rolling U-loop behind the switch plate**, R ≥ 4, envelope modelled |
| 24 | MAJOR | R3 | no 3.3 V for the mic | 3V3 on the cable from the board header |
| 25 | MAJOR | R3 | no ESD/EMC concept | ESD/EMC section + hub protection list + test plan |
| 26 | MAJOR | R3, R4 | glow ring = 4 corner blobs + leaks | translucent **light-guide collar**, 8 × 2020 LEDs, opaque plate core, light baffle, black mesh |
| 27 | MAJOR | R3 | acoustic model aims at the wrong lever | Helmholtz / quarter-wave computed, SPL range 62–69 dB, hole fallback dropped, question to the owner |
| 28 | MAJOR | R3 | key self-heating unanalysed; SHT31 "isolation" wrong | key ΔT estimate; SHT31/VEML deferred to v1 |
| 29 | MAJOR | R3 | relay drive not fail-safe (high-side, stuck GPIO) | one-shot P-FET, reset-low GPIO + pull-down, clamped plate-sense (hub spec) |
| 30 | MAJOR | R4 | key and plate switch different lights | recommendation for firmware/HA: key press = this room's light in L |
| 31 | MAJOR | R4 | strips do not match the render (3 × 12 Ø1.4 vs 4 × 13 fine) | 4 × 13 holes Ø1.0 pitch 1.6 + black acoustic mesh |
| 32 | MAJOR | R5 | IRM-03 is OVC II in an OVC III location | IRM-03 dropped; SPD is a hard precondition (Eltako "ist zu installieren") |
| 33 | MAJOR | R5 | hub parts do not fit the hub envelope | horizontal hub board behind the MX bodies, component heights as parameters |
| — | MINOR | all | ~45 minor items (θ 1.45 vs 1.43, channel figure, SW_RF 0.49, untagged/duplicated values, magic numbers, coupon v1 missing, ALS sees the glow, BOOT strapping, LED level, board PWR LED, RCD/NAV §13, price, …) | fixed in code/doc where still applicable; coupon v1 generated; see the v0.2 change list |

Designer's note: R1's "SELV-only insert, 230 V only in certified devices in a separate chamber or remote"
is the single biggest improvement and removes BLOCKERs 1–2 and MAJORs 7–12, 32 at once. The plate
mechanism was redesigned from scratch (floating plate) because both the hinge and the flexure were
unbuildable.

### v0.2 implementation status of the round-1 resolutions (designer, before round 2)

All rows of the table above are implemented in code/CAD/doc, with these deviations (each recorded in
insert-design.md §0):

| # | Planned | Done in v0.2 | Reason |
|---|---|---|---|
| 3 | floating plate held by two sliding drawer lips (top/bottom) | **top: rigid drawer lip; bottom: two snap lips on flexible deck tongues**; side/bottom skirts locate the plate ±0.1; skirts open where six frame-locating rims stand | found while finishing v0.2: the sideways drawer slide left the plate unlocated in x (only the frame, ±0.3) and sheared the gaskets during assembly |
| 6 | mic pocket open to the back + retaining cap | carrier inserted from the front onto a 0.7 ledge, held by the gasket | no cap part needed; the plate closes the pocket |
| 18 | segmented locating rim | rims now stand in skirt gaps and reach 2.0 into the frame tunnel (the v0.2 draft rim reached only 0.3 into it) | location only; frame *retention* stays Q2 with fallbacks |
| 26 | 8 × 2020 LEDs | 4 × SK6812 MINI at the collar corners; uniformity = desk-rig test with fallbacks | the collar's long sides are blocked by the speaker (right) and webs (left) |
| 7 | ES75 as the T1 relay | ES75 kept, but its data sheet lists **no LED rating** → T1-LED added (reinforced coupling relay + ESR61NP) | verified the ES75 data sheet |
| — | — | Kaiser 1068-02 verified: 149 mm long, ONE device position + electronics chamber, listed under "Auslaufprodukte" → T2/S1 need a box change and a cover for chamber 2 (2-gang frame [TBD]) | data sheet |
| 20 | wall rules | `insert_wallcheck.py` now separates in-plane walls (≥ 0.8, fail < 0.55) from layer-stack thickness (≥ 0.4) — every printed part is printed with its layers normal to d | a 45° lead-in chamfer is thin along d, not a perimeter problem |

Other v0.2 additions: switches at y ±19.5 and carriers 8.0 × 6.2 (room for the tongues, 1.0 flange strip
next to the speaker), five pressed states in CAD (added bottom band and a corner, 3D pivot lines through
the real lip contacts), `press_force()` over every supporting line of the lip contacts, retention detail
sheet `insert-{L,S}_retention.png`, coupon v1 row D rebuilt around the real top lip + snap tongue,
relay pulse/lock-out rule (ES75 20/300 ms), doc rewritten (v0.2, DRAFT/WIP, SELV-only, electrician-only
for 230 V).

---

## Round 2

### Pre-mortem (written before the round)

It is spring 2027 and v0.2 failed. Most likely reasons:

1. **The snap tongues break or creep** (PETG at 40 °C, a child pries the bottom edge; 4.7 N per tongue at
   yield is modest) → the plate hangs forward.
2. **The nub gap stack is wrong**: B3F bottom-out ≠ 0.45 or the carrier glue line adds 0.2 → switches
   pre-click or the plate needs a hard press at the corners.
3. **No topology fits the owner's rooms**: 2-core switch legs (T1 impossible), no N (T2 impossible), no spare
   cable (T3) → only T4 (keep the switch, lose the north-star look).
4. **The frame falls off** — it was held by the rocker; the rims locate but do not hold it.
5. **The front zone collides** because the rocker sits 8 mm (not 9) proud of the wall.
6. **LED lamps + ES75** — the relay has no LED rating; T1-LED needs a DIN-rail coupling relay that does not fit
   a canopy.
7. **The glow ring is blotchy** (bright corners, dark long sides).
8. **The chime is too quiet** (~62 dB) and nobody wakes up.
9. **The printed chassis warps** (71 × 71 flange on tree supports) → the deck is not flat → nub gaps vary.
10. **The key wobbles/rattles** in the 0.25 guide clearance or the U-loop fatigues.

Mitigations in v0.2: 1 → strain 0.79 %, coupon row D pull test, ASA option; 2 → RSS table + coupon row D
three gaps; 3 → T4 fallback + decision tree; 4 → Q2 + fallbacks; 5 → validate() computes 8.95 + B3FS
fallback; 6 → T1-LED + Q4b; 7 → WIP + fallbacks; 8 → Q6; 9 → front-down print, rims support the flange
[not analysed further]; 10 → coupon row G, desk-rig cycle test.

### Artefacts given to the reviewers

`hardware/docs/insert-design.md`, `hardware/cad/insert_params.py` (+ `roomkey_params.py`, `insert_lib.py`,
`make_*.py`, `make_coupon_v1.py`), the `insert_params.py` / `--tbd` output (reviewers ran it),
`hardware/models/insert-{L,S}_check.json`, all PNGs in `hardware/drawings/`, `tools/insert_wallcheck.py` and its
output, `tools/insert_drawings.py`, `docs/north-star.md` + `docs/north-star.jpg`, vendor sources (URLs in
`SOURCES`). Not given: this log, the designer's reasoning.

### Scores (round 2, fresh reviewers, v0.2)

| Reviewer | G | E | M | I | N | T | D | mean | BLOCKER | MAJOR |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 electrician / VDE | 8 | 6 | 8 | 7 | 8 | 7 | 7 | 7.3 | 0 | 6 |
| R2 mechanical / FDM | 6 | 8 | 5 | 6 | 7 | 7 | 6 | 6.4 | 0 | 5 |
| R3 electronics integration | 8 | 7 | 7 | 6 | 8 | 8 | 8 | 7.4 | 0 | 4 |
| R4 product / north star | 7 | 7 | 8 | 7 | 6 | 8 | 7 | 7.1 | 0 | 6 |
| R5 red-team auditor | 6 | 6 | 7 | 6 | 8 | 7 | 7 | 6.7 | 0 | 7 |

**Gate: FAILED** (no BLOCKER any more — round 1 had 7 — but 28 MAJORs; several criteria < 8). Mean over all 35 scores
7.0 (round 1: 5.4).

### Findings (round 2, condensed; full reviewer texts were read in full) and resolutions

| # | Sev | Reviewer(s) | Finding | Resolution in v0.3 |
|---|---|---|---|---|
| 1 | MAJOR | R2, R5, R3 | duct gasket had no seat (2.5 wide vs 1.0 recess, ran into the skirt); gaskets/mesh not modelled; FOAM_K 10–20× too soft → 1–3 N preload, right wing 2–3× force | **gaskets removed**: mic carrier bonded to the plate; speaker sealed at the speaker (face gasket + plenum floor); mesh in a 0.2 recess; 3 soft preload pads (0.22 N) modelled in the forces; pads/face gasket are CAD bodies |
| 2 | MAJOR | R5, R2 | nub-gap chain had 2 of ≥ 5 terms; coupon row D quantised at 0.2 layers, no carrier; carrier 0.05 off the flange | flange datum (carrier on the flange), 6-term chain (±0.26 RSS / ±0.56 worst) in validate, per-switch shims + assembly check; coupon row D rebuilt with the real seat, nub variants, ≤ 0.1 layers |
| 3 | MAJOR | R2 | chassis not printable as documented (floating islands, unsupported datums) | island ribs; supports inside the well documented with the list of supported faces; none is a precision datum (collar glued with the key as jig; switch-plate seat only sets key height) |
| 4 | MAJOR | R2 | collar is not a linear guide (free roll/pitch) | MX stems are the guide (stated); side skirts only; stop bosses (travel 3.68, pitch ≤ 6.8°); collar relief at the short sides; CAD pitch checks |
| 5 | MAJOR | R2 | documented plate release did not work | blade path under the bottom skirt documented and checked in validate (window 6.0 × 2.3) |
| 6 | MAJOR | R4, R2 (minor) | glow ring visible only near head-on | translucent glow rim of the plate itself (co-printed), lit by the collar; collar corners 2.6 thick, LEDs centred on them |
| 7 | MAJOR | R4 | key and plate fire together (palm) | firmware arbitration requirements (250 ms, mask, no relay pulse after a plate press); PLATE_SENSE on IO3 (interrupt-capable); palm/elbow tests on the desk rig |
| 8 | MAJOR | R4, R1, R5 | "T4 always works" false; no owner trade-off table; 2-core leg makes T1 rare | T0 "new cable" outcome, core table, T4 needs its own 12 V feed and a separate box, owner trade-off table §9.4 |
| 9 | MAJOR | R1, R5 | switch-box inventory (through-wiring), TN-C, switch-leg end location missing | decision procedure §9.2 step 1 |
| 10 | MAJOR | R1 | SELV/230 V meet outside devices (canopy, chamber 2), partition passage unverified, Kaiser front geometry unverified, Auslaufprodukt hidden | 414.4.2 rules in §9.1; Q11; Auslaufprodukt in §9/BOM; T2 look marked [TBD] |
| 11 | MAJOR | R1, R5 | no SELV marking; reconnection risk | mandatory labels both ends + documentation + insert/pigtail marking (§8.1) |
| 12 | MAJOR | R1, R3, R5 | 12 V source not power-limited; B3F feed after the hub protection; PLATE short > B3F rating | ≤ 15 W or fused 0.5 A rule; B3Fs fed from the pigtail via their own 50 mA PTC, before the hub |
| 13 | MAJOR | R1 | ES75 LED rating conflicting (distributors 200 W); Finder 38.51 is DIN rail; STOCKO plug | both sources recorded, Q4b; T1-LED needs a DIN enclosure (size in params); STOCKO noted |
| 14 | MAJOR | R3 | ES75 control voltage ≈ 11.6 V < 12 V | Q4d + fallback (15 V source, or internal control voltage on a 4th core) |
| 15 | MAJOR | R3 | hub area never checked | area rule (both sides, 573 vs 827 mm²), bare MAX98357A, polymer caps, fallback second level |
| 16 | MAJOR | R3 | ESD concept protected the wrong lines, no return path/fallback | §8.4 rewritten (distances, mic-carrier clamps, TVS on BOOT/IO3/IO5/PLATE, fallback graphite shield) |
| 17 | MAJOR | R3 | cable flex life: test < life, no fallback | 250 k-press target, flex-PCB fallback |
| 18 | MAJOR | R4 | no light-state feedback, not asked | Q3c (4th core), firmware "toggle" only, stated in the trade-off table |
| 19 | MAJOR | R4, R5 | SPL blocked on data without fallback | +3 dB half space in the estimate (65–71 dB); fallback: secondary chime; measure through the duct |
| 20 | MAJOR | R4, R5, R2 | box interior (Q5) without fallback | parametric fallback (channel 3.1→2.1, hub −2 mm, else box change) |
| 21 | MAJOR | R5 | speaker front volume leaked into the box (pocket clearance cut the channel walls) | plenum floor 0.6 over the speaker edge, channel starts at the face gasket, pocket no longer cuts the floor |
| 22 | MAJOR | R5, R2 | abuse / secondary stop not handled; SW_MAX_FORCE unused | abuse rule (30 N / 2 switches vs 20 N [TBD]), deck as documented secondary stop, coupon 20 N test |
| 23 | MAJOR | R5 | vacuous/soft rules; CAD pressed at nominal only; wall-check exemptions per part | INFO category; fit-critical rules hard; CAD at nominal AND RSS stop; wall check with 3D zones only |
| 24 | MAJOR | R2 (minor) R4 | frame rims only on three sides / frame could rest on the plate | 8 rims on all four sides; top lip and skirts segmented |
| — | MINOR | all | ~50 minors (antenna distances, metal frame ≈ 1 mm wrong, washer bearing 8 mm², slot 3.2 vs 3.6, tags SW_H_TOL/B3F 3–24 V/BUCK_EFF, drawing d-axis labels, speaker retention, assembly order, tongue strain at the lip end 0.84 %, slot corner, 0.35 first layer, key-shell bridge, colour stack, PWR/STAT LEDs, IO8 pull-up, IO5 for the relay, USB back-feed, plate-sense level, mic obsolescence, WAGO space, DIN 18015-2, hollow walls, SNT61 hiccup, …) | fixed in code/doc/drawings; e.g. stainless load plates, speaker hooks, colour coupon row H, tongue root 14.0 with round slot end (1.16 % at the lip end), terminal zone, GPIO map from the schematic |

Designer's note (round 2): the biggest lesson is that every "soft" element (foam, a sliding guide, a printed datum on
supports) was modelled more optimistically than a reviewer with a data sheet or a FreeCAD probe could accept. v0.3
removes the gaskets instead of modelling them, stops claiming the collar guides the key, and moves the glow ring into
the plate. The installation section is now honest that the most common German switch leg needs a new cable.

---

## Round 3

### Pre-mortem (written before the round)

It is spring 2027 and v0.3 failed. Most likely reasons:

1. **The co-printed glow rim** delaminates from the ivory/black body or bleeds colour (AMS in-layer changes on a 0.8 mm
   ring), or it glows unevenly because the collar front is 1.6 mm away.
2. **Preload pads** creep flat in a year → the plate rattles; or they are stiffer than 10 kPa and add feel.
3. **Mic bonded to the plate** picks up every press as a thump; the tether wires fatigue.
4. **Stop bosses** make the key feel dead (3.68 travel, hits plastic) and the MX2 click window at an end press is only
   0.25 mm wide in the worst case.
5. **Supports inside the well** cannot be removed through the collar opening without breaking the bosses.
6. **The switch box** turns out to be a Geräteverbindungsdose with through-wiring → T0 everywhere.
7. **Speaker hooks** break when inserting the speaker; the face gasket leaks.
8. **Hub** does not fit even two-sided; the firmware change (IO3) is never done.
9. **Tolerance**: the worst-case nub spread requires shimming every unit.
10. **Frame** is held only by foam pads and falls off.

### Artefacts given to the reviewers

As in round 2 (design doc, parameter file + output, CAD library + generators, check JSONs, drawings, wall-check tool +
output, north star, vendor sources). Reviewers were told not to open `hardware/reviews/`.

### Scores (round 3, fresh reviewers, v0.3)

| Reviewer | G | E | M | I | N | T | D | mean | BLOCKER | MAJOR |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 electrician / VDE | 8 | 6 | 8 | 8 | 8 | 8 | 8 | 7.7 | 0 | 2 |
| R2 mechanical / FDM | 6 | 8 | 7 | 7 | 7 | 7 | 7 | 7.0 | 0 | 3 |
| R3 electronics integration | 8 | 7 | 8 | 6 | 8 | 8 | 8 | 7.6 | 0 | 3 |
| R4 product / north star | 7 | 8 | 8 | 8 | 6 | 8 | 7 | 7.4 | 0 | 2 |
| R5 red-team auditor | 6 | 7 | 7 | 7 | 7 | 7 | 6 | 6.7 | 0 | 5 |

**Gate: FAILED** (0 BLOCKER; 15 MAJORs, 10 distinct; 19 of 35 scores < 8). Mean over all 35 scores 7.3 (round 2:
7.0). All five verdicts: fit for coupons and for the electrician discussion, **not yet** for the desk/wall prototype.

### Findings (round 3, condensed; full reviewer texts were read in full) and resolutions

| # | Sev | Reviewer(s) | Finding | Resolution in v0.4 |
|---|---|---|---|---|
| 1 | MAJOR | R2-1, R4-1, R5-1 | end-press model impossible (stems cannot tilt 6–7°); CAD pitch check hid a real collision via the key ↔ housing exemption and unmoved stems; stop bosses land on a tapered housing that was modelled flat | pitch model, stop bosses and the exemption removed; MX moved to (0, +15)/(0, −13) (overhang 8.4/10.4 like a keycap edge); key stops at MX bottom-out; CAD wobble check ±1.5° about x and y with the **stems moving**, base exemptions only: 0 collisions; end presses = WARN with desk-rig test + stabiliser fallback (doc §3) |
| 2 | MAJOR | R1-2, R5-2 | terminal zone (24 × 14 × 14) holds one WAGO; no assumption/fallback | 5 × WAGO 221-412 modelled as CAD bodies (d 25.6–44.2) and checked against hub, domes, box; box ≥ 37.2; conductor bends = WARN + wall-fit test with real NYM-J 5×1.5 + fallback (47 mm box / push-in terminals) |
| 3 | MAJOR | R1-1 | T1 understated: T1-LED enclosure 60 deep vs Finder 75.6; ES75 ≤ 10 A missing from tables; wall junction box case infeasible ("plaster work: none" false); luminaire responsibility | T1a/T1b split (T1b = new box, plaster work); ≤ 10 A protection in "needs" and BOM; T1_LED_ENCLOSURE 120 × 100 × 100 with a validate rule (≥ Finder depth + 15); luminaire responsibility and ≤ 50 °C in the table |
| 4 | MAJOR | R2-2, R5-3 | switch datum rides on B3F solder over an unsupported printed ledge; chain misses solder/droop; coupon layers ≠ part layers, coupon without supports/pads | SMD **B3FS-1002P** on a flat-backed carrier (wires from the back into a 3.0 × 1.6 flange slot at r ≤ 27.3, checked against the box); chain 7 terms incl. solder + bridge sag (±0.27/±0.63); 0.10 mm layers for plate, chassis and coupon; support blockers in the carrier pockets; coupon has the real seat, wire slot and a pad |
| 5 | MAJOR | R2-3 (R4-11, R5-11) | speaker not located in x, face gasket never compressed; "front volume opens only to the room" false | 0.8 → 0.55 foam strip between collar and speaker (CAD body) presses it onto the face gasket; hooks got a 45° lead-in; leak paths listed in doc §6.2 and validate INFO; mic wire hole sealed with silicone; continuous glue bead on the collar seam |
| 6 | MAJOR | R3-1 (R4-10, R5-6, R1-3) | a hub short shuts the SNT61 down (polyfuse trips at ~1 A > 0.5 A source); TVS/FET on PLATE can stop the light; "cannot exceed the B3F rating" false | eFuse 0.4 A / OVP 23 V on the hub branch; RELAY_DRIVE FET from the hub rail through a series Schottky; FMEA table (doc §8.2) states exactly which faults stop the light; claims rewritten; plate PTC V max ≥ 30 V |
| 7 | MAJOR | R3-2 | 230 V misconnection: SMBJ18A cannot clamp mains, polyfuse downstream, V-0 only "preferred" | 1 A T 250 V AC entry fuse (≥ 100 A breaking) ahead of everything; text says what really happens; chassis **V-0 mandatory**; marking named as the real protection |
| 8 | MAJOR | R3-3 | SNT61 start-up and mic acoustic path: no assumption/fallback | both as BLOCKED-ON-DATA with assumption, test and fallback (eFuse soft-start / less capacitance; mic_check.py on a plate coupon / ironed land, gasket, port Ø1.2) |
| 9 | MAJOR | R4-2, R5-5 (R3-4) | "shadow gap stays dark" false: 0.75 of the gap looks onto the lit collar | doc §4 describes the glowing gap; Q12 decision on the desk rig (keep, or mask the collar's inner 0.75); LEDs-off look stated |
| 10 | MAJOR | R5-4 | wires inside the key: 0 mm margin, soft rule failed silently | 0.4 channel in the key back (CAD) → 1.2 mm; fallback AWG32 / flex jumper |
| — | MINOR | all | press force counted touching switches as clicked (R2-4) | press_force adds partial pretravel force; "one switch clicks" everywhere; abuse 30 N on ONE switch (coupon row D, stop-ring fallback) |
| — | MINOR | R2-5 | plate ↔ frame only at rest | CAD gaps at the RSS stop for all five press points (0.157–0.225) + validate WARN with fallback |
| — | MINOR | R2-6, R5-9 | skirts rub at the pivot side (0.03) | validate WARN + coupon test + sanding fallback (doc §5.3) |
| — | MINOR | R2-11, R5-10 | tongue numbers (k 7.1 vs code; free length from the slot tangent) | tongue_mech measures from the slot's round end: 11.55 long, 1.36 %, 13.2 N/mm, 5.8 N |
| — | MINOR | R1-4, R3-9, R5-8 | SNT61 ±1 % [DS] and 10 W variant | PSU_V_TOL 0.01 [DS] → 11.8 V; 10 W variant in the power rule |
| — | MINOR | R1-5 | Q4d fallbacks not buildable as written | rewritten: (a) T1-LED, (b) 15 V DIN-rail PSU in T3 only, (c) internal control voltage = hub redesign, not in v0.4 |
| — | MINOR | R1-6, R1-7, R1-8, R1-9, R1-10 | shared-box joints, chamber-2 accessibility, coupled boxes, 411.3.3/RCD-SPD cost, NAV §13 company, S2/S3 wording | doc §9.1–9.4 and the topology sheet updated (incl. T0 panel and a decision guide) |
| — | MINOR | R3-5 | silver contacts need ≥ 1 mA in S | 4.7 kΩ bleeder in S (rule) |
| — | MINOR | R3-6, R5-7 | IO5 = IMU INT1, IO3/IO4 = TF slot, IO16 boot log | firmware requirements (INFO + doc §8.2): never enable INT1, no microSD; amp SD_MODE resistor, idle clocks during boot |
| — | MINOR | R3-7, R3-8, R3-10, R3-11, R3-12 | hub details, firmware power-save `none`, ESD return, brass vs nylon, LED fit | power figures from the firmware (0.65 W); HA cap requirement; I²S lines in the TVS array + spacer fallback; RF text; LED Q5 fallback (2020); 100 nF placement + rig test |
| — | MINOR | R4-3 … R4-9, R4-12 | force map, mic visible, key colour, light-state UX, owner table, S-specific questions, flat-hand test, drawing labels, glossary | both MX the same brown + force map; black solder mask; key in plate ivory; §9.4 rows (12 V dependence, 2 W standby, Q4e, "all lights" excludes it); Q1-S/Q2-S; desk-rig test R11; glossary; captions |
| — | MINOR | R5-11, R5-12, R5-13, R5-14 | tautological rules, wall-check output, captions, CLAMP_N comment | stop-boss rule gone, RF rules split (spring / metal frame), wall check prints "no spot below 0.8", OK threshold 0.80, slices to d 26.4; G–G/D–D captions; over-torque comment corrected ("snug by hand") |

Designer's note (round 3): the most serious mistake of v0.3 was a CAD check that passed because of an exemption: the
pitched key was declared collision-free while its stems were not moved and its housing contact was exempt. v0.4 checks
only physically possible motions (wobble within stem play, with the stems) and puts end presses where they belong — on
a desk rig, with a fallback. The same pattern (a claim stronger than the evidence) was behind the glow, the leak and the
"hub fault cannot stop the light" findings; all three are now stated as what they are.

---

## Round 4

### Pre-mortem (written before the round)

It is spring 2027 and v0.4 failed. Most likely reasons:

1. **End presses bind** on the desk rig (two stems in one key), and the stabiliser fallback does not fit the 1.5 mm
   switch plate around the cable slot.
2. **The glowing gap looks cheap** with the LEDs off (pale band), and masking the collar makes the rim too dim.
3. **The NYM cores do not fit** behind the WAGOs in a real 40 mm box; every position needs a 47 mm box.
4. **SMD B3FS on hand-soldered carriers** sit crooked (solder under the body) → the chain is worse than ±0.05.
5. **The flange seat bridges sag more than 0.05** at 0.10 mm layers, and every unit needs shims.
6. **The eFuse / entry fuse / PTC parts** cannot be found in sizes that fit the hub envelope.
7. **Eltako answers "no"** to Q4a/Q4c, leaving only T1-LED and T3, which most positions cannot use.
8. **Skirt friction** at the pivot side makes the plate sticky.
9. **The speaker back foam** pushes the speaker against the collar and deforms the light guide.
10. **The reviewers find another check that passes for the wrong reason.**

### Artefacts given to the reviewers

As in round 3 (design doc v0.4, parameter file + output, CAD library + generators, check JSONs, drawings, wall-check
tool + output, north star, vendor sources). Reviewers were told not to open `hardware/reviews/`.

### Scores (round 4, fresh reviewers, v0.4)

| Reviewer | G | E | M | I | N | T | D | mean | BLOCKER | MAJOR |
|---|---|---|---|---|---|---|---|---|---|---|
| R1 electrician / VDE | 7 | 6 | 8 | 7 | 8 | 8 | 7 | 7.3 | 0 | 5 |
| R2 mechanical / FDM | 6 | 8 | 6 | 7 | 7 | 8 | 7 | 7.0 | 0 | 4 |
| R3 electronics integration | 8 | 6 | 8 | 6 | 8 | 7 | 8 | 7.3 | 0 | 3 |
| R4 product / north star | 8 | 7 | 8 | 8 | 7 | 8 | 7 | 7.6 | 0 | 2 |
| R5 red-team auditor | 7 | 6 | 7 | 7 | 8 | 6 | 6 | 6.7 | 0 | 5 (one "borderline BLOCKER") |

**Gate: FAILED** (0 BLOCKER; 19 MAJORs, ~13 distinct; 21 of 35 scores < 8). Mean over all 35 scores 7.2 (round 3: 7.3,
round 2: 7.0). All verdicts: fit for coupons and the end-press desk rig; not yet for the wall-fit prototype, the chassis
print or the electrician brief. R2 could not break the CAD (rebuild = STEP, collisions reproduce, extra states clean).

### Findings (round 4, condensed; full reviewer texts were read in full) and resolutions

| # | Sev | Reviewer(s) | Finding | Resolution in v0.5 (NOT re-reviewed) |
|---|---|---|---|---|
| 1 | MAJOR | R2-1, R5-1 | "works down to 7.6 / ≥ 8.3 mm" false: the retention (pressed snap lips vs wall, top lip vs flange) needs WALL_D ≥ 8.9 | `validate()` derives the threshold (8.9) and warns; doc, Q1 and risks say ≥ 8.9; below it = redesign |
| 2 | MAJOR | R1-1, R3-3, R5-4 | misconnection narrative covered one case; the fuse is only in +12 V; with the lamp as return or L on PLATE/0 V nothing opens and the SELV side goes live | per-conductor matrix (§8.1); verification before connecting + RCD 30 mA as preconditions (§9.1); fuse ≥ 1500 A + creepage; "SELV only" qualified; V-0 = mitigation |
| 3 | MAJOR | R1-2 (R2-5, R5) | 40 mm box headline contradicted by the conductor geometry (2.8 mm for 2.7 mm cores) | 47 mm box = planning default; 40 mm only if the wall-fit test passes; evidence stated; WAGOs flat / push-in terminals as fallbacks |
| 4 | MAJOR | R1-3 | north star / READMEs still describe a PSU + relay in the switch box | note added to `docs/north-star.md`; the top-level `README.md`, `README.de.md` and `docs/product-render-prompts.md` were **not** edited (README.md has uncommitted changes by someone else) → open item for the owner |
| 5 | MAJOR | R1-4, R3-2, R5-6 | eFuse rule compared the largest single load; 0.4 A not settable on the named part; SNT61 trip point unknown | rule uses the summed peak 0.37 A with ±7 % (0.43 A, 60 V class, OVLO 17 V) [TBD part]; hub-short-vs-light as BLOCKED-ON-DATA (Q4f, R14, fallbacks) |
| 6 | MAJOR | R1-5 | flange = datum and clamp; box rim offset; over-torque | BLOCKED-ON-DATA with Q1b, click check after wall mounting, support-ring / compression-sleeve fallbacks |
| 7 | MAJOR | R3-1 | IO5 = MTDI floats at reset → relay pulses at power-up / boot loop; strapping list wrong | 100 k pull-down + 20 ms qualifier; test R12; SOURCES corrected |
| 8 | MAJOR | R5-2 | RF spring distance sign error (8.1 pressed, not 11.5) | fixed; soft rule now WARNs; contact leaves / cable wires listed; rotate-MX2 fallback |
| 9 | MAJOR | R5-3 | wall-check slices missed the speaker hooks (0.2–0.6 layer stack) | hooks 1.2 thick (tip 0.8); planes through every lip and hook; claim qualified (sampling limit stated; normal-ray test = v0.6) |
| 10 | MAJOR | R5-5 | Q4e power-cut state without assumption/fallback | assumption, test R15, fallback |
| 11 | MAJOR | R4-1 | touch gestures (0.8–1.2 N) can fire the 1.1 N key | assumption, test R13, fallbacks (heavier switches, firmware gesture lock) |
| 12 | MAJOR | R4-2 | owner measurements that need an open 230 V box not flagged | every question tagged owner / electrician; wall-fit prototype defined (desk, loose box, spare frame) |
| 13 | MAJOR | R2-2 | mic wires squeezed between carrier and pocket floor; service loop behind silicone | wire well beside the pocket (CAD), sideways S-loop, removable foam plug, flex in R8 |
| 14 | MAJOR | R2-3 | coupon not in the chassis' V-0 material; V-0 rating thickness | row D bases in the V-0 filament; V-0 rated at ≤ 0.8 mm; E/σy from its data sheet |
| 15 | MAJOR | R2-4 | end-press binding likely (drawer estimate ≈ 1.2·F friction); stabiliser fallback collides with the cable path; overhang rule tautological | estimate in the doc; rule → INFO; fallback key module must re-route the cable — **not modelled**, both modules for the first rig |
| — | MINOR | R1-6 … R1-12 | 4-core legs from series/two-way switches; Schalterdosentechnik; SELV insulation test; 24 V source; V-0 thickness; dead cable ends; 10 W SNT61 text; 230 V arithmetic as OK; T2 one-frame claim | all addressed in doc/params (230 V arithmetic now INFO; SMBJ24A + OVLO make a 24 V source benign) |
| — | MINOR | R2-6 … R2-13 | elephant foot, supports in the deck–flange slot, speaker foam insertion, tilt ≥ 6°, carriers taped until checked, coupon switch spread, claw boxes, plate flatness, fuse breaking capacity | addressed in §5–§11 (instructions, fallbacks, full-size plate print) |
| — | MINOR | R3-4 … R3-12 | 5 V crest current, no hardware mute, OV coordination, FMEA rows, wetting current in L, self-heating pass limit, RF list, mic ring/firmware deltas, GPIO wording, ESD seam | 470 µF + scope test; mute = accepted risk; SMBJ24A/OVLO; FMEA rows added; bleeder in L and S; pass ≤ 15 K; lists corrected |
| — | MINOR | R4-3 … R4-10 | how the light is switched now, "visible from any angle", 4th core not enough, force map off-centre, key look, self-heating limit, BOOT failure mode, housekeeping | owner table rows; glow visibility from standing height; Q3c needs; force map corrected; key-look note; BOOT failure mode; README desk rig |
| — | MINOR | R5-7 … R5-17 | IO1/IO2 not free, header position, B3FS minimum load, standby 2.3 W, WAGO radius, ratio, TBD list, shadow-gap rule, one-sided sag, coupon pivot, stale texts | all fixed (channel follows the real header, TBD list extended, rules made meaningful, headers say "version from insert_params") |

Also found while fixing: the re-oriented carrier wire slot (1.6 × 3.0) cut 0.1 into the carrier pocket wall (0.71 mm
sliver, wall check) → shortened to 1.6 × 2.6 and a validate rule added (slots stay ≥ 0.1 inside the pockets).

### Decision after round 4: the loop stops here (gate not passable without real-world data)

Rounds 2–4 scored 7.0 / 7.3 / 7.2 on average. Each round removed its MAJORs, and each fresh round found a similar
number of new ones (28 → 15 → 19), increasingly of one kind: claims that only a physical part, a rig or a manufacturer
can settle, where the reviewers judged the stated assumption already doubtful. The gate needs **two consecutive**
passing rounds with every one of 35 scores ≥ 8; with two rounds left and 21 scores below 8, that is not credible on
paper. Continuing would polish text, not reduce risk. v0.5 fixes the round-4 findings (above) but was **not** reviewed
by a fresh round — treat its resolutions as unverified.

**What is needed before another review round can pass** (the honest blockers):

| need | why the reviewers cannot accept it on paper | where |
|---|---|---|
| desk rig R1 with the printed key shell + switch plate + 2 MX (and the stabiliser variant) | end-press binding is estimated *likely*; the fallback re-routes the cable | doc §3 |
| measurements Q1 (rocker ↔ wall, ≥ 8.9?), Q1b (box rim), Q2/Q2-S (frame), Q5 (box) | retention threshold, datum flatness, frame holding, radial room | §13 |
| wall-fit prototype: loose 40 and 47 mm boxes, spare frame, real NYM-J 5×1.5, 5 WAGOs | conductor bends behind the insert | §8.1 |
| parts: B3FS-1002P, V-0 filament rated ≤ 0.8 mm, an eFuse with ILIM ≈ 0.43 A ± 7 %, a 1500 A entry fuse, the mic part | coupon row D in the real material; hub window; misconnection layout | §5, §8, §10 |
| Eltako answers Q4a–f (incl. SNT61 overload behaviour and the ES75 power-cut state) | SELV status, LED rating, minimum voltage, light-path independence | §9 |
| desk-rig tests R2–R15 (glow look Q12, mic path, SPL, cold start, hub short, relay drive at reset, touch vs key, power cut) | every one is a stated assumption with a fallback, but unmeasured | §10 |
| a hub schematic (not an envelope) | the FMEA, the misconnection matrix and the eFuse window can only be closed on a real circuit | §8.2 |

Recommended next step for the owner: print coupon v1 (row D in the chosen V-0 filament) and the key module (and have the
stabiliser variant modelled), build the desk rig, measure Q1/Q2 at one real position, ask Eltako Q4a–f, then run
review round 5 on the measured design.
