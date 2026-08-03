"""Central config for the DMS backend — thresholds and paths are tunable here for live demo tuning."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

HOST = "0.0.0.0"
PORT = 8000

STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "dms.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

EVIDENCE_DIR = STORAGE_DIR / "evidence"
EVIDENCE_IMAGES_DIR = EVIDENCE_DIR / "images"
EVIDENCE_VIDEOS_DIR = EVIDENCE_DIR / "videos"

CORS_ORIGINS = ["*"]

# Rule thresholds — tune live for demos
DROWSINESS_EVENT_COUNT = 3
DROWSINESS_WINDOW_SECONDS = 120

PHONE_USAGE_CONFIDENCE_THRESHOLD = 0.85

DISTRACTION_EVENT_COUNT = 2
DISTRACTION_WINDOW_SECONDS = 60

CONTINUOUS_DRIVE_HOURS_THRESHOLD = 4
