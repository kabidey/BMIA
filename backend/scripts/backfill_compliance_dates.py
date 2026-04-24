"""One-time migration: re-parse date_str on compliance_circulars rows where
year is null / date_iso is empty. Runs idempotently — safe to re-run.

Root cause: BSE RSS feed returns RFC822 dates ("Thu, 23 Apr 2026 17:47:39 GMT").
The old `_parse_date()` didn't handle RFC822, so `year` and `date_iso` were left
blank for every ingested BSE row. This breaks stats/progress calculations.
"""
import os, sys
sys.path.insert(0, "/app/backend")
from pymongo import MongoClient
from daemons.compliance_ingestion import _parse_date

def main():
    mongo_url = os.environ["MONGO_URL"]
    db_name = os.environ["DB_NAME"]
    client = MongoClient(mongo_url)
    db = client[db_name]

    fixed = 0
    scanned = 0
    cursor = db.compliance_circulars.find(
        {"$or": [{"year": None}, {"year": {"$exists": False}}, {"date_iso": ""}]},
        {"_id": 1, "source": 1, "circular_no": 1, "date_str": 1, "url": 1}
    )
    for doc in cursor:
        scanned += 1
        date_str = doc.get("date_str") or ""
        # Fallback: derive from BSE URL filename like "20260418-2.pdf"
        if not date_str and doc.get("url"):
            import re
            m = re.search(r"/(\d{8})-\d+", doc["url"])
            if m:
                date_str = m.group(1)  # YYYYMMDD
        dt = _parse_date(date_str)
        if not dt:
            continue
        patch = {"date_iso": dt.date().isoformat(), "year": dt.year}
        db.compliance_circulars.update_one({"_id": doc["_id"]}, {"$set": patch})
        # Cascade to chunks (so aggregations there also work)
        db.compliance_chunks.update_many(
            {"source": doc["source"], "circular_no": doc["circular_no"]},
            {"$set": patch},
        )
        fixed += 1

    # Also refresh per-source ingestion_state cursors
    for src in ("nse", "bse", "sebi"):
        newest = db.compliance_circulars.find(
            {"source": src, "date_iso": {"$ne": ""}},
            {"date_iso": 1, "_id": 0}
        ).sort("date_iso", -1).limit(1)
        oldest = db.compliance_circulars.find(
            {"source": src, "date_iso": {"$ne": ""}},
            {"date_iso": 1, "_id": 0}
        ).sort("date_iso", 1).limit(1)
        nl = list(newest); ol = list(oldest)
        patch = {}
        if nl: patch["newest_date_iso"] = nl[0]["date_iso"]
        if ol: patch["oldest_date_iso"] = ol[0]["date_iso"]
        if patch:
            db.compliance_ingestion_state.update_one({"source": src}, {"$set": patch}, upsert=True)
            print(f"  state[{src}] ← {patch}")

    print(f"\nScanned: {scanned}  Fixed: {fixed}")
    client.close()

if __name__ == "__main__":
    main()
