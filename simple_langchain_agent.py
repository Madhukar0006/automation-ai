"""
Simple LangChain Agent for Log Parsing
A lightweight agent without tool calling dependencies
"""

import json
import re
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferMemory
from langchain_community.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, AIMessage

from complete_rag_system import CompleteRAGSystem
from vrl_error_integration import VRL_Error_Handler
from log_analyzer import identify_log_type
from lc_bridge import generate_ecs_json_lc as generate_ecs_json


class SimpleLogParsingAgent:
    """Simple LangChain Agent for log parsing without tool calling"""
    
    def __init__(self, rag_system: CompleteRAGSystem):
        self.rag_system = rag_system
        self.error_handler = VRL_Error_Handler()
        
        # Use llama3.2 which is more stable
        self.llm = Ollama(model="llama3.2:latest")
        
        # Create memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert VRL (Vector Remap Language) parser developer and log analysis specialist. 

Your task is to help users generate, validate, and fix VRL parsers for various log formats including syslog, JSON, CEF, and others.

You have access to these capabilities:
1. Log type identification and classification
2. VRL parser generation using RAG knowledge base
3. VRL validation and error fixing
4. ECS field mapping generation
5. Knowledge base search for examples and best practices

Always provide clear explanations and show generated VRL code in proper code blocks.
Be thorough and ensure generated parsers follow best practices."""),
            ("human", "{input}")
        ])
    
    def identify_log_type(self, log_content: str) -> Dict[str, Any]:
        """Identify log type, vendor, and product using sourcelist.json mapping"""
        try:
            # Get basic format from existing function
            log_format = identify_log_type(log_content)
            
            # Load sourcelist.json mapping
            sourcelist_mapping = self._load_sourcelist_mapping()
            
            # Enhanced analysis using sourcelist mapping
            vendor = "Unknown"
            product = "Unknown"
            log_source = "unknown"
            observer_type = "unknown"
            confidence = "medium"
            
            # Try to match against sourcelist mappings with improved scoring
            best_match = None
            best_score = 0
            matched_entry = None
            
            for entry in sourcelist_mapping:
                score = 0
                vendor_keywords = entry.get("observer.vendor", "").lower()
                product_keywords = entry.get("observer.product", "").lower()
                
                # Skip entries with empty or generic keywords
                if not vendor_keywords or vendor_keywords in ["unknown", "generic"]:
                    continue
                
                # Create search patterns from vendor and product
                vendor_pattern = rf'(?i)({re.escape(vendor_keywords)})' if vendor_keywords else None
                product_pattern = rf'(?i)({re.escape(product_keywords)})' if product_keywords else None
                
                # Check for vendor matches (higher weight)
                vendor_match = re.search(vendor_pattern, log_content) if vendor_pattern else False
                if vendor_match:
                    score += 3  # Vendor match gets higher weight
                
                # Check for product matches (highest weight)
                product_match = re.search(product_pattern, log_content) if product_pattern else False
                if product_match:
                    score += 5  # Product match gets highest weight
                
                # Check for specific product keywords in log content
                if product_keywords:
                    # Handle special cases like "asa", "ios", "fortigate", etc.
                    specific_keywords = product_keywords.split()
                    for keyword in specific_keywords:
                        if keyword in ["asa", "ios", "fortigate", "pan-os", "windows", "linux", "syslog"]:
                            if re.search(rf'(?i)\b{re.escape(keyword)}\b', log_content):
                                score += 4  # Specific product keyword match
                
                # If this entry has a better score, use it
                if score > best_score:
                    best_score = score
                    best_match = entry
            
            # Only use the match if score is high enough
            if best_score >= 3:  # Minimum score threshold
                matched_entry = best_match
                confidence = "high" if best_score >= 5 else "medium"
            
            # If we found a match, use the sourcelist data
            if matched_entry:
                vendor = matched_entry.get("observer.vendor", "Unknown")
                product = matched_entry.get("observer.product", "Unknown")
                log_source = matched_entry.get("Log_type", "unknown")
                observer_type = matched_entry.get("observer.type", "unknown")
            else:
                # Fallback to basic pattern matching for common cases
                if re.search(r'(?i)(cisco|asa|ios|nexus|cat|switch|router|firewall)', log_content):
                    vendor = "cisco"
                    if re.search(r'(?i)(asa|firewall)', log_content):
                        product = "asa"
                        log_source = "cisco_asa"
                    elif re.search(r'(?i)(ios)', log_content):
                        product = "ios"
                        log_source = "cisco_ios"
                    elif re.search(r'(?i)(nexus)', log_content):
                        product = "nexus"
                        log_source = "cisco_nexus"
                    else:
                        product = "cisco"
                        log_source = "cisco_unknown"
                    observer_type = "network"
                    confidence = "medium"
                elif re.search(r'(?i)(fortinet|fortigate|forti)', log_content):
                    vendor = "fortinet"
                    product = "fortigate"
                    log_source = "fortinet_fortigate"
                    observer_type = "ngfw"
                    confidence = "medium"
                elif re.search(r'(?i)(palo\s+alto|panos|pa-)', log_content):
                    vendor = "paloalto"
                    product = "pan-os"
                    log_source = "paloalto_firewall"
                    observer_type = "ngfw"
                    confidence = "medium"
                elif re.search(r'(?i)(checkpoint|check\s+point|cp-)', log_content):
                    vendor = "checkpoint"
                    product = "smartdefence/firewall"
                    log_source = "checkpoint_firewall"
                    observer_type = "ngfw"
                    confidence = "medium"
                elif re.search(r'(?i)(sonicwall|sonicos)', log_content):
                    vendor = "sonicwall"
                    product = "firewall"
                    log_source = "sonicwall_firewall"
                    observer_type = "ngfw"
                    confidence = "medium"
                elif re.search(r'(?i)(windows|microsoft|win32)', log_content):
                    vendor = "microsoft"
                    product = "windows(application, defender, powershell, security, system, taskscheduler, wmiactivity)"
                    log_source = "winevtlogs"
                    observer_type = "windows"
                    confidence = "medium"
                elif log_format == "json":
                    vendor = "Application"
                    product = "JSON Logger"
                    log_source = "json_application"
                    observer_type = "application"
                    confidence = "low"
                elif log_format == "syslog":
                    vendor = "linux"
                    product = "syslog"
                    log_source = "linux_syslog"
                    observer_type = "linux"
                    confidence = "low"
            
            result = {
                "log_format": log_format,
                "vendor": vendor,
                "product": product,
                "log_source": log_source,
                "observer_type": observer_type,
                "confidence": confidence,
                "sourcelist_matched": matched_entry is not None
            }
            
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _load_sourcelist_mapping(self) -> List[Dict[str, Any]]:
        """Load sourcelist.json mapping"""
        try:
            import json
            sourcelist_path = "data/sourcelist.json"
            with open(sourcelist_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load sourcelist.json: {e}")
            return []
    
    def search_knowledge_base(self, query: str) -> Dict[str, Any]:
        """Search the RAG knowledge base"""
        try:
            results = self.rag_system.search(query, k=5)
            if not results:
                return {"success": True, "results": "No relevant information found in the knowledge base."}
            
            formatted_results = []
            for i, doc in enumerate(results, 1):
                formatted_results.append(f"{i}. {doc.page_content[:200]}...")
            
            return {"success": True, "results": "\n\n".join(formatted_results)}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_vrl_parser(self, log_content: str, log_format: str = None) -> Dict[str, Any]:
        """Generate VRL parser for the given log content"""
        try:
            if not log_format:
                # Auto-detect log format
                log_format = identify_log_type(log_content)
            
            result = self._generate_simple_vrl(log_content, log_format)
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _generate_simple_vrl(self, log_content: str, log_format: str) -> Dict[str, Any]:
        """Generate comprehensive VRL code that extracts ALL fields like human experts"""
        try:
            # Use CLEAN GROK-based VRL templates that eliminate nested duplication
            if log_format == "json":
                from clean_grok_parser import generate_clean_grok_json_vrl
                vrl_code = generate_clean_grok_json_vrl()
            elif log_format == "syslog":
                from clean_grok_parser import generate_clean_grok_syslog_vrl
                vrl_code = generate_clean_grok_syslog_vrl()
            else:
                vrl_code = """
