#!/usr/bin/env python3
"""
Simple Token Usage Monitor for OpenRouter
Real-time monitoring of GPT-4 token consumption
"""

import os
import time
import json
from datetime import datetime
from typing import Dict, Any

class SimpleTokenMonitor:
    """Simple token usage monitor"""
    
    def __init__(self):
        self.usage_file = "simple_token_usage.json"
        self.current_session = {
            "start_time": datetime.now().isoformat(),
            "requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_detail": []
        }
    
    def log_request(self, prompt_tokens: int, completion_tokens: int, model: str = "gpt-4o"):
        """Log a single request"""
        total_tokens = prompt_tokens + completion_tokens
        
        # GPT-4o pricing
        input_cost = (prompt_tokens / 1000) * 0.0025
        output_cost = (completion_tokens / 1000) * 0.01
        request_cost = input_cost + output_cost
        
        request_data = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost": request_cost
        }
        
        # Update session
        self.current_session["requests"] += 1
        self.current_session["total_tokens"] += total_tokens
        self.current_session["total_cost"] += request_cost
        self.current_session["requests_detail"].append(request_data)
        
        # Save to file
        self._save_usage()
        
        # Print real-time info
        print(f"🔢 Tokens: {prompt_tokens} + {completion_tokens} = {total_tokens}")
        print(f"💰 Cost: ${request_cost:.4f}")
        print(f"📊 Session Total: ${self.current_session['total_cost']:.4f}")
    
    def _save_usage(self):
        """Save usage data to file"""
        with open(self.usage_file, 'w') as f:
            json.dump(self.current_session, f, indent=2)
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session summary"""
        return {
            "session_duration": self._get_session_duration(),
            "total_requests": self.current_session["requests"],
            "total_tokens": self.current_session["total_tokens"],
            "total_cost": self.current_session["total_cost"],
            "avg_tokens_per_request": (
                self.current_session["total_tokens"] / self.current_session["requests"]
                if self.current_session["requests"] > 0 else 0
            ),
            "avg_cost_per_request": (
                self.current_session["total_cost"] / self.current_session["requests"]
                if self.current_session["requests"] > 0 else 0
            )
        }
    
    def _get_session_duration(self) -> str:
        """Get session duration"""
        start_time = datetime.fromisoformat(self.current_session["start_time"])
        duration = datetime.now() - start_time
        return str(duration).split('.')[0]  # Remove microseconds
    
    def print_session_summary(self):
        """Print current session summary"""
        summary = self.get_session_summary()
        
        print("=" * 50)
        print("📊 Current Session Summary")
        print("=" * 50)
        print(f"⏱️  Duration: {summary['session_duration']}")
        print(f"🔢 Total Requests: {summary['total_requests']}")
        print(f"📝 Total Tokens: {summary['total_tokens']:,}")
        print(f"💰 Total Cost: ${summary['total_cost']:.4f}")
        print(f"📊 Avg Tokens/Request: {summary['avg_tokens_per_request']:.1f}")
        print(f"💵 Avg Cost/Request: ${summary['avg_cost_per_request']:.4f}")
        print("=" * 50)
    
    def reset_session(self):
        """Reset current session"""
        self.current_session = {
            "start_time": datetime.now().isoformat(),
            "requests": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "requests_detail": []
        }
        self._save_usage()
        print("🔄 Session reset")


# Global monitor instance
monitor = SimpleTokenMonitor()

def track_request(prompt_tokens: int, completion_tokens: int, model: str = "gpt-4o"):
    """Track a request (convenience function)"""
    monitor.log_request(prompt_tokens, completion_tokens, model)

def show_usage():
    """Show current usage (convenience function)"""
    monitor.print_session_summary()

def reset_usage():
    """Reset usage tracking (convenience function)"""
    monitor.reset_session()

if __name__ == "__main__":
    # Show current usage
    monitor.print_session_summary()
    
    # Example usage
    print("\n🧪 Testing token tracking...")
    track_request(800, 400)  # Example request
    track_request(600, 300)  # Another example
    
    print("\n📊 Updated summary:")
    monitor.print_session_summary()

