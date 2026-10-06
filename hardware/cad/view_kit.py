"""Open the RoomKey kit v0.7 (prototype, WIP) in the FreeCAD GUI to LOOK at it: practice box (transparent), 1-gang frame,
the insert, the back carrier with radar and amplifier, and the reference parts — named, coloured, grouped.

Run (opens FreeCAD):  /Applications/FreeCAD.app/Contents/MacOS/FreeCAD hardware/cad/view_kit.py
Saves hardware/models/kit-v0.7e_ansicht.FCStd (open that file directly next time; render_kit.py makes the README images
from it).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import FreeCAD as App  # noqa: E402
import kit_lib as K  # noqa: E402
import wiring_lib as W  # noqa: E402

L, D, P = K.L, K.D, K.P
IVORY, DARK, GREY = (0.95, 0.93, 0.85), (0.18, 0.18, 0.18), (0.55, 0.55, 0.55)
# name, shape builder, colour, transparency %, group
one = ((0.0, 0.0),)
pbody, prim = L.plate_parts("S")
refs = L.ref_bodies("S")
kr = K.kit_refs()
ITEMS = [
    ("Uebungsdose", lambda: D.wall_block(one), (0.95, 0.55, 0.2), 70, "Übungsdose"),
    ("Rahmen_JungAS500", lambda: D.frame_2x(one, with_rh=True), (0.97, 0.97, 0.97), 35, "Übungsdose"),
    ("Platte", lambda: pbody, IVORY, 0, "Druckteile"),
    ("Platte_Leuchtrand", lambda: prim, (0.85, 0.92, 1.0), 40, "Druckteile"),
    ("Tastenschale_starr", L.key_shell, IVORY, 0, "Druckteile"),
    ("Leuchtring", L.collar, (0.85, 0.92, 1.0), 40, "Druckteile"),
    ("Schalterplatte", L.switch_plate, GREY, 0, "Druckteile"),
    ("Chassis_Bausatz", lambda: K.kit_chassis("S"), DARK, 0, "Druckteile"),
    ("Technik_Traeger", K.back_carrier, (0.75, 0.75, 0.8), 0, "Druckteile"),
    ("Touch_Board", lambda: refs["touch board"], (0.05, 0.05, 0.05), 0, "Bauteile"),
    ("MX_oben", lambda: refs["MX switch 1"], (0.45, 0.3, 0.2), 0, "Bauteile"),
    ("MX_unten", lambda: refs["MX switch 2"], (0.45, 0.3, 0.2), 0, "Bauteile"),
    ("Lautsprecher", lambda: refs["speaker 2030"], (0.1, 0.1, 0.1), 0, "Bauteile"),
    ("Radar_LD2410C", lambda: kr["LD2410C"], (0.1, 0.25, 0.75), 0, "Bauteile"),
    ("Radar_Stiftleiste", lambda: kr["LD2410C header"], (0.05, 0.05, 0.05), 0, "Bauteile"),
    ("Radar_Chip_LED_vorne", lambda: kr["LD2410C front parts"], (0.85, 0.65, 0.1), 0, "Bauteile"),
    ("Radar_Randbauteile_vorne", lambda: kr["LD2410C edge parts"], (0.9, 0.2, 0.2), 0, "Bauteile"),
    ("Radar_Stiftstummel_vorne", lambda: kr["LD2410C pin stubs"], (0.9, 0.5, 0.1), 0, "Bauteile"),
    ("Verstaerker_MAX98357A", lambda: kr["MAX98357A"], (0.5, 0.15, 0.6), 0, "Bauteile"),
    ("Mikrofon_INMP441", lambda: kr["INMP441"], (0.15, 0.6, 0.2), 0, "Bauteile"),
    ("Feuchtesensor_SHT31D_im_Rahmen", lambda: kr["SHT31-D"], (0.55, 0.2, 0.6), 0, "Bauteile"),
    ("Kabelbogen_Taste", lambda: refs["cable loop"], (0.9, 0.4, 0.1), 50, "Bauteile"),
    ("LED_1", lambda: refs["LED 1"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("LED_2", lambda: refs["LED 2"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("LED_3", lambda: refs["LED 3"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("LED_4", lambda: refs["LED 4"], (1.0, 1.0, 1.0), 0, "Bauteile"),
    ("Schraube_links", lambda: refs["box screw L"], (0.8, 0.8, 0.8), 0, "Bauteile"),
    ("Schraube_rechts", lambda: refs["box screw R"], (0.8, 0.8, 0.8), 0, "Bauteile"),
]

doc = App.newDocument("RoomKey_Bausatz_v0_7")
groups = {}
for no, a, b, sig, col, rgb in W.WIRES:
    ITEMS.append((f"Draht_{no:02d}", (lambda no=no, a=a, b=b: W.wire_solid(W.route(no, a, b))), rgb, 0, "Verkabelung"))
for g in ("Übungsdose", "Druckteile", "Bauteile", "Verkabelung"):
    groups[g] = doc.addObject("App::DocumentObjectGroup", g.replace("ü", "ue"))
    groups[g].Label = g
for name, build, col, tr, grp in ITEMS:
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = build()
    if grp == "Verkabelung":
        w = [x for x in W.WIRES if f"Draht_{x[0]:02d}" == name][0]
        obj.Label = f"Draht {w[0]:02d} · {w[3]} · {w[4]}"
    groups[grp].addObject(obj)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = col
        obj.ViewObject.Transparency = tr
doc.recompute()
out = os.path.join(os.path.dirname(HERE), "models", os.environ.get("KIT_VIEW_NAME", "kit-v0.7e_ansicht.FCStd"))
doc.saveAs(out)
if App.GuiUp:
    import FreeCADGui as Gui
    Gui.activeDocument().activeView().viewIsometric()
    Gui.SendMsgToActiveView("ViewFit")
print("RoomKey kit v0.7 view saved:", out)
if os.environ.get("KIT_VIEW_QUIT"):          # headless GUI run (QT_QPA_PLATFORM=offscreen): save with colours, then quit
    os._exit(0)
