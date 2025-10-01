#!/usr/bin/env python3
"""
VRL Error Integration - Integrates error handling into the main VRL generation pipeline
Simplified version without external dependencies
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Simple error types for VRL
class VRL_ERROR_TYPE(Enum):
    SYNTAX_ERROR = "syntax_error"
    PARSE_ERROR = "parse_error"
    FIELD_ERROR = "field_error"
    VALIDATION_ERROR = "validation_error"

class VRL_Error:
    """Simple VRL error class"""
    def __init__(self, error_type: VRL_ERROR_TYPE, message: str, line: int = None):
        self.error_type = error_type
        self.message = message
        self.line = line

class VRL_Error_Handler:
    """Simple VRL error handler"""
    def __init__(self):
        self.errors = []
    
    def add_error(self, error: VRL_Error):
        self.errors.append(error)
    
    def get_errors(self):
        return self.errors
    
    def clear_errors(self):
        self.errors = []

class VRL_Error_Integration:
    """Integrates VRL error handling into the main system"""
    
    def __init__(self, rag_system=None):
        self.error_handler = VRL_Error_Handler()
        self.rag_system = rag_system
        self.error_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "errors_fixed": 0,
            "common_errors": {}
        }
    
    def generate_vrl_with_error_handling(self, context_text: str, raw_log: str, dynamic_prefix: str = "") -> Dict[str, Any]:
        """Generate VRL with comprehensive error handling"""
        self.error_stats["total_generations"] += 1
        
        try:
            # Basic VRL generation (simplified)
            vrl_code = self._generate_basic_vrl(context_text, raw_log, dynamic_prefix)
            
            # Validate the generated VRL
            validation_result = self._validate_vrl(vrl_code)
            
            if validation_result["valid"]:
                self.error_stats["successful_generations"] += 1
                logger.info("VRL generation successful after 1 attempts")
                return {
                    "success": True,
                    "vrl_code": vrl_code,
                    "attempts": 1,
                    "errors_fixed": 0,
                    "validation_result": validation_result
                }
            else:
                # Try to fix errors
                fixed_vrl, fixes_applied = self._attempt_fix_vrl(vrl_code, validation_result["errors"])
                
                if fixed_vrl:
                    self.error_stats["successful_generations"] += 1
                    self.error_stats["errors_fixed"] += fixes_applied
                    logger.info(f"VRL generation successful after 2 attempts with {fixes_applied} fixes")
                    return {
                        "success": True,
                        "vrl_code": fixed_vrl,
                        "attempts": 2,
                        "errors_fixed": fixes_applied,
                        "validation_result": {"valid": True, "errors": []}
                    }
                else:
                    self.error_stats["failed_generations"] += 1
                    return {
                        "success": False,
                        "vrl_code": vrl_code,
                        "attempts": 2,
                        "errors": validation_result["errors"],
                        "validation_result": validation_result
                    }
                    
        except Exception as e:
            self.error_stats["failed_generations"] += 1
            logger.error(f"VRL generation failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "attempts": 1
            }
    
    def _generate_basic_vrl(self, context_text: str, raw_log: str, dynamic_prefix: str = "") -> str:
        """Generate basic VRL code"""
        # Simple VRL template with proper syntax
        vrl_template = f"""
# VRL Parser Generated with Error Handling
{dynamic_prefix}

# Basic event structure
.event.kind = "event"
.event.category = ["unknown"]
.event.created = now()
.event.dataset = "log.parser"

# Parse the message
.message = .

# Set timestamp
.@timestamp = now()

# Convert to string for processing
.input_string = string!(.)

# Try to parse as JSON
if starts_with(.input_string, "{{") {{
    .parsed, err = parse_json(.input_string)
    if err == null {{
        .event.type = ["info"]
        .event.dataset = "json.logs"
    }}
}}

# Try to parse as syslog
if contains(.input_string, "<") {{
    if contains(.input_string, ">") {{
        .parsed, err = parse_syslog(.input_string)
        if err == null {{
            .event.type = ["info"]
            .event.dataset = "syslog.logs"
        }}
    }}
}}

# Default parsing for text logs
if !exists(."event.type") {{
    .event.type = ["info"]
    .event.dataset = "text.logs"
}}

# Ensure required fields
if !exists(."event.kind") {{
    .event.kind = "event"
}}
if !exists(."event.category") {{
    .event.category = ["unknown"]
}}
if !exists(."event.created") {{
    .event.created = now()
}}
}}
"""
        return vrl_template.strip()
    
    def _validate_vrl(self, vrl_code: str) -> Dict[str, Any]:
        """Basic VRL validation"""
        errors = []
        
        # Basic syntax checks
        if not vrl_code.strip():
            errors.append("VRL code is empty")
        
        # Check for basic structure
        if ".event.kind" not in vrl_code:
            errors.append("Missing .event.kind field")
        
        if ".event.created" not in vrl_code:
            errors.append("Missing .event.created field")
        
        # Check for balanced braces
        open_braces = vrl_code.count('{')
        close_braces = vrl_code.count('}')
        if open_braces != close_braces:
            errors.append(f"Mismatched braces: {open_braces} open, {close_braces} close")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _attempt_fix_vrl(self, vrl_code: str, errors: List[str]) -> Tuple[Optional[str], int]:
        """Attempt to fix VRL errors"""
        fixes_applied = 0
        fixed_vrl = vrl_code
        
        for error in errors:
            if "Missing .event.kind" in error:
                if ".event.kind" not in fixed_vrl:
                    fixed_vrl = ".event.kind = \"event\"\n" + fixed_vrl
                    fixes_applied += 1
            
            elif "Missing .event.created" in error:
                if ".event.created" not in fixed_vrl:
                    fixed_vrl = fixed_vrl + "\n.event.created = now()"
                    fixes_applied += 1
            
            elif "Mismatched braces" in error:
                # Simple brace fixing
                open_count = fixed_vrl.count('{')
                close_count = fixed_vrl.count('}')
                if open_count > close_count:
                    fixed_vrl = fixed_vrl + '}' * (open_count - close_count)
                    fixes_applied += 1
        
        # Validate the fixed VRL
        validation = self._validate_vrl(fixed_vrl)
        if validation["valid"]:
            return fixed_vrl, fixes_applied
        else:
            return None, fixes_applied
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return self.error_stats.copy()
    
    def reset_stats(self):
        """Reset error statistics"""
        self.error_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "errors_fixed": 0,
            "common_errors": {}
        }

# Test function
if __name__ == "__main__":
    integration = VRL_Error_Integration()
    
    # Test with sample log
    test_log = "Jan 15 10:30:45 server sshd[1234]: Accepted publickey for user from 192.168.1.100 port 22"
    
    result = integration.generate_vrl_with_error_handling("", test_log)
    print(json.dumps(result, indent=2))