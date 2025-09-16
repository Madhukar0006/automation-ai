import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Any
import json
from fastapi import Body

# Reuse your existing RAG helpers
from log_classifcation import load_rag_system, build_context_for_log, search_rag

app = FastAPI(title="RAG Bridge", version="0.1.0")

# Initialize RAG once
client, collection, embedding_model = load_rag_system(db_path=os.environ.get("RAG_DB_PATH", "./ecs_rag_database"))

METRICS_PATH = os.environ.get("RAG_METRICS_PATH", os.path.join(os.path.dirname(__file__), "metrics.jsonl"))

class MetricEvent(BaseModel):
    vendor: str | None = None
    product: str | None = None
    logType: str | None = None
    templateId: str | None = None
    success: bool
    parsed_fields: int | None = None
    total_fields: int | None = None
    notes: str | None = None

@app.post("/metrics/log")
async def log_metric(ev: MetricEvent):
    rec = ev.model_dump()
    rec["ts"] = __import__("datetime").datetime.utcnow().isoformat() + "Z"
    try:
        with open(METRICS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True}

class RetrieveRequest(BaseModel):
    sample: str
    logType: str | None = None
    vendor: str | None = None
    top_k: int = 8

class RetrieveResponse(BaseModel):
    templateId: str
    snippets: List[str]
    hints: List[str]

@app.post("/rag/retrieve", response_model=RetrieveResponse)
async def rag_retrieve(req: RetrieveRequest):
    if not (collection and embedding_model):
        # Fallback if RAG not initialized
        return RetrieveResponse(templateId=req.logType or "json", snippets=[], hints=["RAG not initialized"])

    fmt = (req.logType or "unknown").lower()

    # Build context for the given sample to bias retrieval
    context, _ = build_context_for_log(req.sample, collection, embedding_model, fmt)

    # Semantic search for top matches; prefer VRL examples/snippets
    results = search_rag(req.sample, collection, embedding_model, n_results=req.top_k)

    vrl_snippets: List[str] = []
    hints: List[str] = []

    # Extract VRL-looking content from top documents
    for r in results:
        doc = r.get("document", "")
        meta = r.get("metadata", {})
        file_name = str(meta.get("file", ""))
        if file_name.endswith(".vrl"):
            vrl_snippets.append(doc)
            hints.append(f"from: {file_name} sim={r.get('similarity', 0):.2f}")
        elif file_name.endswith(".txt") or file_name.endswith(".yaml"):
            # Helpful textual references
            hints.append(f"ref: {file_name} sim={r.get('similarity', 0):.2f}")

    # Fallback if nothing VRL-like was found
    if not vrl_snippets:
        hints.append("no .vrl snippets found in top results; returning empty snippets")

    template_id = req.logType or "json"
    return RetrieveResponse(templateId=template_id, snippets=vrl_snippets, hints=hints)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("RAG_PORT", 8001)))
