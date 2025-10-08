#!/usr/bin/env python3
"""
Intelligent VRL Regenerator
Uses Docker validation errors to intelligently fix VRL parsers
"""

import re
from enhanced_grok_parser import (
    generate_enhanced_grok_json_vrl,
    generate_enhanced_grok_cef_vrl,
    generate_enhanced_grok_syslog_vrl
)

class IntelligentRegenerator:
    def __init__(self):
        self.error_patterns = {
            # GROK pattern errors
            'grok_pattern': r'grok pattern.*?unable to parse',
            'invalid_escape': r'invalid escape character',
            'unnecessary_coalescing': r'unnecessary error coalescing operation',
            'fallible_assignment': r'fallible assignment',
            'undefined_function': r'call to undefined function',
            'syntax_error': r'syntax error',
            'parse_error': r'parse.*?error'
        }
    
    def analyze_error(self, error_message):
        """Analyze Docker validation error and return insights"""
        error_lower = error_message.lower()
        insights = {
            'error_type': 'unknown',
            'suggestions': [],
            'fixes_needed': []
        }
        
        # Check for GROK pattern issues
        if re.search(self.error_patterns['grok_pattern'], error_lower):
            insights['error_type'] = 'grok_pattern'
            insights['suggestions'].append("GROK pattern needs adjustment for log format")
            insights['fixes_needed'].append("fix_grok_pattern")
            
        # Check for escape character issues
        elif re.search(self.error_patterns['invalid_escape'], error_lower):
            insights['error_type'] = 'escape_character'
            insights['suggestions'].append("Remove or fix invalid escape characters")
            insights['fixes_needed'].append("fix_escape_characters")
            
        # Check for unnecessary coalescing
        elif re.search(self.error_patterns['unnecessary_coalescing'], error_lower):
            insights['error_type'] = 'unnecessary_coalescing'
            insights['suggestions'].append("Remove unnecessary ?? operators")
            insights['fixes_needed'].append("remove_coalescing")
            
        # Check for fallible assignments
        elif re.search(self.error_patterns['fallible_assignment'], error_lower):
            insights['error_type'] = 'fallible_assignment'
            insights['suggestions'].append("Use infallible assignment pattern")
            insights['fixes_needed'].append("fix_assignments")
            
        # Check for undefined functions
        elif re.search(self.error_patterns['undefined_function'], error_lower):
            insights['error_type'] = 'undefined_function'
            insights['suggestions'].append("Replace with valid VRL functions")
            insights['fixes_needed'].append("fix_functions")
            
        # Check for syntax errors
        elif re.search(self.error_patterns['syntax_error'], error_lower):
            insights['error_type'] = 'syntax_error'
            insights['suggestions'].append("Fix VRL syntax issues")
            insights['fixes_needed'].append("fix_syntax")
        
        return insights
    
    def regenerate_vrl_with_error_context(self, log_type, error_message, original_vrl=""):
        """Regenerate VRL based on error analysis"""
        insights = self.analyze_error(error_message)
        
        # Choose appropriate parser based on log type and error
        if log_type == "Security" or "CEF" in log_type:
            if insights['error_type'] == 'grok_pattern':
                # Use robust CEF parser for GROK issues
                from optimized_cef_parser_robust import generate_robust_cef_parser
                new_vrl = generate_robust_cef_parser()
            else:
                new_vrl = generate_enhanced_grok_cef_vrl()
                
        elif log_type == "System" or "Syslog" in log_type:
            if insights['error_type'] == 'grok_pattern':
                # Use working syslog parser for GROK issues
                from working_syslog_parser import generate_working_syslog_parser
                new_vrl = generate_working_syslog_parser()
            else:
                new_vrl = generate_enhanced_grok_syslog_vrl()
                
        elif log_type == "Application" or "JSON" in log_type:
            new_vrl = generate_enhanced_grok_json_vrl()
            
        else:
            # Default to robust CEF parser
            from optimized_cef_parser_robust import generate_robust_cef_parser
            new_vrl = generate_robust_cef_parser()
        
        return {
            'new_vrl': new_vrl,
            'insights': insights,
            'regeneration_reason': f"Fixed {insights['error_type']} error",
            'success': True
        }
    
    def apply_specific_fixes(self, vrl_code, fixes_needed):
        """Apply specific fixes to VRL code based on error analysis"""
        fixed_code = vrl_code
        
        for fix in fixes_needed:
            if fix == 'remove_coalescing':
                # Remove unnecessary ?? operators
                fixed_code = re.sub(r'\?\?\s*""', '', fixed_code)
                fixed_code = re.sub(r'\?\?\s*null', '', fixed_code)
                
            elif fix == 'fix_assignments':
                # Convert fallible assignments to infallible
                fixed_code = re.sub(
                    r'\.(\w+) = to_string\(([^)]+)\)',
                    r'.\1, err = to_string(\2)',
                    fixed_code
                )
                fixed_code = re.sub(
                    r'\.(\w+) = to_int\(([^)]+)\)',
                    r'.\1, err = to_int(\2)',
                    fixed_code
                )
                
            elif fix == 'fix_escape_characters':
                # Fix escape characters
                fixed_code = fixed_code.replace('\\(', '(')
                fixed_code = fixed_code.replace('\\)', ')')
                fixed_code = fixed_code.replace('\\[', '[')
                fixed_code = fixed_code.replace('\\]', ']')
        
        return fixed_code

def regenerate_with_intelligence(log_type, error_message, original_vrl=""):
    """Main function to regenerate VRL with error intelligence"""
    regenerator = IntelligentRegenerator()
    return regenerator.regenerate_vrl_with_error_context(log_type, error_message, original_vrl)
