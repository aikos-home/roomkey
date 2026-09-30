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

## Audio route: RoomKey joins the VoIP stack as an ESP peer (2026-09-30)
The stack's own ESP profile, `voip-pcm/1` ([docs/voip_profile.md](https://github.com/n-IA-hane/esphome-intercom/blob/main/docs/voip_profile.md)):
ESP devices are plain SIP user agents (no auth, no REGISTER); **media is RTP `L16`, mandatory**,
network byte order, dynamic payload type 96–127, `a=rtpmap` + `a=ptime`; compressed codecs are
answered with `488`. HA's roster can list direct SIP URIs; ESP-to-ESP calls must work.

RoomKey's existing link already sends exactly that (RTP L16 big-endian, PT 96, 16 kHz, 20 ms).
So **no G.711/G.722** — RoomKey needs only a minimal SIP UA on top: answer/send INVITE, ACK, BYE,
CANCEL, `488` for anything but L16, SDP offer/answer `L16/16000/1`, `ptime 20`. Push-to-talk stays
local (silence while not held); no re-INVITE (the profile answers those with 488 anyway).
To verify on the bench once the Klingelbox talk computer runs.

Security, same rules as Klingelbox: SIP/RTP are unauthenticated → RoomKeys live in the IoT VLAN;
RoomKey only accepts incoming audio during an active call.

## Doorbell on HA-dev
The real bell (Klingelbox device `s3poeeth-intercom-bell`, Waveshare ESP32-S3-ETH) provides the
contract id `binary_sensor.doorbell_button`: Klingelbox renames its entity in the registry.
RoomKey's DEV stand-in was removed on 2026-09-30, including its orphaned entity-registry entry
(a removed YAML entity keeps reserving its entity_id until the registry entry is deleted).
Ringing: the key rings on every off→on of that sensor, no cooldown (while already in a call it
stays in the call). To prove nothing is lost at storm speed, the key counts what it receives:
`sensor.<key>_doorbell_presses_received`, compared with the bell's `presses_since_boot`.
Fallback if presses get lost: subscribe to the state of `event.*_doorbell`.

Coordination between the two threads happens in a shared message file on the home server
(append-only, rules at the top), not in this repo.

## Open questions to the door-station side
Chip/board? Existing audio stream and format? RTP/L16 half-duplex OK, or SIP/WebRTC (→ HA/go2rtc bridge)?
