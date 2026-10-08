# tools/

| What | Where now |
|---|---|
| Transcriber (`rtp_recorder.py`, `transcribe_publish.py`, `talk_live.py`, `talk_identity.py`, `transcriber_service.sh`) | **moved** to [aikos-home/aikos `services/transcriber`](https://github.com/aikos-home/aikos/tree/main/services/transcriber), tag `transcriber-v1.0.0` |
| "Who is speaking" eval (`talk_eval.py`, `talk_eval_cases.json`, `eval/`) | **moved** to `services/transcriber/tools/talk_eval.py` and `services/transcriber/tests/eval/` (snapshot test in CI) |

They were removed here on 2026-10-01 after the Mac service switched to the tag (the git history keeps them). Changes
to the transcriber go to aikos-home/aikos only (pull request, `transcriber-unit` green, RoomKey review of the identity
logic, new tag).

Still RoomKey's own: `rtp_play.py` (send a WAV as RTP: stands in for a key or the door), `mic_check.py`,
`fake_home.py` and `ha_contract_test.py` (Home Assistant contract tests), `voice_host_check.py` (the key's voice v2 on
the simulator against a fake door on this machine, build `esphome/sim_v2_check.yaml` first), `privacy_scan.py`, and the CAD helpers
(`cad_preview.py`, `insert_drawings.py`, `insert_wallcheck.py`, and `bambu_kit.py`, which slices the kit into
ready-to-print Bambu Lab A1 files, see `hardware/print/`).
