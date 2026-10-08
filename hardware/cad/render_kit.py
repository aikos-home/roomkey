"""Render real FreeCAD views of the kit v0.7 (prototype, WIP) to hardware/docs/img/ — run inside the FreeCAD GUI:
    /Applications/FreeCAD.app/Contents/MacOS/FreeCAD hardware/cad/render_kit.py
(with RENDER_QUIT=1 it quits when done). Opens hardware/models/kit-v<insert VERSION>_ansicht.FCStd (made by view_kit.py).
"""
import os
import sys
import time

import FreeCAD as App
import FreeCADGui as Gui

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    os.path.join(os.getcwd(), "hardware", "cad")
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import insert_params as P  # noqa: E402
SRC = os.path.join(ROOT, "models", os.environ.get("KIT_VIEW_NAME", f"kit-v{P.VERSION}_ansicht.FCStd"))
OUT = os.path.join(ROOT, "docs", "img")
os.makedirs(OUT, exist_ok=True)
W, H = 1800, 1350

LOG = os.environ.get("RENDER_LOG")
doc = view = None
objs = {}


def log(*a):
    print(*a)
    if LOG:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(" ".join(str(x) for x in a) + "\n")


def show(names=None, hide=()):
    for n, o in objs.items():
        vis = (names is None or n in names or any(n.startswith(p) for p in names)) and \
              not any(n.startswith(h) for h in hide)
        o.ViewObject.Visibility = vis


def cam(eye, up=(0, 1, 0)):
    """camera looking at the model from direction `eye` (model axes: x right, y up, +z out of the wall), y kept upright"""
    z = App.Vector(*eye).normalize()                 # the camera looks along its −z, so its +z points back to the eye
    x = App.Vector(*up).cross(z).normalize()
    y = z.cross(x)
    m = App.Matrix(x.x, y.x, z.x, 0, x.y, y.y, z.y, 0, x.z, y.z, z.z, 0, 0, 0, 0, 1)
    view.setCameraOrientation(App.Placement(m).Rotation)
    view.fitAll()


def strip_png(path):
    """drop FreeCAD's text chunks (title = the local file path, author, camera XML): keep only the image chunks"""
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
    """offscreen renders on macOS sometimes come back empty (all white): retry until the PNG has content"""
    path = os.path.join(OUT, name)
    for i in range(tries):
        Gui.updateGui()
        QtGui.QApplication.processEvents()
        time.sleep(0.4)
        view.saveImage(path, W, H, "White")
        if os.path.getsize(path) > 25000:
            strip_png(path)
            log("wrote", name, "try", i + 1, os.path.getsize(path))
            return
    log("EMPTY", name)


def run():
    """runs once the GUI event loop is up (a script passed on the command line runs before the 3D view can draw)"""
    global doc, view, objs
    try:
        doc = App.openDocument(SRC)
        Gui.updateGui()
        view = Gui.getDocument(doc.Name).activeView()
        objs = {o.Name: o for o in doc.Objects if hasattr(o, "Shape")}
        log("objects", len(objs))
        shots()
        log("RENDER DONE")
    except Exception as e:  # noqa: BLE001
        log("RENDER FAILED", repr(e))
    finally:
        if os.environ.get("RENDER_QUIT"):
            os._exit(0)


def shots():
    wall = ("Uebungsdose", "Draht_", "Kabelbogen")
    # 1 straight on: what you see on the wall (frame opaque for this one)
    show(None, hide=wall)
    fr = objs["Rahmen_JungAS500"].ViewObject
    t0, fr.Transparency = fr.Transparency, 0
    cam((0, 0, 1))
    shot(f"kit-v{P.VERSION}_face.png")
    fr.Transparency = t0
    # 2 front 3/4 in the practice box (box transparent)
    show(None, hide=("Draht_", "Kabelbogen"))
    cam((-0.65, 0.45, 1))
    shot(f"kit-v{P.VERSION}_front.png")
    # 3 rear 3/4 without the box: back carrier with radar + amplifier, mic, speaker, switches
    show(None, hide=wall)
    cam((0.75, 0.5, -1))
    shot(f"kit-v{P.VERSION}_rear-parts.png")
    # 4 the same with all 41 wires
    show(None, hide=("Uebungsdose", "Kabelbogen"))
    cam((0.75, 0.5, -1))
    shot(f"kit-v{P.VERSION}_wiring.png")
    # 5 the frame from behind and below: humidity sensor flat under its bottom border
    show(("Rahmen_JungAS500", "Feuchtesensor"))
    cam((0.35, -0.55, -1))
    shot("frame_humidity-sensor.png")
    # 6 the rigid key from behind: fixed / floating stem sockets, stop bosses, header slots, the two switches
    show(("Tastenschale", "MX_", "Touch_Board"))
    cam((0.6, 0.55, -1))
    shot(f"key-v{P.VERSION}_rear.png")


from PySide import QtCore, QtGui  # noqa: E402

QtCore.QTimer.singleShot(4000, run)
