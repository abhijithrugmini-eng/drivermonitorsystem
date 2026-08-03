# Review — add-dms-edge

## How this was reviewed

Self-review pass: re-read the full diff (`git diff --cached -- dms-edge dms-spec .gitignore`) after
Apply, plus live end-to-end verification (unit tests, manual `curl` against the Telematics Agent's
listener, a synthetic-video run of the full `main.py` pipeline, and pushing synthetic `DMSEvent`s
through `CloudHubAgent` against the actually-running, Dockerized `dms-backend`).

## Findings

- [bug] `agents/behaviour_detection_agent.py` imported `EventSink` from `src.ui_server`, but it's
  actually defined in `src.dms` — `dms-edge/agents/behaviour_detection_agent.py:13` (pre-fix)
  - **fixed** — caught immediately by the first `python main.py` smoke run (`ImportError`); unit
    tests didn't catch it because they only import `agents.telematics_agent` /
    `agents.cloud_hub_agent`, not `behaviour_detection_agent` (which needs mediapipe/YOLO to
    construct). Fixed by importing `EventSink` from `src.dms` alongside `DriverMonitoringSystem`.
- [gap] `onnxruntime` was never declared as a dependency, in either this change's first draft of
  `requirements.txt` or the original vendored `specs/DriverMonitorPOC-main/requirements.txt` — the
  ONNX model files in `models/` are unusable without it, silently degrading YOLO/phone-detection to
  a no-op (`[YOLO] predict error: No module named 'onnxruntime'` per-frame, pipeline otherwise kept
  running since the reference app already treats YOLO failures as non-fatal)
  - **fixed** — added `onnxruntime>=1.16.0` to `dms-edge/requirements.txt` (not a change to the
    frozen `src/` tree, just the dependency manifest); re-verified the full pipeline picks up YOLO
    correctly afterward (`Using ONNX Runtime 1.28.0 with CPUExecutionProvider`).
- [accepted as-is] `CloudHubAgent.run(input_, evidence_frame=None)` takes an extra optional kwarg
  beyond the strict `BaseAgent[DMSEvent, None]` single-argument shape, so it can attach the
  annotated frame for evidence upload without `CloudHubAgent` reaching into
  `BehaviourDetectionAgent`'s internals itself.
  - **accepted as-is** — `main.py`'s `dispatch()` is the one place that decides which frame to pass
    (only for `PHONE_USAGE`/`DROWSINESS`), keeping `CloudHubAgent` from importing/depending on
    `BehaviourDetectionAgent` at all. A stricter single-arg `run()` would need a second data class
    wrapping `(event, frame)`, which felt like unwarranted ceremony for a POC-scale, one-call-site
    convenience parameter — flagging here rather than silently deviating from the doc's contract.
- [accepted as-is] `dms-edge/main.py` still imports `UI_HOST`/`UI_PORT` from `src.config` without
  using them directly — pre-existing in the original vendored `main.py` (they're consumed inside
  `src/ui_server.py`'s `start_server()`, not by `main.py` itself), not introduced by this change, and
  `src/` is meant to stay untouched/vendored — left as-is rather than "fixing" someone else's frozen
  file's minor unused-import quirk.

## Sign-off

Ready for Release. All 6 `tasks.md` sections checked and verified working (not just written): unit
tests pass (8/8), Telematics Agent's HTTP listener verified live via `curl`, the full `main.py`
pipeline runs end-to-end on a synthetic video with both MediaPipe and YOLO(ONNX) active, and
`CloudHubAgent` was confirmed to produce a real `HIGH` `PHONE_USAGE` violation and a stored evidence
JPG against the live, Dockerized `dms-backend`.
