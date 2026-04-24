"""Compliance GraphRAG — builds a knowledge graph over the ingested
NSE/BSE/SEBI circular corpus and serves subgraphs to the frontend 3D viewer.

Two-layer design:

  Layer 1 — Structural graph (cheap, always on):
    Nodes = compliance_circulars
    Edges =
      * same-source cluster (within a window)
      * same-category
      * shared regulation/keyword (e.g., "LODR Reg 30", "SAST", "Insider Trading")
      * TF-IDF cosine similarity > threshold between titles/texts

  Layer 2 — LLM-extracted entity graph (on demand, higher fidelity):
    Claude Sonnet 4.5 extracts entities (COMPANY, REGULATION, CONCEPT, DATE)
    and relationships (AMENDS, REFERENCES, APPLIES_TO, SUPERSEDES) from the
    top-K retrieved circulars when the user runs a RAG query. Cached so we
    never re-extract the same circular.

Query-time flow (GraphRAG):
  1. TF-IDF retrieval → top-K chunks
  2. Gather the circulars those chunks belong to
  3. Pull neighbors via the structural graph (+1 hop)
  4. Optionally enrich with LLM entities for the final subgraph
  5. Return {answer, citations, subgraph} — the frontend renders #3.
"""
import logging
import os
import re
import json
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Optional, Set, Tuple

import numpy as np
from pymongo.database import Database

logger = logging.getLogger(__name__)

# ─── Entity keyword dictionary (fast, deterministic Layer-1 extraction) ──
REGULATION_KEYWORDS = {
    "LODR": ["lodr", "listing obligations and disclosure", "regulation 30"],
    "SAST": ["sast", "substantial acquisition", "takeover regulations"],
    "InsiderTrading": ["insider trading", "pit regulations", "pit, 2015"],
    "ICDR": ["icdr", "issue of capital and disclosure"],
    "AIF": ["alternative investment fund", "aif regulations"],
    "MutualFund": ["mutual fund", "mf regulations"],
    "PFI": ["portfolio manager", "pms regulations"],
    "REIT": ["reit", "real estate investment trust"],
    "InvIT": ["invit", "infrastructure investment trust"],
    "FPI": ["foreign portfolio investor", "fpi regulations"],
    "DP": ["depository participant", "depositories act"],
    "StockBroker": ["stock broker", "broker regulations"],
    "CA": ["credit rating", "cra regulations"],
    "FPIAML": ["anti money laundering", "aml", "pmla"],
    "IPR": ["investor protection", "ipef"],
    "ESG": ["esg", "business responsibility", "brsr", "sustainability"],
    "Algo": ["algo trading", "algorithmic trading"],
    "T+0": ["t+0", "t plus 0", "shortened settlement"],
    "MaintenanceMargin": ["margin", "maintenance margin", "upfront margin"],
}

CATEGORY_GROUPS = {
    "Circulars": "primary",
    "Master Circulars": "primary",
    "Regulations": "statutory",
    "Rules": "statutory",
    "Acts": "statutory",
    "General Orders": "enforcement",
    "Guidelines": "guidance",
    "Guidance Notes": "guidance",
    "Gazette Notification": "statutory",
    "Advisory/Guidance": "guidance",
    "Company Update": "disclosure",
    "Insider Trading / SAST": "disclosure",
    "Notice": "primary",
    "Corp. Action": "disclosure",
    "Corp Action": "disclosure",
    "AGM/EGM": "disclosure",
}


def _extract_regulation_tags(text: str) -> Set[str]:
    """Match regulation keywords in circular text — deterministic, fast."""
    t = text.lower()
    return {tag for tag, kws in REGULATION_KEYWORDS.items() if any(kw in t for kw in kws)}


