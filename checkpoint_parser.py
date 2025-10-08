#!/usr/bin/env python3
"""
CheckPoint-Specific Parser for CheckPoint Firewall Logs
Optimized for CheckPoint syslog format with proper field extraction
"""

def generate_checkpoint_parser() -> str:
    """Generate CheckPoint-specific parser for firewall logs"""
    return """
##################################################
## CheckPoint Parser - ECS Normalization
## Specialized for CheckPoint Firewall Logs
##################################################

### ECS observer defaults for CheckPoint
.observer.type = "ngfw"
.observer.vendor = "CheckPoint"
.observer.product = "SmartDefence/Firewall"

### ECS event defaults
.event.dataset = "checkpoint.logs"
.event.category = ["network", "security"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse CheckPoint Syslog Message
##################################################
raw_message = to_string(.message) ?? ""

# Parse CheckPoint syslog format with structured data
if contains(raw_message, "[flags:") && contains(raw_message, "origin:") {
    # Extract CheckPoint structured data from message content
    checkpoint_data, checkpoint_err = parse_key_value(raw_message, field_delimiter: " ", value_delimiter: ":")
    
    if checkpoint_err == null && is_object(checkpoint_data) {
        # Store raw CheckPoint data in event_data
        .event_data.checkpoint_raw = checkpoint_data
        
        ##################################################
        ### CheckPoint Header Fields
        ##################################################
        
        # Extract flags
        if exists(checkpoint_data.flags) {
            .event_data.checkpoint_flags = checkpoint_data.flags
        }
        
        # Extract interface direction
        if exists(checkpoint_data.ifdir) {
            .network.direction = checkpoint_data.ifdir
            .event_data.checkpoint_ifdir = checkpoint_data.ifdir
        }
        
        # Extract interface name
        if exists(checkpoint_data.ifname) {
            .network.interface.name = checkpoint_data.ifname
            .event_data.checkpoint_ifname = checkpoint_data.ifname
        }
        
        # Extract log UID
        if exists(checkpoint_data.loguid) {
            .event.id = checkpoint_data.loguid
            .event_data.checkpoint_loguid = checkpoint_data.loguid
        }
        
        # Extract origin IP (source)
        if exists(checkpoint_data.origin) {
            .source.ip = checkpoint_data.origin
            .source.address = checkpoint_data.origin
            .event_data.checkpoint_origin = checkpoint_data.origin
        }
        
        # Extract sequence number
        if exists(checkpoint_data.sequencenum) {
            .event_data.checkpoint_sequencenum = checkpoint_data.sequencenum
        }
        
        # Extract version
        if exists(checkpoint_data.version) {
            .event_data.checkpoint_version = checkpoint_data.version
        }
        
        # Extract product name
        if exists(checkpoint_data.product) {
            .observer.product = checkpoint_data.product
            .event_data.checkpoint_product = checkpoint_data.product
        }
        
        # Extract system message
        if exists(checkpoint_data.sys_message) {
            .message = checkpoint_data.sys_message
            .event_data.checkpoint_sys_message = checkpoint_data.sys_message
        }
        
        ##################################################
        ### CheckPoint Security Event Mapping
        ##################################################
        
        # Map to security events based on message content
        if exists(.message) {
            msg = to_string(.message) ?? ""
            
            # Anti-spoofing detection
            if contains(msg, "anti-spoofing") {
                .event.category = ["network", "security"]
                .event.type = ["info", "vulnerability"]
                .event.action = "anti_spoofing_warning"
                .log.level = "warn"
            }
            
            # Firewall rule actions
            if contains(msg, "blocked") || contains(msg, "denied") {
                .event.category = ["network", "security"]
                .event.type = ["denied"]
                .event.action = "firewall_block"
                .event.outcome = "failure"
                .log.level = "warn"
            }
            
            if contains(msg, "allowed") || contains(msg, "permitted") {
                .event.category = ["network", "security"]
                .event.type = ["allowed"]
                .event.action = "firewall_allow"
                .event.outcome = "success"
                .log.level = "info"
            }
            
            # Network security events
            if contains(msg, "intrusion") || contains(msg, "attack") {
                .event.category = ["intrusion_detection", "security"]
                .event.type = ["info", "alert"]
                .event.action = "intrusion_detection"
                .log.level = "error"
            }
            
            # VPN events
            if contains(msg, "vpn") || contains(msg, "tunnel") {
                .event.category = ["network", "authentication"]
                .event.type = ["connection"]
                .event.action = "vpn_connection"
                .network.protocol = "ipsec"
            }
            
            # Authentication events
            if contains(msg, "authentication") || contains(msg, "login") {
                .event.category = ["authentication"]
                .event.type = ["start"]
                .event.action = "user_login"
            }
        }
    }
}

##################################################
### Parse Standard Syslog Header
##################################################
# Parse the syslog header separately for standard fields
syslog_parsed, syslog_err = parse_syslog(raw_message)

if syslog_err == null && is_object(syslog_parsed) {
    # Map syslog header fields to ECS
    if exists(syslog_parsed.timestamp) {
        .@timestamp = syslog_parsed.timestamp
    }
    
    if exists(syslog_parsed.hostname) {
        .host.hostname = syslog_parsed.hostname
        .host.name = syslog_parsed.hostname
    }
    
    if exists(syslog_parsed.appname) {
        .service.name = syslog_parsed.appname
        .process.name = syslog_parsed.appname
    }
    
    if exists(syslog_parsed.procid) {
        .process.pid, err = to_int(syslog_parsed.procid)
    }
    
    if exists(syslog_parsed.severity) {
        .log.syslog.severity.code = to_int(syslog_parsed.severity) ?? 0
        .log.syslog.facility.code = to_int(syslog_parsed.facility) ?? 0
        
        # Map severity to log level
        sev = to_int(syslog_parsed.severity) ?? 0
        if sev <= 3 { .log.level = "error" }
        if sev == 4 { .log.level = "warn" }
        if sev >= 5 { .log.level = "info" }
    }
}

##################################################
### Network Protocol Detection
##################################################
if exists(.message) {
    msg = to_string(.message) ?? ""
    
    # Detect protocols from message
    if contains(msg, "TCP") {
        .network.protocol = "tcp"
        .network.transport = "tcp"
    }
    
    if contains(msg, "UDP") {
        .network.protocol = "udp"
        .network.transport = "udp"
    }
    
    if contains(msg, "ICMP") {
        .network.protocol = "icmp"
    }
    
    if contains(msg, "HTTP") {
        .network.application = "http"
        .http.request.method = "GET"
    }
    
    if contains(msg, "HTTPS") {
        .network.application = "https"
        .http.request.method = "GET"
    }
}

##################################################
### Related Entities
##################################################
.related.ip = []
.related.user = []
.related.hosts = []

if exists(.source.ip) { .related.ip = push(.related.ip, .source.ip) }
if exists(.destination.ip) { .related.ip = push(.related.ip, .destination.ip) }
if exists(.user.name) { .related.user = push(.related.user, .user.name) }
if exists(.host.hostname) { .related.hosts = push(.related.hosts, .host.hostname) }

.related.ip = unique(flatten(.related.ip))
.related.user = unique(flatten(.related.user))
.related.hosts = unique(flatten(.related.hosts))

##################################################
### Timestamps and Metadata
##################################################
if !exists(.@timestamp) { .@timestamp = now() }
if !exists(.event.created) { .event.created = now() }

.log.original = raw_message

##################################################
### Compact final object
##################################################
. = compact(., null: true)
"""
