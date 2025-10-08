#!/usr/bin/env python3
"""
Enhanced Error Handler for VRL Validation and Regeneration
Handles Docker validation errors and regenerates VRL code with error context
"""

import re
import os
from typing import Dict, Any, List
from enhanced_openrouter_agent import EnhancedOpenRouterAgent

class EnhancedErrorHandler:
    """Enhanced error handler for VRL validation failures"""
    
    def __init__(self, rag_system, openrouter_api_key: str):
        self.rag_system = rag_system
        self.openrouter_agent = EnhancedOpenRouterAgent(rag_system, openrouter_api_key)
        
        # Common VRL error patterns and fixes
        self.error_patterns = {
            r"call to undefined variable\s+`(\w+)`": {
                "description": "Undefined variable error",
                "common_fixes": [
                    "Check if variable is properly declared",
                    "Use correct VRL syntax for variable access",
                    "Ensure proper field mapping syntax"
                ]
            },
            r"`exit` reported as used": {
                "description": "Invalid exit statement",
                "common_fixes": [
                    "Replace 'exit' with 'return'",
                    "Remove exit statement if not needed",
                    "Use proper VRL flow control"
                ]
            },
            r"missing function argument": {
                "description": "Missing function argument",
                "common_fixes": [
                    "Provide required arguments to function",
                    "Check function signature",
                    "Use correct parameter names"
                ]
            },
            r"invalid timestamp format": {
                "description": "Timestamp parsing error",
                "common_fixes": [
                    "Use correct timestamp format string",
                    "Validate timestamp before parsing",
                    "Use parse_timestamp with proper format"
                ]
            },
            r"GROK pattern failed": {
                "description": "GROK parsing failure",
                "common_fixes": [
                    "Simplify GROK pattern",
                    "Use single-line GROK pattern",
                    "Test pattern with sample log",
                    "Use proper GROK syntax"
                ]
            }
        }
    
    def analyze_error(self, error_message: str) -> Dict[str, Any]:
        """Analyze Docker validation error and provide insights"""
        
        error_analysis = {
            "error_type": "Unknown",
            "severity": "medium",
            "suggestions": [],
            "fixes_needed": [],
            "regeneration_prompt": ""
        }
        
        # Check for known error patterns
        for pattern, info in self.error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                error_analysis["error_type"] = info["description"]
                error_analysis["suggestions"] = info["common_fixes"]
                break
        
        # Extract specific error details
        if "undefined variable" in error_message.lower():
            variable_match = re.search(r"undefined variable\s+`(\w+)`", error_message)
            if variable_match:
                undefined_var = variable_match.group(1)
                error_analysis["fixes_needed"].append(f"Fix undefined variable: {undefined_var}")
                error_analysis["regeneration_prompt"] = f"Fix undefined variable '{undefined_var}' in VRL code"
        
        if "exit" in error_message.lower():
            error_analysis["fixes_needed"].append("Replace 'exit' with 'return'")
            error_analysis["regeneration_prompt"] = "Replace all 'exit' statements with 'return' in VRL code"
        
        if "missing function argument" in error_message.lower():
            error_analysis["fixes_needed"].append("Add missing function arguments")
            error_analysis["regeneration_prompt"] = "Add missing required arguments to function calls"
        
        return error_analysis
    
    def regenerate_vrl_with_error_context(self, original_vrl: str, error_message: str, 
                                       log_content: str, log_format: str) -> Dict[str, Any]:
        """Regenerate VRL code with error context using GPT-4"""
        
        try:
            # Analyze the error
            error_analysis = self.analyze_error(error_message)
            
            # Create enhanced regeneration prompt
            regeneration_prompt = f"""Fix this VRL code that failed Docker validation:

ORIGINAL VRL CODE:
{original_vrl}

ERROR MESSAGE:
{error_message}

LOG TO PARSE:
{log_content[:300]}...

LOG FORMAT: {log_format}

ERROR ANALYSIS:
- Error Type: {error_analysis['error_type']}
- Fixes Needed: {', '.join(error_analysis['fixes_needed'])}

CRITICAL REQUIREMENTS:
1. Fix the specific error: {error_analysis['regeneration_prompt']}
2. Use proper VRL syntax (NO 'exit' statements - use 'return' instead)
3. Ensure all variables are properly defined
4. Use correct GROK parsing: parsed, err = parse_grok(raw, pattern)
5. Include proper error handling with if statements
6. End with . = compact(.)
7. Use single-line GROK patterns
8. Include essential comments only

COMMON VRL FIXES:
- Replace 'exit' with 'return' 
- Use proper field access: parsed.field_name (not parsed.source.ip)
- Ensure all variables exist before using them
- Use correct function calls with proper arguments
- Validate timestamps before parsing

Generate ONLY the corrected VRL code with the error fixed."""
            
            # Use GPT-4 to regenerate with error context
            chain = self.openrouter_agent.prompt | self.openrouter_agent.llm
            response = chain.invoke({"input": regeneration_prompt})
            
            # Extract VRL code from response
            regenerated_vrl = response.content.strip()
            
            # Clean up the response (remove markdown formatting if present)
            if regenerated_vrl.startswith("```"):
                lines = regenerated_vrl.split('\n')
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines)
                
                # Find closing ```
                for i, line in enumerate(lines):
                    if line.strip() == "```" and i > start_idx:
                        end_idx = i
                        break
                
                regenerated_vrl = '\n'.join(lines[start_idx:end_idx])
            
            return {
                "success": True,
                "new_vrl": regenerated_vrl,
                "error_analysis": error_analysis,
                "regeneration_reason": f"Fixed {error_analysis['error_type']}",
                "insights": error_analysis
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_analysis": error_analysis,
                "regeneration_reason": "Failed to regenerate",
                "insights": error_analysis
            }
    
    def validate_vrl_syntax(self, vrl_code: str) -> Dict[str, Any]:
        """Basic VRL syntax validation"""
        
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Check for common VRL syntax issues
        if "exit" in vrl_code:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Invalid 'exit' statement - use 'return' instead")
        
        if "undefined variable" in vrl_code.lower():
            validation_result["warnings"].append("Potential undefined variable issues")
        
        if not vrl_code.strip().endswith(". = compact(.)"):
            validation_result["warnings"].append("Missing final compact() function")
        
        if "parse_grok" not in vrl_code:
            validation_result["warnings"].append("No GROK parsing found")
        
        return validation_result


def create_enhanced_error_handler(rag_system, openrouter_api_key: str) -> EnhancedErrorHandler:
    """Create enhanced error handler instance"""
    return EnhancedErrorHandler(rag_system, openrouter_api_key)


if __name__ == "__main__":
    print("🔧 Enhanced Error Handler for VRL Validation")
    print("=" * 50)
    print("✅ Error patterns loaded")
    print("✅ Regeneration system ready")
    print("✅ Docker validation integration prepared")
    
    # Test error analysis
    test_error = "error[E701]: call to undefined variable `exit` reported as used"
    handler = EnhancedErrorHandler(None, "test-key")
    analysis = handler.analyze_error(test_error)
    
    print(f"\n🧪 Test Error Analysis:")
    print(f"Error Type: {analysis['error_type']}")
    print(f"Fixes Needed: {analysis['fixes_needed']}")
    print(f"Regeneration Prompt: {analysis['regeneration_prompt']}")

