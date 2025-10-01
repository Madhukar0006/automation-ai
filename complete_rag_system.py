"""
Complete RAG System with Embeddings and ChromaDB
Handles downloading models, setting up vector database, and RAG operations
"""

import os
import json
import time
import chromadb
from chromadb.config import Settings
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    # Fallback for compatibility issues
    SentenceTransformer = None
import pandas as pd
from typing import List, Dict, Any, Optional
import streamlit as st
from pathlib import Path
import logging
from typing import Iterable

# LangChain v0.3-style RAG (local-only)
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.vectorstores import Chroma as LCChroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_core.documents import Document
    _LC_AVAILABLE = True
except Exception:
    _LC_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompleteRAGSystem:
    """Complete RAG system with embeddings and ChromaDB"""
    
    def __init__(self, 
                 embedding_model_name: str = "all-MiniLM-L6-v2",
                 chroma_persist_directory: str = "./chroma_db",
                 data_directory: str = "./data"):
        
        self.embedding_model_name = embedding_model_name
        self.chroma_persist_directory = chroma_persist_directory
        self.data_directory = data_directory
        
        # Initialize components
        self.embedding_model = None
        self.chroma_client = None
        self.collection = None
        self.vendor_reference = None
        
        # Create directories
        os.makedirs(chroma_persist_directory, exist_ok=True)
        os.makedirs(data_directory, exist_ok=True)
    
    def setup_embedding_model(self):
        """Download and setup the embedding model"""
        try:
            if SentenceTransformer is None:
                logger.error("❌ SentenceTransformer not available - install with: pip install sentence-transformers")
                return False
                
            logger.info(f"Setting up embedding model: {self.embedding_model_name}")
            
            # Check if model is already downloaded
            model_path = f"./models/{self.embedding_model_name}"
            if os.path.exists(model_path):
                logger.info(f"Loading existing model from {model_path}")
                self.embedding_model = SentenceTransformer(model_path)
            else:
                logger.info(f"Downloading model: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                
                # Save model locally
                os.makedirs("./models", exist_ok=True)
                self.embedding_model.save(model_path)
                logger.info(f"Model saved to {model_path}")
            
            logger.info("✅ Embedding model setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup embedding model: {str(e)}")
            return False

    def _iter_index_paths(self) -> Iterable[str]:
        """Yield indexable files under data/ aligned with the tutorial (load → split → embed → store).

        Includes: .vrl, .txt, .md, .json, .csv, .xlsx, .xls. Skips large binaries.
        """
        allow_ext = {".vrl", ".txt", ".md", ".json", ".csv", ".xlsx", ".xls"}
        for root, _dirs, files in os.walk(self.data_directory):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in allow_ext:
                    yield os.path.join(root, fname)

    def build_langchain_index(self) -> bool:
        """Create a LangChain index (Load → Split → Embed → Store) per v0.3 tutorial
        using local HuggingFace embeddings and Chroma, then expose the same
        persisted store through the existing chromadb client.
        """
        if not _LC_AVAILABLE:
            logger.warning("LangChain components not available; skipping LC index build")
            return False

        try:
            logger.info("Indexing data with LangChain (load → split → embed → store)...")

            # 1) Load: read all supported files, converting tabular (xlsx/csv) to JSON strings
            documents = []
            for path in self._iter_index_paths():
                try:
                    ext = os.path.splitext(path)[1].lower()
                    if ext in {".xlsx", ".xls"}:
                        # Convert Excel to JSONL-like string for embedding
                        df = pd.read_excel(path)
                        df.columns = [str(c).strip() for c in df.columns]
                        records = df.to_dict(orient="records")
                        content = json.dumps(records, ensure_ascii=False)
                        documents.append(Document(page_content=content, metadata={"source": path, "kind": "excel"}))
                    elif ext == ".csv":
                        df = pd.read_csv(path)
                        df.columns = [str(c).strip() for c in df.columns]
                        records = df.to_dict(orient="records")
                        content = json.dumps(records, ensure_ascii=False)
                        documents.append(Document(page_content=content, metadata={"source": path, "kind": "csv"}))
                    else:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        documents.append(Document(page_content=content, metadata={"source": path, "kind": "text"}))
                except Exception as e:
                    logger.debug(f"Skip non-text or unreadable file: {path} ({e})")
            if not documents:
                logger.warning("No documents loaded from data/ for indexing (allowed: .vrl,.txt,.md,.json,.csv)")

            # 2) Split - Smart chunks that understand line-by-line content
            chunks = []
            for doc in documents:
                lines = doc.page_content.split('\n')
                current_chunk_lines = []
                current_chunk_start = 0
                
                for i, line in enumerate(lines):
                    line = line.strip()
                    if not line:  # Skip empty lines
                        continue
                    
                    current_chunk_lines.append(line)
                    
                    # Create chunk when we have 3-5 lines or reach end of file
                    if len(current_chunk_lines) >= 3 or i == len(lines) - 1:
                        if current_chunk_lines:  # Only create chunk if we have content
                            chunk_content = '\n'.join(current_chunk_lines)
                            chunks.append(Document(
                                page_content=chunk_content,
                                metadata={
                                    **doc.metadata, 
                                    "start_line": current_chunk_start + 1,
                                    "end_line": current_chunk_start + len(current_chunk_lines),
                                    "line_count": len(current_chunk_lines),
                                    "chunk_type": "smart_line_grouping"
                                }
                            ))
                            current_chunk_start = i + 1
                            current_chunk_lines = []
            
            # Process ALL chunks - no limiting for complete coverage
            logger.info(f"Processing ALL {len(chunks)} chunks for complete knowledge base coverage")
            
            logger.info(f"Prepared {len(chunks)} line-by-line chunks for embedding")

            # 3) Embed (local, free)
            embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name, 
                                               encode_kwargs={"normalize_embeddings": True})

            # 4) Store using direct ChromaDB client (avoid LangChain Chroma conflicts)
            # Generate embeddings in batches to avoid memory issues
            batch_size = 1000  # Larger batch size for efficiency with all content
            embeddings_list = []
            
            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]
                batch_texts = [chunk.page_content for chunk in batch_chunks]
                batch_embeddings = embeddings.embed_documents(batch_texts)
                embeddings_list.extend(batch_embeddings)
                logger.info(f"Processed embedding batch {i//batch_size + 1}/{(len(chunks)-1)//batch_size + 1}")
            
            # Add to existing ChromaDB collection
            if not self.chroma_client:
                self.setup_chromadb()
            
            # Clear and recreate collection to avoid settings conflicts
            try:
                self.chroma_client.delete_collection("parser_knowledge_base")
            except:
                pass
            
            self.collection = self.chroma_client.create_collection(
                name="parser_knowledge_base",
                metadata={"source": "langchain_index"}
            )
            
            # Add documents with embeddings
            documents = [chunk.page_content for chunk in chunks]
            metadatas = [chunk.metadata for chunk in chunks]
            ids = [f"doc_{i}" for i in range(len(chunks))]
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings_list
            )

            logger.info("✅ LangChain index built and persisted")
            return True
        except Exception as e:
            logger.error(f"❌ LangChain index build failed: {e}")
            return False
    
    def setup_chromadb(self):
        """Setup ChromaDB client and collection"""
        try:
            logger.info("Setting up ChromaDB...")
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Create or get collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="log_parsing_knowledge",
                metadata={"description": "Log parsing knowledge base with VRL snippets, ECS fields, and examples"}
            )
            
            logger.info("✅ ChromaDB setup complete")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to setup ChromaDB: {str(e)}")
            return False
    
    def load_vendor_reference(self, xlsx_path: str = "data/all.xlsx", json_path: str = "data/all.json") -> bool:
        """Load vendor/product reference data.

        Preferred order: JSON (data/all.json) → XLSX (data/all.xlsx).
        This allows editing the JSON directly and avoids XLSX parser issues in
        minimal environments.
        """
        try:
            # Prefer JSON if available
            if os.path.exists(json_path):
                logger.info(f"Loading vendor reference from {json_path}")
                # Robust JSON load → DataFrame to avoid pandas orientation issues
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    # If dict of arrays, convert to rows
                    try:
                        self.vendor_reference = pd.DataFrame.from_dict(data)
                    except Exception:
                        self.vendor_reference = pd.json_normalize(data)
                elif isinstance(data, list):
                    self.vendor_reference = pd.DataFrame(data)
                else:
                    raise ValueError("Unsupported JSON format for vendor reference")
            else:
                logger.info(f"Loading vendor reference from {xlsx_path}")
                if not os.path.exists(xlsx_path):
                    logger.warning(f"Vendor reference file not found: {xlsx_path}")
                    # Create a sample file
                    self._create_sample_vendor_reference(xlsx_path)
                self.vendor_reference = pd.read_excel(xlsx_path)
                # Also export a JSON mirror for easier editing/indexing
                try:
                    os.makedirs(os.path.dirname(json_path), exist_ok=True)
                    self.vendor_reference.to_json(json_path, orient="records", indent=2)
                    logger.info(f"Exported vendor reference JSON to {json_path}")
                except Exception as export_err:
                    logger.debug(f"Could not export vendor JSON: {export_err}")
            self.vendor_reference.columns = [c.strip().lower() for c in self.vendor_reference.columns]
            
            logger.info(f"✅ Loaded {len(self.vendor_reference)} vendor references")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load vendor reference: {str(e)}")
            return False
    
    def _create_sample_vendor_reference(self, xlsx_path: str):
        """Create a sample vendor reference file"""
        sample_data = {
            'vendor': ['Cisco', 'Microsoft', 'Checkpoint', 'Fortinet', 'Palo Alto'],
            'product': ['ASA', 'Windows Security', 'Firewall', 'FortiGate', 'PAN-OS'],
            'log_type': ['security', 'security', 'firewall', 'firewall', 'firewall'],
            'format': ['syslog', 'windows_event', 'syslog', 'syslog', 'syslog']
        }
        
        df = pd.DataFrame(sample_data)
        os.makedirs(os.path.dirname(xlsx_path), exist_ok=True)
        df.to_excel(xlsx_path, index=False)
        logger.info(f"Created sample vendor reference: {xlsx_path}")
    
    def create_knowledge_base(self):
        """Create the knowledge base with VRL snippets, ECS fields, and examples"""
        try:
            logger.info("Creating knowledge base...")
            
            # Check if collection already has data
            if self.collection.count() > 0:
                logger.info(f"Knowledge base already exists with {self.collection.count()} documents")
                return True
            
            # Create knowledge base entries
            knowledge_entries = self._get_knowledge_entries()
            
            # Add to ChromaDB
            documents = []
            metadatas = []
            ids = []
            
            for i, entry in enumerate(knowledge_entries):
                documents.append(entry['content'])
                metadatas.append(entry['metadata'])
                ids.append(f"doc_{i}")
            
            # Generate embeddings and add to collection
            embeddings = self.embedding_model.encode(documents).tolist()
            
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
                embeddings=embeddings
            )
            
            logger.info(f"✅ Knowledge base created with {len(knowledge_entries)} entries")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create knowledge base: {str(e)}")
            return False
    
    def _get_knowledge_entries(self) -> List[Dict[str, Any]]:
        """Get knowledge base entries from data folder"""
        entries = []
        
        # Load VRL snippets from data folder
        vrl_snippets = self._load_vrl_snippets()
        entries.extend(vrl_snippets)
        
        # Load reference examples from data folder
        reference_examples = self._load_reference_examples()
        entries.extend(reference_examples)
        
        # Load log samples from data folder
        log_samples = self._load_log_samples()
        entries.extend(log_samples)

        # Load source list mappings (observer.type/vendor/product/log_type)
        source_mappings = self._load_source_list_mappings()
        entries.extend(source_mappings)
        
        # Add ECS fields
        ecs_fields = self._get_ecs_fields()
        entries.extend(ecs_fields)
        
        return entries
    
    def _load_vrl_snippets(self) -> List[Dict[str, Any]]:
        """Load VRL snippets from data/ folder and create field-based indexing"""
        entries = []
        
        # Load VRL snippets from data/ folder (your actual snippets)
        for filename in os.listdir(self.data_directory):
            if filename.endswith('.vrl'):
                filepath = os.path.join(self.data_directory, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Extract ECS fields from the VRL content for better indexing
                        ecs_fields = self._extract_ecs_fields_from_vrl(content)
                        
                        # Create main snippet entry
                        entries.append({
                            'content': f'VRL Snippet ({filename}): {content}',
                            'metadata': {
                                'type': 'vrl_snippet',
                                'file': filename,
                                'category': 'parsing',
                                'format': filename.replace('.vrl', ''),
                                'ecs_fields_count': len(ecs_fields),
                                'ecs_fields_str': ', '.join(ecs_fields[:10])  # Limit to first 10 fields
                            }
                        })
                        
                        # Create individual field entries for better searchability
                        for field in ecs_fields:
                            field_content = self._get_field_context_from_vrl(content, field)
                            entries.append({
                                'content': f'ECS Field {field} in {filename}: {field_content}',
                                'metadata': {
                                    'type': 'ecs_field_mapping',
                                    'field': field,
                                    'file': filename,
                                    'category': 'field_mapping',
                                    'format': filename.replace('.vrl', '')
                                }
                            })
                            
                except Exception as e:
                    logger.warning(f"Could not load VRL snippet {filename}: {e}")
        
        # Load snippets.jsonl if it exists
        snippets_file = os.path.join(self.data_directory, "snippets.jsonl")
        if os.path.exists(snippets_file):
            try:
                with open(snippets_file, 'r') as f:
                    for line in f:
                        if line.strip():
                            snippet = json.loads(line.strip())
                            entries.append({
                                'content': f'VRL Snippet: {snippet.get("snippet", "")}',
                                'metadata': {
                                    'type': 'vrl_snippet',
                                    'category': snippet.get('category', 'parsing'),
                                    'format': snippet.get('format', 'common')
                                }
                            })
            except Exception as e:
                logger.warning(f"Could not load snippets.jsonl: {e}")
        
        return entries

    def _load_source_list_mappings(self) -> List[Dict[str, Any]]:
        """Load observer/log source mappings from data/sourcelist.json and convert to RAG entries.

        Expected keys (best-effort, flexible):
          - observer.type (or 'log.type' / 'type')
          - observer.vendor (or 'lvendor' / 'vendor')
          - observer.product (or 'product')
          - log_type (or 'log.type')
          - category (optional)
          - log_source (optional)
        """
        entries: List[Dict[str, Any]] = []
        path = os.path.join(self.data_directory, "sourcelist.json")
        if not os.path.exists(path):
            return entries

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Normalize to list of dicts
            rows: List[Dict[str, Any]]
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                # If dict, try to interpret values as rows
                rows = data.get("rows") or data.get("items") or []
                if not isinstance(rows, list):
                    # Fallback: treat top-level dict as single row
                    rows = [data]
            else:
                rows = []

            for idx, row in enumerate(rows):
                # Flexible key accessors
                def _get(*keys: str) -> Any:
                    for k in keys:
                        if k in row and row[k] not in (None, "", []):
                            return row[k]
                    return None

                observer_type = _get("observer.type", "log.type", "type")
                vendor = _get("observer.vendor", "lvendor", "vendor")
                product = _get("observer.product", "product")
                log_type = _get("log_type", "log.type")
                log_source = _get("log_source", "source", "observer.product")
                category = _get("category", "event.category")

                # Build content string for embedding
                content_parts = [
                    f"Category: {category or 'unknown'}",
                    f"observer.type: {observer_type or 'unknown'}",
                    f"observer.vendor: {vendor or 'unknown'}",
                    f"observer.product: {product or 'unknown'}",
                    f"log_type: {log_type or 'unknown'}",
                    f"log_source: {log_source or 'unknown'}",
                ]
                content = " | ".join(content_parts)

                entries.append({
                    "content": f"Source Mapping: {content}",
                    "metadata": {
                        "type": "source_mapping",
                        "category": (category or "classification"),
                        "observer_type": observer_type or "unknown",
                        "vendor": vendor or "unknown",
                        "product": product or "unknown",
                        "log_type": log_type or "unknown",
                        "log_source": log_source or "unknown",
                        "file": "sourcelist.json",
                    }
                })

        except Exception as e:
            logger.warning(f"Could not load sourcelist.json: {e}")

        return entries
    
    def _extract_ecs_fields_from_vrl(self, vrl_content: str) -> List[str]:
        """Extract ECS fields from VRL content"""
        import re
        
        # Common ECS field patterns
        ecs_patterns = [
            r'\.source\.ip',
            r'\.destination\.ip', 
            r'\.host\.name',
            r'\.user\.name',
            r'\.event\.(?:kind|category|type|action|severity|description|created)',
            r'\.observer\.(?:type|vendor|product|hostname)',
            r'\.log\.(?:level|format|syslog)',
            r'\.url\.(?:original|path|query|domain)',
            r'\.http\.(?:request|response)',
            r'\.network\.(?:source|destination)',
            r'\.related\.(?:ip|user|hosts)',
            r'\.event_data\.',
            r'\.@timestamp'
        ]
        
        found_fields = set()
        for pattern in ecs_patterns:
            matches = re.findall(pattern, vrl_content)
            found_fields.update(matches)
        
        return list(found_fields)
    
    def _get_field_context_from_vrl(self, vrl_content: str, field: str) -> str:
        """Get context around a specific ECS field in VRL content"""
        lines = vrl_content.split('\n')
        context_lines = []
        
        for i, line in enumerate(lines):
            if field in line:
                # Get context (2 lines before and after)
                start = max(0, i - 2)
                end = min(len(lines), i + 3)
                context_lines.extend(lines[start:end])
                break
        
        return '\n'.join(context_lines)
    
    def _load_reference_examples(self) -> List[Dict[str, Any]]:
        """Load reference examples from data/reference_examples folder"""
        entries = []
        ref_examples_dir = os.path.join(self.data_directory, "reference_examples")
        
        if os.path.exists(ref_examples_dir):
            for filename in os.listdir(ref_examples_dir):
                if filename.endswith('.vrl'):
                    filepath = os.path.join(ref_examples_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                            # Extract vendor/product from filename
                            vendor_product = filename.replace('_professional.vrl', '').replace('.vrl', '')
                            entries.append({
                                'content': f'Reference VRL Example ({vendor_product}): {content}',
                                'metadata': {
                                    'type': 'reference_example',
                                    'file': filename,
                                    'vendor': vendor_product.split('_')[0] if '_' in vendor_product else vendor_product,
                                    'product': vendor_product,
                                    'category': 'reference'
                                }
                            })
                    except Exception as e:
                        logger.warning(f"Could not load reference example {filename}: {e}")
        
        return entries
    
    def _load_log_samples(self) -> List[Dict[str, Any]]:
        """Load log samples from data/log_samples folder"""
        entries = []
        log_samples_dir = os.path.join(self.data_directory, "log_samples")
        
        if os.path.exists(log_samples_dir):
            for filename in os.listdir(log_samples_dir):
                if filename.endswith('.txt'):
                    filepath = os.path.join(log_samples_dir, filename)
                    try:
                        with open(filepath, 'r') as f:
                            content = f.read()
                            # Extract vendor from filename
                            vendor = filename.replace('.txt', '').replace('_', ' ').title()
                            entries.append({
                                'content': f'Log Sample ({vendor}): {content[:500]}...',
                                'metadata': {
                                    'type': 'log_sample',
                                    'file': filename,
                                    'vendor': vendor,
                                    'category': 'sample'
                                }
                            })
                    except Exception as e:
                        logger.warning(f"Could not load log sample {filename}: {e}")
        
        return entries
    
    def _get_ecs_fields(self) -> List[Dict[str, Any]]:
        """Get ECS field definitions from data sources"""
        entries = []
        
        # Load VRL functions from vrl.json
        vrl_functions = self._load_vrl_functions()
        entries.extend(vrl_functions)
        
        # Add comprehensive ECS field mappings
        ecs_fields = [
            # Core fields
            {'content': 'ECS Field: @timestamp - Event timestamp in ISO format', 'metadata': {'type': 'ecs_field', 'field': '@timestamp', 'category': 'core'}},
            {'content': 'ECS Field: event.original - Original log message', 'metadata': {'type': 'ecs_field', 'field': 'event.original', 'category': 'event'}},
            {'content': 'ECS Field: event.created - Event creation timestamp', 'metadata': {'type': 'ecs_field', 'field': 'event.created', 'category': 'event'}},
            {'content': 'ECS Field: event.category - Event category (authentication, network, etc.)', 'metadata': {'type': 'ecs_field', 'field': 'event.category', 'category': 'event'}},
            {'content': 'ECS Field: event.action - Event action (login, logout, etc.)', 'metadata': {'type': 'ecs_field', 'field': 'event.action', 'category': 'event'}},
            {'content': 'ECS Field: event.outcome - Event outcome (success, failure)', 'metadata': {'type': 'ecs_field', 'field': 'event.outcome', 'category': 'event'}},
            
            # Source/Destination
            {'content': 'ECS Field: source.ip - Source IP address', 'metadata': {'type': 'ecs_field', 'field': 'source.ip', 'category': 'source'}},
            {'content': 'ECS Field: source.port - Source port number', 'metadata': {'type': 'ecs_field', 'field': 'source.port', 'category': 'source'}},
            {'content': 'ECS Field: source.domain - Source domain name', 'metadata': {'type': 'ecs_field', 'field': 'source.domain', 'category': 'source'}},
            {'content': 'ECS Field: destination.ip - Destination IP address', 'metadata': {'type': 'ecs_field', 'field': 'destination.ip', 'category': 'destination'}},
            {'content': 'ECS Field: destination.port - Destination port number', 'metadata': {'type': 'ecs_field', 'field': 'destination.port', 'category': 'destination'}},
            {'content': 'ECS Field: destination.domain - Destination domain name', 'metadata': {'type': 'ecs_field', 'field': 'destination.domain', 'category': 'destination'}},
            
            # User
            {'content': 'ECS Field: user.name - Username', 'metadata': {'type': 'ecs_field', 'field': 'user.name', 'category': 'user'}},
            {'content': 'ECS Field: user.id - User ID', 'metadata': {'type': 'ecs_field', 'field': 'user.id', 'category': 'user'}},
            {'content': 'ECS Field: user.email - User email address', 'metadata': {'type': 'ecs_field', 'field': 'user.email', 'category': 'user'}},
            
            # Host
            {'content': 'ECS Field: host.name - Hostname or IP address', 'metadata': {'type': 'ecs_field', 'field': 'host.name', 'category': 'host'}},
            {'content': 'ECS Field: host.ip - Host IP address', 'metadata': {'type': 'ecs_field', 'field': 'host.ip', 'category': 'host'}},
            {'content': 'ECS Field: host.os.name - Operating system name', 'metadata': {'type': 'ecs_field', 'field': 'host.os.name', 'category': 'host'}},
            
            # Process
            {'content': 'ECS Field: process.name - Process name', 'metadata': {'type': 'ecs_field', 'field': 'process.name', 'category': 'process'}},
            {'content': 'ECS Field: process.pid - Process ID', 'metadata': {'type': 'ecs_field', 'field': 'process.pid', 'category': 'process'}},
            {'content': 'ECS Field: process.command_line - Process command line', 'metadata': {'type': 'ecs_field', 'field': 'process.command_line', 'category': 'process'}},
            
            # Network
            {'content': 'ECS Field: network.protocol - Network protocol (tcp, udp, etc.)', 'metadata': {'type': 'ecs_field', 'field': 'network.protocol', 'category': 'network'}},
            {'content': 'ECS Field: network.transport - Network transport (tcp, udp)', 'metadata': {'type': 'ecs_field', 'field': 'network.transport', 'category': 'network'}},
            {'content': 'ECS Field: network.bytes - Network bytes transferred', 'metadata': {'type': 'ecs_field', 'field': 'network.bytes', 'category': 'network'}},
            
            # HTTP
            {'content': 'ECS Field: http.request.method - HTTP request method', 'metadata': {'type': 'ecs_field', 'field': 'http.request.method', 'category': 'http'}},
            {'content': 'ECS Field: http.request.url - HTTP request URL', 'metadata': {'type': 'ecs_field', 'field': 'http.request.url', 'category': 'http'}},
            {'content': 'ECS Field: http.response.status_code - HTTP response status code', 'metadata': {'type': 'ecs_field', 'field': 'http.response.status_code', 'category': 'http'}},
            
            # Observer
            {'content': 'ECS Field: observer.vendor - Observer vendor name', 'metadata': {'type': 'ecs_field', 'field': 'observer.vendor', 'category': 'observer'}},
            {'content': 'ECS Field: observer.product - Observer product name', 'metadata': {'type': 'ecs_field', 'field': 'observer.product', 'category': 'observer'}},
            {'content': 'ECS Field: observer.type - Observer type (firewall, proxy, etc.)', 'metadata': {'type': 'ecs_field', 'field': 'observer.type', 'category': 'observer'}},
            
            # Related
            {'content': 'ECS Field: related.ip - Related IP addresses', 'metadata': {'type': 'ecs_field', 'field': 'related.ip', 'category': 'related'}},
            {'content': 'ECS Field: related.user - Related usernames', 'metadata': {'type': 'ecs_field', 'field': 'related.user', 'category': 'related'}},
            
            # Message
            {'content': 'ECS Field: message - Log message content', 'metadata': {'type': 'ecs_field', 'field': 'message', 'category': 'message'}},
        ]
        
        entries.extend(ecs_fields)
        return entries
    
    def _load_vrl_functions(self) -> List[Dict[str, Any]]:
        """Load VRL functions from vrl.json"""
        entries = []
        vrl_json_path = os.path.join(self.data_directory, "vrl.json")
        
        if os.path.exists(vrl_json_path):
            try:
                with open(vrl_json_path, 'r') as f:
                    vrl_functions = json.load(f)
                
                for func in vrl_functions:
                    function_name = func.get('function_name', '')
                    description = func.get('description', '')
                    function_spec = func.get('function_spec', '')
                    
                    # Create comprehensive entry
                    content = f"VRL Function: {function_name} - {description}\nSpecification: {function_spec}"
                    
                    entries.append({
                        'content': content,
                        'metadata': {
                            'type': 'vrl_function',
                            'function_name': function_name,
                            'category': 'parsing',
                            'format': 'common'
                        }
                    })
                    
            except Exception as e:
                logger.warning(f"Could not load vrl.json: {e}")
        
        return entries
    
    def query_rag(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Query the RAG system"""
        try:
            if not self.embedding_model or not self.collection:
                raise Exception("RAG system not initialized")
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ RAG query failed: {str(e)}")
            return []
    
    def search_ecs_field(self, field_name: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for specific ECS field mappings"""
        try:
            if not self.embedding_model or not self.collection:
                raise Exception("RAG system not initialized")
            
            # Create field-specific query
            field_query = f"ECS field {field_name} mapping VRL"
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([field_query]).tolist()[0]
            
            # Query ChromaDB with field-specific filtering
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances'],
                where={"type": {"$in": ["ecs_field_mapping", "vrl_snippet"]}}
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                metadata = results['metadatas'][0][i]
                # Prioritize results that contain the specific field
                if field_name in results['documents'][0][i]:
                    formatted_results.append({
                        'content': results['documents'][0][i],
                        'metadata': metadata,
                        'distance': results['distances'][0][i],
                        'relevance': 'high' if metadata.get('type') == 'ecs_field_mapping' else 'medium'
                    })
            
            # Sort by relevance and distance
            formatted_results.sort(key=lambda x: (x['relevance'] == 'high', -x['distance']))
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ ECS field search failed: {str(e)}")
            return []
    
    def search_vrl_snippets(self, query: str, format_type: str = None, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search VRL snippets with optional format filtering"""
        try:
            if not self.embedding_model or not self.collection:
                raise Exception("RAG system not initialized")
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Build where clause
            where_clause = {"type": "vrl_snippet"}
            if format_type:
                where_clause["format"] = format_type
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances'],
                where=where_clause
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['documents'][0])):
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i]
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ VRL snippet search failed: {str(e)}")
            return []
    
    def build_context_for_log(self, log_profile: Dict[str, Any]) -> str:
        """Build context for a log profile using RAG"""
        try:
            # Create query from log profile
            query_parts = []
            if log_profile.get('log_type'):
                query_parts.append(f"log type {log_profile['log_type']}")
            if log_profile.get('log_format'):
                query_parts.append(f"format {log_profile['log_format']}")
            if log_profile.get('vendor'):
                query_parts.append(f"vendor {log_profile['vendor']}")
            if log_profile.get('product'):
                query_parts.append(f"product {log_profile['product']}")
            
            query = " ".join(query_parts)
            
            # Query RAG system
            results = self.query_rag(query, n_results=10)
            
            # Build context
            context_parts = []
            for result in results:
                content = result['content']
                metadata = result['metadata']
                
                # Safe key access with fallback
                doc_type = metadata.get('type', 'unknown')
                
                if doc_type == 'vrl_snippet':
                    context_parts.append(f"VRL Snippet: {content}")
                elif doc_type == 'ecs_field':
                    context_parts.append(f"ECS Field: {content}")
                elif doc_type == 'log_example':
                    context_parts.append(f"Example: {content}")
                else:
                    # Fallback for unknown types
                    context_parts.append(f"Reference: {content}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"❌ Context building failed: {str(e)}")
            return f"Error building context: {str(e)}"
    
    def initialize_system(self) -> bool:
        """Initialize the complete RAG system"""
        try:
            logger.info("🚀 Initializing complete RAG system...")
            
            # Step 1: Setup embedding model
            if not self.setup_embedding_model():
                return False
            
            # Step 2: Setup ChromaDB (for direct client access)
            if not self.setup_chromadb():
                return False
            
            # Step 3: Load vendor reference
            if not self.load_vendor_reference():
                return False
            
            # Step 4: Build LangChain index per tutorial; fall back to legacy path
            if not self.build_langchain_index():
                logger.info("Falling back to legacy create_knowledge_base() indexing")
                if not self.create_knowledge_base():
                    return False
            
            logger.info("✅ Complete RAG system initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ System initialization failed: {str(e)}")
            return False
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        status = {
            'embedding_model': self.embedding_model is not None,
            'chromadb': self.chroma_client is not None,
            'collection': self.collection is not None,
            'vendor_reference': self.vendor_reference is not None,
            'knowledge_base_size': self.collection.count() if self.collection else 0
        }
        return status
    
    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """General search method for the RAG system"""
        try:
            if not self.embedding_model or not self.collection:
                logger.warning("RAG system not properly initialized")
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Search the collection
            results = self.collection.query(
                query_embeddings=query_embedding.tolist(),
                n_results=k,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'page_content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0
                    })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []


# Streamlit integration
@st.cache_resource
def get_rag_system() -> CompleteRAGSystem:
    """Get cached RAG system instance"""
    return CompleteRAGSystem()


def render_rag_setup():
    """Render RAG system setup in Streamlit"""
    st.subheader("🧠 RAG System Setup")
    
    # Initialize RAG system
    if "rag_system" not in st.session_state:
        st.session_state.rag_system = get_rag_system()
    
    rag_system = st.session_state.rag_system
    
    # System status
    status = rag_system.get_system_status()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Embedding Model", "✅ Ready" if status['embedding_model'] else "❌ Not Ready")
    
    with col2:
        st.metric("ChromaDB", "✅ Ready" if status['chromadb'] else "❌ Not Ready")
    
    with col3:
        st.metric("Knowledge Base", f"{status['knowledge_base_size']} entries")
    
    # Initialize button
    if not all([status['embedding_model'], status['chromadb'], status['collection']]):
        if st.button("🚀 Initialize RAG System"):
            with st.spinner("Initializing RAG system..."):
                if rag_system.initialize_system():
                    st.success("✅ RAG system initialized successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to initialize RAG system")
    
    # Test RAG system
    if all([status['embedding_model'], status['chromadb'], status['collection']]):
        st.subheader("🧪 Test RAG System")
        
        test_query = st.text_input("Test Query", "Cisco ASA syslog parsing")
        
        if st.button("🔍 Query RAG"):
            results = rag_system.query_rag(test_query, n_results=3)
            
            if results:
                st.success(f"Found {len(results)} relevant results:")
                for i, result in enumerate(results):
                    with st.expander(f"Result {i+1} (Distance: {result['distance']:.3f})"):
                        st.write(f"**Content:** {result['content']}")
                        st.write(f"**Metadata:** {result['metadata']}")
            else:
                st.warning("No results found")
    
    return rag_system
