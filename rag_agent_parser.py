#!/usr/bin/env python3
"""
RAG-Based Agent Parser Generator
Uses RAG system to intelligently generate vendor-specific parsers
"""

import json
import re
from typing import Dict, Any, Optional, List
import requests

class RAGAgentParser:
    """AI Agent that uses RAG system to generate intelligent parsers"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.rag_system = None
        self.load_rag_system()
    
    def load_rag_system(self):
        """Load the RAG system for ECS field knowledge"""
        try:
            # Try to load existing RAG system
            from complete_rag_system import RAGSystem
            self.rag_system = RAGSystem()
            print("✅ RAG System loaded successfully")
        except ImportError:
            print("⚠️ RAG System not available, using basic field mapping")
            self.rag_system = None
    
    def analyze_log_with_rag(self, log_content: str, vendor: str, product: str) -> Dict[str, Any]:
        """Analyze log content using RAG system to determine optimal field mappings"""
        analysis = {
            "vendor": vendor,
            "product": product,
            "log_format": self.detect_log_format(log_content),
            "suggested_ecs_fields": [],
            "event_data_fields": [],
            "parsing_strategy": "generic",
            "confidence": "medium"
        }
        
        if self.rag_system:
            try:
                # Query RAG system for vendor-specific field mappings
                rag_query = f"ECS field mappings for {vendor} {product} logs"
                rag_results = self.rag_system.query(rag_query, top_k=10)
                
                if rag_results:
                    analysis["rag_insights"] = rag_results
                    analysis["confidence"] = "high"
                    
                    # Extract ECS field recommendations
                    for result in rag_results:
                        if "ecs_field" in result:
                            analysis["suggested_ecs_fields"].append(result["ecs_field"])
                        if "event_data_field" in result:
                            analysis["event_data_fields"].append(result["event_data_field"])
            except Exception as e:
                print(f"⚠️ RAG query failed: {e}")
        
        # Fallback analysis based on vendor patterns
        analysis.update(self.fallback_vendor_analysis(vendor, product, log_content))
        
        return analysis
    
    def detect_log_format(self, log_content: str) -> str:
        """Detect the log format"""
        if log_content.strip().startswith("CEF:"):
            return "cef"
        elif log_content.strip().startswith("{") or log_content.strip().startswith("["):
            return "json"
        elif "<" in log_content and ">" in log_content:
            return "syslog"
        else:
            return "unknown"
    
    def fallback_vendor_analysis(self, vendor: str, product: str, log_content: str) -> Dict[str, Any]:
        """Fallback analysis when RAG is not available"""
        vendor_lower = vendor.lower()
        product_lower = product.lower()
        
        analysis = {
            "parsing_strategy": "generic",
            "suggested_ecs_fields": [],
            "event_data_fields": [],
            "confidence": "medium"
        }
        
        # CheckPoint analysis
        if vendor_lower in ["checkpoint", "check point"]:
            analysis["parsing_strategy"] = "checkpoint_structured"
            analysis["suggested_ecs_fields"] = [
                "source.ip", "destination.ip", "network.protocol", 
                "event.action", "event.outcome", "observer.vendor"
            ]
            analysis["event_data_fields"] = [
                "checkpoint_flags", "checkpoint_loguid", "checkpoint_origin",
                "checkpoint_product", "checkpoint_version"
            ]
            analysis["confidence"] = "high"
        
        # Cisco analysis
        elif vendor_lower == "cisco":
            analysis["parsing_strategy"] = "cisco_asa"
            analysis["suggested_ecs_fields"] = [
                "source.ip", "destination.ip", "network.protocol",
                "user.name", "event.action", "network.interface.name"
            ]
            analysis["event_data_fields"] = [
                "cisco_message_id", "cisco_device", "cisco_connection_id",
                "cisco_interface_state"
            ]
            analysis["confidence"] = "high"
        
        # Fortinet analysis
        elif vendor_lower in ["fortinet", "fortigate"]:
            analysis["parsing_strategy"] = "fortinet_keyvalue"
            analysis["suggested_ecs_fields"] = [
                "source.ip", "destination.ip", "network.protocol",
                "user.name", "event.action", "url.full"
            ]
            analysis["event_data_fields"] = [
                "fortinet_policyid", "fortinet_sessionid", "fortinet_app",
                "fortinet_srcintf", "fortinet_dstintf"
            ]
            analysis["confidence"] = "high"
        
        return analysis
    
    def generate_parser_with_agent(self, log_content: str, vendor: str, product: str, log_profile: dict = None) -> str:
        """Generate parser using AI agent with RAG insights"""
        
        # Analyze log with RAG
        analysis = self.analyze_log_with_rag(log_content, vendor, product)
        
        # Create prompt for AI agent
        prompt = self.create_agent_prompt(log_content, analysis)
        
        # Generate parser using Ollama - NO FALLBACK TO TEMPLATES
        print(f"🤖 Generating {vendor.title()} parser with AI agent...")
        try:
            parser_code = self.call_ollama_agent(prompt)
            
            # Use AI-generated VRL directly (it should be proper VRL now)
            # Only apply minimal formatting if needed
            proper_vrl = self._format_ai_generated_vrl(parser_code, log_profile)
            
            print(f"✅ AI Agent generated {len(parser_code)} characters, converted to {len(proper_vrl)} characters of proper VRL")
            return proper_vrl
            
        except Exception as e:
            print(f"❌ AI Agent failed: {e}")
            raise Exception(f"AI Agent failed to generate parser: {e}. Please check Ollama connection.")
    
    def create_agent_prompt(self, log_content: str, analysis: Dict[str, Any]) -> str:
        """Create improved prompt for AI agent to generate proper VRL parser"""
        
        # Create improved prompt similar to GPT-4 system
        vendor = analysis.get('vendor', 'unknown').lower()
        product = analysis.get('product', 'unknown')
        
        prompt = f"""Generate SIMPLE VRL parser for this log:

