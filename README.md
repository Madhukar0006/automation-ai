# Vector Parser Generator

A complete Python project that automatically generates, validates, and pushes Vector VRL parsers using Ollama AI and Docker validation.

## Features

- 🤖 **AI-Powered Generation**: Uses Ollama (Mistral, Llama2, etc.) to generate Vector VRL parsers
- 🐳 **Docker Validation**: Validates parsers using official Vector Docker image
- 🔄 **Auto-Retry Logic**: Automatically retries with error feedback if validation fails
- 📝 **Git Integration**: Commits and pushes validated parsers to main branch
- 🎨 **Streamlit UI**: Beautiful web interface for easy interaction

## Prerequisites

### 1. Install Ollama
```bash
# macOS/Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull a model (in another terminal)
ollama pull mistral
```

### 2. Install Docker
```bash
# Follow Docker installation guide for your OS
# https://docs.docker.com/get-docker/

# Verify installation
docker --version
```

### 3. Install Git
```bash
# Install Git for your OS
# https://git-scm.com/downloads

# Verify installation
git --version
```

### 4. Initialize Git Repository
```bash
# In your project directory
git init
git remote add origin <your-repo-url>
git checkout -b main
```

## Installation

1. **Clone or download this project**
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify all dependencies are working:**
   ```bash
   # Check Ollama
   ollama list
   
   # Check Docker
   docker --version
   
   # Check Git
   git --version
   ```

## Usage

### Start the Application
```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`

### Generate a Parser

1. **Paste a log sample** or **upload a log file**
2. **Configure settings** in the sidebar:
   - Choose Ollama model (Mistral, Llama2, etc.)
   - Set maximum retry attempts
3. **Click "Generate & Validate Parser"**
4. **Watch the magic happen:**
   - 🤖 AI generates the parser
   - 🐳 Docker validates it
   - ❌ If failed, AI learns from errors and retries
   - ✅ Success! Parser is pushed to Git

### Supported Log Formats

The tool can generate parsers for various log formats:

- **JSON Logs**: `{"timestamp": "2023-01-01T12:00:00Z", "level": "info", "message": "User login"}`
- **CEF Logs**: `CEF:0|Security|threatmanager|1.0|100|worm successfully stopped|3|src=10.0.0.1`
- **Syslog**: `<34>Jan 1 12:00:00 server1 sshd[1234]: Failed password for user admin`
- **Custom Formats**: Any structured or semi-structured log format

## How It Works

### 1. AI Generation
- Uses Ollama to generate Vector VRL parsers
- Provides context about log format and ECS mapping requirements
- Generates complete YAML configuration files

### 2. Docker Validation
- Saves generated parser to `vector.yaml`
- Runs Vector validation in Docker container
- Captures validation errors for feedback

### 3. Auto-Retry Logic
- If validation fails, provides error details to AI
- AI learns from errors and generates improved parser
- Continues until success or max retries reached

### 4. Git Integration
- Commits validated parser to `vector.yaml`
- Pushes to main branch automatically
- Provides download link for the final parser

## Configuration

### Ollama Models
The tool supports various Ollama models:
- **Mistral** (recommended) - Fast and accurate
- **Llama2** - Good general performance
- **CodeLlama** - Optimized for code generation
- **Phi** - Lightweight option

### Retry Settings
- **Max Retries**: 1-10 attempts (default: 5)
- **Error Learning**: Each retry includes previous validation errors
- **Timeout**: 2 minutes per generation, 1 minute per validation

## Troubleshooting

### Common Issues

1. **"Ollama not found"**
   - Ensure Ollama is installed and running
   - Check `ollama list` command works
   - Try restarting Ollama service

2. **"Docker not available"**
   - Install Docker Desktop
   - Ensure Docker daemon is running
   - Check `docker --version` command

3. **"Git not found"**
   - Install Git for your operating system
   - Ensure Git is in your PATH
   - Initialize Git repository if needed

4. **"Validation failed"**
   - Check Vector Docker image is available
   - Ensure generated YAML is valid
   - Review error messages for specific issues

### Debug Mode
To see detailed logs, check the browser console or run with debug logging:
```bash
STREAMLIT_LOGGER_LEVEL=debug streamlit run app.py
```

## File Structure

```
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── vector.yaml        # Generated parser (created after first run)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review error messages in the UI
3. Check that all dependencies are properly installed
4. Open an issue with detailed error information