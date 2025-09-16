#!/usr/bin/env python3
"""
Startup script for the AI Log Parser application
Handles dependencies and launches the main application
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import streamlit
        import chromadb
        import sentence_transformers
        import langchain
        import pandas
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False

def install_dependencies():
    """Install required dependencies"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def check_ollama():
    """Check if Ollama is running"""
    try:
        import ollama
        models = ollama.list()
        print(f"✅ Ollama is running with {len(models['models'])} models")
        return True
    except Exception as e:
        print(f"⚠️ Ollama not available: {e}")
        print("💡 Please install and start Ollama: https://ollama.ai/")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "data",
        "data/log_samples", 
        "data/vrl_snippets",
        "data/reference_examples",
        "chroma_db",
        "models"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Directories created")

def main():
    """Main startup function"""
    print("🚀 Starting AI Log Parser Application")
    print("=" * 50)
    
    # Create directories
    create_directories()
    
    # Check dependencies
    if not check_dependencies():
        print("📦 Installing missing dependencies...")
        if not install_dependencies():
            print("❌ Failed to install dependencies. Please run: pip install -r requirements.txt")
            return False
    
    # Check Ollama
    check_ollama()
    
    print("\n🎯 Starting Streamlit application...")
    print("📱 The app will open in your browser at http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the application")
    print("=" * 50)
    
    # Launch Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "main_app.py",
            "--server.headless", "true",
            "--browser.gatherUsageStats", "false"
        ])
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Failed to start application: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
