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
key "Office" pressed ─▶ event {type: answer, node: roomkey-office}
HA ─▶ other keys: ring_stop                       (automation in roomkey_package.yaml)
HA ─▶ door station: "stream to roomkey-office.local:5004"   (door-station side, WIP)
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
