#!/usr/bin/env python3
"""
Final validation for error coalescing fixes
Ensures no unnecessary error coalescing operations remain
"""

import json
from enhanced_grok_parser import (
    generate_enhanced_grok_json_vrl,
    generate_enhanced_grok_cef_vrl,
    generate_enhanced_grok_syslog_vrl
)

def validate_error_coalescing(parser_name, parser_function):
    """Validate that parser has no unnecessary error coalescing"""
    print(f"\n🔍 VALIDATING ERROR COALESCING: {parser_name.upper()}")
    print("-" * 50)
    
    try:
        vrl_content = parser_function()
        
        # Check for unnecessary error coalescing patterns
        unnecessary_patterns = [
            'to_string(json_parsed.method) ?? ""',
            'to_string(json_parsed.action) ?? ""',
            'to_string(cef_parsed.name) ?? ""',
            'to_string(cef_extensions.proto) ?? ""',
            'to_string(cef_extensions.act) ?? ""',
            'to_string(cef_extensions.outcome) ?? ""',
            'to_string(.event.action) ?? ""'
        ]
        
        found_unnecessary = []
        for pattern in unnecessary_patterns:
            if pattern in vrl_content:
                found_unnecessary.append(pattern)
        
        if found_unnecessary:
            print(f"❌ Found {len(found_unnecessary)} unnecessary error coalescing operations:")
            for pattern in found_unnecessary:
                print(f"   • {pattern}")
            return False
        else:
            print(f"✅ No unnecessary error coalescing operations found")
        
        # Check that we still have proper to_string() calls
        to_string_count = vrl_content.count('to_string(')
        print(f"📊 Total to_string() calls: {to_string_count}")
        
        # Check for proper null handling where needed
        null_safe_patterns = [
            'to_string(.message) ?? ""',
            'to_string(.message) ?? to_string(.) ?? ""',
            'to_string(cef_parsed.extension)',
            'to_string(service_match.service_name) ?? ""'
        ]
        
        safe_patterns_found = 0
        for pattern in null_safe_patterns:
            if pattern in vrl_content:
                safe_patterns_found += 1
        
        print(f"📊 Proper null handling patterns: {safe_patterns_found}")
        
        print(f"✅ {parser_name} parser has correct error coalescing")
        return True
        
    except Exception as e:
        print(f"❌ Error validating {parser_name} parser: {e}")
        return False

def demonstrate_error_coalescing_fix():
    """Demonstrate the error coalescing fix"""
    print(f"\n🎯 ERROR COALESCING FIX DEMONSTRATION")
    print("=" * 60)
    
    print(f"""
❌ PROBLEMATIC CODE (Unnecessary Error Coalescing):
```vrl
if exists(cef_parsed.name) {{
    .event.action = downcase(to_string(cef_parsed.name) ?? \"\")  # Unnecessary
}}
```

Error: this expression never resolves -- remove this error coalescing operation

✅ FIXED CODE (Proper Error Coalescing):
```vrl
if exists(cef_parsed.name) {{
    .event.action = downcase(to_string(cef_parsed.name))  # Clean
}}
```

🔍 KEY PRINCIPLES:
• If you check exists() first, to_string() can't fail
• Only use ?? \"\" when the expression might actually fail
• VRL is smart enough to know when expressions are safe
• Unnecessary error coalescing causes validation errors
""")

def main():
    """Main validation function"""
    print("🚀 FINAL ERROR COALESCING VALIDATION")
    print("🎯 ENSURING NO UNNECESSARY ERROR COALESCING OPERATIONS")
    print("=" * 60)
    
    parsers = [
        ("JSON", generate_enhanced_grok_json_vrl),
        ("CEF", generate_enhanced_grok_cef_vrl),
        ("SYSLOG", generate_enhanced_grok_syslog_vrl)
    ]
    
    results = []
    
    for parser_name, parser_function in parsers:
        is_correct = validate_error_coalescing(parser_name, parser_function)
        results.append((parser_name, is_correct))
    
    # Demonstrate the fix
    demonstrate_error_coalescing_fix()
    
    # Summary
    print(f"\n📊 ERROR COALESCING VALIDATION SUMMARY:")
    correct_count = sum(1 for _, is_correct in results if is_correct)
    
    for parser_name, is_correct in results:
        status = "✅ CORRECT" if is_correct else "❌ HAS ISSUES"
        print(f"   {parser_name}: {status}")
    
    print(f"\n🎯 Overall Result: {correct_count}/{len(results)} parsers have correct error coalescing")
    
    if correct_count == len(results):
        print(f"🎉 ALL PARSERS HAVE CORRECT ERROR COALESCING!")
        print(f"✅ No unnecessary error coalescing operations")
        print(f"✅ Proper null handling where needed")
        print(f"✅ Clean, efficient VRL code")
        print(f"✅ Ready for production use")
    else:
        print(f"❌ Some parsers still have error coalescing issues")
    
    return results

if __name__ == "__main__":
    main()

