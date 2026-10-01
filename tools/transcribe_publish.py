#!/usr/bin/env python3
"""
transcribe_publish.py — TEST (WIP): transcribe one intercom utterance with a local Whisper
server, find out who is speaking (tools/talk_identity.py) and publish it in Home Assistant,
where the screen on the OTHER side shows it.

    python3 tools/transcribe_publish.py <wav> --side room|door --ha-url http://<ha>:8123 --token-file ~/.ha-dev/token \
        [--source-ip 192.168.x.y] [--whisper-url http://127.0.0.1:6667/v1/audio/transcriptions] \
        [--llm-url http://127.0.0.1:11434 | --no-llm] [--known-names Jonas,Anna]

Publishes (contract: aikos vertraege.md §6):
  sensor.talk_transcript        speech from a ROOM (a RoomKey)   → shown on the door screen
  sensor.talk_transcript_door   speech from the DOOR (a visitor) → shown on the RoomKeys
      state = ISO timestamp of this transcript (changes every time)
      attributes: text, message, speaker, speaker_kind, speaker_role, speaker_org, speaker_method,
                  side, device, key_id, duration_s, language, model, created, source, transcribe_s
  event  aikos_talk_transcript  with the same data
Test senders (--test-sources, e.g. 127.0.0.1 for tools/rtp_play.py) never reach the live entities: they go to
  sensor.talk_transcript_test / sensor.talk_transcript_door_test and event aikos_talk_transcript_test.
Utterances without words (noise, music, Whisper's silence hallucinations) are not published.

Local only: audio goes to the Whisper server on this computer, never to a cloud.
Standard library only. Hooked into tools/rtp_recorder.py with --exec.
"""
import argparse
import datetime as dt
import os
import re
import io
import json
import sys
import time
import urllib.request
import uuid
import wave
from pathlib import Path

from talk_identity import WHISPER_PROMPT, identify, is_noise, prompt_echo, strip_captions, strip_echo
from talk_live import resident_talk


def has_speech(wav: Path, min_s: float = 0.3) -> bool:
    """At least min_s of 20 ms frames clearly above the recording's own noise floor (10th percentile + 12 dB),
    and not just quiet hiss (> -50 dBFS)."""
    with wave.open(str(wav)) as w:
        rate, n = w.getframerate(), w.getnframes()
        pcm = w.readframes(n)
    import array
    import math
    x = array.array("h", pcm)
    step = rate // 50
    db = []
    for i in range(0, len(x) - step + 1, step):
        fr = x[i:i + step]
        db.append(20 * math.log10(math.sqrt(sum(v * v for v in fr) / step) / 32768 + 1e-9))
    if not db:
        return False
    floor = sorted(db)[len(db) // 10]
    loud = sum(1 for d in db if d > max(floor + 12.0, -50.0))
    return loud * 0.02 >= min_s


def padded(wav: Path) -> bytes:
    """The WAV with 0.3 s of silence before and 1 s after: Whisper drops words that touch the edges."""
    with wave.open(str(wav)) as w:
        rate, pcm = w.getframerate(), w.readframes(w.getnframes())
        b = io.BytesIO()
        with wave.open(b, "wb") as o:
            o.setnchannels(w.getnchannels()); o.setsampwidth(w.getsampwidth()); o.setframerate(rate)
            o.writeframes(b"\x00\x00" * int(0.3 * rate) + pcm + b"\x00\x00" * rate)
    return b.getvalue()


# Whisper's language codes → (German, English) display names. Others: Whisper's English name, capitalised.
LANGUAGES = {
    "de": ("Deutsch", "German"), "en": ("Englisch", "English"), "tr": ("Türkisch", "Turkish"), "ar": ("Arabisch", "Arabic"),
    "ru": ("Russisch", "Russian"), "uk": ("Ukrainisch", "Ukrainian"), "pl": ("Polnisch", "Polish"),
    "ro": ("Rumänisch", "Romanian"), "it": ("Italienisch", "Italian"), "fr": ("Französisch", "French"),
    "es": ("Spanisch", "Spanish"), "pt": ("Portugiesisch", "Portuguese"), "el": ("Griechisch", "Greek"),
    "hr": ("Kroatisch", "Croatian"), "sr": ("Serbisch", "Serbian"), "bs": ("Bosnisch", "Bosnian"), "bg": ("Bulgarisch", "Bulgarian"),
    "hu": ("Ungarisch", "Hungarian"), "cs": ("Tschechisch", "Czech"), "sk": ("Slowakisch", "Slovak"), "nl": ("Niederländisch", "Dutch"),
    "vi": ("Vietnamesisch", "Vietnamese"), "zh": ("Chinesisch", "Chinese"), "ja": ("Japanisch", "Japanese"),
    "ko": ("Koreanisch", "Korean"), "fa": ("Persisch", "Persian"), "ku": ("Kurdisch", "Kurdish"), "hi": ("Hindi", "Hindi"),
    "ur": ("Urdu", "Urdu"), "ta": ("Tamil", "Tamil"), "th": ("Thailändisch", "Thai"), "sq": ("Albanisch", "Albanian"),
    "da": ("Dänisch", "Danish"), "sv": ("Schwedisch", "Swedish"), "no": ("Norwegisch", "Norwegian"), "fi": ("Finnisch", "Finnish"),
    "he": ("Hebräisch", "Hebrew"), "lt": ("Litauisch", "Lithuanian"), "lv": ("Lettisch", "Latvian"), "et": ("Estnisch", "Estonian"),
    "sl": ("Slowenisch", "Slovenian"), "mk": ("Mazedonisch", "Macedonian"), "ka": ("Georgisch", "Georgian"),
    "hy": ("Armenisch", "Armenian"), "az": ("Aserbaidschanisch", "Azerbaijani"), "tl": ("Tagalog", "Tagalog"),
    "id": ("Indonesisch", "Indonesian"), "so": ("Somali", "Somali"), "sw": ("Suaheli", "Swahili"), "am": ("Amharisch", "Amharic"),
}
# Below this, Whisper's guess is not shown. English needs more: short German clips are sometimes taken for English.
LANG_MIN_P, LANG_MIN_P_EN = 0.6, 0.9


def whisper(url: str, wav: Path, language: str, prompt: str = "", verbose: bool = False):
    boundary = uuid.uuid4().hex
    parts = []
    fields = [("response_format", "verbose_json" if verbose else "json"), ("language", language), ("temperature", "0")] + \
        ([("prompt", prompt)] if prompt else [])
    for name, value in fields:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{wav.name}"\r\n'
                  f'Content-Type: audio/wav\r\n\r\n').encode() + padded(wav) + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=b"".join(parts), method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read())
    d["text"] = " ".join(d.get("text", "").split())
    return d if verbose else d["text"]


