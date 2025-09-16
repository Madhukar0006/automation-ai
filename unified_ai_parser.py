#!/usr/bin/env python3
"""
Unified AI Log Parser - Complete Integration
Combines the best of both projects:
- UI from main_app.py (Streamlit)
- RAG/Indexing from automated_ai_parser.py
- Error handling from vrl_error_integration.py
- Enhanced VRL generation
"""

import os
import re
import json
import subprocess
import tempfile
from typing import Dict, Any, List, Tuple
import streamlit as st
import pandas as pd
from datetime import datetime, timezone
import logging

# Import our modules
from complete_rag_system import CompleteRAGSystem, render_rag_setup
from simple_agent import SimpleLogParsingAgent, create_simple_agent
from lc_bridge import classify_log_lc, generate_ecs_json_lc, generate_vrl_lc
from log_analyzer import identify_log_type
from vrl_error_integration import VRL_Error_Integration
from enhanced_vrl_generator import Enhanced_VRL_Generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# Streamlit Settings
# =========================
st.set_page_config(
    page_title="🧠 Unified AI Log Parser", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# Initialize Session State
# =========================
if "rag_system" not in st.session_state:
    st.session_state.rag_system = None

if "agent" not in st.session_state:
    st.session_state.agent = None

if "error_integration" not in st.session_state:
    st.session_state.error_integration = None

if "enhanced_generator" not in st.session_state:
    st.session_state.enhanced_generator = None

if "current_mode" not in st.session_state:
    st.session_state.current_mode = "rag_setup"

if "system_initialized" not in st.session_state:
    st.session_state.system_initialized = False

# =========================
# Unified AI Parser Class
# =========================

class UnifiedAIParser:
    """Unified AI parser combining all capabilities"""
    
    def __init__(self):
        self.rag_system = None
        self.agent = None
        self.error_integration = None
        self.enhanced_generator = None
        self.initialized = False
        
    def initialize_system(self) -> bool:
        """Initialize all components of the unified system"""
        try:
            logger.info("🚀 Initializing Unified AI Parser System...")
            
            # Initialize RAG system
            self.rag_system = CompleteRAGSystem()
            if not self.rag_system.initialize_system():
                raise Exception("Failed to initialize RAG system")
            
            # Initialize error handling
            self.error_integration = VRL_Error_Integration()
            
            # Initialize enhanced VRL generator
            self.enhanced_generator = Enhanced_VRL_Generator()
            
            # Initialize agent
            self.agent = create_simple_agent(
                self.rag_system.build_context_for_log
            )
            
            self.initialized = True
            logger.info("✅ Unified AI Parser System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize system: {e}")
            return False
    
    def parse_log_comprehensive(self, raw_log: str, context: str = "") -> Dict[str, Any]:
        """Comprehensive log parsing with all capabilities"""
        if not self.initialized:
            return {"error": "System not initialized"}
        
        try:
            # Step 1: Log Classification
            log_profile = classify_log_lc(raw_log)
            
            # Step 2: ECS JSON Generation
            ecs_json = generate_ecs_json_lc(context or "Unified AI Parser", raw_log)
            
            # Step 3: Enhanced VRL Generation with Error Handling
            vrl_result = self.error_integration.generate_vrl_with_error_handling(
                context or "Unified AI Parser", raw_log
            )
            
            # Step 4: Agent-based Analysis (if available)
            agent_analysis = None
            if self.agent:
                try:
                    agent_analysis = self.agent.analyze_log(raw_log)
                except Exception as e:
                    logger.warning(f"Agent analysis failed: {e}")
            
            return {
                "success": True,
                "log_profile": log_profile,
                "ecs_json": ecs_json,
                "vrl_result": vrl_result,
                "agent_analysis": agent_analysis,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Comprehensive parsing failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        status = {
            "initialized": self.initialized,
            "rag_system": self.rag_system is not None,
            "agent": self.agent is not None,
            "error_integration": self.error_integration is not None,
            "enhanced_generator": self.enhanced_generator is not None
        }
        
        if self.rag_system:
            status["rag_status"] = self.rag_system.get_system_status()
        
        if self.error_integration:
            status["error_stats"] = self.error_integration.get_error_statistics()
        
        return status

# =========================
# UI Components
# =========================

def render_system_status():
    """Render system status in sidebar"""
    st.sidebar.header("🔧 System Status")
    
    if st.session_state.system_initialized:
        parser = st.session_state.rag_system
        if hasattr(parser, 'get_system_status'):
            status = parser.get_system_status()
            
            # RAG System Status
            st.sidebar.subheader("📚 RAG System")
            st.sidebar.success(f"✅ Knowledge Base: {status.get('knowledge_base_size', 'Unknown')} entries")
            st.sidebar.success(f"✅ Embedding Model: {status.get('embedding_model', 'Unknown')}")
            
            # Error Handling Status
            if st.session_state.error_integration:
                error_stats = st.session_state.error_integration.get_error_statistics()
                st.sidebar.subheader("🛠️ Error Handling")
                st.sidebar.info(f"Generations: {error_stats.get('total_generations', 0)}")
                st.sidebar.info(f"Success Rate: {error_stats.get('success_rate', 0)}%")
                st.sidebar.info(f"Errors Fixed: {error_stats.get('errors_fixed', 0)}")
    else:
        st.sidebar.warning("⚠️ System not initialized")

def render_log_parser():
    """Render the main log parser interface"""
    st.header("🔍 Log Parser")
    
    # Input section
    col1, col2 = st.columns([2, 1])
    
    with col1:
        raw_log = st.text_area(
            "📝 Raw Log Line",
            placeholder="Paste your log line here...",
            height=100,
            help="Enter the raw log line you want to parse"
        )
    
    with col2:
        context = st.text_input(
            "📋 Context (Optional)",
            placeholder="Additional context...",
            help="Provide additional context for better parsing"
        )
        
        parse_button = st.button("🚀 Parse Log", type="primary", use_container_width=True)
    
    if parse_button and raw_log:
        with st.spinner("🔄 Parsing log..."):
            # Parse the log
            result = st.session_state.rag_system.parse_log_comprehensive(raw_log, context)
            
            if result["success"]:
                # Display results in tabs
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Log Profile", "📋 ECS JSON", "⚙️ VRL Parser", "🤖 Agent Analysis"])
                
                with tab1:
                    st.subheader("Log Classification")
                    profile = result["log_profile"]
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Log Type", profile.get("log_type", "Unknown"))
                        st.metric("Log Format", profile.get("log_format", "Unknown"))
                    
                    with col2:
                        st.metric("Vendor", profile.get("vendor", "Unknown"))
                        st.metric("Product", profile.get("product", "Unknown"))
                    
                    with col3:
                        st.metric("Log Source", profile.get("log_source", "Unknown"))
                        st.metric("Category", profile.get("category", "Unknown"))
                
                with tab2:
                    st.subheader("ECS JSON Output")
                    ecs_json = result["ecs_json"]
                    st.json(ecs_json)
                    
                    # Download button
                    st.download_button(
                        label="📥 Download ECS JSON",
                        data=json.dumps(ecs_json, indent=2),
                        file_name=f"ecs_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                with tab3:
                    st.subheader("VRL Parser")
                    vrl_result = result["vrl_result"]
                    
                    # VRL Status
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Success", "✅" if vrl_result["success"] else "❌")
                    with col2:
                        st.metric("Attempts", vrl_result["attempts"])
                    with col3:
                        st.metric("Validation", "✅" if vrl_result["final_validation"] else "❌")
                    
                    # VRL Code
                    st.code(vrl_result["vrl_code"], language="coffeescript")
                    
                    # Download button
                    st.download_button(
                        label="📥 Download VRL",
                        data=vrl_result["vrl_code"],
                        file_name=f"parser_{datetime.now().strftime('%Y%m%d_%H%M%S')}.vrl",
                        mime="text/plain"
                    )
                    
                    # Error information
                    if vrl_result["errors"]:
                        with st.expander("⚠️ Errors Found"):
                            for error in vrl_result["errors"]:
                                st.error(f"{error['error_type']}: {error['message']}")
                    
                    if vrl_result["fixes_applied"]:
                        with st.expander("🔧 Fixes Applied"):
                            for fix in vrl_result["fixes_applied"]:
                                st.success(fix)
                
                with tab4:
                    st.subheader("Agent Analysis")
                    agent_analysis = result["agent_analysis"]
                    if agent_analysis:
                        st.json(agent_analysis)
                    else:
                        st.info("No agent analysis available")
            else:
                st.error(f"❌ Parsing failed: {result.get('error', 'Unknown error')}")

def render_batch_processing():
    """Render batch processing interface"""
    st.header("📦 Batch Processing")
    
    uploaded_file = st.file_uploader(
        "📁 Upload Log File",
        type=['txt', 'log', 'json'],
        help="Upload a file containing multiple log lines"
    )
    
    if uploaded_file:
        # Read file content
        content = uploaded_file.read().decode('utf-8')
        log_lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        st.info(f"📊 Found {len(log_lines)} log lines")
        
        if st.button("🚀 Process All Logs", type="primary"):
            results = []
            progress_bar = st.progress(0)
            
            for i, log_line in enumerate(log_lines):
                result = st.session_state.rag_system.parse_log_comprehensive(log_line)
                results.append({
                    "log_line": log_line,
                    "result": result
                })
                progress_bar.progress((i + 1) / len(log_lines))
            
            # Display results
            st.subheader("📊 Batch Processing Results")
            
            # Summary
            successful = sum(1 for r in results if r["result"]["success"])
            st.metric("Success Rate", f"{successful}/{len(results)} ({successful/len(results)*100:.1f}%)")
            
            # Results table
            df_data = []
            for i, result in enumerate(results):
                df_data.append({
                    "Line": i + 1,
                    "Success": "✅" if result["result"]["success"] else "❌",
                    "Log Type": result["result"].get("log_profile", {}).get("log_type", "Unknown"),
                    "Vendor": result["result"].get("log_profile", {}).get("vendor", "Unknown"),
                    "Error": result["result"].get("error", "")
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            # Download results
            results_json = json.dumps(results, indent=2, default=str)
            st.download_button(
                label="📥 Download Results",
                data=results_json,
                file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )

def render_system_management():
    """Render system management interface"""
    st.header("⚙️ System Management")
    
    # RAG System Management
    st.subheader("📚 RAG System")
    
    if st.session_state.rag_system:
        status = st.session_state.rag_system.get_system_status()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Knowledge Base Size", status.get("knowledge_base_size", "Unknown"))
        with col2:
            st.metric("Embedding Model", status.get("embedding_model", "Unknown"))
        with col3:
            st.metric("ChromaDB Status", "✅ Connected" if status.get("chromadb_ready") else "❌ Disconnected")
        
        # Rebuild RAG button
        if st.button("🔄 Rebuild RAG System", type="secondary"):
            with st.spinner("Rebuilding RAG system..."):
                if st.session_state.rag_system.initialize_system():
                    st.success("✅ RAG system rebuilt successfully")
                    st.rerun()
                else:
                    st.error("❌ Failed to rebuild RAG system")
    
    # Error Handling Statistics
    if st.session_state.error_integration:
        st.subheader("🛠️ Error Handling Statistics")
        error_stats = st.session_state.error_integration.get_error_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Generations", error_stats.get("total_generations", 0))
        with col2:
            st.metric("Success Rate", f"{error_stats.get('success_rate', 0)}%")
        with col3:
            st.metric("Errors Fixed", error_stats.get("errors_fixed", 0))
        with col4:
            st.metric("Failed Generations", error_stats.get("failed_generations", 0))
        
        # Common errors
        if error_stats.get("common_errors"):
            st.subheader("🔍 Common Errors")
            for error_type, count in error_stats["common_errors"].items():
                st.text(f"{error_type}: {count} occurrences")

# =========================
# Main Application
# =========================

def main():
    st.title("🧠 Unified AI Log Parser")
    st.markdown("**Complete log parsing with RAG, embeddings, error handling, and intelligent agents**")
    
    # Initialize system if not done
    if not st.session_state.system_initialized:
        with st.spinner("🚀 Initializing Unified AI Parser System..."):
            parser = UnifiedAIParser()
            if parser.initialize_system():
                st.session_state.rag_system = parser
                st.session_state.system_initialized = True
                st.success("✅ System initialized successfully!")
                st.rerun()
            else:
                st.error("❌ Failed to initialize system. Please check the logs.")
                return
    
    # Render sidebar
    render_system_status()
    
    # Main navigation
    tab1, tab2, tab3 = st.tabs(["🔍 Log Parser", "📦 Batch Processing", "⚙️ System Management"])
    
    with tab1:
        render_log_parser()
    
    with tab2:
        render_batch_processing()
    
    with tab3:
        render_system_management()

if __name__ == "__main__":
    main()

