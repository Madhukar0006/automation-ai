#!/usr/bin/env python3
"""
Compact CEF Parser - Optimized for Size and Performance
Only maps essential ECS fields, stores everything else in event_data
"""

def generate_compact_cef_parser() -> str:
    """Generate compact CEF parser with minimal size"""
    
    return '''##################################################
## Compact CEF Parser - Essential ECS Fields Only
## Optimized for size and performance
##################################################

### Parse CEF message
cef_parsed, cef_err = parse_cef(.message)
if cef_err != null {
    .error = cef_err
    .error_type = "cef_parse_failed"
} else {
    # Store original CEF data
    .event_data.original_cef = cef_parsed
    
    # Essential ECS mappings only
    if exists(cef_parsed.vendor) { .observer.vendor = del(cef_parsed.vendor) }
    if exists(cef_parsed.product) { .observer.product = del(cef_parsed.product) }
    if exists(cef_parsed.version) { .observer.version = del(cef_parsed.version) }
    if exists(cef_parsed.severity) { .event.severity, err = to_int(del(cef_parsed.severity)) }
    if exists(cef_parsed.event_name) { .event.action = del(cef_parsed.event_name) }
    
    # Parse extensions if present
    if exists(cef_parsed.extensions) {
        extensions = cef_parsed.extensions
        cef_extensions, ext_err = parse_key_value(extensions, key_value_delimiter: "=", field_delimiter: " ")
        
        if ext_err == null {
            # Store all extensions in event_data FIRST
            .event_data.cef_extensions = cef_extensions
            
            # Essential ECS mappings from extensions (map to ECS, keep in event_data)
            if exists(cef_extensions.src) { .source.ip = cef_extensions.src }
            if exists(cef_extensions.dst) { .destination.ip = cef_extensions.dst }
            if exists(cef_extensions.spt) { .source.port, err = to_int(cef_extensions.spt) }
            if exists(cef_extensions.dpt) { .destination.port, err = to_int(cef_extensions.dpt) }
            if exists(cef_extensions.proto) { 
                proto_str, err = to_string(cef_extensions.proto)
                .network.protocol = downcase(proto_str)
            }
            if exists(cef_extensions.suser) { .source.user.name = cef_extensions.suser }
            if exists(cef_extensions.duser) { .destination.user.name = cef_extensions.duser }
            if exists(cef_extensions.app) { .service.name = cef_extensions.app }
            if exists(cef_extensions.msg) { .message = cef_extensions.msg }
            
            # Rename non-essential fields in event_data
            if exists(cef_extensions.cs1Label) { .event_data.cs1_label = cef_extensions.cs1Label }
            if exists(cef_extensions.cs1) { .event_data.cs1_value = cef_extensions.cs1 }
            if exists(cef_extensions.cs2Label) { .event_data.cs2_label = cef_extensions.cs2Label }
            if exists(cef_extensions.cs2) { .event_data.cs2_value = cef_extensions.cs2 }
            if exists(cef_extensions.act) { .event_data.action = cef_extensions.act }
            if exists(cef_extensions.outcome) { .event_data.outcome = cef_extensions.outcome }
        }
    }
}

### Set defaults
.event.category = ["network"]
.event.type = ["info"]
.event.kind = "event"

### Related entities
.related.ip = []
.related.user = []
if exists(.source.ip) { .related.ip = push(.related.ip, .source.ip) }
if exists(.destination.ip) { .related.ip = push(.related.ip, .destination.ip) }
if exists(.source.user.name) { .related.user = push(.related.user, .source.user.name) }
if exists(.destination.user.name) { .related.user = push(.related.user, .destination.user.name) }
.related.ip = unique(flatten(.related.ip))
.related.user = unique(flatten(.related.user))

### Timestamp
if !exists(.@timestamp) { .@timestamp = now() }
.event.created = now()

### Compact final object
. = compact(., string: true, array: true, object: true, null: true)'''