LOG: {log_content[:300]}...
VENDOR: {vendor}
PRODUCT: {product}

CRITICAL REQUIREMENTS:
- Keep GROK pattern SIMPLE and SHORT
- Use basic field names: timestamp, hostname, message
- NO complex nested patterns
- Use proper VRL syntax: if exists(parsed.field) {{ .target = del(parsed.field) }}
- Essential field extraction only
- Test the pattern against the log

SIMPLE PATTERN EXAMPLE:
pattern = "<%{{POSINT:priority}}>%{{INT:version}} %{{TIMESTAMP_ISO8601:timestamp}} %{{HOSTNAME:hostname}} %{{GREEDYDATA:message}}"

OUTPUT FORMAT:
##################################################
## VRL Parser - {vendor.title()} {product.title()}
##################################################

### Parse log
raw = to_string(.message) ?? to_string(.) ?? ""
pattern = "[SIMPLE-GROK-PATTERN]"
parsed, err = parse_grok(raw, pattern)

if err != null {{
  .error = "Parse failed"
  . = compact(.)
  return
}}

### Extract basic fields
if exists(parsed.timestamp) {{ .@timestamp = parse_timestamp(del(parsed.timestamp), "%Y-%m-%dT%H:%M:%S%.3f%z") ?? now() }}
if exists(parsed.hostname) {{ .host.name = del(parsed.hostname) }}
if exists(parsed.message) {{ .message = del(parsed.message) }}

### Set basic ECS fields
.observer.type = "application"
.event.category = ["web"]
.event.kind = "event"

. = compact(.)

