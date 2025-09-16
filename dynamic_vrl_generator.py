"""
Dynamic VRL Generator
Generates format-specific VRL based on actual log content and type
"""

import re
import json
from typing import Dict, List, Optional
from log_analyzer import identify_log_type


class DynamicVRLGenerator:
    """Generates dynamic VRL based on log format and content analysis"""
    
    def __init__(self):
        self.log_analyzer = identify_log_type
    
    def generate_vrl(self, raw_log: str, context: str = "") -> Dict:
        """Generate dynamic VRL based on log analysis"""
        result = {
            "success": True,
            "vrl_code": "",
            "errors": [],
            "log_format": "",
            "analysis": {}
        }
        
        try:
            # Analyze the log
            log_format = self.log_analyzer(raw_log)
            result["log_format"] = log_format
            
            # Generate format-specific VRL
            if log_format == "json":
                vrl_code = self._generate_json_vrl(raw_log)
            elif log_format == "syslog":
                vrl_code = self._generate_syslog_vrl(raw_log)
            elif log_format == "cef":
                vrl_code = self._generate_cef_vrl(raw_log)
            elif log_format == "clf":
                vrl_code = self._generate_clf_vrl(raw_log)
            else:
                vrl_code = self._generate_generic_vrl(raw_log)
            
            result["vrl_code"] = vrl_code
            result["analysis"] = self._analyze_log_content(raw_log, log_format)
            
        except Exception as e:
            result["success"] = False
            result["errors"].append(f"Generation error: {str(e)}")
            result["vrl_code"] = self._generate_fallback_vrl(raw_log)
        
        return result
    
    def _generate_json_vrl(self, raw_log: str) -> str:
        """Generate comprehensive VRL for JSON logs following proper structure"""
        try:
            # Parse JSON to understand structure
            log_data = json.loads(raw_log)
            
            vrl_parts = [
                "### Add Event UUID, Organization-ID, Sensor-ID",
                "if !exists(.uuid) { .uuid = uuid_v4() }",
                "if !exists(.organization.id) { .organization.id = get_env_var(\"ORG_CODE\") ?? \"d3b6842a\" }",
                "if !exists(.sensor.id) { .sensor.id = get_env_var(\"SENSOR_ID\") ?? \"GD_VR_S01\" }",
                "",
                ".observer.type = \"application\"",
                ".observer.vendor = \"unknown\"",
                ".observer.product = \"unknown\"",
                ".enrich.geoip = \"true\"",
                ".enrich.iana = \"true\"",
                ".log.schema = \"raw\"",
                ".log.format = \"json\"",
                "",
                "### Add \"event.original\" field",
                "if exists(.message) && is_json(string!(.message)) {",
                "  .event.original = del(.message)",
                "  parsed, err = parse_json(string!(.event.original))",
                "  if err == null {",
                "    .event_data = object!(parsed)",
                "  }",
                "} else if is_string(.message) {",
                "    .event.original = del(.message)",
                "    .event_data = .event.original",
                "} else if !exists(.message) {",
                "    parsed = object(.); del(.); .event = {}",
                "    .event.original = encode_json(parsed)",
                "    .event_data = parsed",
                "}",
                "",
                "###### Parser start ############",
                ".relate.ip = []",
                ".related.hosts = []",
                ".related.user = []",
                ""
            ]
            
            # Add field mapping and processing based on JSON content
            if isinstance(log_data, dict):
                for key, value in log_data.items():
                    key_lower = key.lower()
                    
                    # Timestamp handling
                    if key_lower in ['time', 'timestamp', 'created', 'datetime', 'date']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .event.created = parse_timestamp!(.event_data.{key}, format: \"%Y-%m-%dT%H:%M:%S%.3fZ\")",
                            f"    .event.created = format_timestamp!(.event.created, format: \"%Y-%m-%dT%H:%M:%S%.3fZ\")",
                            f"}}",
                            ""
                        ])
                    
                    # Log level/severity
                    elif key_lower in ['level', 'severity', 'log_level', 'priority']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .event.severity = del(.event_data.{key})",
                            f"    .log.level = string!(.event.severity)",
                            f"}}",
                            ""
                        ])
                    
                    # Host information
                    elif key_lower in ['host', 'hostname', 'host_name', 'server']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .host.name = del(.event_data.{key})",
                            f"    .observer.hostname = .host.name",
                            f"}}",
                            ""
                        ])
                    
                    # User information
                    elif key_lower in ['user', 'username', 'user_name', 'account']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .user.name = del(.event_data.{key})",
                            f"}}",
                            ""
                        ])
                    
                    # Message/description
                    elif key_lower in ['msg', 'message', 'description', 'text', 'content']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .event.description = del(.event_data.{key})",
                            f"}}",
                            ""
                        ])
                    
                    # IP addresses
                    elif key_lower in ['ip', 'ip_address', 'client_ip', 'source_ip']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .source.ip = del(.event_data.{key})",
                            f"    .network.source.ip = .source.ip",
                            f"}}",
                            ""
                        ])
                    
                    # HTTP/URL information
                    elif key_lower in ['url', 'uri', 'path', 'endpoint']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .url.original = del(.event_data.{key})",
                            f"    .url.path = .url.original",
                            f"}}",
                            ""
                        ])
                    
                    # Status codes
                    elif key_lower in ['status', 'status_code', 'code', 'response_code']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .http.response.status_code = to_int!(del(.event_data.{key}))",
                            f"}}",
                            ""
                        ])
                    
                    # Method
                    elif key_lower in ['method', 'http_method', 'request_method']:
                        vrl_parts.extend([
                            f"if exists(.event_data.{key}) {{",
                            f"    .http.request.method = del(.event_data.{key})",
                            f"}}",
                            ""
                        ])
            
            # Add vendor-specific logic if detected
            if any(vendor in raw_log.lower() for vendor in ['cisco', 'checkpoint', 'fortinet', 'palo']):
                vrl_parts.extend([
                    "if contains(string!(.event.original), \"cisco\") {",
                    "    .observer.vendor = \"cisco\"",
                    "    .observer.product = \"unknown\"",
                    "    .observer.type = \"firewall\"",
                    "}",
                    ""
                ])
            
            # Add ECS field initialization and processing
            vrl_parts.extend([
                ".event.kind = \"event\"",
                ".event.category = []",
                ".event.category = push(.event.category, \"application\")",
                "",
                "if exists(.source.ip) && !is_null(.source.ip) {",
                "  .event.category = push(.event.category, \"network\")",
                "  .event.type = [\"connection\"]",
                "}",
                "",
                "if exists(.user.name){",
                "  . |= parse_groks!( (.user.name), [",
                "      \"%{DATA:_tmp.user_leading_domain}\\\\\\%{DATA:user_name}@%{GREEDYDATA:user_domain}\",",
                "      \"%{DATA:user_name}@%{GREEDYDATA:user_domain}\",",
                "      \"%{DATA:user_domain}\\\\\\%{GREEDYDATA:user_name}\",",
                "      \"%{GREEDYDATA:user_name}\"",
                "    ])",
                "}",
                "if exists(.user_name) {.user.name = del(.user_name)}",
                "if exists(.user_domain) {.user.domain = del(.user_domain)}",
                "",
                "if exists(.url.path) && !contains!(.url.path,\"cmd\"){",
                "    . |= parse_groks!( (.url.path), [",
                "        \"%{DATA}\\.%{WORD:url_extension}.*\",",
                "        \"%{GREEDYDATA}\"",
                "    ])",
                "} else {",
                "      . |= parse_groks!( (.url.path), [",
                "          \"%{GREEDYDATA}\\.%{WORD:url_extension}\",",
                "          \"%{GREEDYDATA}\"",
                "      ])",
                "}",
                "if exists(.url_extension) {.url.extension = del(.url_extension)}",
                "",
                "if exists(.user_agent.original)  && !is_nullish(.user_agent.original){",
                "  . |= parse_user_agent!(.user_agent.original)",
                "    if exists(.browser.family) {.user_agent.name = del(.browser.family)}",
                "    if exists(.browser.version) {.user_agent.version = del(.browser.version)}",
                "  del(.browser)",
                "}",
                "",
                "### Add event.created ###",
                "if exists(.event.created){ .cre= parse_timestamp!(del(.event.created),format:\"%F %T\")",
                "  .event.created=format_timestamp!(del(.cre), format: \"%FT%T%.3fZ\")",
                "}",
                "",
                "### Related fields ###",
                ".related.ip = []",
                ".related.user = []",
                ".related.hosts = []",
                "if exists(.destination.ip) && !is_nullish(.destination.ip) {",
                "  .related.ip = push(.related.ip, .destination.ip)",
                "}",
                "if exists(.source.ip) && !is_nullish(.source.ip) {",
                "  .related.ip = push(.related.ip, .source.ip)",
                "}",
                "if exists(.host.name) && !is_nullish(.host.name) {",
                "  .related.hosts = push(.related.hosts, .host.name)",
                "}",
                "if exists(.user.name) && !is_nullish(.user.name) {",
                "  .related.user = push(.related.user, .user.name)",
                "}",
                "if exists(.related.ip) {.related.ip = unique(.related.ip) }",
                "if exists(.related.user) {.related.user = unique(.related.user) }",
                "if exists(.related.hosts) {.related.hosts = unique(.related.hosts) }",
                "",
                "#### Remove empty, null fields ,fields that are not required ####",
                ". = compact(., string: true, array: true, null: true)",
                ""
            ])
            
            return "\n".join(vrl_parts)
            
        except json.JSONDecodeError:
            return self._generate_fallback_vrl(raw_log)
    
    def _generate_syslog_vrl(self, raw_log: str) -> str:
        """Generate comprehensive VRL for syslog following proper structure"""
        vrl_parts = [
            "### Add Event UUID, Organization-ID, Sensor-ID",
            "if !exists(.uuid) { .uuid = uuid_v4() }",
            "if !exists(.organization.id) { .organization.id = get_env_var(\"ORG_CODE\") ?? \"d3b6842a\" }",
            "if !exists(.sensor.id) { .sensor.id = get_env_var(\"SENSOR_ID\") ?? \"GD_VR_S01\" }",
            "",
            ".observer.type = \"system\"",
            ".observer.vendor = \"unknown\"",
            ".observer.product = \"unknown\"",
            ".enrich.geoip = \"true\"",
            ".enrich.iana = \"true\"",
            ".log.schema = \"raw\"",
            ".log.format = \"syslog\"",
            "",
            "### Add \"event.original\" field",
            "if exists(.message) {",
            "    .event.original = del(.message)",
            "} else if !exists(.message) {",
            "    parsed = object(.); del(.); .event = {}",
            "    .event.original = encode_json(parsed)",
            "    .event_data = parsed",
            "}",
            "",
            "###### Parser start ############",
            ".relate.ip = []",
            ".related.hosts = []",
            ".related.user = []",
            "",
            "# Parse syslog message",
            "if exists(.event.original) {",
            "    parsed, err = parse_syslog(.event.original)",
            "    if err == null {",
            "        .log.syslog = object!(parsed)",
            "        ",
            "        # Map syslog fields to ECS",
            "        if exists(.log.syslog.hostname) {",
            "            .host.name = del(.log.syslog.hostname)",
            "            .observer.hostname = .host.name",
            "        }",
            "        ",
            "        if exists(.log.syslog.appname) {",
            "            .observer.product = del(.log.syslog.appname)",
            "        }",
            "        ",
            "        if exists(.log.syslog.severity) {",
            "            .event.severity = del(.log.syslog.severity)",
            "            .log.level = string!(.event.severity)",
            "        }",
            "        ",
            "        if exists(.log.syslog.facility) {",
            "            .log.syslog.facility = del(.log.syslog.facility)",
            "        }",
            "        ",
            "        if exists(.log.syslog.msg) {",
            "            .event.description = del(.log.syslog.msg)",
            "        }",
            "    }",
            "}",
            ""
        ]
        
        # Add specific parsing based on syslog content
        if 'cisco' in raw_log.lower():
            vrl_parts.extend([
                "# Cisco syslog detected",
                ".observer.vendor = \"cisco\"",
                ".observer.type = \"network\"",
                "",
                "# Parse Cisco-specific fields",
                "if match(.event.original, r\"%[A-Z]+-[0-9]+-[A-Z_]+\") {",
                "    facility_severity, err = parse_regex(.event.original, r\"%([A-Z]+)-([0-9]+)-([A-Z_]+)\")",
                "    if err == null {",
                "        .event.provider = facility_severity.1",
                "        .event.severity = to_int!(facility_severity.2)",
                "        .event.action = facility_severity.3",
                "        .log.level = string!(.event.severity)",
                "    }",
                "}",
                "",
                "# Parse IP addresses from Cisco logs",
                "if match(.event.original, r\"\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b\") {",
                "    ip_match, err = parse_regex(.event.original, r\"(\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b)\")",
                "    if err == null {",
                "        .source.ip = ip_match.1",
                "        .network.source.ip = .source.ip",
                "    }",
                "}",
                ""
            ])
        
        # Add ECS field initialization and processing
        vrl_parts.extend([
            ".event.kind = \"event\"",
            ".event.category = []",
            ".event.category = push(.event.category, \"system\")",
            "",
            "if exists(.source.ip) && !is_null(.source.ip) {",
            "  .event.category = push(.event.category, \"network\")",
            "  .event.type = [\"connection\"]",
            "}",
            "",
            "if exists(.user.name){",
            "  . |= parse_groks!( (.user.name), [",
            "      \"%{DATA:_tmp.user_leading_domain}\\\\\\%{DATA:user_name}@%{GREEDYDATA:user_domain}\",",
            "      \"%{DATA:user_name}@%{GREEDYDATA:user_domain}\",",
            "      \"%{DATA:user_domain}\\\\\\%{GREEDYDATA:user_name}\",",
            "      \"%{GREEDYDATA:user_name}\"",
            "    ])",
            "}",
            "if exists(.user_name) {.user.name = del(.user_name)}",
            "if exists(.user_domain) {.user.domain = del(.user_domain)}",
            "",
            "### Add event.created ###",
            "if exists(.event.created){ .cre= parse_timestamp!(del(.event.created),format:\"%F %T\")",
            "  .event.created=format_timestamp!(del(.cre), format: \"%FT%T%.3fZ\")",
            "}",
            "",
            "### Related fields ###",
            ".related.ip = []",
            ".related.user = []",
            ".related.hosts = []",
            "if exists(.destination.ip) && !is_nullish(.destination.ip) {",
            "  .related.ip = push(.related.ip, .destination.ip)",
            "}",
            "if exists(.source.ip) && !is_nullish(.source.ip) {",
            "  .related.ip = push(.related.ip, .source.ip)",
            "}",
            "if exists(.host.name) && !is_nullish(.host.name) {",
            "  .related.hosts = push(.related.hosts, .host.name)",
            "}",
            "if exists(.user.name) && !is_nullish(.user.name) {",
            "  .related.user = push(.related.user, .user.name)",
            "}",
            "if exists(.related.ip) {.related.ip = unique(.related.ip) }",
            "if exists(.related.user) {.related.user = unique(.related.user) }",
            "if exists(.related.hosts) {.related.hosts = unique(.related.hosts) }",
            "",
            "#### Remove empty, null fields ,fields that are not required ####",
            ". = compact(., string: true, array: true, null: true)",
            ""
        ])
        
        return "\n".join(vrl_parts)
    
    def _generate_cef_vrl(self, raw_log: str) -> str:
        """Generate comprehensive VRL for CEF logs"""
        return """
# ========================================
# CEF Parser - Comprehensive ECS Mapping
# ========================================

# Initialize event data and basic fields
.event_data = {}

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

# ========================================
# ECS Field Mapping and Normalization
# ========================================

# Set event kind and category
if !exists(.event.kind) { .event.kind = "event" }
if !exists(.event.category) { .event.category = ["security"] }

# Set observer information
if !exists(.observer.type) { .observer.type = "security" }
if !exists(.observer.vendor) { .observer.vendor = "unknown" }
if !exists(.observer.product) { .observer.product = "unknown" }

# Set log information
if !exists(.log.level) { .log.level = "info" }
if !exists(.log.format) { .log.format = "cef" }

# Set timestamp if not already set
if !exists(.event.created) { .event.created = now() }
if !exists(.@timestamp) { .@timestamp = .event.created }

# ========================================
# Final Cleanup and Optimization
# ========================================

# Remove empty fields and compact
. = compact(., string: true, array: true, object: true, null: true)

# Ensure event_data is properly structured
if !exists(.event_data) { .event_data = {} }
"""
    
    def _generate_clf_vrl(self, raw_log: str) -> str:
        """Generate comprehensive VRL for Common Log Format"""
        return """
# ========================================
# CLF Parser - Comprehensive ECS Mapping
# ========================================

# Initialize event data and basic fields
.event_data = {}

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

# ========================================
# ECS Field Mapping and Normalization
# ========================================

# Set event kind and category
if !exists(.event.kind) { .event.kind = "event" }
if !exists(.event.category) { .event.category = ["web"] }

# Set observer information
if !exists(.observer.type) { .observer.type = "web-server" }
if !exists(.observer.vendor) { .observer.vendor = "unknown" }
if !exists(.observer.product) { .observer.product = "unknown" }

# Set log information
if !exists(.log.level) { .log.level = "info" }
if !exists(.log.format) { .log.format = "clf" }

# Set timestamp if not already set
if !exists(.event.created) { .event.created = now() }
if !exists(.@timestamp) { .@timestamp = .event.created }

# ========================================
# Final Cleanup and Optimization
# ========================================

# Remove empty fields and compact
. = compact(., string: true, array: true, object: true, null: true)

# Ensure event_data is properly structured
if !exists(.event_data) { .event_data = {} }
"""
    
    def _generate_generic_vrl(self, raw_log: str) -> str:
        """Generate comprehensive VRL for unknown/generic logs"""
        return """
# ========================================
# Generic Log Parser - Comprehensive ECS Mapping
# ========================================

# Initialize event data and basic fields
.event_data = {}

# Basic message handling
if exists(.message) {
    .event.original = del(.message)
    .event_data.raw_message = .event.original
}

# Try to extract common patterns
if match(.event.original, r"\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}") {
    timestamp, err = parse_regex(.event.original, r"(\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}[^\\s]*)")
    if err == null {
        .event.created = parse_timestamp!(timestamp.1, format: "%Y-%m-%dT%H:%M:%S%.3fZ")
        .@timestamp = .event.created
    }
}

# Try to extract IP addresses
if match(.event.original, r"\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b") {
    ip_match, err = parse_regex(.event.original, r"(\\b\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\b)")
    if err == null {
        .source.ip = ip_match.1
        .network.source.ip = .source.ip
    }
}

# Try to extract key-value pairs
kvs, err = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
if err == null && is_object(kvs) {
    .event_data = merge(.event_data, kvs, deep: true)
}

# ========================================
# ECS Field Mapping and Normalization
# ========================================

# Set event kind and category
if !exists(.event.kind) { .event.kind = "event" }
if !exists(.event.category) { .event.category = ["unknown"] }

# Set observer information
if !exists(.observer.type) { .observer.type = "unknown" }
if !exists(.observer.vendor) { .observer.vendor = "unknown" }
if !exists(.observer.product) { .observer.product = "unknown" }

# Set log information
if !exists(.log.level) { .log.level = "info" }
if !exists(.log.format) { .log.format = "unknown" }

# Set timestamp if not already set
if !exists(.event.created) { .event.created = now() }
if !exists(.@timestamp) { .@timestamp = .event.created }

# ========================================
# Final Cleanup and Optimization
# ========================================

# Remove empty fields and compact
. = compact(., string: true, array: true, object: true, null: true)

# Ensure event_data is properly structured
if !exists(.event_data) { .event_data = {} }
"""
    
    def _generate_fallback_vrl(self, raw_log: str) -> str:
        """Generate minimal fallback VRL"""
        return """
# ========================================
# Fallback Parser - Basic ECS Mapping
# ========================================

# Initialize event data and basic fields
.event_data = {}

if exists(.message) {
    .event.original = del(.message)
}

# Set basic ECS fields
.event.kind = "event"
.event.category = ["unknown"]
.observer.type = "unknown"
.observer.vendor = "unknown"
.observer.product = "unknown"
.log.level = "info"
.log.format = "unknown"

# Set timestamp
.event.created = now()
.@timestamp = .event.created

# Final cleanup
. = compact(., string: true, array: true, object: true, null: true)
"""
    
    def _analyze_log_content(self, raw_log: str, log_format: str) -> Dict:
        """Analyze log content for additional insights"""
        analysis = {
            "format": log_format,
            "length": len(raw_log),
            "has_timestamp": bool(re.search(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', raw_log)),
            "has_ip": bool(re.search(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', raw_log)),
            "has_json": bool(re.search(r'[{}]', raw_log)),
            "vendors_detected": []
        }
        
        # Detect vendors
        vendors = {
            'cisco': ['cisco', 'wlc', 'asa', 'ios'],
            'checkpoint': ['checkpoint', 'cp-'],
            'fortinet': ['fortinet', 'fortigate'],
            'palo': ['palo', 'pan-']
        }
        
        for vendor, keywords in vendors.items():
            if any(keyword in raw_log.lower() for keyword in keywords):
                analysis["vendors_detected"].append(vendor)
        
        return analysis


# Test the dynamic generator
if __name__ == "__main__":
    generator = DynamicVRLGenerator()
    
    test_logs = [
        '{"time":"2025-09-10T12:34:56Z","level":"info","msg":"test","hostname":"wlc-01"}',
        '<34>1 2023-10-11T22:14:15.003Z cisco-wlc %APF-6-USER_NAME_CREATED: User created',
        'CEF:0|Cisco|ASA|1.0|100|worm successfully stopped|3|src=10.0.0.1',
        '127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET / HTTP/1.1" 200 1234'
    ]
    
    for log in test_logs:
        print(f"\n=== Testing: {log[:50]}... ===")
        result = generator.generate_vrl(log)
        print(f"Format: {result['log_format']}")
        print(f"Success: {result['success']}")
        print(f"VRL Length: {len(result['vrl_code'])}")
        print(f"Analysis: {result['analysis']}")
        print("---")
