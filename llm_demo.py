#!/usr/bin/env python3
"""
LLM Demo - Using your existing LLM system for VRL generation
"""

import sys
import os
from lc_bridge import classify_log_lc, generate_ecs_json_lc, generate_vrl_lc
from complete_rag_system import CompleteRAGSystem

def test_llm_system():
    """Test the LLM system with sample logs"""
    print("🤖 LLM System Demo - Using your existing Ollama/Llama 3.2 system")
    print("=" * 70)
    
    # Initialize RAG system
    print("🔄 Initializing RAG system...")
    try:
        rag_system = CompleteRAGSystem()
        print("✅ RAG system initialized")
    except Exception as e:
        print(f"⚠️ RAG system error: {e}")
        rag_system = None
    
    # Test cases
    test_cases = [
        {
            "name": "Apache Access Log",
            "log": '192.168.0.5 - - [03/Sep/2025:14:25:33 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0" EXTRA-JUNK'
        },
        {
            "name": "Cisco ASA Firewall",
            "log": "%ASA-6-302013: Built outbound TCP connection 12345 for outside:10.0.0.1/80 to inside:192.168.1.100/45678"
        },
        {
            "name": "JSON Application Log",
            "log": '{"timestamp":"2025-09-03T14:25:33Z","level":"INFO","message":"User login successful","user":"alice","ip":"10.0.0.1","extra_data":"unused"}'
        },
        {
            "name": "Windows Security Event",
            "log": "2025-09-03 14:25:33 WIN-SERVER-01 4624 Success alice 10.0.0.1 192.168.1.100 3389"
        },
        {
            "name": "Syslog Message",
            "log": "<34>1 2025-09-03T14:25:33.123Z server01 app 12345 - - [example@32473] This is a test message with extra data"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test {i}: {test_case['name']}")
        print(f"Log: {test_case['log']}")
        print("-" * 50)
        
        try:
            # Step 1: Log Classification
            print("🔍 Step 1: Classifying log...")
            classification = classify_log_lc(test_case['log'])
            print(f"   Classification: {classification}")
            
            # Step 2: ECS JSON Generation
            print("🔍 Step 2: Generating ECS JSON...")
            context_text = "Log parsing context for ECS mapping"
            ecs_json = generate_ecs_json_lc(context_text, test_case['log'])
            print(f"   ECS JSON: {ecs_json}")
            
            # Step 3: VRL Generation
            print("🔍 Step 3: Generating VRL parser...")
            vrl_parser = generate_vrl_lc(context_text, test_case['log'])
            
            if vrl_parser:
                print("✅ VRL parser generated successfully!")
                
                # Save to file
                output_file = f"llm_demo_{i}_{test_case['name'].lower().replace(' ', '_')}.vrl"
                with open(output_file, 'w') as f:
                    f.write(vrl_parser)
                print(f"💾 Saved to: {output_file}")
                
                # Show first few lines
                lines = vrl_parser.split('\n')[:15]
                print("📄 Generated VRL (first 15 lines):")
                for line in lines:
                    print(f"   {line}")
                if len(vrl_parser.split('\n')) > 15:
                    print("   ...")
            else:
                print("❌ Failed to generate VRL parser")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("🏁 LLM Demo completed!")

def test_single_log():
    """Test with a single log line"""
    print("🤖 Single Log LLM Test")
    print("=" * 40)
    
    log_line = '192.168.0.5 - - [03/Sep/2025:14:25:33 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0" EXTRA-JUNK'
    
    print(f"Testing log: {log_line}")
    print()
    
    try:
        # Step 1: Classification
        print("🔍 Classifying log...")
        classification = classify_log_lc(log_line)
        print(f"Classification: {classification}")
        print()
        
        # Step 2: ECS JSON
        print("🔍 Generating ECS JSON...")
        context_text = "Apache access log parsing context"
        ecs_json = generate_ecs_json_lc(context_text, log_line)
        print(f"ECS JSON: {ecs_json}")
        print()
        
        # Step 3: VRL Generation
        print("🔍 Generating VRL parser...")
        vrl_parser = generate_vrl_lc(context_text, log_line)
        
        if vrl_parser:
            print("✅ VRL parser generated!")
            print("\n" + "=" * 40)
            print("GENERATED VRL PARSER:")
            print("=" * 40)
            print(vrl_parser)
            
            # Save to file
            with open("llm_single_test.vrl", 'w') as f:
                f.write(vrl_parser)
            print(f"\n💾 Saved to: llm_single_test.vrl")
        else:
            print("❌ Failed to generate VRL parser")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "single":
        test_single_log()
    else:
        test_llm_system()
