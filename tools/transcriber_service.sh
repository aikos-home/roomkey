#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# aikos transcriber (WIP): one receiver per side, meant to run under launchd.
#   side "room": RoomKeys → UDP 5006 → sensor.talk_transcript        (shown at the door)
#   side "door": door     → UDP 5008 → sensor.talk_transcript_door   (shown on the keys)
# Each utterance (RTP L16 16 kHz, ended by a comfort-noise packet when the talk button is released)
# is transcribed by the local whisper-server, "who is speaking" is detected (tools/talk_identity.py,
# local Ollama as fallback) and the result is published to Home Assistant. Recordings are deleted
# when done. Nothing leaves the machine except the HA call. Python 3.9+ standard library, curl.
#
# Configuration (environment; launchd: EnvironmentVariables):
#   AIKOS_SIDE          room | door                                  (required)
#   AIKOS_PORT          default 5006 (room) / 5008 (door)
#   AIKOS_HA_URL        e.g. http://homeassistant.local:8123         (required)
#   AIKOS_HA_TOKEN_FILE file with a long-lived HA token, mode 600     (required)
#   AIKOS_KNOWN_NAMES   household first names, comma-separated (improves Whisper and display), optional
#   AIKOS_WHISPER_URL   default http://127.0.0.1:6667/v1/audio/transcriptions
#   AIKOS_LLM_URL       default http://127.0.0.1:11434   (Ollama; model qwen3:8b, kept loaded)
#   AIKOS_RECORDINGS    default ~/Library/Application Support/aikos/transcriber/recordings
#   AIKOS_PYTHON        default /usr/bin/python3
#   AIKOS_LIVE          1 = publish partial text while talking (sensor.talk_live_door / sensor.talk_live);
#                       default 1 for the door side, 0 for the room side
# If the port is taken (e.g. another receiver still runs), the script exits; launchd starts it again.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

side="${AIKOS_SIDE:?AIKOS_SIDE=room|door}"
case "$side" in room) port="${AIKOS_PORT:-5006}" ;; door) port="${AIKOS_PORT:-5008}" ;; *) echo "bad AIKOS_SIDE" >&2; exit 2 ;; esac
ha="${AIKOS_HA_URL:?AIKOS_HA_URL}"
token="${AIKOS_HA_TOKEN_FILE:?AIKOS_HA_TOKEN_FILE}"
whisper="${AIKOS_WHISPER_URL:-http://127.0.0.1:6667/v1/audio/transcriptions}"
llm="${AIKOS_LLM_URL:-http://127.0.0.1:11434}"
rec="${AIKOS_RECORDINGS:-$HOME/Library/Application Support/aikos/transcriber/recordings}"
py="${AIKOS_PYTHON:-/usr/bin/python3}"
names="${AIKOS_KNOWN_NAMES:-}"
[ -r "$token" ] || { echo "token file not readable: $token" >&2; exit 2; }

q() { printf '%q' "$1"; }   # quote for the --exec command line
live=()
if [ "${AIKOS_LIVE:-$([ "$side" = door ] && echo 1 || echo 0)}" = 1 ]; then
  entity=sensor.talk_live; [ "$side" = door ] && entity=sensor.talk_live_door
  live=(--live "$entity" --live-side "$side" --ha-url "$ha" --token-file "$token" --whisper-url "$whisper" --known-names "$names")
fi
exec "$py" -u tools/rtp_recorder.py --port "$port" --out "$rec" ${live[@]+"${live[@]}"} \
  --on-start "curl -s -m 30 $(q "$llm")/api/generate -d '{\"model\":\"qwen3:8b\",\"keep_alive\":-1}' >/dev/null" \
  --exec "$(q "$py") -u tools/transcribe_publish.py {wav} --side $side --source-ip {src} --ha-url $(q "$ha") \
--token-file $(q "$token") --whisper-url $(q "$whisper") --llm-url $(q "$llm") --known-names $(q "$names") --delete-wav"
