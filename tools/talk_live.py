#!/usr/bin/env python3
# MOVED to aikos-home/aikos services/transcriber (tag transcriber-v1.0.0). This copy is frozen: the Mac service
# runs it until it switches to that tag, then it is removed here. Changes only there (PR + RoomKey review).
"""
talk_live.py — live text while somebody is still talking (WIP). Used by tools/rtp_recorder.py --live.

Whisper (whisper.cpp server) does not stream, so this re-transcribes the growing recording every
~0.7 s while the speaker holds the talk button and publishes each new partial text to Home Assistant:

    sensor.talk_live_door   state = start of the utterance (ISO, constant during one utterance)
                            attributes: text (grows), speaker (rules only, may appear early), final (false/true),
                                        side, seq, updated
The finished transcript still comes from tools/transcribe_publish.py (sensor.talk_transcript_door) ~1 s after
release; when the utterance ends this entity gets final: true with the last partial text.
Partials use the rules only (no LLM). Standard library only.
"""
from __future__ import annotations

import array
import datetime as dt
import io
import json
import math
import threading
import time
import urllib.request
import uuid
import wave

import os

from talk_identity import WHISPER_PROMPT, by_rules, classify, clean, is_noise, prompt_echo, strip_captions, strip_echo

RATE = 16000


