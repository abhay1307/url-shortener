from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_tables
from app.routes import analytics, url

app = FastAPI(
    title="URL Shortener",
    description="Distributed URL shortener with real-time click analytics",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    create_tables()
    print("[API] Tables ready. Server started.")


app.include_router(url.router)
app.include_router(analytics.router)


@app.get("/health")
def health():
    return {"status": "ok"}
