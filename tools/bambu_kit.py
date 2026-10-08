# -*- coding: utf-8 -*-
"""Slice the RoomKey kit for a Bambu Lab A1 (+ AMS lite) into ready-to-print .gcode.3mf files — WIP, prototype kit.

Two nozzles (0.4 and 0.2), three plates each, two filaments:
  A  white PETG: plate, chassis front / flange / rear, switch plate, carrier — no supports
  B  white PETG: the key shell, tree supports from the build plate (support body PETG, support INTERFACE clear PLA —
     PLA does not bond to PETG, so the contact layers come off clean); no prime tower (the A1 purges each change into its waste chute)
  C  clear PLA: the light-guide collar
Precise and slow: 0.10 mm layers, outer walls 25 mm/s, first layer 15 mm/s, 3 walls.

Run (Windows, Bambu Studio installed):   python tools/bambu_kit.py
Paths can be overridden with BAMBU_CLI / BAMBU_PROFILES. The system presets are inheritance fragments: they are resolved
here (incl. the A1 "include" templates with the real start G-code) — passing them raw crashes the CLI without a message.
Writes hardware/print/bambu/roomkey-kit-v<VERSION>_<plate>_<nozzle>.gcode.3mf.
"""
import json
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hardware", "cad"))
import insert_params as P  # noqa: E402

CLI = os.environ.get("BAMBU_CLI", r"C:\Program Files\Bambu Studio\bambu-studio.exe")
BBL = os.environ.get("BAMBU_PROFILES", r"C:\Program Files\Bambu Studio\resources\profiles\BBL")
MODELS = os.path.join(ROOT, "hardware", "models")
OUT = os.path.join(ROOT, "hardware", "print", "bambu")
WORK = os.path.join(OUT, "_presets")          # resolved presets (not committed)

PLATES = {
    "A-petg": ["plate_S_print.stl", "kit_chassis_1_front_print.stl", "kit_chassis_2_flange_print.stl",
               "kit_chassis_3_rear_print.stl", "switch_plate_print.stl", "kit_back_carrier_print.stl"],
    "B-key": ["key_shell_print.stl"],
    "C-collar-pla": ["collar_print.stl"],
}
NOZZLES = {
    "0.4": ("Bambu Lab A1 0.4 nozzle", "0.12mm Fine @BBL A1", "Generic PETG @BBL A1", "Generic PLA @BBL A1"),
    "0.2": ("Bambu Lab A1 0.2 nozzle", "0.10mm Standard @BBL A1 0.2 nozzle", "Generic PETG @BBL A1 0.2 nozzle",
            "Generic PLA @BBL A1 0.2 nozzle"),
}
SLOW = {"layer_height": 0.10, "wall_loops": 3, "outer_wall_speed": 25, "inner_wall_speed": 40, "small_perimeter_speed": 20,
        "sparse_infill_speed": 50, "internal_solid_infill_speed": 45, "top_surface_speed": 30, "gap_infill_speed": 25,
        "bridge_speed": 15, "initial_layer_speed": 15, "initial_layer_infill_speed": 20, "support_speed": 40,
        "support_interface_speed": 25, "sparse_infill_density": "20%", "sparse_infill_pattern": "gyroid",
        "enable_support": 0}
KEY_SUPPORT = {"enable_support": 1, "support_type": "tree(auto)", "support_on_build_plate_only": 1,
               "support_filament": 1, "support_interface_filament": 2, "support_interface_not_for_body": 1,
               "support_top_z_distance": 0, "support_bottom_z_distance": 0, "support_interface_top_layers": 3,
               "support_interface_bottom_layers": 0, "support_interface_spacing": 0,
               "enable_prime_tower": 0}   # the A1 purges into its chute; a tower failed the G-code check (error 4)
COLOURS = {"PETG": "#FFFFFF", "PLA": "#EAF4FA"}     # white PETG, clear PLA

