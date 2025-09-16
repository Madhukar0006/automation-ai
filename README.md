<<<<<<< HEAD
# agentic-dpm-parsers
repo to track agentic dpm parsers development
=======
# 🧠 AI Log Parser - Complete System

## Overview
A comprehensive AI-powered log parsing automation system that generates VRL (Vector Remap Language) parsers using RAG (Retrieval-Augmented Generation), embeddings, and intelligent agents. The system produces accurate parsers similar to how a human would write them.

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
python3 run_app.py
```

### Option 2: Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama (if not running)
ollama serve

# Run the application
streamlit run main_app.py
```

## 🎯 Key Features

### 🤖 Agent-Based Parsing
- **Intelligent Workflow**: ReAct agent follows logical sequence (identify → retrieve context → generate parser)
- **Streaming Mode**: Real-time visibility into agent reasoning
- **Tool-based Architecture**: Specialized tools for each parsing step

### 🧠 Complete RAG System
- **Embedding Models**: Automatic download and setup of sentence-transformers models
- **ChromaDB Integration**: Persistent vector database for knowledge storage
- **Knowledge Base**: VRL snippets, ECS fields, and log examples
- **Context Retrieval**: Intelligent context building for better parser generation

### 📊 Multiple Parsing Modes
- **Agent Mode**: Intelligent step-by-step parsing with reasoning
- **Classic Mode**: Direct LLM-based parsing (original functionality)
- **Test Mode**: Comprehensive testing with sample logs

### ⚙️ Advanced Features
- **Multi-Model Support**: Ollama with llama3.2 and phi3:mini models
- **ECS Compliance**: Structured JSON following Elastic Common Schema
- **Vector CLI Integration**: Test generated VRL parsers with real Vector runtime
- **Streaming Support**: Real-time parsing progress and results

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Raw Log       │───▶│  Agent System    │───▶│  VRL/JSON       │
│   Input         │    │  (ReAct Pattern) │    │  Output         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  RAG System:     │
                       │  • Embeddings    │
                       │  • ChromaDB      │
                       │  • Knowledge     │
                       │  • Context       │
                       └──────────────────┘
```

## 📁 Project Structure

```
parserautomation/
├── main_app.py              # Main integrated application
├── complete_rag_system.py   # Complete RAG system with embeddings
├── simple_agent.py          # Simplified agent framework
├── lc_bridge.py            # LangChain integration
├── log_analyzer.py         # Basic log type identification
├── run_app.py              # Automated startup script
├── requirements.txt        # Dependencies
├── data/                   # Data directory
│   ├── log_samples/        # Sample log files
│   ├── vrl_snippets/       # VRL code snippets
│   └── reference_examples/ # Reference parsing examples
├── chroma_db/              # ChromaDB storage
└── models/                 # Downloaded embedding models
```

## 🎮 Usage Modes

### 1. RAG Setup Mode
- Initialize embedding models and ChromaDB
- Create knowledge base with VRL snippets and ECS fields
- Test RAG system with sample queries

### 2. Agent Mode
- Intelligent parsing with step-by-step reasoning
- Streaming mode for real-time progress
- Automatic log type detection and appropriate parser generation

### 3. Classic Mode
- Direct LLM-based parsing (original functionality)
- Manual control over parsing steps
- Individual tool testing

### 4. Test Mode
- Comprehensive testing with sample logs
- Performance validation
- System health checks

## 🔧 Configuration

### Models
- **Classification Model**: `llama3.2:latest` (for log identification)
- **VRL Generation Model**: `phi3:mini` (for VRL code generation)
- **Embedding Model**: `all-MiniLM-L6-v2` (for RAG system)

### Output Types
- **Auto**: Automatically choose JSON for JSON logs, VRL for others
- **JSON**: Force ECS JSON generation
- **VRL**: Force VRL parser generation

## 🧪 Testing

The system includes comprehensive testing capabilities:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end parsing workflows
- **Sample Logs**: Pre-configured test cases for common log types
- **Vector CLI Testing**: Real VRL parser validation

## 📊 Performance

- **95%+ Accuracy**: Target parsing success rate
- **ECS Compliance**: Full Elastic Common Schema support
- **Multi-Vendor Support**: Cisco, Microsoft, Checkpoint, Fortinet, Palo Alto
- **Real-time Processing**: Streaming mode for immediate feedback

## 🔄 Human Parser Workflow (Automated)

The system emulates the human parser writing process:

1. **Examine raw samples** → Pattern identification
2. **Decide parsing strategy** → Automatic strategy selection
3. **Write extraction rules** → VRL code generation
4. **Normalize data types** → ECS field mapping
5. **Map to schema** → Structured output
6. **Add fallback rules** → Error handling
7. **Test and iterate** → Vector CLI validation
8. **Record patterns** → RAG knowledge base updates

## 🚀 Next Steps

1. **Run the application**: `python3 run_app.py`
2. **Initialize RAG system** in the RAG Setup tab
3. **Test with sample logs** in the Test Mode
4. **Use Agent Mode** for intelligent parsing
5. **Integrate with your logs** for production use

## 📝 Notes

- First-time setup may take a few minutes to download embedding models
- Ensure Ollama is running for LLM functionality
- ChromaDB automatically persists knowledge base between sessions
- All generated VRL can be tested with Vector CLI integration
>>>>>>> 482c874 (Initial commit for parser automation configs)
