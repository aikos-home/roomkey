"""RoomKey PRACTICE BOX (prototype only: never in a wall, never on 230 V; bench power from a lab supply): one flush-box
replica with open back + a 1-gang frame (Jung AS 500 size). The RoomKey kit (the wall insert) slides in.

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_practice_box.py', encoding='utf-8').read())"
Writes hardware/models/practice_box, practice_frame_1x (.step + _print.stl), practice-box_check.json.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import desk_lib as D  # noqa: E402

D.build_practice()
