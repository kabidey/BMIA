"""
Bharat Market Intel Agent (BMIA) - FastAPI Backend
Slim entry point — routes and daemons are modularized.
"""
import os
import logging
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient

from utils.safe_json import SafeJSONResponse

# Route imports (needed at app-construction time to register endpoints)
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
from routes.fund_management import router as fund_management_router

# Heavy daemon / service imports are deferred to lifespan so the Python module
# import graph during cold-start is lighter (helps deploy-probe succeed faster).

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    force=True,
    handlers=[logging.StreamHandler()],  # ensure stdout stream is used (deploy logs capture stdout)
)
logger = logging.getLogger(__name__)
logger.info("BMIA server.py imported — bootstrapping FastAPI")

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME")

if not MONGO_URL or not DB_NAME:
    # Fail fast with a CLEAR message instead of a cryptic KeyError deep inside
    # FastAPI's lifespan. This also ensures the process writes *something* to
    # stdout before exiting, which helps deploy log triage.
    import sys
    sys.stderr.write(
        f"[BMIA FATAL] Missing env vars — MONGO_URL={'set' if MONGO_URL else 'MISSING'} "
        f"DB_NAME={'set' if DB_NAME else 'MISSING'}. Backend cannot start.\n"
    )
    sys.stderr.flush()
    raise SystemExit(1)


