"""RoomKey wall insert (DRAFT, version = insert_params.VERSION). v0.11: ONE RoomKey (the owner, 2026-10-08), fixed plate, the
2 MX under the key are the only buttons. The code keeps the internal variant key "S".

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_insert.py', encoding='utf-8').read())"
Builds the printed parts (key shell, switch plate, collar, plate, chassis, radar tray), checks every body pair for
collisions at rest and with the key pressed and wobbled (with its stems), measures clearances (incl. antenna ↔ metal),
and writes hardware/models/*.step, *_print.stl, insert_assembly.step, insert_check.json and the section polylines for
tools/insert_drawings.py. insert_params.validate() must show 0 errors first.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_params as P  # noqa: E402
import insert_lib as L  # noqa: E402

errs, _, _ = P.validate("S", verbose=False)
if errs:
    raise SystemExit("insert_params.validate() has errors — fix them first:\n  " + "\n  ".join(errs))
L.build_variant("S")
