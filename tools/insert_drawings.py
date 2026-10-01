#!/usr/bin/env python3
"""To-scale 2D drawings of the RoomKey wall insert (DRAFT, version from insert_params.VERSION): front views, sections, layer plans,
key-module section and the installation-topology sheet.

    python3 tools/insert_drawings.py            # needs numpy + matplotlib
Reads hardware/cad/insert_params.py (dimensions) and hardware/drawings/sections/*.json (true section
polylines cut from the CAD solids by make_insert_L.py / make_insert_S.py; run those first). Writes PNGs
to hardware/drawings/. Every to-scale sheet: equal x/y scale, 5 mm grid, 10 mm scale bar, mm.
"""
import json
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import PathPatch, Circle, Rectangle, FancyBboxPatch  # noqa: E402
from matplotlib.path import Path  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hardware", "cad"))
import insert_params as P  # noqa: E402

R = P.R
OUT = os.path.join(ROOT, "hardware", "drawings")
SECT = os.path.join(OUT, "sections")
DATE = "2026-10-01"
VER = f"v{P.VERSION} DRAFT"
PRESSED_C = "#C0392B"

STYLE = {  # name prefix → (face, edge, legend label); longest prefix wins
    "plate": ("#FBFAF6", "#555048", "printed: plate (ivory face, black core)"),
    "chassis": ("#D9D4C8", "#4A463E", "printed: chassis + flange + duct"),
    "collar": ("#CFE8F2", "#3C7F99", "printed: light-guide collar (natural PETG)"),
    "switch plate": ("#C9C2B3", "#4A463E", "printed: switch plate"),
    "key shell": ("#FFFFFF", "#333333", "printed: key shell"),
    "touch board": ("#2B2B2E", "#000000", "touch board (ref)"),
    "antenna chip": ("#E74C3C", "#7B1F16", "chip antenna (ref)"),
    "MX switch": ("#8C5A3C", "#4A2A18", "MX switch (ref)"),
    "MX stem": ("#B07A5A", "#4A2A18", "MX switch (ref)"),
    "switch": ("#7A4FA0", "#3E2358", "B3FS-1002P (SMD) on FR4 carrier (ref)"),
    "plunger": ("#A98BC7", "#3E2358", "B3FS-1002P (SMD) on FR4 carrier (ref)"),
    "mic carrier": ("#4C7FD6", "#1F3F7A", "I²S MEMS mic on 8 × 8 carrier (ref)"),
    "LED": ("#F2C12E", "#8A6A00", "SK6812 MINI (ref)"),
    "speaker": ("#F08A2C", "#8A4300", "speaker 2030 (ref)"),
    "hub": ("#5FAE63", "#2E6B32", "hub board envelope (ref, TBD)"),
    "cable loop": ("#9AD1C9", "#2A7065", "cable U-loop envelope"),
    "box screw": ("#888888", "#333333", "box screws"),
    "load plate": ("#B8B8C8", "#333344", "stainless load plates"),
    "plate glow rim": ("#DDF3FA", "#3C7F99", "printed: translucent glow rim of the plate"),
    "preload pad": ("#6E6E6E", "#2E2E2E", "soft preload pads (compressed)"),
    "speaker face gasket": ("#3A3A3A", "#111111", "speaker face gasket (foam)"),
    "speaker back foam": ("#3A3A3A", "#111111", "speaker back foam strip (compressed)"),
    "WAGO": ("#F7E3C4", "#C76E00", "5 × WAGO 221-412 (ref)"),
    "box": ("#E8D9BE", "#9C8663", "flush box 40 mm (ref)"),
    "frame": ("#F3EEDD", "#A89D7C", "frame (ref, TBD)"),
}
ORDER = ["box", "frame", "WAGO", "chassis", "collar", "hub", "cable loop", "speaker", "speaker face gasket", "speaker back foam",
         "load plate",
         "preload pad", "switch plate", "MX switch", "MX stem",
         "switch", "plunger", "mic carrier", "LED", "plate", "plate glow rim", "box screw", "key shell", "touch board",
         "antenna chip"]


def _best(name, keys):
    best = None
    for k in keys:
        if name.startswith(k) and (best is None or len(k) > len(best)):
            best = k
    return best


def style_of(name):
    k = _best(name, STYLE)
    return STYLE[k] if k else ("#DDDDDD", "#444444", name)


def rank(name):
    k = _best(name, ORDER)
    return ORDER.index(k) if k else len(ORDER)


def _area(loop):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
        a += x0 * y1 - x1 * y0
    return a / 2


def _inside(pt, loop):
    x, y = pt
    c = False
    for (x0, y0), (x1, y1) in zip(loop, loop[1:] + loop[:1]):
        if (y0 > y) != (y1 > y) and x < (x1 - x0) * (y - y0) / (y1 - y0 + 1e-12) + x0:
            c = not c
    return c


def body_path(loops):
    verts, codes = [], []
    for i, lp in enumerate(loops):
        depth = sum(1 for j, other in enumerate(loops) if j != i and _inside(lp[0], other))
        want_ccw = depth % 2 == 0
        if (_area(lp) > 0) != want_ccw:
            lp = lp[::-1]
        verts += lp + [lp[0]]
        codes += [Path.MOVETO] + [Path.LINETO] * (len(lp) - 1) + [Path.CLOSEPOLY]
    return Path(verts, codes)


def _loops(sec, name, flip_d=True):
    loops = sec["bodies"][name]
    if sec["axis"] in ("x", "y") and flip_d:
        loops = [[(u, -d) for (u, d) in lp] for lp in loops]
    return loops


def draw_section(ax, sec, flip_d=True, only=None, skip=None, lw=0.6):
    """sec = {"axis", "value", "bodies": {name: [loops]}}; loops in (u, d): u horizontal, d down (into the wall)."""
    seen = set(l.get_label() for l in ax.patches)
    for name in sorted(sec["bodies"], key=rank):
        if only and not any(name.startswith(o) for o in only):
            continue
        if skip and any(name.startswith(o) for o in skip):
            continue
        face, edge, lab = style_of(name)
        patch = PathPatch(body_path(_loops(sec, name, flip_d)), facecolor=face, edgecolor=edge, lw=lw,
                          label=None if lab in seen else lab, zorder=2 + rank(name) * 0.01)
        seen.add(lab)
        ax.add_patch(patch)


