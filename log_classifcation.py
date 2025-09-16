import os
import re
import json
import os
import subprocess
import tempfile
import textwrap
from lc_bridge import classify_log_lc, generate_ecs_json_lc, generate_vrl_lc
import pandas as pd
import subprocess
from datetime import datetime, timezone
from typing import List, Tuple, Dict, Any

import streamlit as st
import chromadb
from sentence_transformers import SentenceTransformer
import ollama
import jsonschema

# =========================
# Streamlit Settings
# =========================
st.set_page_config(page_title="🧠 RAG + LLM Universal Log Parser", layout="wide")

# =========================
# Load Vendor/Product Reference (Agent C)
# =========================
@st.cache_data
def load_vendor_reference(xlsx_path: str = "data/all.xlsx") -> pd.DataFrame:
    try:
        df = pd.read_excel(xlsx_path)
        df.columns = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"❌ Could not load vendor reference file: {e}")
        return pd.DataFrame(columns=["vendor", "product"])

VENDOR_REF = load_vendor_reference()

# =========================
# Agent C: Log Classifier (line by line)
# =========================
JSON_REGEX = re.compile(r"^\s*\{.*\}\s*$")
SYSLOG_REGEX = re.compile(r"<\d{1,3}>.*")

def classify_log_line(line: str) -> Dict[str, Any]:
    line = line.strip()
    result = {
        "log_type": "event",
        "log_format": "unknown",
        "vendor": "unknown",
        "product": "unknown"
    }

    # --- Detect format ---
    if JSON_REGEX.match(line):
        result["log_format"] = "json"
    elif SYSLOG_REGEX.match(line):
        result["log_format"] = "syslog"
    else:
        result["log_format"] = "raw"

    # --- Detect vendor/product from all.xlsx ---
    for _, row in VENDOR_REF.iterrows():
        vendor = str(row.get("vendor", "")).lower()
        product = str(row.get("product", "")).lower()
        if vendor and vendor in line.lower():
            result["vendor"] = row.get("vendor")
            result["product"] = row.get("product")
            break
        if product and product in line.lower():
            result["vendor"] = row.get("vendor")
            result["product"] = row.get("product")
            break

    # --- Detect log type (basic heuristic) ---
    if "error" in line.lower():
        result["log_type"] = "error"
    elif "warn" in line.lower():
        result["log_type"] = "warning"
    elif "info" in line.lower():
        result["log_type"] = "info"

    return result

# =========================
# RAG — Init & Indexing
# =========================
COLLECTION_NAME = "ecs_fields_knowledge"

@st.cache_resource
def load_rag_system(db_path: str = "./ecs_rag_database"):
    try:
        client = chromadb.PersistentClient(path=db_path)
        try:
            collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            collection = client.create_collection(name=COLLECTION_NAME)
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return client, collection, embedding_model
    except Exception as e:
        st.error(f"Fatal Error: Failed to initialize RAG. Error: {e}")
        return None, None, None

def index_all_to_rag(collection, embedding_model, root_dir: str = "parserautomation"):
    """
    Recursively index all knowledge (templates, data, ecs fields, VRL snippets, etc.)
    inside the given root_dir into RAG.
    Supports: .txt, .vrl, .json, .yaml, .yml, .xlsx
    """
    if not os.path.isdir(root_dir):
        st.warning(f"Root directory '{root_dir}' not found.")
        return

    added = 0
    for subdir, _, files in os.walk(root_dir):
        for fname in files:
            if not fname.endswith((".txt", ".vrl", ".json", ".yaml", ".yml", ".xlsx")):
                continue

            fpath = os.path.join(subdir, fname)
            rel_path = os.path.relpath(fpath, root_dir)  # store relative path as metadata

            try:
                # Special handling for Excel files
                if fname.endswith(".xlsx"):
                    try:
                        df = pd.read_excel(fpath)
                        text = df.to_csv(index=False)  # flatten into CSV string
                    except Exception as e:
                        st.error(f"Failed to parse Excel {fpath}: {e}")
                        continue
                else:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read().strip()

                if not text:
                    continue

                emb = embedding_model.encode([text])[0].tolist()
                _id = f"doc::{rel_path}"
                collection.add(
                    documents=[text],
                    embeddings=[emb],
                    ids=[_id],
                    metadatas=[{"path": rel_path, "file": fname}]
                )
                added += 1
            except Exception as e:
                st.error(f"Failed to index {rel_path}: {e}")

    if added:
        st.success(f"Indexed {added} document(s) from {root_dir} into RAG ✅")
    else:
        st.info("No documents indexed (check extensions and directories).")
        
