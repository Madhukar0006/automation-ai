#!/usr/bin/env python3
"""
Run the Unified AI Parser Application
"""

import subprocess
import sys
import os

def main():
    """Run the unified AI parser application"""
    print("🚀 Starting Unified AI Parser Application...")
    
    # Check if streamlit is installed
    try:
        import streamlit
    except ImportError:
        print("❌ Streamlit not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])
    
    # Run the application
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "unified_ai_parser.py",
            "--server.port", "8501",
            "--server.address", "0.0.0.0"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error running application: {e}")

if __name__ == "__main__":
    main()

