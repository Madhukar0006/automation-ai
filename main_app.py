"""
AI-Powered Log Parser with RAG System
Complete integration of RAG, embeddings, and intelligent agents for automated log parsing
"""

import os
import re
import json
import subprocess
import tempfile
from typing import Dict, Any, List
import streamlit as st
import pandas as pd
from datetime import datetime, timezone

# Import our modules
from complete_rag_system import CompleteRAGSystem, render_rag_setup
from simple_agent import SimpleLogParsingAgent, create_simple_agent
from lc_bridge import classify_log_lc, generate_ecs_json_lc, generate_vrl_lc
from log_analyzer import identify_log_type
from vrl_error_integration import VRL_Error_Integration

# =========================
# Streamlit Settings
# =========================
st.set_page_config(
    page_title=" AI Log Parser - Complete System", 
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Custom CSS for Better UI
# =========================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .status-card {
        background: #e8f5e8;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #4caf50;
    }
    
    .error-card {
        background: #ffebee;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #f44336;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    
    .log-input {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 8px;
        padding: 1rem;
    }
    
    .result-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .step-indicator {
        display: flex;
        justify-content: space-between;
        margin: 2rem 0;
    }
    
    .step {
        background: #e9ecef;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
    }
    
    .step.active {
        background: #667eea;
        color: white;
    }
    
    .step.completed {
        background: #28a745;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# Initialize Session State
# =========================
if "rag_system" not in st.session_state:
    st.session_state.rag_system = None

if "agent" not in st.session_state:
    st.session_state.agent = None

if "current_mode" not in st.session_state:
    st.session_state.current_mode = "rag_setup"

# =========================
# Helpers
# =========================
def _normalize_profile_for_display(profile: Dict[str, Any]) -> Dict[str, Any]:
    try:
        normalized = dict(profile or {})
        lf = normalized.get("log_format")
        if isinstance(lf, str):
            normalized["log_format"] = lf.lower()
        return normalized
    except Exception:
        return profile

# =========================
# Main Application
# =========================

def main():
    # Main Header with React-like styling
    st.markdown("""
    <div class="main-header">
        <h1>🧠 AI-Powered Log Parser</h1>
        <p>Complete RAG System with Intelligent Agents for Automated Log Parsing</p>
        <div style="margin-top: 1rem;">
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem;">
                🔍 Log Classification
            </span>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem;">
                📊 ECS JSON Generation
            </span>
            <span style="background: rgba(255,255,255,0.2); padding: 0.5rem 1rem; border-radius: 20px; margin: 0 0.5rem;">
                ⚙️ VRL Parser Creation
            </span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # React-like Navigation Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏠 Dashboard", 
        "🔧 RAG Setup", 
        "🤖 Agent Parser", 
        "📊 Classic Parser", 
        "🧪 Test Suite"
    ])
    
    with tab1:
        render_dashboard()
    
    with tab2:
        render_rag_setup_mode()
    
    with tab3:
        render_agent_mode()
    
    with tab4:
        render_classic_mode()
    
    with tab5:
        render_test_mode()
    
    # Enhanced Sidebar with System Status
    with st.sidebar:
        st.markdown("### 🎛️ System Control")
        
        # Quick Actions
        st.markdown("#### ⚡ Quick Actions")
        if st.button("🚀 Initialize System", use_container_width=True, type="primary"):
            if st.session_state.rag_system is None:
                st.session_state.rag_system = CompleteRAGSystem()
            if st.session_state.rag_system.initialize_system():
                st.success("✅ System Ready!")
                st.rerun()
            else:
                st.error("❌ Initialization Failed")
        
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
        
        st.markdown("---")
        
        # System Status Dashboard
        st.markdown("#### 📊 System Status")
        if st.session_state.rag_system:
            status = st.session_state.rag_system.get_system_status()
            
            # Status Cards
            st.markdown(f"""
            <div class="status-card">
                <strong>🧠 Knowledge Base</strong><br>
                {status['knowledge_base_size']} entries
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="status-card">
                <strong>🤖 Embedding Model</strong><br>
                {'✅ Ready' if status['embedding_model'] else '❌ Not Ready'}
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="status-card">
                <strong>🗄️ ChromaDB</strong><br>
                {'✅ Connected' if status['chromadb'] else '❌ Disconnected'}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("⚠️ System not initialized")
        
        st.markdown("---")
        
        # Quick Stats
        st.markdown("#### 📈 Quick Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Logs Processed", "0", "0")
        with col2:
            st.metric("Success Rate", "0%", "0%")
        
        st.markdown("---")
        
        # Help Section
        st.markdown("#### ❓ Help")
        with st.expander("How to Use"):
            st.markdown("""
            1. **Initialize System** - Set up RAG and embeddings
            2. **Choose Parser** - Agent or Classic mode
            3. **Paste Log** - Enter your log line
            4. **Get Results** - View classification, JSON, and VRL
            """)
        
        with st.expander("Supported Log Types"):
            st.markdown("""
            - **Syslog** (Cisco, Juniper, etc.)
            - **JSON Logs** (Application logs)
            - **Windows Events** (Security, System)
            - **Apache/Nginx** (Web server logs)
            - **Custom Formats**
            """)


def render_dashboard():
    """Render main dashboard with overview and quick actions"""
    st.markdown("### 🏠 System Dashboard")
    
    # System Overview Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <h3>🔍</h3>
            <h2>Log Classification</h2>
            <p>AI-powered log type identification</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <h3>📊</h3>
            <h2>ECS JSON</h2>
            <p>Elastic Common Schema mapping</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-card">
            <h3>⚙️</h3>
            <h2>VRL Parser</h2>
            <p>Vector Remap Language generation</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-card">
            <h3>🤖</h3>
            <h2>AI Agents</h2>
            <p>Multi-agent collaboration</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Start Section
    st.markdown("### 🚀 Quick Start")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h4>🎯 One-Click Log Parsing</h4>
            <p>Paste any log line and get instant classification, ECS JSON, and VRL parser code.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if st.button("🚀 Start Parsing", type="primary", use_container_width=True):
            st.session_state.current_mode = "agent_mode"
            st.rerun()
    
    # Sample Logs Section
    st.markdown("### 📝 Sample Logs to Try")
    
    sample_logs = [
        {
            "name": "Cisco ASA Firewall",
            "log": "%ASA-6-302013: Built outbound TCP connection 12345 for outside:10.0.0.1/80 to inside:192.168.1.100/45678",
            "type": "syslog"
        },
        {
            "name": "JSON Application Log",
            "log": '{"timestamp":"2025-01-01T12:34:56Z","level":"INFO","message":"User login successful","user":"alice","ip":"10.0.0.1"}',
            "type": "json"
        },
        {
            "name": "Windows Security Event",
            "log": "Event ID 4624: An account was successfully logged on. Account Name: alice, Source Network Address: 10.0.0.1",
            "type": "windows_event"
        }
    ]
    
    for i, sample in enumerate(sample_logs):
        with st.expander(f"📋 {sample['name']} ({sample['type']})"):
            st.code(sample['log'], language="text")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button(f"🔍 Classify {i+1}", key=f"classify_{i}"):
                    st.session_state.sample_log = sample['log']
                    st.session_state.current_mode = "agent_mode"
                    st.rerun()
            with col2:
                if st.button(f"📊 JSON {i+1}", key=f"json_{i}"):
                    st.session_state.sample_log = sample['log']
                    st.session_state.current_mode = "classic_mode"
                    st.rerun()
            with col3:
                if st.button(f"⚙️ VRL {i+1}", key=f"vrl_{i}"):
                    st.session_state.sample_log = sample['log']
                    st.session_state.current_mode = "classic_mode"
                    st.rerun()
    
    # System Requirements
    st.markdown("### 📋 System Requirements")
    
    requirements = [
        "✅ Python 3.11+",
        "✅ Ollama with Llama 3.2",
        "✅ ChromaDB for vector storage",
        "✅ Sentence Transformers for embeddings",
        "✅ LangChain for LLM integration",
        "✅ Streamlit for UI",
        "✅ Vector CLI for VRL testing"
    ]
    
    col1, col2 = st.columns(2)
    with col1:
        for req in requirements[:4]:
            st.markdown(f"**{req}**")
    with col2:
        for req in requirements[4:]:
            st.markdown(f"**{req}**")


def render_rag_setup_mode():
    """Render RAG system setup"""
    st.header("🔧 RAG System Setup")
    
    # Initialize RAG system
    if st.session_state.rag_system is None:
        st.session_state.rag_system = CompleteRAGSystem()
    
    rag_system = st.session_state.rag_system
    
    # System status
    status = rag_system.get_system_status()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Embedding Model", "✅ Ready" if status['embedding_model'] else "❌ Not Ready")
    
    with col2:
        st.metric("ChromaDB", "✅ Ready" if status['chromadb'] else "❌ Not Ready")
    
    with col3:
        st.metric("Collection", "✅ Ready" if status['collection'] else "❌ Not Ready")
    
    with col4:
        st.metric("Knowledge Base", f"{status['knowledge_base_size']} entries")
    
    # Initialize button
    if not all([status['embedding_model'], status['chromadb'], status['collection']]):
        if st.button("🚀 Initialize Complete RAG System", type="primary"):
            with st.spinner("Initializing RAG system (this may take a few minutes for first-time setup)..."):
                if rag_system.initialize_system():
                    st.success("✅ RAG system initialized successfully!")
                    st.rerun()
                else:
                    st.error("❌ Failed to initialize RAG system")
    
    # Test RAG system
    if all([status['embedding_model'], status['chromadb'], status['collection']]):
        st.subheader("🧪 Test RAG System")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            test_query = st.text_input("Test Query", "Cisco ASA syslog parsing")
        
        with col2:
            n_results = st.number_input("Results", min_value=1, max_value=10, value=5)
        
        if st.button("🔍 Query RAG System"):
            results = rag_system.query_rag(test_query, n_results=n_results)
            
            if results:
                st.success(f"Found {len(results)} relevant results:")
                for i, result in enumerate(results):
                    with st.expander(f"Result {i+1} (Distance: {result['distance']:.3f})"):
                        st.write(f"**Content:** {result['content']}")
                        st.write(f"**Metadata:** {result['metadata']}")
            else:
                st.warning("No results found")


def render_agent_mode():
    """Render agent-based parsing mode with React-like UI"""
    st.markdown("### 🤖 AI Agent Log Parser")
    st.markdown("**Multi-agent system for intelligent log parsing with RAG context**")
    
    if st.session_state.rag_system is None:
        st.markdown("""
        <div class="error-card">
            <h4>⚠️ System Not Initialized</h4>
            <p>Please initialize the RAG system first in the RAG Setup tab or use the Quick Actions in the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Initialize agent
    if st.session_state.agent is None:
        st.session_state.agent = create_simple_agent(
            st.session_state.rag_system.build_context_for_log
        )
    
    agent = st.session_state.agent
    
    # Configuration Panel
    st.markdown("### ⚙️ Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        output_type = st.selectbox(
            "Output Type",
            ["auto", "json", "vrl"],
            format_func=lambda x: {
                "auto": "🔍 Auto-detect",
                "json": "📊 ECS JSON only", 
                "vrl": "⚙️ VRL Parser only"
            }[x]
        )
    
    with col2:
        streaming_mode = st.checkbox("📡 Streaming Mode", help="Show real-time processing steps")
    
    with col3:
        show_context = st.checkbox("📚 Show RAG Context", value=True, help="Display retrieved context from knowledge base")
    
    st.markdown("---")
    
    # Log Input Section
    st.markdown("### 📝 Log Input")
    
    # Pre-fill with sample log if available
    default_log = st.session_state.get('sample_log', '')
    
    raw_log = st.text_area(
        "Raw Log Input",
        value=default_log,
        placeholder="Paste your log line here...\n\nExamples:\n• %ASA-6-302013: Built outbound TCP connection...\n• {\"timestamp\":\"2025-01-01T12:34:56Z\",\"level\":\"INFO\"...}\n• Event ID 4624: An account was successfully logged on...",
        height=120,
        key="agent_raw_log_input",
        help="Enter any log line - the AI will automatically identify the type and generate appropriate parsers"
    )
    
    # Quick Sample Buttons
    st.markdown("**Quick Samples:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔥 Cisco ASA", use_container_width=True):
            st.session_state.agent_raw_log_input = "%ASA-6-302013: Built outbound TCP connection 12345 for outside:10.0.0.1/80 to inside:192.168.1.100/45678"
            st.rerun()
    
    with col2:
        if st.button("📄 JSON Log", use_container_width=True):
            st.session_state.agent_raw_log_input = '{"timestamp":"2025-01-01T12:34:56Z","level":"INFO","message":"User login successful","user":"alice","ip":"10.0.0.1"}'
            st.rerun()
    
    with col3:
        if st.button("🪟 Windows Event", use_container_width=True):
            st.session_state.agent_raw_log_input = "Event ID 4624: An account was successfully logged on. Account Name: alice, Source Network Address: 10.0.0.1"
            st.rerun()
    
    with col4:
        if st.button("🌐 Apache Log", use_container_width=True):
            st.session_state.agent_raw_log_input = '192.168.0.5 - - [03/Sep/2025:14:25:33 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"'
            st.rerun()
    
    st.markdown("---")
    
    # Parse Button and Results
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Parse with AI Agents", type="primary", use_container_width=True):
            if not raw_log.strip():
                st.warning("⚠️ Please enter a log line to parse")
                return
            
            # Process with agent (pre-hint with log_analyzer)
            if streaming_mode:
                render_streaming_results(agent, raw_log, output_type, show_context)
            else:
                render_regular_results(agent, raw_log, output_type, show_context)


def render_streaming_results(agent, raw_log, output_type, show_context):
    """Render streaming results with React-like progress indicators"""
    st.markdown("### 🔄 Agent Execution Stream")
    
    # Progress indicator
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    step_count = 0
    total_steps = 5  # Estimated steps
    
    try:
        for step_result in agent.stream_parse(raw_log, output_type):
            step_count += 1
            progress = min(step_count / total_steps, 1.0)
            progress_bar.progress(progress)
            
            if "error" in step_result:
                st.markdown(f"""
                <div class="error-card">
                    <h4>❌ Error in {step_result['step']}</h4>
                    <p>{step_result['error']}</p>
                </div>
                """, unsafe_allow_html=True)
                break
            
            status_text.text(f"🔄 {step_result['step']}...")
            
            # Show step results (normalize display)
            if "log_profile" in step_result:
                st.markdown("#### 🔍 Log Profile Identified")
                st.json(_normalize_profile_for_display(step_result["log_profile"]))
            
            if "context" in step_result and show_context:
                with st.expander("📚 RAG Context Retrieved"):
                    st.text(step_result["context"])
            
            if "final_output" in step_result:
                status_text.text("✅ Processing Complete!")
                progress_bar.progress(1.0)
                
                # Use classic-mode generators for final output to ensure correctness
                try:
                    # Build context using RAG and LLM classification
                    detected_profile = step_result.get("log_profile") or classify_log_lc(raw_log)
                    context_text = st.session_state.rag_system.build_context_for_log(detected_profile)

                    st.markdown("#### 🎯 Final Output (Classic pipeline)")
                    if output_type == "json":
                        classic_json = generate_ecs_json_lc(context_text, raw_log)
                        st.json(classic_json)
                    else:
                        vrl_integration = VRL_Error_Integration()
                        vrl_res = vrl_integration.generate_vrl_with_error_handling(context_text, raw_log)
                        final_vrl = vrl_res.get("vrl_code", step_result["final_output"])
                        # Persistent editor (Agent - streaming)
                        if "agent_current_vrl_code" not in st.session_state:
                            st.session_state.agent_current_vrl_code = final_vrl
                        st.markdown("##### Editor")
                        agent_stream_vrl = st.text_area(
                            "Edit VRL Parser:",
                            value=st.session_state.agent_current_vrl_code,
                            height=420,
                            key="agent_stream_vrl_editor"
                        )
                        a_s_apply, a_s_save, a_s_test = st.columns([1, 1, 1])
                        with a_s_apply:
                            if st.button("✅ Apply", use_container_width=True, key="agent_stream_apply"):
                                st.session_state.agent_current_vrl_code = agent_stream_vrl
                                st.success("Applied changes to current VRL.")
                        with a_s_save:
                            a_s_name = st.text_input("Filename (data/parsers/)", value="agent_parser_stream.vrl", key="agent_stream_save_name")
                            if st.button("💾 Save to .vrl", use_container_width=True, key="agent_stream_save"):
                                import os
                                target_dir = os.path.join("data", "parsers")
                                os.makedirs(target_dir, exist_ok=True)
                                name = a_s_name.strip() or "agent_parser_stream.vrl"
                                if not name.endswith(".vrl"):
                                    name += ".vrl"
                                path = os.path.join(target_dir, name)
                                with open(path, "w", encoding="utf-8") as f:
                                    f.write(st.session_state.agent_current_vrl_code)
                                st.success(f"Saved to {path}")
                        with a_s_test:
                            if st.button("🧪 Test VRL with Vector CLI", use_container_width=True, key="agent_stream_test"):
                                test_vrl_with_vector(st.session_state.agent_current_vrl_code)
                except Exception as e:
                    st.warning(f"Classic pipeline fallback failed: {str(e)}")
    
    except Exception as e:
        st.error(f"❌ Streaming error: {str(e)}")


def render_regular_results(agent, raw_log, output_type, show_context):
    """Render regular results with React-like cards"""
    with st.spinner("🤖 AI agents are analyzing and parsing the log..."):
        result = agent.parse_log(raw_log, output_type)
        
        if result["success"]:
            st.markdown("""
            <div class="status-card">
                <h4>✅ Agent Parsing Completed Successfully!</h4>
                <p>All AI agents have successfully processed your log.</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Execution Steps
            with st.expander("📋 Execution Steps", expanded=False):
                for i, step in enumerate(result["steps"], 1):
                    st.markdown(f"**{i}.** {step}")
            
            # Log Profile Section (normalize display)
            if "log_profile" in result:
                st.markdown("#### 🔍 Identified Log Profile")
                st.markdown("""
                <div class="result-section">
                """, unsafe_allow_html=True)
                st.json(_normalize_profile_for_display(result["log_profile"]))
                st.markdown("</div>", unsafe_allow_html=True)
            
            # RAG Context Section
            if "context" in result and show_context:
                with st.expander("📚 RAG Context Retrieved", expanded=False):
                    st.text(result["context"])
            
            # Final Output Section (force classic pipeline for correctness)
            st.markdown("#### 🎯 Final Output")
            st.markdown("""
            <div class="result-section">
            """, unsafe_allow_html=True)
            
            try:
                # Build context using RAG and LLM classification
                detected_profile = result.get("log_profile") or classify_log_lc(raw_log)
                context_text = st.session_state.rag_system.build_context_for_log(detected_profile)

                if output_type == "json":
                    classic_json = generate_ecs_json_lc(context_text, raw_log)
                    st.json(classic_json)
                else:
                    vrl_integration = VRL_Error_Integration()
                    vrl_res = vrl_integration.generate_vrl_with_error_handling(context_text, raw_log)
                    final_vrl = vrl_res.get("vrl_code", result.get("final_output", ""))
                    # Persistent editor (Agent - regular)
                    if "agent_current_vrl_code" not in st.session_state:
                        st.session_state.agent_current_vrl_code = final_vrl
                    st.markdown("##### Editor")
                    agent_reg_vrl = st.text_area(
                        "Edit VRL Parser:",
                        value=st.session_state.agent_current_vrl_code,
                        height=420,
                        key="agent_regular_vrl_editor"
                    )
                    a_r_apply, a_r_save, a_r_test = st.columns([1, 1, 1])
                    with a_r_apply:
                        if st.button("✅ Apply", use_container_width=True, key="agent_regular_apply"):
                            st.session_state.agent_current_vrl_code = agent_reg_vrl
                            st.success("Applied changes to current VRL.")
                    with a_r_save:
                        a_r_name = st.text_input("Filename (data/parsers/)", value="agent_parser.vrl", key="agent_regular_save_name")
                        if st.button("💾 Save to .vrl", use_container_width=True, key="agent_regular_save"):
                            import os
                            target_dir = os.path.join("data", "parsers")
                            os.makedirs(target_dir, exist_ok=True)
                            name = a_r_name.strip() or "agent_parser.vrl"
                            if not name.endswith(".vrl"):
                                name += ".vrl"
                            path = os.path.join(target_dir, name)
                            with open(path, "w", encoding="utf-8") as f:
                                f.write(st.session_state.agent_current_vrl_code)
                            st.success(f"Saved to {path}")
                    with a_r_test:
                        if st.button("🧪 Test VRL with Vector CLI", use_container_width=True, key="agent_regular_test"):
                            test_vrl_with_vector(st.session_state.agent_current_vrl_code)
            except Exception as e:
                st.error(f"Final output generation failed: {str(e)}")
            
            st.markdown("</div>", unsafe_allow_html=True)
            
        else:
            st.markdown(f"""
            <div class="error-card">
                <h4>❌ Agent Parsing Failed</h4>
                <p>{result['error']}</p>
            </div>
            """, unsafe_allow_html=True)


def render_classic_mode():
    """Render classic parsing mode with React-like UI"""
    st.markdown("### 📊 Classic Log Parser")
    st.markdown("**Traditional step-by-step log parsing with RAG context**")
    
    if st.session_state.rag_system is None:
        st.markdown("""
        <div class="error-card">
            <h4>⚠️ System Not Initialized</h4>
            <p>Please initialize the RAG system first in the RAG Setup tab or use the Quick Actions in the sidebar.</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # Log Input Section
    st.markdown("### 📝 Log Input")
    
    # Pre-fill with sample log if available
    default_log = st.session_state.get('sample_log', '')
    
    raw_log = st.text_area(
        "Raw Log Input",
        value=default_log,
        placeholder="Enter your log line here...",
        height=100,
        key="classic_raw_log_input",
        help="Enter any log line for step-by-step parsing"
    )
    
    # Quick Sample Buttons
    st.markdown("**Quick Samples:**")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔥 Cisco ASA", key="classic_cisco"):
            st.session_state.classic_raw_log_input = "%ASA-6-302013: Built outbound TCP connection 12345 for outside:10.0.0.1/80 to inside:192.168.1.100/45678"
            st.rerun()
    
    with col2:
        if st.button("📄 JSON Log", key="classic_json"):
            st.session_state.classic_raw_log_input = '{"timestamp":"2025-01-01T12:34:56Z","level":"INFO","message":"User login successful","user":"alice","ip":"10.0.0.1"}'
            st.rerun()
    
    with col3:
        if st.button("🪟 Windows Event", key="classic_windows"):
            st.session_state.classic_raw_log_input = "Event ID 4624: An account was successfully logged on. Account Name: alice, Source Network Address: 10.0.0.1"
            st.rerun()
    
    with col4:
        if st.button("🌐 Apache Log", key="classic_apache"):
            st.session_state.classic_raw_log_input = '192.168.0.5 - - [03/Sep/2025:14:25:33 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0"'
            st.rerun()
    
    st.markdown("---")
    
    # Processing Steps
    st.markdown("### 🔄 Processing Steps")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Step 1: Identify Log Type", use_container_width=True, type="primary"):
            if raw_log.strip():
                render_log_identification(raw_log)
            else:
                st.warning("⚠️ Please enter a log line")
    
    with col2:
        if st.button("📋 Step 2: Generate ECS JSON", use_container_width=True):
            if raw_log.strip():
                render_ecs_generation(raw_log)
            else:
                st.warning("⚠️ Please enter a log line")
    
    with col3:
        if st.button("⚙️ Step 3: Generate VRL Parser", use_container_width=True):
            if raw_log.strip():
                render_vrl_generation(raw_log)
            else:
                st.warning("⚠️ Please enter a log line")
    
    # All-in-One Processing
    st.markdown("---")
    st.markdown("### 🚀 Complete Processing")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🎯 Process All Steps", type="primary", use_container_width=True):
            if raw_log.strip():
                render_complete_processing(raw_log)
            else:
                st.warning("⚠️ Please enter a log line")


def render_log_identification(raw_log):
    """Render log identification results"""
    st.markdown("#### 🔍 Log Identification Results")
    
    with st.spinner("Analyzing log type..."):
        # Use both methods
        basic_result = identify_log_type(raw_log)
        llm_result = classify_log_lc(raw_log)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔬 Basic Analysis:**")
        st.markdown("""
        <div class="result-section">
        """, unsafe_allow_html=True)
        st.json(basic_result)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("**🤖 LLM Analysis:**")
        st.markdown("""
        <div class="result-section">
        """, unsafe_allow_html=True)
        st.json(llm_result)
        st.markdown("</div>", unsafe_allow_html=True)


def render_ecs_generation(raw_log):
    """Render ECS JSON generation results"""
    st.markdown("#### 📋 ECS JSON Generation")
    
    with st.spinner("Generating ECS JSON..."):
        # Get RAG context
        log_profile = classify_log_lc(raw_log)
        context = st.session_state.rag_system.build_context_for_log(log_profile)
        
        # Generate JSON
        ecs_json = generate_ecs_json_lc(context, raw_log)
    
    st.markdown("**Generated ECS JSON:**")
    st.markdown("""
    <div class="result-section">
    """, unsafe_allow_html=True)
    st.json(ecs_json)
    st.markdown("</div>", unsafe_allow_html=True)


def render_vrl_generation(raw_log):
    """Render VRL generation results"""
    st.markdown("#### ⚙️ VRL Parser Generation")
    
    with st.spinner("Generating VRL parser..."):
        # Get RAG context
        log_profile = classify_log_lc(raw_log)
        context = st.session_state.rag_system.build_context_for_log(log_profile)
        
        # Generate VRL with error handling
        vrl_integration = VRL_Error_Integration()
        vrl_result = vrl_integration.generate_vrl_with_error_handling(context, raw_log)
    
    if vrl_result["success"]:
        st.markdown("**Generated VRL Parser:**")
        st.markdown("""
        <div class="result-section">
        """, unsafe_allow_html=True)

        # Persist current VRL in session
        if "current_vrl_code" not in st.session_state:
            st.session_state.current_vrl_code = vrl_result["vrl_code"]
        else:
            # Refresh session value only if empty
            if not st.session_state.current_vrl_code:
                st.session_state.current_vrl_code = vrl_result["vrl_code"]

        # Persistent editor UI
        st.markdown("##### Editor")
        edited_vrl = st.text_area(
            "Edit VRL Parser:",
            value=st.session_state.current_vrl_code,
            height=420,
            key="vrl_editor_persistent"
        )

        col_apply, col_save, col_next = st.columns([1, 1, 1])
        with col_apply:
            if st.button("✅ Apply", use_container_width=True):
                st.session_state.current_vrl_code = edited_vrl
                st.success("Applied changes to current VRL.")

        with col_save:
            save_name = st.text_input("Filename (saved under data/parsers/)", value="parser.vrl", key="vrl_save_name")
            if st.button("💾 Save to .vrl", use_container_width=True):
                import os
                target_dir = os.path.join("data", "parsers")
                os.makedirs(target_dir, exist_ok=True)
                safe_name = save_name.strip() or "parser.vrl"
                if not safe_name.endswith(".vrl"):
                    safe_name += ".vrl"
                target_path = os.path.join(target_dir, safe_name)
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(st.session_state.current_vrl_code)
                st.success(f"Saved to {target_path}")

        with col_next:
            if st.button("➡️ Next", use_container_width=True):
                st.session_state.show_test_results = True

        st.markdown("</div>", unsafe_allow_html=True)

        # Test VRL button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🧪 Test VRL with Vector CLI", use_container_width=True):
                test_vrl_with_vector(st.session_state.current_vrl_code)
    else:
        st.markdown(f"""
        <div class="error-card">
            <h4>❌ VRL Generation Failed</h4>
            <p>Error: {vrl_result.get('error', 'Unknown error')}</p>
        </div>
        """, unsafe_allow_html=True)


def render_complete_processing(raw_log):
    """Render complete processing results"""
    st.markdown("#### 🎯 Complete Processing Results")
    
    # Step 1: Log Identification
    st.markdown("**Step 1: Log Identification**")
    with st.spinner("Identifying log type..."):
        log_profile = classify_log_lc(raw_log)
    
    st.markdown("""
    <div class="result-section">
    """, unsafe_allow_html=True)
    st.json(log_profile)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Step 2: ECS JSON Generation
    st.markdown("**Step 2: ECS JSON Generation**")
    with st.spinner("Generating ECS JSON..."):
        context = st.session_state.rag_system.build_context_for_log(log_profile)
        ecs_json = generate_ecs_json_lc(context, raw_log)
    
    st.markdown("""
    <div class="result-section">
    """, unsafe_allow_html=True)
    st.json(ecs_json)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Step 3: VRL Generation
    st.markdown("**Step 3: VRL Parser Generation**")
    with st.spinner("Generating VRL parser..."):
        vrl_integration = VRL_Error_Integration()
        vrl_result = vrl_integration.generate_vrl_with_error_handling(context, raw_log)
    
    if vrl_result["success"]:
        st.markdown("""
        <div class="result-section">
        """, unsafe_allow_html=True)
        
        # VRL display with edit capability
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("✏️ Edit VRL", key="edit_vrl_complete", use_container_width=True):
                st.session_state.edit_vrl_complete = True
        
        with col2:
            if st.button("➡️ Next", key="next_complete", use_container_width=True):
                st.session_state.show_test_results = True
        
        # Show VRL code
        if st.session_state.get("edit_vrl_complete", False):
            edited_vrl = st.text_area(
                "Edit VRL Parser:",
                value=vrl_result["vrl_code"],
                height=400,
                key="vrl_editor_complete"
            )
            
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button("💾 Save Changes", key="save_vrl_complete", use_container_width=True):
                    vrl_result["vrl_code"] = edited_vrl
                    st.session_state.edit_vrl_complete = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key="cancel_vrl_complete", use_container_width=True):
                    st.session_state.edit_vrl_complete = False
                    st.rerun()
        else:
            st.code(vrl_result["vrl_code"], language="javascript")
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Test VRL button
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("🧪 Test VRL with Vector CLI", key="test_vrl_complete", use_container_width=True):
                test_vrl_with_vector(vrl_result["vrl_code"])
    else:
        st.markdown(f"""
        <div class="error-card">
            <h4>❌ VRL Generation Failed</h4>
            <p>Error: {vrl_result.get('error', 'Unknown error')}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Summary
    st.markdown("""
    <div class="status-card">
        <h4>✅ Complete Processing Finished!</h4>
        <p>All steps have been completed successfully. You now have the log profile, ECS JSON, and VRL parser.</p>
    </div>
    """, unsafe_allow_html=True)


def render_test_mode():
    """Render system testing mode"""
    st.header("🧪 System Testing")
    
    if st.session_state.rag_system is None:
        st.warning("⚠️ Please initialize the RAG system first")
        return
    
    # Test samples
    test_logs = [
        {
            "name": "Cisco ASA",
            "log": "%ASA-6-302013: Built outbound TCP connection 12345 for outside:10.0.0.1/80 to inside:192.168.1.100/45678",
            "expected_type": "syslog"
        },
        {
            "name": "JSON Log",
            "log": '{"timestamp":"2025-01-01T12:34:56Z","level":"INFO","message":"User login successful","user":"alice","ip":"10.0.0.1"}',
            "expected_type": "json"
        },
        {
            "name": "Windows Security",
            "log": "Event ID 4624: An account was successfully logged on. Account Name: alice, Source Network Address: 10.0.0.1",
            "expected_type": "windows_event"
        }
    ]
    
    st.subheader("🧪 Test Log Samples")
    
    for i, test in enumerate(test_logs):
        with st.expander(f"Test {i+1}: {test['name']}"):
            st.code(test['log'])
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button(f"🔍 Identify {i+1}"):
                    result = classify_log_lc(test['log'])
                    st.json(result)
            
            with col2:
                if st.button(f"📋 JSON {i+1}"):
                    log_profile = classify_log_lc(test['log'])
                    context = st.session_state.rag_system.build_context_for_log(log_profile)
                    ecs_json = generate_ecs_json_lc(context, test['log'])
                    st.json(ecs_json)
            
            with col3:
                if st.button(f"⚙️ VRL {i+1}"):
                    log_profile = classify_log_lc(test['log'])
                    context = st.session_state.rag_system.build_context_for_log(log_profile)
                    vrl_code = generate_vrl_lc(context, test['log'])
                    st.code(vrl_code, language="javascript")


def test_vrl_with_vector(vrl_code: str):
    """Test VRL code with Vector CLI"""
    try:
        # Create temporary VRL file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.vrl', delete=False) as f:
            f.write(vrl_code)
            vrl_file = f.name
        
        # Create temporary Vector config
        vector_config = f"""
data_dir = "/tmp/vector"
[sources.in]
type = "stdin"
decoding.codec = "text"

[transforms.parse]
type = "remap"
inputs = ["in"]
file = "{vrl_file}"

[sinks.out]
type = "console"
inputs = ["parse"]
encoding.codec = "json"
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(vector_config)
            config_file = f.name
        
        # Run Vector
        result = subprocess.run(
            ["vector", "--config", config_file],
            input="test log line",
            text=True,
            capture_output=True,
            timeout=10
        )
        
        if result.returncode == 0:
            st.success("✅ VRL executed successfully!")
            st.code(result.stdout, language="json")
        else:
            st.error(f"❌ VRL execution failed: {result.stderr}")
        
        # Cleanup
        os.unlink(vrl_file)
        os.unlink(config_file)
        
    except Exception as e:
        st.error(f"❌ Vector CLI test error: {str(e)}")


if __name__ == "__main__":
    main()