def index_templates_to_rag(collection, embedding_model, template_dir: str = "templates"):
    """
    Index template files from the template directory into RAG.
    Creates the template directory if it doesn't exist.
    """
    # Create template directory if it doesn't exist
    if not os.path.exists(template_dir):
        try:
            os.makedirs(template_dir)
            st.success(f"Created template directory: '{template_dir}' ✅")
        except Exception as e:
            st.error(f"Failed to create template directory: {e}")
            return
    elif not os.path.isdir(template_dir):
        st.error(f"'{template_dir}' exists but is not a directory.")
        return
        
    # Count templates
    added = 0
    
    # Process each subdirectory in the template directory
    for dirname in os.listdir(template_dir):
        dirpath = os.path.join(template_dir, dirname)
        if not os.path.isdir(dirpath):
            continue
            
        for filename in os.listdir(dirpath):
            if not filename.endswith((".txt", ".vrl", ".json", ".yaml", ".yml")):
                continue
                
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()
                    
                if not content:
                    continue
                    
                emb = embedding_model.encode([content])[0].tolist()
                _id = f"template::{dirname}/{filename}"
                collection.add(
                    documents=[content],
                    embeddings=[emb],
                    ids=[_id],
                    metadatas=[{"type": "template", "vendor": dirname, "file": filename}]
                )
                added += 1
            except Exception as e:
                st.error(f"Failed to index template {filepath}: {e}")
    
    if added:
        st.success(f"Indexed {added} template(s) into RAG ✅")
    else:
        st.info("No templates indexed. Add .txt, .vrl, .json, .yaml, or .yml files to template subdirectories.")

# =========================
# Utilities
# =========================
def fix_json_arrays(data):
    if isinstance(data, dict):
        if data and all(k.isdigit() for k in data.keys()):
            keys = sorted(data.keys(), key=int)
            if all(int(k) == i for i, k in enumerate(keys)):
                return [fix_json_arrays(data[k]) for k in keys]
        return {k: fix_json_arrays(v) for k, v in data.items()}
    if isinstance(data, list):
        return [fix_json_arrays(v) for v in data]
    return data

def normalize_distance(d):
    if isinstance(d, (list, tuple)):
        return float(d[0]) if d else 1.0
    try:
        return float(d)
    except:
        return 1.0

def search_rag(query: str, collection, embedding_model, n_results=50):
    if not query.strip():
        return []
    flat_vec = embedding_model.encode([query])[0].tolist()
    sem = collection.query(query_embeddings=[flat_vec], n_results=n_results)
    docs   = sem.get('documents', [[]])[0]
    dists  = sem.get('distances', [[]])[0]
    metas  = sem.get('metadatas', [[]])[0]
    ids    = sem.get('ids', [[]])[0]

    results = []
    seen = set()
    ql = query.lower()
    for i, doc in enumerate(docs):
        doc_id = ids[i] if i < len(ids) else f"doc_{i}"
        if doc_id in seen:
            continue
        seen.add(doc_id)
        dist = normalize_distance(dists[i] if i < len(dists) else 1.0)
        sim = max(0, min(1, 1.0 - dist))
        contains = ql in str(doc).lower()
        if contains:
            sim = min(1.0, sim + 0.3)
        if sim > 0.2 or contains:
            results.append({
                'rank': len(results) + 1,
                'document': str(doc),
                'similarity': sim,
                'metadata': metas[i] if i < len(metas) else {},
                'contains': contains
            })
    return sorted(results, key=lambda x: x['similarity'], reverse=True)

def build_context_for_log(log: str, collection, embedding_model, fmt: str, n_results=20):
    """
    Retrieve the most relevant docs/templates and return a compact context string
    plus the top metadata rows to show in UI.
    """
    qt = f"Log format: {fmt}\n\n{log}"
    flat_vec = embedding_model.encode([qt])[0].tolist()
    res = collection.query(query_embeddings=[flat_vec], n_results=n_results)

    docs = [str(d) for d in res.get("documents", [[]])[0]]
    metas = res.get("metadatas", [[]])[0]

    context_texts = []
    for i, doc in enumerate(docs[:12]):
        meta = metas[i] if metas and i < len(metas) else {}
        label = ""
        if meta.get("type") == "template":
            label = f"[Template: {meta.get('vendor','?')}/{meta.get('file','?')}]"
        elif meta.get("type") == "ecs_field":
            label = f"[ECS Field: {meta.get('field','?')}]"
        else:
            label = "[Context]"
        context_texts.append(f"{label}\n{doc}")

    return "\n\n---\n\n".join(context_texts), metas[:12]

def preprocess_multiline_log(log: str) -> str:
    # For stack traces, collapse to single line (helps grok/LLM)
    if "\n" in log.strip():
        if re.search(r'\s+at\s+[\w\.]+(?:\(.*?\))?', log):
            return " ".join(log.splitlines())
    return log

