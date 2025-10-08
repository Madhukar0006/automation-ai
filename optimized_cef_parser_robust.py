#!/usr/bin/env python3
"""
Robust CEF Parser - Manual CEF Parsing for Better Field Extraction
Manually parses CEF format to ensure all fields are extracted properly
"""

def generate_robust_cef_parser() -> str:
    """Generate robust CEF parser with manual parsing"""
    
    return '''##################################################
## Robust CEF Parser - Manual CEF Parsing
## Ensures all fields are extracted properly
##################################################

### Manual CEF parsing for better field extraction
raw_message = to_string(.message) ?? ""

# Check if it's a CEF message
if starts_with(raw_message, "CEF:") {
    # Split CEF message into parts
    cef_parts = split(raw_message, "|")
    
    if length(cef_parts) >= 7 {
        # CEF Header fields (move with del() - store in event_data first then move)
        .event_data.cef_vendor = cef_parts[1]
        .event_data.cef_product = cef_parts[2]
        .event_data.cef_version = cef_parts[3]
        .event_data.cef_signature_id = cef_parts[4]
        .event_data.cef_event_name = cef_parts[5]
        .event_data.cef_severity = cef_parts[6]
        
        # Move to ECS with del()
        .observer.vendor = del(.event_data.cef_vendor)
        .observer.product = del(.event_data.cef_product)
        .observer.version = del(.event_data.cef_version)
        .event.code = to_int(del(.event_data.cef_signature_id)) ?? null
        .event.action = del(.event_data.cef_event_name)
        .event.severity = to_int(del(.event_data.cef_severity)) ?? null
        
        # Store original CEF data
        .event_data.cef_header = {
            "vendor": cef_parts[1],
            "product": cef_parts[2],
            "version": cef_parts[3],
            "signature_id": cef_parts[4],
            "event_name": cef_parts[5],
            "severity": cef_parts[6]
        }
        
        # Parse CEF extensions if present
        if length(cef_parts) > 7 {
            extensions_string = cef_parts[7]
            
            # Parse key-value pairs from extensions
            cef_extensions, ext_err = parse_key_value(extensions_string, key_value_delimiter: "=", field_delimiter: " ")
            
            if ext_err == null {
                # Store all extensions in event_data
                .event_data.cef_extensions = cef_extensions
                
            # Essential ECS mappings from extensions (move with del())
            if exists(cef_extensions.src) { .source.ip = del(cef_extensions.src) }
            if exists(cef_extensions.dst) { .destination.ip = del(cef_extensions.dst) }
            if exists(cef_extensions.spt) { .source.port, err = to_int(del(cef_extensions.spt)) }
            if exists(cef_extensions.dpt) { .destination.port, err = to_int(del(cef_extensions.dpt)) }
            if exists(cef_extensions.proto) { 
                proto_str, err = to_string(del(cef_extensions.proto))
                .network.protocol = downcase(proto_str)
            }
            if exists(cef_extensions.suser) { .source.user.name = del(cef_extensions.suser) }
            if exists(cef_extensions.duser) { .destination.user.name = del(cef_extensions.duser) }
            if exists(cef_extensions.app) { .service.name = del(cef_extensions.app) }
            if exists(cef_extensions.msg) { .message = del(cef_extensions.msg) }
                
                # Rename non-essential fields in event_data
                if exists(cef_extensions.cs1Label) { .event_data.cs1_label = cef_extensions.cs1Label }
                if exists(cef_extensions.cs1) { .event_data.cs1_value = cef_extensions.cs1 }
                if exists(cef_extensions.cs2Label) { .event_data.cs2_label = cef_extensions.cs2Label }
                if exists(cef_extensions.cs2) { .event_data.cs2_value = cef_extensions.cs2 }
                if exists(cef_extensions.act) { .event_data.action = cef_extensions.act }
                if exists(cef_extensions.outcome) { .event_data.outcome = cef_extensions.outcome }
                
            # Additional useful fields (move with del())
            if exists(cef_extensions.fname) { .file.name = del(cef_extensions.fname) }
            if exists(cef_extensions.filePath) { .file.path = del(cef_extensions.filePath) }
            if exists(cef_extensions.fileSize) { .file.size, err = to_int(del(cef_extensions.fileSize)) }
            if exists(cef_extensions.requestMethod) { 
                method_str, err = to_string(del(cef_extensions.requestMethod))
                .http.request.method = upcase(method_str)
            }
            if exists(cef_extensions.requestUrl) { .url.full = del(cef_extensions.requestUrl) }
            }
        }
    }
} else {
    # Not a CEF message
    .error = "Not a CEF message"
    .error_type = "invalid_format"
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