def draw_pressed(ax, sec, names, label="pressed state (dashed)"):
    first = True
    for name in names:
        if name not in sec["bodies"]:
            continue
        ax.add_patch(PathPatch(body_path(_loops(sec, name)), facecolor="none", edgecolor=PRESSED_C, lw=0.55, ls=(0, (3, 1.5)),
                               zorder=6, label=label if first else None))
        first = False


def dim(ax, p0, p1, text, off=0.0, horiz=True, color="#1A1A1A", fs=6.5, ext=True):
    (x0, y0), (x1, y1) = p0, p1
    if horiz:
        y = y0 + off
        if ext:
            ax.plot([x0, x0], [y0, y], color=color, lw=0.35)
            ax.plot([x1, x1], [y1, y], color=color, lw=0.35)
        ax.annotate("", xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle="<->", lw=0.5, color=color, shrinkA=0, shrinkB=0))
        ax.text((x0 + x1) / 2, y + 0.4, text, ha="center", va="bottom", fontsize=fs, color=color,
                bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.8), zorder=20)
    else:
        x = x0 + off
        if ext:
            ax.plot([x0, x], [y0, y0], color=color, lw=0.35)
            ax.plot([x1, x], [y1, y1], color=color, lw=0.35)
        ax.annotate("", xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle="<->", lw=0.5, color=color, shrinkA=0, shrinkB=0))
        ax.text(x + 0.5, (y0 + y1) / 2, text, ha="left", va="center", fontsize=fs, color=color,
                bbox=dict(fc="white", ec="none", pad=0.3, alpha=0.8), zorder=20)


def note(ax, xy, xytext, text, fs=5.5):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=fs, zorder=21,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.2),
                arrowprops=dict(arrowstyle="-", lw=0.4, color="#333333"))


def frame_axes(ax, xlim, ylim, title, xlabel, ylabel):
    ax.set_aspect("equal")
    ax.set_title(title, fontsize=8.5, loc="left", fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=7)
    ax.set_ylabel(ylabel, fontsize=7)
    ax.tick_params(labelsize=6)

    def ticks(lo, hi, step):
        return list(range(int(math.ceil(lo / step) * step), int(math.floor(hi)) + 1, step))
    ax.set_xticks(ticks(*xlim, 10))
    ax.set_yticks(ticks(*ylim, 10))
    ax.set_xticks(ticks(*xlim, 5), minor=True)
    ax.set_yticks(ticks(*ylim, 5), minor=True)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.grid(which="both", color="#E6E6E6", lw=0.3, zorder=0)
    ax.set_axisbelow(True)
    if ylabel.startswith("d"):              # sections plot −d upward: label the ticks with d itself (positive into the wall)
        from matplotlib.ticker import FuncFormatter
        ax.yaxis.set_major_formatter(FuncFormatter(lambda val, _: f"{-val:g}"))
    x0, y0 = xlim[0] + 2, ylim[0] + 2
    ax.plot([x0, x0 + 10], [y0, y0], color="black", lw=2, zorder=30)
    ax.text(x0 + 5, y0 + 0.8, "10 mm", ha="center", fontsize=6, zorder=30)


def title_block(fig, text):
    fig.text(0.01, 0.005, text, fontsize=6.5, color="#333333", ha="left", va="bottom")


def depth_lines(ax, xr, left=False):
    floor = P.box_floor()
    lines = [(0.0, "plate front d = 0"), (P.DECK_D0, f"deck d = {P.DECK_D0}..{P.DECK_D1}"),
             (P.WALL_D, f"wall / box rim d = {P.WALL_D} [TBD Q1]"),
             (floor, f"usable floor of a {P.BOX_DEPTH:.0f} mm box d = {floor:.1f} [TBD Q5]")]
    for d, t in lines:
        ax.plot(xr, [-d, -d], color="#7A7A7A", lw=0.5, ls=(0, (6, 3)), zorder=1)
        ax.text(xr[0] + 0.5 if left else xr[1] - 0.5, -d + 0.35, t, fontsize=5.5, ha="left" if left else "right",
                va="bottom", color="#555555", zorder=25)


def legend(ax, loc="lower left", ncol=1):
    h, lab = ax.get_legend_handles_labels()
    uniq = {}
    for hh, ll in zip(h, lab):
        uniq.setdefault(ll, hh)
    ax.legend(uniq.values(), uniq.keys(), fontsize=5.3, loc=loc, ncol=ncol, framealpha=0.92)


def fig_legend(fig, axs, ncol=6):
    uniq = {}
    for ax in axs:
        h, lab = ax.get_legend_handles_labels()
        for hh, ll in zip(h, lab):
            uniq.setdefault(ll, hh)
    fig.legend(uniq.values(), uniq.keys(), fontsize=6.2, loc="lower center", ncol=ncol, bbox_to_anchor=(0.5, 0.03),
               framealpha=0.95)


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, facecolor="white")
    plt.close(fig)
    return path


def plate_role(v):
    return ("plate press → 12 V pulse on PLATE → ES75 / coupling relay toggles the light (hard-wired, no software)"
            if v == "L" else "plate press → ESP input (PLATE_SENSE) → HA: room light (needs a smart light) or a scene; "
                             "the socket is gone")