def detect_pairs(before: Dict[str, Any], after: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Find fields that disappeared vs new ECS-like paths (rough rename heuristic)."""
    def paths(d, base=""):
        out = []
        if isinstance(d, dict):
            for k, v in d.items():
                p = f"{base}.{k}" if base else k
                out.append(p)
                out.extend(paths(v, p))
        elif isinstance(d, list):
            for i, v in enumerate(d):
                p = f"{base}[{i}]"
                out.append(p)
                out.extend(paths(v, p))
        return out

    bpaths = set(paths(before))
    apaths = set(paths(after))
    lost = [p for p in bpaths if p not in apaths]
    gained = [p for p in apaths if p not in bpaths and (
        p.startswith(("event.", "host.", "process.", "source.", "destination.",
                      "user.", "client.", "server.", "network.", "related.",
                      "log.", "observer.", "agent.", "winlog."))
    )]
    pairs = []
    for o in lost:
        base = o.split(".")[-1].lower()
        cands = [g for g in gained if g.split(".")[-1].lower() == base]
        if cands:
            pairs.append((o, cands[0]))
    return pairs

def summarize_leftovers(after: Dict[str, Any]) -> List[str]:
    """Return list of fields under event_data.*."""
    out = []
    def walk(d, base=""):
        if isinstance(d, dict):
            for k, v in d.items():
                p = f"{base}.{k}" if base else k
                if p.startswith("event_data") or p.startswith("winlog.event_data"):
                    out.append(p)
                walk(v, p)
        elif isinstance(d, list):
            for i, v in enumerate(d):
                walk(v, f"{base}[{i}]")
    walk(after)
    return sorted(set(out))

# =========================
# Agent C — JSON & VRL Validation
# =========================
ECS_SCHEMA = {
    "type": "object",
    "properties": {
        "@timestamp": {"type": "string"},
        "event": {"type": "object"},
        "host": {"type": "object"},
        "source": {"type": "object"},
        "destination": {"type": "object"},
        "user": {"type": "object"},
        "process": {"type": "object"},
        "network": {"type": "object"},
        "observer": {"type": "object"},
        "agent": {"type": "object"},
        "related": {"type": "object"},
        "log": {"type": "object"},
        "winlog": {"type": "object"},
    },
    "additionalProperties": True  # allow vendor fields
}

def validate_ecs_json(data: dict) -> Tuple[bool, list]:
    """Validate JSON against a minimal ECS schema and return errors."""
    try:
        jsonschema.validate(instance=data, schema=ECS_SCHEMA)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [e.message]

def validate_vrl_text_or_file(vrl_text: str, path: str = None) -> Tuple[bool, str]:
    """
    If a file path is provided and Vector CLI exists, try `vector validate --config`.
    Otherwise run heuristic checks.
    """
    if path:
        try:
            result = subprocess.run(
                ["vector", "validate", "--config", path],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return True, "Vector CLI validation passed ✅"
            else:
                return False, result.stderr.strip() or "Vector CLI validation failed"
        except FileNotFoundError:
            # Fall back to text checks
            pass

    issues = []
    if "parse_groks" not in vrl_text and "parse_json" not in vrl_text and "parse_syslog" not in vrl_text:
        issues.append("No primary parser (parse_groks/parse_json/parse_syslog) found.")
    if ".event.created" not in vrl_text:
        issues.append("Missing .event.created assignment.")
    if "compact(" not in vrl_text:
        issues.append("Missing final compact() call.")
    if "parse_groks" in vrl_text and "[" not in vrl_text.split("parse_groks", 1)[1]:
        issues.append("parse_groks should receive an array of patterns.")

    return (len(issues) == 0, " ; ".join(issues) if issues else "Basic VRL checks passed ✅")

# =========================
# LLM Prompts (Agents A & B) - Base prompts (will be extended by Query Agent)
# =========================
BASE_JSON_SYSTEM_PROMPT = """You are Agent A, a meticulous, expert log parser and ECS mapper. Your primary goal is to produce a clean, flat, and correct ECS JSON object.

Your task is to transform a raw log into a VALID JSON object that strictly adheres to the Elastic Common Schema (ECS).

---

### Core Rules (Mandatory)

1.  **Produce a Flat Structure**: You MUST map all extracted fields to their correct, top-level ECS destinations (e.g., `source.ip`, `host.name`, `event.action`).
2.  **Strict `.event_data` Usage**: The `.event_data` object is ONLY for vendor-specific, non-standard fields that have no place in the ECS schema. Do NOT put standard ECS fields inside `.event_data`.
3.  **No Incorrect Nesting**: Do NOT nest standard ECS fields inside other objects unless the ECS schema explicitly defines it that way. For example, `source.ip` should never be inside `host`.
4.  **Use RAG Context**: You MUST use the provided RAG context (ECS field definitions, vendor info, professional examples) to guide your mapping decisions.
5.  **No Invented Data**: If a value is not present in the raw log, do not add its field to the JSON. The final output should be compact.

---

### Your Process

1.  Analyze the raw log.
2.  Use the RAG context to understand the fields and their correct ECS locations.
3.  Generate a single, clean JSON object that follows all of the rules above.

Return ONLY the final JSON object. Do not include markdown formatting or any other commentary.
"""

BASE_VRL_SYSTEM_PROMPT = """You are Agent B, a meticulous, senior Vector Dev engineer. Your code is clean, efficient, and maintainable. You follow instructions perfectly.

Your task is to generate a professional-grade, production-ready VRL (Vector Remap Language) parser that is as clean and readable as if written by a senior JavaScript developer. You MUST mimic the structure, style, and logic of the professional reference examples provided in the RAG context.

---

### VRL Code Quality Requirements (Mandatory)

1.  **Strict 5-Step Structure**: You MUST organize all VRL code into the following five logical sections, using the provided markdown headers.
    
    *   `## 1. Initialization`: Set base ECS fields like `event.kind`, `observer.vendor`, etc. Initialize empty arrays for `related.*` fields.
    *   `## 2. Primary Parsing`: Perform the main, top-level parsing of the log line (e.g., with `parse_groks` or `parse_json`). Store the result in a temporary variable like `_parsed`.
    *   `## 3. Detailed Field Mapping`: Map the fields from the `_parsed` object into their correct ECS destinations.
    *   `## 4. Data Transformation`: Handle all data type conversions (e.g., `to_int`, `to_float`) and other transformations.
    *   `## 5. Final Cleanup`: Explicitly delete all temporary variables (e.g., `del(._parsed)`), build the `related.*` fields, and run `compact()` on the final event.

2.  **Meaningful Comments**: Add comments only to explain complex grok patterns or non-obvious transformation logic. Do not add comments for simple assignments.

3.  **Error Handling**: The entire script MUST be wrapped in a single `try...catch` block.

---

### Forbidden Actions (What NOT to do)

-   **DO NOT** leave temporary fields (e.g., `_grokked`, `_tmp`, `parsed`, `kv`) in the final event. They MUST be deleted in the Cleanup step.
-   **DO NOT** use complex, inline regex. You MUST use the named grok patterns provided in the RAG context.
-   **DO NOT** produce messy, unformatted, or uncommented code. Your code must be professional.
-   **DO NOT** forget to run `compact()` as the very last step to remove all `null` and empty fields.

---

### Your Process

1.  Analyze the provided professional VRL examples to understand the required style.
2.  Generate a VRL script that perfectly follows all of the quality requirements listed above.

Return ONLY the VRL code. Do not include markdown formatting (like ```vrl) or any other commentary.
"""

# =========================
# Query Agent (Agent Q)
# =========================
def extract_candidate_vendors_and_products(matches: List[Dict[str, Any]], docs: List[str]) -> Tuple[List[str], List[str]]:
    """
    Heuristics: examine metadata 'vendor' and filenames for vendor names,
    and look for product-like tokens in document text (common product keywords).
    """
    vendors = []
    products = []
    product_keywords = ["fortigate", "checkpoint", "cisco", "paloalto", "ngfw", "firewall", "fortinet", "syslog", "nginx", "apache"]
    for m in matches:
        # metadata may be empty or partial
        meta = m if isinstance(m, dict) else {}
        v = meta.get("vendor") or meta.get("file") or meta.get("path") or ""
        if isinstance(v, str) and v:
            # split candidate tokens
            for token in re.split(r"[_\-\./\s]+", v.lower()):
                if token and token not in vendors:
                    vendors.append(token)
        # scan doc text snippets
    for doc in docs:
        txt = doc.lower()
        for k in product_keywords:
            if k in txt and k not in products:
                products.append(k)
        # try to find patterns like 'product: X' or 'vendor: X'
        for m in re.finditer(r"(?:vendor|product|app|module)\s*[:=]\s*([A-Za-z0-9_\-]+)", txt):
            candidate = m.group(1).lower()
            if candidate not in products:
                products.append(candidate)
    # fallback cleanup
    vendors = [v for v in vendors if len(v) > 1][:10]
    products = [p for p in products if len(p) > 1][:10]
    return vendors, products

def recommend_parsers(fmt: str, raw_log: str, vendors: List[str], products: List[str]) -> List[str]:
    """
    Simple heuristics to recommend parser types. Returns ordered list of parser strategies.
    """
    rec = []
    fmt = (fmt or "").lower()
    raw = raw_log.strip()
    if fmt == "json" or raw.startswith("{"):
        rec.append("parse_json")
    if fmt in ("syslog", "apache_access", "apache_error") or re.search(r"<\d+>", raw):
        rec.append("parse_syslog")
    # key-value or kv-like
    if "=" in raw and re.search(r"\w+=\S+", raw):
        rec.append("parse_key_value")
    # grok if unstructured
    if len(rec) == 0:
        # choose grok as default for unstructured textual logs
        rec.append("parse_groks")
    # vendor-specific hints
    if any(v for v in vendors if "forti" in v or "fortigate" in v):
        rec.insert(0, "fortigate_grok_templates")
    if any(p for p in products if "checkpoint" in p):
        rec.insert(0, "checkpoint_grok_templates")
    # dedupe while keeping order
    seen = set()
    out = []
    for r in rec:
        if r not in seen:
            out.append(r)
            seen.add(r)
    return out

def query_agent_summarize(fmt: str, raw_log: str, context_text: str, matches_meta: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Inspect fmt, raw_log, RAG matches and produce a concise summary:
      - detected_log_type
      - recommended_parsers (ordered)
      - candidate_vendors
      - candidate_products
      - top_matches (brief)
    """
    # convert context_text back into snippets
    docs = []
    try:
        # split by our separator if built_context_for_log used
        docs = [s.strip() for s in re.split(r"\n\n---\n\n", context_text) if s.strip()]
    except Exception:
        docs = [context_text] if context_text else []
    vendors, products = extract_candidate_vendors_and_products(matches_meta, docs)
    parsers = recommend_parsers(fmt, raw_log, vendors, products)
    top = []
    for m in matches_meta[:8]:
        summary = {}
        if isinstance(m, dict):
            summary["file"] = m.get("file") or m.get("path") or ""
            summary["type"] = m.get("type") or ""
            summary["field"] = m.get("field") if "field" in m else ""
            # small snippet preview unavailable here — we rely on build_context_for_log display
        top.append(summary)
    summary = {
        "detected_log_type": fmt,
        "recommended_parsers": parsers,
        "candidate_vendors": vendors,
        "candidate_products": products,
        "top_matches": top
    }
    return summary

def query_agent_to_prompt_prefix(summary: Dict[str, Any]) -> str:
    """
    Convert Query Agent summary into a neat text prefix for system prompts.
    This gets prepended to system prompts for Agent A/B so they receive dynamic guidance.
    """
    lines = []
    lines.append("Query Agent Summary:")
    lines.append(f"- Detected log type: {summary.get('detected_log_type','unknown')}")
    cvs = summary.get("candidate_vendors", [])
    if cvs:
        lines.append(f"- Candidate vendors (from RAG matches/filenames): {', '.join(cvs[:6])}")
    cps = summary.get("candidate_products", [])
    if cps:
        lines.append(f"- Candidate products found: {', '.join(cps[:6])}")
    pars = summary.get("recommended_parsers", [])
    if pars:
        lines.append(f"- Recommended parser strategies (priority order): {', '.join(pars)}")
    # short top_matches listing
    top = summary.get("top_matches", [])[:6]
    if top:
        tm = []
        for t in top:
            if t.get("file"):
                tm.append(t.get("file"))
        if tm:
            lines.append(f"- Top matching files: {', '.join(tm)}")
    lines.append("\nPlease use this summary as high-priority guidance when mapping fields or generating VRL.")
    return "\n".join(lines)

# =========================
# LLM Agent Calls (A & B) - updated to accept dynamic prompt prefix
# =========================
def call_llm_for_json(context_text: str, log: str, dynamic_prefix: str = "") -> Dict[str, Any]:
    """
    Agent A: produce ECS JSON. Accepts dynamic_prefix (Query Agent summary) which is prepended
    to the base system prompt for additional guidance.
    """
    try:
        if log.strip().startswith("{"):
            parsed = json.loads(log)
            log_for_llm = json.dumps(parsed, indent=2)
        else:
            log_for_llm = log
    except Exception:
        log_for_llm = log

    system_prompt = dynamic_prefix + "\n\n" + BASE_JSON_SYSTEM_PROMPT if dynamic_prefix else BASE_JSON_SYSTEM_PROMPT

    resp = ollama.chat(
        model="llama3.2:latest",   # Agent A uses llama3
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Authoritative Context:\n{context_text}\n\nRaw Log:\n```\n{log_for_llm}\n```"}
        ],
        format="json",
        # optionally pass additional ollama options if needed
    )

    txt = resp["message"]["content"].strip()
    try:
        data = json.loads(txt)
    except json.JSONDecodeError:
        # recover if fenced or extra text
        txt_clean = re.sub(r"^```(?:json)?", "", txt).strip()
        txt_clean = re.sub(r"```$", "", txt_clean).strip()
        # Some LLM outputs may include leading notes; we assume the JSON starts at first '{'
        idx = txt_clean.find("{")
        if idx != -1:
            txt_clean = txt_clean[idx:]
        data = json.loads(txt_clean)

    data = fix_json_arrays(data)
    if isinstance(data, dict):
        evt = data.get("event", {})
        if isinstance(evt, dict) and "created" not in evt:
            evt["created"] = datetime.now(timezone.utc).isoformat()
            data["event"] = evt
    return data

def call_llm_for_vrl(context_text: str, log: str, dynamic_prefix: str = "") -> str:
    """
    Agent B: generate VRL. Accepts dynamic_prefix (Query Agent summary) which is prepended
    to the base system prompt for additional guidance.
    """
    system_prompt = dynamic_prefix + "\n\n" + BASE_VRL_SYSTEM_PROMPT if dynamic_prefix else BASE_VRL_SYSTEM_PROMPT

    resp = ollama.chat(
        model="phi3:mini",   # Agent B uses mistral
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Authoritative Context:\n{context_text}\n\nWrite a full VRL parser for this sample log:\n{log}"}
        ],
        # format default
    )

    code = resp["message"]["content"].strip()
    code = re.sub(r"^```[a-zA-Z]*", "", code).strip()
    code = re.sub(r"```$", "", code).strip()
    return code

def call_llm_for_classification(log: str, context: str) -> Dict[str, str]:
    """
    Step 1: The Classifier Agent.
    Identifies the log's profile and returns a structured JSON.
    """
    CLASSIFIER_PROMPT = """
    You are an expert log classification agent. Your task is to analyze a raw log and return a JSON object with the following four fields:
    - log_type (e.g., firewall, web, os, application)
    - log_format (e.g., syslog, cef, json, kv, raw)
    - vendor (e.g., Cisco, Check Point, Palo Alto Networks)
    - product (e.g., ASA, Firewall-1, PAN-OS)

    Use the provided RAG context, which contains vendor information from `all.xlsx` and various log examples, to make an informed decision.
    Return ONLY the completed JSON object. No commentary.
    """
    resp = ollama.chat(
        model="llama3.2:latest",
        messages=[
            {"role": "system", "content": CLASSIFIER_PROMPT},
            {"role": "user", "content": f"Authoritative Context:\n{context}\n\nRaw Log:\n```\n{log}\n```\n\nClassify the raw log."}
        ],
        format="json",
    )
    return json.loads(resp["message"]["content"].strip())

def select_and_rewrite_prompt(profile: Dict[str, str]) -> str:
    """
    Steps 2 & 3: The Query Agent.
    Selects a prompt template based on the log format and rewrites it.
    """
    # Guard against non-dict or unexpected values
    if not isinstance(profile, dict):
        profile = {}
    lf = profile.get("log_format", "raw")
    if not isinstance(lf, str):
        lf = "raw"
    log_format = lf.lower()
    
    # In a real system, these would be loaded from the /prompts directory.
    # For now, we define them here for simplicity.
    prompt_templates = {
        "syslog": "You are parsing a {log_format} log for {vendor} {product}, classified as {log_type}. Focus on ECS fields like source.ip, destination.ip, and event.action. Use syslog parsing patterns.",
        "cef": "You are parsing a {log_format} log. Use CEF header parsing and then map the key-value extensions to ECS.",
        "json": "You are parsing a {log_format} log. Your primary task is to map the existing JSON keys to their correct ECS fields.",
        "raw": "You are parsing a raw, unstructured log. Use generic grok patterns and heuristics to extract as much meaningful data as possible."
    }

    # Select the template, defaulting to 'raw'
    template = prompt_templates.get(log_format, prompt_templates["raw"])

    # Rewrite the prompt with the profile information
    rewritten_prompt = template.format(
        log_format=profile.get("log_format", "N/A"),
        vendor=profile.get("vendor", "N/A"),
        product=profile.get("product", "N/A"),
        log_type=profile.get("log_type", "N/A")
    )
    return rewritten_prompt

def lint_and_fix_vrl(vrl: str):
    issues, fixes = [], []

    # Force parse_groks to use array arg shape if present as string
    if "parse_groks" in vrl and "[" not in vrl:
        issues.append("parse_groks missing array brackets")
        vrl = vrl.replace('parse_groks(.event.original, "', 'parse_groks(.event.original, ["')
        vrl = vrl.replace('")', '"])')
        fixes.append("Wrapped parse_groks pattern in array")

    # Ensure event.created exists
    if ".event.created" not in vrl:
        issues.append("No .event.created assignment")
        vrl += '\n.event.created = to_string!(format_timestamp!(now(), "%FT%T%.3fZ"))'
        fixes.append("Added fallback event.created")

    # Ensure compact at end
    if "compact(" not in vrl:
        issues.append("Final compact() missing")
        vrl += '\n. = compact(., string: true, array: true, object: true, null: true)'
        fixes.append("Appended compact()")

    return vrl, issues, fixes

# =========================
# Sidebar — Knowledge Base & Indexing
# =========================
client, collection, embedding_model = load_rag_system()
st.sidebar.title("🧠 RAG Knowledge Base")

with st.sidebar.expander("⚙️  Indexing"):
    data_dir = st.text_input("Data directory", value="data")
    if st.button("Re-index Data → RAG"):
        if collection and embedding_model:
            index_all_to_rag(collection, embedding_model, root_dir=data_dir)
        else:
            st.error("RAG not initialized (collection/model).")

with st.sidebar.expander("⚙️ Full-dir Indexing"):
    root_dir = st.text_input("Root dir to index (for docs/templates)", value="parserautomation")
    if st.button("Index Full Directory → RAG"):
        if collection and embedding_model:
            index_all_to_rag(collection, embedding_model, root_dir=root_dir)
        else:
            st.error("RAG not initialized (collection/model).")

# Streamlit UI (Add Agent C panel)
# =========================
st.sidebar.header("🔍 Agent C - Log Classifier")
sample_log = st.sidebar.text_area("Paste one log line:", height=120, key="agent_c_sample_input")
if st.sidebar.button("Classify Log"):
    if sample_log.strip():
        classification = classify_log_line(sample_log)
        st.sidebar.json(classification)
    else:
        st.sidebar.warning("⚠️ Please paste a log line.")

# =========================
# Main App
# =========================
st.title("🧠 Universal Log Parser (RAG + LLM → ECS & VRL)")

client, collection, embedding_model = load_rag_system()

if not (collection and embedding_model):
    st.error("RAG not initialized.")
    st.stop()

# Sidebar for Data Directories
# ... (sidebar code remains the same)

raw_log = st.text_area("Raw log", height=200, key="raw_log_input")
do_json = st.button("Parse → ECS JSON")
do_vrl = st.button("Generate VRL Parser")

if raw_log and (do_json or do_vrl):
    
    # Step 1: Classify the log
    with st.spinner("Step 1: Classifying log..."):
        # We need some initial context for the classifier.
        # A simple query on the raw log is sufficient.
        initial_ctx, _ = build_context_for_log(raw_log, collection, embedding_model, "unknown")
        # Prefer LangChain-based classifier; fallback to existing on failure
        try:
            profile = classify_log_lc(raw_log)
        except Exception:
            profile = call_llm_for_classification(raw_log, initial_ctx)

    st.subheader("📝 Identified Log Profile")
    st.json(profile)

    # Steps 2 & 3: Select and rewrite the prompt
    with st.spinner("Step 2 & 3: Query Agent is selecting and rewriting prompt..."):
        rewritten_prompt = select_and_rewrite_prompt(profile)
    
    st.subheader("🤖 Dynamic Prompt for Parser Agent")
    st.markdown(f"> {rewritten_prompt}")

    # Step 4: Routing rules
    # - If user clicked Generate VRL → always generate VRL (override auto JSON)
    # - Else if user clicked JSON or auto-detected JSON → generate JSON
    # - Else → generate VRL
    detected_format = str(profile.get("log_format", "")).lower().strip()
    auto_json = detected_format == "json" or raw_log.strip().startswith("{")

    if do_vrl:
        with st.spinner("Step 4: Parser Agent is generating VRL..."):
            try:
                try:
                    vrl_text = generate_vrl_lc(initial_ctx, raw_log, dynamic_prefix=rewritten_prompt)
                except Exception:
                    vrl_text = call_llm_for_vrl(initial_ctx, raw_log, dynamic_prefix=rewritten_prompt)
                # Sanitize: keep only VRL-looking lines (no JSON keys like "ECS Field" etc.)
                cleaned_lines = []
                for line in vrl_text.splitlines():
                    token = line.strip().split()[0] if line.strip() else ""
                    if line.strip().startswith("{"):
                        # looks like JSON/schema prose, skip
                        continue
                    if token and (token.endswith(":") or token in {"ECS", "Field", "Type", "Description"}):
                        continue
                    # Skip non-VRL map literal style like: event_data { "k" => "v" }
                    if "=>" in line and "{" in line and "}" in line:
                        continue
                    if line.strip().startswith("```"):
                        continue
                    cleaned_lines.append(line)
                vrl_text = "\n".join(cleaned_lines).strip()
                st.subheader("🛠️ Generated VRL Parser")
                st.code(vrl_text, language="yaml")

                # Store in session for CLI run
                st.session_state["last_vrl_text"] = vrl_text
                st.session_state["last_sample_log"] = raw_log

                # Offer Vector CLI run on sample
                if st.button("Run Vector CLI on sample"):
                    try:
                        with tempfile.TemporaryDirectory() as td:
                            log_path = os.path.join(td, "sample.log")
                            cfg_path = os.path.join(td, "vector.yaml")
                            with open(log_path, "w", encoding="utf-8") as f:
                                f.write(raw_log.strip() + "\n")
                            cfg = textwrap.dedent(f"""
                            sources:
                              in:
                                type: file
                                include:
                                  - "{log_path}"

                            transforms:
                              remap:
                                type: remap
                                inputs: [in]
                                source: |-
                                  {vrl_text}

                            sinks:
                              out:
                                type: console
                                inputs: [remap]
                                encoding:
                                  codec: json
                            """).strip()
                            with open(cfg_path, "w", encoding="utf-8") as f:
                                f.write(cfg)

                            proc = subprocess.run(
                                ["vector", "--config", cfg_path],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                check=False,
                            )
                            if proc.returncode != 0 and not proc.stdout.strip():
                                st.error("Vector CLI failed. Ensure 'vector' is installed and on PATH.")
                                if proc.stderr:
                                    st.code(proc.stderr)
                            else:
                                out = proc.stdout.strip()
                                last_line = out.strip().splitlines()[-1] if out.strip() else "{}"
                                try:
                                    parsed = json.loads(last_line)
                                    st.subheader("📦 Vector CLI Output (JSON)")
                                    st.code(json.dumps(parsed, indent=2), language="json")
                                except Exception:
                                    st.subheader("📦 Vector CLI Raw Output")
                                    st.code(out)
                    except Exception as e:
                        st.error(f"Vector run error: {e}")
            except Exception as e:
                st.error(f"LLM VRL generation error: {e}")
    elif do_json or auto_json:
        st.info("Detected JSON log format → routing to ECS JSON parsing.")
        with st.spinner("Step 4: Parser Agent is generating JSON..."):
            try:
                try:
                    ecs_json = generate_ecs_json_lc(initial_ctx, raw_log, dynamic_prefix=rewritten_prompt)
                except Exception:
                    ecs_json = call_llm_for_json(initial_ctx, raw_log, dynamic_prefix=rewritten_prompt)
                st.subheader("✅ ECS JSON Output")
                st.code(json.dumps(ecs_json, indent=2), language="json")
            except Exception as e:
                st.error(f"LLM JSON parse error: {e}")
    else:
        with st.spinner("Step 4: Parser Agent is generating VRL..."):
            try:
                try:
                    vrl_text = generate_vrl_lc(initial_ctx, raw_log, dynamic_prefix=rewritten_prompt)
                except Exception:
                    vrl_text = call_llm_for_vrl(initial_ctx, raw_log, dynamic_prefix=rewritten_prompt)
                st.subheader("🛠️ Generated VRL Parser")
                st.code(vrl_text, language="yaml")
            except Exception as e:
                st.error(f"LLM VRL generation error: {e}")

# =========================
# Grok Pattern Assistant (Match or Enhance)
# =========================
def _grok_to_regex(grok: str) -> str:
    import re
    pattern = grok
    # Basic mappings for common GROK tokens
    mappings = {
        'IPORHOST': r'(?P<%FIELD%>(?:[0-9]{1,3}(?:\\.[0-9]{1,3}){3}|[A-Za-z0-9_.-]+))',
        'IP': r'(?P<%FIELD%>(?:[0-9]{1,3}(?:\\.[0-9]{1,3}){3}))',
        'WORD': r'(?P<%FIELD%>[A-Za-z0-9_]+)',
        'NUMBER': r'(?P<%FIELD%>[0-9]+(?:\\.[0-9]+)?)',
        'URIPATHPARAM': r'(?P<%FIELD%>\\S+)',
        'URIPATH': r'(?P<%FIELD%>\\S+)',
        'DATA': r'(?P<%FIELD%>.*)',
        'GREEDYDATA': r'(?P<%FIELD%>.*)',
        'HTTPDATE': r'(?P<%FIELD%>[^\\]]+)',
    }
    # Replace %{PATTERN:field}
    def repl(m):
        pat = m.group(1)
        field = m.group(2)
        base = mappings.get(pat, r'(?P<%FIELD%>.+?)')
        return base.replace('%FIELD%', field)
    pattern = re.sub(r'%\\{([A-Z0-9_]+):([A-Za-z0-9_.]+)\\}', repl, pattern)
    # Replace %{PATTERN} (without field) with non-capturing group
    pattern = re.sub(r'%\\{([A-Z0-9_]+)\\}', r'(?:.+?)', pattern)
    return '^' + pattern + '$'

def grok_match(reference_grok: str, log_line: str) -> bool:
    import re
    try:
        regex = _grok_to_regex(reference_grok)
        return re.match(regex, log_line) is not None
    except Exception:
        return False

def grok_enhance(reference_grok: str, log_line: str):
    # Heuristics: if HTTP pattern, add response code/bytes; else add GREEDY tail
    enhanced = reference_grok
    new_fields = []
    if 'HTTP/%{NUMBER:http_version}' in enhanced:
        if 'response_code' not in enhanced:
            enhanced = enhanced + ' %{NUMBER:response_code}'
            new_fields.append('response_code')
        if 'response_bytes' not in enhanced:
            enhanced = enhanced + ' %{NUMBER:response_bytes}'
            new_fields.append('response_bytes')
    else:
        if '%{GREEDYDATA:' not in enhanced:
            enhanced = enhanced + ' %{GREEDYDATA:message_tail}'
            new_fields.append('message_tail')
    return enhanced, new_fields

st.header("🧩 Grok Pattern Assistant")
ref_grok = st.text_input(
    "Reference Grok pattern",
    value="%{IPORHOST:source_address} - %{WORD:http_method} %{URIPATHPARAM:url} HTTP/%{NUMBER:http_version}"
)
new_log = st.text_area("New log line", height=80, key="grok_new_log")
if st.button("Check / Enhance Grok"):
    if ref_grok.strip() and new_log.strip():
        if grok_match(ref_grok.strip(), new_log.strip()):
            st.success("MATCHED")
        else:
            pattern, new_fields = grok_enhance(ref_grok.strip(), new_log.strip())
            # Output only the Grok pattern
            st.code(pattern, language="text")
            if new_fields:
                st.caption("New fields: " + ", ".join(new_fields))
            # Push to DB button
            if st.button("Push to DB"):
                try:
                    import json, datetime
                    rec = {
                        "reference_grok": ref_grok.strip(),
                        "new_log": new_log.strip(),
                        "enhanced_grok": pattern,
                        "new_fields": new_fields,
                        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
                    }
                    snippets_path = os.path.join("data", "snippets.jsonl")
                    os.makedirs(os.path.dirname(snippets_path), exist_ok=True)
                    with open(snippets_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    st.success("✅ Saved to data/snippets.jsonl")
                except Exception as e:
                    st.error(f"Failed to save: {e}")