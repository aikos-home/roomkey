"""RoomKey PLUG-IN HOUSING ("Steckdosen-RoomKey", v0.3, WIP, not certified): the unchanged RoomKey (kit, both builds) in
a 1-gang-frame-sized housing that plugs into a SCHUKO socket; 230 V only inside an unmodified, certified plug-in USB
charger. Geometry: insert_params.py section 8.

Run headless from the repo root (ROOMKEY_HUB_STEP = the hub STEP if it is not in this checkout):
    PYTHONIOENCODING=utf-8 FreeCADCmd -c "exec(open('hardware/cad/make_plug.py', encoding='utf-8').read())"
Writes hardware/models/plug-<build>_shell, plug-<build>_box (.step + _print.stl) and plug-<build>-v0.3_assembly.step /
_check.json for build = pcb and discrete, plus the TPU rings for both: plug_grip_1…3 (coupons), plug_foot.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import plug_lib as G  # noqa: E402

for build in G.K.BUILDS:
    G.build_plug(build)
G.export_rings()
