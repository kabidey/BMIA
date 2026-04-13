"""
Daemon: Auto-evaluates all open signals every 60 seconds.
"""
import logging
import time
import threading
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from services.signal_service import evaluate_all_signals
from services.learning_service import build_learning_context

logger = logging.getLogger(__name__)


def start_evaluation_scheduler(mongo_url: str, db_name: str):
    """Daemon thread: auto-evaluates all open signals every 60 seconds."""

    def _run():
        logger.info("EVAL SCHEDULER: Started (every 60s)")
        time.sleep(30)
        while True:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                client = AsyncIOMotorClient(mongo_url)
                db = client[db_name]

                async def _eval():
                    results = await evaluate_all_signals(db)
                    evaluated = len(results)
                    if evaluated > 0:
                        logger.info(f"EVAL SCHEDULER: Evaluated {evaluated} signals")
                        try:
                            await build_learning_context(db)
                        except Exception:
                            pass
                    return evaluated

                loop.run_until_complete(_eval())
                client.close()
                loop.close()
            except Exception as e:
                logger.error(f"EVAL SCHEDULER error: {e}")
            time.sleep(60)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