Generate ONLY the VRL code above with a SIMPLE GROK pattern that works."""
        
        return prompt

##################################################
### Parse CheckPoint Message
##################################################
raw_message = to_string(.message) ?? ""

# Parse CheckPoint structured data using parse_key_value
checkpoint_data, err = parse_key_value(raw_message, field_delimiter: " ", key_value_delimiter: ":")
if err == null && is_object(checkpoint_data) {{
    # Extract and map CheckPoint fields
    
    # Map origin to source IP
    if exists(checkpoint_data.origin) {{
        .source.ip = checkpoint_data.origin
        .source.address = checkpoint_data.origin
    }}
    
    # Store CheckPoint-specific fields in event_data
    if exists(checkpoint_data.flags) {{
        .event_data.checkpoint_flags = checkpoint_data.flags
    }}
    
    if exists(checkpoint_data.ifdir) {{
        .event_data.checkpoint_ifdir = checkpoint_data.ifdir
        .network.direction = checkpoint_data.ifdir
    }}
    
    if exists(checkpoint_data.ifname) {{
        .event_data.checkpoint_ifname = checkpoint_data.ifname
        .network.interface.name = checkpoint_data.ifname
    }}
    
    if exists(checkpoint_data.loguid) {{
        .event.id = checkpoint_data.loguid
        .event_data.checkpoint_loguid = checkpoint_data.loguid
    }}
    
    if exists(checkpoint_data.sequencenum) {{
        .event_data.checkpoint_sequencenum = checkpoint_data.sequencenum
    }}
    
    if exists(checkpoint_data.version) {{
        .event_data.checkpoint_version = checkpoint_data.version
    }}
    
    if exists(checkpoint_data.product) {{
        .observer.product = checkpoint_data.product
        .event_data.checkpoint_product = checkpoint_data.product
    }}
    
    if exists(checkpoint_data.sys_message) {{
        .message = checkpoint_data.sys_message
        .event_data.checkpoint_sys_message = checkpoint_data.sys_message
    }}
}}

##################################################
### Parse Standard Syslog Header
##################################################
syslog_parsed, syslog_err = parse_syslog(raw_message)
if syslog_err == null && is_object(syslog_parsed) {{
    if exists(syslog_parsed.timestamp) {{
        .@timestamp = syslog_parsed.timestamp
    }}
    
    if exists(syslog_parsed.hostname) {{
        .host.hostname = syslog_parsed.hostname
        .host.name = syslog_parsed.hostname
    }}
    
    if exists(syslog_parsed.appname) {{
        .service.name = syslog_parsed.appname
        .process.name = syslog_parsed.appname
    }}
}}

##################################################
### Event Categorization
##################################################
if exists(.message) {{
    msg = to_string(.message) ?? ""
    
    # Detect security events
    if contains(msg, "anti-spoofing") {{
        .event.category = ["network", "security"]
        .event.type = ["info", "vulnerability"]
        .event.action = "anti_spoofing_warning"
        .log.level = "warn"
    }}
    
    if contains(msg, "blocked") || contains(msg, "denied") {{
        .event.category = ["network", "security"]
        .event.type = ["denied"]
        .event.action = "firewall_block"
        .event.outcome = "failure"
        .log.level = "warn"
    }}
}}

##################################################
### Timestamps and Metadata
##################################################
if !exists(.@timestamp) {{ .@timestamp = now() }}
if !exists(.event.created) {{ .event.created = now() }}

.log.original = raw_message

##################################################
### Compact final object
##################################################
. = compact(., null: true)

VRL CODE ONLY - NO EXPLANATIONS:"""
        
        elif 'cisco' in vendor:
            prompt = f"""Generate VRL code ONLY (no explanations) for Cisco logs. Use ONLY valid VRL functions:

LOG: {log_content}
{rag_insights}

CRITICAL VRL SYNTAX RULES:
- Use ONLY valid VRL functions: parse_json(), parse_syslog(), parse_cef(), parse_key_value(), parse_grok()
- NO .map() functions (doesn't exist in VRL)
- NO extract() functions (doesn't exist in VRL) 
- NO if-then-else syntax (use if {{ }} instead)
- NO explanatory text, only VRL code

Generate VRL code that:
1. raw_message = to_string(.message) ?? ""
2. Uses parse_syslog() for Cisco syslog logs
3. Maps Cisco fields to ECS using if exists() checks
4. .observer.vendor = "Cisco"
5. .observer.product = "{analysis['product']}"

VRL code only:"""
        
        elif 'fortinet' in vendor:
            prompt = f"""Generate VRL code ONLY (no explanations) for Fortinet logs. Use ONLY valid VRL functions:

LOG: {log_content}
{rag_insights}

CRITICAL VRL SYNTAX RULES:
- Use ONLY valid VRL functions: parse_json(), parse_syslog(), parse_cef(), parse_key_value(), parse_grok()
- NO .map() functions (doesn't exist in VRL)
- NO extract() functions (doesn't exist in VRL) 
- NO if-then-else syntax (use if {{ }} instead)
- NO explanatory text, only VRL code

Generate VRL code that:
1. raw_message = to_string(.message) ?? ""
2. Uses parse_syslog() for Fortinet FortiGate logs
3. Maps Fortinet fields to ECS using if exists() checks
4. .observer.vendor = "Fortinet"
5. .observer.product = "{analysis['product']}"

VRL code only:"""
        
        else:
            prompt = f"""Generate VRL code ONLY (no explanations) for {analysis['vendor']} logs. Use ONLY valid VRL functions:

LOG: {log_content}
{rag_insights}

CRITICAL VRL SYNTAX RULES:
- Use ONLY valid VRL functions: parse_json(), parse_syslog(), parse_cef(), parse_key_value(), parse_grok()
- NO .map() functions (doesn't exist in VRL)
- NO extract() functions (doesn't exist in VRL) 
- NO if-then-else syntax (use if {{ }} instead)
- NO explanatory text, only VRL code

Generate VRL code that:
1. raw_message = to_string(.message) ?? ""
2. Uses appropriate parsing method:
   - parse_json() for JSON logs
   - parse_syslog() for syslog logs  
   - parse_cef() for CEF logs
   - parse_grok() for custom patterns
   - parse_key_value() for key=value pairs
3. Maps vendor-specific fields to ECS using if exists() checks
4. .observer.vendor = "{analysis['vendor'].title()}"
5. .observer.product = "{analysis['product']}"

VRL code only:"""

        return prompt
    
    def _format_ai_generated_vrl(self, ai_code: str, log_profile: dict = None) -> str:
        """Format AI-generated VRL code and apply log profile mapping"""
        
        # Clean up AI output
        vrl_code = ai_code.strip()
        
        # Remove code blocks, explanations, and non-VRL text
        import re
        
        # Remove common AI prefixes and explanations
        vrl_code = re.sub(r'^.*?(?=##################################################)', '', vrl_code, flags=re.DOTALL)
        vrl_code = re.sub(r'^.*?(?=### ECS)', '', vrl_code, flags=re.DOTALL)
        vrl_code = re.sub(r'^.*?(?=raw_message)', '', vrl_code, flags=re.DOTALL)
        
        # Remove explanatory text that appears after the VRL code
        vrl_code = re.sub(r'This VRL parser.*$', '', vrl_code, flags=re.DOTALL)
        vrl_code = re.sub(r'Here is.*?structure.*$', '', vrl_code, flags=re.DOTALL)
        
        # Remove code blocks
        vrl_code = re.sub(r'```vrl\n?', '', vrl_code)
        vrl_code = re.sub(r'```\n?', '', vrl_code)
        
        # Fix common VRL syntax errors
        vrl_code = re.sub(r'value_delimiter:', 'key_value_delimiter:', vrl_code)
        
        # Remove invalid VRL functions
        vrl_code = re.sub(r'\.map\([^)]*\)', '', vrl_code)  # Remove .map() functions
        vrl_code = re.sub(r'extract\([^)]*\)', '', vrl_code)  # Remove extract() functions
        vrl_code = re.sub(r'if\s+.*\s+then\s+', 'if ', vrl_code)  # Fix if-then syntax
        vrl_code = re.sub(r'\s+else\s+if\s+', ' else if ', vrl_code)  # Fix else-if syntax
        vrl_code = re.sub(r'\s+else\s+', ' else ', vrl_code)  # Fix else syntax
        vrl_code = re.sub(r'\s+end\s*$', '', vrl_code, flags=re.MULTILINE)  # Remove end statements
        
        # Apply log profile mapping if available
        if log_profile:
            vendor = log_profile.get('vendor', 'Unknown').title()
            product = log_profile.get('product', 'Unknown')
            log_type = log_profile.get('log_type', 'Security')
            
            # Intelligent mapping based on vendor/product context
            vendor = log_profile.get('vendor', '').lower()
            product = log_profile.get('product', '').lower()
            
            if 'openssh' in vendor or 'ssh' in product:
                observer_type = "system"
            elif 'checkpoint' in vendor or 'fortinet' in vendor or 'cisco' in vendor or 'palo' in vendor:
                observer_type = "ngfw"  # Next Generation Firewall
            elif 'apache' in vendor or 'nginx' in vendor or 'web' in product:
                observer_type = "application"
            elif log_type.lower() == 'security':
                observer_type = "ngfw"
            elif log_type.lower() == 'network':
                observer_type = "network"
            elif log_type.lower() == 'system':
                observer_type = "system"
            elif log_type.lower() == 'application':
                observer_type = "application"
            else:
                observer_type = "system"  # Default to system instead of ngfw
            
            # Replace vendor/product in the AI-generated code
            vrl_code = re.sub(r'\.observer\.vendor\s*=\s*"[^"]*"', f'.observer.vendor = "{vendor}"', vrl_code)
            vrl_code = re.sub(r'\.observer\.product\s*=\s*"[^"]*"', f'.observer.product = "{product}"', vrl_code)
            vrl_code = re.sub(r'\.observer\.type\s*=\s*"[^"]*"', f'.observer.type = "{observer_type}"', vrl_code)
        
        return vrl_code.strip()
    
    def call_ollama_agent(self, prompt: str) -> str:
        """Call Ollama to generate parser using AI agent with improved settings"""
        try:
            # Use improved settings for better VRL generation
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,  # Lower temperature for more consistent output
                        "top_p": 0.9,
                        "max_tokens": 2000,  # Reduced for better focus
                        "repeat_penalty": 1.1,
                        "stop": ["```", "###", "---"]  # Stop at code blocks
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"Failed to call Ollama: {e}")
    
    def generate_template_parser(self, analysis: Dict[str, Any]) -> str:
        """Generate parser using template when AI agent fails"""
        
        vendor = analysis['vendor'].lower()
        strategy = analysis['parsing_strategy']
        
        print(f"🔧 Using template parser for {vendor} with strategy {strategy}")
        
        if vendor == "checkpoint" or strategy == "checkpoint_structured":
            try:
                from checkpoint_parser import generate_checkpoint_parser
                print("✅ Using CheckPoint-specific parser")
                return generate_checkpoint_parser()
            except ImportError:
                print("⚠️ CheckPoint parser not available, using fallback")
        
        if vendor == "cisco" or strategy == "cisco_asa":
            try:
                from cisco_parser import generate_cisco_parser
                print("✅ Using Cisco-specific parser")
                return generate_cisco_parser()
            except ImportError:
                print("⚠️ Cisco parser not available, using fallback")
        
        if vendor == "fortinet" or strategy == "fortinet_keyvalue":
            try:
                from fortinet_parser import generate_fortinet_parser
                print("✅ Using Fortinet-specific parser")
                return generate_fortinet_parser()
            except ImportError:
                print("⚠️ Fortinet parser not available, using fallback")
        
        # Generic parser fallback
        try:
            from compact_syslog_parser import generate_compact_syslog_parser
            print("⚠️ Using generic syslog parser as fallback")
            return generate_compact_syslog_parser()
        except ImportError:
            # Last resort - return basic parser
            return """
# Basic VRL Parser Fallback
raw_message = to_string(.message) ?? ""
.event_data.raw_log = raw_message
.@timestamp = now()
.event.created = now()
.event.kind = "event"
.event.category = ["system"]
.event.type = ["info"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "system"
"""
    
    def validate_generated_parser(self, parser_code: str) -> Dict[str, Any]:
        """Validate the generated parser code"""
        validation = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "parser_length": len(parser_code)
        }
        
        # Basic VRL syntax checks
        required_elements = [
            "raw_message", "parse_", "event_data", "observer", "event"
        ]
        
        for element in required_elements:
            if element not in parser_code:
                validation["warnings"].append(f"Missing {element} in parser")
        
        # Check for common VRL errors
        if "??" in parser_code and "to_string" in parser_code:
            validation["warnings"].append("Potential unnecessary error coalescing")
        
        if "del(" not in parser_code:
            validation["warnings"].append("No field deletion - potential duplication")
        
        return validation


# Test the agent
if __name__ == "__main__":
    agent = RAGAgentParser()
    
    # Test with CheckPoint log
    test_log = """<134>1 2020-03-29T13:19:20Z gw-da58d3 CheckPoint 1930 - - [flags:"133440"; ifdir:"inbound"; ifname:"daemon"; loguid:"{0x5e80a059,0x0,0x6401a8c0,0x3c7878a}"; origin:"192.168.1.100"; sequencenum:"1"; version:"5"; product:"System Monitor"; sys_message::"The eth0 interface is not protected by the anti-spoofing feature. Your network may be at risk"]"""
    
    parser = agent.generate_parser_with_agent(test_log, "checkpoint", "smartdefence")
    print("Generated Parser Length:", len(parser))
    print("Parser Preview:", parser[:200] + "...")
