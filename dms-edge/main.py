"""
Edge AI DMS — entry point.

Phase 1 (demo): pre-recorded video files only.
Phase 2 (deferred): live camera (USB / MIPI / RTSP).

Modes:
  python main.py --video videos/dataset.mp4 --save   (process a recorded file)
  python main.py --camera 0                         (PHASE 2: live camera — not used in demo)
  python main.py --no-ui --video videos/dataset.mp4 (no SSE / no display)

Wires the dms-edge agents (see agents/, .claude/skills/dms-agentic-architecture/SKILL.md) on top of
the frozen src/dms.py pipeline: TelematicsAgent (receives simulated vehicle telemetry),
BehaviourDetectionAgent (wraps DriverMonitoringSystem), ViolationDetectionAgent (local rule
evaluation against storage/local.db), AlarmAgent (escalation-tier in-cabin alert), CloudHubAgent
(pushes events/violations to dms-backend).
"""
import argparse
import cv2
import os
import sys
import time
import threading

from src.config import (
    DISPLAY_WIDTH, DISPLAY_HEIGHT, OUTPUT_DIR,
    LOG_DIR, YOLO_FRAME_SKIP, UI_HOST, UI_PORT,
)
from src.ui_server import sink, start_server
from agents.telematics_agent import TelematicsAgent
from agents.behaviour_detection_agent import BehaviourDetectionAgent
from agents.violation_detection_agent import ViolationDetectionAgent
from agents.alarm_agent import AlarmAgent
from agents.cloud_hub_agent import CloudHubAgent, EVIDENCE_EVENT_TYPES
from storage.database import init_db


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            "Edge AI Driver Monitoring System — AI COE demo.\n"
            "Phase 1: pre-recorded video only. --camera is reserved for Phase 2."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--video", type=str, help="[Phase 1] Path to input video file")
    p.add_argument(
        "--camera", type=int,
        help="[Phase 2, not used in demo] Camera index. Reserved for live in-cabin deployment.",
    )
    p.add_argument("--save", action="store_true", help="Save annotated output video")
    p.add_argument("--no-ui", action="store_true", help="Disable SSE / Flask UI")
    p.add_argument("--no-display", action="store_true", help="Disable cv2.imshow")
    p.add_argument("--no-cloud", action="store_true", help="Disable Cloud Hub Agent push to dms-backend")
    return p.parse_args()


def file_logger(events_log_path: str):
    """Optional: write each DMSEvent as JSONL to logs/events.jsonl"""
    import json
    os.makedirs(LOG_DIR, exist_ok=True)
    f = open(events_log_path, "a", buffering=1)
    lock = threading.Lock()

    class _Sink:
        def emit(self, event):
            with lock:
                f.write(json.dumps(event.to_json()) + "\n")
        def close(self):
            f.close()
    return _Sink()


def main():
    args = parse_args()

    if not args.video and args.camera is None:
        print("Phase 1 demo: provide --video <path>")
        print("Phase 2 (deferred): --camera <index>")
        sys.exit(1)

    if args.camera is not None and args.video is None:
        print("ERROR: --camera is Phase 2 only. Demo runs on --video <path>.")
        sys.exit(1)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    init_db()

    log_path = os.path.join(LOG_DIR, "events.jsonl")
    file_sink = file_logger(log_path)

    telematics_agent = TelematicsAgent()
    threading.Thread(target=telematics_agent.start_listener, daemon=True).start()

    behaviour_agent = BehaviourDetectionAgent()
    violation_agent = ViolationDetectionAgent()
    alarm_agent = AlarmAgent()
    cloud_hub_agent = None if args.no_cloud else CloudHubAgent(telematics_agent)

    def dispatch(event):
        file_sink.emit(event)
        sink.emit(event)

        violation = violation_agent.run(event)
        alarm = None
        if violation is not None:
            vehicle_state = telematics_agent.get_latest_state()
            alarm = alarm_agent.run(violation, speed_kmh=vehicle_state.speed_kmh)

        if cloud_hub_agent is not None:
            evidence_frame = (
                behaviour_agent.last_frame if event.event_type in EVIDENCE_EVENT_TYPES else None
            )
            cloud_hub_agent.run(event, evidence_frame=evidence_frame)
            if violation is not None:
                cloud_hub_agent.push_violation(violation, alarm)

    if not args.no_ui:
        threading.Thread(target=start_server, args=(behaviour_agent.dms,),
                         daemon=True).start()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"Error: cannot open input {args.video}")
        sys.exit(1)

    fps_in = cap.get(cv2.CAP_PROP_FPS) or 30.0
    print(f"Input FPS: {fps_in:.1f}")

    out = None
    if args.save:
        base = os.path.basename(args.video)
        out_path = os.path.join(OUTPUT_DIR, f"dms_out_{base}")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(out_path, fourcc, fps_in,
                              (DISPLAY_WIDTH, DISPLAY_HEIGHT))
        print(f"Recording → {out_path}")

    print(f"Processing (YOLO every {YOLO_FRAME_SKIP} frames)…  press 'q' to quit")
    frame_count = 0
    start = time.time()
    last_frame_t = start
    fps_now = 0.0

    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            frame_count += 1
            now = time.time()
            frame_dt = now - last_frame_t
            last_frame_t = now

            frame = cv2.resize(frame, (DISPLAY_WIDTH, DISPLAY_HEIGHT))
            events = behaviour_agent.run(frame, frame_index=frame_count, frame_dt=frame_dt)
            for event in events:
                dispatch(event)
            processed = behaviour_agent.last_frame

            elapsed = now - start
            fps_now = frame_count / elapsed if elapsed > 0 else 0
            cv2.putText(processed, f"FPS: {fps_now:.1f}",
                        (DISPLAY_WIDTH - 160, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            if out:
                out.write(processed)

            if not args.no_display:
                try:
                    cv2.imshow("Edge AI DMS", processed)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break
                except Exception:
                    pass
    finally:
        cap.release()
        if out:
            out.release()
        cv2.destroyAllWindows()
        file_sink.close()

    stats = behaviour_agent.dms.trip.snapshot()
    print(f"\nDone. {frame_count} frames @ {fps_now:.1f} FPS")
    print(f"Trip stats: {stats}")


if __name__ == "__main__":
    main()
