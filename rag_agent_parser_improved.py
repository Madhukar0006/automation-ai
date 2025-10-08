#!/usr/bin/env python3
"""
Improved RAG Agent Parser with Better Ollama Prompts
Generates proper GROK patterns and field renaming like GPT-4
"""

import json
import requests
import re
from typing import Dict, Any, List
from complete_rag_system import CompleteRAGSystem

class ImprovedRAGAgentParser:
    """Improved RAG Agent Parser with better Ollama prompts"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.rag_system = None
        
    def build_rag_system(self):
        """Build RAG system if not already built"""
        if self.rag_system is None:
            self.rag_system = CompleteRAGSystem()
            self.rag_system.build_langchain_index()
    
    def analyze_log_with_rag(self, log_content: str, vendor: str, product: str) -> Dict[str, Any]:
        """Analyze log with RAG system for better insights"""
        try:
            self.build_rag_system()
            
            # Create search query
            query = f"{vendor} {product} log parsing VRL"
            
            # Get relevant documents from RAG
            relevant_docs = self.rag_system.search_documents(query, top_k=3)
            
            # Extract insights
            rag_insights = []
            for doc in relevant_docs:
                rag_insights.append({
                    "content": doc.page_content[:200] + "...",
                    "source": doc.metadata.get("source", "unknown")
                })
            
            return {
                "vendor": vendor,
                "product": product,
                "rag_insights": rag_insights,
                "parsing_strategy": "improved_dynamic"
            }
            
        except Exception as e:
            print(f"⚠️ RAG System not available, using basic field mapping: {e}")
            return {
                "vendor": vendor,
                "product": product,
                "rag_insights": [],
                "parsing_strategy": "basic_dynamic"
            }
    
    def create_improved_prompt(self, log_content: str, analysis: Dict[str, Any]) -> str:
        """Create improved prompt for Ollama to generate proper VRL"""
        
        vendor = analysis.get('vendor', 'unknown').lower()
        product = analysis.get('product', 'unknown')
        
        # Analyze the log structure first
        log_analysis = self._analyze_log_structure(log_content)
        
        # Create improved prompt similar to GPT-4 system
        prompt = f"""Generate PRODUCTION-READY VRL parser for this log with EXCELLENT structure:

LOG TO ANALYZE:
{log_content}

LOG STRUCTURE ANALYSIS:
{log_analysis}

VENDOR: {vendor}
PRODUCT: {product}

CRITICAL REQUIREMENTS - ANALYZE THE LOG AND GENERATE CORRECT PARSER:

⚠️ IMPORTANT: DO NOT generate generic syslog parsers! 
Analyze the ACTUAL log content and create a CUSTOM parser for THIS specific log!

1. ANALYZE THE LOG STRUCTURE FIRST:
   - Look at the log analysis above to understand what fields are present
   - Create GROK patterns that MATCH the actual log structure
   - Extract ALL fields found in the analysis (IPs, ports, emails, etc.)
   - DO NOT use generic parse_syslog() - create custom GROK patterns!

2. PERFECT STRUCTURE & INDENTATION:
   - Use clear section headers with #### and ###
   - Proper 2-space indentation
   - Descriptive comments for each section
   - Logical grouping of operations

2. PROPER FIELD RENAMING & LOGIC:
   - Use pattern: if exists(.old_field) {{ .new_field = del(.old_field) }}
   - Map to proper ECS fields
   - Clean deletion with del() function

3. ADVANCED GROK PATTERNS (CUSTOM FOR THIS LOG):
   - Use parse_groks() with multiple patterns
   - Include fallback: "%{{GREEDYDATA:unparsed}}"
   - Use named captures: (?<name>pattern)
   - Create patterns that MATCH the specific log structure above
   - Extract ALL fields found in the log analysis (IPs, ports, emails, timestamps, etc.)
   - DO NOT use generic parse_syslog() - create CUSTOM patterns!

4. SMART LOGIC & ERROR HANDLING:
   - Conditional processing based on field values
   - Proper null checks and validation
   - Outcome determination (success/failure)

