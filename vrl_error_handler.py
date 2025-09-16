#!/usr/bin/env python3
"""
VRL Error Handler - Comprehensive error detection, classification, and auto-fixing
Based on Vector VRL error reference: https://vector.dev/docs/reference/vrl/errors/
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum

class VRL_ERROR_TYPE(Enum):
    """VRL Error Types based on Vector documentation"""
    # Compile-time errors
    UNHANDLED_ROOT_RUNTIME_ERROR = "100"
    MALFORMED_REGEX_LITERAL = "101"
    NON_BOOLEAN_IF_PREDICATE = "102"
    UNHANDLED_FALLIBLE_ASSIGNMENT = "103"
    UNNECESSARY_ERROR_ASSIGNMENT = "104"
    UNDEFINED_FUNCTION = "105"
    FUNCTION_ARG_ARITY_MISMATCH = "106"
    # Runtime errors
    ONLY_OBJECTS_CAN_BE_MERGED = "652"
    NON_BOOLEAN_NEGATION = "660"
    CALL_TO_UNDEFINED_VARIABLE = "701"
    USAGE_OF_DEPRECATED_ITEM = "801"
    # Custom errors
    MISSING_INPUT_KEYS = "CUSTOM_001"
    PLACEHOLDER_PATTERNS = "CUSTOM_002"
    SYNTAX_ERROR = "CUSTOM_003"

@dataclass
class VRL_Error:
    """VRL Error representation"""
    error_type: VRL_ERROR_TYPE
    error_code: str
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    context: Optional[str] = None
    suggested_fix: Optional[str] = None
    severity: str = "error"  # error, warning, info

class VRL_Error_Handler:
    """Comprehensive VRL error detection and auto-fixing"""
    
    def __init__(self):
        self.error_patterns = self._build_error_patterns()
        self.fix_suggestions = self._build_fix_suggestions()
        self.common_functions = self._load_common_functions()
        
    def _build_error_patterns(self) -> Dict[VRL_ERROR_TYPE, List[str]]:
        """Build regex patterns for detecting VRL errors"""
        return {
            VRL_ERROR_TYPE.UNHANDLED_ROOT_RUNTIME_ERROR: [
                r"get_env_var\([^)]+\)(?!\s*[=,])",
                r"parse_\w+\([^)]+\)(?!\s*[=,])",
                r"to_\w+\([^)]+\)(?!\s*[=,])"
            ],
            VRL_ERROR_TYPE.MALFORMED_REGEX_LITERAL: [
                r"r'[^']*\[[^\]]*\[[^\]]*\][^']*'",
                r"r'[^']*\(\?P<[^>]*>[^)]*\)[^']*'",
                r"r'[^']*\\[^']*'"
            ],
            VRL_ERROR_TYPE.NON_BOOLEAN_IF_PREDICATE: [
                r"if\s+[^=!<>]+\s*\{",
                r"if\s+\.[a-zA-Z_][a-zA-Z0-9_]*\s*\{"
            ],
            VRL_ERROR_TYPE.UNHANDLED_FALLIBLE_ASSIGNMENT: [
                r"\.\w+\s*=\s*parse_\w+\([^)]+\)(?!\s*[?!])",
                r"\.\w+\s*=\s*to_\w+\([^)]+\)(?!\s*[?!])",
                r"\.\w+\s*=\s*get_env_var\([^)]+\)(?!\s*[?!])"
            ],
            VRL_ERROR_TYPE.UNDEFINED_FUNCTION: [
                r"parse_keyvalue\(",
                r"parse_key_value\(",
                r"parse_common_log\(",
                r"parse_apache_log\(",
                r"parse_nginx_log\("
            ],
            VRL_ERROR_TYPE.ONLY_OBJECTS_CAN_BE_MERGED: [
                r"merge\([^,]+,\s*[^,)]+\)",
                r"\.\w+\s*=\s*merge\([^)]+\)"
            ],
            VRL_ERROR_TYPE.NON_BOOLEAN_NEGATION: [
                r"![^=<>]",
                r"!\d+",
                r"![a-zA-Z_][a-zA-Z0-9_]*"
            ],
            VRL_ERROR_TYPE.CALL_TO_UNDEFINED_VARIABLE: [
                r"\b[a-zA-Z_][a-zA-Z0-9_]*\b(?!\s*[=\(])"
            ],
            VRL_ERROR_TYPE.MISSING_INPUT_KEYS: [
                r"Missing some input keys",
                r"\{\s*\"k\"\s*=>\s*\"v\"\s*\}",
                r"event_data\s*\{\s*\"k\"\s*=>\s*\"v\"\s*\}"
            ],
            VRL_ERROR_TYPE.PLACEHOLDER_PATTERNS: [
                r"\{\s*\"k\"\s*=>\s*\"v\"\s*\}",
                r"event_data\s*\{\s*\"k\"\s*=>\s*\"v\"\s*\}",
                r"Missing some input keys"
            ]
        }
    
    def _build_fix_suggestions(self) -> Dict[VRL_ERROR_TYPE, str]:
        """Build fix suggestions for each error type"""
        return {
            VRL_ERROR_TYPE.UNHANDLED_ROOT_RUNTIME_ERROR: "Add assignment or error handling: .var = function() or function() ?? default",
            VRL_ERROR_TYPE.MALFORMED_REGEX_LITERAL: "Use parse_* functions instead of regex, or fix regex syntax",
            VRL_ERROR_TYPE.NON_BOOLEAN_IF_PREDICATE: "Use exists() or is_nullish() for proper boolean checks",
            VRL_ERROR_TYPE.UNHANDLED_FALLIBLE_ASSIGNMENT: "Add error handling: .var, err = function() or function() ?? default or function!()",
            VRL_ERROR_TYPE.UNDEFINED_FUNCTION: "Check function name spelling and availability",
            VRL_ERROR_TYPE.ONLY_OBJECTS_CAN_BE_MERGED: "Ensure both values are objects before merging",
            VRL_ERROR_TYPE.NON_BOOLEAN_NEGATION: "Use negation only with boolean expressions",
            VRL_ERROR_TYPE.CALL_TO_UNDEFINED_VARIABLE: "Define variable before use or check spelling",
            VRL_ERROR_TYPE.MISSING_INPUT_KEYS: "Remove placeholder patterns and fix VRL syntax",
            VRL_ERROR_TYPE.PLACEHOLDER_PATTERNS: "Remove placeholder patterns and generate proper VRL"
        }
    
    def _load_common_functions(self) -> List[str]:
        """Load list of common VRL functions"""
        return [
            "parse_json", "parse_syslog", "parse_common_log", "parse_apache_log", "parse_nginx_log",
            "parse_key_value", "parse_regex", "parse_timestamp", "parse_cef", "parse_grok",
            "to_string", "to_int", "to_float", "to_bool", "to_timestamp",
            "get_env_var", "get_hostname", "get_tag", "set_tag", "del_tag",
            "exists", "is_nullish", "is_string", "is_integer", "is_float", "is_boolean", "is_object", "is_array",
            "upcase", "downcase", "trim", "strip_ansi", "truncate",
            "merge", "compact", "unique", "sort", "reverse",
            "now", "timestamp", "format_timestamp", "parse_timestamp",
            "encode_base64", "decode_base64", "encode_json", "decode_json",
            "hash", "md5", "sha1", "sha256", "sha512"
        ]
    
    def detect_errors(self, vrl_code: str) -> List[VRL_Error]:
        """Detect all VRL errors in the code"""
        errors = []
        lines = vrl_code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for error_type, patterns in self.error_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, line):
                        error = VRL_Error(
                            error_type=error_type,
                            error_code=error_type.value,
                            message=f"Detected {error_type.name}",
                            line_number=line_num,
                            context=line.strip(),
                            suggested_fix=self.fix_suggestions.get(error_type, "Manual review required")
                        )
                        errors.append(error)
        
        return errors
    
    def fix_vrl_errors(self, vrl_code: str) -> Tuple[str, List[VRL_Error]]:
        """Automatically fix VRL errors where possible"""
        fixed_code = vrl_code
        fixed_errors = []
        
        # Fix Missing Input Keys error
        if VRL_ERROR_TYPE.MISSING_INPUT_KEYS in [e.error_type for e in self.detect_errors(vrl_code)]:
            fixed_code = self._fix_missing_input_keys(fixed_code)
            fixed_errors.append(VRL_Error(
                error_type=VRL_ERROR_TYPE.MISSING_INPUT_KEYS,
                error_code="CUSTOM_001",
                message="Fixed Missing Input Keys error",
                suggested_fix="Removed placeholder patterns"
            ))
        
        # Fix placeholder patterns
        if VRL_ERROR_TYPE.PLACEHOLDER_PATTERNS in [e.error_type for e in self.detect_errors(vrl_code)]:
            fixed_code = self._fix_placeholder_patterns(fixed_code)
            fixed_errors.append(VRL_Error(
                error_type=VRL_ERROR_TYPE.PLACEHOLDER_PATTERNS,
                error_code="CUSTOM_002",
                message="Fixed placeholder patterns",
                suggested_fix="Removed placeholder patterns"
            ))
        
        # Fix unhandled fallible assignments
        fixed_code = self._fix_unhandled_assignments(fixed_code)
        
        # Fix non-boolean if predicates
        fixed_code = self._fix_if_predicates(fixed_code)
        
        # Fix undefined functions
        fixed_code = self._fix_undefined_functions(fixed_code)
        
        return fixed_code, fixed_errors
    
    def _fix_missing_input_keys(self, vrl_code: str) -> str:
        """Fix Missing Input Keys error"""
        # Remove lines with Missing some input keys
        lines = vrl_code.split('\n')
        fixed_lines = [line for line in lines if 'Missing some input keys' not in line]
        
        # Remove placeholder patterns
        fixed_code = '\n'.join(fixed_lines)
        fixed_code = re.sub(r'event_data\s*\{\s*"k"\s*=>\s*"v"\s*\}', '.event_data = {}', fixed_code)
        fixed_code = re.sub(r'\{\s*"k"\s*=>\s*"v"\s*\}', '{}', fixed_code)
        
        return fixed_code
    
    def _fix_placeholder_patterns(self, vrl_code: str) -> str:
        """Fix placeholder patterns"""
        # Remove placeholder patterns
        fixed_code = re.sub(r'event_data\s*\{\s*"k"\s*=>\s*"v"\s*\}', '.event_data = {}', vrl_code)
        fixed_code = re.sub(r'\{\s*"k"\s*=>\s*"v"\s*\}', '{}', fixed_code)
        
        # Remove lines with placeholder patterns
        lines = fixed_code.split('\n')
        fixed_lines = [line for line in lines if '=>' not in line or '=' in line]
        
        return '\n'.join(fixed_lines)
    
    def _fix_unhandled_assignments(self, vrl_code: str) -> str:
        """Fix unhandled fallible assignments"""
        # Pattern: .var = parse_function() -> .var, err = parse_function()
        pattern = r'\.(\w+)\s*=\s*(parse_\w+\([^)]+\))'
        replacement = r'.\1, err = \2'
        fixed_code = re.sub(pattern, replacement, vrl_code)
        
        # Add error handling for assignments
        lines = fixed_code.split('\n')
        fixed_lines = []
        
        for line in lines:
            if re.search(r'\.\w+,\s*err\s*=\s*parse_\w+', line):
                # Add error handling
                indent = len(line) - len(line.lstrip())
                indent_str = ' ' * indent
                fixed_lines.append(line)
                fixed_lines.append(f"{indent_str}if err != null {{")
                fixed_lines.append(f"{indent_str}  .error = err")
                fixed_lines.append(f"{indent_str}  .error_type = \"parsing_error\"")
                fixed_lines.append(f"{indent_str}}} else {{")
                fixed_lines.append(f"{indent_str}  # Successfully parsed")
                fixed_lines.append(f"{indent_str}}}")
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _fix_if_predicates(self, vrl_code: str) -> str:
        """Fix non-boolean if predicates"""
        # Pattern: if .var { -> if exists(.var) {
        pattern = r'if\s+\.(\w+)\s*\{'
        replacement = r'if exists(.\1) {'
        fixed_code = re.sub(pattern, replacement, vrl_code)
        
        return fixed_code
    
    def _fix_undefined_functions(self, vrl_code: str) -> str:
        """Fix undefined functions"""
        # Fix common typos
        fixes = {
            'parse_keyvalue': 'parse_key_value',
            'parse_commonlog': 'parse_common_log',
            'parse_apachelog': 'parse_apache_log',
            'parse_nginxlog': 'parse_nginx_log'
        }
        
        fixed_code = vrl_code
        for wrong, correct in fixes.items():
            fixed_code = fixed_code.replace(wrong, correct)
        
        return fixed_code
    
    def validate_vrl_syntax(self, vrl_code: str) -> Tuple[bool, List[VRL_Error]]:
        """Validate VRL syntax and return validation results"""
        errors = self.detect_errors(vrl_code)
        
        # Check for basic syntax issues
        if not vrl_code.strip():
            errors.append(VRL_Error(
                error_type=VRL_ERROR_TYPE.SYNTAX_ERROR,
                error_code="CUSTOM_003",
                message="Empty VRL code",
                suggested_fix="Generate proper VRL code"
            ))
        
        # Check for balanced braces
        if vrl_code.count('{') != vrl_code.count('}'):
            errors.append(VRL_Error(
                error_type=VRL_ERROR_TYPE.SYNTAX_ERROR,
                error_code="CUSTOM_003",
                message="Unbalanced braces",
                suggested_fix="Check brace matching"
            ))
        
        # Check for balanced parentheses
        if vrl_code.count('(') != vrl_code.count(')'):
            errors.append(VRL_Error(
                error_type=VRL_ERROR_TYPE.SYNTAX_ERROR,
                error_code="CUSTOM_003",
                message="Unbalanced parentheses",
                suggested_fix="Check parenthesis matching"
            ))
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def generate_error_report(self, errors: List[VRL_Error]) -> str:
        """Generate a comprehensive error report"""
        if not errors:
            return "✅ No VRL errors detected"
        
        report = "❌ VRL Error Report\n"
        report += "=" * 50 + "\n\n"
        
        for i, error in enumerate(errors, 1):
            report += f"{i}. Error {error.error_code}: {error.error_type.name}\n"
            report += f"   Message: {error.message}\n"
            if error.line_number:
                report += f"   Line: {error.line_number}\n"
            if error.context:
                report += f"   Context: {error.context}\n"
            if error.suggested_fix:
                report += f"   Fix: {error.suggested_fix}\n"
            report += "\n"
        
        return report
    
    def auto_fix_vrl(self, vrl_code: str) -> Tuple[str, bool, List[VRL_Error]]:
        """Automatically fix VRL code and return results"""
        # Detect errors
        errors = self.detect_errors(vrl_code)
        
        if not errors:
            return vrl_code, True, []
        
        # Try to fix errors
        fixed_code, fixed_errors = self.fix_vrl_errors(vrl_code)
        
        # Validate fixed code
        is_valid, remaining_errors = self.validate_vrl_syntax(fixed_code)
        
        return fixed_code, is_valid, remaining_errors

# Example usage and testing
if __name__ == "__main__":
    handler = VRL_Error_Handler()
    
    # Test with problematic VRL
    test_vrl = '''
# Fallback VRL Parser
# Error: 'NoneType' object has no attribute 'lower'

.event.kind = "event"
.event.category = ["unknown"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "unknown"
.event.dataset = "unknown.logs"

if exists(.message) && is_string(.message) {
  .event.original = del(.message)
}

# Basic parsing attempt
kvs = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
if is_object(kvs) { .event_data = merge(.event_data, kvs, deep: true) }

. = compact(., string: true, array: true, object: true, null: true)
'''
    
    print("Testing VRL Error Handler...")
    print("=" * 50)
    
    # Detect errors
    errors = handler.detect_errors(test_vrl)
    print(f"Detected {len(errors)} errors")
    
    # Generate report
    report = handler.generate_error_report(errors)
    print(report)
    
    # Auto-fix
    fixed_vrl, is_valid, remaining_errors = handler.auto_fix_vrl(test_vrl)
    print(f"Auto-fix successful: {is_valid}")
    print(f"Remaining errors: {len(remaining_errors)}")
    
    if is_valid:
        print("\n✅ Fixed VRL:")
        print(fixed_vrl)
    else:
        print("\n❌ Could not fix all errors")
        print(handler.generate_error_report(remaining_errors))

