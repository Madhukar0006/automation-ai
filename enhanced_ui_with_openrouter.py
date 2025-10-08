"""
Enhanced UI with OpenRouter GPT-4 Integration
A comprehensive UI that compares Ollama vs OpenRouter GPT-4 performance
"""

import streamlit as st
import json
import time
from typing import Dict, Any
import pandas as pd

from complete_rag_system import CompleteRAGSystem
from simple_langchain_agent import SimpleLogParsingAgent
from enhanced_openrouter_agent import EnhancedOpenRouterAgent

# Import Docker validation
try:
    from ec2_deployment.agent03_validator import Agent03_DockerValidator
    DOCKER_VALIDATION_AVAILABLE = True
except ImportError:
    DOCKER_VALIDATION_AVAILABLE = False
    st.warning("⚠️ Docker validation not available - install Docker to enable VRL validation")


def initialize_session_state():
    """Initialize session state variables"""
    if 'rag_system' not in st.session_state:
        st.session_state.rag_system = None
    if 'ollama_agent' not in st.session_state:
        st.session_state.ollama_agent = None
    if 'openrouter_agent' not in st.session_state:
        st.session_state.openrouter_agent = None
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None
    if 'docker_validator' not in st.session_state:
        st.session_state.docker_validator = None


def setup_agents():
    """Initialize both Ollama and OpenRouter agents"""
    with st.spinner("Initializing RAG system and agents..."):
        try:
            # Initialize RAG system
            if st.session_state.rag_system is None:
                st.session_state.rag_system = CompleteRAGSystem()
                st.session_state.rag_system.build_langchain_index()
            
            # Initialize Ollama agent
            if st.session_state.ollama_agent is None:
                st.session_state.ollama_agent = SimpleLogParsingAgent(st.session_state.rag_system)
            
            # Initialize OpenRouter agent
            if st.session_state.openrouter_agent is None:
                openrouter_key = st.session_state.get('openrouter_api_key')
                if openrouter_key:
                    st.session_state.openrouter_agent = EnhancedOpenRouterAgent(
                        st.session_state.rag_system, 
                        openrouter_key
                    )
                else:
                    st.error("Please enter your OpenRouter API key in the sidebar")
                    return False
            
            # Initialize Docker validator if available
            if DOCKER_VALIDATION_AVAILABLE and st.session_state.docker_validator is None:
                try:
                    st.session_state.docker_validator = Agent03_DockerValidator()
                    st.success("✅ Docker validator initialized")
                except Exception as e:
                    st.warning(f"⚠️ Docker validator initialization failed: {str(e)}")
                    st.session_state.docker_validator = None
            
            return True
        except Exception as e:
            st.error(f"Failed to initialize agents: {str(e)}")
            return False


