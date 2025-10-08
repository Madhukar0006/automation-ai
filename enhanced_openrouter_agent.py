"""
Enhanced OpenRouter Agent for Log Parsing with GPT-4
A high-performance agent using OpenRouter API with GPT-4 for superior parsing quality
"""

import json
import re
import os
from typing import Dict, List, Any, Optional
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import HumanMessage, AIMessage

from complete_rag_system import CompleteRAGSystem
from log_analyzer import identify_log_type
from lc_bridge import generate_ecs_json_lc as generate_ecs_json
from token_usage_tracker import track_openrouter_usage


class EnhancedOpenRouterAgent:
    """Enhanced agent using OpenRouter with GPT-4 for superior log parsing"""
    
    def __init__(self, rag_system: CompleteRAGSystem, openrouter_api_key: str = None):
        self.rag_system = rag_system
        
        # Set up OpenRouter API key
        if openrouter_api_key:
            os.environ["OPENROUTER_API_KEY"] = openrouter_api_key
        elif not os.environ.get("OPENROUTER_API_KEY"):
            raise ValueError("OpenRouter API key must be provided either as parameter or environment variable")
        
        # Initialize GPT-4 via OpenRouter
        self.llm = ChatOpenAI(
            model="openai/gpt-4o",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
            temperature=0.0,  # Lower temperature for more consistent parsing
            max_tokens=3000,  # Increased to allow complete VRL with all logic sections
            extra_headers={
                "HTTP-Referer": "https://parserautomation.local",
                "X-Title": "Log Parser Automation"
            }
        )
        
        # Create memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Enhanced prompt template with better instructions for GPT-4
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert VRL (Vector Remap Language) parser developer and log analysis specialist with deep expertise in cybersecurity, network monitoring, and log analysis.

Your primary task is to generate, validate, and optimize VRL parsers for various log formats including syslog, JSON, CEF, and vendor-specific formats.

EXPERTISE AREAS:
1. Log type identification and classification with high accuracy
2. VRL parser generation using advanced patterns and GROK expressions
3. VRL validation and error fixing with comprehensive error handling
4. ECS (Elastic Common Schema) field mapping with proper normalization
5. Knowledge base search for examples and best practices
6. Vendor-specific log format expertise (Cisco, Fortinet, Palo Alto, Check Point, etc.)

PARSING REQUIREMENTS:
- Generate comprehensive VRL parsers that extract ALL relevant fields
- Use proper ECS field mappings and normalization
- Include robust error handling and fallback mechanisms
- Provide detailed explanations for complex parsing logic
- Ensure parsers are production-ready and optimized
- Follow VRL best practices and performance guidelines

OUTPUT FORMAT:
- Always provide clear, well-commented VRL code in proper code blocks
- Include detailed explanations of parsing logic
- Show field mappings and transformations
- Provide validation results and recommendations
- Be thorough and ensure generated parsers follow industry best practices

QUALITY STANDARDS:
- Aim for 95%+ field extraction accuracy
- Include comprehensive error handling
- Optimize for performance and maintainability
- Follow security best practices for log parsing
- Ensure compatibility with major SIEM platforms"""),
            ("human", "{input}")
        ])
    
    def identify_log_type_enhanced(self, log_content: str) -> Dict[str, Any]:
        """Enhanced log type identification using GPT-4 with improved accuracy"""
        try:
            # Create specialized prompt for log identification
            identification_prompt = f"""Classify this log:

{log_content[:200]}...

