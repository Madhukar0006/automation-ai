#!/usr/bin/env python3
"""
Compact Syslog Parser - Clean, efficient, and properly structured
No big gaps, correct GROK patterns, proper field renaming
"""

def generate_compact_syslog_parser() -> str:
    """Generate compact Syslog parser with proper GROK and field mapping"""
    return """
##################################################
## Compact Syslog Parser - Fixed All Issues
##################################################

raw_message = to_string(.message) ?? ""

# Parse Syslog format with correct GROK pattern for RFC 5424
if contains(raw_message, "<") && contains(raw_message, ">") {
    # Handle RFC 5424 format with ISO8601 timestamp
    syslog_parsed, syslog_err = parse_grok(raw_message, "<%{INT:priority}>%{INT:version} %{TIMESTAMP_ISO8601:timestamp} %{HOSTNAME:hostname} %{PROG:program} %{INT:pid} %{GREEDYDATA:content}")
    
    if syslog_err == null && is_object(syslog_parsed) {
        # Don't store entire parsed object - we'll extract fields individually
        
        # Extract priority components with proper integer math (move with del)
        priority_num = to_int(syslog_parsed.priority) ?? 0
        facility_code = floor(priority_num / 8)
        severity_code = priority_num - (facility_code * 8)
        del(syslog_parsed.priority)
        
        # Map priority to log level
        .log.syslog.facility.code = facility_code
        .log.syslog.severity.code = severity_code
        if severity_code <= 3 { .log.level = "error" }
        if severity_code == 4 { .log.level = "warn" }
        if severity_code >= 5 { .log.level = "info" }
        
        # Map timestamp (ISO8601 format) - move with del
        if exists(syslog_parsed.timestamp) {
            .@timestamp = syslog_parsed.timestamp
            del(syslog_parsed.timestamp)
        }
        
        # Map version to syslog (move with del)
        if exists(syslog_parsed.version) {
            .log.syslog.version = syslog_parsed.version
            del(syslog_parsed.version)
        }
        
        # Map hostname to ECS (move with del)
        if exists(syslog_parsed.hostname) {
            .host.hostname = syslog_parsed.hostname
            .host.name = .host.hostname
            del(syslog_parsed.hostname)
        }
        
        # Map PID to process (move with del)
        if exists(syslog_parsed.pid) {
            .process.pid, err = to_int(syslog_parsed.pid)
            del(syslog_parsed.pid)
        }
        
        # Map program to ECS with vendor detection (move with del)
        if exists(syslog_parsed.program) {
            program_name = syslog_parsed.program
            .service.name = program_name
            .process.name = program_name
            del(syslog_parsed.program)
            
            # Detect vendor based on program name
            if program_name == "sshd" {
                .observer.vendor = "OpenSSH"
                .observer.product = "OpenSSH Server"
                .observer.type = "security"
            } else if program_name == "firewall" || program_name == "iptables" {
                .observer.vendor = "Linux"
                .observer.product = "iptables"
                .observer.type = "security"
            } else if program_name == "apache" || program_name == "httpd" {
                .observer.vendor = "Apache"
                .observer.product = "Apache HTTP Server"
                .observer.type = "web"
            } else if program_name == "nginx" {
                .observer.vendor = "Nginx"
                .observer.product = "Nginx HTTP Server"
                .observer.type = "web"
            } else {
                .observer.vendor = "System"
                .observer.product = program_name
                .observer.type = "system"
            }
        }
        
        # Parse message content for additional fields
        if exists(syslog_parsed.content) {
            msg = to_string(syslog_parsed.content) ?? ""
            
            # SSH Authentication Success - Handle syslog format with dashes
            ssh_parsed, ssh_err = parse_grok(msg, "- - Accepted password for %{USERNAME:ssh_user} from %{IP:ssh_ip} port %{INT:ssh_port} %{WORD:ssh_version}")
            if ssh_err == null && exists(ssh_parsed.ssh_user) {
                .user.name = ssh_parsed.ssh_user
                .source.ip = ssh_parsed.ssh_ip
                .source.port, err = to_int(ssh_parsed.ssh_port)
                .network.protocol = "ssh"
                .network.application = "ssh"
                .event.category = ["authentication"]
                .event.type = ["start"]
                .event.outcome = "success"
                .event.action = "ssh_login"
                .event_data.ssh_version = ssh_parsed.ssh_version
            } else {
                # SSH Authentication Failure - Handle syslog format with dashes
                ssh_fail_parsed, ssh_fail_err = parse_grok(msg, "- - Failed password for %{USERNAME:ssh_user} from %{IP:ssh_ip} port %{INT:ssh_port}")
                if ssh_fail_err == null && exists(ssh_fail_parsed.ssh_user) {
                    .user.name = ssh_fail_parsed.ssh_user
                    .source.ip = ssh_fail_parsed.ssh_ip
                    .source.port, err = to_int(ssh_fail_parsed.ssh_port)
                    .network.protocol = "ssh"
                    .network.application = "ssh"
                    .event.category = ["authentication"]
                    .event.type = ["start"]
                    .event.outcome = "failure"
                    .event.action = "ssh_login_failed"
                }
            }
            
            # Network Connection - Single GROK pattern
            net_parsed, net_err = parse_grok(msg, "Connection from %{IP:source_ip} port %{INT:source_port}")
            if net_err == null && exists(net_parsed.source_ip) {
                .source.ip = net_parsed.source_ip
                .source.port, err = to_int(net_parsed.source_port)
                .event.category = ["network"]
                .event.type = ["connection"]
                .network.protocol = "tcp"
            }
            
            # HTTP Request - Single GROK pattern
            http_parsed, http_err = parse_grok(msg, "%{WORD:http_method} %{URIPATH:http_path} HTTP/%{NUMBER:http_version}")
            if http_err == null && exists(http_parsed.http_method) {
                method_str, err = to_string(http_parsed.http_method)
                .http.request.method = upcase(method_str)
                .url.path = http_parsed.http_path
                .http.version = http_parsed.http_version
                .event.category = ["web"]
                .event.type = ["access"]
                .network.protocol = "http"
            }
            
            # File Operation - Single GROK pattern
            file_parsed, file_err = parse_grok(msg, "file %{QUOTEDSTRING:file_path} %{WORD:file_action}")
            if file_err == null && exists(file_parsed.file_path) {
                .file.path = file_parsed.file_path
                .event.action = file_parsed.file_action
                .event.category = ["file"]
                .event.type = ["access"]
            }
            
            # Process Information - Single GROK pattern
            proc_parsed, proc_err = parse_grok(msg, "process %{WORD:process_name} pid %{INT:process_id}")
            if proc_err == null && exists(proc_parsed.process_name) {
                .process.name = proc_parsed.process_name
                .process.pid, err = to_int(proc_parsed.process_id)
            }
            
            # Set message content and store in event_data
            .message = syslog_parsed.content
            .event_data.syslog_content = syslog_parsed.content
        }
    }
}

# Set defaults only if not already set
if !exists(.event.category) { .event.category = ["network", "system"] }
if !exists(.event.type) { .event.type = ["info"] }
if !exists(.event.kind) { .event.kind = "event" }
if !exists(.observer.type) { .observer.type = "system" }
if !exists(.observer.vendor) { .observer.vendor = "syslog" }
if !exists(.observer.product) { .observer.product = "syslog" }

# Timestamp
if !exists(.@timestamp) { .@timestamp = now() }
if !exists(.event.created) { .event.created = now() }

# Light compact - only remove null values
. = compact(., null: true)
"""
