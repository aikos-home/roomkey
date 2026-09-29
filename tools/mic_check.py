#!/usr/bin/env python3
"""
mic_check.py — verify a RoomKey microphone running esphome/mic_test.yaml.

Resets the board, prints the level log, plays a 1 kHz beep + a spoken sentence on
this Mac when the board starts recording, rebuilds the recording as a WAV and
checks that the beep and the voice are in it.

    python3 mic_check.py [/dev/cu.usbmodemXXXX]
"""
import base64
import re
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
import serial

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem3101"
OUT = Path(__file__).resolve().parent / "recordings" / f"mic_check_{time.strftime('%Y%m%d_%H%M%S')}.wav"
RATE = 16000
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def play_test_sound() -> None:
    tmp = Path(tempfile.mkdtemp())
    t = np.arange(int(0.8 * 44100)) / 44100
    tone = (0.5 * np.sin(2 * np.pi * 1000 * t) * np.minimum(1, np.minimum(t, t[::-1]) / 0.02) * 32767).astype("<i2")
    with wave.open(str(tmp / "beep.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes(tone.tobytes())
    time.sleep(0.4)
    subprocess.run(["afplay", str(tmp / "beep.wav")])
    time.sleep(0.3)
    subprocess.run(["say", "Hello from the front door. This is a microphone test."])


def main() -> None:
    p = serial.Serial(PORT, 115200, timeout=0.2)
    p.dtr = False; p.rts = True; time.sleep(0.1); p.rts = False  # reset
    chunks: dict[int, bytes] = {}
    t_armed = None
    buf = b""
    deadline = time.time() + 60
    while time.time() < deadline:
        buf += p.read(8192)
        *lines, buf = buf.split(b"\n")
        for raw in lines:
            line = ANSI.sub("", raw.decode("utf-8", "replace")).strip()
            if "LEVEL" in line:
                print(line.split("LEVEL", 1)[1].strip(), flush=True)
            elif "CAPTURE ARMED" in line:
                t_armed = time.time()
                print(">>> recording 5 s — playing beep + voice on the Mac", flush=True)
                threading.Thread(target=play_test_sound, daemon=True).start()
            elif " B64 " in line:
                pos, data = line.split(" B64 ", 1)[1].split(" ", 1)
                chunks[int(pos)] = base64.b64decode(data)
            elif "CAPTURE END" in line:
                pcm = b"".join(chunks[k] for k in sorted(chunks))
                analyse(pcm)
                return
            elif "[E]" in line or "[W]" in line:
                print(line, flush=True)
    sys.exit("timed out waiting for the capture (is mic_test.yaml flashed?)")


def analyse(pcm: bytes) -> None:
    x = np.frombuffer(pcm, "<i2").astype(np.float64)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    norm = x / max(1.0, np.abs(x).max()) * 0.9 * 32767  # normalised copy for listening
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE); w.writeframes(norm.astype("<i2").tobytes())
    win = RATE // 10
    rms = [20 * np.log10(np.sqrt(np.mean((x[i:i + win] / 32768) ** 2)) + 1e-9) for i in range(0, len(x) - win, win)]
    floor = np.percentile(rms, 15)
    loud = np.percentile(rms, 90)
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1 / RATE)
    band = (f > 950) & (f < 1050)
    ref = (f > 1200) & (f < 3000)
    beep_snr = 20 * np.log10(spec[band].max() / (np.median(spec[ref]) + 1e-9))
    print(f"\nsamples {len(x)}  ({len(x) / RATE:.1f} s)  → {OUT}")
    print(f"noise floor ≈ {floor:.1f} dBFS   loud parts ≈ {loud:.1f} dBFS   dynamic range {loud - floor:.1f} dB")
    print(f"1 kHz beep peak vs. neighbourhood: {beep_snr:.1f} dB")
    print("timeline (100 ms blocks, dBFS):")
    print("  " + " ".join(f"{v:.0f}" for v in rms))
    ok_signal = np.abs(x).max() > 0 and floor > -110
    ok_sound = loud - floor > 10 or beep_snr > 20
    print("\nRESULT:", "MIC WORKS ✅" if ok_signal and ok_sound else
          ("mic delivers data but didn't hear the Mac clearly (volume? distance?)" if ok_signal else
           "NO SIGNAL ❌ — digital silence: check VDD/GND/L-R wiring or SD pin"))


if __name__ == "__main__":
    main()
