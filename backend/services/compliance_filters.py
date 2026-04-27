"""Central definition of which compliance_circulars categories represent
material ISSUED BY the regulator/exchange (i.e. real circulars), as opposed
to filings RECEIVED BY them from listed companies.

The compliance-research user asked only for the former. By default every
retrieval, graph-build and stats query goes through `is_regulatory()` so
company filings (BSE Announcements, AGM/EGM, Corp Action, etc.) never appear
as compliance citations.

We do not delete the company-filing rows — they may be useful for other
features later (e.g. Big Market terminal, company-specific intel) — we just
exclude them from the compliance corpus surface.
"""
from __future__ import annotations

# Categories that ARE genuine regulator-/exchange-issued material.
# Anything not in this set is treated as a company filing / noise and excluded
# from compliance retrieval.
_REGULATORY_CATEGORIES: dict[str, set[str]] = {
    # NSE: every NSE circular is published by NSE itself, so all categories qualify.
    "nse": {
        "Compliance", "Listing", "Trading", "Clearing", "Others",
        "Trading, Clearing & settlement",
        "Member Circular", "Department",
    },
    # BSE: only Notices and Master Circulars are issued by BSE.
    # Company Update / Insider Trading-SAST / AGM-EGM / Corp Action are filings
    # BY companies, hosted on BSE — explicitly excluded.
    "bse": {
        "Notice", "Notices", "Master Circular", "Master Circulars",
        "Listing Obligations", "Circulars", "Circular",
    },
    # SEBI: classic compliance corpus.
    "sebi": {
        "Circulars", "Circular", "Master Circulars", "Master Circular",
        "Regulations", "Rules", "Acts",
        "General Orders", "Guidelines", "Guidance Notes",
        "Gazette Notification", "Advisory/Guidance",
        "General",  # SEBI "General" section often holds policy circulars
    },
}


def is_regulatory(source: str | None, category: str | None) -> bool:
    """True iff this circular was issued BY the regulator/exchange.

    Bulk-uploaded PDFs (category="bulk_upload_*") are ALSO treated as
    regulatory because they're hand-picked by the compliance team."""
    if not source:
        return False
    src = source.lower()
    cat = (category or "").strip()
    if cat.startswith("bulk_upload"):
        return True
    return cat in _REGULATORY_CATEGORIES.get(src, set())


def regulatory_categories(source: str | None) -> list[str]:
    """Public view of the allowed-list for a source — used by the Mongo
    `$in` filter in retrieval and graph code."""
    if not source:
        return []
    return sorted(_REGULATORY_CATEGORIES.get(source.lower(), set()))


def mongo_regulatory_filter(source: str | None = None) -> dict:
    """Return a Mongo filter clause that restricts to regulator-issued
    circulars. Pass `source` to scope to one regulator, or None for all."""
    if source:
        cats = regulatory_categories(source) + []
        # Allow bulk_upload_<source> too
        return {
            "source": source.lower(),
            "$or": [
                {"category": {"$in": cats}},
                {"category": {"$regex": "^bulk_upload"}},
            ],
        }
    # All sources — union per-source allowed lists with bulk_upload escape hatch
    or_clauses = []
    for src, cats in _REGULATORY_CATEGORIES.items():
        or_clauses.append({"source": src, "category": {"$in": sorted(cats)}})
    or_clauses.append({"category": {"$regex": "^bulk_upload"}})
    return {"$or": or_clauses}
