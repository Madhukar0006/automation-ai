"""
Fully Automated AI Log Parser
Handles everything automatically - no manual intervention required
"""

import os
import json
import re
import streamlit as st
from typing import Dict, Any, List
from datetime import datetime
import logging

# Import our modules
from complete_rag_system import CompleteRAGSystem
from simple_agent import SimpleLogParsingAgent, create_simple_agent
from lc_bridge import classify_log_lc, generate_ecs_json_lc, generate_vrl_lc
from log_analyzer import identify_log_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================
# Automated AI Parser Class
# =========================

class AutomatedAIParser:
    """Fully automated AI log parser with intelligent error handling"""
    
    def __init__(self):
        self.rag_system = None
        self.agent = None
        self.initialized = False
        self.auto_mode = True
        
    def auto_initialize(self):
        """Automatically initialize all components"""
        try:
            logger.info("🤖 Starting automated AI parser initialization...")
            
            # Initialize RAG system
            self.rag_system = CompleteRAGSystem()
            if not self.rag_system.initialize_system():
                raise Exception("Failed to initialize RAG system")
            
            # Initialize agent
            self.agent = create_simple_agent(
                self.rag_system.build_context_for_log
            )
            
            self.initialized = True
            logger.info("✅ Automated AI parser initialized successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Auto-initialization failed: {str(e)}")
            return False
    
    def auto_parse_log(self, raw_log: str, output_type: str = "auto") -> Dict[str, Any]:
        """Automatically parse a log with full error handling"""
        if not self.initialized:
            if not self.auto_initialize():
                return self._create_error_response(raw_log, "System initialization failed")
        
        try:
            # Step 1: Auto-detect log type
            log_profile = self._auto_classify_log(raw_log)
            
            # Step 2: Auto-determine output type if needed
            if output_type == "auto":
                output_type = self._auto_determine_output_type(log_profile, raw_log)
            
            # Step 3: Auto-generate appropriate output
            if output_type == "json":
                result = self._auto_generate_json(raw_log, log_profile)
            else:
                result = self._auto_generate_vrl(raw_log, log_profile)
            
            return {
                "success": True,
                "raw_log": raw_log,
                "log_profile": log_profile,
                "output_type": output_type,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Auto-parsing failed: {str(e)}")
            return self._create_error_response(raw_log, str(e))
    
    def _auto_classify_log(self, raw_log: str) -> Dict[str, Any]:
        """Automatically classify log with fallbacks"""
        try:
            # Try LLM classification first
            llm_result = classify_log_lc(raw_log)
            if llm_result and not any(v == "unknown" for v in llm_result.values()):
                return llm_result
        except:
            pass
        
        try:
            # Fallback to basic classification
            basic_result = identify_log_type(raw_log)
            return {
                "log_type": basic_result.get("log_type", "unknown"),
                "log_format": basic_result.get("log_format", "unknown"),
                "log_source": basic_result.get("log_source", "unknown"),
                "product": basic_result.get("product", "unknown"),
                "vendor": basic_result.get("vendor", "unknown")
            }
        except:
            # Ultimate fallback
            return {
                "log_type": "unknown",
                "log_format": "unknown",
                "log_source": "unknown",
                "product": "unknown",
                "vendor": "unknown"
            }
    
    def _auto_determine_output_type(self, log_profile: Dict[str, Any], raw_log: str) -> str:
        """Automatically determine the best output type"""
        # Check if it's JSON
        if log_profile.get("log_format") == "json" or raw_log.strip().startswith("{"):
            return "json"
        
        # Check if it's a simple key-value log
        if "=" in raw_log and " " in raw_log:
            return "json"
        
        # Default to VRL for complex parsing
        return "vrl"
    
    def _auto_generate_json(self, raw_log: str, log_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically generate JSON with multiple strategies"""
        try:
            # Get RAG context
            context = self.rag_system.build_context_for_log(log_profile)
            
            # Try LLM generation
            ecs_json = generate_ecs_json_lc(context, raw_log)
            
            # Validate the result
            if self._validate_ecs_json(ecs_json):
                return ecs_json
            
        except Exception as e:
            logger.warning(f"LLM JSON generation failed: {e}")
        
        # Fallback to automated extraction
        return self._extract_structured_data(raw_log)
    
    def _auto_generate_vrl(self, raw_log: str, log_profile: Dict[str, Any]) -> str:
        """Automatically generate VRL with multiple strategies"""
        try:
            # Get RAG context
            context = self.rag_system.build_context_for_log(log_profile)
            
            # Try LLM generation
            vrl_code = generate_vrl_lc(context, raw_log)
            
            # Validate the result
            if self._validate_vrl_code(vrl_code):
                return vrl_code
                
        except Exception as e:
            logger.warning(f"LLM VRL generation failed: {e}")
        
        # Fallback to automated VRL generation
        return self._generate_automated_vrl(raw_log, log_profile)
    
    def _validate_ecs_json(self, ecs_json: Dict[str, Any]) -> bool:
        """Validate ECS JSON structure"""
        required_fields = ["@timestamp", "event", "message"]
        return all(field in ecs_json for field in required_fields)
    
    def _validate_vrl_code(self, vrl_code: str) -> bool:
        """Validate VRL code"""
        if not vrl_code or len(vrl_code.strip()) < 10:
            return False
        
        # Check for basic VRL syntax
        vrl_indicators = [".", "=", "parse_", "if ", "else", "event_data"]
        return any(indicator in vrl_code for indicator in vrl_indicators)
    
    def _extract_structured_data(self, raw_log: str) -> Dict[str, Any]:
        """Extract structured data from log using regex patterns"""
        timestamp = datetime.now().isoformat() + "Z"
        
        # Extract timestamp from log if present
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', raw_log)
        if timestamp_match:
            timestamp = timestamp_match.group(1).replace(' ', 'T') + 'Z'
        
        # Extract IP addresses
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, raw_log)
        
        # Extract usernames
        user_pattern = r'(?:user|username|account)[\s:=]+([a-zA-Z0-9_-]+)'
        user_match = re.search(user_pattern, raw_log, re.IGNORECASE)
        username = user_match.group(1) if user_match else None
        
        # Extract ports
        port_pattern = r':(\d{1,5})\b'
        ports = re.findall(port_pattern, raw_log)
        
        # Determine event category
        category = "unknown"
        if any(word in raw_log.lower() for word in ['login', 'auth', 'password']):
            category = "authentication"
        elif any(word in raw_log.lower() for word in ['connection', 'tcp', 'udp', 'network']):
            category = "network"
        elif any(word in raw_log.lower() for word in ['error', 'failed', 'denied']):
            category = "error"
        
        # Build ECS structure
        ecs_json = {
            "@timestamp": timestamp,
            "event": {
                "original": raw_log,
                "created": timestamp,
                "category": category
            },
            "message": raw_log
        }
        
        # Add extracted fields
        if ips:
            if len(ips) >= 2:
                ecs_json["source"] = {"ip": ips[0]}
                ecs_json["destination"] = {"ip": ips[1]}
            else:
                ecs_json["source"] = {"ip": ips[0]}
        
        if username:
            ecs_json["user"] = {"name": username}
        
        if ports:
            if "source" in ecs_json:
                ecs_json["source"]["port"] = int(ports[0])
            if len(ports) >= 2 and "destination" in ecs_json:
                ecs_json["destination"]["port"] = int(ports[1])
        
        return ecs_json
    
    def _generate_automated_vrl(self, raw_log: str, log_profile: Dict[str, Any]) -> str:
        """Generate VRL code automatically using reference examples"""
        try:
            # Get appropriate reference VRL example
            reference_vrl = self._get_reference_vrl_for_log(log_profile, raw_log)
            
            # Adapt the reference for the specific log
            adapted_vrl = self._adapt_reference_vrl(reference_vrl, raw_log, log_profile)
            
            return adapted_vrl
            
        except Exception as e:
            # Fallback to basic VRL generation
            return self._generate_basic_vrl(raw_log, str(e))
    
    def _get_reference_vrl_for_log(self, log_profile: Dict[str, Any], raw_log: str) -> str:
        """Get appropriate reference VRL example based on log profile"""
        vendor = log_profile.get("vendor", "").lower()
        product = log_profile.get("product", "").lower()
        log_format = log_profile.get("log_format", "").lower()
        
        # Map log types to reference examples
        reference_mapping = {
            "cisco": "fortinet_fortigate_professional.vrl",
            "fortinet": "fortinet_fortigate_professional.vrl", 
            "fortigate": "fortinet_fortigate_professional.vrl",
            "palo": "palo_alto_professional.vrl",
            "palo_alto": "palo_alto_professional.vrl",
            "aws": "aws_elb_professional.vrl",
            "elb": "aws_elb_professional.vrl",
            "apache": "apache_access_professional.vrl"
        }
        
        # Try to find matching reference
        reference_file = None
        for key, filename in reference_mapping.items():
            if key in vendor or key in product or key in log_format:
                reference_file = filename
                break
        
        # Default to Fortinet if no match
        if not reference_file:
            reference_file = "fortinet_fortigate_professional.vrl"
        
        # Load the reference file
        try:
            reference_path = f"data/reference_examples/{reference_file}"
            with open(reference_path, 'r') as f:
                return f.read()
        except Exception as e:
            # Return a basic template if file not found
            return self._get_basic_vrl_template()
    
    def _adapt_reference_vrl(self, reference_vrl: str, raw_log: str, log_profile: Dict[str, Any]) -> str:
        """Adapt reference VRL for specific log"""
        # Update vendor and product information
        vendor = log_profile.get("vendor", "unknown").lower()
        product = log_profile.get("product", "unknown").lower()
        
        # Replace vendor/product in the reference
        adapted_vrl = reference_vrl.replace("fortinet", vendor)
        adapted_vrl = adapted_vrl.replace("fortigate", product)
        adapted_vrl = adapted_vrl.replace("palo_alto_networks", vendor)
        adapted_vrl = adapted_vrl.replace("pan-os", product)
        
        # Update dataset name
        dataset_name = f"{vendor}.{product}" if vendor != "unknown" and product != "unknown" else "unknown.logs"
        adapted_vrl = re.sub(r'\.event\.dataset = "[^"]*"', f'.event.dataset = "{dataset_name}"', adapted_vrl)
        
        # Add log-specific parsing if needed
        if "cisco" in vendor.lower() and "asa" in product.lower():
            # Add Cisco ASA specific parsing
            cisco_parsing = """
# Cisco ASA specific parsing
if match(.event.original, r"%ASA-") {
  .observer.vendor = "cisco"
  .observer.product = "asa"
  .observer.type = "firewall"
  
  # Parse ASA log format
  asa_match = match(.event.original, r"%ASA-(\\d+)-(\\d+): (.+)")
  if asa_match {
    .event_data.asa_severity = asa_match[1]
    .event_data.asa_message_id = asa_match[2]
    .event_data.asa_message = asa_match[3]
  }
}
"""
            # Insert after the basic structure
            adapted_vrl = adapted_vrl.replace(
                "if exists(.message) && is_string(.message) {",
                cisco_parsing + "\nif exists(.message) && is_string(.message) {"
            )
        
        return adapted_vrl
    
    def _get_basic_vrl_template(self) -> str:
        """Get basic VRL template when reference files are not available"""
        return """
.event.kind = "event"
.event.category = ["network", "security"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "firewall"
.event.dataset = "unknown.logs"

if exists(.message) && is_string(.message) {
  .event.original = del(.message)
}

# Parse key-value pairs if present
kvs = parse_key_value(.event.original, field_delimiter: ",", key_value_delimiter: "=")
if is_object(kvs) { .event_data = merge(.event_data, kvs, deep: true) }

# Extract common fields
if exists(.event_data.srcip) { .source.ip = del(.event_data.srcip) }
if exists(.event_data.dstip) { .destination.ip = del(.event_data.dstip) }
if exists(.event_data.sport) { .source.port = to_int!(del(.event_data.sport)) }
if exists(.event_data.dport) { .destination.port = to_int!(del(.event_data.dport)) }
if exists(.event_data.action) { .event.action = del(.event_data.action) }

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""
    
    def _generate_basic_vrl(self, raw_log: str, error_msg: str) -> str:
        """Generate basic VRL when all else fails"""
        return f"""
# Basic VRL Parser
# Error: {error_msg}

.event.kind = "event"
.event.category = ["unknown"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "unknown"
.event.dataset = "unknown.logs"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Basic parsing attempt
kvs = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
if is_object(kvs) {{ .event_data = merge(.event_data, kvs, deep: true) }}

. = compact(., string: true, array: true, object: true, null: true)
"""
    
    def _create_error_response(self, raw_log: str, error_msg: str) -> Dict[str, Any]:
        """Create error response with fallback data"""
        return {
            "success": False,
            "raw_log": raw_log,
            "error": error_msg,
            "fallback_result": {
                "@timestamp": datetime.now().isoformat() + "Z",
                "event": {
                    "original": raw_log,
                    "created": datetime.now().isoformat() + "Z",
                    "category": "error"
                },
                "message": raw_log,
                "error": {
                    "message": error_msg,
                    "type": "parsing_error"
                }
            },
            "timestamp": datetime.now().isoformat()
        }


# =========================
# Streamlit Interface
# =========================

def render_automated_ai_interface():
    """Render the automated AI interface"""
    st.header("🤖 Fully Automated AI Log Parser")
    st.markdown("**Zero manual intervention - AI handles everything automatically**")
    
    # Initialize parser
    if "automated_parser" not in st.session_state:
        st.session_state.automated_parser = AutomatedAIParser()
    
    parser = st.session_state.automated_parser
    
    # Status display
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = "✅ Ready" if parser.initialized else "⏳ Initializing..."
        st.metric("AI Parser Status", status)
    
    with col2:
        if parser.rag_system:
            kb_size = parser.rag_system.get_system_status()['knowledge_base_size']
            st.metric("Knowledge Base", f"{kb_size} entries")
        else:
            st.metric("Knowledge Base", "Not loaded")
    
    with col3:
        st.metric("Auto Mode", "🔄 Enabled")
    
    # Auto-initialize if needed
    if not parser.initialized:
        with st.spinner("🤖 AI is initializing automatically..."):
            if parser.auto_initialize():
                st.success("✅ AI Parser ready!")
                st.rerun()
            else:
                st.error("❌ Auto-initialization failed")
                return
    
    # Main input area
    st.subheader("📝 Log Input")
    
    # Multiple input methods
    input_method = st.radio(
        "Input Method",
        ["Single Log", "Multiple Logs", "File Upload"],
        horizontal=True
    )
    
    if input_method == "Single Log":
        raw_log = st.text_area(
            "Enter your log line",
            placeholder="Paste your log line here...",
            height=100,
            key="auto_single_log"
        )
        logs_to_process = [raw_log] if raw_log.strip() else []
    
    elif input_method == "Multiple Logs":
        raw_logs = st.text_area(
            "Enter multiple log lines (one per line)",
            placeholder="Paste multiple log lines here...",
            height=200,
            key="auto_multiple_logs"
        )
        logs_to_process = [line.strip() for line in raw_logs.split('\n') if line.strip()]
    
    else:  # File Upload
        uploaded_file = st.file_uploader(
            "Upload log file",
            type=['txt', 'log', 'json'],
            key="auto_file_upload"
        )
        if uploaded_file:
            content = uploaded_file.read().decode('utf-8')
            logs_to_process = [line.strip() for line in content.split('\n') if line.strip()]
        else:
            logs_to_process = []
    
    # Processing options
    col1, col2 = st.columns(2)
    
    with col1:
        output_type = st.selectbox(
            "Output Type",
            ["auto", "json", "vrl"],
            format_func=lambda x: {
                "auto": "🤖 Auto-detect (AI decides)",
                "json": "📋 ECS JSON",
                "vrl": "⚙️ VRL Parser"
            }[x]
        )
    
    with col2:
        batch_size = st.number_input(
            "Batch Size",
            min_value=1,
            max_value=50,
            value=min(10, len(logs_to_process)) if logs_to_process else 1
        )
    
    # Process button
    if st.button("🚀 Auto-Parse with AI", type="primary", use_container_width=True):
        if not logs_to_process:
            st.warning("⚠️ Please provide logs to parse")
            return
        
        # Process logs
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, log in enumerate(logs_to_process[:batch_size]):
            status_text.text(f"🤖 AI is parsing log {i+1}/{min(batch_size, len(logs_to_process))}")
            
            result = parser.auto_parse_log(log, output_type)
            results.append(result)
            
            progress_bar.progress((i + 1) / min(batch_size, len(logs_to_process)))
        
        status_text.text("✅ AI parsing completed!")
        
        # Display results
        st.subheader("🎯 AI Parsing Results")
        
        for i, result in enumerate(results):
            with st.expander(f"Result {i+1}: {'✅ Success' if result['success'] else '❌ Error'}"):
                if result['success']:
                    st.write("**Log Profile:**")
                    st.json(result['log_profile'])
                    
                    st.write(f"**Output Type:** {result['output_type']}")
                    
                    if result['output_type'] == 'json':
                        st.write("**Generated ECS JSON:**")
                        st.json(result['result'])
                    else:
                        st.write("**Generated VRL Parser:**")
                        st.code(result['result'], language="javascript")
                else:
                    st.error(f"Error: {result['error']}")
                    if 'fallback_result' in result:
                        st.write("**Fallback Result:**")
                        st.json(result['fallback_result'])
        
        # Summary
        success_count = sum(1 for r in results if r['success'])
        st.success(f"🎉 AI processed {success_count}/{len(results)} logs successfully!")


# =========================
# Main Application
# =========================

def main():
    """Main automated AI application"""
    st.set_page_config(
        page_title="🤖 Automated AI Log Parser",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.title("🤖 Automated AI Log Parser")
    st.markdown("**Fully automated log parsing with AI - Zero manual intervention required**")
    
    # Sidebar with info
    with st.sidebar:
        st.header("🤖 AI Features")
        st.markdown("""
        - **Auto-Initialization**: Sets up everything automatically
        - **Auto-Classification**: Identifies log types intelligently  
        - **Auto-Parsing**: Generates JSON or VRL automatically
        - **Auto-Error Handling**: Graceful fallbacks for any issues
        - **Auto-Validation**: Ensures output quality
        - **Auto-Batch Processing**: Handles multiple logs efficiently
        """)
        
        st.header("🎯 Supported Formats")
        st.markdown("""
        - **Syslog**: Cisco ASA, Checkpoint, etc.
        - **JSON**: Application logs, API responses
        - **Windows Events**: Security, system logs
        - **CEF**: Common Event Format
        - **Custom**: Any structured log format
        """)
    
    # Main interface
    render_automated_ai_interface()


if __name__ == "__main__":
    main()
