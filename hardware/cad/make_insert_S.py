"""RoomKey wall insert (DRAFT, version = insert_params.VERSION), Variant S (socket replacement: same printed parts; the plate reports to the ESP only (optionally fixed)).

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_insert_S.py', encoding='utf-8').read())"
Builds the printed parts (key shell, switch plate, collar, plate_S, chassis_S), checks every body pair for
collisions at rest, with the key pressed and wobbled (with its stems) and with the plate tipped at five press locations, measures clearances
(incl. antenna ↔ metal), and writes hardware/models/*.step, *_print.stl, insert-S_assembly.step,
insert-S_check.json and the section polylines for tools/insert_drawings.py.
insert_params.validate('S') must show 0 errors first.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_params as P  # noqa: E402
import insert_lib as L  # noqa: E402

errs, _, _ = P.validate("S", verbose=False)
if errs:
    raise SystemExit("insert_params.validate('S') has errors — fix them first:\n  " + "\n  ".join(errs))
L.build_variant("S")
