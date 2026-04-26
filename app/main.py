from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app import models

# Create database tables (for simple setup)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FastAPI App",
    description="A FastAPI backend with PostgreSQL",
    version="1.0.0",
)

# =========================
# CORS CONFIGURATION
# =========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# ROOT ENDPOINT
# =========================
@app.get("/")
def read_root():
    return {
        "message": "FastAPI is running 🚀",
        "status": "success"
    }

# =========================
# HEALTH CHECK
# =========================
@app.get("/health")
def health_check():
    return {"status": "ok"}