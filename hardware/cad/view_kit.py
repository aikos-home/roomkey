"""Open the RoomKey kit (prototype, WIP) in the FreeCAD GUI to LOOK at it: the printed parts, the electronics and every
wire — named, coloured, grouped (the plug-in housing round it: view_plug.py). ROOMKEY_BUILD = pcb (default) or discrete.

Run (opens FreeCAD):  ROOMKEY_BUILD=pcb /Applications/FreeCAD.app/Contents/MacOS/FreeCAD hardware/cad/view_kit.py
Saves hardware/models/kit-<build>-v<VERSION>_ansicht.FCStd (open that file directly next time; render_kit.py makes the
README images from it).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import FreeCAD as App  # noqa: E402
import kit_lib as K  # noqa: E402
BUILD = os.environ.get("ROOMKEY_BUILD", "pcb")
if BUILD == "pcb":
    import wiring_pcb as W  # noqa: E402
else:
    import wiring_lib as W  # noqa: E402

L, P = K.L, K.P
IVORY, DARK, GREY = (0.95, 0.93, 0.85), (0.18, 0.18, 0.18), (0.55, 0.55, 0.55)
# name, shape builder, colour, transparency %, group
pbody, prim = L.plate_parts("S")
refs = L.ref_bodies("S", BUILD)
kr = K.kit_refs(BUILD)
radar = refs if BUILD == "pcb" else kr
_parts = {}


def part(kind, i):
    """v0.10 split prints, built once: chassis front / flange / rear."""
    if kind not in _parts:
        _parts[kind] = L.chassis_parts(K.kit_chassis(BUILD), BUILD)
    return _parts[kind][i]


ITEMS = [
    ("Platte", lambda: pbody, IVORY, 0, "Druckteile"),
    ("Platte_Leuchtrand", lambda: prim, (0.85, 0.92, 1.0), 40, "Druckteile"),
    ("Tastenschale_starr", L.key_shell, IVORY, 0, "Druckteile"),
    ("Leuchtring", L.collar, (0.85, 0.92, 1.0), 40, "Druckteile"),
    ("Schalterplatte", lambda: L.switch_plate(BUILD), GREY, 0, "Druckteile"),
    ("Chassis_1_vorne", lambda: part("chassis", 0), DARK, 0, "Druckteile"),
    ("Chassis_2_Flansch", lambda: part("chassis", 1), (0.3, 0.33, 0.45), 0, "Druckteile"),
    ("Chassis_3_hinten", lambda: part("chassis", 2), (0.42, 0.25, 0.22), 0, "Druckteile"),

    ("Touch_Board", lambda: refs["touch board"], (0.05, 0.05, 0.05), 0, "Bauteile"),
    ("MX_oben", lambda: refs["MX switch 1"], (0.45, 0.3, 0.2), 0, "Bauteile"),
    ("MX_unten", lambda: refs["MX switch 2"], (0.45, 0.3, 0.2), 0, "Bauteile"),
    ("Lautsprecher", lambda: refs["speaker 2030"], (0.1, 0.1, 0.1), 0, "Bauteile"),
    ("Radar_LD2410C", lambda: radar["LD2410C"], (0.1, 0.25, 0.75), 0, "Bauteile"),
    ("Radar_Stiftleiste", lambda: radar["LD2410C header"], (0.05, 0.05, 0.05), 0, "Bauteile"),
    ("Radar_Chip_vorne", lambda: radar["LD2410C front parts"], (0.85, 0.65, 0.1), 0, "Bauteile"),
    ("Radar_Randbauteile_vorne", lambda: radar["LD2410C edge parts"], (0.9, 0.2, 0.2), 0, "Bauteile"),
    ("Radar_Stiftstummel_vorne", lambda: radar["LD2410C pin stubs"], (0.9, 0.5, 0.1), 0, "Bauteile"),
    ("Feuchtesensor_SHT31D_unten", lambda: kr["SHT31-D"], (0.55, 0.2, 0.6), 0, "Bauteile"),
    ("Kabelbogen_Taste", lambda: refs["cable loop"], (0.9, 0.4, 0.1), 50, "Bauteile"),
    ("LED_1", lambda: refs["LED 1"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("LED_2", lambda: refs["LED 2"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("LED_3", lambda: refs["LED 3"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("LED_4", lambda: refs["LED 4"], (1.0, 1.0, 1.0), 0, "Bauteile"),
]

if BUILD == "pcb":
    ITEMS += [("Radar_Kaefig", L.radar_cage, (0.75, 0.75, 0.8), 0, "Druckteile"),
              ("Hub_Platine", lambda: refs["hub"], (0.1, 0.45, 0.2), 0, "Bauteile")]
    for no, a, b, sig, col, rgb, rt, dia, _ in W.wires():      # v0.11: the wires that the hub PCB leaves
        ITEMS.append((f"Draht_{no:02d}", (lambda rt=rt, dia=dia: W.wire_solid(rt(), dia)), rgb, 0, "Verkabelung"))
else:
    ITEMS += [("Technik_Traeger", K.back_carrier, (0.75, 0.75, 0.8), 0, "Druckteile"),
              ("Verstaerker_MAX98357A", lambda: kr["MAX98357A"], (0.5, 0.15, 0.6), 0, "Bauteile"),
              ("Mikrofon_INMP441", lambda: kr["INMP441"], (0.15, 0.6, 0.2), 0, "Bauteile")]
    for no, a, b, sig, col, rgb in W.WIRES:                     # every wire of the self-wired kit
        ITEMS.append((f"Draht_{no:02d}", (lambda no=no, a=a, b=b: W.wire_solid(W.route(no, a, b))), rgb, 0, "Verkabelung"))

doc = App.newDocument(f"RoomKey_Bausatz_{BUILD}_v" + P.VERSION.replace(".", "_"))
groups = {}
for g in ("Druckteile", "Bauteile", "Verkabelung"):
    groups[g] = doc.addObject("App::DocumentObjectGroup", g.replace("ü", "ue"))
    groups[g].Label = g
for name, build, col, tr, grp in ITEMS:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = build()
    groups[grp].addObject(obj)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = col
        obj.ViewObject.Transparency = tr
doc.recompute()
out = os.path.join(os.path.dirname(HERE), "models", os.environ.get("KIT_VIEW_NAME", f"kit-{BUILD}-v{P.VERSION}_ansicht.FCStd"))
doc.saveAs(out)
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
print(f"RoomKey kit view ({BUILD} build, parts v{P.VERSION}) saved:", out)
if os.environ.get("KIT_VIEW_QUIT"):          # headless GUI run (QT_QPA_PLATFORM=offscreen): save with colours, then quit
    os._exit(0)