# ─── Auto-migration (idempotent, runs once per deploy) ──────────────────────
# When the scraper was first wired, the daemon workers had already persisted
# rows with year=None (old parser) and the SEBI worker had flipped to `live`
# phase with only ~25 items of the 3,039-item corpus ingested. This helper
# self-heals that state so every deploy starts from a known-good place,
# without the operator having to remember to run curls.
#
# The `compliance_migrations` collection acts as a fingerprint ledger — each
# migration runs at most once. New migrations are added by appending a new
# `name` + code branch.
async def _run_auto_migrations():
    """One-shot repairs that should happen after a deploy picks up new code
    or env. Idempotent: re-runs do nothing once the marker row exists."""
    import pymongo
    import re as _re
    try:
        client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        sync_db = client[DB_NAME]
        done = {d["name"] for d in sync_db.compliance_migrations.find({}, {"_id": 0, "name": 1})}

        if "2026-04-scraper-v1" not in done:
            logger.info("AUTO-MIGRATION: 2026-04-scraper-v1 running")
            from daemons.compliance_ingestion import _parse_date
            fixed = 0
            for doc in sync_db.compliance_circulars.find(
                {"$or": [{"year": None}, {"year": {"$exists": False}}, {"date_iso": ""}]},
                {"_id": 1, "source": 1, "circular_no": 1, "date_str": 1, "url": 1},
            ):
                date_str = doc.get("date_str") or ""
                if not date_str and doc.get("url"):
                    m = _re.search(r"/(\d{8})-\d+", doc["url"])
                    if m:
                        date_str = m.group(1)
                dt = _parse_date(date_str)
                if not dt:
                    continue
                patch = {"date_iso": dt.date().isoformat(), "year": dt.year}
                sync_db.compliance_circulars.update_one({"_id": doc["_id"]}, {"$set": patch})
                sync_db.compliance_chunks.update_many(
                    {"source": doc["source"], "circular_no": doc["circular_no"]},
                    {"$set": patch},
                )
                fixed += 1
            for src in ("nse", "bse", "sebi"):
                newest = list(sync_db.compliance_circulars.find(
                    {"source": src, "date_iso": {"$ne": ""}}, {"date_iso": 1, "_id": 0},
                ).sort("date_iso", -1).limit(1))
                oldest = list(sync_db.compliance_circulars.find(
                    {"source": src, "date_iso": {"$ne": ""}}, {"date_iso": 1, "_id": 0},
                ).sort("date_iso", 1).limit(1))
                patch = {}
                if newest:
                    patch["newest_date_iso"] = newest[0]["date_iso"]
                if oldest:
                    patch["oldest_date_iso"] = oldest[0]["date_iso"]
                if patch:
                    sync_db.compliance_ingestion_state.update_one(
                        {"source": src}, {"$set": patch}, upsert=True,
                    )
            today_iso = datetime.utcnow().date().isoformat()
            sync_db.compliance_ingestion_state.update_one(
                {"source": "sebi"},
                {"$set": {
                    "phase": "backfill",
                    "oldest_date_iso": today_iso,
                    "target_start_year": 1995,
                    "consecutive_no_data": 0,
                    "last_error": None,
                }},
                upsert=True,
            )
            sync_db.compliance_ingestion_state.update_one(
                {"source": "bse"},
                {"$set": {
                    "phase": "backfill",
                    "target_start_year": 2010,
                    "consecutive_no_data": 0,
                    "last_error": None,
                }},
                upsert=True,
            )
            sync_db.compliance_migrations.insert_one({
                "name": "2026-04-scraper-v1",
                "ran_at": datetime.utcnow().isoformat(),
                "fixed_rows": fixed,
            })
            logger.info(
                f"AUTO-MIGRATION: 2026-04-scraper-v1 complete "
                f"(fixed {fixed} rows, reset sebi+bse workers)"
            )

        # ── 2026-04-regulatory-purge ─────────────────────────────────
        # Removes company-filing pollution from the corpus so compliance
        # research only surfaces material ISSUED BY NSE/BSE/SEBI, never
        # filings RECEIVED FROM listed companies. Also rebuilds the
        # TF-IDF stores so the cleaned corpus is searchable immediately.
        if "2026-04-regulatory-purge" not in done:
            logger.info("AUTO-MIGRATION: 2026-04-regulatory-purge running")
            bse_noise_cats = [
                "Company Update", "Insider Trading / SAST",
                "AGM/EGM", "Corp. Action", "Corp Action",
            ]
            # Snapshot the (source, circular_no) pairs we're about to delete
            # so we can also remove their chunks.
            bse_targets = list(sync_db.compliance_circulars.find(
                {"source": "bse", "category": {"$in": bse_noise_cats}},
                {"_id": 0, "circular_no": 1},
            ))
            sebi_targets = list(sync_db.compliance_circulars.find(
                {"source": "sebi", "category": {"$regex": r"^intmid="}},
                {"_id": 0, "circular_no": 1},
            ))

            r1 = sync_db.compliance_circulars.delete_many(
                {"source": "bse", "category": {"$in": bse_noise_cats}},
            )
            r2 = sync_db.compliance_circulars.delete_many(
                {"source": "sebi", "category": {"$regex": r"^intmid="}},
            )
            chunk_del = 0
            if bse_targets:
                cnos = [t["circular_no"] for t in bse_targets]
                rc = sync_db.compliance_chunks.delete_many(
                    {"source": "bse", "circular_no": {"$in": cnos}},
                )
                chunk_del += rc.deleted_count
            if sebi_targets:
                cnos = [t["circular_no"] for t in sebi_targets]
                rc = sync_db.compliance_chunks.delete_many(
                    {"source": "sebi", "circular_no": {"$in": cnos}},
                )
                chunk_del += rc.deleted_count

            sync_db.compliance_migrations.insert_one({
                "name": "2026-04-regulatory-purge",
                "ran_at": datetime.utcnow().isoformat(),
                "deleted_bse": r1.deleted_count,
                "deleted_sebi": r2.deleted_count,
                "deleted_chunks": chunk_del,
            })
            logger.info(
                "AUTO-MIGRATION: 2026-04-regulatory-purge complete "
                f"(bse={r1.deleted_count} sebi={r2.deleted_count} chunks={chunk_del}). "
                "Schedule a TF-IDF rebuild — handled by the deferred init."
            )

        # ── 2026-05-portfolio-cash-reconcile ─────────────────────────
        # `auto_reinvest.reinvest_proceeds` historically double-booked the
        # exit proceeds: `_enforce_stops` had already credited them to
        # `cash_balance`, and the reinvest path added them again before
        # deducting the deployed amount. Every successful stop-out + auto-
        # reinvest pair therefore inflated `cash_balance`, `current_value`
        # and `total_pnl` by exactly the exit proceeds. Code is fixed; this
        # migration cleans up the historical inflation in production using
        # the invariant
        #     expected_cash = initial_capital + realized_pnl
        #                       − Σ(entry_price × qty for h in holdings)
        # (no external deposits/withdrawals on autonomous strategy
        # portfolios). Only acts when stored_cash − expected_cash > ₹1
        # so under-counted portfolios (a different, older issue) are not
        # touched here.
        if "2026-05-portfolio-cash-reconcile" not in done:
            logger.info("AUTO-MIGRATION: 2026-05-portfolio-cash-reconcile running")
            ran_at = datetime.utcnow().isoformat()
            fixes = []
            for p in sync_db.portfolios.find({"status": "active"}):
                ptype = p["type"]
                stored_cash = float(p.get("cash_balance", 0) or 0)
                initial_capital = float(p.get("initial_capital", 0) or 0)
                realized_pnl = float(p.get("realized_pnl", 0) or 0)
                holdings = p.get("holdings", []) or []
                cost_basis = sum(
                    float(h.get("entry_price", 0) or 0) * (h.get("quantity", 0) or 0)
                    for h in holdings
                )
                expected_cash = initial_capital + realized_pnl - cost_basis
                delta = stored_cash - expected_cash  # >0 ⇒ inflated by old bug

                if delta <= 1.0:
                    logger.info(
                        f"AUTO-MIGRATION: portfolio-cash-reconcile [{ptype}] "
                        f"cash={stored_cash:,.2f} expected={expected_cash:,.2f} "
                        f"delta={delta:+,.2f} — skipped"
                    )
                    continue

                holdings_value = sum(
                    float(h.get("current_price", h.get("entry_price", 0)) or 0)
                    * (h.get("quantity", 0) or 0)
                    for h in holdings
                )
                fixed_cash = max(expected_cash, 0.0)
                fixed_value = holdings_value + fixed_cash
                unrealized_pnl = holdings_value - cost_basis
                total_pnl = fixed_value - initial_capital
                total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0

                sync_db.portfolios.update_one(
                    {"type": ptype},
                    {"$set": {
                        "cash_balance": round(fixed_cash, 2),
                        "current_value": round(fixed_value, 2),
                        "holdings_value": round(holdings_value, 2),
                        "unrealized_pnl": round(unrealized_pnl, 2),
                        "total_pnl": round(total_pnl, 2),
                        "total_pnl_pct": round(total_pnl_pct, 2),
                        "reconciled_at": ran_at,
                        "reconcile_note": (
                            f"Removed ₹{delta:,.2f} of double-booked reinvestment "
                            "proceeds (auto_reinvest pre-fix bug)."
                        ),
                    }}
                )
                sync_db.portfolio_rebalance_log.insert_one({
                    "portfolio_type": ptype,
                    "action": "RECONCILE_INFLATED_REINVEST",
                    "timestamp": ran_at,
                    "delta_removed": round(delta, 2),
                    "old_cash": round(stored_cash, 2),
                    "new_cash": round(fixed_cash, 2),
                    "old_current_value": round(holdings_value + stored_cash, 2),
                    "new_current_value": round(fixed_value, 2),
                    "note": "Auto-migration 2026-05-portfolio-cash-reconcile",
                })
                fixes.append({
                    "type": ptype,
                    "delta_removed": round(delta, 2),
                    "old_cash": round(stored_cash, 2),
                    "new_cash": round(fixed_cash, 2),
                })
                logger.info(
                    f"AUTO-MIGRATION: portfolio-cash-reconcile [{ptype}] "
                    f"cash {stored_cash:,.2f} → {fixed_cash:,.2f} "
                    f"(removed ₹{delta:,.2f} inflation)"
                )

            sync_db.compliance_migrations.insert_one({
                "name": "2026-05-portfolio-cash-reconcile",
                "ran_at": ran_at,
                "portfolios_fixed": len(fixes),
                "total_inflation_removed": round(sum(f["delta_removed"] for f in fixes), 2),
                "fixes": fixes,
            })
            logger.info(
                f"AUTO-MIGRATION: 2026-05-portfolio-cash-reconcile complete "
                f"({len(fixes)} portfolios fixed, "
                f"₹{sum(f['delta_removed'] for f in fixes):,.0f} total inflation removed)"
            )
        client.close()
    except Exception as e:
        logger.error(f"AUTO-MIGRATION failed (non-fatal): {e}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Use `serverSelectionTimeoutMS=5000` so we don't hang forever on a dead
    # Mongo Atlas endpoint during startup — fail fast with a clear error instead.
    app.mongodb_client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
    app.db = app.mongodb_client[DB_NAME]
    logger.info("Connected to MongoDB (lazy — first query triggers actual connection)")

    # ─── STARTUP POLICY ───────────────────────────────────────────────────
    # On deploy pods, the probe times out at 120s. The lifespan hot-path must
    # therefore be as tiny as possible. We:
    #   • spawn all background daemons (threads — return instantly)
    #   • DEFER every heavy build (vector store, compliance RAG, ingestion
    #     workers) well past the probe window
    #
    # If things still fail, set BMIA_MINIMAL_STARTUP=1 in the deploy env —
    # this skips ALL background daemons and heavy work entirely, so the
    # process is a bare FastAPI server with DB access only. Once the probe
    # passes, remove the flag for full functionality.
    import asyncio
    import os as _os

    minimal = _os.environ.get("BMIA_MINIMAL_STARTUP", "").strip().lower() in ("1", "true", "yes")

    if minimal:
        logger.warning("BMIA_MINIMAL_STARTUP=1 → skipping ALL background daemons & deferred builds")
    else:
        # Lazy-import the heavy daemon/service modules (sklearn, pdfminer,
        # pandas chains) only when we actually need to start them. This keeps
        # the server.py import graph lean so cold-disk pod starts are fast.
        from services.dashboard_service import start_background_cache
        from services.guidance_service import start_guidance_scheduler
        from services.pdf_extractor_service import start_pdf_extraction_daemon
        from services.vector_store import guidance_vector_store
        from services.compliance_rag import compliance_router
        from daemons.evaluation_scheduler import start_evaluation_scheduler
        from daemons.portfolio_daemon import start_portfolio_daemon
        from daemons.compliance_ingestion import start_compliance_daemon
        from daemons.fund_management_daemon import start_fund_management_daemon

        # Light-weight daemons — safe to start immediately
        for name, starter, args in [
            ("Background cache", start_background_cache, ()),
            ("Evaluation scheduler", start_evaluation_scheduler, (MONGO_URL, DB_NAME)),
            ("Guidance scheduler", start_guidance_scheduler, (MONGO_URL, DB_NAME)),
            ("PDF extraction daemon", start_pdf_extraction_daemon, (MONGO_URL, DB_NAME)),
            ("Portfolio daemon", start_portfolio_daemon, (MONGO_URL, DB_NAME)),
            ("Fund management daemon", start_fund_management_daemon, (MONGO_URL, DB_NAME)),
        ]:
            try:
                starter(*args)
            except Exception as e:
                logger.error(f"{name} start failed (non-fatal): {e}")

        # Heavy background work — deferred FAR past probe window so the pod
        # settles into a stable memory/CPU state before heavy work kicks in.
        # If Kubernetes still kills the pod on liveness failure or OOM during
        # these, set BMIA_MINIMAL_STARTUP=1 to disable them entirely.
        async def _deferred_vector_store_build():
            try:
                await asyncio.sleep(300)  # 5 min — well past probe + settle time
                logger.info("Starting deferred guidance vector store build")
                await guidance_vector_store.build(app.db)
            except Exception as e:
                logger.error(f"Vector store initial build failed (non-fatal): {e}")

        async def _deferred_compliance_init():
            try:
                # 1) Start daemon workers quickly so UI shows backfill activity within a minute.
                #    Threads spawn instantly; per-cycle work is tiny.
                await asyncio.sleep(60)
                logger.info("Starting compliance ingestion daemon (backfill workers)")
                start_compliance_daemon(MONGO_URL, DB_NAME)

                # 1.5) AUTO-MIGRATION: run once after each deploy to fix the DB
                # state that older ingests left behind and to re-point SEBI's
                # backfill cursor at the full 3,039-item corpus. Idempotent
                # via `compliance_migrations` marker collection.
                await _run_auto_migrations()

                # 1.6) Recover any fund_runs that were left in `running`
                # status when the previous backend died (asyncio.create_task
                # is killed on restart so the pipeline never wrote a final
                # state). Marks rows as `orphaned` so the UI shows the truth.
                try:
                    from routes.fund_management import recover_orphaned_runs
                    await recover_orphaned_runs(app.db)
                except Exception as e:
                    logger.warning(f"FUND orphan recovery failed (non-fatal): {e}")

                # 2) Defer the heavy TF-IDF vector build further — this loads all
                #    persisted chunks and fits the vectorizer. If the DB is empty
                #    it's a no-op; if large, it can take several seconds.
                await asyncio.sleep(240)  # additional 4 min → total 5 min post-boot
                logger.info("Starting deferred compliance RAG vector build")
                await compliance_router.build_all(app.db)

                # 3) Start the background graph-entity extraction daemon. This
                #    pre-computes LLM entity/relation extractions for every
                #    circular so the "View 3D Graph" button opens instantly
                #    without on-demand LLM latency. Kicks off only AFTER the
                #    RAG store is warm, so it doesn't compete for CPU during
                #    the critical post-boot interval.
                from daemons.graph_extraction import start_graph_extraction_daemon
                start_graph_extraction_daemon(MONGO_URL, DB_NAME)

                # 4) Start the re-chunking daemon. Walks every circular with
                #    too-many chunks (legacy CHUNK_SIZE=800 ingests) and
                #    consolidates them into the new larger 1600-char chunks.
                #    Idempotent — skips already-rechunked or small circulars.
                from daemons.rechunk import start_rechunk_daemon
                start_rechunk_daemon(MONGO_URL, DB_NAME)

                # 5) Warm up the sentence-transformer embedding model in the
                #    background so the first compliance query doesn't pay the
                #    3s model-load cost. Runs in a worker thread; no-op if the
                #    package isn't installed.
                from services.compliance_embed import warmup_async
                asyncio.ensure_future(warmup_async())
            except Exception as e:
                logger.error(f"Compliance init failed (non-fatal): {e}")

        asyncio.ensure_future(_deferred_vector_store_build())
        asyncio.ensure_future(_deferred_compliance_init())

    # LOUD ready marker — flushed to stdout so any log-scraping deploy probe
    # can pattern-match on it. Printed immediately before FastAPI marks the
    # app as ready to serve requests.
    import sys as _sys
    print("READY: BMIA backend listening on 0.0.0.0:8001", flush=True)
    _sys.stdout.flush()
    logger.info("READY: BMIA backend listening on 0.0.0.0:8001")

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


from fastapi.responses import PlainTextResponse


@app.get("/api/health")
@app.get("/health")
@app.get("/healthz")
@app.get("/readyz")
@app.get("/livez")
async def health():
    return {"status": "ok", "service": "BMIA", "timestamp": datetime.now().isoformat()}


# Plain-text health aliases — some deploy probes expect `text/plain` "OK"
@app.get("/ping", response_class=PlainTextResponse)
@app.get("/status", response_class=PlainTextResponse)
async def ping():
    return "OK"


# Root — many deploy platforms probe "/" expecting a 200 response to mark the
# container as healthy. Return a tiny payload so probes pass immediately.
@app.get("/")
async def root():
    return {"service": "BMIA", "status": "ok"}


# ── Deep health probe for post-deploy monitoring ─────────────────────────
# Unlike /api/health (which always 200s so K8s doesn't kill boot), this
# endpoint actually pings each subsystem and returns 503 if anything is
# degraded. Wire this into Emergent's health-check URL once backfill is
# past the first 5 min so failures auto-restart the pod.
@app.get("/api/deploy-health")
async def deploy_health():
    from fastapi.responses import JSONResponse
    from datetime import timezone as _tz

    result: dict = {"service": "BMIA", "checked_at": datetime.now(_tz.utc).isoformat()}
    critical_failures: list = []

    # 1. Mongo reachability
    try:
        await app.db.command("ping")
        result["mongo"] = "ok"
    except Exception as e:
        result["mongo"] = f"error: {str(e)[:80]}"
        critical_failures.append("mongo")

    # 2. Emergent LLM key present (non-empty env var)
    llm_key = os.environ.get("EMERGENT_LLM_KEY", "").strip()
    result["llm_key"] = "ok" if llm_key else "missing"
    if not llm_key:
        critical_failures.append("llm_key")

    # 3. Compliance worker phases + freshness
    try:
        workers: dict = {}
        latest_ingest_at: Optional[datetime] = None
        async for state in app.db.compliance_ingestion_state.find({}, {"_id": 0}):
            src = state.get("source")
            if not src:
                continue
            workers[src] = state.get("phase", "unknown")
            ts = state.get("last_new_ingest_at")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")) if isinstance(ts, str) else ts
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=_tz.utc)
                    if latest_ingest_at is None or dt > latest_ingest_at:
                        latest_ingest_at = dt
                except Exception:
                    pass
        result["compliance_workers"] = workers or "not_started"

        if latest_ingest_at:
            delta = datetime.now(_tz.utc) - latest_ingest_at
            mins = int(delta.total_seconds() // 60)
            if mins < 60:
                result["last_new_ingest"] = f"{mins} min ago"
            elif mins < 1440:
                result["last_new_ingest"] = f"{mins // 60} h ago"
            else:
                result["last_new_ingest"] = f"{mins // 1440} d ago"
            result["last_new_ingest_at"] = latest_ingest_at.isoformat()
        else:
            result["last_new_ingest"] = "never"
    except Exception as e:
        result["compliance_workers"] = f"error: {str(e)[:80]}"

    # 4. Vector stores ready flags (non-critical — report but don't fail)
    try:
        from routes import compliance as compliance_router
        stores = {}
        for src in ("nse", "bse", "sebi"):
            store = compliance_router._STORES.get(src) if hasattr(compliance_router, "_STORES") else None
            stores[src] = bool(store and getattr(store, "ready", False))
        result["vector_stores_ready"] = stores
    except Exception:
        pass

    result["status"] = "degraded" if critical_failures else "ok"
    result["failing"] = critical_failures or None
    status_code = 503 if critical_failures else 200
    return JSONResponse(status_code=status_code, content=result)


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
app.include_router(fund_management_router)

app.middleware("http")(audit_middleware)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