# ================================================================================ front view
def front_view(v, secs):
    fig, ax = plt.subplots(figsize=(8.8, 8.8), dpi=200)
    lim = 44
    frame_axes(ax, (-lim, lim), (-lim, lim), f"Variant {v}: front view (hidden parts dashed)", "x [mm]", "y [mm]")
    fo, fi = P.FRAME_OUT / 2, P.FRAME_OPEN / 2
    ax.add_patch(FancyBboxPatch((-fo, -fo), 2 * fo, 2 * fo, boxstyle="round,pad=0,rounding_size=4", fc="#F3EEDD",
                                ec="#A89D7C", lw=0.8, zorder=1, label="frame (ref, TBD)"))
    ax.add_patch(Rectangle((-fi, -fi), 2 * fi, 2 * fi, fc="#EDE7D3", ec="#A89D7C", lw=0.5, zorder=1.1))
    draw_section(ax, secs["F_d1"], flip_d=False, only=["plate"])            # plate with its 2 × 52 holes, true CAD cut
    ax.add_patch(FancyBboxPatch((-P.CUT_W / 2, -P.CUT_H / 2), P.CUT_W, P.CUT_H, boxstyle=f"round,pad=0,rounding_size={P.CUT_R}",
                                fc="#2A2A2A", ec="none", zorder=4.5, label="shadow gap 1.0"))
    ax.add_patch(FancyBboxPatch((-P.CUT_W / 2 - P.GLOW_RIM_W, -P.CUT_H / 2 - P.GLOW_RIM_W), P.CUT_W + 2 * P.GLOW_RIM_W,
                                P.CUT_H + 2 * P.GLOW_RIM_W, boxstyle=f"round,pad=0,rounding_size={P.CUT_R + P.GLOW_RIM_W}",
                                fc="none", ec="#3C9FC9", lw=2.2, zorder=4.6, label=f"glow ring = translucent plate rim {P.GLOW_RIM_W}"))
    ax.add_patch(FancyBboxPatch((-P.KEY_W / 2, -P.KEY_H / 2), P.KEY_W, P.KEY_H, boxstyle=f"round,pad=0,rounding_size={P.KEY_R}",
                                fc="#FFFFFF", ec="#333333", lw=0.8, zorder=5, label="printed: key shell"))
    ax.add_patch(FancyBboxPatch((-R.TB_W / 2, -R.TB_H / 2), R.TB_W, R.TB_H, boxstyle=f"round,pad=0,rounding_size={R.TB_CORNER_R}",
                                fc="#1E1E20", ec="#000000", lw=0.5, zorder=6, label="touch board (ref)"))
    ax.add_patch(FancyBboxPatch((-R.TB_ACTIVE_W / 2, -R.TB_ACTIVE_H / 2 - 1.2), R.TB_ACTIVE_W, R.TB_ACTIVE_H,
                                boxstyle="round,pad=0,rounding_size=2.5", fc="#34343A", ec="#555555", lw=0.4, zorder=7))
    ax.text(0, 9.5, f"active\n{R.TB_ACTIVE_W} × {R.TB_ACTIVE_H}", color="#BBBBBB", fontsize=5.5, ha="center", va="center", zorder=8)
    # collar ring (visible as the glow ring between key and plate)
    ax.add_patch(FancyBboxPatch((-P.COLLAR_OUT_X, -P.COLLAR_OUT_Y), 2 * P.COLLAR_OUT_X, 2 * P.COLLAR_OUT_Y,
                                boxstyle=f"round,pad=0,rounding_size={P.COLLAR_OUT_R}", fc="none", ec="#3C7F99", lw=0.7,
                                ls="--", zorder=9, label="light-guide collar (behind the gap)"))
    # hidden components (dashed outlines from the layout envelopes)
    E = {e["name"]: e for e in P.layout(v)}
    hidden = ["switch TL", "switch TR", "switch BL", "switch BR", "mic carrier", "LED 1", "LED 2", "LED 3", "LED 4",
              "preload pad 1", "preload pad 2", "preload pad 3",
              "speaker 2030", "duct", "hub", "cable loop", "antenna chip", "WAGO 1", "WAGO 2", "WAGO 3", "WAGO 4", "WAGO 5"]
    for nm in hidden:
        e = E[nm]
        _, edge, lab = style_of(nm if nm != "duct" else "chassis")
        if nm.startswith("WAGO"):
            ax.add_patch(Rectangle((e["x0"], e["y0"]), e["x1"] - e["x0"], e["y1"] - e["y0"], fc="none", ec=edge, lw=0.5,
                                   ls=":", zorder=9))
            continue
        ax.add_patch(Rectangle((e["x0"], e["y0"]), e["x1"] - e["x0"], e["y1"] - e["y0"], fc="none", ec=edge, lw=0.7,
                               ls="--", zorder=9))
    for (x, y) in P.SW_POS:
        ax.add_patch(Circle((x, y), P.SW_PLUNGER_D / 2, fc="none", ec="#3E2358", lw=0.6, ls="--", zorder=9))
    # box, domes, screws
    ax.add_patch(Circle((0, 0), P.BOX_OPEN_D / 2, fc="none", ec="#9C8663", lw=0.8, ls="-.", zorder=10, label="box opening Ø60 [DS]"))
    ax.add_patch(Circle((0, 0), P.BOX_USABLE_D / 2, fc="none", ec="#9C8663", lw=0.6, ls=":", zorder=10, label="usable Ø58 [TBD Q5]"))
    for ang in P.BOX_DOME_ANGLES:
        a = math.radians(ang)
        ca, sa = round(math.cos(a)), round(math.sin(a))
        r0, w = P.BOX_DOME_R_IN, P.BOX_DOME_W / 2
        if ca:
            ax.add_patch(Rectangle((min(ca * r0, ca * 30), -w), abs(30 - r0), 2 * w, fc="none", ec="#9C8663", lw=0.5, ls=":", zorder=10))
        else:
            ax.add_patch(Rectangle((-w, min(sa * r0, sa * 30)), 2 * w, abs(30 - r0), fc="none", ec="#9C8663", lw=0.5, ls=":", zorder=10))
    for sx in (-1, 1):
        ax.add_patch(Circle((sx * 30, 0), P.SCREW_HEAD_D / 2, fc="#BBBBBB", ec="#333333", lw=0.6, zorder=11,
                            label="box screw on load plate (±30, 0)"))
    # dimensions
    h = P.HALF
    dim(ax, (-h, h), (h, h), "plate 55.0 [MEAS, FROZEN]", off=11.0)
    dim(ax, (-P.CUT_W / 2, P.CUT_H / 2), (P.CUT_W / 2, P.CUT_H / 2), f"cut-out {P.CUT_W:.2f} × {P.CUT_H:.1f}", off=7.5)
    dim(ax, (-h, -h), (-P.CUT_W / 2, -h), f"wing {h - P.CUT_W / 2:.2f}", off=-5.0)
    dim(ax, (-P.KEY_W / 2, -P.KEY_H / 2), (P.KEY_W / 2, -P.KEY_H / 2), f"key {P.KEY_W:.2f} × {P.KEY_H:.1f}", off=-9.0)
    dim(ax, (h, -h), (h, h), "55.0", off=10.0, horiz=False)
    dim(ax, (h, P.CUT_H / 2), (h, h), f"band {h - P.CUT_H / 2:.2f}", off=2.5, horiz=False, fs=5.5)
    # notes
    note(ax, (P.PERF_XS[-1], P.PERF_YS[0]), (26, -39.5), f"{P.PERF_COLS} × {P.PERF_ROWS} holes Ø{P.PERF_D} pitch {P.PERF_PITCH}\n"
         f"per wing + black mesh behind")
    note(ax, P.MIC_PORT, (-43, 33), "mic port (carrier bonded to the plate back)")
    note(ax, P.LED_POS[0], (-43, 29.5), "SK6812 MINI (4) behind the collar corners")
    note(ax, P.SW_POS[0], (-43, 37), "B3FS-1002P on FR4 carrier, one per wing corner (4)")
    note(ax, (P.SPK_X0 + 2, -12), (23, -34.5), "speaker on edge → duct → right strip")
    note(ax, (0, R.TB_ANT[1]), (-43, -33), "chip antenna (on the PCB back)")
    note(ax, (-10, h - 0.3), (-43, 41.5), "top edge: rigid drawer lip (3 segments between the rims); bottom: 2 snap lips on deck tongues")
    for sx in (-1, 1):
        ax.add_patch(Rectangle((sx * P.TONGUE_X[0] if sx > 0 else -P.TONGUE_X[1], -P.DECK_HALF_Y), P.TONGUE_X[1] - P.TONGUE_X[0],
                               P.TONGUE_W, fc="none", ec="#4A463E", lw=0.7, ls="--", zorder=9))
    note(ax, (-(P.SNAP_X[0] + P.SNAP_X[1]) / 2, -P.DECK_HALF_Y + 0.4), (-43, -37.5), "snap lip on a flexible deck tongue (2)")
    note(ax, (P.HUB[0] + 1, P.HUB[3] - 1), (-43, 25.5), "hub board (behind the switch plate, d 25.5–37.5)")
    note(ax, (-5, -6), (-43, -27), "cable U-loop (behind the MX bodies)")
    ax.text(0, -41.8, plate_role(v), fontsize=6, ha="center", color="#7B1F16" if v == "L" else "#1F3F7A",
            bbox=dict(fc="white", ec="#BBBBBB", pad=0.4), zorder=22)
    legend(ax, "upper right")
    title_block(fig, f"RoomKey wall insert {VER}, Variant {v}, {DATE}. mm, grid 5 mm. Dashed = behind the plate. "
                     f"[TBD] = to be measured. Plate + holes cut from the CAD solid at d = 1.")
    fig.tight_layout()
    return save(fig, f"insert-{v}_front.png")


