"""RoomKey KIT (prototype, WIP: whole RoomKey in one box; bench power from a lab supply at 5 V) — both builds.

Run headless from the repo root (ROOMKEY_BUILD=pcb or discrete builds only that one):
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_kit.py', encoding='utf-8').read())"
Writes hardware/models/kit-<build>_* (.step + _print.stl), kit-<build>-v<VERSION>_assembly.step and _check.json, and
checks the wiring of each build (wiring_pcb.py / wiring_lib.py).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402

for build in ([os.environ["ROOMKEY_BUILD"]] if os.environ.get("ROOMKEY_BUILD") else K.BUILDS):
    K.build_kit(build)
    if build == "pcb":
        import wiring_pcb  # noqa: E402
        wiring_pcb.check()
    else:
        import wiring_lib  # noqa: E402
        wiring_lib.build_wiring()