5. DATA PROCESSING:
   - Use parse_key_value!() for structured data
   - Proper timestamp processing
   - Data merging with merge() function

EXACT OUTPUT FORMAT:
###############################################################
## VRL Transforms for {vendor.title()} {product.title()} Logs
###############################################################      

#### Adding ECS fields ####
if !exists(.observer.type) {{ .observer.type = "application" }}
if !exists(.observer.vendor) {{ .observer.vendor = "{vendor}" }}
if !exists(.observer.product) {{ .observer.product = "{product}" }}
if !exists(.event.dataset) {{ .event.dataset = "{product.lower()}.logs" }}

#### Parse log message ####
if exists(.event.original) {{ 
  _grokked, err = parse_groks(.event.original, [
    "[GROK-PATTERN-1]",
    "[GROK-PATTERN-2]",
    "%{{GREEDYDATA:unparsed}}"
  ])
  if err == null {{     
   . = merge(., _grokked, deep: true)
  }}
}}

#### Field extraction and ECS mapping ####
if exists(.field1) {{ .ecs_field1 = del(.field1) }}
if exists(.field2) {{ .ecs_field2 = del(.field2) }}

#### Smart logic and outcome determination ####
if exists(.error_field) && .error_field == "0" {{
   .event.outcome = "success"
}} else if exists(.error_field) && .error_field != "0" {{
   .event.outcome = "failure"
}}

#### Cleanup ####
del(.temp_field1)
del(.temp_field2)
. = compact(., string: true, array: true, object: true, null: true)

Generate ONLY the VRL code above with proper GROK patterns, field renaming, and logic.

