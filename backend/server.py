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
from services.vector_store import guidance_vector_store
from daemons.evaluation_scheduler import start_evaluation_scheduler
from daemons.portfolio_daemon import start_portfolio_daemon
from daemons.compliance_ingestion import start_compliance_daemon
from services.compliance_rag import compliance_router
from utils.safe_json import SafeJSONResponse

from routes.symbols import router as symbols_router
from routes.market import router as market_router
from routes.analysis import router as analysis_router
from routes.signals import router as signals_router
from routes.guidance import router as guidance_router
from routes.bse import router as bse_router
from routes.portfolios import router as portfolios_router
from routes.custom_portfolios import router as custom_portfolios_router
from routes.totp_auth import router as totp_auth_router
from routes.daemon_control import router as daemon_control_router
from routes.audit_log import router as audit_log_router, audit_middleware
from routes.big_market import router as big_market_router
from routes.compliance import router as compliance_router_routes

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
        ("Compliance ingestion daemon", start_compliance_daemon, (MONGO_URL, DB_NAME)),
    ]:
        try:
            starter(*args)
        except Exception as e:
            logger.error(f"{name} start failed (non-fatal): {e}")

    # Build vector store in background (non-blocking — server starts immediately)
    import asyncio
    async def _build_vector_store():
        try:
            await guidance_vector_store.build(app.db)
        except Exception as e:
            logger.error(f"Vector store initial build failed (non-fatal): {e}")
    asyncio.ensure_future(_build_vector_store())

    # Build compliance RAG stores (non-blocking)
    async def _build_compliance_stores():
        try:
            await compliance_router.build_all(app.db)
        except Exception as e:
            logger.error(f"Compliance RAG initial build failed (non-fatal): {e}")
    asyncio.ensure_future(_build_compliance_stores())

    yield
    app.mongodb_client.close()


app = FastAPI(
    title="Bharat Market Intel Agent",
    lifespan=lifespan,
    default_response_class=SafeJSONResponse,
)

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
app.include_router(custom_portfolios_router)
app.include_router(totp_auth_router)
app.include_router(daemon_control_router)
app.include_router(audit_log_router)
app.include_router(big_market_router)
app.include_router(compliance_router_routes)

app.middleware("http")(audit_middleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