# ================================================================================ vertical sections (y–d)
def key_chain(ax, x, y_lab):
    s = P.KS
    chain = [(s["glass"], "glass"), (s["pcb_front"], "PCB"), (s["standoff_end"], "standoffs"), (s["key_back"], "key back"),
             (s["mx_top"], "MX housing top"), (s["plate_front"], "switch plate"), (s["mx_pins"], "MX pins")]
    for (d0, _), (d1, _) in zip(chain, chain[1:]):
        dim(ax, (x, -d0), (x, -d1), f"{d1 - d0:.1f}", off=0, horiz=False, fs=5.2, ext=False)
    last = 99
    for d, n in chain:
        ty = min(-d, last - 1.9)
        last = ty
        ax.text(y_lab, ty, f"{n}  d = {d:+.1f}", fontsize=5.2, va="center", zorder=25,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.1))


def sections_sheet(v, secs, pressed):
    floor = P.box_floor()
    fig, axs = plt.subplots(1, 3, figsize=(22, 7.4), dpi=170, gridspec_kw=dict(width_ratios=[108, 88, 88]))
    spec = [("AA_x0", "A–A at x = 0 (key, MX switches, cable loop, hub)",
             ["key shell (pressed)", "touch board (pressed)", "plate (top band pressed)"]),
            ("DD_xsw", f"D–D at x = {P.SW_POS[1][0]:+.1f} (right wing: switches TR/BR, preload pads, top lip, bottom skirt)", ["plate (top band pressed)"]),
            ("EE_xmic", f"E–E at x = {P.MIC_PORT[0]:+.2f} (left wing: mic carrier, switches TL/BL)", [])]
    for ax, (k, title, pr) in zip(axs, spec):
        xr = (-44, 64) if k == "AA_x0" else (-44, 44)
        frame_axes(ax, xr, (-floor - 4, 12), f"Variant {v}: section {title}", "y [mm]", "d [mm] (into the wall ↓)")
        draw_section(ax, secs[k])
        if pressed and k in pressed and pr:
            draw_pressed(ax, pressed[k], pr)
        depth_lines(ax, (-44, 44), left=(k != "AA_x0"))
        if k == "AA_x0":
            key_chain(ax, 45.5, 47.0)
            note(ax, (P.LOOP_Y[0] + 2, -(P.LOOP_D0 + 6)), (-43, -44), "rolling U-loop of the flat cable (R 4)")
            note(ax, (18, -(P.HUB[4] + 3)), (8, -50), "hub envelope (buck, amp, protection) [TBD]")
            note(ax, (0, -P.COLLAR_D0 - 3), (-43, 8), "collar = light guide behind the plate's glow rim")
            ax.text(-43, -30, f"dashed red: key fully pressed ({P.KEY_TRAVEL:.2f}, to MX bottom-out like a keycap)\nand plate "
                              f"pressed on the top band (tips about the bottom snaps)",
                    fontsize=5.5, color=PRESSED_C, zorder=25)
        if k == "DD_xsw":
            tip, front, back, cback = P.sw_depths()
            note(ax, (P.SW_POS[1][1], -tip), (4, 8), f"nominal: nub gap {P.NUB_GAP} → click after {P.NUB_GAP + P.SW_PT:.2f}, stop at "
                 f"{P.NUB_GAP + P.SW_TRAVEL_TOTAL:.2f} [TBD] (tolerances: doc §5.1)")
            note(ax, (P.DECK_HALF_Y, -P.LIP_D0), (30, -16), f"top drawer lip hooks {P.LIP_IN - (P.HALF - P.PLATE_SKIRT_T - P.DECK_HALF_Y):.1f}"
                 f" behind the deck")
            note(ax, (-P.DECK_HALF_Y, -P.SKIRT_D), (-43, -16), "bottom skirt locates on the deck edge\n(snap lips at |x| 22.5–25.5: sheet 'retention')")
            note(ax, (31.0, -(P.WALL_D - 0.6)), (14, -24), "flange 1.2 under the frame; box screws at (±30, 0)")
        if k == "EE_xmic":
            note(ax, (P.MIC_PORT[1], -P.MIC_FACE_D - 1), (18, 8), "mic carrier bonded to the plate (moves with it),\nclearance pocket in the chassis")
    fig_legend(fig, axs, ncol=7)
    title_block(fig, f"RoomKey wall insert {VER}, Variant {v}: vertical sections cut from the CAD solids, {DATE}, mm. "
                     f"Grey dashed: plate front, deck, wall plane [TBD], usable box floor.")
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    return save(fig, f"insert-{v}_sections.png")


