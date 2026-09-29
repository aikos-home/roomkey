#!/usr/bin/env python3
"""
fake_home.py — pretend to be Home Assistant (and the door station) for a RoomKey.

Connects over the native ESPHome API exactly like HA does, serves the entities the
key subscribes to (lights, alarm, doorbell), answers its service calls
(light.toggle, the disarm script) and prints its events (answer, talk, hangup…).

    # interactive: type `help`
    python3 fake_home.py --host roomkey-office.local
    # automated end-to-end test of the HA contract (works against the simulator)
    python3 fake_home.py --host localhost --test
    # also be the door station's audio: stream to the key on answer, record what it sends
    python3 fake_home.py --host roomkey-office.local --door-audio some.mp3

Run it with the Python that ships with ESPHome (it has aioesphomeapi):
    ~/.local/share/uv/tools/esphome/bin/python fake_home.py …
"""
from __future__ import annotations

import argparse
import asyncio
import math
import re
import socket
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

from aioesphomeapi import APIClient, HomeassistantServiceCall, SwitchInfo, UserService

LIGHT = "light.all_lights"
ALARM = "alarm_control_panel.house"
DOORBELL = "binary_sensor.doorbell_button"
DISARM_SCRIPT = "script.roomkey_disarm"

C = {"dim": "\033[2m", "cyan": "\033[36m", "green": "\033[32m", "red": "\033[31m", "yellow": "\033[33m", "off": "\033[0m"}


def say(color: str, *msg) -> None:
    print(f"{C[color]}{time.strftime('%H:%M:%S')} {' '.join(str(m) for m in msg)}{C['off']}", flush=True)


def api_key_from_secrets(path: Path) -> str:
    m = re.search(r'^api_key:\s*"?([^"\n]+)"?', path.read_text(), re.M)
    if not m:
        sys.exit(f"no api_key in {path}")
    return m.group(1).strip()


