# RoomKey intercom protocol (WIP)

Status: **WIP** — media path implemented and tested end-to-end on the desktop
(simulator ⇄ `tools/fake_home.py`), not yet on hardware (needs Wi-Fi provisioning,
the INMP441 wired, and — for listening — an I²S amp + speaker).

## Why not an existing stack?

The most complete HA intercom stack ([n-IA-hane/esphome-intercom](https://github.com/n-IA-hane/esphome-intercom))
lists the ESP32-C6 as unsupported and wants PSRAM. The C6 has neither PSRAM nor
enough headroom for SIP + AEC, so RoomKey uses the simplest thing that
interoperates: **plain RTP**, with signalling done by Home Assistant.

## Split of responsibilities

| Concern | Where | How |
|---|---|---|
| Doorbell ring | HA → key | `binary_sensor.doorbell_button` turns on, **or** HA calls `esphome.<key>_ring` |
| Answer / dismiss / hang up / talk | key → HA | event `esphome.roomkey` `{room, node, type}` |
| Door ended the call | HA → key | `esphome.<key>_call_state` `{state: ended}` |
| Where to send audio | key | latched from the first RTP stream received, or `esphome.<key>_set_intercom_peer {peer_host, peer_port}` |
| Audio | key ⇄ door | RTP over UDP (below) |

## Media

* RTP v2 (RFC 3550), payload type **96**, **L16** (RFC 3551: signed 16-bit, **big-endian**), **16 kHz, mono**
* 20 ms per packet = 320 samples = 640 bytes payload (+12 byte header), 50 pkt/s ≈ 262 kbit/s
* Key listens on **UDP 5004**. The door station sends to `<key-ip>:5004` from any port;
  the key replies to that source address/port (symmetric RTP).
* **Half-duplex, push-to-talk.** While the key is held the key sends its mic and
  drops incoming audio; while released it plays incoming audio and sends nothing.
  This matches the hardware (mic and amp share one I²S bus on the C6) and avoids
  echo without needing AEC.
* Marker bit set on the first packet of each talk spurt.
* go2rtc / ffmpeg can consume it with an SDP like:

```
v=0
o=- 0 0 IN IP4 0.0.0.0
s=RoomKey
c=IN IP4 0.0.0.0
t=0 0
m=audio 5006 RTP/AVP 96
a=rtpmap:96 L16/16000/1
```

## Call sequence

```
door button ─▶ HA (binary_sensor on) ─▶ all keys ring
key "Office" pressed ─▶ event {type: answer, node: aikos-roomkey-office}
HA ─▶ other keys: ring_stop                       (automation in roomkey_package.yaml)
HA ─▶ door station: "stream to aikos-roomkey-office.local:5004"   (door-station side, WIP)
door ══ RTP ══▶ key :5004  (key latches door as peer, plays it)
key held   ─▶ event talk_start;  key ══ RTP ══▶ door   (door plays it)
key released ─▶ event talk_stop
key pressed ─▶ event hangup        |  door ends ─▶ HA ─▶ keys: call_state ended
```

## Door station checklist

1. On `esphome.roomkey` `answer`/`call_door`: start sending RTP/L16/16k to `<node>.local:5004`.
2. Play whatever RTP arrives on your socket (the key sends only while held).
3. On `hangup`: stop. When the visitor side ends: tell HA → `call_state: ended`.

`tools/fake_home.py` implements exactly this door-side behaviour and is the reference.

## Transcription and "who is speaking" (WIP, test setup)

Both sides can be transcribed locally, and a visitor's self-introduction is shown on the
screen on the other side (the RoomKey shows who is at the door; the door screen shows who
answered). Nothing leaves the house; when the transcriber is off, calls work as before.

```
key (talking) ── RTP copy ──▶ transcriber :5006  (side "room")  ─┐   Whisper (local)
door (mic)    ── RTP copy ──▶ transcriber :5008  (side "door")  ─┤─▶ who is speaking      ─▶ Home Assistant
                                                                  │     sensor.talk_transcript       (room → shown at the door)
                                                                  └──   sensor.talk_transcript_door  (door → shown on the keys)
```

* **Key:** entity "Transcriber address" (`host:port`, empty = off). While the key transmits
  (push-to-talk) every RTP packet also goes there. Only its own microphone, never the door's.
* **Door station:** sends a copy of its microphone to port 5008 while ringing and during a call;
  the transcriber cuts a continuous stream into utterances at pauses (`--split-on-silence`).
* **Transcriber** (aikos building block [`services/transcriber`](https://github.com/aikos-home/aikos/tree/main/services/transcriber),
  tag `transcriber-v1.0.0`; it started here in `tools/`. E.g. on a Mac with whisper.cpp): one WAV per utterance → text → who is speaking → HA state + event
  `aikos_talk_transcript`. Attributes: `text`, `message` (without greeting and introduction),
  `speaker` ("Anna", "Paketdienst · DHL", "Polizei", "" if nobody introduced themselves),
  `speaker_kind`, `speaker_role`, `speaker_org`, `speaker_method`, `side`, `device`, …
* **Who is speaking** (`aikos_transcriber.identity`): rules first (self-introductions like "hier ist …",
  "ich bin …", "… mein Name", "… hier", and roles or companies said up front), a local LLM through
  Ollama only when the rules find nobody; its answer counts only if the words are in the transcript.
  A role word later in a sentence is a topic, not an introduction ("beim Nachbarn abgeben").
  **Nothing is verified:** anyone can say "Polizei". Screens show it as said.
* **Spoken language:** Whisper runs twice in parallel: once fixed to German (`text`, `message`, `speaker` —
  foreign speech comes out translated into German) and once detecting the language (`language`, `language_name`,
  `language_name_en`, `language_probability`, `text_original`). A foreign language counts from 60 % certainty
  (English 90 %: short German clips are sometimes taken for English).
* **Whisper hint:** a word list of doorstep vocabulary (couriers, authorities, household names). If Whisper
  answers unclear audio with the hint itself, the clip is transcribed again without it.
* **RoomKey screen:** while ringing and in a call the door name ("Front door") is replaced by the
  visitor's `speaker`, and a foreign language shows as "Speaks Chinese"; both are cleared on the next ring
  and when the call ends. From a room only a name counts as a speaker (residents mention couriers as topics).
* **Test recording** (WIP switch "TEST record after ring"): ends ~1.2 s after the last word (speech =
  11 dB above the 5th percentile of the last 1.5 s, held for a third of 120 ms; `VoiceGate`, the same as
  `aikos_voice` `level.h`), at most "TEST record length" seconds.

### Measuring it

The eval moved with the transcriber: `services/transcriber/tools/talk_eval.py` in aikos-home/aikos speaks test cases
with macOS voices (German, and foreign voices reading German = accented German), degrades them (street noise, voices in
the background, distance and echo, shouting, telephone band, the key's 120 Hz high-pass), transcribes them and scores
who was recognised. 716 cases (`services/transcriber/tests/eval/`): 98.9 % on the ideal transcripts with the local
LLM; CI checks every case of the rules against a frozen snapshot. Running the transcriber: see its README
(`python3 -m aikos_transcriber`, configuration from `AIKOS_*` environment variables).
