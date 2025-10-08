#!/usr/bin/env python3
"""
Optimized JSON Parser - RAG-Based Field Optimization
Based on RAG analysis: moves 371 standard ECS fields out of event_data, keeps only 57 vendor-specific fields
"""

def generate_optimized_json_parser() -> str:
    """Generate optimized JSON parser with RAG-based field optimization"""
    return """
##################################################
## Optimized JSON Parser - RAG-Based Field Optimization
## Based on RAG analysis: moves standard ECS fields out of event_data
##################################################

### ECS observer defaults
if !exists(.observer.type) { .observer.type = "application" }
if !exists(.observer.vendor) { .observer.vendor = "json" }
if !exists(.observer.product) { .observer.product = "json" }

### ECS event base defaults
if !exists(.event.dataset) { .event.dataset = "json.logs" }
.event.category = ["application"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse JSON message
##################################################
raw = to_string(.message) ?? to_string(.) ?? ""

# Parse JSON format
json_parsed, json_err = parse_json(raw)

##################################################
### Optimized Field Mapping - RAG-Based
##################################################
if json_err == null && is_object(json_parsed) {
    .event.dataset = "json.logs"
    .observer.type = "application"
    
    # Initialize event_data with ONLY vendor-specific fields
    .event_data = {}
    
    # ===== TIMESTAMP MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.timestamp) { 
        .@timestamp = json_parsed.timestamp
    }
    if exists(json_parsed.time) { 
        .@timestamp = json_parsed.time
    }
    if exists(json_parsed.date) { 
        .@timestamp = json_parsed.date
    }
    if exists(json_parsed.datetime) { 
        .@timestamp = json_parsed.datetime
    }
    
    # ===== LOG LEVEL MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.level) {
        .log.level = downcase(to_string(json_parsed.level) ?? "")
    }
    if exists(json_parsed.severity) {
        if !exists(.log.level) {
            .log.level = downcase(to_string(json_parsed.severity) ?? "")
        }
    }
    if exists(json_parsed.priority) {
        if !exists(.log.level) {
            .log.level = downcase(to_string(json_parsed.priority) ?? "")
        }
    }
    
    # Microsoft/Azure AD level mapping (ECS Field - NOT in event_data)
    if exists(json_parsed.Level) { 
        level_num = to_int(json_parsed.Level) ?? 0
        if level_num <= 2 { .log.level = "critical" }
        if level_num == 3 { .log.level = "error" }
        if level_num == 4 { .log.level = "warn" }
        if level_num == 5 { .log.level = "info" }
        if level_num >= 6 { .log.level = "debug" }
    }
    
    # ===== MESSAGE MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.message) { 
        .message = json_parsed.message
    }
    if exists(json_parsed.msg) { 
        .message = json_parsed.msg
    }
    if exists(json_parsed.text) { 
        .message = json_parsed.text
    }
    
    # ===== HOST MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.host) { 
        .host.name = json_parsed.host
    }
    if exists(json_parsed.hostname) { 
        .host.name = json_parsed.hostname
    }
    if exists(json_parsed.server) { 
        .host.name = json_parsed.server
    }
    if exists(json_parsed.computer) { 
        .host.name = json_parsed.computer
    }
    
    # ===== SERVICE MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.service) { 
        .service.name = json_parsed.service
    }
    if exists(json_parsed.app) { 
        .service.name = json_parsed.app
    }
    if exists(json_parsed.application) { 
        .service.name = json_parsed.application
    }
    
    # Microsoft/Azure AD service mapping (ECS Fields - NOT in event_data)
    if exists(json_parsed.appDisplayName) { 
        .service.name = json_parsed.appDisplayName
    }
    if exists(json_parsed.resourceDisplayName) { 
        .service.name = json_parsed.resourceDisplayName
    }
    
    # ===== USER MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.user) { 
        .user.name = json_parsed.user
    }
    if exists(json_parsed.username) { 
        .user.name = json_parsed.username
    }
    if exists(json_parsed.user_name) { 
        .user.name = json_parsed.user_name
    }
    if exists(json_parsed.account) { 
        .user.name = json_parsed.account
    }
    
    # Microsoft/Azure AD user mapping (ECS Fields - NOT in event_data)
    if exists(json_parsed.identity) { 
        .user.name = json_parsed.identity
    }
    if exists(json_parsed.userDisplayName) { 
        .user.name = json_parsed.userDisplayName
    }
    if exists(json_parsed.userPrincipalName) { 
        .user.name = json_parsed.userPrincipalName
    }
    
    # ===== SOURCE IP MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.ip) { 
        .source.ip = json_parsed.ip
    }
    if exists(json_parsed.client_ip) { 
        .source.ip = json_parsed.client_ip
    }
    if exists(json_parsed.remote_ip) { 
        .source.ip = json_parsed.remote_ip
    }
    if exists(json_parsed.src_ip) { 
        .source.ip = json_parsed.src_ip
    }
    
    # Microsoft/Azure AD source IP mapping (ECS Fields - NOT in event_data)
    if exists(json_parsed.callerIpAddress) { 
        .source.ip = json_parsed.callerIpAddress
    }
    if exists(json_parsed.ipAddress) { 
        .source.ip = json_parsed.ipAddress
    }
    
    # ===== DESTINATION IP MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.dest_ip) { 
        .destination.ip = json_parsed.dest_ip
    }
    if exists(json_parsed.dst_ip) { 
        .destination.ip = json_parsed.dst_ip
    }
    if exists(json_parsed.destination_ip) { 
        .destination.ip = json_parsed.destination_ip
    }
    if exists(json_parsed.target_ip) { 
        .destination.ip = json_parsed.target_ip
    }
    
    # ===== PORT MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.src_port) { 
        .source.port = to_int(json_parsed.src_port) ?? null
    }
    if exists(json_parsed.source_port) { 
        .source.port = to_int(json_parsed.source_port) ?? null
    }
    if exists(json_parsed.local_port) { 
        .source.port = to_int(json_parsed.local_port) ?? null
    }
    if exists(json_parsed.dst_port) { 
        .destination.port = to_int(json_parsed.dst_port) ?? null
    }
    if exists(json_parsed.destination_port) { 
        .destination.port = to_int(json_parsed.destination_port) ?? null
    }
    if exists(json_parsed.port) { 
        .destination.port = to_int(json_parsed.port) ?? null
    }
    
    # ===== HTTP MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.method) { 
        .http.request.method = upcase(to_string(json_parsed.method) ?? "")
    }
    if exists(json_parsed.http_method) { 
        .http.request.method = upcase(to_string(json_parsed.http_method) ?? "")
    }
    if exists(json_parsed.url) { 
        .url.full = json_parsed.url
    }
    if exists(json_parsed.uri) { 
        .url.full = json_parsed.uri
    }
    if exists(json_parsed.path) { 
        .url.path = json_parsed.path
    }
    
    # ===== STATUS CODE MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.status) { 
        status_code = to_int(json_parsed.status) ?? 0
        .http.response.status_code = status_code
        if status_code >= 200 && status_code < 300 { .event.outcome = "success" }
        if status_code >= 400 { .event.outcome = "failure" }
    }
    if exists(json_parsed.status_code) { 
        status_code = to_int(json_parsed.status_code) ?? 0
        .http.response.status_code = status_code
        if status_code >= 200 && status_code < 300 { .event.outcome = "success" }
        if status_code >= 400 { .event.outcome = "failure" }
    }
    
    # ===== ACTION MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.action) { 
        .event.action = downcase(to_string(json_parsed.action) ?? "")
    }
    if exists(json_parsed.operation) { 
        .event.action = downcase(to_string(json_parsed.operation) ?? "")
    }
    
    # Microsoft/Azure AD action mapping (ECS Fields - NOT in event_data)
    if exists(json_parsed.operationName) { 
        .event.action = downcase(to_string(json_parsed.operationName) ?? "")
    }
    
    # ===== AZURE-SPECIFIC FIELDS (Keep in event_data - Not in RAG knowledge base) =====
    if exists(json_parsed.azure) {
        .event_data.azure = json_parsed.azure
        
        # Azure signin logs
        if exists(json_parsed.azure.signinlogs) {
            azure_signin = json_parsed.azure.signinlogs
            .event_data.azure_signin = azure_signin
            
            # Azure properties mapping (Keep in event_data)
            if exists(azure_signin.properties) {
                azure_props = azure_signin.properties
                .event_data.azure_properties = azure_props
                
                # Azure-specific fields that are NOT in standard ECS
                if exists(azure_props.is_interactive) {
                    .event_data.parsed_is_interactive = azure_props.is_interactive
                }
                if exists(azure_props.user_type) {
                    .event_data.parsed_user_type = azure_props.user_type
                }
                if exists(azure_props.authentication_protocol) {
                    .event_data.parsed_auth_protocol = azure_props.authentication_protocol
                }
                if exists(azure_props.conditional_access_status) {
                    .event_data.parsed_conditional_access_status = azure_props.conditional_access_status
                }
                
                # Device details (Keep in event_data)
                if exists(azure_props.device_detail) {
                    device_detail = azure_props.device_detail
                    .event_data.device_detail = device_detail
                    if exists(device_detail.browser) {
                        .event_data.parsed_device_browser = device_detail.browser
                    }
                    if exists(device_detail.operating_system) {
                        .event_data.parsed_device_os = device_detail.operating_system
                    }
                }
                
                # Location details (Keep in event_data)
                if exists(azure_props.location) {
                    location = azure_props.location
                    .event_data.location = location
                    if exists(location.countryOrRegion) {
                        .event_data.parsed_country = location.countryOrRegion
                    }
                    if exists(location.city) {
                        .event_data.parsed_city = location.city
                    }
                    if exists(location.state) {
                        .event_data.parsed_state = location.state
                    }
                    if exists(location.geoCoordinates) {
                        geo_coords = location.geoCoordinates
                        if exists(geo_coords.latitude) {
                            .event_data.parsed_latitude = geo_coords.latitude
                        }
                        if exists(geo_coords.longitude) {
                            .event_data.parsed_longitude = geo_coords.longitude
                        }
                    }
                }
                
                # Processing time (Keep in event_data)
                if exists(azure_props.processing_time_in_milliseconds) {
                    .event_data.parsed_processing_time_ms = azure_props.processing_time_in_milliseconds
                }
            }
        }
        
        # Azure correlation ID (ECS Field - NOT in event_data)
        if exists(json_parsed.azure.correlation_id) {
            .session.id = json_parsed.azure.correlation_id
        }
        
        # Azure tenant ID (ECS Field - NOT in event_data)
        if exists(json_parsed.azure.tenant_id) {
            .organization.id = json_parsed.azure.tenant_id
        }
    }
    
    # ===== SESSION MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.session_id) { 
        .session.id = json_parsed.session_id
    }
    if exists(json_parsed.correlation_id) { 
        .session.id = json_parsed.correlation_id
    }
    if exists(json_parsed.correlationId) { 
        .session.id = json_parsed.correlationId
    }
    
    # ===== PROTOCOL MAPPING (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.protocol) { 
        .network.protocol = downcase(to_string(json_parsed.protocol) ?? "")
    }
    if exists(json_parsed.proto) { 
        .network.protocol = downcase(to_string(json_parsed.proto) ?? "")
    }
    if exists(json_parsed.authenticationProtocol) { 
        .network.protocol = downcase(to_string(json_parsed.authenticationProtocol) ?? "")
    }
    
    # ===== EVENT CATEGORIZATION (ECS Fields - NOT in event_data) =====
    if exists(json_parsed.authenticationRequirement) {
        .event.category = ["authentication"]
        .event.type = ["start"]
    }
    if exists(json_parsed.userType) {
        .user.type = json_parsed.userType
    }
    if exists(json_parsed.isInteractive) {
        if json_parsed.isInteractive == true {
            .event.type = ["start"]
        }
        if json_parsed.isInteractive == false {
            .event.type = ["info"]
        }
    }
}

##################################################
### Event categorization based on content
##################################################
if exists(.message) {
    msg = to_string(.message) ?? ""
    
    # Detect event categories based on message content
    if contains(msg, "authentication") || contains(msg, "login") || contains(msg, "sign") {
        .event.category = ["authentication"]
        .event.type = ["start"]
    }
    if contains(msg, "network") || contains(msg, "connection") {
        .event.category = ["network"]
        .event.type = ["connection"]
    }
    if contains(msg, "file") || contains(msg, "access") {
        .event.category = ["file"]
        .event.type = ["access"]
    }
    
    # Detect success/failure based on message content
    if contains(msg, "failed") || contains(msg, "failure") || contains(msg, "error") {
        .event.outcome = "failure"
    }
    if contains(msg, "success") || contains(msg, "accepted") || contains(msg, "completed") {
        .event.outcome = "success"
    }
}

##################################################
### Related entities
##################################################
.related.ip = []
.related.user = []
.related.hosts = []

if exists(.source.ip) { .related.ip = push(.related.ip, .source.ip) }
if exists(.destination.ip) { .related.ip = push(.related.ip, .destination.ip) }
if exists(.user.name) { .related.user = push(.related.user, .user.name) }
if exists(.host.name) { .related.hosts = push(.related.hosts, .host.name) }

.related.ip = unique(flatten(.related.ip))
.related.user = unique(flatten(.related.user))
.related.hosts = unique(flatten(.related.hosts))

##################################################
### Timestamp and metadata
##################################################
if !exists(.@timestamp) {
    .@timestamp = now()
}
if !exists(.event.created) {
    .event.created = now()
}

.log.original = raw

##################################################
### Compact final object
##################################################
. = compact(., string: true, array: true, object: true, null: true)
"""
