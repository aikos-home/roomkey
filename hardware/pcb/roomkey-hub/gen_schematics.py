#!/usr/bin/env python3
"""RoomKey hub PCB set: writes the KiCad schematics of the three boards and the project symbol library.

    "C:/Program Files/KiCad/10.0/bin/python.exe" hardware/pcb/roomkey-hub/gen_schematics.py

Boards (one KiCad project each, because KiCad has one PCB per project):
  hub/       the static hub in the flush box: 5 V input, protection, audio, mic, MX sockets, connectors
  sht-tail/  the SHT4x board in the frame's bottom border, on a Qwiic/STEMMA QT cable
  pogo/      the adapter that moves with the key: spring pins on the touch board's H1 pads -> 16-pin FFC

The parts tables below are the source while the schematics are drafted; the FFC pinout is defined once (FFC_PINS) and
used by both the hub and the pogo adapter. Every net is a label (or a power symbol) at a short wire stub, so each pin
shows its net's name. UUIDs are derived from names, so a rerun gives the same files. Positions are in grid units
(2.54 mm). The script also checks that no two texts or symbols overlap and that every named net reaches two pins.
"""
import copy
import math
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_SYM = os.environ.get("KICAD10_SYMBOL_DIR", r"C:/Program Files/KiCad/10.0/share/kicad/symbols")
DATE = "2026-10-08"
REV = "A (draft)"
GRID = 2.54
CHAR_W = 1.2  # mm per character at 1.27 mm text (generous, for the overlap check)


# ── s-expressions ────────────────────────────────────────────────────────────────────────────────────────────────────
class Q(str):
    """A quoted string token."""


