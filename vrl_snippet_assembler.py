"""
VRL Snippet Assembler
Assembles VRL snippets based on log format detection
"""

import os
from typing import Dict, List, Optional
from log_analyzer import identify_log_type


class VRLSnippetAssembler:
    """Assembles VRL snippets based on log format and requirements"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.snippet_files = {
            "commons": "commansineppets.vrl",
            "eventcreated": "eventcreatedsinppets.vrl", 
            "syslog": "syslogsinppets.vrl",
            "format_specific": "format_specific_parser.vrl",
            "json_handler": "json_handler.vrl"
        }
    
    def _load_snippet(self, snippet_name: str) -> Optional[str]:
        """Load a VRL snippet from file"""
        if snippet_name not in self.snippet_files:
            return None
            
        file_path = os.path.join(self.data_dir, self.snippet_files[snippet_name])
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            print(f"Warning: Snippet file not found: {file_path}")
            return None
        except Exception as e:
            print(f"Error loading snippet {snippet_name}: {e}")
            return None
    
    def _create_json_handler_snippet(self) -> str:
        """Create JSON handler snippet for all formats"""
        return """
# JSON Handler - Always included for JSON logs
if exists(.message) && is_json(string!(.message)) {
    .event.original = del(.message)
    parsed, err = parse_json(string!(.event.original))
    if err == null {
        .event_data = object!(parsed)
    }
} else if is_string(.message) {
    .event.original = del(.message)
    .event_data = .event.original
} else if !exists(.message) {
    parsed = object(.); del(.); .event = {}
    .event.original = encode_json(parsed)
    .event_data = parsed
}

# Initialize event_data if not exists
if !exists(.event_data) {
    .event_data = {}
}
"""
    
    def assemble_vrl(self, raw_log: str, log_format: Optional[str] = None) -> str:
        """
        Assemble VRL parser from snippets based on log format
        
        Args:
            raw_log: Raw log line for format detection
            log_format: Pre-detected log format (optional)
            
        Returns:
            Complete VRL parser code
        """
        # Detect log format if not provided
        if log_format is None:
            log_format = identify_log_type(raw_log)
        
        vrl_parts = []
        
        # Format-specific assembly logic
        if log_format == "json":
            # JSON-specific assembly
            json_handler = self._create_json_handler_snippet()
            vrl_parts.append(json_handler)
            
            # Add JSON-specific commons
            commons = self._load_snippet("commons")
            if commons:
                vrl_parts.append(commons)
            
            # Add eventcreated for JSON
            eventcreated = self._load_snippet("eventcreated")
            if eventcreated:
                vrl_parts.append(eventcreated)
            
            # Add JSON-specific format parser
            format_specific = self._load_snippet("format_specific")
            if format_specific:
                vrl_parts.append(format_specific)
                
        elif log_format == "syslog":
            # Syslog-specific assembly
            commons = self._load_snippet("commons")
            if commons:
                vrl_parts.append(commons)
            
            # Add syslog-specific snippet
            syslog = self._load_snippet("syslog")
            if syslog:
                vrl_parts.append(syslog)
            
            # Add eventcreated for syslog
            eventcreated = self._load_snippet("eventcreated")
            if eventcreated:
                vrl_parts.append(eventcreated)
            
            # Add format-specific parser for syslog
            format_specific = self._load_snippet("format_specific")
            if format_specific:
                vrl_parts.append(format_specific)
                
        elif log_format == "cef":
            # CEF-specific assembly
            commons = self._load_snippet("commons")
            if commons:
                vrl_parts.append(commons)
            
            # Add CEF-specific parsing
            cef_parser = self._create_cef_parser_snippet()
            vrl_parts.append(cef_parser)
            
            # Add eventcreated for CEF
            eventcreated = self._load_snippet("eventcreated")
            if eventcreated:
                vrl_parts.append(eventcreated)
                
        elif log_format == "clf":
            # CLF-specific assembly
            commons = self._load_snippet("commons")
            if commons:
                vrl_parts.append(commons)
            
            # Add CLF-specific parsing
            clf_parser = self._create_clf_parser_snippet()
            vrl_parts.append(clf_parser)
            
            # Add eventcreated for CLF
            eventcreated = self._load_snippet("eventcreated")
            if eventcreated:
                vrl_parts.append(eventcreated)
                
        else:
            # Generic/unknown format - minimal assembly
            commons = self._load_snippet("commons")
            if commons:
                vrl_parts.append(commons)
            
            # Add eventcreated
            eventcreated = self._load_snippet("eventcreated")
            if eventcreated:
                vrl_parts.append(eventcreated)
        
        # Add final cleanup
        cleanup = """
