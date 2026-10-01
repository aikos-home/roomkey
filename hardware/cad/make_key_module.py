"""RoomKey key module (DRAFT, shared by Variant L and S): keycap shell with side skirts (roll limit) and a wire channel,
switch plate, light-guide collar.

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_key_module.py', encoding='utf-8').read())"
Writes hardware/models/key_shell, switch_plate, collar (.step + _print.stl).
Geometry: insert_params.py / roomkey_params.py only.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import insert_lib as L  # noqa: E402

L.build_key_module()
