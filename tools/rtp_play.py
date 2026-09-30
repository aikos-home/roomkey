#!/usr/bin/env python3
"""
rtp_play.py — send a WAV file as an intercom RTP stream (L16 big-endian, 16 kHz mono, PT 96, 20 ms).

Test tool: stands in for a door station or a key, e.g. to feed the transcriber or play audio on a key.

    python3 tools/rtp_play.py <file.wav> <host:port> [--silence-s 1.5]
    say -v Anna -o /tmp/x.aiff "Hallo, hier ist der Paketdienst"      # macOS: make a German test sentence
    afconvert -f WAVE -d LEI16@16000 -c 1 /tmp/x.aiff /tmp/x.wav

The WAV must be 16-bit mono 16 kHz. Standard library only.
"""
import argparse
import random
import socket
import struct
import time
import wave

RATE, FRAME, PT_L16 = 16000, 320, 96


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav")
    ap.add_argument("dest", help="host:port")
    ap.add_argument("--silence-s", type=float, default=0.0, help="quiet frames sent after the file")
    ap.add_argument("--no-cn", action="store_true", help="don't end with a comfort-noise packet (= button released)")
    a = ap.parse_args()
    host, port = a.dest.rsplit(":", 1)
    with wave.open(a.wav) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, RATE), "need 16-bit mono 16 kHz"
        pcm = w.readframes(w.getnframes())
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm) + (0,) * int(a.silence_s * RATE)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ssrc, seq, ts = random.getrandbits(32), random.getrandbits(16), random.getrandbits(32)
    t_next = time.monotonic()
    n = 0
    for i in range(0, len(samples) - FRAME + 1, FRAME):
        hdr = struct.pack(">BBHII", 0x80, PT_L16 | (0x80 if i == 0 else 0), seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc)
        sock.sendto(hdr + struct.pack(f">{FRAME}h", *samples[i:i + FRAME]), (host, int(port)))
        seq, ts, n = seq + 1, ts + FRAME, n + 1
        t_next += FRAME / RATE
        time.sleep(max(0.0, t_next - time.monotonic()))
    if not a.no_cn:   # RFC 3389 comfort noise, 1-byte noise level: "I stopped talking"
        sock.sendto(struct.pack(">BBHII", 0x80, 13, seq & 0xFFFF, ts & 0xFFFFFFFF, ssrc) + bytes([127]), (host, int(port)))
    print(f"sent {n} packets ({n * FRAME / RATE:.1f} s) to {host}:{port}" + ("" if a.no_cn else " + end (comfort noise)"))


if __name__ == "__main__":
    main()
