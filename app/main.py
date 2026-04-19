import time
import uuid

from fastapi import FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.api.v1 import health, auth, conversation
from app.websocket.router import router as ws_router
from app.core.limiter import limiter
from app.core.logger import logger, bind_contextvars, clear_contextvars
from app.core.error_handler import validation_exception_handler, unhandled_exception_handler

app = FastAPI(title="Chat-Backend")

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    clear_contextvars()

    request_id = str(uuid.uuid4())

    bind_contextvars(request_id=request_id)

    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    process_time_ms = round((time.time() - start_time) * 1000, 2)

    if request.url.path != "/favicon.ico":
        logger.info(
            "access_log",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=process_time_ms,
            client_ip=request.client.host if request.client else None
        )

    response.headers["X-Request-ID"] = request_id

    return response

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(conversation.router, prefix="/api/v1")
app.include_router(ws_router)