def build_structural_graph(db: Database, source_filter: Optional[List[str]] = None,
                           max_nodes: int = 5000) -> Dict:
    """Build a structural graph over the circular corpus. Stored in-memory,
    re-built on demand (few seconds for 5k nodes)."""
    query = {}
    if source_filter:
        query["source"] = {"$in": source_filter}

    circulars = list(db.compliance_circulars.find(
        query,
        {"_id": 0, "source": 1, "circular_no": 1, "title": 1, "category": 1,
         "year": 1, "date_iso": 1, "url": 1},
    ).limit(max_nodes))

    nodes: List[Dict] = []
    by_tag: Dict[str, List[str]] = defaultdict(list)
    by_source_year: Dict[Tuple[str, int], List[str]] = defaultdict(list)

    for c in circulars:
        nid = f"{c['source']}:{c.get('circular_no', '')}"[:200]
        title = c.get("title", "")[:240]
        tags = _extract_regulation_tags(title)
        node = {
            "id": nid,
            "label": title or nid,
            "source": c.get("source"),
            "category": c.get("category") or "General",
            "category_group": CATEGORY_GROUPS.get(c.get("category") or "", "other"),
            "year": c.get("year"),
            "date": c.get("date_iso"),
            "url": c.get("url", ""),
            "tags": list(tags),
            "val": 2 + len(tags) * 2,  # node size in 3D viz
        }
        nodes.append(node)
        for tag in tags:
            by_tag[tag].append(nid)
        if c.get("year"):
            by_source_year[(c["source"], c["year"])].append(nid)

    edges: List[Dict] = []
    edge_set: Set[Tuple[str, str, str]] = set()

    # Edges via shared regulation tag (e.g., two LODR circulars)
    for tag, ids in by_tag.items():
        if len(ids) < 2 or len(ids) > 200:  # skip giant buckets (noise)
            continue
        for i in range(len(ids)):
            for j in range(i + 1, min(i + 20, len(ids))):
                a, b = ids[i], ids[j]
                key = (a, b, tag) if a < b else (b, a, tag)
                if key in edge_set:
                    continue
                edge_set.add(key)
                edges.append({"source": a, "target": b, "relation": tag, "type": "regulation"})

    # Edges via same source-year cluster (chronological context)
    for (src, yr), ids in by_source_year.items():
        if len(ids) < 2 or len(ids) > 150:
            continue
        # Link consecutive circulars in chrono order so timeline is implied
        for i in range(0, len(ids) - 1, 2):
            a, b = ids[i], ids[i + 1]
            key = (a, b, f"{src}-{yr}") if a < b else (b, a, f"{src}-{yr}")
            if key in edge_set:
                continue
            edge_set.add(key)
            edges.append({"source": a, "target": b, "relation": f"{yr}", "type": "temporal"})

    logger.info(f"Structural graph: {len(nodes)} nodes, {len(edges)} edges (sources={source_filter})")
    return {"nodes": nodes, "edges": edges, "built_at": datetime.utcnow().isoformat()}


def build_subgraph(db: Database, circular_ids: List[str], hop: int = 1) -> Dict:
    """Given a seed list of `source:circular_no` ids, expand to include
    neighbors via shared regulation tags + same source-year clusters.

    Returns a compact subgraph suitable for 3D rendering."""
    if not circular_ids:
        return {"nodes": [], "edges": []}

    full = build_structural_graph(db, max_nodes=8000)
    node_idx = {n["id"]: n for n in full["nodes"]}
    seed_set = set(circular_ids)

    # Expand via adjacency
    neighbor_set: Set[str] = set(seed_set)
    if hop >= 1:
        adj: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for e in full["edges"]:
            adj[e["source"]].append((e["target"], e["relation"]))
            adj[e["target"]].append((e["source"], e["relation"]))
        for nid in list(seed_set):
            for neighbor, _ in adj.get(nid, [])[:8]:  # cap per seed
                neighbor_set.add(neighbor)

    # Build output
    nodes = [
        {**node_idx[nid], "seed": nid in seed_set}
        for nid in neighbor_set if nid in node_idx
    ]
    keep_ids = {n["id"] for n in nodes}
    edges = [
        e for e in full["edges"]
        if e["source"] in keep_ids and e["target"] in keep_ids
    ]
    return {"nodes": nodes, "edges": edges}


# ─── Layer 2: LLM entity extraction (on-demand, cached) ─────────────────

ENTITY_SYSTEM = """You are a Tier-1 compliance legal analyst at SMIFS. Extract structured entities and relationships from Indian capital-markets circulars.

Return ONLY valid JSON of the shape:
{
  "entities": [
    {"name": "<canonical name>", "type": "REGULATION|CIRCULAR|COMPANY|PERSON|CONCEPT|DATE|EVENT", "aliases": ["..."]}
  ],
  "relations": [
    {"src": "<entity>", "dst": "<entity>", "type": "AMENDS|REFERENCES|APPLIES_TO|SUPERSEDES|ISSUED_BY|REQUIRES"}
  ]
}

Rules:
- Use canonical names (e.g., "SEBI LODR Regulations, 2015", not abbreviations unless widely used like "SAST").
- Include only entities that matter for compliance research.
- Max 10 entities, 15 relations. Be precise; noise pollutes the graph.
"""


