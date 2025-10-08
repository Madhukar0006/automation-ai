#!/usr/bin/env python3
"""
Token Usage Tracker for OpenRouter GPT-4
Monitors token consumption and costs
"""

import json
import time
from datetime import datetime
from typing import Dict, Any, List
import os

class TokenUsageTracker:
    """Track token usage for OpenRouter API calls"""
    
    def __init__(self, log_file: str = "token_usage.json"):
        self.log_file = log_file
        self.usage_data = self._load_usage_data()
        
    def _load_usage_data(self) -> Dict[str, Any]:
        """Load existing usage data from file"""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "total_requests": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0.0,
            "requests": [],
            "daily_usage": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_usage_data(self):
        """Save usage data to file"""
        self.usage_data["last_updated"] = datetime.now().isoformat()
        with open(self.log_file, 'w') as f:
            json.dump(self.usage_data, f, indent=2)
    
    def track_request(self, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4o"):
        """Track a single API request"""
        total_tokens = prompt_tokens + completion_tokens
        
        # GPT-4o pricing (as of 2024)
        # Input: $0.0025 per 1K tokens
        # Output: $0.01 per 1K tokens
        input_cost = (prompt_tokens / 1000) * 0.0025
        output_cost = (completion_tokens / 1000) * 0.01
        request_cost = input_cost + output_cost
        
        request_data = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_usd": request_cost
        }
        
        # Update totals
        self.usage_data["total_requests"] += 1
        self.usage_data["total_prompt_tokens"] += prompt_tokens
        self.usage_data["total_completion_tokens"] += completion_tokens
        self.usage_data["total_tokens"] += total_tokens
        self.usage_data["estimated_cost_usd"] += request_cost
        
        # Add to requests list
        self.usage_data["requests"].append(request_data)
        
        # Keep only last 100 requests to avoid file bloat
        if len(self.usage_data["requests"]) > 100:
            self.usage_data["requests"] = self.usage_data["requests"][-100:]
        
        # Update daily usage
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.usage_data["daily_usage"]:
            self.usage_data["daily_usage"][today] = {
                "requests": 0,
                "tokens": 0,
                "cost_usd": 0.0
            }
        
        self.usage_data["daily_usage"][today]["requests"] += 1
        self.usage_data["daily_usage"][today]["tokens"] += total_tokens
        self.usage_data["daily_usage"][today]["cost_usd"] += request_cost
        
        self._save_usage_data()
        
        print(f"🔢 Token Usage: {prompt_tokens} + {completion_tokens} = {total_tokens} tokens")
        print(f"💰 Cost: ${request_cost:.4f}")
        print(f"📊 Total Cost: ${self.usage_data['estimated_cost_usd']:.4f}")
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get current usage summary"""
        return {
            "total_requests": self.usage_data["total_requests"],
            "total_tokens": self.usage_data["total_tokens"],
            "estimated_cost_usd": self.usage_data["estimated_cost_usd"],
            "average_tokens_per_request": (
                self.usage_data["total_tokens"] / self.usage_data["total_requests"]
                if self.usage_data["total_requests"] > 0 else 0
            ),
            "last_updated": self.usage_data["last_updated"]
        }
    
    def get_daily_usage(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily usage for last N days"""
        from datetime import datetime, timedelta
        
        daily_data = []
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.usage_data["daily_usage"]:
                day_data = self.usage_data["daily_usage"][date].copy()
                day_data["date"] = date
                daily_data.append(day_data)
            else:
                daily_data.append({
                    "date": date,
                    "requests": 0,
                    "tokens": 0,
                    "cost_usd": 0.0
                })
        
        return list(reversed(daily_data))
    
    def print_usage_report(self):
        """Print a detailed usage report"""
        summary = self.get_usage_summary()
        daily_usage = self.get_daily_usage(7)
        
        print("=" * 60)
        print("📊 GPT-4 Token Usage Report")
        print("=" * 60)
        print(f"Total Requests: {summary['total_requests']}")
        print(f"Total Tokens: {summary['total_tokens']:,}")
        print(f"Estimated Cost: ${summary['estimated_cost_usd']:.4f}")
        print(f"Avg Tokens/Request: {summary['average_tokens_per_request']:.1f}")
        print()
        
        print("📅 Last 7 Days:")
        print("-" * 40)
        for day in daily_usage:
            print(f"{day['date']}: {day['requests']} requests, {day['tokens']:,} tokens, ${day['cost_usd']:.4f}")
        
        print()
        print("💡 Cost Breakdown:")
        print(f"  Input Tokens: {self.usage_data['total_prompt_tokens']:,} (${self.usage_data['total_prompt_tokens']/1000*0.0025:.4f})")
        print(f"  Output Tokens: {self.usage_data['total_completion_tokens']:,} (${self.usage_data['total_completion_tokens']/1000*0.01:.4f})")
        print("=" * 60)


# Global tracker instance
tracker = TokenUsageTracker()

def track_openrouter_usage(response_data: Dict[str, Any], model: str = "gpt-4o"):
    """Track usage from OpenRouter API response"""
    if "usage" in response_data:
        usage = response_data["usage"]
        tracker.track_request(
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            model=model
        )

if __name__ == "__main__":
    # Print current usage report
    tracker.print_usage_report()