# Clean GROK-Based Generic Log Parser - No Duplication, No Nesting
.message = .

# Basic text processing using GROK patterns
if is_string(.) {
    .input_string = string!(.)
    
    # Extract timestamp using GROK
    .timestamp_parsed, err = parse_grok(.input_string, "%{TIMESTAMP_ISO8601:timestamp}")
    if err == null && exists(.timestamp_parsed.timestamp) {
        .@timestamp = .timestamp_parsed.timestamp
    }
    
    # Extract log levels using GROK
    .level_parsed, err = parse_grok(.input_string, "%{LOGLEVEL:log_level}")
    if err == null && exists(.level_parsed.log_level) {
        .log.level = .level_parsed.log_level
    }
    
    # Extract IP addresses using GROK
    .ip_parsed, err = parse_grok(.input_string, "%{IP:source_ip}")
    if err == null && exists(.ip_parsed.source_ip) {
        .source.ip = .ip_parsed.source_ip
    }
    
    # Extract port numbers using GROK
    .port_parsed, err = parse_grok(.input_string, "port %{INT:dest_port}")
    if err == null && exists(.port_parsed.dest_port) {
        .destination.port, err = to_int(.port_parsed.dest_port)
    }
    
    # Extract usernames using GROK
    .user_parsed, err = parse_grok(.input_string, "user %{USERNAME:username}")
    if err == null && exists(.user_parsed.username) {
        .user.name = .user_parsed.username
    }
    
    # Extract file paths using GROK
    .path_parsed, err = parse_grok(.input_string, "%{UNIXPATH:file_path}")
    if err == null && exists(.path_parsed.file_path) {
        .file.path = .path_parsed.file_path
    }
    
    # Extract log levels (fallback)
    if contains(.input_string, "error") {
        .log.level = "error"
    }
    if contains(.input_string, "warn") {
        .log.level = "warn"
    }
    if contains(.input_string, "info") {
        .log.level = "info"
    }
    if contains(.input_string, "debug") {
        .log.level = "debug"
    }
}

