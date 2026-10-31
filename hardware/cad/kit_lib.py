"""RoomKey KIT (prototype, WIP): the whole RoomKey in ONE box (supply separate; bench = lab supply 5 V), in TWO builds
from the same printed key, collar and plate (the owner, 2026-10-09: keep both until the PCB order is decided; every fit
fix goes into both):

  pcb       (v0.11) the hub PCB behind the switch plate (MX hot-swap sockets, mic, amplifier, connectors) on two chassis
            posts + one switch-plate post (M2); v0.12: the LD2410C in a cage IN the hub plane (the hub's radar window), on
            a blade of the chassis flange part; a sound tube from the plate's mic hole to the hub's port. wiring_pcb.py
            has the wires the hub leaves.
  discrete  (v0.10.x) the self-wired kit: pins on the chassis' 4 hub posts and a BACK CARRIER on them with the LD2410C
            (antenna forward behind a window) and the MAX98357A; the round INMP441 behind the ledge, upper left, fed by
            a sound tube. wiring_lib.py has every wire.
Both get the v0.11 product decisions (one RoomKey, fixed plate on rest pads, no plate switches). v0.12: RoomKey is built
only as the plug-in device (owner 2026-10-31); the housing (plug_lib.py) holds the kit and the humidity sensor, whose
place and wires are part of the kit here. Geometry: insert_params.py §7, §8.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_lib as L  # noqa: E402

P, R, V, EPS = L.P, L.R, L.V, L.EPS
box, cyl, rrect, fuse, cut = L.box, L.cyl, L.rrect, L.fuse, L.cut
R_BOX = 28.5        # the self-wired build's parts behind the flange are trimmed to this radius (the plug interior is a square
#                     of ±P.plug_in_half(); nothing reaches its edges on the axes — the housing check proves it)
BUILDS = ("pcb", "discrete")


def mic_parts():
    """sound tube (plate mic hole → INMP441 port, through the deck pocket and the flange), a 1 mm shelf behind the ledge
    (anchored on the well's rear wall, kept outside the well so it clears the switch plate) and a partial ring that
    holds the round module. Foam seal rings at both tube ends (not modelled)."""
    px, py = P.KIT_MIC_PORT
    cx, cy = P.KIT_MIC_C
    bore, wall = P.KIT_MIC_TUBE
    t0 = P.PLATE_T + P.KIT_MIC_FOAM_FRONT[1]                    # v0.10: flush with the deck front
    t1 = P.KIT_MIC_D0 - P.KIT_MIC_FOAM[1]
    rm = R.MIC_D / 2
    tube = cyl(px, py, bore / 2 + wall, t0, t1)
    shelf = cyl(cx, cy, rm + 1.2, P.COLLAR_D1, t1).common(box(-40, -(P.WELL_IN_X + 0.2), -40, 40, 0, 40))   # v0.10: down
    # to the rear part's front face (d COLLAR_D1) — a 1 mm shelf at t1 hung in the air when the rear part prints front down
    ring = cyl(cx, cy, rm + 0.2 + 1.0, t1, P.KIT_MIC_D0 + R.MIC_T + 0.6).cut(cyl(cx, cy, rm + 0.2, 0, 40))
    body = fuse([tube, shelf, ring]).common(cyl(0, 0, R_BOX - 0.2, 0, 60))
    return body, cyl(px, py, bore / 2, P.PLATE_T - 0.5, t1 + 0.1)


def kit_chassis(build="pcb"):
    """the kit chassis. pcb: the insert chassis (hub posts, sound tube to the hub, radar blade). discrete: the chassis with
    the carrier posts + a pin on each of the 4 hub posts (the carrier slides on and is glued) + the mic tube/holder."""
    ch, _ = L.chassis("S", build)
    if build == "pcb":
        return ch
    pd, pl, _ = P.KIT_POST_PIN
    pins = [cyl(x, y, pd / 2, P.HUB[4] - EPS, P.HUB[4] + pl) for (x, y) in P.HUB_POSTS]
    mic, bore = mic_parts()
    return cut(fuse([ch, mic] + pins), [bore])


def rh_ref():
    """v0.12: the humidity sensor (SHT31-D breakout; PCB build later the sensor tail in the same place) in G2's bottom wall,
    chip side DOWN behind the skin's vents: board + chip."""
    g = P.plug_rh()
    ccx, ccd = g["chip"]
    board = box(g["x0"], g["x1"], g["y0"], g["y1"], g["d0"], g["d1"])
    return board.fuse(box(ccx - 1.25, ccx + 1.25, g["y0"] - 1.1, g["y0"] + 0.01, ccd - 1.25, ccd + 1.25))


def rh_pins():
    """VIN, GND, SCL, SDA along the board's back edge, on its top (inner) face."""
    g = P.plug_rh()
    xc, d = (g["x0"] + g["x1"]) / 2, g["d1"] - 1.6
    return {nm: (xc + (k - 1.5) * 2.54, g["y1"] + 0.3, d) for k, nm in enumerate(R.RH_PINS)}


def kit_refs(build="pcb"):
    if build == "pcb":
        return {"SHT31-D": rh_ref()}                 # radar refs in insert_lib
    return kit_refs_discrete()


def back_carrier():
    """plate on the hub-post pins: amplifier area (the hub envelope) + radar area (lower left), trimmed to the box radius;
    a window in front of the radar's antennas; v0.8: a closed TRAY wall round the radar (it was a floppy open U with corner
    brackets); two pins for the amplifier on the back face. Printed front face down, no supports."""
    c0, c1 = P.KIT_CARRIER_D
    rx0, rx1, ry0, ry1, rd = P.KIT_RADAR
    hub = box(P.HUB[0] + 1.3, P.HUB[1] - 0.1, P.HUB[2] - 0.4, P.HUB[3] - 0.2, c0, c1)
    rad = box(rx0 - 0.6, rx1 + 0.3, ry0 - 0.6, ry1 + 0.6, c0, c1)
    pads = [cyl(x, y, P.KIT_POST_PIN[2] / 2 + P.KIT_PAD_WALL, c0, c1) for (x, y) in P.HUB_POSTS]   # wall round the holes
    plate = fuse([hub, rad] + pads).common(cyl(0, 0, R_BOX - 0.2, c0 - 1, c1 + 10))
    keep_loop = box(-P.CABLE_W / 2 - 1.0, P.CABLE_W / 2 + 1.0, P.LOOP_Y[0] - 0.5, P.LOOP_Y[1] + 0.2, c0 - 1, c1 + 5)
    tools = [keep_loop]
    tools += [cyl(x, y, P.KIT_POST_PIN[2] / 2, c0 - 1, c1 + 1) for (x, y) in P.HUB_POSTS]
    # v0.8 radar tray: closed perimeter wall round the board (outside its footprint), plate front → 0.3 behind the board
    tw, tc = P.KIT_RADAR_TRAY
    rz = P.KIT_RADAR_RAISE
    t1 = c1 + rz + R.RADAR_T + 0.3
    tray = box(rx0 - tc - tw, rx1 + tc + tw, ry0 - tc - tw, ry1 + tc + tw, c0, t1).cut(
        box(rx0 - tc, rx1 + tc, ry0 - tc, ry1 + tc, c1 - EPS, t1 + 1))
    plate = fuse([plate, tray]).common(cyl(0, 0, R_BOX - 0.2, c0 - 1, t1 + 1))
    wy1 = min(ry1 - 1.5, P.HUB_POSTS[0][1] - P.KIT_POST_PIN[2] / 2 - 0.8)          # stays below the hub-post pin
    # v0.9.2: back to the v0.8 window (the board is raised on ledges, its parts clear the plate) → the plate strip under
    # the parts edge closes the tray frame beside the cable-loop keep-out
    tools.append(box(rx0 - tc, rx1 - 1.8, ry0 + 1.5, wy1, c0 - 1, c1 + 1).common(      # window for the antennas; its −x side
        cyl(0, 0, R_BOX - 0.2 - 1.0, c0 - 2, c1 + 2)))                                # ends at the tray wall, ≥ 1.0 from the
                                                                                      # box-radius trim (no skin)
    body = cut(plate, tools)
    # v0.9.2 ledges at the board's short ends, header side only (the parts edge stays free); the top one stops short of the
    # hub-post pin's hole wall
    hx = P.HUB_POSTS[0][0] - P.KIT_POST_PIN[2] / 2 - 0.8
    ledges = [box(rx0 - tc, rx0 + P.KIT_RADAR_LEDGE_X, ry0 - tc, ry0 + 1.5, c1 - EPS, c1 + rz),
              box(rx0 - tc, min(rx0 + P.KIT_RADAR_LEDGE_X, hx), wy1 + 0.5, ry1 + tc, c1 - EPS, c1 + rz)]
    parts = [fuse([body] + ledges)]
    # amplifier pins (its two mounting holes, top corners) on the back face
    ax, ay = P.KIT_AMP_C
    hy = ay + R.AMP_H / 2 - R.AMP_HOLE_C[1]
    parts += [cyl(ax + sx * (R.AMP_W / 2 - R.AMP_HOLE_C[0]), hy, R.AMP_PIN_D / 2, c1 - EPS, c1 + 3.0) for sx in (-1, 1)]
    return fuse(parts).common(cyl(0, 0, R_BOX, c0 - 1, c1 + 20))


def carrier_webs(bc):
    """thinnest material between the carrier's outline and each hole / the window, in a section through the plate —
    what the slicer sees. Below ~0.8 (2 lines) it drops the web and the hole opens over the edge."""
    import Part
    c0, c1 = P.KIT_CARRIER_D
    wires = bc.slice(V(0, 0, 1), -(c0 + c1) / 2)
    outer = max(wires, key=lambda w: abs(Part.Face(w).Area))
    inner = [w for w in wires if w is not outer]
    webs = {}
    for i, w in enumerate(sorted(inner, key=lambda w: (round(w.BoundBox.Center.x), round(w.BoundBox.Center.y)))):
        c = w.BoundBox.Center
        nm = "window" if w.BoundBox.XLength > 5 else f"hole ({c.x:+.1f}, {c.y:+.1f})"
        webs[nm + " ↔ edge"] = w.distToShape(outer)[0]
        for w2 in inner:
            if w2 is not w:
                webs.setdefault(nm + " ↔ next opening", 99.0)
                webs[nm + " ↔ next opening"] = min(webs[nm + " ↔ next opening"], w.distToShape(w2)[0])
    return {k: round(v, 2) for k, v in webs.items()}


def kit_refs_discrete():
    rx0, rx1, ry0, ry1, rd = P.KIT_RADAR
    c1 = P.KIT_CARRIER_D[1] + P.KIT_RADAR_RAISE      # v0.9.2: the board's front face (on its ledges)
    ew, eh = P.KIT_RADAR_EDGE
    refs = {"LD2410C": box(rx0, rx1, ry0, ry1, c1, c1 + R.RADAR_T),
            "LD2410C header": box(rx0 + 0.3, rx0 + 2.8, ry0 + 3.0, ry1 - 3.0, c1 + R.RADAR_T, c1 + R.RADAR_T_PINS - R.RADAR_T),
            # antenna face, from the owner's photo 2026-10-06 [±0.5]: the chip (2.3–8.2 from the parts edge), the band of
            # SMD parts along the whole parts edge, the header pin stubs
            "LD2410C front parts": box(rx0 + 7.0, rx1 - ew - 0.1, ry0 + 8.0, ry0 + 14.0, c1 - 1.0, c1),
            "LD2410C edge parts": box(rx1 - ew, rx1 - 0.2, ry0 + 0.4, ry1 - 0.4, c1 - eh, c1),
            "LD2410C pin stubs": box(rx0 + 0.3, rx0 + 2.4, ry0 + 5.0, ry0 + 17.0, c1 - P.KIT_RADAR_STUBS, c1)}
    ax, ay = P.KIT_AMP_C
    refs["MAX98357A"] = box(ax - R.AMP_W / 2, ax + R.AMP_W / 2, ay - R.AMP_H / 2, ay + R.AMP_H / 2, c1, c1 + R.AMP_T)
    cx, cy = P.KIT_MIC_C
    refs["INMP441"] = cyl(cx, cy, R.MIC_D / 2, P.KIT_MIC_D0, P.KIT_MIC_D0 + R.MIC_T)
    refs["SHT31-D"] = rh_ref()                         # v0.12: in the housing's bottom wall (G2)
    return refs


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


def kit_bodies(build="pcb"):
    """every printed part and reference body of the kit, at rest (also used by the wiring and the plug housing)."""
    pbody, prim = L.plate_parts("S")
    bodies = {"key shell": L.key_shell(), "switch plate": L.switch_plate(build), "collar": L.collar(),
              "plate": fuse([pbody, prim]), "chassis (kit)": kit_chassis(build)}
    if build == "pcb":
        bodies["radar cage"] = L.radar_cage()
    else:
        bodies["back carrier"] = back_carrier()
    refs = L.ref_bodies("S", build)
    keys = ["touch board", "antenna chip", "MX switch 1", "MX switch 2", "speaker 2030", "LED 1", "LED 2", "LED 3", "LED 4",
            "cable loop", "speaker back foam"]
    if build == "pcb":
        keys += ["hub", "LD2410C", "LD2410C header", "LD2410C front parts", "LD2410C edge parts", "LD2410C pin stubs"]
    for k in keys:
        bodies[k] = refs[k]
    bodies.update(kit_refs(build))
    return bodies


def build_kit(build="pcb"):
    tag = f"kit-{build}"
    print(f"\n==================== RoomKey KIT, {build} build — parts v{P.VERSION} ====================")
    bodies = kit_bodies(build)
    carrier = "radar cage" if build == "pcb" else "back carrier"
    ch, bc = bodies["chassis (kit)"], bodies[carrier]
    for nm in ("chassis (kit)", carrier):
        bb = bodies[nm].BoundBox
        print(f"  {nm:15s} valid {bodies[nm].isValid()} | solids {len(bodies[nm].Solids)} | {bb.XLength:.1f} × {bb.YLength:.1f} × "
              f"{bb.ZLength:.1f} | {bodies[nm].Volume/1000:.2f} cm³")
    ex = {frozenset(("MX switch 1", "switch plate")), frozenset(("MX switch 2", "switch plate")),
          frozenset(("speaker 2030", "speaker back foam")), frozenset(("chassis (kit)", "speaker back foam"))}
    ex |= L.HUB_EXEMPT if build == "pcb" else {frozenset(("MAX98357A", "back carrier"))}   # amp holes on the carrier pins
    # v0.9.2: the radar's front parts are no longer exempt — they must clear the carrier (the board sits on ledges)
    if build == "discrete":
        webs = carrier_webs(bc)
        print(f"  {carrier}: thinnest web {min(webs.values()):.2f} (rule ≥ {P.KIT_MIN_WEB}) | " +
              ", ".join(f"{k} {v:.2f}" for k, v in webs.items()))
        # v0.9.2: the radar tray must be a CLOSED frame — along the parts edge, where the cable-loop keep-out takes the
        # tray wall, the plate strip under the board must run through (v0.9.1 lost it and the tray became an open "C")
        rx0, rx1, ry0, ry1, _ = P.KIT_RADAR
        c0 = P.KIT_CARRIER_D[0]
        ly0, ly1 = P.LOOP_Y
        ys = [ly0 - 0.5 + i * 0.5 for i in range(int((ly1 - ly0) / 0.5) + 2)]
        gaps_ = [y for y in ys if not bc.isInside(V(rx1 - 1.1, y, -(c0 + 0.75)), 0.001, True)]
        print(f"  radar tray frame: {'CLOSED' if not gaps_ else 'OPEN at y ' + ', '.join(f'{y:.1f}' for y in gaps_)}")
        assert not gaps_, "radar tray frame is open along the parts edge (strip under the board missing)"
    else:
        webs = {}
    col = L.check_state(bodies, "kit, rest", ex)
    # key pressed / rocked with the kit parts present
    kb = dict(bodies)
    for nm in ("key shell", "touch board", "antenna chip"):
        kb[nm] = L.key_pressed(bodies[nm])
    col += L.check_state(kb, "kit, key pressed", ex, only=("key shell", "touch board", "antenna chip"))
    if build == "pcb":
        pairs = (("LD2410C front parts", "radar cage"), ("LD2410C edge parts", "radar cage"),
                 ("LD2410C pin stubs", "radar cage"), ("LD2410C", "radar cage"), ("LD2410C", "MX switch 2"),
                 ("radar cage", "hub"), ("LD2410C", "hub"), ("LD2410C header", "hub"), ("radar cage", "MX switch 2"),
                 ("radar cage", "switch plate"), ("radar cage", "chassis (kit)"), ("hub", "chassis (kit)"),
                 ("hub", "switch plate"), ("hub", "speaker 2030"))
    else:
        pairs = (("LD2410C front parts", "back carrier"), ("LD2410C edge parts", "back carrier"),
                 ("LD2410C pin stubs", "back carrier"), ("MAX98357A", "cable loop"), ("back carrier", "cable loop"),
                 ("back carrier", "speaker 2030"), ("back carrier", "chassis (kit)"), ("LD2410C", "MX switch 2"),
                 ("INMP441", "chassis (kit)"), ("INMP441", "switch plate"), ("INMP441", "LD2410C"))
    pairs += (("chassis (kit)", "switch plate"), ("chassis (kit)", "plate"), ("SHT31-D", "chassis (kit)"))
    gaps = {f"{a} ↔ {b}": round(L.min_gap(bodies[a], bodies[b]), 3) for a, b in pairs}
    print(f"  collisions: {len(col)}")
    for c_ in col:
        print("    COLLISION", c_)
    for k, val in gaps.items():
        print(f"    gap {k:45s} {val}")
    ch.exportStep(os.path.join(L.OUT, f"{tag}_chassis.step"))                 # the glued assembly (reference)
    for i, (lab, part) in enumerate(zip(("front", "flange", "rear"), L.chassis_parts(ch, build)), 1):   # three prints
        L.export(part, f"{tag}_chassis_{i}_{lab}", "front_down")
        L.ceilings(part, f"{tag}_chassis_{i}_{lab}", "front_down")
    L.export(bodies["switch plate"], f"{tag}_switch_plate", "front_down")
    L.ceilings(bodies["switch plate"], f"{tag}_switch_plate", "front_down")
    cname = carrier.replace(" ", "_")
    how = "back_down" if build == "pcb" else "front_down"
    L.export(bc, f"{tag}_{cname}", how)
    L.ceilings(bc, f"{tag}_{cname}", how)
    if build == "pcb":
        hd = hub_dummy()
        L.export(hd, f"{tag}_hub_dummy", "front_down")
        L.ceilings(hd, f"{tag}_hub_dummy", "front_down")
    import Part
    Part.makeCompound(list(bodies.values())).exportStep(os.path.join(L.OUT, f"{tag}-v{P.VERSION}_assembly.step"))
    L.write_stl(Part.makeCompound([bodies[k] for k in ("key shell", "switch plate", "collar", "plate", "chassis (kit)", carrier)]),
                os.path.join(L.OUT, f"{tag}-v{P.VERSION}_printed-assembly.stl"), 0.05, 0.4)
    if webs and min(webs.values()) < P.KIT_MIN_WEB:
        print(f"  ERROR {carrier} web below {P.KIT_MIN_WEB}: the slicer will open it")
    with open(os.path.join(L.OUT, f"{tag}-v{P.VERSION}_check.json"), "w", encoding="utf-8") as f:
        json.dump({"collisions": col, "gaps": gaps, "webs": webs}, f, indent=1, ensure_ascii=False)