def parse(text):
    stack = [[]]
    for tok in re.findall(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+', text):
        if tok == "(":
            stack.append([])
        elif tok == ")":
            done = stack.pop()
            stack[-1].append(done)
        else:
            stack[-1].append(Q(tok[1:-1]) if tok.startswith('"') else tok)
    return stack[0]


def fmt(v):
    v = round(v, 4)
    if v == int(v):
        return str(int(v))
    return ("%.4f" % v).rstrip("0").rstrip(".")


def dump(x, ind=0):
    if not isinstance(x, list):
        if isinstance(x, Q):
            return '"' + x.replace("\n", "\\n") + '"'
        if isinstance(x, float):
            return fmt(x)
        return str(x)
    if not any(isinstance(e, list) for e in x):
        return "(" + " ".join(dump(e) for e in x) + ")"
    pad = "\t" * (ind + 1)
    out = "(" + " ".join(dump(e) for e in x if not isinstance(e, list))
    for e in x:
        if isinstance(e, list):
            out += "\n" + pad + dump(e, ind + 1)
    return out + "\n" + "\t" * ind + ")"


def kid(node, key):
    for e in node:
        if isinstance(e, list) and e and e[0] == key:
            return e
    return None


def kids(node, key):
    return [e for e in node if isinstance(e, list) and e and e[0] == key]


def uid(*parts):
    return Q(str(uuid.uuid5(uuid.NAMESPACE_URL, "roomkey-hub/" + "/".join(str(p) for p in parts))))


def font(size=1.27, bold=False):
    f = ["font", ["size", size, size]]
    if bold:
        f.append(["bold", "yes"])
    return f


# ── symbol libraries ─────────────────────────────────────────────────────────────────────────────────────────────────
_LIBS = {}


def lib_index(lib):
    if lib not in _LIBS:
        if lib == "roomkey":
            text = custom_lib_text()
        else:
            text = open(os.path.join(KICAD_SYM, lib + ".kicad_sym"), encoding="utf-8").read()
        _LIBS[lib] = {str(s[1]): s for s in kids(parse(text)[0], "symbol")}
    return _LIBS[lib]


def flat_symbol(lib, name):
    """The library symbol with any `extends` resolved (symbols embedded in a schematic must be flat)."""
    node = copy.deepcopy(lib_index(lib)[name])
    ext = kid(node, "extends")
    if not ext:
        return node
    parent = flat_symbol(lib, str(ext[1]))
    pname = str(parent[1])
    own_props = {str(p[1]): p for p in kids(node, "property")}
    new = ["symbol", Q(name)]
    for e in parent[2:]:
        if isinstance(e, list) and e[0] == "property":
            new.append(own_props.pop(str(e[1]), e))
        elif isinstance(e, list) and e[0] == "symbol":
            e = copy.deepcopy(e)
            e[1] = Q(name + str(e[1])[len(pname):])
            new.append(e)
        else:
            new.append(e)
    last = max(i for i, e in enumerate(new) if isinstance(e, list) and e[0] == "property")
    for p in own_props.values():
        last += 1
        new.insert(last, p)
    return new


def symbol_pins(sym, unit=1):
    """[(number, name, x, y, angle_toward_body, hidden, type)] in symbol coordinates (Y up)."""
    pins = []
    for sub in kids(sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", str(sub[1]))
        if not m or int(m.group(1)) not in (0, unit) or int(m.group(2)) not in (0, 1):
            continue
        for p in kids(sub, "pin"):
            at = kid(p, "at")
            hide = kid(p, "hide")
            hidden = "hide" in p or (hide is not None and hide[1] == "yes")
            pins.append((str(kid(p, "number")[1]), str(kid(p, "name")[1]), float(at[1]), float(at[2]),
                         float(at[3]) if len(at) > 3 else 0.0, hidden, str(p[1])))
    return pins


def symbol_body_box(sym, unit=1):
    xs, ys = [], []
    for sub in kids(sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", str(sub[1]))
        if not m or int(m.group(1)) not in (0, unit):
            continue
        for gfx in sub:
            if not isinstance(gfx, list):
                continue
            if gfx[0] == "rectangle":
                for k in ("start", "end"):
                    xs.append(float(kid(gfx, k)[1])); ys.append(float(kid(gfx, k)[2]))
            elif gfx[0] in ("polyline", "bezier"):
                for xy in kids(kid(gfx, "pts"), "xy"):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
            elif gfx[0] == "circle":
                c, r = kid(gfx, "center"), float(kid(gfx, "radius")[1])
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
            elif gfx[0] == "arc":
                for k in ("start", "mid", "end"):
                    xs.append(float(kid(gfx, k)[1])); ys.append(float(kid(gfx, k)[2]))
    if not xs:
        return (-1.27, -1.27, 1.27, 1.27)
    return (min(xs), min(ys), max(xs), max(ys))


def rot(x, y, r):
    """Symbol coordinates (Y up) rotated by r degrees -> schematic offset (Y down)."""
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return x * c - y * s, -(x * s + y * c)


def unit_vec(d):
    return round(math.cos(math.radians(d))), -round(math.sin(math.radians(d)))


# ── schematic model ──────────────────────────────────────────────────────────────────────────────────────────────────
POWER_SYMBOLS = {"GND": "power:GND", "+5V": "power:+5V", "+3V3": "power:+3V3"}
NC = None  # pin deliberately unconnected (no-connect flag)


class Part:
    def __init__(self, ref, lib_id, value, at, nets, fp="", mpn="", mfr="", rot=0, dnp=False, note="",
                 fields=None, unit=1, bom=True, lcsc=""):
        """at = grid units; fields = None (auto) | 'R'/'L'/'T'/'B' | ((x, y), justify) in grid units."""
        self.ref, self.lib_id, self.value, self.nets = ref, lib_id, value, nets
        self.at = (round(at[0] * GRID, 4), round(at[1] * GRID, 4))
        self.fp, self.mpn, self.mfr, self.rot, self.dnp, self.note = fp, mpn, mfr, rot, dnp, note
        self.fields, self.unit, self.bom = fields, unit, bom
        self.lcsc = lcsc or LCSC.get(mpn, "")


class Sheet:
    def __init__(self, project, title, paper="A3", comments=(), origin=(3, 2)):
        self.project, self.title, self.paper, self.comments = project, title, paper, comments
        self.ox, self.oy = origin
        self.root = uid(project, "root")
        self.parts, self.items, self.libsyms = [], [], {}
        self.npwr = 0
        self.netpins = {}   # net -> [(ref, pin)]
        self.boxes = []     # (x0, y0, x1, y1, owner, what) for the overlap check
        self.points = {}    # connection point -> net, for the short check

    def box(self, x0, y0, x1, y1, owner, what):
        self.boxes.append((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1), owner, what))

    def point(self, pt, net, owner):
        pt = (round(pt[0], 3), round(pt[1], 3))
        if pt in self.points and self.points[pt][0] != net:
            raise SystemExit("SHORT at %s: %s (%s) vs %s (%s)" % (pt, net, owner, *self.points[pt]))
        self.points[pt] = (net, owner)

    def lib(self, lib_id):
        if lib_id not in self.libsyms:
            lib, name = lib_id.split(":")
            s = flat_symbol(lib, name)
            s[1] = Q(lib_id)
            self.libsyms[lib_id] = s
        return self.libsyms[lib_id]

    @staticmethod
    def prop(key, val, at, angle=0, hide=False, justify=None, size=1.27):
        eff = ["effects", font(size)]
        if justify:
            eff.append(["justify"] + justify.split())
        p = ["property", Q(key), Q(val), ["at", at[0], at[1], angle]]
        if hide:
            p.append(["hide", "yes"])
        return p + [["show_name", "no"], ["do_not_autoplace", "no"], eff]

    def text_box(self, s, at, angle, justify, owner, size=1.27):
        """Approximate extent of a text for the overlap check (KiCad centres text unless justified)."""
        w, h = len(s) * CHAR_W * size / 1.27, 1.5 * size / 1.27
        jh = "left" if "left" in justify else "right" if "right" in justify else "center"
        if angle in (0, 180):
            x0 = at[0] if jh == "left" else at[0] - w if jh == "right" else at[0] - w / 2
            self.box(x0, at[1] - h / 2, x0 + w, at[1] + h / 2, owner, "text " + s)
        else:
            y1 = at[1] if jh == "left" else at[1] + w if jh == "right" else at[1] + w / 2
            self.box(at[0] - h / 2, y1 - w, at[0] + h / 2, y1, owner, "text " + s)

    def instance(self, lib_id, ref, value, at, r, props, pin_numbers, dnp=False, unit=1, key=None, bom=True):
        node = ["symbol", ["lib_id", Q(lib_id)], ["at", at[0], at[1], r], ["unit", unit], ["body_style", 1],
                ["exclude_from_sim", "no"], ["in_bom", "yes" if bom and not ref.startswith("#") else "no"],
                ["on_board", "yes"],
                ["in_pos_files", "yes"], ["dnp", "yes" if dnp else "no"], ["uuid", uid(self.project, key or ref)]]
        node += props
        for n in pin_numbers:
            node.append(["pin", Q(n), ["uuid", uid(self.project, key or ref, "pin", n)]])
        node.append(["instances", ["project", Q(self.project),
                                   ["path", Q("/" + self.root), ["reference", Q(ref)], ["unit", unit]]]])
        self.items.append(node)

    def wire(self, a, b, net, owner):
        self.items.append(["wire", ["pts", ["xy", a[0], a[1]], ["xy", b[0], b[1]]],
                           ["stroke", ["width", 0], ["type", "default"]], ["uuid", uid(self.project, "w", owner, a)]])
        self.point(a, net, owner)
        self.point(b, net, owner)

    def label(self, net, at, d, owner, glob=False):
        just = "left bottom" if d in (0, 90) else "right bottom"
        if glob:
            self.items.append(["global_label", Q(net), ["shape", "passive"], ["at", at[0], at[1], d],
                               ["effects", font(1.0), ["justify", just.split()[0]]], ["uuid", uid(self.project, "g", owner, at)]])
        else:
            self.items.append(["label", Q(net), ["at", at[0], at[1], d],
                               ["effects", font(), ["justify"] + just.split()], ["uuid", uid(self.project, "l", owner, at)]])
        w, h = (len(net) + (2 if glob else 0)) * CHAR_W, 1.5
        ux, uy = unit_vec(d)
        if d in (0, 180):
            self.box(at[0], at[1] - h, at[0] + ux * w, at[1], owner, "label " + net)
        else:
            self.box(at[0] - h, at[1], at[0], at[1] + uy * w, owner, "label " + net)

    def power(self, net, at, d, owner, flag=False):
        lib_id = "power:PWR_FLAG" if flag else POWER_SYMBOLS[net]
        sym = self.lib(lib_id)
        (num, _, px, py, pa, _, _), = symbol_pins(sym)
        r = int((d - pa) % 360)
        self.npwr += 1
        ref = ("#FLG%02d" if flag else "#PWR%02d") % self.npwr
        vp = kid(next(p for p in kids(sym, "property") if p[1] == "Value"), "at")
        ox, oy = rot(float(vp[1]), float(vp[2]), r)
        vat = (at[0] + ox, at[1] + oy)
        props = [self.prop("Reference", ref, at, hide=True),
                 self.prop("Value", "PWR_FLAG" if flag else net, vat),
                 self.prop("Footprint", "", at, hide=True), self.prop("Datasheet", "", at, hide=True),
                 self.prop("Description", "", at, hide=True)]
        self.instance(lib_id, ref, net, at, r, props, [num], key=("pwr", owner, at))
        bx0, by0, bx1, by1 = symbol_body_box(sym)
        cs = [rot(x, y, r) for x, y in ((bx0, by0), (bx1, by1))]
        self.box(at[0] + min(c[0] for c in cs), at[1] + min(c[1] for c in cs),
                 at[0] + max(c[0] for c in cs), at[1] + max(c[1] for c in cs), owner, "power " + net)
        self.text_box("PWR_FLAG" if flag else net, vat, 0, "", owner)

    def flag(self, net, at, d=90):
        """PWR_FLAG on a net: the net's symbol/label at `at`, a stub in direction d, the flag at its end."""
        at = ((at[0] + self.ox) * GRID, (at[1] + self.oy) * GRID)
        ux, uy = unit_vec(d)
        tip = (at[0] + GRID * ux, at[1] + GRID * uy)
        self.wire(at, tip, net, "flag " + net)
        self.power(net, tip, d, "flag " + net, flag=True)
        if net in POWER_SYMBOLS:
            self.power(net, at, (d + 180) % 360, "flag " + net)
        else:
            self.label(net, at, (d + 180) % 360, "flag " + net)

    def text(self, s, at, size=1.27, bold=False):
        at = ((at[0] + self.ox) * GRID, (at[1] + self.oy) * GRID)
        self.items.append(["text", Q(s), ["exclude_from_sim", "no"], ["at", at[0], at[1], 0],
                           ["effects", font(size, bold), ["justify", "left", "top"]],
                           ["uuid", uid(self.project, "t", s[:40], at)]])
        lines = s.split("\n")
        w = max(len(x) for x in lines) * CHAR_W * 0.85 * size / 1.27
        self.box(at[0], at[1], at[0] + w, at[1] + len(lines) * 2.2 * size / 1.27, "text", s[:20])

    def frame(self, x0, y0, x1, y1, title):
        o = (self.ox, self.oy)
        self.items.append(["rectangle", ["start", (x0 + o[0]) * GRID, (y0 + o[1]) * GRID],
                           ["end", (x1 + o[0]) * GRID, (y1 + o[1]) * GRID],
                           ["stroke", ["width", 0.3], ["type", "dash"]], ["fill", ["type", "none"]],
                           ["uuid", uid(self.project, "frame", title)]])
        self.text(title, (x0 + 0.6, y0 + 0.6), size=2.0, bold=True)

    def add(self, part):
        self.parts.append(part)
        sym = self.lib(part.lib_id)
        pins = symbol_pins(sym, part.unit)
        X, Y = part.at[0] + self.ox * GRID, part.at[1] + self.oy * GRID
        r = part.rot
        seen, sides = {}, set()
        for num, name, px, py, pa, hidden, ptype in pins:
            if num not in part.nets:
                if hidden and ptype == "no_connect":
                    continue
                raise SystemExit("%s: pin %s (%s) has no net" % (part.ref, num, name))
            net = part.nets[num]
            ox, oy = rot(px, py, r)
            pt = (round(X + ox, 4), round(Y + oy, 4))
            d = int((pa + 180 + r) % 360)
            if net is not NC:
                self.netpins.setdefault(net, []).append((part.ref, num))
            if hidden and net is NC:
                continue
            sides.add(d)
            if pt in seen:
                if seen[pt] != net:
                    raise SystemExit("%s: stacked pins at %s on different nets" % (part.ref, pt))
                continue
            seen[pt] = net
            if net is NC:
                self.items.append(["no_connect", ["at", pt[0], pt[1]], ["uuid", uid(self.project, part.ref, "nc", num)]])
                self.point(pt, "NC/%s/%s" % (part.ref, num), part.ref)
                continue
            ux, uy = unit_vec(d)
            tip = (round(pt[0] + GRID * ux, 4), round(pt[1] + GRID * uy, 4))
            owner = "%s.%s" % (part.ref, num)
            self.wire(pt, tip, net, owner)
            if net in POWER_SYMBOLS and d in (90, 270):
                self.power(net, tip, d, owner)
            elif net in POWER_SYMBOLS:  # sideways: a global label (joins the power net by name), no turned symbol
                self.label(net, tip, d, owner, glob=True)
            else:
                self.label(net, tip, d, owner)
        unknown = set(part.nets) - {p[0] for p in pins}
        if unknown:
            raise SystemExit("%s: unknown pins %s" % (part.ref, sorted(unknown)))
        # body (incl. pins) for the overlap check
        bx0, by0, bx1, by1 = symbol_body_box(sym, part.unit)
        cs = [rot(x, y, r) for x, y in ((bx0, by0), (bx1, by1))]
        x0, x1 = X + min(c[0] for c in cs), X + max(c[0] for c in cs)
        y0, y1 = Y + min(c[1] for c in cs), Y + max(c[1] for c in cs)
        self.box(x0, y0, x1, y1, part.ref, "body")
        # reference + value beside the body, on a side without pins (or where the part says)
        cy, cx = (y0 + y1) / 2, (x0 + x1) / 2
        f = part.fields or next((s for s, d in (("R", 0), ("L", 180), ("T", 90), ("B", 270)) if d not in sides), "TR")
        if isinstance(f, tuple):
            (fx, fy), just = f
            ref_at, val_at = ((fx + self.ox) * GRID, (fy + self.oy) * GRID), ((fx + self.ox) * GRID, (fy + self.oy) * GRID + 2.4)
        elif f == "R":
            ref_at, val_at, just = (x1 + 1.27, cy - 1.0), (x1 + 1.27, cy + 1.4), "left"
        elif f == "L":
            ref_at, val_at, just = (x0 - 1.27, cy - 1.0), (x0 - 1.27, cy + 1.4), "right"
        elif f == "T":
            ref_at, val_at, just = (cx, y0 - 3.6), (cx, y0 - 1.3), ""
        elif f == "B":
            ref_at, val_at, just = (cx, y1 + 1.6), (cx, y1 + 3.9), ""
        else:  # "TR": above the top-right corner
            ref_at, val_at, just = (x1 + 1.27, y0 - 3.4), (x1 + 1.27, y0 - 1.0), "left"
        fa = 90 if r in (90, 270) else 0  # KiCad turns field text with the symbol; this keeps it horizontal
        jk = just
        if just and r in (90, 180):  # KiCad mirrors the justification of a symbol turned 90 or 180 degrees
            jk = {"left": "right", "right": "left"}[just]
        props = [self.prop("Reference", part.ref, ref_at, fa, justify=jk or None),
                 self.prop("Value", part.value, val_at, fa, justify=jk or None),
                 self.prop("Footprint", part.fp, (X, Y), hide=True),
                 self.prop("Datasheet", next((str(p[2]) for p in kids(sym, "property") if p[1] == "Datasheet"), ""),
                           (X, Y), hide=True),
                 self.prop("Description", part.note or next((str(p[2]) for p in kids(sym, "property")
                                                             if p[1] == "Description"), ""), (X, Y), hide=True),
                 self.prop("MPN", part.mpn, (X, Y), hide=True),
                 self.prop("Manufacturer", part.mfr, (X, Y), hide=True),
                 self.prop("LCSC", part.lcsc, (X, Y), hide=True)]
        self.text_box(part.ref, ref_at, 0, just or "", part.ref)
        self.text_box(part.value, val_at, 0, just or "", part.ref)
        self.instance(part.lib_id, part.ref, part.value, (X, Y), r, props,
                      sorted({p[0] for p in pins}, key=lambda n: (len(n), n)), dnp=part.dnp, unit=part.unit,
                      bom=part.bom)

    def overlaps(self):
        bad = []
        bs = self.boxes
        for i in range(len(bs)):
            a = bs[i]
            for b in bs[i + 1:]:
                if a[4] == b[4]:
                    continue
                if a[0] < b[2] - 0.15 and b[0] < a[2] - 0.15 and a[1] < b[3] - 0.15 and b[1] < a[3] - 0.15:
                    bad.append("%s %s  x  %s %s  @ (%.0f, %.0f) grid" % (a[4], a[5], b[4], b[5],
                                                                       max(a[0], b[0]) / GRID, max(a[1], b[1]) / GRID))
        return bad

    def write(self, path):
        tb = ["title_block", ["title", Q(self.title)], ["date", Q(DATE)], ["rev", Q(REV)],
              ["company", Q("aikos-home / RoomKey")]]
        for i, c in enumerate(self.comments, 1):
            tb.append(["comment", i, Q(c)])
        doc = ["kicad_sch", ["version", "20260101"], ["generator", Q("eeschema")], ["generator_version", Q("10.0")],
               ["uuid", self.root], ["paper", Q(self.paper)], tb,
               ["lib_symbols"] + list(self.libsyms.values())] + self.items + \
              [["sheet_instances", ["path", Q("/"), ["page", Q("1")]]], ["embedded_fonts", "no"]]
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(dump(doc) + "\n")


# ── custom symbols (lib/roomkey.kicad_sym) ───────────────────────────────────────────────────────────────────────────
CUSTOM_LIB_PATH = os.path.join(HERE, "lib", "roomkey.kicad_sym")
PI, PO, BI, PS, PWR_IN, PWR_OUT, OC = "input", "output", "bidirectional", "passive", "power_in", "power_out", "open_collector"


def ic_symbol(name, ref, desc, fp, ds, left, right, bottom=(), width=15.24, stacked=()):
    """A box symbol; left/right/bottom = [(number, name, type) or None for a gap];
    stacked = [(number, name, type, on_number)]: a hidden pin on top of another (e.g. an exposed pad on GND)."""
    n = max(len(left), len(right), 2)
    hw = width / 2
    ytop = math.ceil((n + 1) * GRID / 2 / GRID) * GRID
    ybot = ytop - (n + 1) * GRID
    pins, where = [], {}

    def pin(num, nm, typ, x, y, a, hide=False):
        p = ["pin", typ, "line", ["at", x, y, a], ["length", GRID]]
        if hide:
            p.append(["hide", "yes"])
        pins.append(p + [["name", Q(nm), ["effects", font()]], ["number", Q(num), ["effects", font()]]])
        where[num] = (x, y, a)

    for i, p in enumerate(left):
        if p:
            pin(p[0], p[1], p[2], -hw - GRID, ytop - GRID * (i + 1), 0)
    for i, p in enumerate(right):
        if p:
            pin(p[0], p[1], p[2], hw + GRID, ytop - GRID * (i + 1), 180)
    for i, p in enumerate(bottom):
        if p:
            pin(p[0], p[1], p[2], -GRID * (len(bottom) - 1) / 2 + GRID * i, ybot - GRID, 90)
    for num, nm, typ, on in stacked:
        pin(num, nm, typ, *where[on], hide=True)
    eff = ["effects", font()]
    return ["symbol", Q(name), ["pin_names", ["offset", 1.016]], ["exclude_from_sim", "no"], ["in_bom", "yes"],
            ["on_board", "yes"],
            ["property", Q("Reference"), Q(ref), ["at", -hw, ytop + 1.27, 0], ["effects", font(), ["justify", "left"]]],
            ["property", Q("Value"), Q(name), ["at", -hw, ybot - 1.27, 0], ["effects", font(), ["justify", "left"]]],
            ["property", Q("Footprint"), Q(fp), ["at", 0, 0, 0], ["hide", "yes"], eff],
            ["property", Q("Datasheet"), Q(ds), ["at", 0, 0, 0], ["hide", "yes"], eff],
            ["property", Q("Description"), Q(desc), ["at", 0, 0, 0], ["hide", "yes"], eff],
            ["symbol", Q(name + "_0_1"), ["rectangle", ["start", -hw, ytop], ["end", hw, ybot],
                                           ["stroke", ["width", 0.254], ["type", "default"]],
                                           ["fill", ["type", "background"]]]],
            ["symbol", Q(name + "_1_1")] + pins]


# pin facts [DS = data sheet, see README "Sources"]
TPS25200_PINS = {"OUT": ("1", "OUT", PWR_OUT), "ILIM": ("2", "ILIM", PS), "FAULT": ("3", "~{FAULT}", OC),
                 "EN": ("4", "EN", PI), "GND": ("5", "GND", PWR_IN), "IN": ("6", "IN", PWR_IN),
                 "EP": ("7", "EP", PS)}  # [DS SLVSC71, DRV package; PowerPAD = GND]
VEML6030_PINS = {"GND": ("1", "GND", PWR_IN), "SDA": ("2", "SDA", BI), "INT": ("3", "~{INT}", OC),
                 "ADDR": ("4", "ADDR", PI), "SCL": ("5", "SCL", PI), "VDD": ("6", "VDD", PWR_IN)}  # [DS 84366 p.10]

# touch board H1 pads used by the pogo adapter (pad number, signal). No pin on: 2 VBAT, 8 3V3, 9 RST, 11 IO1,
# 13 IO2, 14/16 USB D+/D-.
POGO_LEFT = [(1, "VBUS"), (3, "GND"), (5, "TXD_IO16"), (7, "RXD_IO17"), (15, "IO3"), (17, "IO4"), (19, "IO5"),
             (21, "IO6")]
POGO_RIGHT = [(4, "GND"), (6, "GND"), (10, "SCL_IO19"), (12, "SDA_IO18"), (18, "IO9_BOOT"), (20, "IO8"), (22, "IO7")]


def patched_copy(lib, name, pin_types):
    """A stock symbol copied into the project library with some pin types changed."""
    sym = flat_symbol(lib, name)
    for sub in kids(sym, "symbol"):
        for p in kids(sub, "pin"):
            if str(kid(p, "number")[1]) in pin_types:
                p[1] = pin_types[str(kid(p, "number")[1])]
    return sym


def custom_symbols():
    T = TPS25200_PINS
    V = VEML6030_PINS
    return [
        patched_copy("Audio", "MAX98357A", {"17": PS}),  # stock: exposed pad "unspecified" -> ERC warning on GND
        ic_symbol("TPS25200", "U", "5 V eFuse: 5.7 V overvoltage clamp, adjustable current limit, WSON-6 2x2",
                  "Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm", "https://www.ti.com/lit/ds/symlink/tps25200.pdf",
                  left=[T["IN"], T["EN"], None, T["ILIM"]], right=[T["OUT"], None, T["FAULT"]], bottom=[T["GND"]],
                  stacked=[T["EP"] + ("5",)]),
        ic_symbol("VEML6030", "U", "Ambient light sensor, I2C, 2 x 2 mm", "roomkey:Vishay_VEML6030_2x2mm",
                  "https://www.vishay.com/docs/84366/veml6030.pdf",
                  left=[V["SDA"], V["SCL"], V["ADDR"]], right=[V["VDD"], V["INT"], V["GND"]], width=12.7),
    ]


def custom_lib_text():
    root = ["kicad_symbol_lib", ["version", "20251024"], ["generator", Q("roomkey_gen_schematics")],
            ["generator_version", Q("10.0")]] + custom_symbols()
    return dump(root) + "\n"


# ── the FFC between pogo adapter and hub: ONE definition for both ends ───────────────────────────────────────────────
FFC_PINS = {1: "VBUS_KEY", 2: "VBUS_KEY", 3: "GND", 4: "KEY_TOP_IO9", 5: "KEY_BOT_IO6", 6: "GLOW_IO4",
            7: "ESP_TO_RADAR_IO5", 8: "RADAR_TO_ESP_IO3", 9: "I2C_SDA_IO18", 10: "I2C_SCL_IO19", 11: "GND",
            12: "I2S_DOUT_IO16", 13: "I2S_BCLK_IO7", 14: "GND", 15: "I2S_WS_IO8", 16: "I2S_DIN_IO17"}
FFC_MIRROR = False  # True if the chosen cable/connector pairing reverses the conductor order (decided at layout)
H1_TO_NET = {1: "VBUS_KEY", 3: "GND", 4: "GND", 6: "GND", 5: "I2S_DOUT_IO16", 7: "I2S_DIN_IO17", 10: "I2C_SCL_IO19",
             12: "I2C_SDA_IO18", 15: "RADAR_TO_ESP_IO3", 17: "GLOW_IO4", 18: "KEY_TOP_IO9", 19: "ESP_TO_RADAR_IO5",
             20: "I2S_WS_IO8", 21: "KEY_BOT_IO6", 22: "I2S_BCLK_IO7"}
assert set(H1_TO_NET.values()) == set(FFC_PINS.values()), "pogo pins and FFC must carry the same nets"

FFC_CONN = dict(lib_id="Connector_Generic_MountingPin:Conn_01x16_MountingPin",
                fp="Connector_FFC-FPC:Hirose_FH12-16S-0.5SH_1x16-1MP_P0.50mm_Horizontal",
                mpn="FH12-16S-0.5SH(55)", mfr="Hirose")

R0402 = "Resistor_SMD:R_0402_1005Metric"
C0402 = "Capacitor_SMD:C_0402_1005Metric"
C0603 = "Capacitor_SMD:C_0603_1608Metric"
C0805 = "Capacitor_SMD:C_0805_2012Metric"
JST_SH = "Connector_JST:JST_SH_SM0%dB-SRSS-TB_1x0%d-1MP_P1.00mm_Horizontal"
JST_SHV = "Connector_JST:JST_SH_BM0%dB-SRSS-TB_1x0%d-1MP_P1.00mm_Vertical"   # top entry (hub: saves depth)
TP_FP = "TestPoint:TestPoint_Pad_D1.0mm"
# JLCPCB / LCSC parts (2026-10-08): passives are JLCPCB "basic" parts (no loading fee) except 64.9k
RES = {"100k": ("0402WGF1003TCE", "C25741"), "10k": ("0402WGF1002TCE", "C25744"), "1k": ("0402WGF1001TCE", "C11702"),
       "1M": ("0402WGF1004TCE", "C26083"), "4.7k": ("0402WGF4701TCE", "C25900"), "330": ("0402WGF3300TCE", "C25104"),
       "64.9k": ("0402WGF6492TCE", "C26984")}
C1206 = "Capacitor_SMD:C_1206_3216Metric"
CAPS = {"100n": ("CL05B104KO5NNNC", C0402, "C1525"), "1u": ("CL10A105KB8NNNC", C0603, "C15849"),
        "10u": ("CL21A106KAYNNNE", C0805, "C15850"), "100u": ("CL31A107MQHNNNE", C1206, "C15008")}
LCSC = {  # MPN -> LCSC part number (stock checked on jlcpcb.com 2026-10-08)
    "SMF12CA": "C123801", "AO3401A": "C15127", "LBZT52C6V2T1G": "C27091", "TPS25200DRVR": "C128401",
    "SMF5.0A": "C193402", "PMEG3020EH": "C19268151", "BAT54C": "C2135", "TPS7A2033PDBVR": "C2862740",
    "MAX98357AETE+T": "C910544", "2N7002": "C8545", "A1251WV-S-2P": "C225104", "ICS-43434": "C5656610",
    "TCA9534PWR": "C783615", "SN74AHCT1G125DBVR": "C7484", "B2B-PH-SM4-TB(LF)(SN)": "C160352",
    "BM02B-SRSS-TB(LF)(SN)": "C160388", "BM03B-SRSS-TB(LF)(SN)": "C160389", "BM04B-SRSS-TB(LF)(SN)": "C160390",
    "BM05B-SRSS-TB(LF)(SN)": "C160391", "CPG151101S11-2": "C49352235",
    "S2B-PH-K-S(LF)(SN)": "C173752"}  # J1 5 V plug (rev D): extended, through-hole (JLCPCB solders it by wave)


def R(ref, val, at, a, b, rot=0, note="", dnp=False, fields=None):
    mpn, lcsc = RES.get(val, ("TBD", ""))
    return Part(ref, "Device:R", val, at, {"1": a, "2": b}, fp=R0402, rot=rot, dnp=dnp, fields=fields,
                mpn=mpn, mfr="UNI-ROYAL" if lcsc else "", note=note, lcsc=lcsc)


def C(ref, val, at, a, b, note="", fields=None):
    mpn, fp, lcsc = CAPS[val]
    return Part(ref, "Device:C", val, at, {"1": a, "2": b}, fp=fp, mpn=mpn, mfr="Samsung", note=note, fields=fields,
                lcsc=lcsc)


def TP(ref, net, at):
    return Part(ref, "Connector:TestPoint", net, at, {"1": net}, fp=TP_FP, rot=180, note="Test pad", bom=False)


# ── hub (A2) ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def hub():
    s = Sheet("roomkey-hub", "RoomKey hub (static, in the flush box)", paper="A2", comments=(
        "5 V SELV only, from a certified supply in the NEIGHBOURING box. Never 230 V here.",
        "Generated by gen_schematics.py; the FFC pinout is shared with the pogo adapter.",
        "[TBD] marks open values; see README.md."))
    P = s.add

    # 1 · power -----------------------------------------------------------------------------------------------------
    s.frame(2, 3, 113, 60, "1  Power: 5 V terminal -> protection -> +5V;  VBUS for the key;  +3V3")
    P(Part("J1", "Connector_Generic:Conn_01x02", "5V IN", (8, 16), {"1": "GND", "2": "VIN_RAW"}, rot=180,
           fp="Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", mpn="S2B-PH-K-S(LF)(SN)", mfr="JST", fields="L",
           note="5 V in: JST PH 2-pin (2 A), SIDE entry, through-hole (owner 2026-10-31, was two solder holes; rev D: "
                "side entry, a top-entry plug + lead did not fit in front of the charger in the 64 mm housing). A short "
                "lead (AWG 24 max., PH crimps) from a solder-type USB-A plug in the USB charger plugs in here. "
                "Pin 2 = +5 V (USB VBUS), pin 1 = GND"))
    P(Part("D1", "Device:D_TVS", "SMF12CA", (17, 19), {"1": "VIN_RAW", "2": "GND"}, rot=270,
           fp="Diode_SMD:D_SOD-123F", mpn="SMF12CA", mfr="MDD",
           note="Bidirectional TVS at the terminal: ESD/surge; does not conduct at 12 V or a reversed 5 V"))
    P(Part("Q1", "Transistor_FET:AO3401A", "AO3401A", (27, 17), {"1": "Q1_GATE", "2": "VIN_PROT", "3": "VIN_RAW"},
           rot=90, fp="Package_TO_SOT_SMD:SOT-23", mpn="AO3401A", mfr="Alpha & Omega Semiconductor",
           note="Reverse-polarity protection: P-FET, drain to the terminal"))
    P(R("R1", "100k", (32, 24), "Q1_GATE", "GND", note="Turns Q1 on (gate to GND)"))
    P(Part("D2", "Device:D_Zener", "BZT52C6V2", (37, 24), {"1": "VIN_PROT", "2": "Q1_GATE"}, rot=270,
           fp="Diode_SMD:D_SOD-123", mpn="LBZT52C6V2T1G", mfr="LRC",
           note="Clamps Q1's gate-source voltage to 6.2 V (its limit is 12 V)"))
    P(C("C1", "1u", (46, 24), "VIN_PROT", "GND", note="eFuse input capacitor, 25 V"))
    P(Part("U1", "roomkey:TPS25200", "TPS25200DRVR", (59, 17),
           {"6": "VIN_PROT", "5": "GND", "4": "U1_EN", "3": NC, "2": "U1_ILIM", "1": "+5V", "7": "GND"},
           fp="Package_SON:WSON-6-1EP_2x2mm_P0.65mm_EP1x1.6mm", mpn="TPS25200DRVR", mfr="Texas Instruments",
           note="eFuse: current limit, output clamp 5.25-5.55 V for IN 5.4-7.6 V; above 6.8 V (min) it switches the "
                "output off (a 12 V supply by mistake; IN up to 20 V) [DS 7.4.3/7.4.4]; soft start, thermal cut-out "
                "with auto-retry. FAULT is not used (no free ESP pin)"))
    P(R("R2", "64.9k", (52, 27), "U1_ILIM", "GND",
        note="eFuse current limit 98322/R^1.003 mA = 1.5 A typ (1.38-1.62 A): above the ~1 A peak, below the 2 A supply"))
    P(R("R17", "1M", (47, 34), "VIN_PROT", "U1_EN", rot=90, note="Keeps the eFuse on; >= 300k when EN hangs on IN [DS]"))
    P(Part("D3", "Device:D_Zener", "SMF5.0A", (72, 24), {"1": "+5V", "2": "GND"}, rot=270,
           fp="Diode_SMD:D_SOD-123F", mpn="SMF5.0A", mfr="MDD",
           note="Unidirectional TVS on +5V (breaks down at 6.4 V min, above the eFuse's 5.55 V clamp)"))
    P(C("C2", "100u", (79, 24), "+5V", "GND",
        note="Reservoir for the amplifier's peaks: 100 uF 6.3 V X5R 1206, JLCPCB basic part (ten times the kit "
             "breakout's 10 uF; a tantalum was neither in stock nor needed)"))
    P(C("C3", "10u", (85, 24), "+5V", "GND", note="10 V X5R"))
    P(C("C4", "100n", (91, 24), "+5V", "GND"))
    P(TP("TP1", "+5V", (97, 23)))
    P(Part("D4", "Diode:PMEG3020EH", "PMEG3020EH", (98, 17), {"1": "VBUS_KEY", "2": "+5V"}, rot=180,
           fp="Diode_SMD:D_SOD-123F", mpn="PMEG3020EH", mfr="TECH PUBLIC",
           note="+5V -> the key's VBUS; stops USB-C power from flowing back into the hub"))
    P(TP("TP3", "VBUS_KEY", (110, 20)))
    P(Part("D5", "Diode:BAT54C", "BAT54C", (12, 41), {"1": "+5V", "2": "VBUS_KEY", "3": "LDO_IN"},
           fp="Package_TO_SOT_SMD:SOT-23", mpn="BAT54C", mfr="Changjiang (CJ)",
           note="3.3 V regulator fed from either side: hub supply OR the key's USB-C (bench rescue)"))
    P(C("C5", "1u", (26, 45), "LDO_IN", "GND"))
    P(Part("U2", "Regulator_Linear:TPS7A20xxxDBV", "TPS7A2033PDBVR", (40, 41),
           {"1": "LDO_IN", "2": "GND", "3": "LDO_IN", "5": "+3V3"},
           fp="Package_TO_SOT_SMD:SOT-23-5", mpn="TPS7A2033PDBVR", mfr="Texas Instruments",
           note="Low-noise 3.3 V for the mic, the key pull-ups and the sensor tail"))
    P(C("C6", "1u", (50, 45), "+3V3", "GND"))
    P(TP("TP2", "+3V3", (55, 44)))
    s.flag("GND", (64, 42))
    s.flag("VIN_PROT", (70, 42))
    s.flag("LDO_IN", (76, 42))
    s.text("Flow: terminal -> TVS -> reverse-polarity FET Q1 -> eFuse U1 (1.5 A limit, overvoltage off, soft start)\n"
           "-> +5V node (TVS D3, bulk C2) -> amplifier, radar, glow ring.  +5V -> Schottky D4 -> VBUS_KEY -> FFC ->\n"
           "touch board VBUS.  USB-C on the touch board stays usable: D4 keeps USB power out of the hub; D5 runs the\n"
           "3.3 V regulator from either side, so I2C, mic and the IO8 pull-up are live whenever the key has power.",
           (4, 51))

    # 2 · audio -----------------------------------------------------------------------------------------------------
    s.frame(116, 3, 226, 60, "2  Audio: I2S amplifier + speaker, I2S microphone (one shared I2S bus)")
    P(Part("U3", "roomkey:MAX98357A", "MAX98357AETE+T", (142, 22),
           {"1": "I2S_DOUT_IO16", "2": NC, "3": "GND", "4": "AMP_SD", "7": "+5V", "8": "+5V", "9": "SPK_P",
            "10": "SPK_N", "11": "GND", "14": "I2S_WS_IO8", "15": "GND", "16": "I2S_BCLK_IO7", "17": "GND"},
           fp="Package_DFN_QFN:TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm", mpn="MAX98357AETE+T", mfr="Analog Devices",
           fields=((147, 15), "left"),
           note="3.2 W class-D I2S amplifier; GAIN_SLOT open = 9 dB, as the kit's breakout"))
    P(R("R3", "1M", (124, 31), "+5V", "AMP_SD",
        note="SD_MODE with the chip's internal 100k: (L+R)/2 mono, same as the kit's breakout"))
    P(C("C7", "10u", (153, 29), "+5V", "GND"))
    P(C("C8", "100n", (158, 29), "+5V", "GND"))
    P(Part("J2", "Connector_Generic_MountingPin:Conn_01x02_MountingPin", "SPEAKER", (170, 21),
           {"1": "SPK_P", "2": "SPK_N", "MP": NC},
           fp="Connector_Molex:Molex_PicoBlade_53398-0271_1x02-1MP_P1.25mm_Vertical", mpn="A1251WV-S-2P",
           mfr="CJT", note="Waveshare 2030 speaker: 2-pin 1.25 mm plug (owner: 'PH1.25 2P'). CJT A1251WV-S = PicoBlade "
                           "53398 equivalent in JLCPCB stock [TBD: footprint check in JLCPCB's preview]"))
    P(Part("U4", "Sensor_Audio:ICS-43434", "ICS-43434", (198, 22),
           {"1": "I2S_WS_IO8", "2": "GND", "3": "GND", "4": "I2S_BCLK_IO7", "5": "+3V3", "6": "I2S_DIN_IO17"},
           fp="Sensor_Audio:InvenSense_ICS-43434-6_3.5x2.65mm", mpn="ICS-43434", mfr="TDK InvenSense",
           fields=((186, 16.5), "left"),
           note="I2S MEMS mic, bottom port -> hole through the PCB; L/R = GND (left slot, as the firmware reads). "
                "Obsolete but stocked (Digi-Key ~90k); alt. MEMSensing MSM261S3526Z0CM (same size, other pinout)"))
    P(C("C9", "100n", (190, 31), "+3V3", "GND"))
    P(R("R5", "100k", (212, 31), "I2S_DIN_IO17", "GND",
        note="Mic SD pull-down: discharges the line while the mic's output is off"))
    P(R("R6", "10k", (220, 31), "+3V3", "I2S_WS_IO8",
        note="IO8 is a strapping pin: must read high for ROM download mode (BOOT held)"))
    s.text("Amplifier and mic share BCLK (IO7) and WS (IO8): half duplex, as in the kit.\n"
           "The amplifier behaves exactly like the kit's breakout; it idles in standby while BCLK is stopped.",
           (150, 47))

    # 3 · I2C bus + screw holes ---------------------------------------------------------------------------------------
    s.frame(2, 62, 113, 145, "3  I2C bus (to the sensor tail); screw holes")
    for i, (x, y) in enumerate(((10, 76), (16, 76), (22, 76))):
        P(Part("H%d" % (i + 1), "Mechanical:MountingHole", "M2", (x, y), {}, fields="B",
               fp="MountingHole:MountingHole_2.2mm_M2", bom=False,
               note="M2 screw into a chassis post (posts end at the hub's front face)"))
    P(R("R11", "4.7k", (102, 80), "+3V3", "I2C_SDA_IO18", dnp=True,
        note="DNP: the touch board already pulls the I2C bus up; fit only if needed"))
    P(R("R12", "4.7k", (108, 80), "+3V3", "I2C_SCL_IO19", dnp=True, note="DNP, see R11"))
    s.text("I2C addresses: VEML6030 0x10 and SHT4x 0x44 on the sensor tail,\n"
           "touch AXS5106L 0x63 and IMU QMI8658 0x6B (both on the touch board). No clashes.\n"
           "No plate button and no I/O expander (owner 2026-10-08: the two MX are the only buttons);\n"
           "the hub uses exactly the kit's ESP pins, so the firmware needs no change for it.", (4, 126))

    # 4 · connectors ------------------------------------------------------------------------------------------------
    s.frame(116, 62, 226, 145, "4  Connectors: key wires, radar, MX sockets, glow ring, SHT tail")
    ffc_nets = {str(k): v for k, v in FFC_PINS.items()}
    ffc_nets["MP"] = "GND"
    del ffc_nets["MP"]
    P(Part("J4", "Connector_Generic:Conn_02x08_Odd_Even", "KEY WIRES", (142, 84), ffc_nets,
           fp="Connector_PinHeader_1.27mm:PinHeader_2x08_P1.27mm_Vertical", dnp=True, bom=False,
           note="Solder holes for the key's wires (owner 2026-10-08: wires as in the kit, no FFC in this order); "
                "same order as the FFC_PINS table, so the pogo/flex link can come later"))
    P(Part("J5", "Connector_Generic_MountingPin:Conn_01x05_MountingPin", "RADAR", (176, 72),
           {"1": "RADAR_TO_ESP_IO3", "2": "ESP_TO_RADAR_IO5", "3": NC, "4": "GND", "5": "+5V", "MP": NC},
           fp=JST_SHV % (5, 5), mpn="BM05B-SRSS-TB(LF)(SN)", mfr="JST",
           note="Cable to the HLK-LD2410C, so the radar can sit wherever it works best: JST SH 5-pin here, 2.54 mm "
                "female on the module's header. Order = the module's silkscreen TX, RX, OUT, GND, VCC (owner's photo "
                "2026-10-08); OUT is not used (presence comes over the UART), the pin keeps the cable 1:1"))
    for ref, net, y, name in (("SW1", "KEY_TOP_IO9", 84, "top"), ("SW2", "KEY_BOT_IO6", 90, "bottom")):
        P(Part(ref, "Switch:SW_Push", "MX %s" % name, (176, y), {"1": net, "2": "GND"}, fields="T",
               fp="roomkey:SW_MX_Hotswap_Kailh_1.00u", mpn="CPG151101S11-2", mfr="HanElectricity",
               note="MX switch %s plugs straight into a Kailh hot-swap socket on the hub (owner 2026-10-08); "
                    "the switch itself is the owner's, the socket is assembled" % name))
    P(R("R13", "10k", (156, 92), "+3V3", "KEY_TOP_IO9", note="Key pull-ups (IO9 also has the board's own)"))
    P(R("R14", "10k", (162, 92), "+3V3", "KEY_BOT_IO6"))
    P(Part("U7", "74xGxx:74AHCT1G125", "SN74AHCT1G125DBVR", (198, 76),
           {"1": "GND", "2": "GLOW_IO4", "3": "GND", "4": "GLOW_5V", "5": "+5V"},
           fp="Package_TO_SOT_SMD:SOT-23-5", mpn="SN74AHCT1G125DBVR", mfr="Texas Instruments",
           fields=((201, 67.5), "left"), note="3.3 V -> 5 V level shifter for the LED data"))
    P(R("R15", "100k", (184, 82), "GLOW_IO4", "GND", note="Keeps the LED data low while the ESP boots"))
    P(R("R16", "330", (217, 76), "GLOW_5V", "GLOW_DATA", rot=90, note="Series resistor at the chain start"))
    P(C("C13", "100n", (198, 89), "+5V", "GND"))
    P(C("C14", "10u", (204, 89), "+5V", "GND", note="At the LED chain start (no room for 100 n on the LED carriers)"))
    P(Part("J8", "Connector_Generic:Conn_01x03", "GLOW LEDS", (219, 92), {"1": "GND", "2": "+5V", "3": "GLOW_DATA"},
           fp="Connector_PinHeader_1.27mm:PinHeader_1x03_P1.27mm_Vertical", dnp=True, bom=False,
           note="Solder holes for the glow LED chain (4 x WS2812B-Mini behind the clear collar, BR -> TR -> TL -> BL). "
                "The LEDs sit in FRONT of the hub: their 3 wires come from the BR LED through the switch-plate notch "
                "into the 3.5 mm gap and into these holes near the BR corner (CAD thread 2026-10-09); a plug on the "
                "back could not be reached"))
    P(C("C15", "100n", (204, 108), "+3V3", "GND", note="At the SHT tail connector"))
    P(Part("J9", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "SHT TAIL", (219, 108),
           {"1": "GND", "2": "+3V3", "3": "I2C_SDA_IO18", "4": "I2C_SCL_IO19", "MP": NC}, fp=JST_SHV % (4, 4),
           mpn="BM04B-SRSS-TB(LF)(SN)", mfr="JST",
           note="Qwiic / STEMMA QT pinout (GND, 3V3, SDA, SCL): a ready-made 4-pin JST SH cable fits"))
    s.text("Key wires J4 (2 x 8 holes, 1.27 mm; same order as a later FFC):\n" +
           "\n".join("%2d  %s" % (k, v) for k, v in FFC_PINS.items()), (121, 106))
    return s


# ── SHT tail board (A4) ──────────────────────────────────────────────────────────────────────────────────────────────
def sht_tail():
    s = Sheet("roomkey-sht-tail", "RoomKey sensor tail (in the frame's bottom border)", paper="A4", comments=(
        "Temperature / humidity and room brightness, in room air and light. Qwiic cable to the hub's J9.",
        "Generated by gen_schematics.py."))
    P = s.add
    s.frame(4, 4, 76, 46, "Sensor tail: SHT40 + VEML6030")
    P(Part("U2", "roomkey:VEML6030", "VEML6030", (40, 30),
           {"1": "GND", "2": "I2C_SDA", "3": NC, "4": "GND", "5": "I2C_SCL", "6": "+3V3"},
           fp="roomkey:Vishay_VEML6030_2x2mm", mpn="VEML6030", mfr="Vishay",
           note="Ambient light, I2C 0x10 (ADDR = GND); looks at the room through a clear dot in the frame border "
                "(moved here from the hub 2026-10-08: at the hub depth it could not see the room)"))
    P(C("C2", "100n", (52, 31), "+3V3", "GND"))
    P(Part("J1", "Connector_Generic_MountingPin:Conn_01x04_MountingPin", "TO HUB", (20, 18),
           {"1": "GND", "2": "+3V3", "3": "I2C_SDA", "4": "I2C_SCL", "MP": NC}, fp=JST_SH % (4, 4),
           mpn="SM04B-SRSS-TB", mfr="JST", note="Qwiic / STEMMA QT pinout", fields="R"))
    P(Part("U1", "Sensor_Humidity:SHT4x", "SHT40-AD1B-R2", (40, 18),
           {"1": "I2C_SDA", "2": "I2C_SCL", "3": "+3V3", "4": "GND"},
           fp="Sensor_Humidity:Sensirion_DFN-4_1.5x1.5mm_P0.8mm_SHT4x_NoCentralPad", mpn="SHT40-AD1B-R2",
           mfr="Sensirion", fields="R",
           note="I2C 0x44. Keep copper and parts away from it (heat); slot around it at layout"))
    P(C("C1", "100n", (52, 19), "+3V3", "GND"))
    s.flag("+3V3", (60, 17), 270)
    s.flag("GND", (66, 17))
    s.text("No pull-ups here: the touch board pulls SDA/SCL up (hub R11/R12 as a DNP backup).", (6, 41))
    return s


# ── glow ring board (A4) ─────────────────────────────────────────────────────────────────────────────────────────────
def glow_ring():
    s = Sheet("roomkey-glow-ring", "RoomKey glow ring (frame around the key, behind the collar)", paper="A4", comments=(
        "4 x WS2812B-Mini where the kit's hand-wired LED carriers sit; owner chose an assembled board 2026-10-08.",
        "3-pin JST SH cable to the hub's J8. Generated by gen_schematics.py."))
    P = s.add
    s.frame(4, 4, 104, 50, "Glow ring: 4 x WS2812B-Mini, one chain")
    P(Part("J1", "Connector_Generic_MountingPin:Conn_01x03_MountingPin", "TO HUB", (14, 20),
           {"1": "GND", "2": "+5V", "3": "GLOW_DIN", "MP": NC}, fp=JST_SH % (3, 3), mpn="SM03B-SRSS-TB", mfr="JST",
           fields="R", note="Same pinout as the hub's J8 (1 GND, 2 +5V, 3 data); a 1:1 JST SH cable"))
    chain = ["GLOW_DIN", "LED_D2", "LED_D3", "LED_D4", NC]
    for i, corner in enumerate(("bottom right", "top right", "top left", "bottom left")):
        x = 32 + 18 * i
        P(Part("D%d" % (i + 1), "LED:WS2812B", "WS2812B-Mini", (x, 22),
               {"1": "+5V", "2": chain[i + 1], "3": "GND", "4": chain[i]},
               fp="LED_SMD:LED_WS2812B-Mini_PLCC4_3.5x3.5mm", mpn="WS2812B-Mini", mfr="Worldsemi", fields="TR",
               note="Glow LED %d, %s corner (chain order = firmware order) [TBD: exact suffix / stock]" % (i + 1, corner)))
        P(C("C%d" % (i + 1), "100n", (x + 6, 32), "+5V", "GND", note="Decoupling right at LED %d" % (i + 1)))
    s.flag("+5V", (14, 32), 270)
    s.flag("GND", (20, 32))
    s.text("Chain: J1 -> D1 bottom right -> D2 top right -> D3 top left -> D4 bottom left (as the firmware expects).\n"
           "The level shifter and the 330 ohm series resistor are on the hub; brightness is capped in firmware (45 %).\n"
           "Board outline from the CAD: a thin frame around the key collar, LEDs at today's carrier positions.", (6, 41))
    return s


# ── pogo adapter (A4) ────────────────────────────────────────────────────────────────────────────────────────────────
POGO_MPN = "0900-0-15-20-76-14-11-0"  # Mill-Max SMT spring pin: working height 3.0 mm (2.5-3.48), stroke ~1 mm, 0.6 N


def pogo():
    s = Sheet("roomkey-pogo", "RoomKey pogo adapter (moves with the key)", paper="A4", comments=(
        "15 spring pins on the touch board's H1 pads -> 16-pin FFC to the hub.",
        "Passive: pins + FFC connector only. Generated by gen_schematics.py."))
    P = s.add
    s.frame(4, 4, 104, 60, "Pogo adapter: touch board H1 -> FFC")
    s.text("One spring pin per used H1 pad (value = pad).\nOdd pads = H1 left column, even = right column\n"
           "(seen from the board's back).", (6, 8))
    for i, (pad, sig) in enumerate(POGO_LEFT + POGO_RIGHT):
        col, row = (0, i) if i < len(POGO_LEFT) else (1, i - len(POGO_LEFT))
        P(Part("P%d" % (i + 1), "Connector_Generic:Conn_01x01", "H1-%d" % pad, (22 + 26 * col, 18 + 3 * row),
               {"1": H1_TO_NET[pad]}, fp="roomkey:PogoPin_MillMax_0900_SMD", mpn=POGO_MPN, mfr="Mill-Max",
               fields="R", note="Spring pin on touch board H1 pad %d (%s) [TBD: height vs. the stack, tip shape]"
                                % (pad, sig)))
    order = sorted(FFC_PINS, reverse=FFC_MIRROR)
    ffc_nets = {str(i + 1): FFC_PINS[k] for i, k in enumerate(order)}
    ffc_nets["MP"] = "GND"
    P(Part("J1", FFC_CONN["lib_id"], "FFC 16p 0.5", (90, 30), ffc_nets, fp=FFC_CONN["fp"], mpn=FFC_CONN["mpn"],
           mfr=FFC_CONN["mfr"], note="16-pin 0.5 mm FFC to the hub's J4"))
    s.flag("GND", (66, 46))
    s.text("H1 pads without a pin: 2 VBAT, 8 3V3, 9 RST, 11 IO1, 13 IO2, 14/16 USB D+/D-.\n"
           "Same conductor order as the hub's J4 (FFC_PINS); FFC_MIRROR flips it if the cable type demands.",
           (6, 55))
    return s


# ── footprints (lib/roomkey.pretty) ──────────────────────────────────────────────────────────────────────────────────
def fp_text(kind, text, at, layer, hide=False):
    p = ["property", Q(kind), Q(text), ["at", at[0], at[1], 0], ["layer", Q(layer)]]
    if hide:
        p.append(["hide", "yes"])
    return p + [["effects", ["font", ["size", 0.8, 0.8], ["thickness", 0.12]]]]


def fp_rect(x0, y0, x1, y1, layer, w=0.1):
    return ["fp_rect", ["start", x0, y0], ["end", x1, y1], ["stroke", ["width", w], ["type", "default"]],
            ["fill", "no"], ["layer", Q(layer)], ["uuid", uid("fp", layer, x0, y0)]]


def footprint(name, descr, pads, fab, court, silk=()):
    fp = ["footprint", Q(name), ["version", "20241229"], ["generator", Q("roomkey_gen_schematics")],
          ["layer", Q("F.Cu")], ["descr", Q(descr)], ["attr", "smd"],
          fp_text("Reference", "REF**", (0, court[1] - 0.8), "F.SilkS"),
          fp_text("Value", name, (0, court[3] + 0.8), "F.Fab"),
          fp_rect(*fab, "F.Fab"), fp_rect(*court, "F.CrtYd", 0.05)] + list(silk) + pads
    return dump(fp) + "\n"


def smd_pad(num, x, y, w, h, shape="roundrect"):
    p = ["pad", Q(num), "smd", shape, ["at", x, y], ["size", w, h], ["layers", Q("F.Cu"), Q("F.Paste"), Q("F.Mask")]]
    if shape == "roundrect":
        p.append(["roundrect_rratio", 0.25])
    return p + [["uuid", uid("pad", num, x, y)]]


def footprints():
    out = {}
    # VEML6030: Vishay data sheet 84366 rev 1.8, p.10 "Recommended Footprint" (top view): pads 0.55 x 0.3,
    # outer span 2.3 x 1.6; right column top->bottom 3 INT, 2 SDA, 1 GND; left column 4 ADDR, 5 SCL, 6 VDD.
    pads = [smd_pad(str(n), x, y, 0.55, 0.3) for n, x, y in
            ((1, 0.875, 0.65), (2, 0.875, 0), (3, 0.875, -0.65), (4, -0.875, -0.65), (5, -0.875, 0), (6, -0.875, 0.65))]
    silk = [["fp_circle", ["center", 1.55, 1.05], ["end", 1.65, 1.05], ["stroke", ["width", 0.12], ["type", "default"]],
             ["fill", "yes"], ["layer", Q("F.SilkS")], ["uuid", uid("fp", "veml", "pin1")]]]
    out["Vishay_VEML6030_2x2mm"] = footprint(
        "Vishay_VEML6030_2x2mm", "Vishay VEML6030 ambient light sensor, 2 x 2 x 0.87 mm, land pattern per data sheet "
        "84366 rev 1.8 p.10; pin 1 = bottom right in the top view", pads, (-1, -1, 1, 1), (-1.4, -1.25, 1.4, 1.25), silk)
    # Mill-Max 0900 SMT spring pin: flange 1.83 mm -> 2.0 mm round pad [TBD: Mill-Max recommended land]
    out["PogoPin_MillMax_0900_SMD"] = footprint(
        "PogoPin_MillMax_0900_SMD", "Mill-Max 0900-x-15-20-7x-14-11-0 SMT spring pin, flange 1.83 mm; place on the "
        "H1 grid (2.54 mm): seen from the pin side, odd H1 pads are on the RIGHT (mirror of the board-back view)",
        [smd_pad("1", 0, 0, 2.0, 2.0, "circle")], (-0.92, -0.92, 0.92, 0.92), (-1.15, -1.15, 1.15, 1.15))
    # Kailh MX hot-swap socket CPG151101S11 under a 1u MX switch. Drawn as seen from the BACK (socket side), so it is
    # placed FLIPPED on the bottom: then the holes match KiCad's SW_Cherry_MX_1.00u_PCB seen from the front (centre
    # Ø4, pins at (2.54, -5.08) and (-3.81, -2.54), pegs at (+-5.08, 0)). Socket pads 2.55 x 2.5 outboard of the pin
    # holes [TBD: check against the Kailh drawing at layout].
    def npth(x, y, d):
        return ["pad", Q(""), "np_thru_hole", "circle", ["at", x, y], ["size", d, d], ["drill", d],
                ["layers", Q("*.Cu"), Q("*.Mask")], ["uuid", uid("npth", x, y, d)]]
    pads = [npth(0, 0, 4.0), npth(-2.54, -5.08, 3.0), npth(3.81, -2.54, 3.0), npth(-5.08, 0, 1.75), npth(5.08, 0, 1.75),
            smd_pad("1", -5.842, -5.08, 2.55, 2.5, "rect"), smd_pad("2", 7.085, -2.54, 2.55, 2.5, "rect")]
    out["SW_MX_Hotswap_Kailh_1.00u"] = footprint(
        "SW_MX_Hotswap_Kailh_1.00u", "Kailh CPG151101S11 MX hot-swap socket, 1u (19.05). Drawn from the socket side: "
        "place FLIPPED on the bottom layer, the switch plugs in from the front", pads, (-7, -7, 7, 7),
        (-7.6, -7.0, 8.8, 2.3))  # courtyard: socket body + switch holes (the rest of the 19 mm cell stays usable)
    return out


# ── project files ────────────────────────────────────────────────────────────────────────────────────────────────────
def write_project(folder, name, sheet):
    os.makedirs(folder, exist_ok=True)
    sheet.write(os.path.join(folder, name + ".kicad_sch"))
    pro = os.path.join(folder, name + ".kicad_pro")
    if not os.path.exists(pro):
        with open(pro, "w", encoding="utf-8", newline="\n") as f:
            f.write('{\n  "meta": {\n    "filename": "%s.kicad_pro",\n    "version": 3\n  }\n}\n' % name)
    for table, kind, uri in (("sym-lib-table", "sym_lib_table", "roomkey.kicad_sym"),
                             ("fp-lib-table", "fp_lib_table", "roomkey.pretty")):
        with open(os.path.join(folder, table), "w", encoding="utf-8", newline="\n") as f:
            f.write('(%s\n  (version 7)\n  (lib (name "roomkey")(type "KiCad")(uri "${KIPRJMOD}/../lib/%s")'
                    '(options "")(descr "RoomKey hub set"))\n)\n' % (kind, uri))
    problems = ["net %s reaches only %s" % (n, p) for n, p in sorted(sheet.netpins.items()) if len(p) < 2]
    problems += sheet.overlaps()
    for p in problems:
        print("  CHECK %s: %s" % (name, p))
    return problems


def main():
    os.makedirs(os.path.dirname(CUSTOM_LIB_PATH), exist_ok=True)
    with open(CUSTOM_LIB_PATH, "w", encoding="utf-8", newline="\n") as f:
        f.write(custom_lib_text())
    pretty = os.path.join(HERE, "lib", "roomkey.pretty")
    os.makedirs(pretty, exist_ok=True)
    for name, text in footprints().items():
        with open(os.path.join(pretty, name + ".kicad_mod"), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    total = 0
    for folder, name, make in (("hub", "roomkey-hub", hub), ("sht-tail", "roomkey-sht-tail", sht_tail),
                               ("pogo", "roomkey-pogo", pogo), ("glow-ring", "roomkey-glow-ring", glow_ring)):
        sheet = make()
        total += len(write_project(os.path.join(HERE, folder), name, sheet))
        print("wrote %s/%s.kicad_sch: %d parts" % (folder, name, len(sheet.parts)))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