class DoorAudio(asyncio.DatagramProtocol):
    """Door-station side of the intercom media path: RTP / L16 / 16 kHz mono."""

    RATE, FRAME, PT = 16000, 320, 96

    def __init__(self, key_host: str, key_port: int, source: Path | None, rec_dir: Path):
        self.key = (socket.gethostbyname(key_host), key_port)
        self.source = source
        self.rec_dir = rec_dir
        self.transport: asyncio.DatagramTransport | None = None
        self.streaming: asyncio.Task | None = None
        self.rx_pkts = 0
        self.rx_samples: list[int] = []
        self.wav: wave.Wave_write | None = None

    # receive what the key's microphone sends (only while its key is held)
    def connection_made(self, transport) -> None:
        self.transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        if len(data) <= 12 or data[0] >> 6 != 2 or data[1] & 0x7F != self.PT:
            return
        payload = data[12 + 4 * (data[0] & 0x0F):]
        self.rx_pkts += 1
        samples = struct.unpack(f">{len(payload) // 2}h", payload[: len(payload) // 2 * 2])
        self.rx_samples.extend(samples)
        if self.wav is None:
            self.rec_dir.mkdir(parents=True, exist_ok=True)
            path = self.rec_dir / f"from_key_{time.strftime('%Y%m%d_%H%M%S')}.wav"
            self.wav = wave.open(str(path), "wb")
            self.wav.setnchannels(1); self.wav.setsampwidth(2); self.wav.setframerate(self.RATE)
            say("cyan", f"recording what the key says → {path}")
        self.wav.writeframes(struct.pack(f"<{len(samples)}h", *samples))

    def pitch(self) -> float:
        s = self.rx_samples
        if len(s) < 1000:
            return 0.0
        crossings = sum(1 for a, b in zip(s, s[1:]) if (a < 0) != (b < 0))
        return crossings / 2 / (len(s) / self.RATE)

    def _pcm_source(self):
        if self.source:  # any audio file → 16 kHz mono s16 via ffmpeg
            raw = subprocess.run(["ffmpeg", "-v", "quiet", "-i", str(self.source), "-f", "s16le", "-ac", "1",
                                  "-ar", str(self.RATE), "-"], capture_output=True, check=True).stdout
            pcm = struct.unpack(f"<{len(raw) // 2}h", raw[: len(raw) // 2 * 2])
            while True:
                yield from pcm
        t = 0
        while True:  # synthetic "visitor": 300 Hz voice-ish tone, distinct from the key's 440 Hz
            x = t / self.RATE
            env = 0.5 + 0.5 * math.sin(2 * math.pi * 2.5 * x)
            yield int(8000 * env * (math.sin(2 * math.pi * 300 * x) + 0.4 * math.sin(2 * math.pi * 600 * x)))
            t += 1

    async def _stream(self) -> None:
        src, seq, ts, t0, n = self._pcm_source(), 0, 0, time.monotonic(), 0
        say("cyan", f"door → key audio started ({self.key[0]}:{self.key[1]})")
        while True:
            frame = [next(src) for _ in range(self.FRAME)]
            hdr = struct.pack(">BBHII", 0x80, self.PT | (0x80 if seq == 0 else 0), seq & 0xFFFF, ts, 0xD0021234)
            self.transport.sendto(hdr + struct.pack(f">{self.FRAME}h", *frame), self.key)
            seq, ts, n = seq + 1, ts + self.FRAME, n + 1
            await asyncio.sleep(max(0.0, t0 + n * 0.02 - time.monotonic()))  # real-time pacing

    def start(self) -> None:
        if self.streaming is None:
            self.streaming = asyncio.ensure_future(self._stream())

    def stop(self) -> None:
        if self.streaming:
            self.streaming.cancel()
            self.streaming = None
            say("cyan", "door → key audio stopped")
        if self.wav:
            self.wav.close()
            self.wav = None


class FakeHome:
    def __init__(self, cli: APIClient, disarm_delay: float = 0.6):
        self.cli = cli
        self.state = {LIGHT: "off", ALARM: "disarmed", DOORBELL: "off"}
        self.subscribed: set[str] = set()
        self.calls: list[tuple[str, dict]] = []  # (service or event, data) — for the test
        self.actions: dict[str, UserService] = {}
        self.demo_key: int | None = None
        self.disarm_delay = disarm_delay
        self.door: DoorAudio | None = None
        self.sensors: dict[int, str] = {}
        self.values: dict[str, float] = {}

    # ── device → "HA" ──────────────────────────────────────────────────────
    def on_state_sub(self, entity_id: str, attribute: str | None) -> None:
        self.subscribed.add(entity_id)
        say("dim", f"device subscribed to {entity_id}")
        self.push(entity_id)

    def on_call(self, call: HomeassistantServiceCall) -> None:
        data = {**call.data, **call.data_template}
        self.calls.append((call.service, data))
        if call.is_event:
            say("cyan", f"EVENT {call.service} {data}")
            if self.door and data.get("type") in ("answer", "call_door"):
                self.door.start()
            elif self.door and data.get("type") == "hangup":
                self.door.stop()
            return
        say("yellow", f"CALL  {call.service} {data}")
        if call.service == "light.toggle":
            self.set(LIGHT, "off" if self.state[LIGHT] == "on" else "on")
        elif call.service == DISARM_SCRIPT:
            asyncio.get_running_loop().call_later(self.disarm_delay, self.set, ALARM, "disarmed")

    def on_state(self, st) -> None:
        if st.key in self.sensors and hasattr(st, "state"):
            self.values[self.sensors[st.key]] = st.state

    # ── "HA" → device ──────────────────────────────────────────────────────
    def push(self, entity_id: str) -> None:
        if entity_id in self.state:
            self.cli.send_home_assistant_state(entity_id, None, self.state[entity_id])

    def set(self, entity_id: str, value: str) -> None:
        self.state[entity_id] = value
        say("green", f"STATE {entity_id} = {value}")
        self.push(entity_id)

    async def action(self, action_name: str, /, **data) -> None:
        if action_name not in self.actions:
            say("red", f"device has no action '{action_name}' (has: {', '.join(self.actions)})")
            return
        await self.cli.execute_service(self.actions[action_name], data)

    def demo(self, on: bool) -> None:
        if self.demo_key is not None:
            self.cli.switch_command(self.demo_key, on)
            say("dim", f"demo mode {'on' if on else 'off'}")

    async def start(self) -> None:
        entities, services = await self.cli.list_entities_services()
        self.actions = {s.name: s for s in services}
        for e in entities:
            if isinstance(e, SwitchInfo) and e.object_id.endswith("demo_mode"):
                self.demo_key = e.key
            self.sensors[e.key] = e.object_id
        self.cli.subscribe_home_assistant_states_and_services(
            on_state=self.on_state, on_service_call=self.on_call, on_state_sub=self.on_state_sub
        )


HELP = """commands:
  ring | stop                     doorbell rings / stops (via the `ring` action)
  bell                            doorbell via the binary_sensor entity instead
  arm [home|away|night]           alarm armed_* ;  arming | pending | trigger | disarm
  lights on|off                   push light state
  demo on|off                     toggle the key's demo mode (off = use this fake HA)
  press | hold [ms]               simulate the mechanical key
  call active|ended               door station says the call started / ended
  toast <text>                    show a message on the key
  quit"""


async def interactive(home: FakeHome) -> None:
    print(HELP)
    loop = asyncio.get_running_loop()
    while True:
        line = (await loop.run_in_executor(None, sys.stdin.readline)).strip()
        if not line:
            continue
        cmd, *rest = line.split(maxsplit=1)
        arg = rest[0] if rest else ""
        try:
            if cmd == "quit":
                return
            elif cmd == "ring":
                await home.action("ring")
            elif cmd == "stop":
                await home.action("ring_stop")
            elif cmd == "bell":
                home.set(DOORBELL, "on")
                await asyncio.sleep(0.3)
                home.set(DOORBELL, "off")
            elif cmd == "arm":
                home.set(ALARM, f"armed_{arg or 'night'}")
            elif cmd in ("arming", "pending", "disarm"):
                home.set(ALARM, {"disarm": "disarmed"}.get(cmd, cmd))
            elif cmd == "trigger":
                home.set(ALARM, "triggered")
            elif cmd == "lights":
                home.set(LIGHT, arg or "on")
            elif cmd == "demo":
                home.demo(arg != "off")
            elif cmd == "press":
                await home.action("simulate_key", hold_ms=90)
            elif cmd == "hold":
                await home.action("simulate_key", hold_ms=int(arg or 1800))
            elif cmd == "call":
                await home.action("call_state", state=arg or "active")
            elif cmd == "toast":
                await home.action("show_toast", message=arg)
            else:
                print(HELP)
        except Exception as exc:  # keep the REPL alive
            say("red", f"error: {exc}")


async def run_test(home: FakeHome, shots: bool) -> bool:
    """End-to-end check of the RoomKey ⇄ HA contract. Returns True on success."""
    results: list[tuple[str, bool]] = []

    async def snap(name: str) -> None:
        if shots and "snapshot" in home.actions:
            await home.action("snapshot", name=name)

    def seen(service: str, **match) -> bool:
        return any(s == service and all(d.get(k) == v for k, v in match.items()) for s, d in home.calls)

    def check(label: str, ok: bool) -> None:
        results.append((label, ok))
        say("green" if ok else "red", f"{'PASS' if ok else 'FAIL'}  {label}")

    async def key(ms: int) -> None:
        await home.action("simulate_key", hold_ms=ms)
        await asyncio.sleep(ms / 1000 + 0.35)

    home.demo(False)
    await asyncio.sleep(2.5)  # let the key see us as "online"
    check("key subscribed to light, alarm and doorbell entities",
          {LIGHT, ALARM, DOORBELL} <= home.subscribed)

    home.set(LIGHT, "off"); home.set(ALARM, "disarmed")
    await asyncio.sleep(0.4)
    await key(90)
    await asyncio.sleep(0.4)
    check("press on home → light.toggle", seen("light.toggle", entity_id=LIGHT))
    check("fake HA flipped the light on", home.state[LIGHT] == "on")
    await snap("e2e_01_lights_on_via_ha")

    home.set(ALARM, "armed_night")
    await asyncio.sleep(0.5)
    await snap("e2e_02_armed_night")
    await key(1800)
    await asyncio.sleep(0.2)
    check("hold on armed home → disarm script with room + entity",
          seen(DISARM_SCRIPT, entity_id=ALARM, room="Office"))
    await asyncio.sleep(0.8)
    check("alarm disarmed after HA confirmed", home.state[ALARM] == "disarmed")

    home.set(DOORBELL, "on"); await asyncio.sleep(0.3); home.set(DOORBELL, "off")
    await asyncio.sleep(0.8)
    await snap("e2e_03_ring_from_ha_entity")
    await key(90)
    check("press while ringing → event answer", seen("esphome.roomkey", type="answer"))
    if home.door:
        await asyncio.sleep(6.0)  # the key reports its packet counters every 5 s
        await snap("e2e_03b_listening_to_door")
        check("key receives door audio (RTP)", home.values.get("intercom_rx_packets", 0) > 50)
    await key(1500)
    check("hold in call → talk_start + talk_stop events",
          seen("esphome.roomkey", type="talk_start") and seen("esphome.roomkey", type="talk_stop"))
    if home.door:
        pitch = home.door.pitch()
        check(f"door receives the key's voice while held ({home.door.rx_pkts} pkts, ~{pitch:.0f} Hz)",
              home.door.rx_pkts >= 40 and 380 < pitch < 520)
    await key(90)
    check("press in call → event hangup", seen("esphome.roomkey", type="hangup"))

    await home.action("ring")
    await asyncio.sleep(0.5)
    await home.action("ring_stop")
    await asyncio.sleep(0.3)

    home.set(ALARM, "pending")
    await asyncio.sleep(1.2)
    await snap("e2e_04_entry_delay_from_ha")
    home.set(ALARM, "triggered")
    await asyncio.sleep(0.6)
    n_before = sum(1 for s, _ in home.calls if s == DISARM_SCRIPT)
    await key(1800)
    await asyncio.sleep(1.0)
    check("hold during triggered alarm → disarm script",
          sum(1 for s, _ in home.calls if s == DISARM_SCRIPT) == n_before + 1)
    await snap("e2e_05_disarmed_flash")

    await home.action("show_toast", message="Parcel at the door")
    await asyncio.sleep(0.3)
    await snap("e2e_06_toast_from_ha")

    home.demo(True)
    ok = all(r for _, r in results)
    say("green" if ok else "red", f"{sum(r for _, r in results)}/{len(results)} checks passed")
    return ok


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=6053)
    ap.add_argument("--secrets", type=Path, default=Path(__file__).resolve().parent.parent / "esphome" / "secrets.yaml")
    ap.add_argument("--test", action="store_true", help="run the automated contract test and exit")
    ap.add_argument("--shots", action="store_true", help="with --test: save simulator snapshots")
    ap.add_argument("--no-audio", action="store_true", help="don't act as the door station's audio side")
    ap.add_argument("--door-audio", type=Path, help="audio file the 'visitor' plays (default: synthetic tone)")
    ap.add_argument("--door-port", type=int, default=5006, help="local UDP port of the fake door station")
    ap.add_argument("--key-port", type=int, default=5004, help="the key's intercom UDP port")
    ap.add_argument("--recordings", type=Path, default=Path(__file__).resolve().parent / "recordings")
    args = ap.parse_args()

    cli = APIClient(args.host, args.port, "", noise_psk=api_key_from_secrets(args.secrets), client_info="fake_home")
    await cli.connect(login=True)
    info = await cli.device_info()
    say("dim", f"connected to {info.name} ({info.project_name} {info.project_version}, ESPHome {info.esphome_version})")
    home = FakeHome(cli)
    if not args.no_audio:
        loop = asyncio.get_running_loop()
        door = DoorAudio(args.host, args.key_port, args.door_audio, args.recordings)
        await loop.create_datagram_endpoint(lambda: door, local_addr=("0.0.0.0", args.door_port))
        home.door = door
    await home.start()
    try:
        if args.test:
            ok = await run_test(home, args.shots)
            await asyncio.sleep(0.3)
            sys.exit(0 if ok else 1)
        await interactive(home)
    finally:
        await cli.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
