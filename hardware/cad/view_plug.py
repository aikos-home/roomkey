"""Open the RoomKey PLUG-IN HOUSING (concept v0.1, WIP) in the FreeCAD GUI: shell, box, charger, USB plug and wires,
the unchanged kit (PCB build) and a reference SCHUKO socket in a piece of wall — named, coloured, grouped — plus a
section through x = 0. Saves hardware/models/plug-v0.1_ansicht.FCStd; with PLUG_RENDER=1 it also renders the images
to RENDER_OUT (default hardware/docs/img) and quits.

Run (opens FreeCAD):  FreeCAD hardware/cad/view_plug.py   (env ROOMKEY_HUB_STEP as for make_plug.py)
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import FreeCAD as App  # noqa: E402
import plug_lib as G  # noqa: E402

K, L, P, W = G.K, G.L, G.P, G.W
IVORY, DARK, GREY = (0.95, 0.93, 0.85), (0.18, 0.18, 0.18), (0.55, 0.55, 0.55)
OUT = os.environ.get("RENDER_OUT") or os.path.join(os.path.dirname(HERE), "docs", "img")
LOG = os.environ.get("RENDER_LOG")
WPX, HPX = 1800, 1350
W.supply_route = G.supply_route            # the kit's lab-supply pigtail becomes the USB plug → J1 pair
pbody, prim = L.plate_parts("S")
refs = L.ref_bodies("S", "pcb")
kr = K.kit_refs("pcb")
_parts = {}


def part(i):
    if "ch" not in _parts:
        _parts["ch"] = L.chassis_parts(K.kit_chassis("pcb"), "pcb")
    return _parts["ch"][i]


# name, builder, colour, transparency %, group, in the x = 0 section?
ITEMS = [
    ("G1_Gehaeuse_Rahmen", G.shell, (0.97, 0.97, 0.97), 0, "Gehäuse", True),
    ("G2_Dose_Netzteilfach", G.box_g2, (0.95, 0.55, 0.2), 0, "Gehäuse", True),
    ("Netzteil_revolt_PX8884", G.charger, (0.92, 0.92, 0.9), 0, "Netzteil", True),
    ("USB_A_Stecker", G.usb_plug, (0.35, 0.35, 0.38), 0, "Netzteil", True),
    ("Platte", lambda: pbody, IVORY, 0, "Druckteile", True),
    ("Platte_Leuchtrand", lambda: prim, (0.85, 0.92, 1.0), 40, "Druckteile", True),
    ("Tastenschale_starr", L.key_shell, IVORY, 0, "Druckteile", True),
    ("Leuchtring", L.collar, (0.85, 0.92, 1.0), 40, "Druckteile", True),
    ("Schalterplatte", lambda: L.switch_plate("pcb"), GREY, 0, "Druckteile", True),
    ("Chassis_1_vorne", lambda: part(0), DARK, 0, "Druckteile", True),
    ("Chassis_2_Flansch", lambda: part(1), (0.3, 0.33, 0.45), 0, "Druckteile", True),
    ("Chassis_3_hinten", lambda: part(2), (0.42, 0.25, 0.22), 0, "Druckteile", True),
    ("Radar_Wanne", L.radar_tray, (0.75, 0.75, 0.8), 0, "Druckteile", True),
    ("Touch_Board", lambda: refs["touch board"], (0.05, 0.05, 0.05), 0, "Bauteile", True),
    ("Hub_Platine", lambda: refs["hub"], (0.1, 0.45, 0.2), 0, "Bauteile", True),
    ("MX_oben", lambda: refs["MX switch 1"], (0.45, 0.3, 0.2), 0, "Bauteile", True),
    ("MX_unten", lambda: refs["MX switch 2"], (0.45, 0.3, 0.2), 0, "Bauteile", True),
    ("Lautsprecher", lambda: refs["speaker 2030"], (0.1, 0.1, 0.1), 0, "Bauteile", True),
    ("Radar_LD2410C", lambda: refs["LD2410C"], (0.1, 0.25, 0.75), 0, "Bauteile", True),
    ("Radar_Stiftleiste", lambda: refs["LD2410C header"], (0.05, 0.05, 0.05), 0, "Bauteile", True),
    ("Feuchtesensor_SHT31D_im_Rahmen", lambda: kr["SHT31-D"], (0.55, 0.2, 0.6), 0, "Bauteile", True),
    ("Kabelbogen_Taste", lambda: refs["cable loop"], (0.9, 0.4, 0.1), 50, "Bauteile", True),
    ("Steckdose_JungAS500_Referenz", G.socket_ref, (0.99, 0.99, 0.97), 0, "Wand", True),
    ("Wand_Referenz", G.wall_ref, (0.82, 0.8, 0.76), 60, "Wand", False),
]
for no, a, b, sig, col, rgb, rt, dia, _ in W.wires():
    ITEMS.append((f"Draht_{no:02d}", (lambda rt=rt, dia=dia: W.wire_solid(rt(), dia)), rgb, 0, "Verkabelung", False))


def log(*a):
    print(*a)
    if LOG:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(" ".join(str(x) for x in a) + "\n")


doc = App.newDocument("RoomKey_Steckdose_v0_1")
groups = {}
for g in ("Gehäuse", "Netzteil", "Druckteile", "Bauteile", "Verkabelung", "Wand", "Schnitt"):
    groups[g] = doc.addObject("App::DocumentObjectGroup", g.replace("ä", "ae"))
    groups[g].Label = g
half = L.box(0.0, 120.0, -120.0, 120.0, -40.0, 120.0)        # keeps x ≥ 0: the section looks from +x at the cut face
for name, build, col, tr, grp, sec in ITEMS:
    shape = build()
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    groups[grp].addObject(obj)
    if App.GuiUp:
        obj.ViewObject.ShapeColor = col
        obj.ViewObject.Transparency = tr
    if sec:
        s = shape.common(half)
        if s.Volume > 1e-3:
            so = doc.addObject("Part::Feature", "Schnitt_" + name)
            so.Shape = s
            groups["Schnitt"].addObject(so)
            if App.GuiUp:
                so.ViewObject.ShapeColor = col
                so.ViewObject.Transparency = 0
                so.ViewObject.Visibility = False
EXPLODE = (("G1_Gehaeuse_Rahmen", 75.0), ("G2_Dose_Netzteilfach", -50.0), ("Netzteil_revolt_PX8884", -105.0),
           ("USB_A_Stecker", -105.0))          # exploded view: shift along Z (+ = into the room)
for name, dz in EXPLODE:
    src = doc.getObject(name)
    eo = doc.addObject("Part::Feature", "Explo_" + name)
    s = src.Shape.copy()
    s.translate(App.Vector(0, 0, dz))
    eo.Shape = s
    groups["Schnitt"].addObject(eo)
    if App.GuiUp:
        eo.ViewObject.ShapeColor = src.ViewObject.ShapeColor
        eo.ViewObject.Visibility = False
doc.recompute()
SRC = os.path.join(os.path.dirname(HERE), "models", f"{G.TAG}_ansicht.FCStd")
doc.saveAs(SRC)
log("plug view saved:", SRC)

if App.GuiUp:
    import FreeCADGui as Gui
    from PySide import QtCore, QtGui
    view = Gui.activeDocument().activeView()
    objs = {o.Name: o for o in doc.Objects if hasattr(o, "Shape")}

    def show(names=None, hide=()):
        for n, o in objs.items():
            vis = (names is None or any(n.startswith(p) for p in names)) and not any(n.startswith(h) for h in hide)
            o.ViewObject.Visibility = vis

    def cam(eye, up=(0, 1, 0)):
        z = App.Vector(*eye).normalize()
        x = App.Vector(*up).cross(z).normalize()
        y = z.cross(x)
        m = App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)
        view.setCameraOrientation(App.Placement(m).Rotation)
        view.fitAll()

    def strip_png(path):
        import struct
        keep = (b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND")
        d = open(path, "rb").read()
        out, i = [d[:8]], 8
        while i < len(d):
            n = struct.unpack(">I", d[i:i + 4])[0]
            if d[i + 4:i + 8] in keep:
                out.append(d[i:i + 12 + n])
            i += 12 + n
        with open(path, "wb") as f:
            f.write(b"".join(out))

    def shot(name, tries=6):
        path = os.path.join(OUT, name)
        for i in range(tries):
            Gui.updateGui()
            QtGui.QApplication.processEvents()
            time.sleep(0.4)
            view.saveImage(path, WPX, HPX, "White")
            if os.path.getsize(path) > 8000:           # a plain side silhouette is only ≈ 15 kB
                strip_png(path)
                log("wrote", name, os.path.getsize(path))
                return
        log("EMPTY", name)

    def shots():
        os.makedirs(OUT, exist_ok=True)
        wall = ("Steckdose_", "Wand_")
        inner = ("Draht_", "Kabelbogen", "Schnitt_", "Explo_")
        # 1 face on: the same front as the flush-mounted RoomKey
        show(None, hide=wall + inner)
        cam((0, 0, 1))
        shot(f"{G.TAG}_vorne.png")
        # 2 plugged into the socket, 3/4 from the front left
        show(None, hide=inner)
        cam((-0.7, 0.35, 1))
        shot(f"{G.TAG}_an-der-wand.png")
        # 3 side view on the wall: how far it stands out
        cam((1, 0, 0))
        shot(f"{G.TAG}_seite.png")
        # 4 section x = 0, looking at the cut face from the left: key, insert, U-loop, USB plug, charger in the sleeve,
        #   socket recess (the kept half is x ≥ 0)
        show(("Schnitt_",), hide=("Schnitt_Wand", "Explo_"))
        objs["Wand_Referenz"].ViewObject.Visibility = True
        cam((-1, 0.1, 0.06))
        shot(f"{G.TAG}_schnitt.png")
        # 5 the back off the wall: back plate, sleeve, charger pins, the 4 screws' countersinks
        show(None, hide=wall + inner + ("Explo_",))
        cam((0.55, 0.4, -1))
        shot(f"{G.TAG}_hinten.png")
        # 6 open: shell and box hidden — the insert with the USB plug, its two wires and the charger behind
        show(None, hide=wall + ("G1_", "G2_", "Kabelbogen", "Schnitt_", "Explo_"))
        cam((0.8, 0.45, -0.6))
        shot(f"{G.TAG}_offen.png")
        # 7 exploded: shell forward, box and charger back (assembly from behind)
        show(("Explo_", "Platte", "Tastenschale", "Leuchtring", "Schalterplatte", "Chassis_", "Radar_", "Touch_",
              "Hub_", "MX_", "Lautsprecher", "Feuchtesensor"))
        cam((-1, 0.35, 0.5))
        shot(f"{G.TAG}_explosion.png")

    def run():
        try:
            shots()
            log("RENDER DONE")
        except Exception as e:  # noqa: BLE001
            log("RENDER FAILED", repr(e))
        finally:
            if os.environ.get("RENDER_QUIT"):
                os._exit(0)

    if os.environ.get("PLUG_RENDER"):
        QtCore.QTimer.singleShot(4000, run)
    else:
        view.viewIsometric()
        Gui.SendMsgToActiveView("ViewFit")
