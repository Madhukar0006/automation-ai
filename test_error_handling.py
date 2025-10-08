#!/usr/bin/env python3
"""
Test Enhanced Error Handling and VRL Regeneration
"""

import os
from enhanced_error_handler import EnhancedErrorHandler
from complete_rag_system import CompleteRAGSystem

def test_error_handling():
    """Test the enhanced error handling system"""
    
    print("🧪 Testing Enhanced Error Handling")
    print("=" * 50)
    
    # Initialize RAG system
    print("📚 Initializing RAG system...")
    rag_system = CompleteRAGSystem()
    rag_system.build_langchain_index()
    
    # Create error handler
    openrouter_key = "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"
    error_handler = EnhancedErrorHandler(rag_system, openrouter_key)
    
    # Test error message (the one you encountered)
    test_error = """error[E701]: call to undefined variable
┌─ :19:3
│
19 │   exit
│   ^^^^
│   │
│   undefined variable
│   did you mean "err"?"""
    
    print(f"🔍 Analyzing error...")
    print(f"Error: {test_error[:100]}...")
    
    # Analyze the error
    analysis = error_handler.analyze_error(test_error)
    
    print(f"\n📊 Error Analysis:")
    print(f"  Error Type: {analysis['error_type']}")
    print(f"  Fixes Needed: {analysis['fixes_needed']}")
    print(f"  Regeneration Prompt: {analysis['regeneration_prompt']}")
    
    # Test VRL with the error
    problematic_vrl = """##################################################
## VRL Parser - syslog
##################################################

### ECS defaults
if !exists(.observer.type) { .observer.type = "network" }
if !exists(.event.dataset) { .event.dataset = "syslog.logs" }
.event.category = ["network"]
.event.kind = "event"

### Parse log
raw = to_string(.message) ?? to_string(.) ?? ""
pattern = "<%{POSINT:syslog.priority}>%{INT:syslog.version} %{TIMESTAMP_ISO8601:@timestamp} %{HOSTNAME:observer.hostname} %{WORD:process.program} %{INT:process.pid} - - %%{WORD:asa.level}-%{INT:asa.message_id}: Built outbound %{WORD:network.transport} connection %{INT:network.connection_id} for %{WORD:network.direction}:%{IP:source.ip}/%{INT:source.port} \\(%{IP:source.nat_ip}/%{INT:source.nat_port}\\) to %{WORD:network.direction}:%{IP:destination.ip}/%{INT:destination.port} \\(%{IP:destination.nat_ip}/%{INT:destination.nat_port}\\)"

parsed, err = parse_grok(raw, pattern)

if err != null {
  .error = "Parse failed"
  . = compact(.)
  exit
}

### Field mapping
if exists(parsed.syslog.priority) { .log.syslog.priority = del(parsed.syslog.priority) }
if exists(parsed.syslog.version) { .log.syslog.version = del(parsed.syslog.version) }
if exists(parsed.observer.hostname) { .observer.hostname = del(parsed.observer.hostname) }
if exists(parsed.process.program) { .process.name = del(parsed.process.program) }
if exists(parsed.process.pid) { .process.pid = del(parsed.process.pid) }

.@timestamp = now()
. = compact(.)"""
    
    test_log = "<134>1 2024-01-15T10:30:45.123Z firewall.example.com asa 12345 - - %ASA-6-302013: Built outbound TCP connection 1234567890 for outside:203.0.113.5/80 (203.0.113.5/12345) to inside:192.168.1.100/54321 (192.168.1.100/54321)"
    
    print(f"\n🔄 Regenerating VRL with error context...")
    
    # Regenerate VRL with error context
    regeneration_result = error_handler.regenerate_vrl_with_error_context(
        problematic_vrl,
        test_error,
        test_log,
        "syslog"
    )
    
    if regeneration_result['success']:
        print(f"✅ Regeneration successful!")
        print(f"📝 Reason: {regeneration_result['regeneration_reason']}")
        
        new_vrl = regeneration_result['new_vrl']
        print(f"\n📋 Regenerated VRL:")
        print("=" * 50)
        print(new_vrl[:500] + "..." if len(new_vrl) > 500 else new_vrl)
        
        # Check if the error is fixed
        if "exit" not in new_vrl:
            print(f"\n✅ SUCCESS: 'exit' statement removed!")
        else:
            print(f"\n⚠️ WARNING: 'exit' statement still present")
            
        if "return" in new_vrl:
            print(f"✅ SUCCESS: 'return' statement added!")
        else:
            print(f"⚠️ WARNING: 'return' statement not found")
            
    else:
        print(f"❌ Regeneration failed: {regeneration_result.get('error', 'Unknown error')}")
    
    print(f"\n🎯 Error Handling Test Complete!")

if __name__ == "__main__":
    test_error_handling()

