import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, accounts, posts, insights, recommendations, briefs, metrics, remix, csv_import, sync
from app.workers.scheduler import setup_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_scheduler()
    yield
    # Shutdown


app = FastAPI(title="Social Media Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(posts.router)
app.include_router(insights.router)
app.include_router(recommendations.router)
app.include_router(briefs.router)
app.include_router(metrics.router)
app.include_router(remix.router)
app.include_router(csv_import.router)
app.include_router(sync.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