def has_speech_pcm(pcm: bytes, min_s: float = 0.3) -> bool:
    """At least min_s of 20 ms frames clearly above the recording's own noise floor (see transcribe_publish)."""
    x = array.array("h", pcm)
    step = RATE // 50
    db = [20 * math.log10(math.sqrt(sum(v * v for v in x[i:i + step]) / step) / 32768 + 1e-9)
          for i in range(0, len(x) - step + 1, step)]
    if not db:
        return False
    floor = sorted(db)[len(db) // 10]
    return sum(1 for d in db if d > max(floor + 12.0, -50.0)) * 0.02 >= min_s


def resident_talk(activity_file: str) -> tuple[float, float]:
    """(start, last audio) of the latest resident talk, from the room receiver's activity file; (0, 0) if unknown."""
    try:
        last = os.path.getmtime(activity_file)
        with open(activity_file) as f:
            start = float(f.read().strip() or last)
        return min(start, last), last
    except (OSError, ValueError):
        return 0.0, 0.0


def wav_bytes(pcm: bytes) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(b"\x00\x00" * int(0.3 * RATE) + pcm + b"\x00\x00" * (RATE // 2))
    return b.getvalue()


class Live:
    def __init__(self, ha_url: str, token: str, entity: str, side: str, whisper_url: str, names=(), interval: float = 0.3,
                 quiet_file: str = "", echo_ref: str = "sensor.talk_transcript"):
        self.ha_url, self.token, self.entity, self.side = ha_url.rstrip("/"), token, entity, side
        self.whisper_url, self.names, self.interval = whisper_url, list(names), interval
        self.prompt = WHISPER_PROMPT + (" Namen: " + ", ".join(self.names) + "." if self.names else "")
        self.quiet_file = quiet_file   # touched by the room receiver while a RoomKey talks: no door partials then (echo)
        self.echo_ref = echo_ref       # after that, the resident's transcript: its echo is removed from the partials
        self.rec = None
        self.lock = threading.Lock()
        threading.Thread(target=self._run, daemon=True).start()

    # ── called from the recorder (main thread) ──
    def start(self, rec, test: bool = False):
        """A new utterance. test = from a test sender: published to <entity>_test, compared with test residents only."""
        sfx = "_test" if test else ""
        with self.lock:
            self.rec, self.text, self.speaker, self.seq, self.done_len = rec, "", "", 0, 0
            self.cur_entity, self.cur_ref = self.entity + sfx, self.echo_ref + sfx
            self.cur_quiet = self.quiet_file + sfx if self.quiet_file else ""
            self.vtype, self.urgent, self.warned, self.overlap = "", False, False, False
            self.started = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    def stop(self, rec):
        with self.lock:
            if self.rec is not rec:
                return
            self.rec = None
            text, speaker, started, seq, entity = self.text, self.speaker, self.started, self.seq, self.cur_entity
        if text:
            self._publish(entity, started, text, speaker, True, seq + 1)

    # ── worker ──
    def _run(self):
        while True:
            time.sleep(self.interval)
            with self.lock:
                rec = self.rec
                if rec is None:
                    continue
                pcm = bytes(rec.pcm)
                started, done_len, entity, quiet, ref = self.started, self.done_len, self.cur_entity, self.cur_quiet, self.cur_ref
            if len(pcm) - done_len < int(0.3 * RATE) * 2 or not has_speech_pcm(pcm):
                continue
            began, active = resident_talk(quiet) if quiet else (0.0, 0.0)
            if time.time() - active < 0.8:
                self.overlap = True             # a resident is talking: the door mic hears the door speaker
                continue
            said = None
            if self.overlap:                    # this utterance overlapped the resident: wait for the resident's text
                said = self._resident_text(ref, began, active)
                if said is None:
                    continue
            try:
                text = self._whisper(wav_bytes(pcm))
            except Exception as exc:
                if not getattr(self, "warned", False):
                    print(f"  live: Whisper failed ({exc})", flush=True)
                    self.warned = True
                continue
            text = strip_captions(text)
            if said:
                text = strip_echo(text, said)
            if not text or is_noise(text) or prompt_echo(text, self.prompt):
                continue
            who = classify(by_rules(text, self.names, self.side), clean(text), self.side)
            with self.lock:
                if self.rec is not rec:
                    continue                    # a new utterance began meanwhile: this text is stale
                if text == self.text:
                    self.done_len = len(pcm)
                    continue
                self.text, self.done_len, self.seq = text, len(pcm), self.seq + 1
                self.speaker = who.speaker or self.speaker
                self.vtype = who.vtype or getattr(self, "vtype", "")
                self.urgent = who.urgent or getattr(self, "urgent", False)
                speaker, seq = self.speaker, self.seq
            self._publish(entity, started, text, speaker, False, seq)

    def _resident_text(self, ref: str, began: float, active: float):
        """The resident's transcript of the talk that began at `began`; None while it is still being made."""
        req = urllib.request.Request(f"{self.ha_url}/api/states/{ref}", headers={"Authorization": f"Bearer {self.token}"})
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                st = json.loads(r.read())
            made = dt.datetime.fromisoformat(st["state"]).timestamp()
        except Exception:
            return ""                           # no reference: show the partials unfiltered (the final text is filtered)
        if made < began - 0.2 and time.time() - active < 5:
            return None
        return st["attributes"].get("text", "") if time.time() - made < 30 else ""

    def _whisper(self, audio: bytes) -> str:
        boundary = uuid.uuid4().hex
        fields = [("response_format", "json"), ("language", "de"), ("temperature", "0"), ("prompt", self.prompt)]
        body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields)
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="live.wav"\r\n'
                 "Content-Type: audio/wav\r\n\r\n").encode() + audio + f"\r\n--{boundary}--\r\n".encode()
        req = urllib.request.Request(self.whisper_url, data=body, method="POST",
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return " ".join(json.loads(r.read())["text"].split())

    def _publish(self, entity: str, started: str, text: str, speaker: str, final: bool, seq: int):
        body = {"state": started, "attributes": {
            "text": text, "speaker": speaker, "speaker_role": getattr(self, "vtype", ""), "urgent": getattr(self, "urgent", False),
            "final": final, "side": self.side, "seq": seq,
            "updated": dt.datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "friendly_name": "Talk live " + self.side + (" (test senders)" if entity.endswith("_test") else " (TEST)"),
            "icon": "mdi:text-recognition"}}
        req = urllib.request.Request(f"{self.ha_url}/api/states/{entity}", data=json.dumps(body).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=5).read()
            print(f"  ⋯ live {'final' if final else seq}: “{text}”" + (f" [{speaker}]" if speaker else ""), flush=True)
        except Exception as exc:
            print(f"  live publish failed: {exc}", flush=True)
