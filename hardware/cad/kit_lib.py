"""RoomKey KIT v0.7 (prototype, WIP): the whole RoomKey in ONE box (supply separate; bench = lab supply 5 V).

Adds to the unchanged wall insert (insert_lib): pins on the chassis' 4 hub posts and a BACK CARRIER on them, holding the
owner's LD2410C radar (antenna side forward behind a window, patch antennas at the outer −x edge so they look forward
through the left wing only) and the MAX98357A (on pins, components to the open back). The round INMP441 sits behind
the ledge, upper left, fed by a sound tube from the plate's mic hole (it fits neither the 12.0 wing nor the touch-board
back).
Checked inside the practice box (desk_lib.wall_block, one box). Geometry: insert_params.py §7.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import desk_lib as D  # noqa: E402

L, P, R, V, EPS = D.L, D.P, D.R, D.V, D.EPS
box, cyl, rrect, fuse, cut = D.box, D.cyl, D.rrect, D.fuse, D.cut
R_BOX = P.BOX_USABLE_D / 2 - P.FIT_MARGIN          # 28.5: everything behind the wall plane stays inside this radius


def kit_chassis(v="S"):
    """the insert chassis (v0.11: with the hub posts, the sound tube and the radar's support blade) + the hole where the
    SHT31-D's wires from the frame enter the box."""
    ch, _ = L.chassis(v)
    hx, hy, hd = P.FRAME_RH_HOLE                      # wires of the SHT31-D in the frame enter the box here (rim gap)
    rh_hole = cyl(hx, hy, hd / 2, P.WALL_D - P.FLANGE_T - 0.5, P.WALL_D + 0.5)
    return cut(ch, [rh_hole])


def kit_refs():
    return {"SHT31-D": D.rh_ref()}                    # in the practice frame's bottom border (v0.11: radar refs in insert_lib)


def tray_webs(bc):
    """thinnest material between the tray's outline and each opening (window, pin holes), in a section through its
    plate — what the slicer sees. Below ~0.8 (2 lines of a 0.4 nozzle) the slicer drops the web."""
    import Part
    c0, c1 = P.KIT_CARRIER_D
    wires = bc.slice(V(0, 0, 1), -(c0 + c1) / 2)
    outer = max(wires, key=lambda w: abs(Part.Face(w).Area))
    inner = [w for w in wires if w is not outer]
    webs = {}
    for w in inner:
        c = w.BoundBox.Center
        nm = "window" if w.BoundBox.XLength > 5 else f"hole ({c.x:+.1f}, {c.y:+.1f})"
        webs[nm + " ↔ edge"] = round(w.distToShape(outer)[0], 2)
        others = [w2 for w2 in inner if w2 is not w]
        if others:
            webs[nm + " ↔ next opening"] = round(min(w.distToShape(w2)[0] for w2 in others), 2)
    return webs


HUB_MX_HOLES = ((5.08, 15.0, 1.75), (2.54, 20.08, 3.0), (0.0, 15.0, 4.0), (-3.81, 17.54, 3.0), (-5.08, 15.0, 1.75),
                (-5.08, -13.0, 1.75), (-2.54, -18.08, 3.0), (0.0, -13.0, 4.0), (3.81, -15.54, 3.0), (5.08, -13.0, 1.75))
# [KiCad] the hub's SW1/SW2 (Kailh hot-swap) holes (x, y, drill): kept open through the socket blocks of the dummy, so
#         the real MX switches plug in for the fit test (board 2026-10-09 00:28)


def hub_dummy():
    """v0.11: a printable stand-in for the hub PCB, to try the fit before ordering: the board (outline, slot, cut-outs,
    drill holes) from its STEP, and every part on its back as a block of its real footprint and height (the part models
    float on their pads, so they are not fused as they are). Printed front face down; ONE solid."""
    h = L.hub_pcb()
    sol = sorted(h.Solids, key=lambda q: -q.Volume)
    board = sol[0]
    back = P.HUB_PCB_D0 + P.HUB_PCB_STEP_TOP
    blocks = []
    for q in sol[1:]:
        bb = q.BoundBox
        top = -bb.ZMin                                   # deepest point (d) of the part
        if top <= back + 0.05 or bb.XLength < 0.2 or bb.YLength < 0.2:
            continue                                     # front-side bits / flat pads: not printed
        blocks.append(L.box(bb.XMin, bb.XMax, bb.YMin, bb.YMax, back - 0.05, top))
    body = board.fuse(blocks).removeSplitter() if blocks else board
    holes = [L.cyl(x, y, d / 2 + 0.1, P.HUB_PCB_D0 - 1.0, back + 8.0) for (x, y, d) in HUB_MX_HOLES]
    body = body.cut([L.box(-40, 40, -40, 40, P.HUB_PCB_D0 - 5.0, P.HUB_PCB_D0)] + holes)
    assert len(body.Solids) == 1, f"hub dummy: {len(body.Solids)} solids"
    return body.Solids[0]


def kit_bodies():
    """every printed part and reference body of the kit in the practice box, at rest (also used by the wiring)."""
    one = ((0.0, 0.0),)
    pbody, prim = L.plate_parts("S")
    bodies = {"practice box": D.wall_block(one), "frame 1-gang": D.frame_2x(one, with_rh=True), "key shell": L.key_shell(),
              "switch plate": L.switch_plate(), "collar": L.collar(), "plate": fuse([pbody, prim]),
              "chassis (kit)": kit_chassis("S"), "radar tray": L.radar_tray()}
    refs = L.ref_bodies("S")
    for k in ("touch board", "antenna chip", "MX switch 1", "MX switch 2", "speaker 2030", "LED 1", "LED 2", "LED 3", "LED 4",
              "box screw L", "box screw R", "load plate L", "load plate R", "cable loop", "speaker back foam", "hub",
              "LD2410C", "LD2410C header", "LD2410C front parts", "LD2410C edge parts", "LD2410C pin stubs"):
        bodies[k] = refs[k]
    bodies.update(kit_refs())
    return bodies


def build_kit():
    print(f"\n==================== RoomKey KIT (concept v0.7: one box, lab supply 5 V) — parts v{P.VERSION} ====")
    bodies = kit_bodies()
    ch, bc = bodies["chassis (kit)"], bodies["radar tray"]
    for nm in ("chassis (kit)", "radar tray"):
        bb = bodies[nm].BoundBox
        print(f"  {nm:15s} valid {bodies[nm].isValid()} | solids {len(bodies[nm].Solids)} | {bb.XLength:.1f} × {bb.YLength:.1f} × "
              f"{bb.ZLength:.1f} | {bodies[nm].Volume/1000:.2f} cm³")
    ex = {frozenset(("box screw L", "practice box")), frozenset(("box screw R", "practice box")),
          frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate")),
          frozenset(("speaker 2030", "speaker back foam")), frozenset(("chassis (kit)", "speaker back foam"))} | L.HUB_EXEMPT
    # v0.9.2: the radar's front parts are no longer exempt — they must clear the carrier (the board sits on ledges)
    webs = tray_webs(bc)
    print(f"  radar tray: thinnest web {min(webs.values()):.2f} (rule ≥ {P.KIT_MIN_WEB}) | " +
          ", ".join(f"{k} {v:.2f}" for k, v in webs.items()))
    # v0.9.2: the radar tray must be a CLOSED frame — along the parts edge, where the cable-loop keep-out takes the tray
    # wall, the plate strip under the board must run through (v0.9.1 lost it and the tray became an open "C")
    rx0, rx1, ry0, ry1, _ = P.KIT_RADAR
    c0 = P.KIT_CARRIER_D[0]
    _, _, ly0, ly1, _, _ = P.loop_up()
    ys = [ly0 - 0.5 + i * 0.5 for i in range(int((min(ly1, ry1) - ly0) / 0.5) + 2)]
    gaps_ = [y for y in ys if not bc.isInside(V(rx1 - 1.1, y, -(c0 + 0.75)), 0.001, True)]
    print(f"  radar tray frame: {'CLOSED' if not gaps_ else 'OPEN at y ' + ', '.join(f'{y:.1f}' for y in gaps_)}")
    assert not gaps_, "radar tray frame is open along the parts edge (strip under the board missing)"
    col = L.check_state(bodies, "kit, rest", ex)
    # key pressed / rocked with the kit parts present
    kb = dict(bodies)
    for nm in ("key shell", "touch board", "antenna chip"):
        kb[nm] = L.key_pressed(bodies[nm])
    col += L.check_state(kb, "kit, key pressed", ex, only=("key shell", "touch board", "antenna chip"))
    gaps = {}
    for a, b in (("LD2410C front parts", "radar tray"), ("LD2410C edge parts", "radar tray"),
                 ("LD2410C pin stubs", "radar tray"), ("LD2410C", "practice box"), ("LD2410C header", "practice box"),
                 ("radar tray", "hub"), ("LD2410C", "hub"), ("LD2410C header", "hub"), ("radar tray", "cable loop"),
                 ("radar tray", "speaker 2030"), ("radar tray", "chassis (kit)"), ("hub", "chassis (kit)"),
                 ("hub", "switch plate"), ("hub", "speaker 2030"), ("hub", "practice box"),
                 ("chassis (kit)", "switch plate"), ("chassis (kit)", "plate"), ("SHT31-D", "frame 1-gang"),
                 ("SHT31-D", "chassis (kit)"), ("SHT31-D", "plate"), ("SHT31-D", "practice box")):
        gaps[f"{a} ↔ {b}"] = round(L.min_gap(bodies[a], bodies[b]), 3)
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    for k, val in gaps.items():
        print(f"    gap {k:45s} {val}")
    ch.exportStep(os.path.join(L.OUT, "kit_chassis.step"))                     # the glued assembly (reference)
    for i, (lab, part) in enumerate(zip(("front", "flange", "rear"), L.chassis_parts(ch)), 1):   # v0.10: three prints
        L.export(part, f"kit_chassis_{i}_{lab}", "front_down")
        L.ceilings(part, f"kit_chassis_{i}_{lab}", "front_down")
    L.export(bc, "radar_tray", "front_down")
    L.ceilings(bc, "radar_tray", "front_down")
    hd = hub_dummy()
    L.export(hd, "hub_dummy", "front_down")
    L.ceilings(hd, "hub_dummy", "front_down")
    import Part
    Part.makeCompound(list(bodies.values())).exportStep(os.path.join(L.OUT, f"kit-v{P.VERSION}_assembly.step"))
    L.write_stl(Part.makeCompound([bodies[k] for k in ("key shell", "switch plate", "collar", "plate", "chassis (kit)", "radar tray")]),
                os.path.join(L.OUT, f"kit-v{P.VERSION}_printed-assembly.stl"), 0.05, 0.4)
    if min(webs.values()) < P.KIT_MIN_WEB:
        print(f"  ERROR radar tray web below {P.KIT_MIN_WEB}: the slicer will open it")
    with open(os.path.join(L.OUT, f"kit-v{P.VERSION}_check.json"), "w", encoding="utf-8") as f:
        json.dump({"collisions": col, "gaps": gaps, "tray_webs": webs}, f, indent=1, ensure_ascii=False)
