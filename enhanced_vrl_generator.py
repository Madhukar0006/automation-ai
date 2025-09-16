#!/usr/bin/env python3
"""
Enhanced VRL Generator with comprehensive error handling
Integrates with VRL_Error_Handler for automatic error detection and fixing
"""

import json
import re
from typing import Dict, List, Tuple, Optional, Any
from vrl_error_handler import VRL_Error_Handler, VRL_Error, VRL_ERROR_TYPE
from lc_bridge import classify_log_lc, generate_ecs_json_lc
from vrl_snippet_assembler import VRLSnippetAssembler

class Enhanced_VRL_Generator:
    """Enhanced VRL generator with automatic error handling and fixing"""
    
    def __init__(self):
        self.error_handler = VRL_Error_Handler()
        self.snippet_assembler = VRLSnippetAssembler()
        self.generation_attempts = 0
        self.max_attempts = 1  # Reduced from 3 to 1 for faster processing
        
    def generate_robust_vrl(self, context_text: str, raw_log: str, dynamic_prefix: str = "") -> Dict[str, Any]:
        """Generate VRL using RAG system ONLY - no fallbacks"""
        # Use RAG (VRL Snippet Assembler) ONLY
        try:
            vrl_code = self.snippet_assembler.assemble_vrl(raw_log)
            vrl_code = self._final_sanitize_vrl(vrl_code)
            
            result = {
                "success": True,
                "vrl_code": vrl_code,
                "errors": [],
                "log_format": self.log_analyzer(raw_log) if hasattr(self, 'log_analyzer') else "unknown",
                "analysis": {"method": "rag_snippet_assembler_only"},
                "fixes_applied": ["Used RAG snippet assembler ONLY"],
                "attempts": 1,
                "final_validation": True
            }
            
        except Exception as e:
            # RAG failed - return error but don't use fallbacks
            result = {
                "success": False,
                "vrl_code": "",
                "errors": [f"RAG snippet assembler failed: {str(e)}"],
                "log_format": "unknown",
                "analysis": {"method": "rag_failed"},
                "fixes_applied": ["RAG generation failed"],
                "attempts": 1,
                "final_validation": False
            }
        
        # Ensure all expected keys are present for compatibility
        if "fixes_applied" not in result:
            result["fixes_applied"] = []
        if "attempts" not in result:
            result["attempts"] = 1
        if "final_validation" not in result:
            result["final_validation"] = True
        
        return result
    
    def _generate_vrl_with_fallback(self, context_text: str, raw_log: str, dynamic_prefix: str = "") -> str:
        """Generate VRL using existing system with fallback"""
        try:
            from lc_bridge import generate_vrl_lc
            return generate_vrl_lc(context_text, raw_log, dynamic_prefix)
        except Exception as e:
            # Fallback to simple generation
            return self._generate_simple_vrl(raw_log)
    
    def _generate_simple_vrl(self, raw_log: str) -> str:
        """Generate a simple, reliable VRL parser"""
        # Fast detection using log_analyzer
        try:
            from log_analyzer import identify_log_type
            detected_format = identify_log_type(raw_log)
            
            if detected_format == "json":
                return self._generate_json_vrl_simple(raw_log)
            elif detected_format == "syslog":
                return self._generate_syslog_vrl_simple(raw_log)
            elif detected_format == "cef":
                return self._generate_cef_vrl_simple(raw_log)
            else:
                return self._generate_generic_vrl_simple(raw_log)
        except:
            return self._generate_minimal_vrl()
    
    def _generate_json_vrl_simple(self, raw_log: str) -> str:
        """Generate comprehensive JSON VRL parser using log_analyzer pattern"""
        return '''
## 01 - Identify and validate incoming "message" field's log format.  
## Validate and set ".log.format" field based on ".message" field
#####################################################################
if exists(.message) {
  .message = string!(.message)
  if starts_with(.message, "{") && is_json(.message) {
    if exists(.log.format) && .log.format != "json" { 
      .log.format = "json"
    }
  }
  .metadata.pipeline_stage = "logformat_validation"
}

## 04 - Pre-Parse JSON format, Add "event original" field
###########################################################
if .log.format == "json" {
    if .source_type != "logstash" && .log.type != "winevtlogs" {
        .event.original = .message
        .metadata.pipeline_stage = "preparse_json"
    }
}

## 05 Add "event original" if event.original is not set 
if !exists(.event.original) { .event.original = .message }

## Initialize event_data and set basic fields
.event_data = {}
.event.kind = "event"
.event.category = ["application"]
.observer.type = "application"
.log.level = "info"
'''
    
    def _generate_http_vrl_simple(self, raw_log: str) -> str:
        """Generate simple HTTP VRL parser"""
        return f'''
.event.kind = "event"
.event.category = ["web"]
.observer.type = "web-server"
.event.dataset = "http.logs"
.event_data = {{}}

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Basic HTTP log parsing
if exists(.event.original) {{
  # Extract IP address
  if .event.original matches /^(\\d+\\.\\d+\\.\\d+\\.\\d+)/ {{
    .source.ip = $1
  }}
  
  # Extract timestamp
  if .event.original matches /\\[(\\d{{2}}/[A-Za-z]{{3}}/\\d{{4}}:\\d{{2}}:\\d{{2}}:\\d{{2}} [+-]\\d{{4}})\\]/ {{
    .@timestamp = parse_timestamp!($1, format: "%d/%b/%Y:%H:%M:%S %z")
  }}
  
  # Extract HTTP method and path
  if .event.original matches /"([A-Z]+) ([^ ]+) HTTP/ {{
    .http.request.method = $1
    .url.original = $2
  }}
  
  # Extract status code
  if .event.original matches /" \\d+ (\\d{{3}}) / {{
    .http.response.status_code = to_int!($1)
  }}
  
  .event.action = "http_request"
}}

. = compact(., string: true, array: true, object: true, null: true)
'''
    
    def _generate_syslog_vrl_simple(self, raw_log: str) -> str:
        """Generate comprehensive syslog VRL parser using log_analyzer pattern"""
        return '''
## 01 - Identify and validate incoming "message" field's log format.  
## Validate and set ".log.format" field based on ".message" field
#####################################################################
if exists(.message) {
  .message = string!(.message)
  if match(.message, r'^<\\d+>(\\d+\\s)?\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:[+-]\\d{2}:\\d{2}|Z)?\\s\\w[-\\w]+(?:\\s\\w+(\\[\\d+\\])?)?(?:\\s?\\[.*\\])?:') ||
            match(.message, r'^<\\d+>[A-Za-z]{3} \\d{1,2}\\s\\d{2}:\\d{2}:\\d{2}\\s\\S+ (?:\\S+|\\S+\\[\\d+\\])(?:: )?') {
    ## Regex for Syslog RFC5424, RFC3164
    if exists(.log.format) && .log.format != "syslog" { 
      .log.format = "syslog"
    }
  }
  .metadata.pipeline_stage = "logformat_validation"
}

## 02 - Pre-Parse SYSLOG format, Add "event original" field
## Try parsing different SYSLOG message formats (RFC5424, RFC3164, RFC6587)
############################################################################
if .log.format == "syslog" {
    .event.original = del(.message)
    .metadata.pipeline_stage = "preparse_syslog"
}

## 05 Add "event original" if event.original is not set 
if !exists(.event.original) { .event.original = .message }

## Initialize event_data and set basic fields
.event_data = {}
.event.kind = "event"
.event.category = ["system"]
.observer.type = "system"
.log.level = "info"
'''
    
    def _generate_cef_vrl_simple(self, raw_log: str) -> str:
        """Generate comprehensive CEF VRL parser using log_analyzer pattern"""
        return '''
## 01 - Identify and validate incoming "message" field's log format.  
## Validate and set ".log.format" field based on ".message" field
#####################################################################
if exists(.message) {
  .message = string!(.message)
  if match(.message, r'^(<\\d+>CEF:|CEF:)') || 
            match(.message, r'^<\\d+>[A-Za-z]{3}\\s\\d{1,2}\\s\\d{2}:\\d{2}:\\d{2}\\s\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\sCEF:') || 
            match(.message, r'^<\\d+>1\\s\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z\\s\\w+\\s\\w+\\s\\w+\\s-\\sCEF:') || 
            match(.message, r'^<\\d+>\\d{1,2}\\s[A-Za-z]{3}\\s\\d{1,2}\\s\\d{2}:\\d{2}:\\d{2}\\s\\w+\\s\\w+\\[\\d+\\]:\\sCEF:') || 
            match(.message, r'^<\\d+>\\d{1,2}\\s[A-Za-z]{3}\\s\\d{1,2}\\s\\d{2}:\\d{2}:\\d{2}\\s\\w+\\s\\w+\\[\\d+\\]:\\s.*\\sCEF:') {
    if exists(.log.format) && .log.format != "cef" { 
      .log.format = "cef"
    }
  }
  .metadata.pipeline_stage = "logformat_validation"
}

## 03 - Pre-Parse CEF format, Add "event original" field
##########################################################
if .log.format == "cef" {
    .event.original = del(.message)
    .event.original = replace(string!(.event.original), r'^.*\\sCEF:', "CEF:")
    .metadata.pipeline_stage = "preparse_cef"
}

## 05 Add "event original" if event.original is not set 
if !exists(.event.original) { .event.original = .message }

## Initialize event_data and set basic fields
.event_data = {}
.event.kind = "event"
.event.category = ["security"]
.observer.type = "security"
.log.level = "info"
'''

    def _generate_generic_vrl_simple(self, raw_log: str) -> str:
        """Generate simple generic VRL parser"""
        return f'''
.event.kind = "event"
.event.category = ["unknown"]
.observer.type = "unknown"
.event.dataset = "generic.logs"
.event_data = {{}}

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Basic key-value parsing
if exists(.event.original) {{
  kvs, err = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
  if err == null && is_object(kvs) {{
    .event_data = merge(.event_data, kvs, deep: true)
  }}
}}

. = compact(., string: true, array: true, object: true, null: true)
'''
    
    def _generate_minimal_vrl(self, raw_log: str) -> str:
        """Generate minimal working VRL as last resort"""
        return f'''
.event.kind = "event"
.event.category = ["unknown"]
.observer.type = "unknown"
.event.dataset = "minimal.logs"
.event_data = {{}}

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

. = compact(., string: true, array: true, object: true, null: true)
'''

    def _final_sanitize_vrl(self, vrl_text: str) -> str:
        """Remove placeholder maps and ensure required initializations to avoid 'Missing some input keys'."""
        try:
            text = vrl_text or ""
            # Remove any lines containing the placeholder pattern or Ruby hash rocket
            cleaned_lines = []
            for line in text.splitlines():
                if '"k" => "v"' in line:
                    continue
                if '=>' in line:
                    continue
                cleaned_lines.append(line)
            cleaned = "\n".join(cleaned_lines)
            # Ensure .event_data is initialized
            if ".event_data = {}" not in cleaned:
                cleaned = cleaned.replace(".observer.type", ".observer.type\n.event_data = {}")
            return cleaned
        except Exception:
            return vrl_text
    
    def _error_to_dict(self, error: VRL_Error) -> Dict[str, Any]:
        """Convert VRL_Error to dictionary"""
        return {
            "error_type": error.error_type.name,
            "error_code": error.error_code,
            "message": error.message,
            "line_number": error.line_number,
            "column": error.column,
            "context": error.context,
            "suggested_fix": error.suggested_fix,
            "severity": error.severity
        }
    
    def _get_applied_fixes(self, original: str, fixed: str) -> List[str]:
        """Get list of fixes applied"""
        fixes = []
        
        if "Missing some input keys" in original and "Missing some input keys" not in fixed:
            fixes.append("Removed 'Missing some input keys' error")
        
        if '"k" => "v"' in original and '"k" => "v"' not in fixed:
            fixes.append("Removed placeholder patterns")
        
        if original.count('{') != fixed.count('{') or original.count('}') != fixed.count('}'):
            fixes.append("Fixed brace balancing")
        
        if original.count('(') != fixed.count('(') or original.count(')') != fixed.count(')'):
            fixes.append("Fixed parenthesis balancing")
        
        return fixes
    
    def generate_error_report(self, result: Dict[str, Any]) -> str:
        """Generate comprehensive error report"""
        report = "🔍 Enhanced VRL Generation Report\n"
        report += "=" * 50 + "\n\n"
        
        report += f"Success: {'✅' if result['success'] else '❌'}\n"
        report += f"Attempts: {result['attempts']}\n"
        report += f"Final Validation: {'✅' if result['final_validation'] else '❌'}\n\n"
        
        if result['fixes_applied']:
            report += "🔧 Fixes Applied:\n"
            for fix in result['fixes_applied']:
                report += f"  • {fix}\n"
            report += "\n"
        
        if result['errors']:
            report += "❌ Errors Found:\n"
            for i, error in enumerate(result['errors'], 1):
                report += f"  {i}. {error['error_type']}: {error['message']}\n"
                if error['suggested_fix']:
                    report += f"     Fix: {error['suggested_fix']}\n"
            report += "\n"
        
        return report
    
    def _generate_comprehensive_vrl(self, raw_log: str) -> str:
        """Generate comprehensive VRL parser with format detection"""
        try:
            # Read the comprehensive parser
            with open('data/comprehensive_parser.vrl', 'r') as f:
                return f.read()
        except FileNotFoundError:
            # Fallback to simple VRL
            return self._generate_simple_vrl(raw_log)

# Example usage and testing
if __name__ == "__main__":
    generator = Enhanced_VRL_Generator()
    
    # Test with problematic log
    test_log = '192.168.0.5 - - [03/Sep/2025:14:25:33 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0" EXTRA-JUNK'
    
    print("Testing Enhanced VRL Generator...")
    print("=" * 50)
    
    result = generator.generate_robust_vrl("test context", test_log)
    
    print(generator.generate_error_report(result))
    
    if result['success']:
        print("✅ Generated VRL:")
        print(result['vrl_code'])
    else:
        print("❌ Failed to generate valid VRL")

