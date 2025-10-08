"""
Simple OpenRouter Integration Test
Quick test to verify GPT-4 integration works
"""

import os
from langchain_openai import ChatOpenAI


def test_openrouter_connection():
    """Test basic OpenRouter connection"""
    
    # Your OpenRouter API key
    OPENROUTER_API_KEY = "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"
    
    print("🚀 Testing OpenRouter GPT-4 Integration")
    print("=" * 50)
    
    try:
        # Initialize GPT-4 via OpenRouter
        llm = ChatOpenAI(
            model="openai/gpt-4o",
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
            temperature=0.1,
            max_tokens=1000,
            extra_headers={
                "HTTP-Referer": "https://parserautomation.local",
                "X-Title": "Log Parser Test"
            }
        )
        
        print("✅ OpenRouter client initialized successfully")
        
        # Test with a simple log parsing request
        test_log = """<134>1 2024-01-15T10:30:45.123Z firewall.example.com asa 12345 - - %ASA-6-302013: Built outbound TCP connection 1234567890 for outside:203.0.113.5/80 (203.0.113.5/80) to inside:192.168.1.100/54321 (192.168.1.100/54321)"""
        
        prompt = f"""
You are an expert log parser. Analyze this log and identify:
1. Log format (syslog, json, cef, etc.)
2. Vendor (cisco, fortinet, etc.)
3. Product (asa, ios, etc.)
4. Key fields extracted

Log: {test_log}

Provide a JSON response with your analysis.
"""
        
        print("📝 Sending test request to GPT-4...")
        response = llm.invoke(prompt)
        
        print("✅ Response received successfully!")
        print(f"📊 Response length: {len(response.content)} characters")
        print("\n🤖 GPT-4 Response:")
        print("-" * 30)
        print(response.content)
        
        print("\n🎯 OpenRouter GPT-4 Integration Test: SUCCESS!")
        print("✅ API connection working")
        print("✅ GPT-4 responding correctly")
        print("✅ Ready for enhanced log parsing")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        print("Please check your OpenRouter API key and network connection.")
        return False


if __name__ == "__main__":
    success = test_openrouter_connection()
    
    if success:
        print("\n🚀 Next Steps:")
        print("1. Run the enhanced UI: streamlit run enhanced_ui_with_openrouter.py")
        print("2. Test the full integration: python test_openrouter_integration.py")
        print("3. Compare Ollama vs OpenRouter performance")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Verify your OpenRouter API key")
        print("2. Check internet connection")
        print("3. Ensure you have credits in your OpenRouter account")
