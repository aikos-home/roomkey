#!/usr/bin/env python3
"""
ha_contract_test.py — end-to-end test of a RoomKey against a REAL Home Assistant.

Drives the key through HA (the key's `simulate_key` action) and checks what HA sees.
Needs the RoomKey HA package plus stand-ins for lights / alarm / doorbell
(homeassistant/dev/roomkey.yaml) and "Allow the device to perform Home Assistant actions".

    python3 tools/ha_contract_test.py --url http://<ha>:8123 --token-file ~/.ha-dev/token --node roomkey-sim

Only the Python standard library. Leaves the stand-ins as it found them (lights off, alarm
disarmed, doorbell off) and the key's demo mode OFF (live against HA).
"""
import argparse
import datetime as dt
import json
import sys
import time
import urllib.request
from pathlib import Path


class HA:
    def __init__(self, url, token):
        self.url, self.token = url.rstrip("/"), token

    def _req(self, method, path, body=None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
            return json.loads(raw) if raw else None

    def state(self, eid):
        return self._req("GET", f"/api/states/{eid}")["state"]

    def call(self, domain, service, **data):
        return self._req("POST", f"/api/services/{domain}/{service}", data)

    def logbook_since(self, t0):
        return self._req("GET", "/api/logbook/" + t0.isoformat()) or []

    def entities(self, prefix):
        return [s["entity_id"] for s in self._req("GET", "/api/states") if s["entity_id"].startswith(prefix)]


def wait_for(fn, expect, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v == expect:
            return v
        time.sleep(0.3)
    return fn()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", required=True)
    ap.add_argument("--token-file", type=Path, required=True)
    ap.add_argument("--node", default="roomkey-sim", help="ESPHome node name of the key")
    a = ap.parse_args()
    ha = HA(a.url, a.token_file.expanduser().read_text().strip())
    svc = a.node.replace("-", "_")
    results = []

    def check(label, ok, detail=""):
        results.append(ok)
        print(("PASS  " if ok else "FAIL  ") + label + (f"  ({detail})" if detail else ""), flush=True)

    def key(ms):
        ha.call("esphome", f"{svc}_simulate_key", hold_ms=ms)
        time.sleep(ms / 1000 + 0.6)

    t0 = dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=2)
    demo = [e for e in ha.entities("switch.") if e.endswith("demo_mode") and svc.split("_")[-1] in e] or \
           [e for e in ha.entities("switch.") if e.endswith("demo_mode")]
    check("key's demo-mode switch found in HA", bool(demo), demo[0] if demo else "none")
    if demo:
        ha.call("switch", "turn_off", entity_id=demo[0])
        time.sleep(1.5)

    # lights
    ha.call("light", "turn_off", entity_id="light.all_lights")
    wait_for(lambda: ha.state("light.all_lights"), "off")
    key(90)
    check("key press → HA light.toggle → all lights on", wait_for(lambda: ha.state("light.all_lights"), "on") == "on")
    key(90)
    check("second press → all lights off", wait_for(lambda: ha.state("light.all_lights"), "off") == "off")

    # alarm: arm night, hold to disarm via the HA policy script
    ha.call("alarm_control_panel", "alarm_arm_night", entity_id="alarm_control_panel.house")
    armed = wait_for(lambda: ha.state("alarm_control_panel.house"), "armed_night", timeout=10)
    check("test alarm armed (night)", armed == "armed_night", armed)
    key(1900)
    st = wait_for(lambda: ha.state("alarm_control_panel.house"), "disarmed", timeout=6)
    check("hold 1.5 s on armed key → roomkey_disarm script → disarmed", st == "disarmed", st)

    # policy: AWAY must be refused
    ha.call("alarm_control_panel", "alarm_arm_away", entity_id="alarm_control_panel.house")
    armed = wait_for(lambda: ha.state("alarm_control_panel.house"), "armed_away", timeout=10)
    key(1900)
    time.sleep(1.5)
    st = ha.state("alarm_control_panel.house")
    check("policy: hold during ARMED_AWAY is refused by HA", st == "armed_away", st)
    ha.call("alarm_control_panel", "alarm_disarm", entity_id="alarm_control_panel.house")
    time.sleep(9)   # the key waits 8 s for a disarm that HA refused, then returns home

    # doorbell → ring → answer / talk / hang up events
    # The real bell can't be pressed by software → ring via the key's own action
    # (the doorbell entity path is verified with real presses and "Doorbell presses received").
    ha.call("esphome", f"{svc}_ring")
    time.sleep(1.2)
    key(90)          # answer
    key(1200)        # talk
    key(90)          # hang up
    # The recorder commits every ~5 s and the logbook API reads the database → poll.
    want = ("answer", "talk_start", "talk_stop", "hangup")
    end = time.time() + 12
    while True:
        msgs = [e.get("message", "") for e in ha.logbook_since(t0) if e.get("name") == "RoomKey"]
        if all(any(m.endswith(": " + k) for m in msgs) for k in want) or time.time() > end:
            break
        time.sleep(1.0)
    for kind in want:
        check(f"HA logbook shows event '{kind}'", any(m.endswith(": " + kind) for m in msgs))
    check("HA logbook shows the allowed + refused disarm requests",
          any("allowed" in m for m in msgs) and any("refused" in m for m in msgs))

    ok = all(results)
    print(f"\n{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
