"""RoomKey DESK REPLICA (prototype only: never in a wall, never on 230 V; USB 5 V): two coupled flush-box replicas,
2-gang frame, sensor cover + carrier for the owner's breakout boards. The top box takes the unchanged wall insert.

Run headless from the repo root:
    PYTHONIOENCODING=utf-8 /Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd -c "exec(open('hardware/cad/make_desk_replica.py', encoding='utf-8').read())"
Writes hardware/models/desk_wall_block, desk_frame_2x, desk_sensor_carrier, desk_sensor_face (.step + _print.stl),
desk-replica_assembly.step, desk-replica_printed-assembly.stl, desk-replica_check.json.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import desk_lib as D  # noqa: E402

D.build()
