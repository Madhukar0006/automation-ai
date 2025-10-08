#!/usr/bin/env python3
"""
Cisco-Specific Parser for Cisco ASA, IOS, and Nexus Logs
Optimized for Cisco network device logs
"""

def generate_cisco_parser() -> str:
    """Generate Cisco-specific parser for ASA, IOS, and Nexus logs"""
    return """
##################################################
## Cisco Parser - ECS Normalization
## Specialized for Cisco ASA, IOS, Nexus Logs
##################################################

### ECS observer defaults for Cisco
.observer.type = "network"
.observer.vendor = "Cisco"

### ECS event defaults
.event.dataset = "cisco.logs"
.event.category = ["network", "security"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse Cisco Message
##################################################
raw_message = to_string(.message) ?? ""

# Detect Cisco device type and set appropriate product
if contains(raw_message, "%ASA-") {
    .observer.product = "ASA"
    .observer.type = "firewall"
} else if contains(raw_message, "%IOS-") {
    .observer.product = "IOS"
    .observer.type = "router"
} else if contains(raw_message, "%NEXUS-") {
    .observer.product = "Nexus"
    .observer.type = "switch"
} else {
    .observer.product = "Cisco"
    .observer.type = "network"
}

##################################################
### Parse Cisco Syslog Format
##################################################
# Cisco logs often have format: %ASA-6-302013: Built outbound TCP connection...
cisco_parsed, cisco_err = parse_grok(raw_message, "%{DATA:cisco_header} %{GREEDYDATA:cisco_message}")

if cisco_err == null && is_object(cisco_parsed) {
    .event_data.cisco_header = cisco_parsed.cisco_header
    .event_data.cisco_message = cisco_parsed.cisco_message
    
    # Parse Cisco header for severity and message ID
    header_parsed, header_err = parse_grok(cisco_parsed.cisco_header, "%{DATA:device}-%{INT:severity}-%{INT:message_id}")
    if header_err == null && is_object(header_parsed) {
        .log.syslog.severity.code = header_parsed.severity
        .event_data.cisco_message_id = header_parsed.message_id
        .event_data.cisco_device = header_parsed.device
        
        # Map Cisco severity to log level
        sev = to_int(header_parsed.severity) ?? 0
        if sev <= 2 { .log.level = "critical" }
        if sev == 3 { .log.level = "error" }
        if sev == 4 { .log.level = "warn" }
        if sev >= 5 { .log.level = "info" }
    }
}

##################################################
### Parse Cisco ASA Firewall Events
##################################################
if contains(raw_message, "%ASA-") && exists(cisco_parsed.cisco_message) {
    msg = to_string(cisco_parsed.cisco_message) ?? ""
    
    # Built connection events
    built_conn, built_err = parse_grok(msg, "Built %{WORD:direction} %{WORD:protocol} connection %{INT:connection_id} for %{DATA:interface}:%{IP:source_ip}\\(%{INT:source_port}\\) %{IP:destination_ip}\\(%{INT:destination_port}\\)")
    if built_err == null && is_object(built_conn) {
        .source.ip = built_conn.source_ip
        .source.port, err = to_int(built_conn.source_port)
        .destination.ip = built_conn.destination_ip
        .destination.port, err = to_int(built_conn.destination_port)
        .network.protocol = downcase(built_conn.protocol)
        .network.transport = downcase(built_conn.protocol)
        .event.action = "connection_built"
        .event.outcome = "success"
        .event.category = ["network"]
        .event.type = ["connection"]
    }
    
    # Denied connection events
    denied_conn, denied_err = parse_grok(msg, "Denied %{WORD:protocol} connection from %{IP:source_ip}/%{INT:source_port} to %{IP:destination_ip}/%{INT:destination_port}")
    if denied_err == null && is_object(denied_conn) {
        .source.ip = denied_conn.source_ip
        .source.port, err = to_int(denied_conn.source_port)
        .destination.ip = denied_conn.destination_ip
        .destination.port, err = to_int(denied_conn.destination_port)
        .network.protocol = downcase(denied_conn.protocol)
        .network.transport = downcase(denied_conn.protocol)
        .event.action = "connection_denied"
        .event.outcome = "failure"
        .event.category = ["network", "security"]
        .event.type = ["denied"]
    }
    
    # Authentication events
    auth_event, auth_err = parse_grok(msg, "User %{USERNAME:username} authenticated from %{IP:source_ip}")
    if auth_err == null && is_object(auth_event) {
        .user.name = auth_event.username
        .source.ip = auth_event.source_ip
        .event.action = "user_authentication"
        .event.category = ["authentication"]
        .event.type = ["start"]
        .event.outcome = "success"
    }
    
    # VPN events
    vpn_event, vpn_err = parse_grok(msg, "Group %{DATA:vpn_group} User %{USERNAME:username} IP %{IP:user_ip} %{WORD:vpn_action}")
    if vpn_err == null && is_object(vpn_event) {
        .user.name = vpn_event.username
        .client.ip = vpn_event.user_ip
        .event_data.cisco_vpn_group = vpn_event.vpn_group
        .event.action = vpn_event.vpn_action
        .event.category = ["authentication", "network"]
        .event.type = ["start"]
        .network.protocol = "ipsec"
    }
}

##################################################
### Parse Cisco IOS Router Events
##################################################
if contains(raw_message, "%IOS-") && exists(cisco_parsed.cisco_message) {
    msg = to_string(cisco_parsed.cisco_message) ?? ""
    
    # Interface up/down events
    interface_event, int_err = parse_grok(msg, "Interface %{DATA:interface_name}, changed state to %{WORD:interface_state}")
    if int_err == null && is_object(interface_event) {
        .network.interface.name = interface_event.interface_name
        .event_data.cisco_interface_state = interface_event.interface_state
        .event.action = "interface_state_change"
        .event.category = ["network"]
        .event.type = ["change"]
        
        if interface_event.interface_state == "up" {
            .event.outcome = "success"
        } else {
            .event.outcome = "failure"
        }
    }
    
    # OSPF neighbor events
    ospf_event, ospf_err = parse_grok(msg, "OSPF-5-ADJCHG: Process %{INT:ospf_process}, Nbr %{IP:neighbor_ip} on %{DATA:interface} from %{WORD:old_state} to %{WORD:new_state}")
    if ospf_err == null && is_object(ospf_event) {
        .source.ip = ospf_event.neighbor_ip
        .network.interface.name = ospf_event.interface
        .event_data.cisco_ospf_process = ospf_event.ospf_process
        .event_data.cisco_ospf_old_state = ospf_event.old_state
        .event_data.cisco_ospf_new_state = ospf_event.new_state
        .event.action = "ospf_neighbor_change"
        .event.category = ["network"]
        .event.type = ["change"]
        .network.protocol = "ospf"
    }
}

##################################################
### Parse Standard Syslog Header
##################################################
syslog_parsed, syslog_err = parse_syslog(raw_message)

if syslog_err == null && is_object(syslog_parsed) {
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
}

##################################################
### Related Entities
##################################################
.related.ip = []
.related.user = []
.related.hosts = []

if exists(.source.ip) { .related.ip = push(.related.ip, .source.ip) }
if exists(.destination.ip) { .related.ip = push(.related.ip, .destination.ip) }
if exists(.client.ip) { .related.ip = push(.related.ip, .client.ip) }
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