# Ensure required fields exist
if !exists(."event.kind") {
    .event.kind = "event"
}
if !exists(."event.category") {
    .event.category = ["unknown"]
}
if !exists(."event.type") {
    .event.type = ["info"]
}
if !exists(."event.dataset") {
    .event.dataset = "generic.logs"
}
if !exists(."event.created") {
    .event.created = now()
}
if !exists(."@timestamp") {
    .@timestamp = now()
}

# Add metadata (single assignments only)
.log.original = .
.tags = ["generic", "parsed", "grok-based"]

# Compact the output
. = compact(., string: true, array: true, object: true, null: true)
"""
            
            return {
                "success": True,
                "vrl_code": vrl_code.strip(),
                "log_format": log_format
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def validate_vrl(self, vrl_code: str) -> Dict[str, Any]:
        """Validate VRL code using simple validation"""
        try:
            # Simple validation
            errors = []
            
            if not vrl_code.strip():
                errors.append({"type": "syntax_error", "message": "VRL code is empty", "line": 0})
            
            if ".event.kind" not in vrl_code:
                errors.append({"type": "field_error", "message": "Missing .event.kind field", "line": 0})
            
            if ".event.created" not in vrl_code:
                errors.append({"type": "field_error", "message": "Missing .event.created field", "line": 0})
            
            return {
                "success": len(errors) == 0,
                "errors": errors,
                "vrl_code": vrl_code
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_ecs_mapping(self, log_content: str) -> Dict[str, Any]:
        """Generate ECS field mapping for the log"""
        try:
            result = generate_ecs_json("Generate ECS mapping", log_content)
            # Ensure the result has the expected format
            if isinstance(result, dict):
                if "success" not in result:
                    return {"success": True, "result": result}
                else:
                    return result
            else:
                return {"success": False, "error": "ECS generation returned unexpected format"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def fix_vrl_errors(self, vrl_code: str, errors: str) -> Dict[str, Any]:
        """Fix VRL code errors"""
        try:
            result = self.error_handler.fix_vrl_errors(vrl_code, errors)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def chat(self, message: str) -> str:
        """Simple chat interface with the agent"""
        try:
            # Create chain
            chain = self.prompt | self.llm
            
            # Get chat history
            chat_history = self.memory.chat_memory.messages
            
            # Prepare input
            input_data = {
                "input": message,
                "chat_history": chat_history
            }
            
            # Get response
            response = chain.invoke(input_data)
            
            # Save to memory
            self.memory.save_context(
                {"input": message},
                {"output": response}
            )
            
            return response
            
        except Exception as e:
            return f"Chat failed: {str(e)}"
    
    def run_4_agent_workflow(self, log_content: str) -> Dict[str, Any]:
        """Run the 4-agent workflow: Identify → Generate → Validate → ECS Map"""
        
        workflow_results = {
            "log_content": log_content,
            "steps": [],
            "final_vrl": None,
            "success": False
        }
        
        try:
            # Step 1: Log Type Identification
            step1_result = self.identify_log_type(log_content)
            workflow_results["steps"].append({
                "step": 1,
                "agent": "Log Type Identifier",
                "result": step1_result,
                "status": "completed" if step1_result["success"] else "failed"
            })
            
            # Step 2: VRL Generation
            log_format = step1_result.get("result", {}).get("log_format", "unknown") if step1_result["success"] else "unknown"
            step2_result = self.generate_vrl_parser(log_content, log_format)
            workflow_results["steps"].append({
                "step": 2,
                "agent": "VRL Generator",
                "result": step2_result,
                "status": "completed" if step2_result["success"] else "failed"
            })
            
            # Extract VRL code from step 2 if successful
            vrl_code = None
            if step2_result["success"]:
                vrl_code = step2_result.get("vrl_code", "")
            
            # Step 3: VRL Validation (if we have VRL code)
            if vrl_code:
                step3_result = self.validate_vrl(vrl_code)
                workflow_results["steps"].append({
                    "step": 3,
                    "agent": "VRL Validator",
                    "result": step3_result,
                    "status": "completed" if step3_result["success"] else "failed"
                })
                workflow_results["final_vrl"] = vrl_code
            
            # Step 4: ECS Mapping (always run this step)
            step4_result = self.generate_ecs_mapping(log_content)
            workflow_results["steps"].append({
                "step": 4,
                "agent": "ECS Mapper",
                "result": step4_result,
                "status": "completed" if step4_result["success"] else "failed"
            })
            
            # Consider workflow successful if we have VRL code and ECS mapping
            workflow_results["success"] = vrl_code is not None and step4_result["success"]
            
        except Exception as e:
            workflow_results["error"] = str(e)
        
        return workflow_results


class SimpleAgentOrchestrator:
    """Simple orchestrator for the log parsing agent"""
    
    def __init__(self, rag_system: CompleteRAGSystem):
        self.rag_system = rag_system
        self.main_agent = SimpleLogParsingAgent(rag_system)
        
    def run_4_agent_workflow(self, log_content: str) -> Dict[str, Any]:
        """Run the 4-agent workflow"""
        return self.main_agent.run_4_agent_workflow(log_content)


# Convenience function to create simple agent system
def create_simple_log_parsing_agents(rag_system: CompleteRAGSystem) -> SimpleAgentOrchestrator:
    """Create and return the simple agent orchestrator"""
    return SimpleAgentOrchestrator(rag_system)


if __name__ == "__main__":
    # Example usage
    print("Initializing RAG system...")
    rag_system = CompleteRAGSystem()
    rag_system.build_langchain_index()
    
    print("Creating simple agents...")
    orchestrator = create_simple_log_parsing_agents(rag_system)
    
    # Test with sample log
    sample_log = """<134>1 2024-01-15T10:30:45.123Z firewall.example.com asa 12345 - - %ASA-6-302013: Built outbound TCP connection 1234567890 for outside:203.0.113.5/80 (203.0.113.5/80) to inside:192.168.1.100/54321 (192.168.1.100/54321)"""
    
    print("Running 4-agent workflow...")
    result = orchestrator.run_4_agent_workflow(sample_log)
    
    print(f"Workflow completed: {result['success']}")
    if result['success'] and result['final_vrl']:
        print("Generated VRL:")
        print(result['final_vrl'])
