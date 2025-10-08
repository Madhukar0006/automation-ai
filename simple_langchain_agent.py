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
from log_analyzer import identify_log_type
from lc_bridge import generate_ecs_json_lc as generate_ecs_json


class VRL_Error_Handler:
    """Simple VRL error handler for compatibility"""
    def fix_vrl_errors(self, vrl_code: str, errors: str) -> Dict[str, Any]:
        return {"success": True, "fixed_vrl": vrl_code, "message": "Error handling not implemented"}


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
    
    def _generate_minimal_microsoft_parser(self) -> str:
        """Generate minimal VRL parser specifically for Microsoft/Azure AD logs"""
        return '''##################################################
## Minimal Microsoft/Azure AD JSON Parser
##################################################

### ECS observer defaults
if !exists(.observer.type) { .observer.type = "application" }
if !exists(.observer.vendor) { .observer.vendor = "microsoft" }
if !exists(.observer.product) { .observer.product = "azure-ad" }

### ECS event base defaults
if !exists(.event.dataset) { .event.dataset = "azure-ad.logs" }
.event.category = ["authentication"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse JSON message
##################################################
raw = to_string(.message) ?? to_string(.) ?? ""

# Parse JSON format
json_parsed, json_err = parse_json(raw)

##################################################
### Process Microsoft/Azure AD fields
##################################################
if json_err == null && is_object(json_parsed) {
    # Microsoft/Azure AD specific fields
    if exists(json_parsed.Level) { 
        level_num = to_int(json_parsed.Level) ?? 0
        if level_num <= 2 { .log.level = "critical" }
        if level_num == 3 { .log.level = "error" }
        if level_num == 4 { .log.level = "warn" }
        if level_num == 5 { .log.level = "info" }
        if level_num >= 6 { .log.level = "debug" }
    }
    
    if exists(json_parsed.callerIpAddress) { .source.ip = json_parsed.callerIpAddress }
    if exists(json_parsed.ipAddress) { .source.ip = json_parsed.ipAddress }
    
    if exists(json_parsed.identity) { .user.name = json_parsed.identity }
    if exists(json_parsed.userDisplayName) { .user.name = json_parsed.userDisplayName }
    if exists(json_parsed.userPrincipalName) { .user.name = json_parsed.userPrincipalName }
    
    if exists(json_parsed.operationName) { .event.action = downcase(string!(json_parsed.operationName)) }
    
    if exists(json_parsed.correlationId) { .session.id = json_parsed.correlationId }
    
    if exists(json_parsed.location) { .geo.country_iso_code = json_parsed.location }
    if exists(json_parsed.countryOrRegion) { .geo.country_iso_code = json_parsed.countryOrRegion }
    
    if exists(json_parsed.appDisplayName) { .service.name = json_parsed.appDisplayName }
    if exists(json_parsed.resourceDisplayName) { .service.name = json_parsed.resourceDisplayName }
    
    if exists(json_parsed.conditionalAccessStatus) { .event.outcome = json_parsed.conditionalAccessStatus }
    
    if exists(json_parsed.time) { .@timestamp = json_parsed.time }
    if exists(json_parsed.createdDateTime) { .@timestamp = json_parsed.createdDateTime }
    
    # Device information
    if exists(json_parsed.deviceDetail) {
        if is_object(json_parsed.deviceDetail) {
            if exists(json_parsed.deviceDetail.displayName) { .host.name = json_parsed.deviceDetail.displayName }
            if exists(json_parsed.deviceDetail.operatingSystem) { .host.os.name = json_parsed.deviceDetail.operatingSystem }
            if exists(json_parsed.deviceDetail.browser) { .user_agent.name = json_parsed.deviceDetail.browser }
        }
    }
    
    # Authentication details
    if exists(json_parsed.authenticationRequirement) { .event.type = ["authentication"] }
    if exists(json_parsed.userType) { .user.type = json_parsed.userType }
    if exists(json_parsed.isInteractive) { 
        if json_parsed.isInteractive == true { .event.type = ["start"] }
        if json_parsed.isInteractive == false { .event.type = ["info"] }
    }
}

##################################################
### Related entities
##################################################
.related.ip = []
.related.user = []

if exists(.source.ip) { .related.ip = push(.related.ip, .source.ip) }
if exists(.user.name) { .related.user = push(.related.user, .user.name) }

.related.ip = unique(flatten(.related.ip))
.related.user = unique(flatten(.related.user))

##################################################
### Timestamp and metadata
##################################################
# Note: No now() fallback - only use parsed timestamps
.log.original = raw

##################################################
### Compact final object
##################################################
. = compact(., string: true, array: true, object: true, null: true)'''
    
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
        """Generate comprehensive VRL code that extracts ALL fields using AI (NO HARDCODING)"""
        try:
            # ✅ USE AI TO GENERATE VRL WITH GROK PATTERNS - NO HARDCODING!
            # Search RAG for examples
            rag_results = self.rag_system.search(f"VRL parser for {log_format} logs with GROK patterns", k=3)
            rag_context = "\n".join([doc.page_content[:300] for doc in rag_results]) if rag_results else "No examples found"
            
            # Create comprehensive prompt matching GPT-4o's structure and quality
            vrl_prompt = f"""Generate PRODUCTION-READY VRL parser for this log with EXCELLENT structure and indentation.

IMPORTANT: VRL is NOT Python/JavaScript - it has NO imports, NO functions definitions, NO classes!

LOG TO ANALYZE:
{log_content}

FORMAT: {log_format}

CRITICAL REQUIREMENTS - GENERATE LIKE A PROFESSIONAL VECTOR ENGINEER:

1. ANALYZE LOG STRUCTURE:
   - Identify ALL fields in the log (timestamps, IPs, ports, usernames, etc.)
   - Create GROK patterns that MATCH the actual log structure
   - Extract EVERY meaningful field from the log

2. PERFECT STRUCTURE & INDENTATION:
   - Use clear section headers with ############ and ####
   - Proper 2-space indentation throughout
   - Descriptive comments for each section
   - Logical grouping of operations
   - Clean, readable code

3. PROPER FIELD RENAMING & LOGIC:
   - Use pattern: if exists(.old_field) {{ .new_field = del(.old_field) }}
   - Map to proper ECS fields: @timestamp, host.hostname, source.ip, destination.ip, source.port, destination.port, user.name, event.action, event.outcome, log.level, message, etc.
   - For fields NOT in ECS schema: Move to event_data.field_name
   - Clean deletion with del() function for EVERY extracted field

4. ADVANCED GROK PATTERNS:
   - Use parse_groks() with multiple patterns
   - ONLY use standard GROK syntax: %{{PATTERN:field_name}}
   - Include fallback: "%{{GREEDYDATA:unparsed}}"
   - NEVER use regex (?<field>...) or made-up patterns
   - Common patterns: %{{TIMESTAMP_ISO8601}}, %{{IP}}, %{{HOSTNAME}}, %{{INT}}, %{{WORD}}, %{{NOTSPACE}}, %{{DATA}}, %{{GREEDYDATA}}

5. SMART LOGIC & ERROR HANDLING:
   - Priority calculation: .log.syslog.facility.code = floor(priority / 8)
   - Severity mapping: 8 levels (emergency, alert, critical, error, warning, notice, informational, debug)
   - Event outcome: failure for errors, success otherwise
   - Type conversions: to_int!() for ports/numbers, downcase!() for strings
   - Related entities: arrays for hosts, IPs, users

6. TIMESTAMP PROCESSING:
   - NEVER use ?? now() fallback
   - Use: parsed_ts, err = parse_timestamp(.field, "%Y-%m-%dT%H:%M:%S%.f%:z")
         if err == null {{ .@timestamp = parsed_ts }}
   - NEVER use to_timestamp!() on strings

RAG EXAMPLES:
{rag_context}

VRL SYNTAX RULES:
- VRL has NO imports (no import statements!)
- VRL has NO function definitions (no def or function)
- VRL has NO classes
- VRL is a transformation language, not programming language
- Start directly with comments and code
- NEVER add: import @vrl/..., def function(), class Parser, etc.

EXACT OUTPUT FORMAT (match this structure exactly - NO IMPORTS!):
###############################################################
## VRL Transforms for {log_format.title()} Logs
###############################################################

#### Adding ECS fields ####
if !exists(.observer.type) {{ .observer.type = "host" }}
if !exists(.observer.vendor) {{ .observer.vendor = "syslog" }}
if !exists(.observer.product) {{ .observer.product = "{log_format.lower()}" }}
if !exists(.event.dataset) {{ .event.dataset = "{log_format.lower()}.logs" }}
.event.category = ["network"]
.event.kind = "event"

#### Adding log metadata for visibility ####
.log_type = "{log_format}"
.log_format = "{log_format}"
.log_source = "detected_from_log"
.vendor = .observer.vendor
.product = .observer.product

#### Parse log message ####
raw = to_string(.message) ?? to_string(.) ?? ""

_grokked, err = parse_groks(raw, [
  "[BUILD COMPLETE GROK WITH %{{PATTERN:field}} SYNTAX]",
  "%{{GREEDYDATA:unparsed}}"
])

if err == null {{ . = merge(., _grokked, deep: true) }}

#### Priority calculation (for syslog) ####
if exists(.priority) {{
  priority_int = to_int(.priority) ?? 0
  .log.syslog.facility.code = floor(priority_int / 8)
  .log.syslog.severity.code = mod(priority_int, 8)
  
  severity = .log.syslog.severity.code
  if severity == 0 {{ .log.level = "emergency" }}
  if severity == 1 {{ .log.level = "alert" }}
  if severity == 2 {{ .log.level = "critical" }}
  if severity == 3 {{ .log.level = "error" }}
  if severity == 4 {{ .log.level = "warning" }}
  if severity == 5 {{ .log.level = "notice" }}
  if severity == 6 {{ .log.level = "informational" }}
  if severity == 7 {{ .log.level = "debug" }}
  
  del(.priority)
}}

#### Parse timestamp ####
if exists(.timestamp) {{
  parsed_ts, ts_err = parse_timestamp(.timestamp, "%Y-%m-%dT%H:%M:%S%.f%:z")
  if ts_err == null {{ .@timestamp = parsed_ts }}
  del(.timestamp)
}}

#### Field extraction and ECS mapping ####
if exists(.hostname) {{
  .host.hostname = del(.hostname)
  .host.name = .host.hostname
}}

if exists(.service) {{
  .service.name = del(.service)
  .process.name = .service.name
}}

if exists(.level) {{
  .log.level = downcase!(del(.level)) ?? null
}}

if exists(.source_ip) {{ .source.ip = del(.source_ip) }}
if exists(.dest_ip) {{ .destination.ip = del(.dest_ip) }}
if exists(.source_port) {{ .source.port = to_int!(del(.source_port)) ?? null }}
if exists(.dest_port) {{ .destination.port = to_int!(del(.dest_port)) ?? null }}
if exists(.username) {{ .user.name = del(.username) }}

#### Store non-ECS fields in event_data ####
# Initialize event_data for custom/vendor-specific fields
if !exists(.event_data) {{ .event_data = {{}} }}

# IMPORTANT: Move fields that are NOT in ECS schema to event_data
# Standard ECS fields: @timestamp, host.*, source.*, destination.*, user.*, event.*, log.*, observer.*, network.*, process.*, file.*, service.*, related.*
# Non-ECS fields should go to: .event_data.field_name

# Example: If you parsed vendor-specific fields like .session_id, .app_name, .custom_status
# if exists(.session_id) {{ .event_data.session_id = del(.session_id) }}
# if exists(.app_name) {{ .event_data.app_name = del(.app_name) }}
# if exists(.custom_status) {{ .event_data.custom_status = del(.custom_status) }}

# Add mappings for ANY field that's not in ECS standard

#### Event outcome logic ####
if exists(.log.level) {{
  level = .log.level
  if level == "error" || level == "err" || level == "critical" || level == "alert" || level == "emergency" {{
        .event.outcome = "failure"
  }} else {{
        .event.outcome = "success"
  }}
}}

#### Related entities ####
.related.hosts = []
if exists(.host.hostname) {{ .related.hosts = push(.related.hosts, .host.hostname) }}
.related.hosts = unique(flatten(.related.hosts))

.related.ip = []
if exists(.source.ip) {{ .related.ip = push(.related.ip, .source.ip) }}
if exists(.destination.ip) {{ .related.ip = push(.related.ip, .destination.ip) }}
.related.ip = unique(flatten(.related.ip))

#### Set original log ####
.event.original = raw

#### Cleanup temp fields ####
del(.version)
del(.procid)
del(.msgid)
del(.structdata)

#### Compact final object ####
. = compact(., string: true, array: true, object: true, null: true)

CRITICAL: 
- Generate ONLY pure VRL code (NO imports, NO def, NO class)
- Start with ###############################################################
- NO explanations before or after the code
- NO "Below is the VRL parser" or similar text
- NO Python/JavaScript syntax
- Just the VRL code with exact indentation (2 spaces)"""
            
            # Use Ollama AI to generate VRL
            response = self.llm.invoke(vrl_prompt)
            vrl_code = response.strip()
            
            # Clean up markdown if present
            if vrl_code.startswith("```"):
                lines = vrl_code.split('\n')
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                vrl_code = '\n'.join(lines[start_idx:end_idx])
            
            # Remove any preamble text before the actual VRL code
            lines = vrl_code.split('\n')
            cleaned_lines = []
            vrl_started = False
            
            for line in lines:
                # Skip invalid VRL syntax
                if line.strip().startswith('import '):
                    continue
                if line.strip().startswith('from '):
                    continue
                if 'Below is' in line or 'Here is' in line:
                    continue
                if line.strip().startswith('def '):
                    continue
                if line.strip().startswith('class '):
                    continue
                
                # VRL starts with # or ##
                if not vrl_started and (line.startswith('#') or line.startswith('if ') or line.startswith('.')):
                    vrl_started = True
                
                if vrl_started:
                    cleaned_lines.append(line)
            
            vrl_code = '\n'.join(cleaned_lines).strip()
            
            # If AI generation has placeholders, clean them up
            if "GROK-PATTERN-HERE" in vrl_code or "BUILD" in vrl_code:
                # Replace placeholders with actual pattern based on log content
                import re
                # Simple fallback: use parse_syslog/parse_json based on format
                if log_format == "json":
                    vrl_code = vrl_code.replace("[BUILD COMPLETE GROK PATTERN WITH %{PATTERN:field} SYNTAX]", 
                                               "# Parse JSON\njson_parsed, json_err = parse_json(raw)\nif json_err == null { . = merge(., json_parsed, deep: true) }")
                elif log_format == "syslog":
                    vrl_code = vrl_code.replace("[BUILD COMPLETE GROK PATTERN WITH %{PATTERN:field} SYNTAX]",
                                               "# Parse syslog\nsyslog_parsed, syslog_err = parse_syslog(raw)\nif syslog_err == null { . = merge(., syslog_parsed, deep: true) }")
                else:
                    vrl_code = vrl_code.replace("[BUILD COMPLETE GROK PATTERN WITH %{PATTERN:field} SYNTAX]",
                                               "# Parse key-value\nkv_parsed, kv_err = parse_key_value(raw)\nif kv_err == null { . = merge(., kv_parsed, deep: true) }")
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