async def extract_entities_llm(text: str, circ_no: str, api_key: str) -> Dict:
    """Extract entities from a circular using Claude. Cached by caller."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    chat = LlmChat(
        api_key=api_key,
        session_id=f"graph-extract-{circ_no}",
        system_message=ENTITY_SYSTEM,
    ).with_model("anthropic", "claude-sonnet-4-5-20250929")
    user = UserMessage(text=text[:8000])  # cap input tokens
    try:
        response = await chat.send_message(user)
        # Strip any markdown code fences
        raw = response.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
        data = json.loads(raw)
        return {"entities": data.get("entities", [])[:10],
                "relations": data.get("relations", [])[:15]}
    except Exception as e:
        logger.warning(f"LLM extract failed for {circ_no}: {e}")
        return {"entities": [], "relations": []}


async def enrich_subgraph_with_llm(db: Database, subgraph: Dict, max_enrich: int = 8) -> Dict:
    """Take a structural subgraph and layer in LLM-extracted entities for the
    seed nodes. Cached per circular in compliance_graph_entities so we never
    re-extract."""
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        return subgraph  # no enrichment available

    seeds = [n for n in subgraph["nodes"] if n.get("seed")][:max_enrich]
    added_entities: Dict[str, Dict] = {}
    added_relations: List[Dict] = []

    for node in seeds:
        circ_no = node["id"].split(":", 1)[1] if ":" in node["id"] else node["id"]
        # Check cache
        cached = db.compliance_graph_entities.find_one(
            {"circular_id": node["id"]}, {"_id": 0, "entities": 1, "relations": 1},
        )
        if cached:
            ents = cached.get("entities", [])
            rels = cached.get("relations", [])
        else:
            # Pull the circular's full text chunks
            chunks = list(db.compliance_chunks.find(
                {"source": node["source"], "circular_no": circ_no},
                {"_id": 0, "text": 1},
            ).limit(6))
            if not chunks:
                continue
            full_text = (node["label"] or "") + "\n\n" + "\n".join(
                c.get("text", "") for c in chunks
            )
            extracted = await extract_entities_llm(full_text, circ_no, api_key)
            ents = extracted["entities"]
            rels = extracted["relations"]
            db.compliance_graph_entities.update_one(
                {"circular_id": node["id"]},
                {"$set": {
                    "circular_id": node["id"],
                    "entities": ents,
                    "relations": rels,
                    "extracted_at": datetime.utcnow().isoformat(),
                }},
                upsert=True,
            )

        # Merge entities as new nodes (color = by type)
        for ent in ents:
            key = f"ent:{ent['type']}:{ent['name']}"
            if key not in added_entities:
                added_entities[key] = {
                    "id": key,
                    "label": ent["name"],
                    "source": "entity",
                    "category": ent["type"],
                    "category_group": "entity",
                    "year": None,
                    "url": "",
                    "val": 3,
                    "entity_type": ent["type"],
                }
            # Edge from circular → entity
            added_relations.append({
                "source": node["id"],
                "target": key,
                "relation": "MENTIONS",
                "type": "entity",
            })
        for rel in rels:
            src_key = None
            dst_key = None
            for k, v in added_entities.items():
                if v["label"] == rel.get("src"):
                    src_key = k
                if v["label"] == rel.get("dst"):
                    dst_key = k
            if src_key and dst_key:
                added_relations.append({
                    "source": src_key, "target": dst_key,
                    "relation": rel.get("type", "RELATED"), "type": "entity-rel",
                })

    subgraph["nodes"].extend(added_entities.values())
    subgraph["edges"].extend(added_relations)
    return subgraph


def graph_stats(db: Database) -> Dict:
    """Summary stats for the graph: total circulars (nodes), extracted
    entities, cached enrichments."""
    return {
        "total_circulars": db.compliance_circulars.count_documents({}),
        "llm_enriched_circulars": db.compliance_graph_entities.count_documents({}),
        "sources": db.compliance_circulars.distinct("source"),
    }