# Final cleanup and validation
. = compact(., string: true, array: true, object: true, null: true)
"""
        vrl_parts.append(cleanup)
        
        # Join all parts
        complete_vrl = "\n\n".join(vrl_parts)
        
        return complete_vrl
    
    def _create_cef_parser_snippet(self) -> str:
        """Create CEF-specific parser snippet"""
        return """
# CEF Parser - Comprehensive ECS Mapping
# Parse CEF message
if exists(.message) {
    .event.original = del(.message)
    parsed, err = parse_cef(.event.original)
    if err == null {
        .cef = object!(parsed)
        
        # Map CEF fields to ECS
        if exists(.cef.device_vendor) {
            .observer.vendor = del(.cef.device_vendor)
        }
        if exists(.cef.device_product) {
            .observer.product = del(.cef.device_product)
        }
        if exists(.cef.device_version) {
            .observer.version = del(.cef.device_version)
        }
        if exists(.cef.severity) {
            .event.severity = del(.cef.severity)
            .log.level = string!(.event.severity)
        }
        if exists(.cef.name) {
            .event.action = del(.cef.name)
        }
        if exists(.cef.signature) {
            .event.description = del(.cef.signature)
        }
        
        # Parse CEF extensions
        if exists(.cef.extensions) {
            .event_data = merge(.event_data, .cef.extensions, deep: true)
        }
    }
}

# Set CEF-specific ECS fields
.event.kind = "event"
.event.category = ["security"]
.observer.type = "security"
.log.format = "cef"
"""
    
    def _create_clf_parser_snippet(self) -> str:
        """Create CLF-specific parser snippet"""
        return """
# CLF Parser - Comprehensive ECS Mapping
# Parse CLF message
if exists(.message) {
    .event.original = del(.message)
    parsed, err = parse_common_log(.event.original)
    if err == null {
        # Map CLF fields to ECS
        if exists(parsed.client_ip) {
            .source.ip = del(parsed.client_ip)
            .network.source.ip = .source.ip
        }
        if exists(parsed.ident) {
            .user.name = del(parsed.ident)
        }
        if exists(parsed.auth) {
            .user.name = del(parsed.auth)
        }
        if exists(parsed.timestamp) {
            .event.created = parse_timestamp!(del(parsed.timestamp), format: "%d/%b/%Y:%H:%M:%S %z")
            .@timestamp = .event.created
        }
        if exists(parsed.method) {
            .http.request.method = del(parsed.method)
        }
        if exists(parsed.uri) {
            .url.original = del(parsed.uri)
            .url.path = .url.original
        }
        if exists(parsed.status) {
            .http.response.status_code = to_int!(del(parsed.status))
        }
        if exists(parsed.size) {
            .http.response.bytes = to_int!(del(parsed.size))
        }
        if exists(parsed.user_agent) {
            .user_agent.original = del(parsed.user_agent)
        }
    }
}

# Set CLF-specific ECS fields
.event.kind = "event"
.event.category = ["web"]
.observer.type = "web-server"
.log.format = "clf"
"""
    
    def get_available_snippets(self) -> List[str]:
        """Get list of available snippet files"""
        available = []
        for name, filename in self.snippet_files.items():
            file_path = os.path.join(self.data_dir, filename)
            if os.path.exists(file_path):
                available.append(name)
        return available
    
    def validate_snippet(self, snippet_name: str) -> bool:
        """Validate that a snippet file exists and is readable"""
        if snippet_name not in self.snippet_files:
            return False
            
        file_path = os.path.join(self.data_dir, self.snippet_files[snippet_name])
        return os.path.exists(file_path) and os.access(file_path, os.R_OK)


# Test the assembler
if __name__ == "__main__":
    assembler = VRLSnippetAssembler()
    
    # Test with different log formats
    test_logs = [
        '{"properties":{"category":"AzureFirewallNatRuleLog"}}',  # JSON
        '<34>1 2023-10-11T22:14:15.003Z siem su - ID47 - BOM\'su root\' failed',  # Syslog
        'CEF:0|Security|threatmanager|1.0|100|worm successfully stopped|3|src=10.0.0.1',  # CEF
    ]
    
    for log in test_logs:
        print(f"\n=== Testing log: {log[:50]}... ===")
        vrl = assembler.assemble_vrl(log)
        print(f"Generated VRL length: {len(vrl)} characters")
        print(f"Available snippets: {assembler.get_available_snippets()}")
        print("---")
