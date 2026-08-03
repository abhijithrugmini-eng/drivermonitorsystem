"""
Configuration for Edge AI Driver Monitoring System
AI Center of Excellence — Renesas R-Car / 4 GB RAM / Linux prototype

All temporal thresholds are in seconds (frame-rate independent).
"""
import os

# ──────────────────────────────────────────────
# Project Paths
# ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
VIDEOS_DIR = os.path.join(PROJECT_ROOT, "videos")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")
BENCH_DIR = os.path.join(OUTPUT_DIR, "benchmarks")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
CALIB_DIR = os.path.join(DATA_DIR, "calib")

# ──────────────────────────────────────────────
# Model Paths
# ──────────────────────────────────────────────
YOLO_MODEL_PATH = os.path.join(MODELS_DIR, "yolov8n.pt")
YOLO_ONNX_FP32 = os.path.join(MODELS_DIR, "yolov8n_fp32.onnx")
YOLO_ONNX_FP16 = os.path.join(MODELS_DIR, "yolov8n_fp16.onnx")
YOLO_ONNX_INT8 = os.path.join(MODELS_DIR, "yolov8n_int8.onnx")
# Backward-compat alias (used by the production runtime)
YOLO_ONNX_PATH = YOLO_ONNX_INT8
LLM_MODEL_PATH = os.path.join(MODELS_DIR, "smollm2-135m-instruct-q8_0.gguf")

# ──────────────────────────────────────────────
# Inference Schedule (tuned for 4 GB Renesas board)
# ──────────────────────────────────────────────
PROCESS_WIDTH = 640
PROCESS_HEIGHT = 360
YOLO_INPUT_SIZE = 320
YOLO_FRAME_SKIP = 3
INFER_EVERY_N_FRAMES = 1

# ──────────────────────────────────────────────
# Face Analysis — Drowsiness (Eye Aspect Ratio)
# Time-based so behavior is consistent across all input frame rates.
# ──────────────────────────────────────────────
EAR_THRESHOLD = 0.21
EAR_CONSEC_SECS = 0.7             # eyes closed continuously > 0.7s → drowsy
BLINK_MAX_SECS = 0.25             # up to 0.25s is a normal blink (do not alert)

# ──────────────────────────────────────────────
# Face Analysis — Yawning (Mouth Aspect Ratio)
# ──────────────────────────────────────────────
MAR_THRESHOLD = 0.70
MAR_CONSEC_SECS = 0.5             # mouth open > 0.5s → yawn

# ──────────────────────────────────────────────
# Face Analysis — Distraction (Head Pose)
# ──────────────────────────────────────────────
HEAD_YAW_THRESHOLD = 30.0
HEAD_PITCH_THRESHOLD = 25.0
GAZE_AWAY_CONSEC_SECS = 1.0       # look away > 1.0s → distracted

# ──────────────────────────────────────────────
# Face presence
# ──────────────────────────────────────────────
NO_FACE_CONSEC_SECS = 2.0         # no face detected > 2.0s → alert

# ──────────────────────────────────────────────
# YOLO Object Detection
# ──────────────────────────────────────────────
YOLO_CONFIDENCE = 0.45
YOLO_TARGET_CLASSES = {
    67: "cell phone",
}

# ──────────────────────────────────────────────
# Continuous driving
# ──────────────────────────────────────────────
CONTINUOUS_DRIVE_ALERT_MINS = 120
CONTINUOUS_DRIVE_REMIND_MINS = 30

# ──────────────────────────────────────────────
# Alert Cooldowns (per event type)
# ──────────────────────────────────────────────
ALERT_COOLDOWN_SECS = 10.0
CRITICAL_ALERT_COOLDOWN_SECS = 5.0
ADMIN_ALERT_COOLDOWN_SECS = 30.0

# ──────────────────────────────────────────────
# Small LLM (off-device only for phase 1)
# ──────────────────────────────────────────────
LLM_ENABLED = False
LLM_MAX_TOKENS = 100
LLM_TEMPERATURE = 0.3
LLM_N_CTX = 512
LLM_N_THREADS = 4

# ──────────────────────────────────────────────
# UI / SSE Server
# ──────────────────────────────────────────────
UI_HOST = "0.0.0.0"
UI_PORT = 5050  # macOS AirPlay uses 5000; pick something free on the Renesas board too

# ──────────────────────────────────────────────
# Display
# ──────────────────────────────────────────────
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720

# ──────────────────────────────────────────────
# Agentic layer (dms-edge/agents/) — Telematics / Behaviour Detection / Cloud Hub
# See .claude/skills/dms-agentic-architecture/SKILL.md and dms-edge-dev/SKILL.md
# ──────────────────────────────────────────────
EDGE_VEHICLE_REGISTRATION = os.environ.get("EDGE_VEHICLE_REGISTRATION", "EDGE-DEMO-001")

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
BACKEND_REQUEST_TIMEOUT_SECS = 0.5

TELEMATICS_INGEST_HOST = "0.0.0.0"
TELEMATICS_INGEST_PORT = int(os.environ.get("TELEMATICS_INGEST_PORT", "5060"))

DEVICE_ID = os.environ.get("DEVICE_ID", "edge-001")
DEVICE_MODEL = "renesas_rcar"
CAMERA_ID = "cam-0"

# ──────────────────────────────────────────────
# Violation Detection Agent — local rule thresholds
# Ported from dms-backend/app/config.py; keep these in sync — see
# dms-spec/changes/move-violation-detection-to-edge/design.md "Risks".
# ──────────────────────────────────────────────
DROWSINESS_EVENT_COUNT = 3
DROWSINESS_WINDOW_SECONDS = 120

PHONE_USAGE_CONFIDENCE_THRESHOLD = 0.85

DISTRACTION_EVENT_COUNT = 2
DISTRACTION_WINDOW_SECONDS = 60

CONTINUOUS_DRIVE_HOURS_THRESHOLD = 4

LOCAL_DB_PATH = os.environ.get("LOCAL_DB_PATH", os.path.join(PROJECT_ROOT, "storage", "local.db"))
