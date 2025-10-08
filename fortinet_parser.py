#!/usr/bin/env python3
"""
Fortinet-Specific Parser for FortiGate Firewall Logs
Optimized for FortiGate firewall and security logs
"""

def generate_fortinet_parser() -> str:
    """Generate Fortinet-specific parser for FortiGate logs"""
    return """
##################################################
## Fortinet Parser - ECS Normalization
## Specialized for FortiGate Firewall Logs
##################################################

### ECS observer defaults for Fortinet
.observer.type = "ngfw"
.observer.vendor = "Fortinet"
.observer.product = "FortiGate"

### ECS event defaults
.event.dataset = "fortinet.logs"
.event.category = ["network", "security"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse Fortinet Message
##################################################
raw_message = to_string(.message) ?? ""

# Parse FortiGate log format
fortinet_parsed, fortinet_err = parse_key_value(raw_message, field_delimiter: " ", value_delimiter: "=")

if fortinet_err == null && is_object(fortinet_parsed) {
    # Store raw Fortinet data
    .event_data.fortinet_raw = fortinet_parsed
    
    ##################################################
    ### Fortinet Header Fields
    ##################################################
    
    # Extract timestamp
    if exists(fortinet_parsed.date) {
        .event_data.fortinet_date = fortinet_parsed.date
    }
    
    if exists(fortinet_parsed.time) {
        .event_data.fortinet_time = fortinet_parsed.time
    }
    
    # Extract log level
    if exists(fortinet_parsed.level) {
        .log.level = downcase(fortinet_parsed.level)
        .event_data.fortinet_level = fortinet_parsed.level
    }
    
    # Extract log type
    if exists(fortinet_parsed.logtype) {
        .event_data.fortinet_logtype = fortinet_parsed.logtype
        
        # Map log type to event category
        logtype = downcase(fortinet_parsed.logtype)
        if logtype == "traffic" {
            .event.category = ["network"]
            .event.type = ["info"]
        } else if logtype == "event" {
            .event.category = ["security"]
            .event.type = ["info"]
        } else if logtype == "webfilter" {
            .event.category = ["web"]
            .event.type = ["info"]
        } else if logtype == "antivirus" {
            .event.category = ["malware"]
            .event.type = ["info"]
        }
    }
    
    # Extract subtype
    if exists(fortinet_parsed.subtype) {
        .event.action = fortinet_parsed.subtype
        .event_data.fortinet_subtype = fortinet_parsed.subtype
    }
    
    # Extract source IP
    if exists(fortinet_parsed.srcip) {
        .source.ip = fortinet_parsed.srcip
        .source.address = fortinet_parsed.srcip
        .event_data.fortinet_srcip = fortinet_parsed.srcip
    }
    
    # Extract destination IP
    if exists(fortinet_parsed.dstip) {
        .destination.ip = fortinet_parsed.dstip
        .destination.address = fortinet_parsed.dstip
        .event_data.fortinet_dstip = fortinet_parsed.dstip
    }
    
    # Extract source port
    if exists(fortinet_parsed.srcport) {
        .source.port, err = to_int(fortinet_parsed.srcport)
        .event_data.fortinet_srcport = fortinet_parsed.srcport
    }
    
    # Extract destination port
    if exists(fortinet_parsed.dstport) {
        .destination.port, err = to_int(fortinet_parsed.dstport)
        .event_data.fortinet_dstport = fortinet_parsed.dstport
    }
    
    # Extract protocol
    if exists(fortinet_parsed.proto) {
        .network.protocol = downcase(fortinet_parsed.proto)
        .network.transport = downcase(fortinet_parsed.proto)
        .event_data.fortinet_proto = fortinet_parsed.proto
    }
    
    # Extract action
    if exists(fortinet_parsed.action) {
        action = downcase(fortinet_parsed.action)
        .event_data.fortinet_action = fortinet_parsed.action
        
        if action == "accept" || action == "allow" {
            .event.outcome = "success"
        } else if action == "deny" || action == "drop" || action == "block" {
            .event.outcome = "failure"
        }
    }
    
    # Extract service
    if exists(fortinet_parsed.service) {
        .network.application = fortinet_parsed.service
        .event_data.fortinet_service = fortinet_parsed.service
    }
    
    # Extract user
    if exists(fortinet_parsed.user) {
        .user.name = fortinet_parsed.user
        .event_data.fortinet_user = fortinet_parsed.user
    }
    
    # Extract group
    if exists(fortinet_parsed.group) {
        .event_data.fortinet_group = fortinet_parsed.group
    }
    
    # Extract policy ID
    if exists(fortinet_parsed.policyid) {
        .event_data.fortinet_policyid = fortinet_parsed.policyid
    }
    
    # Extract policy name
    if exists(fortinet_parsed.policyname) {
        .event_data.fortinet_policyname = fortinet_parsed.policyname
    }
    
    # Extract interface information
    if exists(fortinet_parsed.srcintf) {
        .network.interface.name = fortinet_parsed.srcintf
        .event_data.fortinet_srcintf = fortinet_parsed.srcintf
    }
    
    if exists(fortinet_parsed.dstintf) {
        .event_data.fortinet_dstintf = fortinet_parsed.dstintf
    }
    
    # Extract application information
    if exists(fortinet_parsed.app) {
        .event_data.fortinet_app = fortinet_parsed.app
    }
    
    if exists(fortinet_parsed.appcat) {
        .event_data.fortinet_appcat = fortinet_parsed.appcat
    }
    
    # Extract URL information
    if exists(fortinet_parsed.url) {
        .url.full = fortinet_parsed.url
        .event_data.fortinet_url = fortinet_parsed.url
    }
    
    # Extract hostname
    if exists(fortinet_parsed.hostname) {
        .host.hostname = fortinet_parsed.hostname
        .host.name = fortinet_parsed.hostname
        .event_data.fortinet_hostname = fortinet_parsed.hostname
    }
    
    # Extract device name
    if exists(fortinet_parsed.devname) {
        .event_data.fortinet_devname = fortinet_parsed.devname
    }
    
    # Extract message
    if exists(fortinet_parsed.msg) {
        .message = fortinet_parsed.msg
        .event_data.fortinet_msg = fortinet_parsed.msg
    }
    
    # Extract session ID
    if exists(fortinet_parsed.sessionid) {
        .session.id = fortinet_parsed.sessionid
        .event_data.fortinet_sessionid = fortinet_parsed.sessionid
    }
    
    # Extract bytes information
    if exists(fortinet_parsed.sentbyte) {
        .network.bytes = to_int(fortinet_parsed.sentbyte) ?? 0
        .event_data.fortinet_sentbyte = fortinet_parsed.sentbyte
    }
    
    if exists(fortinet_parsed.rcvdbyte) {
        .event_data.fortinet_rcvdbyte = fortinet_parsed.rcvdbyte
    }
    
    # Extract packet information
    if exists(fortinet_parsed.sentpkt) {
        .event_data.fortinet_sentpkt = fortinet_parsed.sentpkt
    }
    
    if exists(fortinet_parsed.rcvdpkt) {
        .event_data.fortinet_rcvdpkt = fortinet_parsed.rcvdpkt
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
    
    if exists(syslog_parsed.severity) {
        .log.syslog.severity.code = to_int(syslog_parsed.severity) ?? 0
        .log.syslog.facility.code = to_int(syslog_parsed.facility) ?? 0
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
