#!/usr/bin/env python3
"""
rtp_recorder.py — save RoomKey audio streams (RTP / L16 / 16 kHz mono) as WAV files.

Test receiver for the talk path: every stream becomes one WAV file (a pause of more than
2 s starts a new one). Prints duration, packets, lost packets and level per recording.

    python3 tools/rtp_recorder.py [--port 5006] [--out tools/recordings]

Point a key at it with its "TEST recorder address" entity: <this computer's IP>:5006.
Standard library only. Recordings are local files — never commit them (tools/recordings/ is gitignored).
"""
import argparse
import math
import socket
import struct
import time
import wave
from pathlib import Path

RATE, PT_L16, GAP_S = 16000, 96, 2.0


class Recording:
    def __init__(self, out: Path, src):
        out.mkdir(parents=True, exist_ok=True)
        self.path = out / f"roomkey_{time.strftime('%Y%m%d_%H%M%S')}_{src[0].replace('.', '-')}.wav"
        self.wav = wave.open(str(self.path), "wb")
        self.wav.setnchannels(1); self.wav.setsampwidth(2); self.wav.setframerate(RATE)
        self.src, self.t0, self.last = src, time.time(), time.time()
        self.pkts = self.lost = self.samples = 0
        self.seq = None
        self.sumsq = 0.0
        self.peak = 0
        print(f"● recording from {src[0]}:{src[1]} → {self.path}", flush=True)

    def add(self, seq, payload):
        if self.seq is not None:
            gap = (seq - self.seq - 1) & 0xFFFF
            if 0 < gap < 1000:
                self.lost += gap
                self.wav.writeframes(b"\x00\x00" * (320 * gap))   # keep the timeline: silence for lost packets
        self.seq = seq
        n = len(payload) // 2
        pcm = struct.unpack(f">{n}h", payload[: n * 2])            # L16 = big-endian
        self.wav.writeframes(struct.pack(f"<{n}h", *pcm))
        self.sumsq += sum(v * v for v in pcm)
        self.peak = max(self.peak, max((abs(v) for v in pcm), default=0))
        self.pkts += 1
        self.samples += n
        self.last = time.time()

    def close(self):
        self.wav.close()
        dur = self.samples / RATE
        rms = math.sqrt(self.sumsq / max(1, self.samples)) / 32768
        db = 20 * math.log10(rms + 1e-9)
        pk = 20 * math.log10(self.peak / 32768 + 1e-9)
        print(f"■ saved {self.path.name}: {dur:.1f} s, {self.pkts} packets, {self.lost} lost, "
              f"level {db:.1f} dBFS (peak {pk:.1f})", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=5006)
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent / "recordings")
    a = ap.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", a.port))
    sock.settimeout(0.5)
    print(f"listening for RTP/L16 16 kHz on UDP {a.port}, saving to {a.out}", flush=True)
    rec = None
    while True:
        try:
            data, src = sock.recvfrom(2048)
        except socket.timeout:
            data = None
        if rec and time.time() - rec.last > GAP_S:
            rec.close()
            rec = None
        if not data or len(data) <= 12 or data[0] >> 6 != 2 or data[1] & 0x7F != PT_L16:
            continue
        hdr = 12 + 4 * (data[0] & 0x0F)
        seq = struct.unpack(">H", data[2:4])[0]
        if rec is None:
            rec = Recording(a.out, src)
        rec.add(seq, data[hdr:])


if __name__ == "__main__":
    main()