def display_comparison_results(results: Dict[str, Any]):
    """Display side-by-side comparison results"""
    if not results:
        return
    
    st.subheader("🔍 Performance Comparison Results")
    
    # Create tabs for different views
    tabs = ["📊 Overview", "🔧 VRL Code", "📋 ECS Mapping", "⚡ Performance"]
    if DOCKER_VALIDATION_AVAILABLE:
        tabs.append("🐳 Docker Validation")
    
    tabs_obj = st.tabs(tabs)
    tab1, tab2, tab3, tab4 = tabs_obj[:4]
    tab5 = tabs_obj[4] if len(tabs_obj) > 4 else None
    
    with tab1:
        st.subheader("📊 Comparison Overview")
        
        # Create comparison metrics
        ollama_success = results.get('ollama', {}).get('success', False)
        openrouter_success = results.get('openrouter', {}).get('success', False)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Ollama Success", "✅" if ollama_success else "❌", 
                     "Success" if ollama_success else "Failed")
        
        with col2:
            st.metric("OpenRouter Success", "✅" if openrouter_success else "❌",
                     "Success" if openrouter_success else "Failed")
        
        with col3:
            improvement = "🆙 Enhanced" if openrouter_success and not ollama_success else "🔄 Same" if ollama_success == openrouter_success else "📉 Degraded"
            st.metric("Improvement", improvement)
        
        # Docker validation status
        if DOCKER_VALIDATION_AVAILABLE:
            st.subheader("🐳 Docker Validation Status")
            col1, col2 = st.columns(2)
            
            ollama_docker = results.get('ollama', {}).get('docker_validation', {})
            openrouter_docker = results.get('openrouter', {}).get('docker_validation', {})
            
            with col1:
                if ollama_docker:
                    docker_status = "✅ Valid" if ollama_docker.get('valid') else "❌ Invalid"
                    st.metric("Ollama Docker", docker_status)
                    if not ollama_docker.get('valid') and ollama_docker.get('error_message'):
                        st.error(f"Error: {ollama_docker['error_message']}")
                else:
                    st.metric("Ollama Docker", "⏸️ Not Tested")
            
            with col2:
                if openrouter_docker:
                    docker_status = "✅ Valid" if openrouter_docker.get('valid') else "❌ Invalid"
                    st.metric("OpenRouter Docker", docker_status)
                    if not openrouter_docker.get('valid') and openrouter_docker.get('error_message'):
                        st.error(f"Error: {openrouter_docker['error_message']}")
                else:
                    st.metric("OpenRouter Docker", "⏸️ Not Tested")
        
        # Detailed comparison
        st.subheader("📈 Detailed Analysis")
        
        comparison_data = []
        
        # Log identification comparison
        ollama_id = results.get('ollama', {}).get('steps', [{}])[0] if results.get('ollama', {}).get('steps') else {}
        openrouter_id = results.get('openrouter', {}).get('steps', [{}])[0] if results.get('openrouter', {}).get('steps') else {}
        
        comparison_data.append({
            "Metric": "Log Identification",
            "Ollama": "✅" if ollama_id.get('status') == 'completed' else "❌",
            "OpenRouter": "✅" if openrouter_id.get('status') == 'completed' else "❌",
            "Confidence (Ollama)": ollama_id.get('result', {}).get('result', {}).get('confidence', 'N/A'),
            "Confidence (OpenRouter)": openrouter_id.get('result', {}).get('confidence', 'N/A')
        })
        
        # VRL generation comparison
        ollama_vrl = results.get('ollama', {}).get('steps', [{}])[1] if len(results.get('ollama', {}).get('steps', [])) > 1 else {}
        openrouter_vrl = results.get('openrouter', {}).get('steps', [{}])[1] if len(results.get('openrouter', {}).get('steps', [])) > 1 else {}
        
        ollama_vrl_code = ollama_vrl.get('result', {}).get('vrl_code', '')
        openrouter_vrl_code = openrouter_vrl.get('result', {}).get('vrl_code', '')
        
        comparison_data.append({
            "Metric": "VRL Generation",
            "Ollama": "✅" if ollama_vrl.get('status') == 'completed' else "❌",
            "OpenRouter": "✅" if openrouter_vrl.get('status') == 'completed' else "❌",
            "Code Length (Ollama)": f"{len(ollama_vrl_code)} chars",
            "Code Length (OpenRouter)": f"{len(openrouter_vrl_code)} chars"
        })
        
        # Validation comparison
        ollama_val = results.get('ollama', {}).get('steps', [{}])[2] if len(results.get('ollama', {}).get('steps', [])) > 2 else {}
        openrouter_val = results.get('openrouter', {}).get('steps', [{}])[2] if len(results.get('openrouter', {}).get('steps', [])) > 2 else {}
        
        comparison_data.append({
            "Metric": "VRL Validation",
            "Ollama": "✅" if ollama_val.get('status') == 'completed' else "❌",
            "OpenRouter": "✅" if openrouter_val.get('status') == 'completed' else "❌",
            "Validation (Ollama)": "Valid" if ollama_val.get('result', {}).get('success', False) else "Invalid",
            "Validation (OpenRouter)": "Valid" if openrouter_val.get('result', {}).get('syntax_valid', False) else "Invalid"
        })
        
        # Display comparison table
        df = pd.DataFrame(comparison_data)
        # Convert all columns to string to avoid Arrow serialization issues
        df = df.astype(str)
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.subheader("🔧 VRL Code Comparison")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Ollama (llama3.2)")
            if ollama_vrl_code:
                st.code(ollama_vrl_code, language='vrl')
            else:
                st.error("No VRL code generated")
        
        with col2:
            st.subheader("🚀 OpenRouter (GPT-4)")
            if openrouter_vrl_code:
                st.code(openrouter_vrl_code, language='vrl')
            else:
                st.error("No VRL code generated")
        
        # Code quality analysis
        if ollama_vrl_code and openrouter_vrl_code:
            st.subheader("📊 Code Quality Analysis")
            
            ollama_lines = len(ollama_vrl_code.split('\n'))
            openrouter_lines = len(openrouter_vrl_code.split('\n'))
            
            ollama_comments = ollama_vrl_code.count('#')
            openrouter_comments = openrouter_vrl_code.count('#')
            
            quality_data = [
                {"Metric": "Total Lines", "Ollama": ollama_lines, "OpenRouter": openrouter_lines},
                {"Metric": "Comments", "Ollama": ollama_comments, "OpenRouter": openrouter_comments},
                {"Metric": "Comment Ratio", "Ollama": f"{ollama_comments/ollama_lines*100:.1f}%", "OpenRouter": f"{openrouter_comments/openrouter_lines*100:.1f}%"},
                {"Metric": "ECS Fields", "Ollama": ollama_vrl_code.count('.event.'), "OpenRouter": openrouter_vrl_code.count('.event.')},
                {"Metric": "Error Handling", "Ollama": ollama_vrl_code.count('if.*err'), "OpenRouter": openrouter_vrl_code.count('if.*err')}
            ]
            
            quality_df = pd.DataFrame(quality_data)
            # Convert all columns to string to avoid Arrow serialization issues
            quality_df = quality_df.astype(str)
            st.dataframe(quality_df, use_container_width=True)
    
    with tab3:
        st.subheader("📋 ECS Mapping Comparison")
        
        # ECS mapping results
        ollama_ecs = results.get('ollama', {}).get('steps', [{}])[3] if len(results.get('ollama', {}).get('steps', [])) > 3 else {}
        openrouter_ecs = results.get('openrouter', {}).get('steps', [{}])[3] if len(results.get('openrouter', {}).get('steps', [])) > 3 else {}
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🤖 Ollama ECS Mapping")
            if ollama_ecs.get('result'):
                st.json(ollama_ecs['result'])
            else:
                st.error("No ECS mapping generated")
        
        with col2:
            st.subheader("🚀 OpenRouter ECS Mapping")
            if openrouter_ecs.get('result'):
                st.json(openrouter_ecs['result'])
            else:
                st.error("No ECS mapping generated")
    
    with tab4:
        st.subheader("⚡ Performance Metrics")
        
        # Performance data
        ollama_time = results.get('ollama', {}).get('execution_time', 0)
        openrouter_time = results.get('openrouter', {}).get('execution_time', 0)
        
        perf_data = [
            {"Metric": "Execution Time", "Ollama": f"{ollama_time:.2f}s", "OpenRouter": f"{openrouter_time:.2f}s"},
            {"Metric": "Success Rate", "Ollama": "100%" if ollama_success else "0%", "OpenRouter": "100%" if openrouter_success else "0%"},
            {"Metric": "Enhancement Level", "Ollama": "Basic", "OpenRouter": "GPT-4 Enhanced"},
            {"Metric": "Model", "Ollama": "llama3.2", "OpenRouter": "GPT-4o"}
        ]
        
        perf_df = pd.DataFrame(perf_data)
        # Convert all columns to string to avoid Arrow serialization issues
        perf_df = perf_df.astype(str)
        st.dataframe(perf_df, use_container_width=True)
        
        # Speed comparison chart
        if ollama_time > 0 and openrouter_time > 0:
            speed_comparison = pd.DataFrame({
                'Model': ['Ollama (llama3.2)', 'OpenRouter (GPT-4)'],
                'Execution Time (seconds)': [ollama_time, openrouter_time]
            })
            st.bar_chart(speed_comparison.set_index('Model'))
    
    # Docker validation tab
    if tab5 and DOCKER_VALIDATION_AVAILABLE:
        with tab5:
            st.subheader("🐳 Docker Validation Results")
            
            ollama_docker = results.get('ollama', {}).get('docker_validation', {})
            openrouter_docker = results.get('openrouter', {}).get('docker_validation', {})
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🤖 Ollama VRL Validation")
                if ollama_docker:
                    if ollama_docker.get('valid'):
                        st.success("✅ VRL is valid and ready for production!")
                        st.json({
                            "Status": "Valid",
                            "Validation ID": ollama_docker.get('validation_id', 'N/A'),
                            "Docker Valid": ollama_docker.get('docker_valid', False),
                            "Syntax Valid": ollama_docker.get('syntax_valid', False)
                        })
                    else:
                        st.error("❌ VRL validation failed")
                        st.error(f"Error: {ollama_docker.get('error_message', 'Unknown error')}")
                        if ollama_docker.get('output'):
                            st.text_area("Validation Output", ollama_docker['output'], height=200)
                else:
                    st.info("⏸️ No Docker validation performed")
            
            with col2:
                st.subheader("🚀 OpenRouter VRL Validation")
                if openrouter_docker:
                    if openrouter_docker.get('valid'):
                        st.success("✅ VRL is valid and ready for production!")
                        st.json({
                            "Status": "Valid",
                            "Validation ID": openrouter_docker.get('validation_id', 'N/A'),
                            "Docker Valid": openrouter_docker.get('docker_valid', False),
                            "Syntax Valid": openrouter_docker.get('syntax_valid', False)
                        })
                    else:
                        st.error("❌ VRL validation failed")
                        st.error(f"Error: {openrouter_docker.get('error_message', 'Unknown error')}")
                        if openrouter_docker.get('output'):
                            st.text_area("Validation Output", openrouter_docker['output'], height=200)
                else:
                    st.info("⏸️ No Docker validation performed")
            
            # Validation summary
            st.subheader("📊 Validation Summary")
            validation_summary = []
            
            if ollama_docker:
                validation_summary.append({
                    "Model": "Ollama",
                    "VRL Valid": "✅" if ollama_docker.get('valid') else "❌",
                    "Docker Valid": "✅" if ollama_docker.get('docker_valid') else "❌",
                    "Syntax Valid": "✅" if ollama_docker.get('syntax_valid') else "❌"
                })
            
            if openrouter_docker:
                validation_summary.append({
                    "Model": "OpenRouter",
                    "VRL Valid": "✅" if openrouter_docker.get('valid') else "❌",
                    "Docker Valid": "✅" if openrouter_docker.get('docker_valid') else "❌",
                    "Syntax Valid": "✅" if openrouter_docker.get('syntax_valid') else "❌"
                })
            
            if validation_summary:
                validation_df = pd.DataFrame(validation_summary)
                validation_df = validation_df.astype(str)
                st.dataframe(validation_df, use_container_width=True)


