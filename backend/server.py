"""
Bharat Market Intel Agent (BMIA) - FastAPI Backend
Slim entry point — routes and daemons are modularized.
"""
import os
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from services.dashboard_service import start_background_cache
from services.guidance_service import start_guidance_scheduler
from services.pdf_extractor_service import start_pdf_extraction_daemon
from services.portfolio_engine import start_portfolio_daemon
from daemons.evaluation_scheduler import start_evaluation_scheduler

from routes.symbols import router as symbols_router
from routes.market import router as market_router
from routes.analysis import router as analysis_router
from routes.signals import router as signals_router
from routes.guidance import router as guidance_router
from routes.bse import router as bse_router
from routes.portfolios import router as portfolios_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = AsyncIOMotorClient(MONGO_URL)
    app.db = app.mongodb_client[DB_NAME]
    logger.info("Connected to MongoDB")

    # Start background daemons (all non-blocking)
    for name, starter, args in [
        ("Background cache", start_background_cache, ()),
        ("Evaluation scheduler", start_evaluation_scheduler, (MONGO_URL, DB_NAME)),
        ("Guidance scheduler", start_guidance_scheduler, (MONGO_URL, DB_NAME)),
        ("PDF extraction daemon", start_pdf_extraction_daemon, (MONGO_URL, DB_NAME)),
        ("Portfolio daemon", start_portfolio_daemon, (MONGO_URL, DB_NAME)),
    ]:
        try:
            starter(*args)
        except Exception as e:
            logger.error(f"{name} start failed (non-fatal): {e}")

    yield
    app.mongodb_client.close()


app = FastAPI(title="Bharat Market Intel Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "BMIA", "timestamp": datetime.now().isoformat()}


# Register route modules
app.include_router(symbols_router)
app.include_router(market_router)
app.include_router(analysis_router)
app.include_router(signals_router)
app.include_router(guidance_router)
app.include_router(bse_router)
app.include_router(portfolios_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
