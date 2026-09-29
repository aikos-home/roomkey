# Context for the doorbell / intercom thread

Shared with the parallel Claude Code thread that builds the door station, so both sides
agree on the ground rules and the interface. Proposal — not fixed.

## Ground rules (set by the project owner for all devices)
1. Each device is built and tested on its own; integration into one Home Assistant happens only
   at the very end, when each device is ready for final production.
2. Until then every device presents itself to HA the usual way: ESPHome native API,
   auto-discovery, standard entities, HA events/actions, no custom integration required.
3. Everything is open source on GitHub and shown publicly (web, LinkedIn): clean READMEs, no
   secrets or personal data, AI-generated renders labelled, WIP clearly marked.

## Interface RoomKey ⇄ door station
- Ring: HA `binary_sensor.doorbell_button` (subscribed by every key) or ESPHome actions `ring` / `ring_stop`.
- Signalling: HA event `esphome.roomkey {room, node, type}`, type ∈ answer, dismiss, call_door,
  hangup, talk_start, talk_stop. Door ends a call → HA calls `call_state {state: ended}` on the keys.
  One room answers → HA sends `ring_stop` to the others.
- Audio: see [intercom-protocol.md](intercom-protocol.md) — RTP/L16/16 kHz mono, 20 ms, UDP 5004,
  symmetric-RTP latching, half-duplex push-to-talk, `set_intercom_peer(peer_host, peer_port)`.

## Finding after reading the intercom repo (2026-09-29)
Klingelbox's talk computer (ESP32-S3-POE-ETH, INMP441 + MAX98357A) plans the
[n-IA-hane VoIP stack](https://github.com/n-IA-hane/esphome-intercom) with Home Assistant as the
SIP router. That stack does not support the ESP32-C6. Its README also lists "push-to-talk into
speakers inside the house" as not designed yet — that is exactly RoomKey's job.

Likely path: RoomKey gets a **minimal SIP user agent** (SIP signalling is light; only echo
cancellation needs PSRAM, and RoomKey avoids it with push-to-talk). Then HA routes door ⇄ rooms
the same way as door ⇄ phone, and the RTP media (PCM) may already match. To be confirmed
with the door-station side before either device commits.

Security, same rules as Klingelbox: RoomKeys live in the IoT VLAN; RoomKey only accepts
incoming audio during an active call (packets outside a call are dropped unheard).

## Open questions to the door-station side
Chip/board? Existing audio stream and format? RTP/L16 half-duplex OK, or SIP/WebRTC (→ HA/go2rtc bridge)?
