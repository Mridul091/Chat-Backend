from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import health, db_test, auth, conversation
from app.websocket.router import router as ws_router

app = FastAPI(title="Chat-Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000", 
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(db_test.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(conversation.router, prefix="/api/v1")
app.include_router(ws_router)

# Serve the test frontend at /static/index.html
static_dir = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir), html=True), name="static")