def main():
    """Main application"""
    st.set_page_config(
        page_title="Enhanced Log Parser - OpenRouter vs Ollama",
        page_icon="🚀",
        layout="wide"
    )
    
    st.title("🚀 Enhanced Log Parser with OpenRouter GPT-4")
    st.markdown("Compare Ollama (llama3.2) vs OpenRouter (GPT-4) for superior log parsing performance")
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # OpenRouter API Key input
        openrouter_key = st.text_input(
            "OpenRouter API Key",
            value=st.session_state.get('openrouter_api_key', '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'),
            type='password',
            help="Enter your OpenRouter API key to use GPT-4"
        )
        
        if openrouter_key:
            st.session_state.openrouter_api_key = openrouter_key
        
        st.markdown("---")
        
        # Sample logs
        st.subheader("📝 Sample Logs")
        sample_logs = {
            "Cisco ASA": """<134>1 2024-01-15T10:30:45.123Z firewall.example.com asa 12345 - - %ASA-6-302013: Built outbound TCP connection 1234567890 for outside:203.0.113.5/80 (203.0.113.5/80) to inside:192.168.1.100/54321 (192.168.1.100/54321)""",
            
            "Fortinet Fortigate": """<134>1 2024-01-15T10:30:45.123Z fortigate.example.com FortiGate 12345 - - date=2024-01-15 time=10:30:45 logid=0000000013 type=traffic subtype=forward level=notice vd=root srcip=203.0.113.5 srcport=80 srcintf=port1 dstip=192.168.1.100 dstport=54321 dstintf=port2 action=accept policyid=1 service=HTTP sessionid=1234567890 srcnatip=0.0.0.0 dstnatip=0.0.0.0""",
            
            "JSON Application": """{"timestamp": "2024-01-15T10:30:45.123Z", "level": "INFO", "message": "User authentication successful", "user_id": "12345", "ip_address": "192.168.1.100", "user_agent": "Mozilla/5.0", "endpoint": "/api/auth/login", "status_code": 200}""",
            
            "Windows Event": """<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event"><System><Provider Name="Microsoft-Windows-Security-Auditing" Guid="{54849625-5478-4994-A5BA-3E3B0328C30D}"/><EventID>4624</EventID><Version>2</Version><Level>0</Level><Task>12544</Task><Opcode>0</Opcode><Keywords>0x8020000000000000</Keywords><TimeCreated SystemTime="2024-01-15T10:30:45.1234567Z"/><EventRecordID>123456</EventRecordID><Correlation ActivityID="{00000000-0000-0000-0000-000000000000}"/><Execution ProcessID="1234" ThreadID="5678"/><Channel>Security</Channel><Computer>WIN-SERVER</Computer><Security/></System><EventData><Data Name="SubjectUserSid">S-1-5-18</Data><Data Name="SubjectUserName">SYSTEM</Data><Data Name="TargetUserName">administrator</Data><Data Name="LogonType">10</Data><Data Name="WorkstationName">WIN-CLIENT</Data></EventData></Event>"""
        }
        
        selected_sample = st.selectbox("Choose a sample log:", list(sample_logs.keys()))
        if st.button("Load Sample"):
            st.session_state.log_input = sample_logs[selected_sample]
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📝 Log Input")
        log_input = st.text_area(
            "Enter your log entry:",
            value=st.session_state.get('log_input', ''),
            height=200,
            placeholder="Paste your log entry here..."
        )
        
        if st.button("🚀 Parse with Both Models", type="primary"):
            if not log_input.strip():
                st.error("Please enter a log entry to parse")
            else:
                # Setup agents
                if not setup_agents():
                    return
                
                # Run comparison
                with st.spinner("Running comparison analysis..."):
                    comparison_results = {}
                    
                    # Run Ollama analysis
                    st.info("🤖 Running Ollama analysis...")
                    start_time = time.time()
                    try:
                        ollama_result = st.session_state.ollama_agent.run_4_agent_workflow(log_input)
                        ollama_time = time.time() - start_time
                        ollama_result['execution_time'] = ollama_time
                        comparison_results['ollama'] = ollama_result
                    except Exception as e:
                        comparison_results['ollama'] = {"success": False, "error": str(e), "execution_time": 0}
                    
                    # Run OpenRouter analysis
                    st.info("🚀 Running OpenRouter GPT-4 analysis...")
                    start_time = time.time()
                    try:
                        openrouter_result = st.session_state.openrouter_agent.run_enhanced_workflow(log_input)
                        openrouter_time = time.time() - start_time
                        openrouter_result['execution_time'] = openrouter_time
                        comparison_results['openrouter'] = openrouter_result
                    except Exception as e:
                        comparison_results['openrouter'] = {"success": False, "error": str(e), "execution_time": 0}
                    
                    # Add Docker validation if available
                    if DOCKER_VALIDATION_AVAILABLE and st.session_state.docker_validator:
                        st.info("🐳 Running Docker validation...")
                        for model_name, result in comparison_results.items():
                            if result.get('success') and 'vrl_code' in result:
                                try:
                                    validation_result = st.session_state.docker_validator.validate_vrl(
                                        result['vrl_code'], 
                                        log_input
                                    )
                                    result['docker_validation'] = validation_result
                                    if validation_result.get('valid'):
                                        st.success(f"✅ {model_name} VRL validated successfully!")
                                    else:
                                        st.warning(f"⚠️ {model_name} VRL validation issues: {validation_result.get('error_message', 'Unknown error')}")
                                except Exception as e:
                                    result['docker_validation'] = {"valid": False, "error": str(e)}
                                    st.error(f"❌ Docker validation failed for {model_name}: {str(e)}")
                    
                    # Store results
                    st.session_state.comparison_results = comparison_results
    
    with col2:
        st.subheader("📊 Quick Stats")
        
        if st.session_state.comparison_results:
            ollama_success = st.session_state.comparison_results.get('ollama', {}).get('success', False)
            openrouter_success = st.session_state.comparison_results.get('openrouter', {}).get('success', False)
            
            # Docker validation status
            ollama_docker = st.session_state.comparison_results.get('ollama', {}).get('docker_validation', {}).get('valid', None)
            openrouter_docker = st.session_state.comparison_results.get('openrouter', {}).get('docker_validation', {}).get('valid', None)
            
            st.metric("Ollama Success", "✅" if ollama_success else "❌")
            st.metric("OpenRouter Success", "✅" if openrouter_success else "❌")
            
            if ollama_docker is not None:
                st.metric("Ollama Docker", "✅" if ollama_docker else "❌")
            if openrouter_docker is not None:
                st.metric("OpenRouter Docker", "✅" if openrouter_docker else "❌")
            
            ollama_time = st.session_state.comparison_results.get('ollama', {}).get('execution_time', 0)
            openrouter_time = st.session_state.comparison_results.get('openrouter', {}).get('execution_time', 0)
            
            st.metric("Ollama Time", f"{ollama_time:.2f}s")
            st.metric("OpenRouter Time", f"{openrouter_time:.2f}s")
            
            if ollama_time > 0 and openrouter_time > 0:
                speed_diff = ((openrouter_time - ollama_time) / ollama_time) * 100
                st.metric("Speed Difference", f"{speed_diff:+.1f}%")
    
    # Display results
    if st.session_state.comparison_results:
        display_comparison_results(st.session_state.comparison_results)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    ### 🔧 Features Comparison
    
    | Feature | Ollama (llama3.2) | OpenRouter (GPT-4) |
    |---------|-------------------|---------------------|
    | **Accuracy** | Good | Superior |
    | **Speed** | Fast (Local) | Fast (API) |
    | **Cost** | Free | Pay-per-use |
    | **Field Extraction** | Basic | Comprehensive |
    | **Error Handling** | Standard | Advanced |
    | **Comments** | Basic | Detailed |
    | **ECS Compliance** | Good | Excellent |
    
    ### 🚀 Benefits of OpenRouter GPT-4
    - **Higher Accuracy**: Better understanding of log patterns
    - **Comprehensive Parsing**: Extracts more fields with better precision
    - **Advanced Error Handling**: Robust fallback mechanisms
    - **Detailed Documentation**: Well-commented and explained code
    - **Production Ready**: Enterprise-grade parsing quality
    """)


if __name__ == "__main__":
    main()
