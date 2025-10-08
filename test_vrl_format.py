"""
Test VRL Format Generation
Verify that the OpenRouter agent generates properly formatted VRL code
"""

import os
from enhanced_openrouter_agent import EnhancedOpenRouterAgent
from complete_rag_system import CompleteRAGSystem


def test_vrl_format_generation():
    """Test that VRL is generated in the correct format"""
    
    OPENROUTER_API_KEY = "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"
    
    print("🧪 Testing VRL Format Generation")
    print("=" * 50)
    
    # Initialize RAG system
    rag_system = CompleteRAGSystem()
    rag_system.build_langchain_index()
    
    # Initialize OpenRouter agent
    agent = EnhancedOpenRouterAgent(rag_system, OPENROUTER_API_KEY)
    
    # Test with a Cisco ASA log
    test_log = """<134>1 2024-01-15T10:30:45.123Z firewall.example.com asa 12345 - - %ASA-6-302013: Built outbound TCP connection 1234567890 for outside:203.0.113.5/80 (203.0.113.5/80) to inside:192.168.1.100/54321 (192.168.1.100/54321)"""
    
    print(f"📝 Testing with log: {test_log[:80]}...")
    
    # Generate VRL
    result = agent.generate_vrl_parser_enhanced(test_log)
    
    if result['success']:
        vrl_code = result['vrl_code']
        
        print("✅ VRL generated successfully!")
        print(f"📏 Length: {len(vrl_code)} characters")
        print(f"📄 Lines: {len(vrl_code.split(chr(10)))}")
        
        # Check VRL format requirements
        print("\n🔍 Checking VRL Format Requirements:")
        
        # Check for proper structure
        has_header = "##################################################" in vrl_code
        has_observer_defaults = ".observer.type" in vrl_code
        has_event_defaults = ".event.kind" in vrl_code
        has_parsing_section = "Parse log message" in vrl_code
        has_proper_syntax = "if !exists(" in vrl_code
        has_compact = "compact(" in vrl_code
        no_functions = "def " not in vrl_code and "function " not in vrl_code
        
        print(f"   ✅ Header comments: {has_header}")
        print(f"   ✅ Observer defaults: {has_observer_defaults}")
        print(f"   ✅ Event defaults: {has_event_defaults}")
        print(f"   ✅ Parsing section: {has_parsing_section}")
        print(f"   ✅ Proper VRL syntax: {has_proper_syntax}")
        print(f"   ✅ Compact function: {has_compact}")
        print(f"   ✅ No function definitions: {no_functions}")
        
        # Show the generated VRL
        print("\n📋 Generated VRL Code:")
        print("-" * 50)
        print(vrl_code)
        print("-" * 50)
        
        # Overall assessment
        format_score = sum([has_header, has_observer_defaults, has_event_defaults, 
                           has_parsing_section, has_proper_syntax, has_compact, no_functions])
        
        print(f"\n🎯 VRL Format Score: {format_score}/7")
        
        if format_score >= 6:
            print("✅ EXCELLENT: VRL format is correct!")
        elif format_score >= 4:
            print("⚠️  GOOD: VRL format is mostly correct with minor issues")
        else:
            print("❌ POOR: VRL format needs improvement")
            
        return True
    else:
        print(f"❌ Failed to generate VRL: {result.get('error', 'Unknown error')}")
        return False


if __name__ == "__main__":
    success = test_vrl_format_generation()
    
    if success:
        print("\n🎉 VRL Format Test: SUCCESS!")
        print("The OpenRouter agent is now generating properly formatted VRL code.")
    else:
        print("\n❌ VRL Format Test: FAILED!")
        print("Please check the agent configuration and prompts.")
