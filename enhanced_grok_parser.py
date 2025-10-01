#!/usr/bin/env python3
"""
Enhanced GROK-Based VRL Parser Generator
Creates parsers that eliminate duplication and extract ALL fields properly
"""

def generate_enhanced_grok_syslog_vrl() -> str:
    """Generate enhanced GROK-based syslog parser with complete field extraction"""
    return """
# Enhanced GROK-Based Syslog Parser - Complete Field Extraction, No Duplication
.message = .

# Parse syslog using GROK patterns
if is_string(.) {
    .input_string = string!(.)
    
    # Try syslog parsing first
    if contains(.input_string, "<") {
        if contains(.input_string, ">") {
            .parsed, err = parse_syslog(.input_string)
            if err == null {
                .event.dataset = "syslog.parsed"
                
                if is_object(.parsed) {
                    # Extract ALL syslog fields to proper ECS fields (single assignments only)
                    
                    # Timestamp extraction
                    if exists(.parsed.timestamp) {
                        .@timestamp = .parsed.timestamp
                        .event.start = .parsed.timestamp
                    }
                    
                    # Hostname extraction - map to proper ECS fields
                    if exists(.parsed.hostname) {
                        .host.name = .parsed.hostname
                        .observer.hostname = .parsed.hostname
                        .log.origin.host.name = .parsed.hostname
                    }
                    
                    # Program/Service extraction - map to proper ECS fields
                    if exists(.parsed.program) {
                        .service.name = .parsed.program
                        .process.name = .parsed.program
                        .log.syslog.program = .parsed.program
                        .event.provider = .parsed.program
                    }
                    
                    # Process ID extraction - map to proper ECS fields
                    if exists(.parsed.pid) {
                        .process.pid = .parsed.pid
                        .log.syslog.pid = .parsed.pid
                    }
                    
                    # Message extraction
                    if exists(.parsed.message) {
                        .message = .parsed.message
                        .log.original = .parsed.message
                    }
                    
                    # Facility and Severity - store in event_data for non-ECS fields
                    if exists(.parsed.facility) {
                        .event_data.facility = .parsed.facility
                        .event_data.facility_name = to_string(.parsed.facility)
                    }
                    if exists(.parsed.severity) {
                        .event_data.severity = .parsed.severity
                        .event_data.severity_name = to_string(.parsed.severity)
                        .log.level = to_string(.parsed.severity)
                    }
                    
                    # Message ID if present
                    if exists(.parsed.msgid) {
                        .log.syslog.msgid = .parsed.msgid
                        .event.id = .parsed.msgid
                    }
                }
            }
        }
    }
    
    # Enhanced message content parsing - extract ALL key-value pairs
    if exists(.message) {
        .msg_content = string!(.message)
        
        # GROK patterns for IP addresses
        .ip_parsed, err = parse_grok(.msg_content, "%{IP:source_ip}")
        if err == null && exists(.ip_parsed.source_ip) {
            .source.ip = .ip_parsed.source_ip
        }
        
        # GROK patterns for port numbers
        .port_parsed, err = parse_grok(.msg_content, "port %{INT:dest_port}")
        if err == null && exists(.port_parsed.dest_port) {
            .destination.port, err = to_int(.port_parsed.dest_port)
        }
        
        # GROK patterns for usernames
        .user_parsed, err = parse_grok(.msg_content, "user %{USERNAME:username}")
        if err == null && exists(.user_parsed.username) {
            .user.name = .user_parsed.username
        }
        
        # GROK patterns for file paths
        .path_parsed, err = parse_grok(.msg_content, "%{UNIXPATH:file_path}")
        if err == null && exists(.path_parsed.file_path) {
            .file.path = .path_parsed.file_path
        }
        
        # Extract key-value pairs from message content (comprehensive extraction)
        # Pattern for conn=2942113, op=26, err=0 style
        .conn_parsed, err = parse_grok(.msg_content, "conn=%{INT:connection_id}")
        if err == null && exists(.conn_parsed.connection_id) {
            .event_data.connection_id = .conn_parsed.connection_id
        }
        
        .op_parsed, err = parse_grok(.msg_content, "op=%{INT:operation_id}")
        if err == null && exists(.op_parsed.operation_id) {
            .event_data.operation_id = .op_parsed.operation_id
        }
        
        .err_parsed, err = parse_grok(.msg_content, "err=%{INT:error_code}")
        if err == null && exists(.err_parsed.error_code) {
            .event_data.error_code = .err_parsed.error_code
            if .err_parsed.error_code == 0 {
                .event.outcome = "success"
            } else {
                .event.outcome = "failure"
                .error.code = .err_parsed.error_code
            }
        }
        
        # Extract LDAP specific fields
        if contains(.msg_content, "ldap") {
            .event_data.protocol = "ldap"
            .network.protocol = "ldap"
            .network.application = "ldap"
        }
        
        # Extract more key-value patterns
        .kv_patterns = [
            "uid=%{WORD:user_id}",
            "dn=%{DATA:distinguished_name}",
            "result=%{INT:result_code}",
            "time=%{INT:response_time}",
            "msg=%{DATA:error_message}",
            "code=%{INT:ldap_code}"
        ]
        
        for_each(.kv_patterns) -> |pattern| {
            .kv_parsed, err = parse_grok(.msg_content, pattern)
            if err == null {
                for_each(object!(.kv_parsed)) -> |key, value| {
                    .event_data[key] = value
                }
            }
        }
        
        # Action detection based on message content
        if contains(.msg_content, "accepted") {
            .event.action = "accepted"
            .event.outcome = "success"
        }
        if contains(.msg_content, "denied") {
            .event.action = "denied"
            .event.outcome = "failure"
        }
        if contains(.msg_content, "failed") {
            .event.action = "failed"
            .event.outcome = "failure"
        }
        if contains(.msg_content, "success") {
            .event.action = "success"
            .event.outcome = "success"
        }
        if contains(.msg_content, "login") {
            .event.action = "login"
            .event.category = ["authentication"]
        }
        if contains(.msg_content, "logout") {
            .event.action = "logout"
            .event.category = ["authentication"]
        }
        
        # Protocol detection
        if contains(.msg_content, "TCP") {
            .network.protocol = "tcp"
            .network.transport = "tcp"
        }
        if contains(.msg_content, "UDP") {
            .network.protocol = "udp"
            .network.transport = "udp"
        }
        if contains(.msg_content, "HTTP") {
            .network.protocol = "http"
            .network.application = "http"
        }
        if contains(.msg_content, "HTTPS") {
            .network.protocol = "https"
            .network.application = "https"
        }
        if contains(.msg_content, "SSH") {
            .network.protocol = "ssh"
            .network.application = "ssh"
        }
        if contains(.msg_content, "FTP") {
            .network.protocol = "ftp"
            .network.application = "ftp"
        }
        if contains(.msg_content, "LDAP") {
            .network.protocol = "ldap"
            .network.application = "ldap"
        }
    }
}

# Set defaults only if not already set (no duplicates)
if !exists(."event.kind") {
    .event.kind = "event"
}
if !exists(."event.category") {
    .event.category = ["network", "system"]
}
if !exists(."event.type") {
    .event.type = ["info"]
}
if !exists(."event.dataset") {
    .event.dataset = "syslog.logs"
}
if !exists(."event.created") {
    .event.created = now()
}
if !exists(."@timestamp") {
    .@timestamp = now()
}

# Add metadata (single assignments only)
.tags = ["parsed", "grok-based", "syslog", "enhanced"]

# Compact the output to remove empty fields
. = compact(., string: true, array: true, object: true, null: true)
"""