# ================================================================================ horizontal sections (x–d)
def plan_sheet(v, secs, pressed):
    floor = P.box_floor()
    fig, axs = plt.subplots(1, 3, figsize=(21, 7.0), dpi=170)
    spec = [("BB_y0", "B–B at y = 0 (speaker on edge + back foam, key, screws, cable loop)", []),
            ("CC_ymic", f"C–C at y = {P.MIC_PORT[1]:+.1f} (mic | key, MX 1 | duct, hub)", []),
            ("GG_ysw", f"G–G at y = {P.SW_POS[2][1]:+.1f} (switches BL/BR, MX 2, WAGO 1–3)",
             ["plate (left wing pressed)", "key shell (pressed)", "touch board (pressed)"])]
    for ax, (k, title, pr) in zip(axs, spec):
        frame_axes(ax, (-44, 44), (-floor - 4, 12), f"Variant {v}: section {title}", "x [mm]", "d [mm] (into the wall ↓)")
        draw_section(ax, secs[k])
        if pressed and k in pressed and pr:
            draw_pressed(ax, pressed[k], pr)
        depth_lines(ax, (-44, 44))
        for sx in (-1, 1):
            ax.plot([sx * P.BOX_USABLE_D / 2] * 2, [-P.WALL_D, -floor], color="#9C8663", lw=0.5, ls=":")
        if k == "BB_y0":
            note(ax, (P.SPK_X0 + R.SPK_T / 2, -(P.SPK_D0 + 8)), (22, -44), "speaker 2030 on edge, grille → +x → duct")
            note(ax, (30, -(P.WALL_D - 1)), (24, 8), "box screw on a stainless load plate")
        if k == "GG_ysw":
            ax.text(-43, -30, "dashed red: key pressed and\nplate pressed on the left wing\n(tips about the right lip ends)",
                    fontsize=5.5, color=PRESSED_C, zorder=25)
    fig_legend(fig, axs, ncol=7)
    title_block(fig, f"RoomKey wall insert {VER}, Variant {v}: horizontal sections cut from the CAD solids, {DATE}, mm. "
                     f"Brown dotted: usable box Ø58 [TBD].")
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    return save(fig, f"insert-{v}_plan-sections.png")


def layers_sheet(v, secs):
    fig, axs = plt.subplots(1, 3, figsize=(16.5, 6.9), dpi=180)
    for ax, (k, t) in zip(axs, [("F_d6", "d = 6.3: behind the deck (switches, mic, speaker, duct)"),
                                ("F_d14", "d = 13.5: LEDs, rear wall, MX housings"),
                                ("F_d30", "d = 30: hub + cable loop in the box")]):
        frame_axes(ax, (-38, 38), (-38, 38), f"Variant {v}: cut at {t}", "x [mm]", "y [mm]")
        draw_section(ax, secs[k], flip_d=False, skip=["frame"])
        ax.add_patch(Circle((0, 0), P.BOX_USABLE_D / 2, fc="none", ec="#9C8663", lw=0.6, ls=":"))
        ax.add_patch(Rectangle((-P.FRAME_OPEN / 2, -P.FRAME_OPEN / 2), P.FRAME_OPEN, P.FRAME_OPEN, fc="none", ec="#A89D7C",
                               lw=0.5, ls="--"))
    fig_legend(fig, axs, ncol=6)
    title_block(fig, f"RoomKey wall insert {VER}, Variant {v}: cuts parallel to the wall (front-view orientation), {DATE}. "
                     f"Dotted circle = usable box Ø58 [TBD], dashed square = frame opening [TBD].")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    return save(fig, f"insert-{v}_layers.png")


def key_module_sheet(secs, pressed):
    fig, ax = plt.subplots(figsize=(10.0, 6.6), dpi=220)
    s = P.KS
    frame_axes(ax, (-32, 32), (-27, 11), "Key module: section A–A at x = 0 (both MX switches, stem posts, collar)",
               "y [mm]", "d [mm]")
    draw_section(ax, secs["AA_x0"], only=["key shell", "touch board", "antenna chip", "MX switch", "MX stem", "switch plate",
                                          "collar", "chassis", "plate"])
    if pressed:
        draw_pressed(ax, pressed["AA_x0"], ["key shell (pressed)", "touch board (pressed)"], label="key fully pressed (dashed)")
    chain = [(s["glass"], "glass (key front)"), (s["pcb_front"], "PCB front"), (s["pcb_back"], "PCB back"),
             (s["standoff_end"], "brass standoffs end"), (s["key_back"], "key back"), (s["post_end"], "stem post end"),
             (s["mx_top"], "MX housing top"), (s["plate_front"], "switch plate front"), (s["plate_back"], "switch plate back"),
             (s["mx_bottom"], "MX housing bottom"), (s["mx_pins"], "MX pin tips")]
    x = 27.5
    for (d0, _), (d1, _) in zip(chain, chain[1:]):
        dim(ax, (x, -d0), (x, -d1), f"{d1 - d0:.1f}", off=0, horiz=False, fs=5.0, ext=False)
    last = 99
    for d, n in chain:
        ax.plot([-26, x + 0.4], [-d, -d], color="#CCCCCC", lw=0.25, zorder=1)
        ty = min(-d, last - 1.3)
        last = ty
        ax.text(-31.5, ty, f"{n}: d = {d:+.1f}", fontsize=5.0, va="center", zorder=25,
                bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.1))
    ax.plot([-32, 32], [0, 0], color="#7A7A7A", lw=0.6, ls=(0, (6, 3)))
    ax.text(31, 0.4, "plate front d = 0", fontsize=5.5, ha="right")
    ax.text(0, 9.3, f"MX on the long axis (y {R.MX_SW_POS[0][1]:+.1f} / {R.MX_SW_POS[1][1]:+.1f}); key travel {P.KEY_TRAVEL:.2f} "
                    f"(stops at MX bottom-out; click at {R.MX_PRETRAVEL} ± 0.6); side skirts in the collar limit roll; end presses: desk rig",
            fontsize=5.5, ha="center")
    legend(ax, "lower right")
    title_block(fig, f"RoomKey key module {VER}, {DATE}, mm. MX data: Cherry MX drawing; board: Waveshare drawing.")
    fig.tight_layout()
    return save(fig, "key-module_section.png")