_index = {}
for root, _, files in os.walk(BBL):
    for f in files:
        if f.endswith(".json"):
            _index.setdefault(f[:-5], os.path.join(root, f))


def load(name):
    with open(_index[name], encoding="utf-8") as f:
        return json.load(f)


def resolve(name, depth=0):
    """flatten the "inherits" chain and mix in the "include" templates (A1 start / end / layer-change G-code)."""
    assert depth < 15, name
    d = load(name)
    base = resolve(d["inherits"], depth + 1) if d.get("inherits") else {}
    for inc in d.get("include", []):
        base.update({k: v for k, v in load(inc).items() if k not in ("name", "type", "from", "instantiation", "setting_id")})
    base.update({k: v for k, v in d.items() if k not in ("inherits", "include")})
    return base


def typed(old, new):
    """keep the preset's value shape: Bambu stores most values as strings, some as one-element lists."""
    v = str(new)
    return [v] if isinstance(old, list) else v


def write(name, kind, extra=None, tag=""):
    d = resolve(name)
    d.update({"from": "system", "is_custom_defined": "0", "name": name + tag, "type": kind})
    for k, v in (extra or {}).items():
        d[k] = typed(d.get(k, ""), v) if not isinstance(v, list) else v
    os.makedirs(WORK, exist_ok=True)
    p = os.path.join(WORK, (name + tag).replace("@", "at").replace(" ", "_") + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    return p


def slice_plate(nozzle, plate, files):
    machine, process, petg, pla = NOZZLES[nozzle]
    tag = f" RoomKey {plate}"
    m = write(machine, "machine")
    pr = dict(SLOW, print_settings_id=process + tag)
    if plate == "B-key":
        pr.update(KEY_SUPPORT)
    p = write(process, "process", pr, tag)
    fil = {"PETG": write(petg, "filament", {"filament_colour": [COLOURS["PETG"]], "default_filament_colour": [""]}),
           "PLA": write(pla, "filament", {"filament_colour": [COLOURS["PLA"]], "default_filament_colour": [""]})}
    mats = ["PLA"] if plate == "C-collar-pla" else (["PETG", "PLA"] if plate == "B-key" else ["PETG"])
    name = f"roomkey-kit-v{P.VERSION}_{plate}_{nozzle}nozzle.gcode.3mf"
    cmd = [CLI, "--load-settings", f"{m};{p}", "--load-filaments", ";".join(fil[x] for x in mats),
           "--load-filament-ids", ",".join("1" for _ in files), "--curr-bed-type", "Textured PEI Plate",
           "--orient", "0", "--arrange", "1", "--allow-mix-temp", "--slice", "0",
           "--export-3mf", name, "--outputdir", OUT] + [os.path.join(MODELS, f) for f in files]
    r = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
    out = os.path.join(OUT, name)
    ok = r.returncode == 0 and os.path.exists(out)
    info = ""
    if ok:
        z = zipfile.ZipFile(out)
        g = "".join(z.read(n).decode("utf-8", "ignore") for n in z.namelist() if n.endswith(".gcode"))
        assert "M1002 gcode_claim_action" in g, f"{name}: generic start G-code (A1 includes not resolved)"
        t = [ln for ln in g.splitlines() if ln.startswith("; total estimated time") or "model printing time" in ln][:1]
        info = (t[0] if t else "") + f" | tool changes {g.count(chr(10) + 'T1') + g.count(chr(10) + 'T0')}"
    print(f"  {'OK ' if ok else 'ERR'} {name}  {info}")
    if not ok:
        print(r.stdout[-1500:], r.stderr[-800:])
    return ok


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    res = [slice_plate(n, pl, fs) for n in NOZZLES for pl, fs in PLATES.items()]
    for f in os.listdir(OUT):                     # CLI by-products next to the .gcode.3mf files
        if f.endswith(".gcode") or f == "result.json":
            os.remove(os.path.join(OUT, f))
    sys.exit(0 if all(res) else 1)
