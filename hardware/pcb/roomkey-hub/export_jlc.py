#!/usr/bin/env python3
"""RoomKey hub: the JLCPCB order files (Gerbers + drill zip, BOM, CPL) into output/jlcpcb/.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/export_jlc.py

Board: 4 layers, 1.6 mm, all assembled parts on the BOTTOM (economic PCBA, one side). The BOM lists every part with an
LCSC number (DNP parts, test pads, holes and the key-wire holes J4 are not assembled). Check every part's position and
rotation in JLCPCB's assembly preview before paying: some footprints differ in KiCad's and JLCPCB's zero rotation.
"""
import csv
import glob
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
CLI = r"C:/Program Files/KiCad/10.0/bin/kicad-cli.exe"
PCB = os.path.join(HERE, "hub", "roomkey-hub.kicad_pcb")
SCH = os.path.join(HERE, "hub", "roomkey-hub.kicad_sch")
OUT = os.path.join(HERE, "output", "jlcpcb")
LAYERS = "F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts"


def run(*args):
    r = subprocess.run([CLI] + list(args), capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(r.stdout + r.stderr)


def main():
    gdir = os.path.join(OUT, "gerbers")
    os.makedirs(gdir, exist_ok=True)
    for f in glob.glob(os.path.join(gdir, "*")):
        os.remove(f)
    run("pcb", "export", "gerbers", "--layers", LAYERS, "--subtract-soldermask", "--check-zones", "-o", gdir + "/", PCB)
    run("pcb", "export", "drill", "--format", "excellon", "--excellon-separate-th", "-o", gdir + "/", PCB)
    zpath = os.path.join(OUT, "roomkey-hub_gerbers.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(os.listdir(gdir)):
            z.write(os.path.join(gdir, f), f)

    # BOM: from the schematic (the LCSC field), JLCPCB columns
    tmp = os.path.join(OUT, "_bom_raw.csv")
    run("sch", "export", "bom", "--fields", "Value,Reference,Footprint,LCSC,${DNP}", "--group-by", "Value,LCSC,Footprint",
        "--exclude-dnp", "-o", tmp, SCH)
    rows = list(csv.DictReader(open(tmp, encoding="utf-8")))
    os.remove(tmp)
    bom = [r for r in rows if r["LCSC"].strip()]
    with open(os.path.join(OUT, "roomkey-hub_bom.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
        for r in bom:
            w.writerow([r["Value"], r["Reference"], r["Footprint"].split(":")[-1], r["LCSC"]])
    assembled = set()
    for r in bom:
        for part in r["Reference"].split(","):
            part = part.strip()
            if "-" in part and part[0].isalpha():        # "C4-C6" style ranges
                a, b = part.split("-")
                pre = a.rstrip("0123456789")
                for n in range(int(a[len(pre):]), int(b[len(pre):]) + 1):
                    assembled.add(pre + str(n))
            else:
                assembled.add(part)

    # CPL: KiCad's position file → JLCPCB columns, only the assembled parts
    tmp = os.path.join(OUT, "_pos_raw.csv")
    run("pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--exclude-dnp", "-o", tmp, PCB)
    pos = list(csv.DictReader(open(tmp, encoding="utf-8")))
    os.remove(tmp)
    with open(os.path.join(OUT, "roomkey-hub_cpl.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        n = 0
        for p in pos:
            if p["Ref"] in assembled:
                w.writerow([p["Ref"], p["PosX"] + "mm", p["PosY"] + "mm", "Top" if p["Side"] == "top" else "Bottom",
                            p["Rot"]])
                n += 1
    missing = assembled - {p["Ref"] for p in pos}
    print("gerbers: %s (%d files)" % (zpath, len(os.listdir(gdir))))
    print("BOM: %d lines, %d parts; CPL: %d parts%s" % (len(bom), len(assembled), n,
                                                         "; NOT IN CPL: %s" % sorted(missing) if missing else ""))


if __name__ == "__main__":
    sys.exit(main())