IMPORTANT: Generate a COMPLETE VRL parser with ALL sections above. Do not stop early!
The parser should be at least 50 lines long and include ALL the sections shown in the template."""
        
        return prompt
    
    def _analyze_log_structure(self, log_content: str) -> str:
        """Analyze log structure to help generate correct GROK patterns"""
        analysis = []
        
        # Basic log analysis
        analysis.append(f"LOG LENGTH: {len(log_content)} characters")
        analysis.append(f"LOG TYPE: {'Syslog' if log_content.startswith('<') else 'Other'}")
        
        # Analyze common patterns
        if log_content.startswith('<'):
            analysis.append("SYSLOG HEADER DETECTED:")
            analysis.append(f"  - Priority: {log_content[1:log_content.find('>')] if '>' in log_content else 'Not found'}")
            analysis.append(f"  - Version: {log_content[log_content.find('>')+1:log_content.find('>')+2] if '>' in log_content else 'Not found'}")
        
        # Look for timestamps
        import re
        timestamp_patterns = [
            r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO8601
            r'\w{3}\s+\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}',  # Apache style
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}'  # Standard format
        ]
        
        for pattern in timestamp_patterns:
            matches = re.findall(pattern, log_content)
            if matches:
                analysis.append(f"TIMESTAMP DETECTED: {matches[0]}")
                break
        
        # Look for IP addresses
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, log_content)
        if ips:
            analysis.append(f"IP ADDRESSES: {', '.join(ips)}")
        
        # Look for ports
        port_pattern = r':(\d{4,5})'
        ports = re.findall(port_pattern, log_content)
        if ports:
            analysis.append(f"PORTS: {', '.join(ports)}")
        
        # Look for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, log_content)
        if emails:
            analysis.append(f"EMAIL ADDRESSES: {', '.join(emails)}")
        
        # Look for bracketed sections
        bracket_pattern = r'\[([^\]]+)\]'
        brackets = re.findall(bracket_pattern, log_content)
        if brackets:
            analysis.append(f"BRACKETED SECTIONS: {', '.join(brackets[:5])}")  # Limit to first 5
        
        # Look for key-value pairs
        kv_pattern = r'(\w+)=([^\s]+)'
        kv_pairs = re.findall(kv_pattern, log_content)
        if kv_pairs:
            analysis.append(f"KEY-VALUE PAIRS: {', '.join([f'{k}={v}' for k, v in kv_pairs[:3]])}")
        
        return '\n'.join(analysis)
    
    def call_ollama_improved(self, prompt: str) -> str:
        """Call Ollama with improved settings for better VRL generation"""
        try:
            # Use improved settings for better VRL generation
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Slightly higher for more creativity
                        "top_p": 0.9,
                        "num_predict": 3000,  # More tokens for longer output
                        "repeat_penalty": 1.1,
                        "stop": ["```", "### END", "--- END"]  # Better stop conditions
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                raise Exception(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"Failed to call Ollama: {e}")
    
    def generate_parser_with_improved_ollama(self, log_content: str, vendor: str, product: str, log_profile: dict = None) -> str:
        """Generate parser using improved Ollama with better prompts"""
        
        # Analyze log structure first (NEW METHOD)
        log_analysis = self._analyze_log_structure(log_content)
        
        # Create analysis dict for compatibility
        analysis = {
            'vendor': vendor,
            'product': product,
            'log_format': log_profile.get('log_format', 'unknown') if log_profile else 'unknown'
        }
        
        # Create improved prompt with log analysis
        prompt = self.create_improved_prompt(log_content, analysis)
        
        # Generate parser using improved Ollama
        print(f"🤖 Generating {vendor.title()} parser with improved Ollama...")
        try:
            parser_code = self.call_ollama_improved(prompt)
            
            # Clean up the generated VRL
            proper_vrl = self._clean_generated_vrl(parser_code)
            
            print(f"✅ Improved Ollama generated {len(parser_code)} characters, cleaned to {len(proper_vrl)} characters")
            return proper_vrl
            
        except Exception as e:
            print(f"❌ Improved Ollama failed: {e}")
            raise Exception(f"Improved Ollama failed to generate parser: {e}")
    
    def _clean_generated_vrl(self, vrl_code: str) -> str:
        """Clean up generated VRL code"""
        
        # Remove markdown formatting
        if vrl_code.startswith("```"):
            lines = vrl_code.split('\n')
            start_idx = 1 if lines[0].startswith("```") else 0
            end_idx = len(lines)
            
            # Find closing ```
            for i, line in enumerate(lines):
                if line.strip() == "```" and i > start_idx:
                    end_idx = i
                    break
            
            vrl_code = '\n'.join(lines[start_idx:end_idx])
        
        # Fix common issues
        vrl_code = re.sub(r'return\s*$', '', vrl_code, flags=re.MULTILINE)  # Remove standalone return
        vrl_code = re.sub(r'exit\s*$', 'return', vrl_code, flags=re.MULTILINE)  # Replace exit with return
        
        # Ensure proper ending
        if not vrl_code.strip().endswith(". = compact(.)"):
            vrl_code = vrl_code.strip() + "\n\n. = compact(.)"
        
        return vrl_code.strip()

def test_improved_ollama():
    """Test the improved Ollama system"""
    
    print("🧪 Testing Improved Ollama VRL Generation")
    print("=" * 50)
    
    # Test log
    test_log = '<190>1 2025-09-18T07:40:33.360853+00:00 ma1-ipa-master httpd-error - - - [Thu Sep 18 07:40:31.606853 2025] [wsgi:error] [pid 2707661:tid 2707884] [remote 10.10.6.173:60801] ipa: INFO: [jsonserver_session] dhan@BHERO.IO: batch(config_show(), whoami(), env(None), dns_is_enabled(), trustconfig_show(), domainlevel_get(), ca_is_enabled(), vaultconfig_show()): SUCCESS'
    
    try:
        # Create improved agent
        agent = ImprovedRAGAgentParser()
        
        # Generate parser
        vrl_code = agent.generate_parser_with_improved_ollama(test_log, 'ipa', 'httpd', {'log_format': 'syslog'})
        
        print("✅ Improved Ollama Generated VRL Successfully!")
        print("📏 Length:", len(vrl_code))
        print()
        print("🔧 Generated VRL:")
        print(vrl_code)
        print()
        print("🎯 This has proper GROK patterns, field renaming, and logic!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure Ollama is running with: ollama serve")

if __name__ == "__main__":
    test_improved_ollama()
