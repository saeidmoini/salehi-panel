from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.db import Base, engine
from .core.config import get_settings
from .api import auth, admins, schedule, numbers, dialer, stats

settings = get_settings()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Salehi Dialer Admin Panel")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admins.router, prefix="/api/admins", tags=["admins"])
app.include_router(schedule.router, prefix="/api/schedule", tags=["schedule"])
app.include_router(numbers.router, prefix="/api/numbers", tags=["numbers"])
app.include_router(dialer.router, prefix="/api/dialer", tags=["dialer"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])


@app.get("/health")
def health():
    return {"status": "ok"}