# ================================================================================ retention detail
def retention_sheet(v, secs, pressed):
    """zoomed sections of the plate retention: bottom snap lip on its tongue, top drawer lip, tongue plan."""
    fig, axs = plt.subplots(1, 3, figsize=(17, 6.6), dpi=190, gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    xs = (P.SNAP_X[0] + P.SNAP_X[1]) / 2
    tm = P.tongue_mech()
    # 1 bottom edge
    ax = axs[0]
    frame_axes(ax, (-30.5, -18.5), (-10.5, 1.5), f"H–H at x = {xs:+.1f}: bottom snap lip on the tongue", "y [mm]", "d [mm] ↓")
    draw_section(ax, secs["HH_xsnap"], lw=0.8)
    if pressed and "HH_xsnap" in pressed:
        draw_pressed(ax, pressed["HH_xsnap"], ["plate (top band pressed)"], label="plate pressed on the top band (dashed)")
    note(ax, (-P.DECK_HALF_Y + 0.3, -P.SNAP_D0), (-30, -9.6), f"catch face d {P.SNAP_D0}: lip {P.LIP_IN} in, overlap "
         f"{tm['overlap']:.1f}\nlead-in 45° × {P.SNAP_CHAMFER} on lip and tongue")
    note(ax, (-P.DECK_HALF_Y + P.TONGUE_W / 2, -5.0), (-24.5, -1.2), f"tongue {P.TONGUE_W} × {tm['h']:.1f} (deck + rib),\n"
         f"{tm['L']:.1f} long, flexes +y into a {P.TONGUE_SLOT} slot")
    note(ax, (-P.DECK_HALF_Y - 0.9, -7.8), (-30, -4.2), "flange window: room for\nthe lip at full press,\nrelease access")
    # 2 top edge
    ax = axs[1]
    frame_axes(ax, (18.5, 30.5), (-10.5, 1.5), f"H–H at x = {xs:+.1f}: top drawer lip (rigid deck edge)", "y [mm]", "d [mm] ↓")
    draw_section(ax, secs["HH_xsnap"], lw=0.8)
    if pressed and "HH_xsnap" in pressed:
        draw_pressed(ax, pressed["HH_xsnap"], ["plate (bottom band pressed)"], label="plate pressed on the bottom band (dashed)")
    note(ax, (P.DECK_HALF_Y - 0.3, -P.LIP_D0), (18.8, -9.6), f"catch face d {P.LIP_D0} on the deck back;\nhooked by a "
         f"{tm['overlap'] + 0.1:.1f} mm upward shift")
    # 3 plan at d 5.75
    ax = axs[2]
    frame_axes(ax, (0, 30), (-30, -14), "cut at d = 5.75 (bottom right): tongue rib, slot, snap lip, switch pocket",
               "x [mm]", "y [mm]")
    draw_section(ax, secs["F_d575"], flip_d=False, skip=["frame", "box"])
    ax.add_patch(Rectangle((P.SNAP_X[0], -(P.HALF - P.PLATE_SKIRT_T)), P.SNAP_X[1] - P.SNAP_X[0], P.LIP_IN, fc="none",
                           ec=PRESSED_C, lw=0.8, ls="--", label="snap lip (behind the tongue, d 6.5–7.1)"))
    for x in (P.TONGUE_X[0], P.TONGUE_X[1]):
        ax.plot([x, x], [-P.DECK_HALF_Y, -P.DECK_HALF_Y + P.TONGUE_W], color="#7B1F16", lw=0.6)
    ax.text(P.TONGUE_X[0] + 0.3, -P.DECK_HALF_Y - 1.4, f"tongue root |x| {P.TONGUE_X[0]} → free end {P.TONGUE_X[1]}; snap "
            f"strain {100 * tm['eps']:.2f} %, tip {tm['tip']:.2f}; pull at yield ≈ {tm['p_yield']:.1f} N / tongue [TBD material]",
            fontsize=5.6, zorder=25)
    fig_legend(fig, axs, ncol=6)
    title_block(fig, f"RoomKey wall insert {VER}, Variant {v}: plate retention (top lip rigid, bottom snap tongues), cut from the "
                     f"CAD solids, {DATE}, mm. Mount: tilt, hook the top lip (shift up), press the bottom edge until both snaps click.")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    return save(fig, f"insert-{v}_retention.png")


# ================================================================================ installation topologies (schematic)
def _blk(ax, x, y, w, h, text, fc, ec="#333333", fs=5.6, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08", fc=fc, ec=ec, lw=0.7))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal")


def _wire(ax, pts, color, text=None, ls="-", fs=5.2, at=0.5, dy=0.12):
    xs, ys = zip(*pts)
    ax.plot(xs, ys, color=color, lw=1.4, ls=ls, solid_capstyle="round")
    if text:
        i = max(0, min(len(pts) - 2, int(at * (len(pts) - 1))))
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        ax.text(mx, my + dy, text, fontsize=fs, ha="center", va="bottom", color=color,
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=0.1))


MAINS, SELV_C = "#C0392B", "#1F6F3A"
C_MAINS, C_SELV, C_KEY, C_DB = "#F6D5D1", "#D5EFDC", "#FFFFFF", "#ECECEC"


