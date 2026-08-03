from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.api import fleet_api, inject_api, websocket
from app.db.database import init_db

app = FastAPI(title="DMS Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()


app.include_router(inject_api.router)
app.include_router(fleet_api.router)
app.include_router(websocket.router)


@app.get("/")
def root():
    return {"status": "ok", "service": "dms-backend"}
