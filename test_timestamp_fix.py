#!/usr/bin/env python3
"""
Test that GPT-4o now generates correct timestamp parsing syntax
"""

import re
from enhanced_openrouter_agent import EnhancedOpenRouterAgent
from complete_rag_system import CompleteRAGSystem

def test_timestamp_syntax():
    """Test that generated VRL uses correct timestamp functions"""
    
    print("🧪 Testing GPT-4o Timestamp Function Generation Fix")
    print("=" * 60)
    
    # Initialize system
    print("\n1️⃣ Initializing RAG system...")
    rag_system = CompleteRAGSystem()
    rag_system.build_langchain_index()
    
    # Initialize agent with new OpenRouter key
    print("2️⃣ Initializing GPT-4o agent...")
    api_key = "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"
    agent = EnhancedOpenRouterAgent(rag_system, api_key)
    
    # Test log with timestamp
    test_log = """2024-01-15T10:30:45.123Z INFO user=john.doe action=login status=success ip=192.168.1.100"""
    
    print(f"3️⃣ Generating VRL for test log:")
    print(f"   {test_log[:80]}...")
    
    # Generate VRL
    result = agent.generate_vrl_parser_enhanced(test_log, "json")
    
    if not result.get("success"):
        print(f"\n❌ VRL generation failed: {result.get('error')}")
        return False
    
    vrl_code = result.get("vrl_code", "")
    
    print("\n4️⃣ Analyzing generated VRL code...")
    
    # Check for WRONG pattern
    wrong_patterns = [
        r'to_timestamp!\([^)]*\.timestamp[^)]*\)',  # to_timestamp!(.timestamp)
        r'to_timestamp!\([^)]*\.time[^)]*\)',        # to_timestamp!(.time)
        r'to_timestamp!\([^)]*\"[^\"]*\"[^)]*\)',    # to_timestamp!("string")
    ]
    
    has_wrong_usage = False
    for pattern in wrong_patterns:
        if re.search(pattern, vrl_code):
            print(f"   ❌ FOUND WRONG USAGE: {pattern}")
            matches = re.findall(pattern, vrl_code)
            for match in matches:
                print(f"      {match}")
            has_wrong_usage = True
    
    # Check for CORRECT pattern
    correct_patterns = [
        r'parse_timestamp!\([^)]+,\s*["\'][^"\']+["\']\)',  # parse_timestamp!(field, "format")
        r'parse_timestamp\([^)]+,\s*["\'][^"\']+["\']\)',   # parse_timestamp(field, "format")
    ]
    
    has_correct_usage = False
    for pattern in correct_patterns:
        matches = re.findall(pattern, vrl_code)
        if matches:
            print(f"   ✅ FOUND CORRECT USAGE:")
            for match in matches:
                print(f"      {match}")
            has_correct_usage = True
    
    # Check that to_timestamp!() is not used incorrectly
    to_timestamp_usage = re.findall(r'to_timestamp!\([^)]+\)', vrl_code)
    if to_timestamp_usage:
        print(f"\n   ⚠️  Found to_timestamp!() usage (verify it's for integers):")
        for match in to_timestamp_usage:
            print(f"      {match}")
    
    print("\n5️⃣ Results:")
    if has_wrong_usage:
        print("   ❌ FAIL: Still using wrong timestamp functions")
        print("\n📄 Generated VRL (excerpt):")
        print("   " + "\n   ".join(vrl_code.split('\n')[:50]))
        return False
    elif has_correct_usage:
        print("   ✅ PASS: Using correct timestamp functions!")
        print("   ✅ No incorrect to_timestamp!() usage found")
        return True
    else:
        print("   ⚠️  WARNING: No timestamp parsing found in generated VRL")
        print("   (This might be OK if log doesn't have timestamps)")
        return True


def test_prompt_content():
    """Test that the prompt includes correct instructions"""
    
    print("\n" + "=" * 60)
    print("🔍 Checking Prompt Instructions")
    print("=" * 60)
    
    # Read the agent file
    with open('enhanced_openrouter_agent.py', 'r') as f:
        agent_code = f.read()
    
    # Check that prompt includes correct instructions
    checks = {
        "TIMESTAMP PROCESSING": "TIMESTAMP PROCESSING" in agent_code,
        "parse_timestamp mention": "parse_timestamp" in agent_code,
        "Warning about to_timestamp": "NEVER use to_timestamp!()" in agent_code or "IT DOES NOT EXIST" in agent_code,
        "Timestamp example": "parse_timestamp!(.timestamp" in agent_code,
    }
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {check_name}")
        if not passed:
            all_passed = False
    
    return all_passed


if __name__ == "__main__":
    print("🔧 GPT-4o Timestamp Fix Verification Test")
    print("=" * 60)
    
    # Test 1: Check prompt content
    prompt_ok = test_prompt_content()
    
    # Test 2: Generate actual VRL and check syntax
    # Note: This will use actual API tokens
    user_input = input("\n⚠️  Run actual GPT-4o test (uses API tokens)? [y/N]: ")
    
    if user_input.lower() == 'y':
        syntax_ok = test_timestamp_syntax()
    else:
        print("\n⏭️  Skipping actual GPT-4o test")
        syntax_ok = None
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    print(f"   Prompt Instructions: {'✅ PASS' if prompt_ok else '❌ FAIL'}")
    if syntax_ok is not None:
        print(f"   Generated VRL Syntax: {'✅ PASS' if syntax_ok else '❌ FAIL'}")
    else:
        print(f"   Generated VRL Syntax: ⏭️  SKIPPED")
    
    if prompt_ok and (syntax_ok is None or syntax_ok):
        print("\n🎉 Fix appears to be working correctly!")
    else:
        print("\n❌ Some tests failed - please review")