# words only one of the two languages uses — to see whether pass 1 really produced German
DE_ONLY = set("ich bin ist sind der die das den dem und nicht ein eine einen einem mit zu für sie wir hier auf komme kommt "
              "gleich bitte hallo danke ja nein mein meine heiße habe hab vom im es du euch uns mal noch schon auch was wer "
              "wo wie aber oder mich dich dir mir ihnen möchte will kann muss".split())
EN_ONLY = set("i i'm am is are the and not a an with to for you we here on coming please hello thanks yes no my have has "
              "from it it's this that can your our what who where how but or me want would could should".split())


def looks_german(text: str) -> bool:
    """Did Whisper's German pass produce German? For English it often just writes English."""
    if re.search(r"[^\W\d_]", text) and not re.search(r"[A-Za-zÄÖÜäöüß]", text):
        return False                                           # another script altogether
    ws = re.findall(r"[a-zäöüß']+", text.lower())
    de, en = sum(w in DE_ONLY for w in ws), sum(w in EN_ONLY for w in ws)
    return len(ws) <= 2 or de >= en


def to_german(text: str, language: str, url: str, model: str) -> str:
    """Translate an utterance into German with the local LLM ("" if it fails)."""
    body = {"model": model, "stream": False, "think": False, "keep_alive": -1, "options": {"temperature": 0},
            "messages": [{"role": "system", "content":
                          f"Übersetze die folgende Äußerung ({language}), gesprochen an einer Haustür-Sprechanlage, ins "
                          "Deutsche. Namen, Firmen und Zahlen unverändert lassen. Antworte nur mit der Übersetzung."},
                         {"role": "user", "content": text}]}
    req = urllib.request.Request(url.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return " ".join(json.loads(r.read())["message"]["content"].strip().strip('"„“').split())
    except Exception:
        return ""


def spoken_language(d: dict) -> tuple[str, float]:
    """(code, probability) of Whisper's language detection; "de" when unsure."""
    probs = d.get("language_probabilities") or {}
    code, p = max(probs.items(), key=lambda kv: kv[1]) if probs else ("de", 1.0)
    return (code, p) if p >= (LANG_MIN_P_EN if code == "en" else LANG_MIN_P) else ("de", p)


def drop_echo(text: str, ha_url: str, token: str, door_span: tuple[float, float], activity_file: str,
              ref_entity: str = "sensor.talk_transcript", wait_s: float = 4.0) -> str:
    """The door mic hears the resident through the door speaker (voice v2: door mic on for the whole call). If a
    resident talked while this door audio was recorded (door_span = start, end), drop the door sentences that mostly
    repeat the resident's transcript, waiting up to wait_s for it. No overlap: nothing to drop (and no delay)."""
    began, last = resident_talk(activity_file)
    if not began or min(last, door_span[1]) - max(began, door_span[0]) < 0.5:
        return text                                    # < 0.5 s together: not even a word of echo
    deadline = time.time() + wait_s
    while True:
        try:
            room = ha(ha_url, token, "GET", f"/api/states/{ref_entity}")
            made = dt.datetime.fromisoformat(room["state"]).timestamp()
        except Exception:
            return text
        if made >= began - 0.2 or time.time() >= deadline:
            return strip_echo(text, room["attributes"].get("text", ""))
        time.sleep(0.3)


def ha(url: str, token: str, method: str, path: str, body=None):
    req = urllib.request.Request(url.rstrip("/") + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as r:
        raw = r.read()
        return json.loads(raw) if raw else None


def key_for_ip(url: str, token: str, ip: str):
    """Find which key sent the audio: the *_ip_address sensor whose state is that IP."""
    for s in ha(url, token, "GET", "/api/states"):
        if s["entity_id"].endswith("_ip_address") and s["state"] == ip:
            name = s["attributes"].get("friendly_name", "").removesuffix(" IP address").strip()
            return name, s["entity_id"].split(".", 1)[1].removesuffix("_ip_address")
    return None, None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("wav", type=Path)
    ap.add_argument("--ha-url", required=True)
    ap.add_argument("--token-file", type=Path, required=True)
    ap.add_argument("--whisper-url", default="http://127.0.0.1:6667/v1/audio/transcriptions")
    ap.add_argument("--language", default="de", help='"auto" guesses per clip — unreliable for 2–5 s of speech')
    ap.add_argument("--source-ip", default="")
    ap.add_argument("--side", choices=("room", "door"), default="room", help="who spoke: a RoomKey (room) or the door")
    ap.add_argument("--entity", default="", help="default: sensor.talk_transcript (room) / sensor.talk_transcript_door (door)")
    ap.add_argument("--llm-url", default="http://127.0.0.1:11434", help="local Ollama, only asked when the rules find nobody")
    ap.add_argument("--llm-model", default="qwen3:8b")
    ap.add_argument("--no-llm", action="store_true")
    ap.add_argument("--no-prompt", action="store_true", help="don't give Whisper the doorstep vocabulary hint")
    ap.add_argument("--known-names", default="", help="comma-separated household names (spelling as shown)")
    ap.add_argument("--delete-wav", action="store_true", help="delete the recording when done (privacy; for the service)")
    ap.add_argument("--echo-ref", default="sensor.talk_transcript", help="door side: the room transcript to filter echoes against")
    ap.add_argument("--activity-file", default="", help="door side: touched by the room receiver while a resident talks")
    ap.add_argument("--test-sources", default="", help="comma-separated IPs of test senders → *_test entities and event")
    a = ap.parse_args()
    entity = a.entity or ("sensor.talk_transcript" if a.side == "room" else "sensor.talk_transcript_door")
    test = a.source_ip in {s.strip() for s in a.test_sources.split(",") if s.strip()}
    sfx = "_test" if test else ""                      # tests never write into live entities (qualitaet.md §3.8)
    entity, event = entity + sfx, "aikos_talk_transcript" + sfx
    echo_ref, activity_file = a.echo_ref + sfx, a.activity_file + sfx if a.activity_file else ""
    token = a.token_file.expanduser().read_text().strip()

    with wave.open(str(a.wav)) as w:
        duration = w.getnframes() / w.getframerate()
    t0 = time.time()
    names = [n.strip() for n in a.known_names.split(",") if n.strip()]
    # household names as a plain list (not "Hier ist Anna." — on silence Whisper answers with such a sentence)
    prompt = "" if a.no_prompt else WHISPER_PROMPT + (" Namen: " + ", ".join(names) + "." if names else "")
    if not has_speech(a.wav):                     # key pressed, nothing said: never let Whisper "hear" its hint
        print(f"· {a.side}: no speech in {a.wav.name} (level), not transcribed", flush=True)
        return
    # Pass 1: German text for the screens (for foreign speech Whisper translates it into German on the way).
    # It is published at once; pass 2 (which language was spoken, and its words) follows ~1 s later under the same
    # timestamp. The Whisper server works one request at a time, so waiting for both would delay the text by ~1 s.
    text = whisper(a.whisper_url, a.wav, a.language, prompt)
    if not a.no_prompt and prompt_echo(text, prompt):  # unclear audio: Whisper repeated its hint → ask again without it
        text = whisper(a.whisper_url, a.wav, a.language, "")
    took = time.time() - t0
    if is_noise(text):
        print(f"· {a.side}: no speech in {a.wav.name} (“{text}”), not published", flush=True)
        return
    text = strip_captions(text)
    detected, lang, lang_p, original = None, "", None, ""
    if not looks_german(text):
        # Not German (Whisper translates many languages on the way, but not e.g. English): find out which language,
        # then let the local LLM translate. Text and original go out together — no English-then-German flicker.
        detected = whisper(a.whisper_url, a.wav, "auto", "", True)
        probs = detected.get("language_probabilities") or {"de": 1.0}
        lang, lang_p = max(probs.items(), key=lambda kv: kv[1])
        if lang != "de":
            original = strip_captions(detected.get("text", "")) or text
            text = (to_german(original, LANGUAGES.get(lang, (lang,))[0], a.llm_url, a.llm_model) if not a.no_llm else "") or text
        took = time.time() - t0
    if a.side == "door":
        end = a.wav.stat().st_mtime
        text = drop_echo(text, a.ha_url, token, (end - duration, end), activity_file, ref_entity=echo_ref)
        if not text:
            print(f"· door: only an echo of the resident in {a.wav.name}, not published", flush=True)
            return
    who = identify(text, names,
                   "" if a.no_llm else a.llm_url, a.llm_model, side=a.side)
    device, key_id = key_for_ip(a.ha_url, token, a.source_ip) if a.source_ip else (None, None)
    created = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    data = {"text": text, "message": who.message, "speaker": who.speaker, "speaker_kind": who.kind,
            "speaker_role": who.vtype, "speaker_org": who.org, "speaker_method": who.method, "urgent": who.urgent,
            "side": a.side,
            "device": device or "unknown", "key_id": key_id or "unknown", "duration_s": round(duration, 1),
            "language": lang, "language_name": LANGUAGES.get(lang, (lang,))[0] if lang else "",
            "language_name_en": LANGUAGES.get(lang, (None, lang))[1] if lang else "",
            "language_probability": round(lang_p, 2) if lang_p is not None else None,
            "text_original": original, "model": "whisper.cpp large-v3 (local)", "created": created,
            "source": "roomkey-test", "transcribe_s": round(took, 1)}
    name = ("Talk transcript (TEST)" if a.side == "room" else "Talk transcript door (TEST)") + (" test senders" if test else "")
    extra = {"friendly_name": name, "icon": "mdi:text-box-outline"}
    ha(a.ha_url, token, "POST", f"/api/states/{entity}", {"state": created, "attributes": {**data, **extra}})
    shown = time.time() - t0
    print(f"✎ {a.side} {device or '?'}: “{text}”  → speaker “{who.speaker or '–'}” ({who.method or 'none'}), "
          f"message “{who.message}”  ({duration:.1f} s audio, in HA after {shown:.1f} s) → {entity}", flush=True)
    if detected is not None:                               # foreign: everything went out together already
        ha(a.ha_url, token, "POST", f"/api/events/{event}", data)
        print(f"  language {lang} ({lang_p:.2f}), translated: “{original}”", flush=True)
        return
    try:                                                   # pass 2: the language is a bonus, the text is out already
        detected = whisper(a.whisper_url, a.wav, "auto", "", True)
    except Exception:
        detected = {}
    lang, lang_p = spoken_language(detected)
    if lang == "en":
        lang = "de"                                        # the German pass WAS German: a short German clip taken for English
    data.update({"language": lang, "language_name": LANGUAGES.get(lang, (lang,))[0],
                 "language_name_en": LANGUAGES.get(lang, (None, lang))[1], "language_probability": round(lang_p, 2),
                 "text_original": strip_captions(detected.get("text", "")) if lang != "de" else ""})
    ha(a.ha_url, token, "POST", f"/api/states/{entity}", {"state": created, "attributes": {**data, **extra}})
    ha(a.ha_url, token, "POST", f"/api/events/{event}", data)
    print(f"  language {lang} ({lang_p:.2f}) after {time.time() - t0:.1f} s"
          + (f": “{data['text_original']}”" if lang != "de" else ""), flush=True)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # never crash the recorder that called us
        print(f"transcribe_publish failed: {exc}", file=sys.stderr, flush=True)
        sys.exit(1)
    finally:
        if "--delete-wav" in sys.argv[1:]:
            wav = next((Path(x) for x in sys.argv[1:] if x.endswith(".wav")), None)
            if wav:
                wav.unlink(missing_ok=True)
