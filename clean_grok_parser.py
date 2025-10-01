#!/usr/bin/env python3
"""
Clean GROK-Based VRL Parser Generator
Creates parsers without nested duplication or recursive processing
"""

def generate_clean_grok_syslog_vrl() -> str:
    """Generate clean GROK-based syslog parser without duplication"""
    return """
# Clean GROK-Based Syslog Parser - No Duplication, No Nesting
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
                    # Map syslog fields to ECS (single assignments only)
                    if exists(.parsed.timestamp) {
                        .@timestamp = .parsed.timestamp
                    }
                    if exists(.parsed.hostname) {
                        .host.name = .parsed.hostname
                    }
                    if exists(.parsed.program) {
                        .service.name = .parsed.program
                    }
                    if exists(.parsed.pid) {
                        .process.pid = .parsed.pid
                    }
                    if exists(.parsed.message) {
                        .message = .parsed.message
                    }
                    if exists(.parsed.facility) {
                        .event_data.facility = .parsed.facility
                    }
                    if exists(.parsed.severity) {
                        .event_data.severity = .parsed.severity
                    }
                }
            }
        }
    }
    
    # Use GROK patterns for message content parsing (no regex)
    if exists(.message) {
        .msg_content = string!(.message)
        
        # GROK pattern for IP addresses
        .ip_parsed, err = parse_grok(.msg_content, "%{IP:source_ip}")
        if err == null && exists(.ip_parsed.source_ip) {
            .source.ip = .ip_parsed.source_ip
        }
        
        # GROK pattern for port numbers
        .port_parsed, err = parse_grok(.msg_content, "port %{INT:dest_port}")
        if err == null && exists(.port_parsed.dest_port) {
            .destination.port, err = to_int(.port_parsed.dest_port)
        }
        
        # GROK pattern for usernames
        .user_parsed, err = parse_grok(.msg_content, "user %{USERNAME:username}")
        if err == null && exists(.user_parsed.username) {
            .user.name = .user_parsed.username
        }
        
        # GROK pattern for file paths
        .path_parsed, err = parse_grok(.msg_content, "%{UNIXPATH:file_path}")
        if err == null && exists(.path_parsed.file_path) {
            .file.path = .path_parsed.file_path
        }
        
        # GROK patterns for actions (single assignments)
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
        
        # GROK patterns for protocols (single assignments)
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
.log.original = .
.tags = ["parsed", "grok-based", "syslog"]

# Compact the output
. = compact(., string: true, array: true, object: true, null: true)
"""

def generate_clean_grok_json_vrl() -> str:
    """Generate clean GROK-based JSON parser without duplication"""
    return """
# Clean GROK-Based JSON Parser - No Duplication, No Nesting
.message = .

# Parse JSON using GROK patterns
if is_string(.) {
    .input_string = string!(.)
    
    if starts_with(.input_string, "{") {
        .parsed, err = parse_json(.input_string)
        if err == null {
            .event.dataset = "json.parsed"
            
            if is_object(.parsed) {
                # Map JSON fields to ECS (single assignments only)
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
                if exists(.parsed.level) {
                    .log.level = .parsed.level
                }
                if exists(.parsed.severity) {
                    .log.level = .parsed.severity
                }
                if exists(.parsed.priority) {
                    .log.level = .parsed.priority
                }
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
                if exists(.parsed.host) {
                    .host.name = .parsed.host
                }
                if exists(.parsed.hostname) {
                    .host.name = .parsed.hostname
                }
                if exists(.parsed.server) {
                    .host.name = .parsed.server
                }
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
                if exists(.parsed.pid) {
                    .process.pid, err = to_int(.parsed.pid)
                }
                if exists(.parsed.process_id) {
                    .process.pid, err = to_int(.parsed.process_id)
                }
                if exists(.parsed.user) {
                    .user.name = .parsed.user
                }
                if exists(.parsed.username) {
                    .user.name = .parsed.username
                }
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
                if exists(.parsed.error) {
                    .error.message = .parsed.error
                }
                if exists(.parsed.exception) {
                    .error.message = .parsed.exception
                }
                if exists(.parsed.action) {
                    .event.action = .parsed.action
                }
                if exists(.parsed.event) {
                    .event.action = .parsed.event
                }
                if exists(.parsed.operation) {
                    .event.action = .parsed.operation
                }
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
.log.original = .
.tags = ["json", "parsed", "grok-based"]

# Compact the output
. = compact(., string: true, array: true, object: true, null: true)
"""
