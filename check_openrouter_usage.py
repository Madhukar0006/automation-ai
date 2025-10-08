#!/usr/bin/env python3
"""
Check OpenRouter Token Usage and Credits
Monitor your OpenRouter API usage and remaining credits
"""

import requests
import json
from datetime import datetime

# Your OpenRouter API Key
OPENROUTER_API_KEY = "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"

def check_credits():
    """Check remaining credits on OpenRouter account"""
    try:
        url = "https://openrouter.ai/api/v1/auth/key"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}


def get_model_pricing():
    """Get current pricing for GPT-4o"""
    try:
        url = "https://openrouter.ai/api/v1/models"
        response = requests.get(url)
        
        if response.status_code == 200:
            models = response.json()
            for model in models.get('data', []):
                if model.get('id') == 'openai/gpt-4o':
                    return model.get('pricing', {})
        return {}
    except Exception as e:
        return {"error": str(e)}


def test_simple_request():
    """Test a simple request to verify API key works"""
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://parserautomation.local",
            "X-Title": "Log Parser Automation"
        }
        
        data = {
            "model": "openai/gpt-4o",
            "messages": [
                {"role": "user", "content": "Say 'API key is working!' (respond with exactly 5 words)"}
            ],
            "max_tokens": 10
        }
        
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            usage = result.get('usage', {})
            return {
                "status": "success",
                "response": content,
                "usage": usage
            }
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    print("=" * 60)
    print("🔍 OpenRouter Token Usage Monitor")
    print("=" * 60)
    print(f"⏰ Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check credits
    print("📊 Checking Account Credits...")
    credits = check_credits()
    if "error" in credits:
        print(f"❌ Error: {credits['error']}")
    else:
        print("✅ Account Info:")
        print(json.dumps(credits, indent=2))
    print()
    
    # Get pricing
    print("💰 Current GPT-4o Pricing...")
    pricing = get_model_pricing()
    if pricing and "error" not in pricing:
        prompt_price = float(pricing.get('prompt', '0')) * 1000  # Convert to per 1K tokens
        completion_price = float(pricing.get('completion', '0')) * 1000
        print(f"   Input:  ${prompt_price:.4f} per 1K tokens")
        print(f"   Output: ${completion_price:.4f} per 1K tokens")
    else:
        print("   Using standard pricing:")
        print("   Input:  $0.0025 per 1K tokens")
        print("   Output: $0.0100 per 1K tokens")
    print()
    
    # Test API key
    print("🧪 Testing API Key...")
    test_result = test_simple_request()
    if test_result.get('status') == 'success':
        print("✅ API Key is Working!")
        print(f"   Response: {test_result['response']}")
        print(f"   Token Usage:")
        usage = test_result['usage']
        print(f"      Prompt:     {usage.get('prompt_tokens', 0)} tokens")
        print(f"      Completion: {usage.get('completion_tokens', 0)} tokens")
        print(f"      Total:      {usage.get('total_tokens', 0)} tokens")
        
        # Calculate cost
        prompt_tokens = usage.get('prompt_tokens', 0)
        completion_tokens = usage.get('completion_tokens', 0)
        cost = (prompt_tokens / 1000 * 0.0025) + (completion_tokens / 1000 * 0.01)
        print(f"      Cost:       ${cost:.6f}")
    else:
        print(f"❌ Error: {test_result.get('message', 'Unknown error')}")
    print()
    
    print("=" * 60)
    print("📈 Usage Estimates (with optimizations):")
    print("=" * 60)
    print("Per Complete Parse (Classification + VRL + ECS):")
    print("   Tokens: ~1,700-3,200 tokens")
    print("   Cost:   ~$0.006-$0.018")
    print()
    print("Daily Estimates:")
    print("   10 logs/day:   $0.40-$1.00/day   (~$12-$30/month)")
    print("   100 logs/day:  $4.00-$10.00/day  (~$120-$300/month)")
    print("   1000 logs/day: $40.00-$100/day   (~$1,200-$3,000/month)")
    print()
    print("💡 To reduce costs to $0:")
    print("   Use Ollama with Llama 3.2 (FREE, local)")
    print("   Run: streamlit run enhanced_ui_with_openrouter.py")
    print("   Choose Ollama column for free inference!")
    print("=" * 60)


if __name__ == "__main__":
    main()
