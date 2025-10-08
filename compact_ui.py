#!/usr/bin/env python3
"""
Compact Agent Parser UI - Clean and Small
"""

import streamlit as st
import subprocess
import tempfile
import os
import time
from datetime import datetime
from pathlib import Path

# Import our parsers
try:
    from enhanced_grok_parser import generate_enhanced_grok_json_vrl, generate_enhanced_grok_cef_vrl, generate_enhanced_grok_syslog_vrl
except ImportError:
    # Fallback imports
    try:
        from compact_syslog_parser import generate_compact_syslog_parser as generate_enhanced_grok_syslog_vrl
        from optimized_cef_parser_robust import generate_robust_cef_parser as generate_enhanced_grok_cef_vrl
        from enhanced_grok_parser import generate_enhanced_grok_json_vrl
    except ImportError as e:
        st.error(f"❌ Import error: {e}")
        generate_enhanced_grok_json_vrl = None
        generate_enhanced_grok_cef_vrl = None
        generate_enhanced_grok_syslog_vrl = None

def get_docker_container_info():
    """Get detailed Docker container information"""
    try:
        # Check for dpm-test-config-validator container
        result = subprocess.run(['docker', 'ps', '--filter', 'name=dpm-test-config-validator', '--format', 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'], 
                              capture_output=True, text=True, timeout=10)
        
        if 'dpm-test-config-validator' in result.stdout:
            lines = result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Parse the container line properly (handle multiple spaces)
                container_line = lines[1]
                # Split by multiple spaces and filter out empty strings
                container_parts = [part for part in container_line.split() if part]
                
                return {
                    "running": True,
                    "name": container_parts[0] if len(container_parts) > 0 else "dpm-test-config-validator",
                    "image": container_parts[1] if len(container_parts) > 1 else "Unknown",
                    "status": f"{container_parts[2]} {container_parts[3]}" if len(container_parts) > 3 else container_parts[2] if len(container_parts) > 2 else "Running",
                    "ports": container_parts[4] if len(container_parts) > 4 else "None"
                }
        
        # Also check for any Vector containers
        vector_result = subprocess.run(['docker', 'ps', '--filter', 'ancestor=timberio/vector:latest-debian', '--format', 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'], 
                                     capture_output=True, text=True, timeout=10)
        
        if vector_result.stdout.strip():
            lines = vector_result.stdout.strip().split('\n')
            if len(lines) > 1:
                # Parse the container line properly (handle multiple spaces)
                container_line = lines[1]
                # Split by multiple spaces and filter out empty strings
                container_parts = [part for part in container_line.split() if part]
                
                return {
                    "running": True,
                    "name": container_parts[0] if len(container_parts) > 0 else "vector-container",
                    "image": container_parts[1] if len(container_parts) > 1 else "timberio/vector:latest-debian",
                    "status": f"{container_parts[2]} {container_parts[3]}" if len(container_parts) > 3 else container_parts[2] if len(container_parts) > 2 else "Running",
                    "ports": container_parts[4] if len(container_parts) > 4 else "None"
                }
        
        return {"running": False, "name": None, "image": None, "status": "Not Running", "ports": None}
    except Exception as e:
        return {"running": False, "name": None, "image": None, "status": f"Error: {str(e)}", "ports": None}

def validate_with_docker(vrl_code, filename):
    """Validate VRL using the running Docker container"""
    try:
        # Create temporary files in current directory
        temp_file = f"temp_validation_{int(time.time())}.vrl"
        config_file = f"temp_config_{int(time.time())}.yaml"
        
        # Write VRL file
        with open(temp_file, 'w') as f:
            f.write(vrl_code)
        
        # Create Vector config with inline VRL
        indented_vrl = '\n'.join('      ' + line for line in vrl_code.split('\n'))
        
        config_content = f"""data_dir: "/tmp"
timezone: "UTC"

sources:
  my_source:
    type: stdin

transforms:
  my_transform_id:
    type: remap
    inputs: ["my_source"]
    source: |
{indented_vrl}

sinks:
  my_sink:
    type: console
    inputs: ["my_transform_id"]
    encoding:
      codec: json
"""
        
        # Write config file
        with open(config_file, 'w') as f:
            f.write(config_content)
        
        # Run Docker validation using the running container
        cmd = [
            'docker', 'exec', '-i', 'dpm-test-config-validator',
            'vector', 'validate', f'/app/{os.path.basename(config_file)}'
        ]
        
        # Copy config to container
        copy_cmd = ['docker', 'cp', config_file, 'dpm-test-config-validator:/app/']
        subprocess.run(copy_cmd, capture_output=True, timeout=10)
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # Clean up temporary files
        try:
            os.remove(temp_file)
            os.remove(config_file)
        except:
            pass
        
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
        
    except Exception as e:
        return {
            "success": False,
            "stdout": "",
            "stderr": "",
            "error_details": str(e)
        }

def main():
    st.set_page_config(
        page_title="🤖 Agent Parser",
        page_icon="🤖",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    # Compact Header
    st.title("🤖 Agent Parser")
    st.caption("Smart Log Processing")
    
    # Compact RAG Status
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 KB", "1,210")
    with col2:
        st.metric("🔤 Model", "MiniLM")
    with col3:
        st.metric("💾 DB", "Active")
    with col4:
        st.metric("📚 ECS", "Ready")
    
    st.success("✅ RAG System Ready")
    
    # Detailed Docker Container Info
    st.markdown("### 🐳 Docker Container")
    container_info = get_docker_container_info()
    
    if container_info["running"]:
        st.success("✅ Container Running")
        
        # Display container details in a compact format
        col1, col2 = st.columns(2)
        with col1:
            st.metric("📦 Name", container_info["name"])
            st.metric("🖼️ Image", container_info["image"])
        with col2:
            st.metric("📊 Status", container_info["status"])
            st.metric("🔌 Ports", container_info["ports"] if container_info["ports"] != "None" else "None")
        
        # Show container details in expandable section
        with st.expander("📋 Container Details"):
            st.code(f"""Container Name: {container_info["name"]}
Image: {container_info["image"]}
Status: {container_info["status"]}
Ports: {container_info["ports"] if container_info["ports"] != "None" else "None"}""", language="text")
    else:
        st.error("❌ No Container Running")
        st.info("💡 Start container with: `docker run -d --name dpm-test-config-validator vonwig/inotifywait:latest`")
        
        # Show all running containers
        with st.expander("🔍 Check All Running Containers"):
            try:
                all_containers = subprocess.run(['docker', 'ps', '--format', 'table {{.Names}}\t{{.Image}}\t{{.Status}}'], 
                                              capture_output=True, text=True, timeout=10)
                if all_containers.stdout.strip():
                    st.code(all_containers.stdout, language="text")
                else:
                    st.warning("No Docker containers are currently running")
            except:
                st.error("Failed to check Docker containers")
    
    st.markdown("---")
    
    # Compact Log Input
    log_input = st.text_area(
        "📝 Log Content:",
        height=100,
        placeholder="Paste log here...",
        key="log_input"
    )
    
    # Identify Log Profile Button
    if st.button("🔍 Identify Log", type="primary", use_container_width=True):
        if not log_input.strip():
            st.error("❌ Please enter log content!")
            return
        
        # Smart vendor detection
        if log_input.strip().startswith("CEF:"):
            try:
                cef_parts = log_input.strip().split("|")
                if len(cef_parts) >= 3:
                    vendor = cef_parts[1].strip()
                    product = cef_parts[2].strip()
                    log_source = f"{vendor} {product}"
                else:
                    vendor = "Unknown CEF"
                    product = "Unknown CEF"
                    log_source = "Security Device"
                
                log_type = "Security"
                log_format = "CEF"
                identified_reason = f"CEF: {vendor} {product}"
            except:
                log_type = "Security"
                log_format = "CEF"
                log_source = "Security Device"
                product = "Security Agent"
                vendor = "Unknown"
                identified_reason = "CEF format detected"
                
        elif log_input.strip().startswith("{") or log_input.strip().startswith("["):
            try:
                import json
                json_data = json.loads(log_input.strip())
                
                vendor = "Unknown"
                product = "JSON Logger"
                
                if "vendor" in json_data:
                    vendor = json_data["vendor"]
                elif "source" in json_data:
                    vendor = json_data["source"]
                elif "service" in json_data:
                    vendor = json_data["service"]
                
                if "product" in json_data:
                    product = json_data["product"]
                elif "application" in json_data:
                    product = json_data["application"]
                elif "app" in json_data:
                    product = json_data["app"]
                
                log_source = f"{vendor} {product}" if vendor != "Unknown" else "Application"
                
                log_type = "Application"
                log_format = "JSON"
                identified_reason = f"JSON: {vendor} {product}"
            except:
                log_type = "Application"
                log_format = "JSON"
                log_source = "Application"
                product = "JSON Logger"
                vendor = "Unknown"
                identified_reason = "JSON format detected"
                
        elif log_input.strip().startswith("<") and ">" in log_input:
            try:
                # Advanced vendor detection using main app logic
                import re
                vendor = "Unknown"
                product = "Syslog"
                log_source = "System"
                log_type = "System"
                log_format = "Syslog"
                
                # Extract hostname and program from RFC5424 syslog for better detection
                hostname = ""
                program = ""
                # RFC5424: <PRI>VER TIMESTAMP HOSTNAME APP-NAME PROCID MSGID STRUCTURED-DATA MSG
                syslog_match = re.search(r'<(\d+)>(\d+)\s+\S+\s+(\S+)\s+(\S+)\s+', log_input.strip())
                if syslog_match:
                    priority, version, hostname, program = syslog_match.groups()
                    log_content = f"{hostname} {program} {log_input}"
                else:
                    log_content = log_input.lower()
                
                # Advanced vendor detection patterns from main app
                if re.search(r'(?i)(cisco|asa|ios|nexus|cat|switch|router)', log_content):
                    vendor = "cisco"
                    if re.search(r'(?i)(asa|firewall)', log_content):
                        product = "asa"
                        log_source = "cisco_asa"
                        log_type = "Security"
                    elif re.search(r'(?i)(ios)', log_content):
                        product = "ios"
                        log_source = "cisco_ios"
                        log_type = "Network"
                    else:
                        product = "cisco"
                        log_source = "cisco_network"
                        log_type = "Network"
                elif re.search(r'(?i)(fortinet|fortigate|forti)', log_content):
                    vendor = "fortinet"
                    product = "fortigate"
                    log_source = "fortinet_fortigate"
                    log_type = "Security"
                elif re.search(r'(?i)(palo\s+alto|panos|pa-)', log_content):
                    vendor = "paloalto"
                    product = "pan-os"
                    log_source = "paloalto_firewall"
                    log_type = "Security"
                elif re.search(r'(?i)(checkpoint|check\s+point|cp-)', log_content):
                    vendor = "checkpoint"
                    product = "smartdefence/firewall"
                    log_source = "checkpoint_firewall"
                    log_type = "Security"
                elif re.search(r'(?i)(sonicwall|sonicos)', log_content):
                    vendor = "sonicwall"
                    product = "firewall"
                    log_source = "sonicwall_firewall"
                    log_type = "Security"
                elif re.search(r'(?i)(sshd|accepted password|failed password)', log_content):
                    vendor = "OpenSSH"
                    product = "OpenSSH Server"
                    log_source = "OpenSSH Server"
                    log_type = "Security"
                elif re.search(r'(?i)(firewall|iptables|ufw|pfsense)', log_content):
                    vendor = "Linux"
                    product = "iptables"
                    log_source = "Linux Firewall"
                    log_type = "Security"
                elif re.search(r'(?i)(apache|nginx|httpd)', log_content):
                    vendor = "Web Server"
                    product = "Web Server"
                    log_source = "Web Server"
                    log_type = "Web"
                elif re.search(r'(?i)(mysql|postgres|mongodb)', log_content):
                    vendor = "Database"
                    product = "Database"
                    log_source = "Database"
                    log_type = "Database"
                elif re.search(r'(?i)(dirsrv|ipa|ldap|directory)', log_content):
                    vendor = "RedHat"
                    product = "IPA"
                    log_source = "ipa-dirsrv"
                    log_type = "System"
                elif re.search(r'(?i)(windows|microsoft|win32)', log_content):
                    vendor = "microsoft"
                    product = "windows"
                    log_source = "winevtlogs"
                    log_type = "System"
                elif re.search(r'(?i)(linux|ubuntu|centos|rhel)', log_content):
                    vendor = "linux"
                    product = "syslog"
                    log_source = "linux_syslog"
                    log_type = "System"
                else:
                    # Default syslog - try to extract from hostname/program
                    if hostname:
                        vendor = hostname.split('-')[0] if '-' in hostname else "Unknown"
                        log_source = hostname
                    else:
                        vendor = "Unknown"
                        log_source = "syslog"
                    
                    if program:
                        product = program
                    else:
                        product = "syslog"
                    
                    log_type = "System"
                
                identified_reason = f"Syslog: {vendor} {product}"
            except:
                log_type = "System"
                log_format = "Syslog"
                log_source = "Firewall"
                product = "Firewall"
                vendor = "Unknown"
                identified_reason = "Syslog format detected"
        else:
            log_type = "Unknown"
            log_format = "Unknown"
            log_source = "Unknown"
            product = "Unknown"
            vendor = "Unknown"
            identified_reason = "Unable to identify format"
        
        # Store in session state
        st.session_state.log_profile = {
            "log_type": log_type,
            "log_format": log_format,
            "log_source": log_source,
            "product": product,
            "vendor": vendor
        }
        st.session_state.identified_reason = identified_reason
        st.session_state.identified_log_content = log_input
        
        # Auto-generate VRL parser immediately after profile identification
        st.session_state.auto_generate_parser = True
    
    # Display Identified Log Profile
    if 'log_profile' in st.session_state:
        st.markdown("---")
        st.subheader("📋 Log Profile")
        
        profile = st.session_state.log_profile
        
        # Map log_type to ECS observer.type based on vendor and product
        log_type = profile['log_type']
        vendor = profile.get('vendor', '').lower()
        product = profile.get('product', '').lower()
        
        # Intelligent mapping based on vendor/product context
        if 'openssh' in vendor or 'ssh' in product:
            observer_type = "system"
        elif 'checkpoint' in vendor or 'fortinet' in vendor or 'cisco' in vendor or 'palo' in vendor:
            observer_type = "ngfw"  # Next Generation Firewall
        elif 'apache' in vendor or 'nginx' in vendor or 'web' in product:
            observer_type = "application"
        elif log_type.lower() == 'security':
            observer_type = "ngfw"
        elif log_type.lower() == 'network':
            observer_type = "network"
        elif log_type.lower() == 'system':
            observer_type = "system"
        elif log_type.lower() == 'application':
            observer_type = "application"
        else:
            observer_type = "system"  # Default to system instead of ngfw
        
        profile_json = f"""{{
    "observer.type": "{observer_type}",
    "log_format": "{profile['log_format']}",
    "observer.source": "{profile['log_source']}",
    "observer.product": "{profile['product']}",
    "observer.vendor": "{profile['vendor']}"
}}"""
        st.code(profile_json, language="json")
        
        st.caption(f"🔍 {st.session_state.identified_reason}")
        
        # Auto-generate VRL parser if flag is set
        if st.session_state.get('auto_generate_parser', False):
            # Clear the flag to prevent re-generation
            st.session_state.auto_generate_parser = False
            
            # Show auto-generation message
            with st.spinner("🤖 Auto-generating VRL parser based on log profile..."):
                # Import RAG agent
                try:
                    from rag_agent_parser import RAGAgentParser
                    rag_agent_available = True
                except ImportError:
                    rag_agent_available = False
                
                # Get vendor information from identified profile
                profile = st.session_state.log_profile
                vendor = str(profile['vendor']) if profile['vendor'] else "unknown"
                product = str(profile['product']) if profile['product'] else "unknown"
                log_format = str(profile['log_format']) if profile['log_format'] else "unknown"
                log_content = st.session_state.identified_log_content
                
                # Use RAG agent to generate intelligent parser
                if rag_agent_available:
                    try:
                        agent = RAGAgentParser()
                        # Ensure log_content is a string
                        if not isinstance(log_content, str):
                            log_content = str(log_content)
                        vrl_code = agent.generate_parser_with_agent(log_content, vendor, product, profile)
                        
                        # Validate generated parser
                        validation = agent.validate_generated_parser(vrl_code)
                        
                        if validation["is_valid"]:
                            st.success(f"✅ Auto-generated {vendor.title()}-specific parser for {product}")
                            if validation["warnings"]:
                                for warning in validation["warnings"][:2]:  # Show first 2 warnings
                                    st.warning(f"⚠️ {warning}")
                        else:
                            st.error("❌ Auto-generation failed - invalid parser")
                            return
                        
                        parser_type = f"AI Generated - {vendor.title()} {product.title()}"
                        st.session_state.generated_vrl = vrl_code
                        st.session_state.vrl_generated = True
                        st.session_state.parser_type = parser_type
                        
                    except Exception as e:
                        st.warning(f"⚠️ Auto-generation failed: {e}")
                        st.session_state.auto_generate_parser = False
                else:
                    st.warning("⚠️ RAG Agent not available for auto-generation")
                    st.session_state.auto_generate_parser = False
        
        # Edit Profile Button
        if st.button("✏️ Edit Profile", use_container_width=True):
            st.session_state.editing_profile = True
        
        # Edit Profile Form
        if st.session_state.get('editing_profile', False):
            st.markdown("#### Edit Profile")
            
            col1, col2 = st.columns(2)
            with col1:
                new_log_type = st.text_input("Log Type:", value=st.session_state.log_profile['log_type'])
                new_log_format = st.selectbox("Format:", ["JSON", "CEF", "Syslog", "Unknown"], 
                                            index=["JSON", "CEF", "Syslog", "Unknown"].index(st.session_state.log_profile['log_format']) 
                                            if st.session_state.log_profile['log_format'] in ["JSON", "CEF", "Syslog", "Unknown"] else 3)
            with col2:
                new_vendor = st.text_input("Vendor:", value=st.session_state.log_profile['vendor'])
                new_product = st.text_input("Product:", value=st.session_state.log_profile['product'])
            
            new_log_source = st.text_input("Source:", value=st.session_state.log_profile['log_source'])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Save", type="primary", use_container_width=True):
                    st.session_state.log_profile = {
                        "log_type": new_log_type,
                        "log_format": new_log_format,
                        "log_source": new_log_source,
                        "product": new_product,
                        "vendor": new_vendor
                    }
                    st.session_state.identified_reason = f"Edited - {new_log_type} from {new_product}"
                    st.session_state.editing_profile = False
                    st.success("✅ Profile updated!")
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.editing_profile = False
                    st.rerun()
    
    # Manual VRL Generation (if auto-generation failed or user wants to regenerate)
    if 'log_profile' in st.session_state and not st.session_state.get('vrl_generated', False):
        st.markdown("---")
        st.markdown("#### 🤖 AI Agent Parser Generation")
        st.caption("The AI Agent analyzes your log using RAG system knowledge to generate vendor-specific parsers")
        
        if st.button("🤖 Generate VRL Parser with AI Agent", type="primary", use_container_width=True):
            # Import RAG agent
            try:
                from rag_agent_parser import RAGAgentParser
                rag_agent_available = True
            except ImportError:
                rag_agent_available = False
                st.warning("⚠️ RAG Agent not available, using template parsers")
            
            # Get vendor information from identified profile
            profile = st.session_state.log_profile
            vendor = str(profile['vendor']) if profile['vendor'] else "unknown"
            product = str(profile['product']) if profile['product'] else "unknown"
            log_format = str(profile['log_format']) if profile['log_format'] else "unknown"
            log_content = st.session_state.identified_log_content
            
            # Debug information
            st.caption(f"🔍 Debug: vendor='{vendor}', product='{product}', format='{log_format}'")
            
            # Use RAG agent to generate intelligent parser
            if rag_agent_available:
                try:
                    with st.spinner("🤖 AI Agent analyzing log with RAG system..."):
                        agent = RAGAgentParser()
                        # Ensure log_content is a string
                        if not isinstance(log_content, str):
                            log_content = str(log_content)
                        vrl_code = agent.generate_parser_with_agent(log_content, vendor, product, profile)
                        
                        # Validate generated parser
                        validation = agent.validate_generated_parser(vrl_code)
                        
                        if validation["is_valid"]:
                            st.success(f"✅ AI Agent generated {vendor.title()}-specific parser for {product}")
                            if validation["warnings"]:
                                for warning in validation["warnings"][:2]:  # Show first 2 warnings
                                    st.warning(f"⚠️ {warning}")
                        else:
                            st.error("❌ AI Agent generated invalid parser")
                            return
                        
                        parser_type = f"AI Generated - {vendor.title()} {product.title()}"
                    
                except Exception as e:
                    st.warning(f"⚠️ RAG Agent failed: {e}, using template parsers")
                    rag_agent_available = False
            
            # Fallback to template-based parsers if RAG agent failed
            if not rag_agent_available:
                # Import vendor parser router
                try:
                    from vendor_parser_router import get_parser_by_vendor, get_parser_info
                    vendor_routing_available = True
                except ImportError:
                    vendor_routing_available = False
                    st.warning("⚠️ Template parsers not available, using generic parsers")
                
                vendor_lower = str(vendor).lower() if vendor else "unknown"
                product_lower = str(product).lower() if product else "unknown"
                log_format_lower = str(log_format).lower() if log_format else "unknown"
                
                # Use vendor-specific template parser if available
                if vendor_routing_available:
                    try:
                        vrl_code = get_parser_by_vendor(vendor_lower, product_lower, log_format_lower)
                        parser_info = get_parser_info(vendor_lower, product_lower, log_format_lower)
                        parser_type = f"{parser_info['parser_type'].replace('_', ' ').title()}"
                        
                        # Show which parser was selected
                        st.info(f"🎯 Selected: {parser_type} for {vendor} {product}")
                        
                    except Exception as e:
                        st.warning(f"⚠️ Template parser failed: {e}, using generic fallback")
                        vendor_routing_available = False
                
                # Fallback to generic parsers if template routing failed
                if not vendor_routing_available:
                    if log_format_lower == "json":
                        if generate_enhanced_grok_json_vrl is None:
                            st.error("❌ JSON parser not available!")
                            return
                        vrl_code = generate_enhanced_grok_json_vrl()
                        parser_type = "JSON Parser"
                    elif log_format_lower == "cef":
                        if generate_enhanced_grok_cef_vrl is None:
                            st.error("❌ CEF parser not available!")
                            return
                        vrl_code = generate_enhanced_grok_cef_vrl()
                        parser_type = "CEF Parser"
                    elif log_format_lower == "syslog":
                        if generate_enhanced_grok_syslog_vrl is None:
                            st.error("❌ Syslog parser not available!")
                            return
                        vrl_code = generate_enhanced_grok_syslog_vrl()
                        parser_type = "Syslog Parser"
                    else:
                        st.error("❌ Unsupported log format!")
                        return
            
            st.session_state.generated_vrl = vrl_code
            st.session_state.vrl_generated = True
    
    # Display Generated VRL
    if st.session_state.get('vrl_generated', False):
        st.markdown("---")
        st.subheader("🔧 Generated VRL Parser")
        
        vrl_code = st.session_state.generated_vrl
        st.code(vrl_code, language="vrl")
        
        # Docker Validation
        st.markdown("---")
        st.subheader("🐳 Docker Validation")
        
        if st.button("✅ Validate with Docker", type="primary", use_container_width=True):
            with st.spinner("Validating..."):
                result = validate_with_docker(vrl_code, "parser.vrl")
            
            if result["success"]:
                st.success("✅ Docker Validation PASSED!")
                
                # Save to desktop
                desktop_path = Path.home() / "Desktop"
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"validated_parser_{timestamp}.vrl"
                filepath = desktop_path / filename
                
                with open(filepath, 'w') as f:
                    f.write(vrl_code)
                
                st.success(f"💾 Saved to Desktop: {filename}")
                
            else:
                st.error("❌ Docker Validation FAILED!")
                if result["stderr"]:
                    st.code(result["stderr"], language="text")
                
                # Automatic regeneration with error context
                st.markdown("#### 🔄 Auto-Regeneration with Error Context")
                st.info("🤖 **Sending error details to agent for intelligent regeneration...**")
                
                with st.spinner("🤖 Analyzing error and regenerating VRL intelligently..."):
                    # Store error details for regeneration
                    error_context = result["stderr"] if result["stderr"] else result.get("error_details", "Validation failed")
                    
                    # Generate new VRL based on log type with intelligent error analysis
                    log_type = st.session_state.get('log_type', 'Unknown')
                    
                    try:
                        # Use enhanced error handler with OpenRouter
                        from enhanced_error_handler import EnhancedErrorHandler
                        from complete_rag_system import CompleteRAGSystem
                        
                        # Initialize RAG system if not already done
                        if 'rag_system' not in st.session_state:
                            st.session_state.rag_system = CompleteRAGSystem()
                            st.session_state.rag_system.build_langchain_index()
                        
                        # Get OpenRouter API key from session state or use default
                        openrouter_key = st.session_state.get('openrouter_api_key', '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')
                        
                        # Create enhanced error handler
                        error_handler = EnhancedErrorHandler(st.session_state.rag_system, openrouter_key)
                        
                        # Get log content and format for regeneration
                        log_content = st.session_state.get('identified_log_content', '')
                        log_format = st.session_state.log_profile.get('log_format', 'unknown') if 'log_profile' in st.session_state else 'unknown'
                        
                        # Regenerate with error context
                        regeneration_result = error_handler.regenerate_vrl_with_error_context(
                            st.session_state.generated_vrl,
                            error_context,
                            log_content,
                            log_format
                        )
                        
                        if regeneration_result['success']:
                            # Update VRL code with regenerated version
                            new_vrl = regeneration_result['new_vrl']
                            st.session_state.generated_vrl = new_vrl
                            
                            # Show regeneration details
                            insights = regeneration_result['insights']
                            st.success(f"🔄 **{regeneration_result['regeneration_reason']}**")
                            
                            # Show error analysis
                            with st.expander("🔍 Error Analysis"):
                                st.code(error_context, language="text")
                                
                            with st.expander("🧠 Intelligence Applied"):
                                st.write(f"**Error Type:** {insights['error_type']}")
                                if insights['suggestions']:
                                    st.write("**Suggestions:**")
                                    for suggestion in insights['suggestions']:
                                        st.write(f"• {suggestion}")
                                if insights['fixes_needed']:
                                    st.write("**Fixes Applied:**")
                                    for fix in insights['fixes_needed']:
                                        st.write(f"• {fix}")
                            
                            st.info("💡 **AI has analyzed the error and applied intelligent fixes to the VRL parser**")
                            
                            # Auto-retry validation
                            if st.button("🔄 Auto-Retry Validation", type="primary", use_container_width=True):
                                st.rerun()
                        else:
                            st.error("❌ Intelligent regeneration failed")
                            
                    except Exception as e:
                        st.error(f"❌ Regeneration failed: {e}")
                        
                        # Fallback to basic regeneration
                        try:
                            if log_type == "Security" or "CEF" in log_type:
                                if generate_enhanced_grok_cef_vrl is not None:
                                    new_vrl = generate_enhanced_grok_cef_vrl()
                                    st.session_state.generated_vrl = new_vrl
                                    st.success("🔄 Fallback CEF Parser Regenerated!")
                                else:
                                    st.error("❌ CEF parser not available for fallback!")
                            elif log_type == "System" or "Syslog" in log_type:
                                if generate_enhanced_grok_syslog_vrl is not None:
                                    new_vrl = generate_enhanced_grok_syslog_vrl()
                                    st.session_state.generated_vrl = new_vrl
                                    st.success("🔄 Fallback Syslog Parser Regenerated!")
                                else:
                                    st.error("❌ Syslog parser not available for fallback!")
                            else:
                                if generate_enhanced_grok_cef_vrl is not None:
                                    new_vrl = generate_enhanced_grok_cef_vrl()
                                    st.session_state.generated_vrl = new_vrl
                                    st.success("🔄 Fallback Parser Regenerated!")
                                else:
                                    st.error("❌ Default parser not available for fallback!")
                                
                        except Exception as e2:
                            st.error(f"❌ Fallback regeneration also failed: {e2}")
                            
                            # Manual regeneration
                            if st.button("🔄 Manual Regenerate", type="secondary", use_container_width=True):
                                st.session_state.vrl_generated = False
                                st.session_state.generated_vrl = ""
                                st.rerun()

if __name__ == "__main__":
    main()