def topologies_sheet():
    fig, axs = plt.subplots(2, 4, figsize=(22, 10), dpi=160)
    for ax in axs.flat:
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 6)
        ax.axis("off")

    def key(ax, x, y, text="RoomKey insert\n(SELV only, 12 V in)"):
        _blk(ax, x, y, 2.3, 1.2, text, C_KEY, ec=SELV_C, bold=True)

    # T1 remote
    ax = axs[0, 0]
    ax.set_title("L · T1 remote (switch leg with ≥ 3 usable cores)", fontsize=8, loc="left", fontweight="bold")
    _blk(ax, 0.1, 4.2, 2.2, 1.4, "distribution board\nMCB ≤ 10 A for this\ncircuit + RCD 30 mA\n+ SPD type 2/3", C_DB, fs=5.2)
    _blk(ax, 3.5, 3.5, 4.0, 2.4, "T1a: luminaire canopy / ceiling box\nT1b: wall junction box (new/larger box)\n"
                                 "Eltako SNT61 12 V (6 W)\n+ ES75-12..24V UC (SELV input; LED rating\nconflicting, Q4b) or T1-LED: "
                                 "Finder 38.51\n+ ESR61NP in a surface DIN enclosure ≥ 95 deep", C_MAINS, ec=MAINS, fs=5.0)
    _blk(ax, 8.0, 4.4, 1.8, 1.0, "lamp", "#FFF6D6")
    key(ax, 4.3, 0.6)
    _wire(ax, [(2.3, 4.9), (3.5, 4.9)], MAINS, "L, N, PE")
    _wire(ax, [(7.5, 4.9), (8.0, 4.9)], MAINS, "sw. L")
    _wire(ax, [(5.5, 3.5), (5.5, 1.8)], SELV_C, "old switch-leg cable, now SELV:\n+12 V · 0 V · PLATE (3 cores)", at=0.5, dy=-0.9)
    ax.text(0.1, 0.05, "No N at the switch. PE stays PE (never a SELV conductor); the cable carries ONLY SELV after\n"
                       "conversion (0100-410 414.4), marked at both ends. ES75: ≤ 10 A protection [DS]. Two-way: T3, or T1 if ALL cores of both legs become SELV.",
            fontsize=5.2, color="#333333")
    # T2 two-chamber
    ax = axs[0, 1]
    ax.set_title("L · T2 two-chamber box at the switch (N in the box; Eltako OK)", fontsize=8, loc="left", fontweight="bold")
    _blk(ax, 0.1, 4.2, 2.2, 1.4, "distribution board\nMCB + RCD 30 mA\n+ SPD type 2/3", C_DB)
    ax.add_patch(Rectangle((3.2, 0.5), 6.5, 4.0, fc="none", ec="#555555", lw=0.8, ls="--"))
    ax.text(3.3, 4.2, "Kaiser 1068-02 Electronic-Dose (or successor),\npartition supplied; chamber 2 front geometry\nand cover: Q11 [TBD]",
            fontsize=5.1, va="top")
    ax.plot([6.3, 6.3], [0.5, 4.5], color="#333333", lw=2.2)
    ax.text(6.35, 0.6, "partition", fontsize=5.2, rotation=90)
    key(ax, 3.6, 2.0, "RoomKey insert\nchamber 1: SELV only")
    _blk(ax, 6.8, 2.6, 2.7, 1.5, "chamber 2 (230 V):\nSNT61 12 V\n+ ESR61NP-230V+UC", C_MAINS, ec=MAINS)
    _blk(ax, 6.8, 0.8, 2.7, 1.0, "→ lamp (switched L)", "#FFF6D6")
    _wire(ax, [(2.3, 4.9), (8.1, 4.9), (8.1, 4.1)], MAINS, "L, N, PE (N at the switch!)", at=0.0)
    _wire(ax, [(6.8, 3.2), (5.9, 3.2)], SELV_C, "+12 V · 0 V · PLATE", dy=0.1)
    ax.text(0.1, 0.05, "ESR61NP A1/A2: 'galvanisch getrennt' [DS], NOT declared SELV → only with Eltako's\n"
                       "written OK (Q4a); else T1/T3. Chamber 2 must stay closed/accessible per 0100-520.",
            fontsize=5.2, color="#333333")
    # T3 distribution board
    ax = axs[0, 2]
    ax.set_title("L · T3 distribution board (spare cable; two-way circuits)", fontsize=8, loc="left", fontweight="bold")
    _blk(ax, 0.1, 2.6, 4.2, 3.0, "distribution board\nDIN-rail PSU 12 V (IEC 61558-2-16,\n≤ 15 W or fused 0.5 A)\n"
                                 "+ coupling relay, reinforced\n(Finder 38.51 type, 6 kV / 8 mm)\n+ impulse relay (LED-rated)\n"
                                 "MCB + RCD 30 mA + SPD", C_DB, ec=MAINS, fs=5.2)
    _blk(ax, 7.5, 4.3, 2.3, 1.0, "lamp", "#FFF6D6")
    key(ax, 7.3, 1.0)
    _wire(ax, [(4.3, 4.8), (7.5, 4.8)], MAINS, "switched L (existing)")
    _wire(ax, [(4.3, 3.2), (6.2, 3.2), (6.2, 1.6), (7.3, 1.6)], SELV_C, "spare cable: +12 V · 0 V · PLATE", at=0.2)
    ax.text(0.1, 0.2, "Relay contact and 230 V stay in the board; only SELV runs to the switch.\n"
                      "Old legs of a two-way circuit are reused only if ALL their cores become SELV.",
            fontsize=5.2, color="#333333")
    # T4 keep switch
    ax = axs[0, 3]
    ax.set_title("L · T4 keep the old switch, RoomKey in an added box", fontsize=8, loc="left", fontweight="bold")
    _blk(ax, 0.3, 2.3, 2.5, 1.6, "old light switch\n(unchanged, 230 V box)", "#FFF6D6", ec=MAINS)
    key(ax, 3.6, 2.5, "RoomKey in a\nSEPARATE added box")
    _blk(ax, 6.9, 2.3, 2.9, 1.6, "own 12 V SELV feed:\nnew 2-core cable from a\nPSU elsewhere (board / T2)", C_SELV,
         ec=SELV_C, fs=5.2)
    _wire(ax, [(6.9, 3.1), (5.9, 3.1)], SELV_C, "+12 V · 0 V")
    ax.text(0.1, 0.4, "2-gang frame (switch + RoomKey); the boxes are NOT coupled openly (no 230 V in the\n"
                      "RoomKey box). The plate acts like Variant S (ESP input only). Light works as before.",
            fontsize=5.2, color="#333333")
    # S1 two-chamber at the socket
    ax = axs[1, 0]
    ax.set_title("S · S1 two-chamber box at the socket position (box change)", fontsize=8, loc="left", fontweight="bold")
    ax.add_patch(Rectangle((3.2, 0.9), 6.5, 3.8, fc="none", ec="#555555", lw=0.8, ls="--"))
    ax.plot([6.3, 6.3], [0.9, 4.7], color="#333333", lw=2.2)
    key(ax, 3.6, 2.2, "RoomKey insert\nchamber 1: SELV only")
    _blk(ax, 6.8, 2.6, 2.7, 1.6, "chamber 2 (230 V):\nSNT61 12 V\n+ WAGO 221 through-\nterminals L · N · PE", C_MAINS, ec=MAINS)
    _blk(ax, 0.1, 4.3, 2.4, 1.3, "socket circuit\n(MCB + RCD 30 mA)", C_DB)
    _wire(ax, [(2.5, 5.0), (8.1, 5.0), (8.1, 4.2)], MAINS, "L, N, PE in")
    _wire(ax, [(9.5, 3.2), (9.9, 3.2), (9.9, 0.4)], MAINS, "onward to next socket", at=0.9, dy=-0.1)
    _wire(ax, [(6.8, 3.2), (5.9, 3.2)], SELV_C, "+12 V · 0 V", dy=0.1)
    ax.text(0.1, 0.05, "The socket is lost. PE continues through the WAGO; the insert needs no PE (class III).\n"
                       "Socket circuits: 0100-410 411.3.3 RCD stays in force for the remaining sockets.",
            fontsize=5.2, color="#333333")
    # S2 remote 12 V, S3
    ax = axs[1, 1]
    ax.set_title("S · S2 remote 12 V (own cable), S3 keep the socket", fontsize=8, loc="left", fontweight="bold")
    _blk(ax, 0.1, 3.4, 3.2, 2.0, "12 V source elsewhere:\nT2/S1 chamber 2 nearby, or\nDIN-rail PSU in the board", C_SELV,
         ec=SELV_C)
    key(ax, 6.8, 3.8)
    _wire(ax, [(3.3, 4.4), (6.8, 4.4)], SELV_C, "own cable: +12 V · 0 V")
    _blk(ax, 0.1, 0.7, 4.0, 1.6, "old 230 V cable to this box:\ndisconnected at BOTH ends by the\nelectrician (or rerouted), never left\n"
                                 "live in the RoomKey chamber", C_MAINS, ec=MAINS, fs=5.3)
    _blk(ax, 5.0, 0.7, 4.8, 1.6, "S3: keep the socket, RoomKey in a SEPARATE\nadded box (not coupled openly), 2-gang\n"
                                 "frame, 12 V per S2", "#FFF6D6", fs=5.3)
    # T0 none
    ax = axs[1, 2]
    ax.set_title("T0 · no topology fits (no N, 2 cores, no spare cable)", fontsize=8, loc="left", fontweight="bold")
    _blk(ax, 0.3, 3.2, 4.2, 2.2, "the owner decides:\n• new cable (conduit / surface duct)\n  → then T1/T3\n"
                                 "• or no RoomKey at this position\n  (keep the switch / socket)", "#FFFFFF", ec="#555555", fs=5.6)
    _blk(ax, 5.2, 3.2, 4.5, 2.2, "never:\n• 230 V into the RoomKey box\n• PE or N used as a SELV conductor\n"
                                 "• SELV and 230 V in one cable", C_MAINS, ec=MAINS, fs=5.6)
    ax.text(0.1, 1.5, "T0 is a valid outcome, not a failure: the insert is SELV-only and never\nworks around a missing "
                      "cable with mains in its chamber.", fontsize=5.6, color="#333333")
    # decision guide
    ax = axs[1, 3]
    ax.set_title("Decision guide (the electrician decides per position, doc §9)", fontsize=8, loc="left", fontweight="bold")
    rows = [("switch leg: 2 usable cores (NYM-J 3×1.5)", "T2 (N in box) · T3 · T4 · T0"),
            ("switch leg: 3 cores (NYM-J 4×1.5)", "T1a / T1b (or T2 / T3)"),
            ("switch leg: 4 cores (NYM-J 5×1.5)", "T1 + light-state feedback core"),
            ("two-way / corridor circuit", "T3 (all old cores SELV) or T4"),
            ("LED lamp", "T1-LED · T2 · T3 (LED-rated relay)"),
            ("socket position", "S1 · S2 · S3"),
            ("any doubt", "T4 / S3 (keep the device) or T0")]
    for i, (a, b) in enumerate(rows):
        y = 5.2 - i * 0.7
        ax.text(0.1, y, a, fontsize=5.6, va="center")
        ax.text(6.0, y, "→ " + b, fontsize=5.6, va="center", fontweight="bold")
        ax.plot([0.1, 9.9], [y - 0.35, y - 0.35], color="#DDDDDD", lw=0.4)
    fig.suptitle(f"RoomKey insert v{P.VERSION} DRAFT: installation topologies (schematic, not to scale). Nothing here is "
                 "certified; 230 V work only by an electrician / company in the grid operator's installer register "
                 "(NAV §13); test per VDE 0100-600. Red = 230 V (certified devices only), green = SELV.",
                 fontsize=8.5, x=0.01, ha="left")
    title_block(fig, f"RoomKey wall insert {VER}, {DATE}. Product names are examples with checked data sheets "
                     f"(see insert_params.SOURCES); the electrician chooses per position (insert-design.md §9).")
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    return save(fig, "insert-topologies.png")


def main():
    made = []
    for v in P.VARIANTS:
        with open(os.path.join(SECT, f"insert-{v}_sections.json"), encoding="utf-8") as f:
            secs = json.load(f)
        pressed = None
        pp = os.path.join(SECT, f"insert-{v}-pressed_sections.json")
        if os.path.exists(pp):
            with open(pp, encoding="utf-8") as f:
                pressed = json.load(f)
        made.append(front_view(v, secs))
        made.append(sections_sheet(v, secs, pressed))
        made.append(plan_sheet(v, secs, pressed))
        made.append(layers_sheet(v, secs))
        made.append(retention_sheet(v, secs, pressed))
        if v == "L":
            made.append(key_module_sheet(secs, pressed))
    made.append(topologies_sheet())
    for m in made:
        print("wrote", os.path.relpath(m, ROOT))


if __name__ == "__main__":
    main()