Return JSON:
{{"log_format": "format", "vendor": "vendor", "product": "product", "key_fields": {{"field1": "value1"}}}}"""
            
            # Use GPT-4 for enhanced classification
            chain = self.prompt | self.llm
            response = chain.invoke({"input": identification_prompt})
            
            # Track token usage
            if hasattr(response, 'response_metadata') and 'token_usage' in response.response_metadata:
                track_openrouter_usage(response.response_metadata['token_usage'], "gpt-4o")
            
            # Extract JSON from response
            response_text = response.content.strip()
            
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
            else:
                # Fallback to basic classification
                result = self._fallback_classification(log_content)
            
            # Validate and enhance result
            result = self._validate_and_enhance_classification(result, log_content)
            
            return {"success": True, "result": result}
            
        except Exception as e:
            # Fallback to basic classification on error
            fallback_result = self._fallback_classification(log_content)
            return {"success": True, "result": fallback_result, "warning": f"Used fallback classification due to: {str(e)}"}
    
    def _fallback_classification(self, log_content: str) -> Dict[str, Any]:
        """Fallback classification using pattern matching"""
        # Basic format detection
        log_format = identify_log_type(log_content)
        
        # Vendor detection
        vendor = "unknown"
        product = "unknown"
        log_source = "unknown"
        observer_type = "unknown"
        confidence = "low"
        
        # Enhanced vendor detection patterns
        if re.search(r'(?i)(cisco|asa|ios|nexus|cat|switch|router|firewall)', log_content):
            vendor = "cisco"
            if re.search(r'(?i)(asa|firewall)', log_content):
                product = "asa"
                log_source = "cisco_asa"
                observer_type = "firewall"
            elif re.search(r'(?i)(ios)', log_content):
                product = "ios"
                log_source = "cisco_ios"
                observer_type = "network"
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
            product = "smartdefence"
            log_source = "checkpoint_firewall"
            observer_type = "ngfw"
            confidence = "medium"
        elif log_format == "json":
            vendor = "application"
            product = "json_logger"
            log_source = "json_application"
            observer_type = "application"
            confidence = "low"
        elif log_format == "syslog":
            vendor = "linux"
            product = "syslog"
            log_source = "linux_syslog"
            observer_type = "system"
            confidence = "low"
        
        return {
            "log_format": log_format,
            "vendor": vendor,
            "product": product,
            "log_source": log_source,
            "observer_type": observer_type,
            "confidence": confidence,
            "parsing_complexity": "simple",
            "key_indicators": ["pattern_matching"],
            "recommended_parser": "generic"
        }
    
    def _validate_and_enhance_classification(self, result: Dict[str, Any], log_content: str) -> Dict[str, Any]:
        """Validate and enhance classification result"""
        # Ensure required fields exist
        required_fields = ["log_format", "vendor", "product", "log_source", "observer_type", "confidence"]
        for field in required_fields:
            if field not in result:
                result[field] = "unknown"
        
        # Normalize values
        if result["log_format"] not in ["syslog", "json", "cef", "keyvalue", "other"]:
            result["log_format"] = "other"
        
        if result["confidence"] not in ["high", "medium", "low"]:
            result["confidence"] = "low"
        
        # Enhance with additional context
        result["log_length"] = len(log_content)
        result["has_timestamp"] = bool(re.search(r'\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}', log_content))
        result["has_ip_address"] = bool(re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', log_content))
        
        return result
    
    def generate_vrl_parser_enhanced(self, log_content: str, log_format: str = None) -> Dict[str, Any]:
        """Generate enhanced VRL parser using GPT-4 with superior quality"""
        try:
            if not log_format:
                # Auto-detect log format
                log_format = identify_log_type(log_content)
            
            # Analyze the log structure first
            log_analysis = self._analyze_log_structure(log_content)
            
            # Create enhanced prompt for VRL generation with excellent structure
            vrl_prompt = f"""Generate PRODUCTION-READY VRL parser for this log with EXCELLENT structure:

LOG TO ANALYZE:
{log_content}

LOG STRUCTURE ANALYSIS:
{log_analysis}

FORMAT: {log_format}

CRITICAL REQUIREMENTS - ANALYZE THE LOG AND GENERATE CORRECT PARSER:

1. ANALYZE LOG STRUCTURE:
   - Identify ALL fields in the log (timestamps, IPs, ports, usernames, etc.)
   - Create GROK patterns that MATCH the actual log structure
   - Extract EVERY meaningful field from the log

