"""RoomKey PLUG-IN HOUSING ("Steckdosen-RoomKey", v0.4, WIP, not certified): the RoomKey (kit, both builds) in a 64 × 64
housing that plugs into a SCHUKO socket; 230 V only inside an unmodified, certified plug-in USB charger. RoomKey is built
only this way (owner 2026-10-31). Geometry: insert_params.py section 8.

Run headless from the repo root (ROOMKEY_HUB_STEP = the hub STEP if it is not in this checkout):
    PYTHONIOENCODING=utf-8 FreeCADCmd -c "exec(open('hardware/cad/make_plug.py', encoding='utf-8').read())"
Writes hardware/models/plug-<build>_skin (the resin skin; also printable), _tunnel, _column (print 4), _box (G2)
(.step + _print.stl) and plug-<build>-v0.4_assembly.step / _check.json for build = pcb and discrete, plus the TPU rings
for both: plug_grip_1…3 (coupons), plug_foot, and the probe sleeve.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(os.getcwd(), "hardware", "cad")
sys.path.insert(0, HERE)
import plug_lib as G  # noqa: E402

for build in G.K.BUILDS:
    G.build_plug(build)
G.export_rings()
