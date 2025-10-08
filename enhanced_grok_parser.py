#!/usr/bin/env python3
"""
Enhanced GROK Parser with ECS Field Mapping
"""

def generate_enhanced_grok_syslog_vrl() -> str:
    """Generate enhanced GROK-based syslog parser"""
    return """
##################################################
## Syslog Parser - ECS Normalization
##################################################

### ECS observer defaults
if !exists(.observer.type) { .observer.type = "host" }
if !exists(.observer.vendor) { .observer.vendor = "syslog" }
if !exists(.observer.product) { .observer.product = "syslog" }

### ECS event base defaults
if !exists(.event.dataset) { .event.dataset = "syslog" }
.event.category = ["network"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse syslog message
##################################################
raw = to_string(.message) ?? to_string(.) ?? ""

# Parse syslog format
parsed, err = parse_syslog(raw)

if err == null && is_object(parsed) {
    # Extract timestamp
    if exists(parsed.timestamp) { .@timestamp = parsed.timestamp }
    
    # Extract hostname
    if exists(parsed.hostname) { 
        .host.hostname = parsed.hostname
        .host.name = parsed.hostname
    }
    
    # Extract application/program
    if exists(parsed.appname) { 
        .service.name = parsed.appname
        .process.name = parsed.appname
    }
    
    # Extract process ID
    if exists(parsed.procid) { 
        .process.pid = to_int(parsed.procid) ?? null
    }
    
    # Extract message content
    if exists(parsed.message) { 
        .message = parsed.message
    }
    
    # Extract severity
    if exists(parsed.severity) { 
        .log.syslog.severity.code = parsed.severity
        .log.level = parsed.severity
    }
    
    # Extract facility
    if exists(parsed.facility) { 
        .log.syslog.facility.code = parsed.facility
    }
}

.log.original = raw

##################################################
### Compact final object
##################################################
. = compact(., string: true, array: true, object: true, null: true)
"""


def generate_enhanced_grok_json_vrl() -> str:
    """Generate enhanced GROK-based JSON parser with ECS mapping + event_data"""
    # Import the enhanced parser
    from enhanced_json_parser_with_ecs import generate_enhanced_json_parser_with_ecs
    return generate_enhanced_json_parser_with_ecs()