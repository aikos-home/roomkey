"""RoomKey FRONT STACK (WIP, version = insert_params.VERSION): key on its two MX switches, plate, collar, switch plate,
chassis and (PCB build) the radar cage, in the plug-in housing's front frame (its skin border and carrier tunnel).

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 FreeCADCmd -c "exec(open('hardware/cad/make_front.py', encoding='utf-8').read())"
Checks every body pair for collisions at rest, with the key pressed, wobbled and pulled and with MX2 off its nominal
place; measures clearances (incl. antenna ↔ metal); writes hardware/models/plate (.step, _print.stl + the body / glow-rim
STLs for a two-colour print), front_check.json and the section slices for tools/insert_wallcheck.py.
insert_params.validate() must show 0 errors first. The chassis and the radar cage are exported by make_kit.py.
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
