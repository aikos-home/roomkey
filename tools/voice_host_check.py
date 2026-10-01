#!/usr/bin/env python3
"""
voice_host_check.py — the key's voice v2 on the simulator, end to end against a fake door on this machine.

Runs the review build esphome/sim_v2_check.yaml (aikos_voice with push_samples(), no mic) and is its door: the key's
hold must reach the door as RTP (L16, 16 kHz) with its voice, nothing while another key has the floor ("besetzt"),
again once the floor is free, and nothing after the release. Nothing here talks to the house: the door is
127.0.0.1:5036, the key's RTP port 5034, its API port 6063, and it has no link to the real door or the bell.

    cd esphome && esphome compile sim_v2_check.yaml && python3 ../tools/voice_host_check.py
"""
from __future__ import annotations

import math
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

DOOR = ("127.0.0.1", 5036)
PROGRAM = Path(__file__).resolve().parent.parent / "esphome/.esphome/build/roomkey-v2check/.pioenvs/roomkey-v2check/program"
PT_L16 = 96


def main() -> int:
    if not PROGRAM.exists():
        print(f"build first: cd esphome && esphome compile sim_v2_check.yaml ({PROGRAM} is missing)")
        return 2
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(DOOR)
    sock.settimeout(0.2)
    packets: list[tuple[float, float]] = []     # (arrival, RMS of the L16 payload)
    stop = threading.Event()

    def receive():
        while not stop.is_set():
            try:
                data, _ = sock.recvfrom(4096)
            except socket.timeout:
                continue
            if len(data) < 12 or data[1] & 0x7F != PT_L16:
                continue
            body = data[12:len(data) - (len(data) - 12) % 2]
            samples = struct.unpack(f">{len(body) // 2}h", body) if body else ()
            rms = math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0.0
            packets.append((time.monotonic(), rms))

    rx = threading.Thread(target=receive, daemon=True)
    rx.start()
    marks: dict[str, tuple[float, str]] = {}
    proc = subprocess.Popen([str(PROGRAM)], cwd=PROGRAM.parent, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace", env=dict(os.environ, RK_V2CHECK="1"))
    deadline = time.monotonic() + 40
    for line in proc.stdout:
        line = re.sub(r"\x1b\[[0-9;]*m", "", line).strip()
        m = re.search(r"CHECK (\w+)(.*)", line)
        if m:
            marks[m.group(1)] = (time.monotonic(), m.group(2).strip())
            print("  " + line)
        if time.monotonic() > deadline:
            proc.kill()
            break
    proc.wait(timeout=5)
    stop.set()
    rx.join()

    def window(a: str, b: str, skip: float = 0.3):
        t0, t1 = marks[a][0] + skip, marks[b][0]
        got = [r for t, r in packets if t0 <= t <= t1]
        return len(got), (sorted(got)[len(got) // 2] if got else 0.0)

    def field(mark: str, name: str) -> int:
        m = re.search(rf"{name}=(-?\d+)", marks[mark][1])
        return int(m.group(1)) if m else -1

    need = ["hold", "door_call", "talking", "floor_other", "busy", "floor_free", "release", "done"]
    missing = [k for k in need if k not in marks]
    if missing:
        print(f"FAIL: the simulator did not get through the check (missing: {', '.join(missing)})")
        return 1
    talk_n, talk_rms = window("door_call", "talking")
    busy_n, _ = window("floor_other", "floor_free")
    free_n, free_rms = window("floor_free", "release")
    after_n, _ = window("release", "done")
    checks = [
        ("holding: the voice reaches the door", talk_n >= 50 and talk_rms > 1000, f"{talk_n} packets, median RMS {talk_rms:.0f}"),
        ("holding: talk on, key_state 2, not busy", (field("talking", "talking"), field("talking", "key_state"),
                                                     field("talking", "busy")) == (1, 2, 0), marks["talking"][1]),
        ("another key has the floor: busy on the key and the screen", (field("busy", "busy"), field("busy", "screen")) == (1, 1),
         marks["busy"][1]),
        ("busy: nothing is sent", busy_n == 0, f"{busy_n} packets"),
        ("floor free: the voice comes back", free_n >= 30 and free_rms > 1000, f"{free_n} packets, median RMS {free_rms:.0f}"),
        ("released: nothing is sent, not talking", after_n == 0 and field("done", "talking") == 0 and field("done", "key_state") < 2,
         f"{after_n} packets, {marks['done'][1]}"),
    ]
    for name, ok, detail in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {name}  ({detail})")
    failed = sum(not ok for _, ok, _ in checks)
    print("all ok" if not failed else f"{failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