def generate_enhanced_grok_json_vrl() -> str:
    """Generate enhanced GROK-based JSON parser with complete field extraction"""
    return """
# Enhanced GROK-Based JSON Parser - Complete Field Extraction, No Duplication
.message = .

# Parse JSON using GROK patterns
if is_string(.) {
    .input_string = string!(.)
    
    if starts_with(.input_string, "{") {
        .parsed, err = parse_json(.input_string)
        if err == null {
            .event.dataset = "json.parsed"
            
            if is_object(.parsed) {
                # Extract ALL JSON fields to proper ECS fields (single assignments only)
                
                # Timestamp extraction
                if exists(.parsed.timestamp) {
                    .@timestamp = .parsed.timestamp
                }
                if exists(.parsed.time) {
                    .@timestamp = .parsed.time
                }
                if exists(.parsed.date) {
                    .@timestamp = .parsed.date
                }
                if exists(.parsed.datetime) {
                    .@timestamp = .parsed.datetime
                }
                
                # Log level extraction
                if exists(.parsed.level) {
                    .log.level = .parsed.level
                }
                if exists(.parsed.severity) {
                    .log.level = .parsed.severity
                }
                if exists(.parsed.priority) {
                    .log.level = .parsed.priority
                }
                
                # Message extraction
                if exists(.parsed.message) {
                    .message = .parsed.message
                }
                if exists(.parsed.msg) {
                    .message = .parsed.msg
                }
                if exists(.parsed.text) {
                    .message = .parsed.text
                }
                if exists(.parsed.description) {
                    .message = .parsed.description
                }
                
                # Host extraction
                if exists(.parsed.host) {
                    .host.name = .parsed.host
                }
                if exists(.parsed.hostname) {
                    .host.name = .parsed.hostname
                }
                if exists(.parsed.server) {
                    .host.name = .parsed.server
                }
                
                # Service extraction
                if exists(.parsed.service) {
                    .service.name = .parsed.service
                }
                if exists(.parsed.app) {
                    .service.name = .parsed.app
                }
                if exists(.parsed.application) {
                    .service.name = .parsed.application
                }
                if exists(.parsed.component) {
                    .service.name = .parsed.component
                }
                
                # Process extraction
                if exists(.parsed.pid) {
                    .process.pid, err = to_int(.parsed.pid)
                }
                if exists(.parsed.process_id) {
                    .process.pid, err = to_int(.parsed.process_id)
                }
                
                # User extraction
                if exists(.parsed.user) {
                    .user.name = .parsed.user
                }
                if exists(.parsed.username) {
                    .user.name = .parsed.username
                }
                
                # Network extraction
                if exists(.parsed.ip) {
                    .source.ip = .parsed.ip
                }
                if exists(.parsed.client_ip) {
                    .source.ip = .parsed.client_ip
                }
                if exists(.parsed.remote_ip) {
                    .source.ip = .parsed.remote_ip
                }
                if exists(.parsed.dest_ip) {
                    .destination.ip = .parsed.dest_ip
                }
                if exists(.parsed.port) {
                    .destination.port, err = to_int(.parsed.port)
                }
                
                # HTTP extraction
                if exists(.parsed.method) {
                    .http.request.method = .parsed.method
                }
                if exists(.parsed.url) {
                    .url, err = parse_url(.parsed.url)
                    .url.full = .parsed.url
                    .http.request.url = .parsed.url
                }
                if exists(.parsed.uri) {
                    .url, err = parse_url(.parsed.uri)
                    .url.full = .parsed.uri
                    .http.request.url = .parsed.uri
                }
                if exists(.parsed.path) {
                    .url.path = .parsed.path
                    .http.request.path = .parsed.path
                }
                if exists(.parsed.status) {
                    .http.response.status_code = .parsed.status
                    if .parsed.status >= 200 {
                        if .parsed.status < 300 {
                            .event.outcome = "success"
                        } else {
                            .event.outcome = "failure"
                        }
                    } else {
                        .event.outcome = "failure"
                    }
                }
                if exists(.parsed.status_code) {
                    .http.response.status_code = .parsed.status_code
                    if .parsed.status_code >= 200 {
                        if .parsed.status_code < 300 {
                            .event.outcome = "success"
                        } else {
                            .event.outcome = "failure"
                        }
                    } else {
                        .event.outcome = "failure"
                    }
                }
                
                # Error extraction
                if exists(.parsed.error) {
                    .error.message = .parsed.error
                }
                if exists(.parsed.exception) {
                    .error.message = .parsed.exception
                }
                
                # Action extraction
                if exists(.parsed.action) {
                    .event.action = .parsed.action
                }
                if exists(.parsed.event) {
                    .event.action = .parsed.event
                }
                if exists(.parsed.operation) {
                    .event.action = .parsed.operation
                }
                
                # File extraction
                if exists(.parsed.file) {
                    .file.name = .parsed.file
                }
                if exists(.parsed.filename) {
                    .file.name = .parsed.filename
                }
                if exists(.parsed.file_path) {
                    .file.path = .parsed.file_path
                }
                
                # Map remaining non-ECS fields to event_data (avoid for_each to prevent duplication)
                # Only add specific known non-ECS fields
                if exists(.parsed.custom) {
                    .event_data.custom = .parsed.custom
                }
                if exists(.parsed.metadata) {
                    .event_data.metadata = .parsed.metadata
                }
                if exists(.parsed.tags) {
                    .event_data.tags = .parsed.tags
                }
                if exists(.parsed.vendor) {
                    .event_data.vendor = .parsed.vendor
                }
                if exists(.parsed.product) {
                    .event_data.product = .parsed.product
                }
                if exists(.parsed.version) {
                    .event_data.version = .parsed.version
                }
                if exists(.parsed.session_id) {
                    .event_data.session_id = .parsed.session_id
                }
                if exists(.parsed.request_id) {
                    .event_data.request_id = .parsed.request_id
                }
                if exists(.parsed.correlation_id) {
                    .event_data.correlation_id = .parsed.correlation_id
                }
            }
        }
    }
}

# Set defaults (no duplicates)
if !exists(."event.kind") {
    .event.kind = "event"
}
if !exists(."event.category") {
    .event.category = ["application"]
}
if !exists(."event.type") {
    .event.type = ["info"]
}
if !exists(."event.dataset") {
    .event.dataset = "json.logs"
}
if !exists(."event.created") {
    .event.created = now()
}
if !exists(."@timestamp") {
    .@timestamp = now()
}

# Add metadata (single assignments only)
.tags = ["json", "parsed", "grok-based", "enhanced"]

# Compact the output to remove empty fields
. = compact(., string: true, array: true, object: true, null: true)
"""
