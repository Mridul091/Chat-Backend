from fastapi import FastAPI
from app.api.v1 import health, db_test, auth, conversation

app = FastAPI(title="Chat-Backend")

app.include_router(health.router, prefix="/api/v1")
app.include_router(db_test.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(conversation.router, prefix="/api/v1")