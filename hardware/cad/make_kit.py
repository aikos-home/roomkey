"""RoomKey KIT v0.7 (prototype, WIP: whole RoomKey in one box; bench power from a lab supply at 5 V).

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_kit.py', encoding='utf-8').read())"
Writes hardware/models/kit_chassis, kit_back_carrier (.step + _print.stl), kit-v<VERSION>_assembly.step, kit-v<VERSION>_check.json (VERSION = insert_params.VERSION, the parts' version).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import kit_lib as K  # noqa: E402

K.build_kit()