2. PERFECT STRUCTURE & INDENTATION:
   - Use clear section headers with #### and ###
   - Proper 2-space indentation
   - Descriptive comments for each section
   - Logical grouping of operations

3. PROPER FIELD RENAMING & LOGIC:
   - Use pattern: if exists(.old_field) {{ .new_field = del(.old_field) }}
   - Map to proper ECS fields
   - Clean deletion with del() function

4. ADVANCED GROK PATTERNS:
   - Use parse_groks() with multiple patterns
   - Include fallback: "%{{GREEDYDATA:unparsed}}"
   - Use named captures: (?<name>pattern)
   - Create patterns that ACTUALLY MATCH the log structure

5. SMART LOGIC & ERROR HANDLING:
   - Conditional processing based on field values
   - Proper null checks and validation
   - Outcome determination (success/failure)

6. DATA PROCESSING:
   - Use parse_key_value!() for structured data
   - TIMESTAMP PROCESSING (CRITICAL - USE CORRECT FUNCTIONS):
     * parse_timestamp(string, format) - parses timestamp string
     * format_timestamp(timestamp, format) - formats timestamp
     * NEVER use to_timestamp!() on strings - IT DOES NOT EXIST
     * NEVER use ?? now() fallback - user doesn't want current time as fallback
     * Example with error handling:
       parsed_ts, err = parse_timestamp(.timestamp, "%Y-%m-%d %H:%M:%S")
       if err == null {{ .@timestamp = parsed_ts }}
     * Example infallible (only if timestamp is guaranteed valid):
       .@timestamp = parse_timestamp!(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ")
   - Data merging with merge() function

EXACT OUTPUT FORMAT:
###############################################################
## VRL Transforms for {log_format.title()} Logs
###############################################################      

#### Adding ECS fields ####
if !exists(.observer.type) {{ .observer.type = "application" }}
if !exists(.observer.vendor) {{ .observer.vendor = "unknown" }}
if !exists(.observer.product) {{ .observer.product = "{log_format.lower()}" }}
if !exists(.event.dataset) {{ .event.dataset = "{log_format.lower()}.logs" }}

#### Adding log metadata for visibility ####
.log_type = "{log_format}"
.log_format = "{log_format}"
.log_source = "detected_from_log"
.vendor = .observer.vendor
.product = .observer.product

#### Parse log message ####
if exists(.event.original) {{ 
  _grokked, err = parse_groks(.event.original, [
    "[GROK-PATTERN-1]",
    "[GROK-PATTERN-2]",
    "%{{GREEDYDATA:unparsed}}"
  ])
  if err == null {{     
   . = merge(., _grokked, deep: true)
  }}
}}

#### Field extraction and ECS mapping ####
if exists(.field1) {{ .ecs_field1 = del(.field1) }}
if exists(.field2) {{ .ecs_field2 = del(.field2) }}

#### Store non-ECS fields in event_data ####
# Initialize event_data for custom fields not in ECS schema
if !exists(.event_data) {{ .event_data = {{}} }}

# Move any remaining parsed fields that are not ECS standard to event_data
# Example: if exists(.custom_field) {{ .event_data.custom_field = del(.custom_field) }}

#### Timestamp processing (USE CORRECT FUNCTIONS - NO now() FALLBACK) ####
if exists(.timestamp) {{
  parsed_ts, ts_err = parse_timestamp(.timestamp, "%Y-%m-%dT%H:%M:%S%.fZ")
  if ts_err == null {{ .@timestamp = parsed_ts }}
}}

#### Smart logic and outcome determination ####
if exists(.error_field) && .error_field == "0" {{
   .event.outcome = "success"
}} else if exists(.error_field) && .error_field != "0" {{
   .event.outcome = "failure"
}}

#### Cleanup ####
del(.temp_field1)
del(.temp_field2)
. = compact(., string: true, array: true, object: true, null: true)

Generate ONLY the VRL code above with proper GROK patterns, field renaming, and logic."""
            
            # Use GPT-4 for enhanced VRL generation
            chain = self.prompt | self.llm
            response = chain.invoke({"input": vrl_prompt})
            
            # Track token usage
            if hasattr(response, 'response_metadata') and 'token_usage' in response.response_metadata:
                track_openrouter_usage(response.response_metadata['token_usage'], "gpt-4o")
            
            # Extract VRL code from response
            vrl_code = response.content.strip()
            
            # Clean up the response (remove markdown formatting if present)
            if vrl_code.startswith("```"):
                lines = vrl_code.split('\n')
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                vrl_code = '\n'.join(lines[start_idx:end_idx])
            
            # Validate the generated VRL
            validation_result = self.validate_vrl_enhanced(vrl_code)
            
            return {
                "success": True,
                "vrl_code": vrl_code,
                "log_format": log_format,
                "validation": validation_result,
                "generation_method": "gpt4_enhanced"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _analyze_log_structure(self, log_content: str) -> str:
        """Analyze log structure to help generate correct GROK patterns"""
        analysis = []
        
        # Basic log analysis
        analysis.append(f"LOG LENGTH: {len(log_content)} characters")
        analysis.append(f"LOG TYPE: {'Syslog' if log_content.startswith('<') else 'Other'}")
        
        # Analyze common patterns
        if log_content.startswith('<'):
            analysis.append("SYSLOG HEADER DETECTED:")
            analysis.append(f"  - Priority: {log_content[1:log_content.find('>')] if '>' in log_content else 'Not found'}")
            analysis.append(f"  - Version: {log_content[log_content.find('>')+1:log_content.find('>')+2] if '>' in log_content else 'Not found'}")
        
        # Look for timestamps
        import re
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO8601
            r'\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',  # Apache style
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'  # Standard format
        ]
        
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, log_content)
            if matches:
                analysis.append(f"TIMESTAMP DETECTED: {matches[0]}")
                break
        
        # Look for IP addresses
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, log_content)
        if ips:
            analysis.append(f"IP ADDRESSES: {', '.join(ips)}")
        
        # Look for ports
        port_pattern = r':(\d{4,5})'
        ports = re.findall(port_pattern, log_content)
        if ports:
            analysis.append(f"PORTS: {', '.join(ports)}")
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, log_content)
        if emails:
            analysis.append(f"EMAIL ADDRESSES: {', '.join(emails)}")
        
        # Look for bracketed sections
        bracket_pattern = r'\[([^\]]+)\]'
        brackets = re.findall(bracket_pattern, log_content)
        if brackets:
            analysis.append(f"BRACKETED SECTIONS: {', '.join(brackets[:5])}")  # Limit to first 5
        
        # Look for key-value pairs
        kv_pattern = r'(\w+)=([^\s]+)'
        kv_pairs = re.findall(kv_pattern, log_content)
        if kv_pairs:
            analysis.append(f"KEY-VALUE PAIRS: {', '.join([f'{k}={v}' for k, v in kv_pairs[:3]])}")
        
        return '\n'.join(analysis)
    
    def validate_vrl_enhanced(self, vrl_code: str) -> Dict[str, Any]:
        """Enhanced VRL validation using GPT-4"""
        try:
            validation_prompt = f"""
You are a VRL syntax expert. Analyze this VRL code for syntax errors, best practices, and potential improvements.

VRL CODE TO VALIDATE:
```vrl
{vrl_code}
```

Please provide a JSON response with:
{{
    "syntax_valid": true/false,
    "errors": ["list of syntax errors if any"],
    "warnings": ["list of warnings or suggestions"],
    "best_practices_score": "1-10 rating",
    "performance_score": "1-10 rating",
    "maintainability_score": "1-10 rating",
    "recommendations": ["list of improvement suggestions"],
    "required_fields_present": ["list of ECS fields that should be present"],
    "missing_fields": ["list of important missing fields"]
}}

Focus on:
1. VRL syntax correctness
2. ECS field mapping completeness
3. Error handling robustness
4. Performance optimization opportunities
5. Code maintainability and readability
6. Security considerations

Return ONLY the JSON object.
"""
            
            # Use GPT-4 for enhanced validation
            chain = self.prompt | self.llm
            response = chain.invoke({"input": validation_prompt})
            
            # Extract JSON from response
            response_text = response.content.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                validation_result = json.loads(json_match.group())
            else:
                # Fallback validation
                validation_result = self._fallback_validation(vrl_code)
            
            return validation_result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _fallback_validation(self, vrl_code: str) -> Dict[str, Any]:
        """Fallback validation using basic checks"""
        errors = []
        warnings = []
        
        # Basic syntax checks
        if not vrl_code.strip():
            errors.append("VRL code is empty")
        
        # Check for required ECS fields
        required_fields = [".event.kind", ".event.category", ".@timestamp"]
        missing_fields = []
        for field in required_fields:
            if field not in vrl_code:
                missing_fields.append(field)
        
        if missing_fields:
            warnings.append(f"Missing recommended ECS fields: {', '.join(missing_fields)}")
        
        # Check for common issues
        if "parse_json" in vrl_code and "json_err" not in vrl_code:
            warnings.append("JSON parsing without error handling")
        
        if "parse_syslog" in vrl_code and "syslog_err" not in vrl_code:
            warnings.append("Syslog parsing without error handling")
        
        return {
            "syntax_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "best_practices_score": 7 if len(warnings) < 3 else 5,
            "performance_score": 8,
            "maintainability_score": 7,
            "recommendations": ["Add more error handling", "Include comprehensive field extraction"],
            "required_fields_present": [field for field in required_fields if field in vrl_code],
            "missing_fields": missing_fields
        }
    
    def generate_ecs_mapping_enhanced(self, log_content: str) -> Dict[str, Any]:
        """Generate enhanced ECS mapping using GPT-4"""
        try:
            ecs_prompt = f"""
You are an ECS (Elastic Common Schema) expert. Generate a comprehensive ECS field mapping for this log entry.

LOG TO ANALYZE:
{log_content}

REQUIREMENTS:
1. Map all relevant fields to proper ECS field names
2. Include proper data type conversions
3. Add field descriptions and examples
4. Ensure compliance with ECS specification
5. Include both required and recommended fields

Please provide a JSON response with:
{{
    "ecs_fields": {{
        "field_name": {{
            "value": "extracted_value",
            "type": "string|integer|boolean|array|object",
            "description": "field description",
            "required": true/false,
            "example": "example value"
        }}
    }},
    "field_mappings": {{
        "source_field": "target_ecs_field"
    }},
    "transformation_notes": ["notes about data transformations"],
    "compliance_score": "1-10 rating of ECS compliance"
}}

Focus on:
1. Proper ECS field naming conventions
2. Appropriate data types
3. Required vs optional fields
4. Field relationships and dependencies
5. Security and privacy considerations

Return ONLY the JSON object.
"""
            
            # Use GPT-4 for enhanced ECS mapping
            chain = self.prompt | self.llm
            response = chain.invoke({"input": ecs_prompt})
            
            # Extract JSON from response
            response_text = response.content.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                ecs_result = json.loads(json_match.group())
                return {"success": True, "result": ecs_result}
            else:
                # Fallback to existing ECS generation
                fallback_result = generate_ecs_json("Generate ECS mapping", log_content)
                return {"success": True, "result": fallback_result, "method": "fallback"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def chat_enhanced(self, message: str) -> str:
        """Enhanced chat interface with GPT-4"""
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
                {"output": response.content}
            )
            
            return response.content
            
        except Exception as e:
            return f"Enhanced chat failed: {str(e)}"
    
    def run_enhanced_workflow(self, log_content: str) -> Dict[str, Any]:
        """Run the enhanced 4-agent workflow with GPT-4"""
        
        workflow_results = {
            "log_content": log_content,
            "steps": [],
            "final_vrl": None,
            "success": False,
            "enhancement_level": "gpt4_enhanced"
        }
        
        try:
            # Step 1: Enhanced Log Type Identification
            step1_result = self.identify_log_type_enhanced(log_content)
            workflow_results["steps"].append({
                "step": 1,
                "agent": "Enhanced Log Type Identifier (GPT-4)",
                "result": step1_result,
                "status": "completed" if step1_result["success"] else "failed"
            })
            
            # Step 2: Enhanced VRL Generation
            log_format = step1_result.get("result", {}).get("log_format", "unknown") if step1_result["success"] else "unknown"
            step2_result = self.generate_vrl_parser_enhanced(log_content, log_format)
            workflow_results["steps"].append({
                "step": 2,
                "agent": "Enhanced VRL Generator (GPT-4)",
                "result": step2_result,
                "status": "completed" if step2_result["success"] else "failed"
            })
            
            # Extract VRL code from step 2 if successful
            vrl_code = None
            if step2_result["success"]:
                vrl_code = step2_result.get("vrl_code", "")
            
            # Step 3: Enhanced VRL Validation
            if vrl_code:
                step3_result = self.validate_vrl_enhanced(vrl_code)
                workflow_results["steps"].append({
                    "step": 3,
                    "agent": "Enhanced VRL Validator (GPT-4)",
                    "result": step3_result,
                    "status": "completed"
                })
                workflow_results["final_vrl"] = vrl_code
            
            # Step 4: Enhanced ECS Mapping
            step4_result = self.generate_ecs_mapping_enhanced(log_content)
            workflow_results["steps"].append({
                "step": 4,
                "agent": "Enhanced ECS Mapper (GPT-4)",
                "result": step4_result,
                "status": "completed" if step4_result["success"] else "failed"
            })
            
            # Consider workflow successful if we have VRL code and ECS mapping
            workflow_results["success"] = vrl_code is not None and step4_result["success"]
            
            # Add performance metrics
            workflow_results["performance_metrics"] = {
                "total_steps": 4,
                "completed_steps": len([s for s in workflow_results["steps"] if s["status"] == "completed"]),
                "enhancement_level": "gpt4_enhanced",
                "quality_improvement": "superior_accuracy_and_completeness"
            }
            
        except Exception as e:
            workflow_results["error"] = str(e)
        
        return workflow_results


class EnhancedAgentOrchestrator:
    """Enhanced orchestrator for the GPT-4 powered log parsing agent"""
    
    def __init__(self, rag_system: CompleteRAGSystem, openrouter_api_key: str = None):
        self.rag_system = rag_system
        self.main_agent = EnhancedOpenRouterAgent(rag_system, openrouter_api_key)
        
    def run_enhanced_workflow(self, log_content: str) -> Dict[str, Any]:
        """Run the enhanced workflow"""
        return self.main_agent.run_enhanced_workflow(log_content)


# Convenience function to create enhanced agent system
def create_enhanced_log_parsing_agents(rag_system: CompleteRAGSystem, openrouter_api_key: str = None) -> EnhancedAgentOrchestrator:
    """Create and return the enhanced agent orchestrator"""
    return EnhancedAgentOrchestrator(rag_system, openrouter_api_key)


if __name__ == "__main__":
    # Example usage with your OpenRouter API key
    OPENROUTER_API_KEY = "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"
    
    print("Initializing RAG system...")
    rag_system = CompleteRAGSystem()
    rag_system.build_langchain_index()
    
    print("Creating enhanced GPT-4 agents...")
    orchestrator = create_enhanced_log_parsing_agents(rag_system, OPENROUTER_API_KEY)
    
    # Test with sample log
    sample_log = """<134>1 2024-01-15T10:30:45.123Z firewall.example.com asa 12345 - - %ASA-6-302013: Built outbound TCP connection 1234567890 for outside:203.0.113.5/80 (203.0.113.5/80) to inside:192.168.1.100/54321 (192.168.1.100/54321)"""
    
    print("Running enhanced GPT-4 workflow...")
    result = orchestrator.run_enhanced_workflow(sample_log)
    
    print(f"Enhanced workflow completed: {result['success']}")
    if result['success'] and result['final_vrl']:
        print("Generated Enhanced VRL:")
        print(result['final_vrl'])
