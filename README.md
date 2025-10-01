# VRL Parser Automation System

A comprehensive log parsing system that generates Vector Remap Language (VRL) parsers using AI agents, GROK patterns, and ECS-compliant field mapping.

## 🚀 Features

- **AI-Powered VRL Generation**: Uses LangChain agents to generate intelligent VRL parsers
- **GROK Pattern Support**: Replaces regex with clean GROK patterns for better parsing
- **ECS Compliance**: Maps fields to Elastic Common Schema (ECS) with proper categorization
- **Docker Validation**: Validates VRL parsers using Docker and Vector CLI
- **Multi-Agent Workflow**: 4-agent orchestration system for comprehensive parsing
- **Web UI**: Streamlit-based interface for easy interaction
- **RAG System**: Retrieval Augmented Generation for context-aware parsing

## 📋 Main Components

### Core Application
- `main_app.py` - Main Streamlit UI application
- `run_app.py` - Application runner script
- `requirements.txt` - Python dependencies

### Agent System
- `simple_langchain_agent.py` - Main VRL generation agent
- `four_agent_orchestrator.py` - 4-agent workflow orchestration
- `ec2_deployment/agent03_validator.py` - Docker validation agent

### RAG System
- `complete_rag_system.py` - Main RAG system
- `lc_bridge.py` - LangChain bridge functions

### VRL Parsers
- `clean_grok_parser.py` - Clean GROK-based parsers (current)
- `comprehensive_vrl_parser.py` - Comprehensive syslog parser
- `comprehensive_json_vrl.py` - Comprehensive JSON parser

### Data Files
- `data/ecsfields.json` - ECS field definitions
- `data/vrl.json` - VRL function definitions
- `data/all.json` - Sample log data

### Docker Setup
- `docker-compose-test.yaml` - Docker validation setup
- `docker/vector_config/config.yaml` - Vector configuration

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd parserautomation
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run main_app.py
```

## 🎯 Usage

### Web Interface
1. Open your browser to `http://localhost:8501`
2. Choose your parsing mode:
   - **Agent Parser**: AI-powered VRL generation
   - **Docker Validation**: Test parsers with Docker
   - **Classic Parser**: Traditional parsing methods

### Docker Validation
1. Ensure Docker is running
2. Use the Docker Validation tab in the UI
3. Test your VRL parsers with real log data

## 🔧 Key Features

### GROK-Based Parsing
- Uses GROK patterns instead of complex regex
- Cleaner, more maintainable parsing logic
- Better error handling and validation

### ECS Compliance
- Maps fields to Elastic Common Schema
- Non-ECS fields go to `event_data` section
- Maintains proper data structure for Elasticsearch

### No Nested Duplication
- Eliminates recursive processing
- Clean, flat JSON structure
- No event wrapping issues

## 📊 Supported Log Formats

- **Syslog**: RFC 3164 and RFC 5424 formats
- **JSON**: Structured JSON logs
- **Generic**: Custom text-based logs
- **Apache Access**: Web server logs
- **Windows Security**: Windows event logs

## 🐳 Docker Support

The system includes Docker validation:
- Vector CLI integration
- Containerized parsing environment
- Real-time validation feedback

## 🤖 AI Agents

### Agent01: Log Analysis
- Analyzes log structure and format
- Identifies parsing requirements

### Agent02: VRL Generation
- Generates VRL parsing code
- Uses GROK patterns and ECS mapping

### Agent03: Docker Validation
- Validates VRL with Docker
- Provides feedback for improvements

### Agent04: Field Mapping
- Maps fields to ECS structure
- Handles non-ECS field categorization

## 📁 Project Structure

```
├── main_app.py                 # Main UI application
├── simple_langchain_agent.py   # VRL generation agent
├── clean_grok_parser.py        # GROK-based parsers
├── complete_rag_system.py      # RAG system
├── four_agent_orchestrator.py  # Agent orchestration
├── data/                       # Data files
│   ├── ecsfields.json         # ECS field definitions
│   ├── vrl.json               # VRL functions
│   └── all.json               # Sample data
├── docker/                     # Docker configuration
│   └── vector_config/         # Vector config files
└── ec2_deployment/            # Deployment files
    └── agent03_validator.py   # Docker validator
```

## 🔍 Testing

Test your VRL parsers:
```bash
vector validate docker/vector_config/config.yaml
```

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📞 Support

For issues and questions, please open an issue in the GitHub repository.

---

**Ready to parse logs like a pro!** 🚀