#!/usr/bin/env python3
"""
Optimized CEF Parser - RAG-Based Field Optimization
Based on RAG analysis: moves standard ECS fields out of event_data, keeps only CEF-specific fields
"""

def generate_optimized_cef_parser() -> str:
    """Generate optimized CEF parser with RAG-based field optimization"""
    return """
##################################################
## Optimized CEF Parser - RAG-Based Field Optimization
## Based on RAG analysis: moves standard ECS fields out of event_data
##################################################

### ECS observer defaults
if !exists(.observer.type) { .observer.type = "security" }
if !exists(.observer.vendor) { .observer.vendor = "cef" }
if !exists(.observer.product) { .observer.product = "cef" }

### ECS event base defaults
if !exists(.event.dataset) { .event.dataset = "cef.logs" }
.event.category = ["security"]
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse CEF message
##################################################
raw = to_string(.message) ?? to_string(.) ?? ""

# Parse CEF format
cef_parsed, cef_err = parse_grok(raw, "CEF:%{NUMBER:cef_version}|%{DATA:vendor}|%{DATA:product}|%{DATA:version}|%{DATA:signature_id}|%{DATA:event_name}|%{NUMBER:severity}|%{GREEDYDATA:extensions}")

##################################################
### Optimized Field Mapping - RAG-Based
##################################################
if cef_err == null && is_object(cef_parsed) {
    .event.dataset = "cef.logs"
    .observer.type = "security"
    
    # Initialize event_data with ONLY CEF-specific fields
    .event_data = {}
    
    # ===== CEF HEADER FIELDS (ECS Fields - NOT in event_data) =====
    if exists(cef_parsed.vendor) {
        .observer.vendor = del(cef_parsed.vendor)
    }
    if exists(cef_parsed.product) {
        .observer.product = del(cef_parsed.product)
    }
    if exists(cef_parsed.version) {
        .observer.version = del(cef_parsed.version)
    }
    if exists(cef_parsed.signature_id) {
        .event.code = to_int(del(cef_parsed.signature_id)) ?? null
    }
    if exists(cef_parsed.event_name) {
        .event.action = del(cef_parsed.event_name)
    }
    
    # CEF header fields that don't have proper ECS mappings are stored in event_data
    # (vendor, product, version, signature_id, event_name already mapped to proper ECS fields above using del())
    # ===== CEF SEVERITY MAPPING (ECS Fields - NOT in event_data) =====
    if exists(cef_parsed.severity) {
        sev = to_int(del(cef_parsed.severity)) ?? 0
        .event.severity = sev
        if sev >= 0 && sev <= 3 { .log.level = "low" }
        if sev >= 4 && sev <= 6 { .log.level = "medium" }
        if sev >= 7 && sev <= 8 { .log.level = "high" }
        if sev >= 9 { .log.level = "critical" }
    }
    
    # ===== CEF EXTENSIONS PROCESSING =====
    if exists(cef_parsed.extensions) {
        extensions = cef_parsed.extensions
        cef_extensions, ext_err = parse_key_value(extensions, key_value_delimiter: "=", field_delimiter: " ")
        
        if ext_err == null {
            # Store ALL CEF extensions in event_data (CEF-specific)
            .event_data.cef_extensions = cef_extensions
            
            # ===== STANDARD ECS MAPPINGS (Move from CEF extensions to ECS fields) =====
            if exists(cef_extensions.src) { 
                .source.ip = del(cef_extensions.src)
            }
            if exists(cef_extensions.dst) { 
                .destination.ip = del(cef_extensions.dst)
            }
            if exists(cef_extensions.spt) { 
                .source.port = to_int(del(cef_extensions.spt)) ?? null
            }
            if exists(cef_extensions.dpt) { 
                .destination.port = to_int(del(cef_extensions.dpt)) ?? null
            }
            if exists(cef_extensions.proto) { 
                .network.protocol = downcase(to_string(del(cef_extensions.proto)) ?? "")
            }
            if exists(cef_extensions.suser) { 
                .source.user.name = del(cef_extensions.suser)
            }
            if exists(cef_extensions.duser) { 
                .destination.user.name = del(cef_extensions.duser)
            }
            # Custom String mappings (cs1, cs2, etc.)
            if exists(cef_extensions.cs1) { 
                .user.name = cef_extensions.cs1
                .event_data.cs1_value = cef_extensions.cs1
            }
            if exists(cef_extensions.cs1Label) {
                .event_data.cs1_label = cef_extensions.cs1Label
            }
            if exists(cef_extensions.cs2) { 
                .event_data.cs2_value = cef_extensions.cs2
            }
            if exists(cef_extensions.cs2Label) {
                .event_data.cs2_label = cef_extensions.cs2Label
            }
            if exists(cef_extensions.cs3) { 
                .event_data.cs3_value = cef_extensions.cs3
            }
            if exists(cef_extensions.cs3Label) {
                .event_data.cs3_label = cef_extensions.cs3Label
            }
            if exists(cef_extensions.cs4) { 
                .event_data.cs4_value = cef_extensions.cs4
            }
            if exists(cef_extensions.cs4Label) {
                .event_data.cs4_label = cef_extensions.cs4Label
            }
            if exists(cef_extensions.cs5) { 
                .event_data.cs5_value = cef_extensions.cs5
            }
            if exists(cef_extensions.cs5Label) {
                .event_data.cs5_label = cef_extensions.cs5Label
            }
            if exists(cef_extensions.cs6) { 
                .event_data.cs6_value = cef_extensions.cs6
            }
            if exists(cef_extensions.cs6Label) {
                .event_data.cs6_label = cef_extensions.cs6Label
            }
            if exists(cef_extensions.act) { 
                .event.action = cef_extensions.act
                
            }
            if exists(cef_extensions.outcome) { 
                .event.outcome = downcase(to_string(del(cef_extensions.outcome)) ?? "")
                
            }
            if exists(cef_extensions.app) { 
                .service.name = del(cef_extensions.app)
                
            }
            if exists(cef_extensions.fname) { 
                .file.name = del(cef_extensions.fname)
                
            }
            if exists(cef_extensions.filePath) {
                .file.path = del(cef_extensions.filePath)
                
            }
            if exists(cef_extensions.fileHash) {
                .file.hash.sha256 = cef_extensions.fileHash
                .event_data.cef_extensions.fileHash = del(.event_data.cef_extensions.fileHash)
            }
            if exists(cef_extensions.fileType) {
                .file.type = cef_extensions.fileType
                .event_data.cef_extensions.fileType = del(.event_data.cef_extensions.fileType)
            }
            if exists(cef_extensions.fileSize) {
                .file.size = to_int(del(cef_extensions.fileSize)) ?? null
                
            }
            
            # Additional network fields (with priority handling - ECS only, no event_data storage)
            if exists(cef_extensions.requestUrl) {
                .url.full = del(cef_extensions.requestUrl)
            } else if exists(cef_extensions.request) {
                .url.full = del(cef_extensions.request)
            }
            if exists(cef_extensions.requestMethod) {
                .http.request.method = upcase(to_string(del(cef_extensions.requestMethod)) ?? "")
                
            }
            if exists(cef_extensions.requestClientApplication) {
                .user_agent.name = del(cef_extensions.requestClientApplication)
                
            }
            
            # Additional user fields (only new ECS mappings, not duplicates)
            if exists(cef_extensions.suid) {
                .source.user.id = del(cef_extensions.suid)
                
            }
            if exists(cef_extensions.duid) {
                .destination.user.id = del(cef_extensions.duid)
                
            }
            
            # Additional event fields
            if exists(cef_extensions.category) {
                .event.category = [downcase(to_string(cef_extensions.category) ?? "")]
            }
            if exists(cef_extensions.severity) {
                severity_num = to_int(cef_extensions.severity) ?? 0
                .event_data.cef_severity = severity_num
                if severity_num >= 8 { .log.level = "critical" }
                if severity_num >= 6 && severity_num < 8 { .log.level = "error" }
                if severity_num >= 4 && severity_num < 6 { .log.level = "warn" }
                if severity_num >= 2 && severity_num < 4 { .log.level = "info" }
                if severity_num < 2 { .log.level = "debug" }
            }
            
            # Additional host fields
            if exists(cef_extensions.shost) {
                .source.domain = del(cef_extensions.shost)
                
            }
            if exists(cef_extensions.dhost) {
                .destination.domain = del(cef_extensions.dhost)
                
            }
            if exists(cef_extensions.dvc) {
                .host.name = del(cef_extensions.dvc)
                
            }
            if exists(cef_extensions.dvcHost) {
                .host.name = del(cef_extensions.dvc)Host
                
            }
            
            # Additional application fields (only new ECS mappings, not duplicates)
            if exists(cef_extensions.applicationProtocol) {
                .network.protocol = downcase(to_string(del(cef_extensions.applicationProtocol)) ?? "")
                
            }
            if exists(cef_extensions.transportProtocol) {
                .network.transport = downcase(to_string(del(cef_extensions.transportProtocol)) ?? "")
                
            }
            if exists(cef_extensions.fsize) { 
                .file.size = to_int(del(cef_extensions.fsize)) ?? null
            }
            if exists(cef_extensions.msg) { 
                .message = cef_extensions.msg
            }
            
            # ===== CEF-SPECIFIC FIELDS (Keep in event_data - Not in RAG knowledge base) =====
            # CEF extension fields that are CEF-specific and not standard ECS
            if exists(cef_extensions.cs1Label) {
                .event_data.cs1_label = cef_extensions.cs1Label
                .event_data.cef_extensions.cs1Label = del(.event_data.cef_extensions.cs1Label)
            }
            if exists(cef_extensions.cs2Label) {
                .event_data.cs2_label = cef_extensions.cs2Label
                .event_data.cef_extensions.cs2Label = del(.event_data.cef_extensions.cs2Label)
            }
            if exists(cef_extensions.cs3) {
                .event_data.cs3 = cef_extensions.cs3
                .event_data.cef_extensions.cs3 = del(.event_data.cef_extensions.cs3)
            }
            if exists(cef_extensions.cs3Label) {
                .event_data.cs3_label = cef_extensions.cs3Label
                .event_data.cef_extensions.cs3Label = del(.event_data.cef_extensions.cs3Label)
            }
            if exists(cef_extensions.cs4) {
                .event_data.cs4 = cef_extensions.cs4
                .event_data.cef_extensions.cs4 = del(.event_data.cef_extensions.cs4)
            }
            if exists(cef_extensions.cs4Label) {
                .event_data.cs4_label = cef_extensions.cs4Label
                .event_data.cef_extensions.cs4Label = del(.event_data.cef_extensions.cs4Label)
            }
            if exists(cef_extensions.cs5) {
                .event_data.cs5 = cef_extensions.cs5
                .event_data.cef_extensions.cs5 = del(.event_data.cef_extensions.cs5)
            }
            if exists(cef_extensions.cs5Label) {
                .event_data.cs5_label = cef_extensions.cs5Label
                .event_data.cef_extensions.cs5Label = del(.event_data.cef_extensions.cs5Label)
            }
            if exists(cef_extensions.cs6) {
                .event_data.cs6 = cef_extensions.cs6
                .event_data.cef_extensions.cs6 = del(.event_data.cef_extensions.cs6)
            }
            if exists(cef_extensions.cs6Label) {
                .event_data.cs6_label = cef_extensions.cs6Label
                .event_data.cef_extensions.cs6Label = del(.event_data.cef_extensions.cs6Label)
            }
            
            # CEF-specific network fields
            if exists(cef_extensions.smac) {
                .event_data.smac = cef_extensions.smac
                .event_data.cef_extensions.smac = del(.event_data.cef_extensions.smac)
            }
            if exists(cef_extensions.dmac) {
                .event_data.dmac = cef_extensions.dmac
                .event_data.cef_extensions.dmac = del(.event_data.cef_extensions.dmac)
            }
            if exists(cef_extensions.shost) {
                .event_data.shost = cef_extensions.shost
                
            }
            if exists(cef_extensions.dhost) {
                .event_data.dhost = cef_extensions.dhost
                
            }
            
            # CEF-specific device fields
            if exists(cef_extensions.deviceExternalId) {
                .event_data.device_external_id = cef_extensions.deviceExternalId
                .event_data.cef_extensions.deviceExternalId = del(.event_data.cef_extensions.deviceExternalId)
            }
            if exists(cef_extensions.deviceFacility) {
                .event_data.device_facility = cef_extensions.deviceFacility
                .event_data.cef_extensions.deviceFacility = del(.event_data.cef_extensions.deviceFacility)
            }
            if exists(cef_extensions.deviceSeverity) {
                .event_data.device_severity = cef_extensions.deviceSeverity
                .event_data.cef_extensions.deviceSeverity = del(.event_data.cef_extensions.deviceSeverity)
            }
            if exists(cef_extensions.deviceDirection) {
                .event_data.device_direction = cef_extensions.deviceDirection
                .event_data.cef_extensions.deviceDirection = del(.event_data.cef_extensions.deviceDirection)
            }
            if exists(cef_extensions.deviceDnsDomain) {
                .event_data.device_dns_domain = cef_extensions.deviceDnsDomain
                .event_data.cef_extensions.deviceDnsDomain = del(.event_data.cef_extensions.deviceDnsDomain)
            }
            if exists(cef_extensions.deviceCustomString1) {
                .event_data.device_custom_string1 = cef_extensions.deviceCustomString1
                .event_data.cef_extensions.deviceCustomString1 = del(.event_data.cef_extensions.deviceCustomString1)
            }
            if exists(cef_extensions.deviceCustomString2) {
                .event_data.device_custom_string2 = cef_extensions.deviceCustomString2
                .event_data.cef_extensions.deviceCustomString2 = del(.event_data.cef_extensions.deviceCustomString2)
            }
            if exists(cef_extensions.deviceCustomString3) {
                .event_data.device_custom_string3 = cef_extensions.deviceCustomString3
                .event_data.cef_extensions.deviceCustomString3 = del(.event_data.cef_extensions.deviceCustomString3)
            }
            if exists(cef_extensions.deviceCustomString4) {
                .event_data.device_custom_string4 = cef_extensions.deviceCustomString4
                .event_data.cef_extensions.deviceCustomString4 = del(.event_data.cef_extensions.deviceCustomString4)
            }
            if exists(cef_extensions.deviceCustomString5) {
                .event_data.device_custom_string5 = cef_extensions.deviceCustomString5
                .event_data.cef_extensions.deviceCustomString5 = del(.event_data.cef_extensions.deviceCustomString5)
            }
            if exists(cef_extensions.deviceCustomString6) {
                .event_data.device_custom_string6 = cef_extensions.deviceCustomString6
                .event_data.cef_extensions.deviceCustomString6 = del(.event_data.cef_extensions.deviceCustomString6)
            }
            
            # CEF-specific file fields
            if exists(cef_extensions.fileType) {
                .event_data.file_type = cef_extensions.fileType
                .event_data.cef_extensions.fileType = del(.event_data.cef_extensions.fileType)
            }
            if exists(cef_extensions.filePermission) {
                .event_data.file_permission = cef_extensions.filePermission
                .event_data.cef_extensions.filePermission = del(.event_data.cef_extensions.filePermission)
            }
            if exists(cef_extensions.fileHash) {
                .event_data.file_hash = cef_extensions.fileHash
                .event_data.cef_extensions.fileHash = del(.event_data.cef_extensions.fileHash)
            }
            if exists(cef_extensions.fileHashMd5) {
                .event_data.file_hash_md5 = cef_extensions.fileHashMd5
                .event_data.cef_extensions.fileHashMd5 = del(.event_data.cef_extensions.fileHashMd5)
            }
            if exists(cef_extensions.fileHashSha1) {
                .event_data.file_hash_sha1 = cef_extensions.fileHashSha1
                .event_data.cef_extensions.fileHashSha1 = del(.event_data.cef_extensions.fileHashSha1)
            }
            if exists(cef_extensions.fileHashSha256) {
                .event_data.file_hash_sha256 = cef_extensions.fileHashSha256
                .event_data.cef_extensions.fileHashSha256 = del(.event_data.cef_extensions.fileHashSha256)
            }
            
            # CEF-specific application fields
            if exists(cef_extensions.request) {
                .event_data.request = cef_extensions.request
                .event_data.cef_extensions.request = del(.event_data.cef_extensions.request)
            }
            if exists(cef_extensions.requestClientApplication) {
                .event_data.request_client_application = cef_extensions.requestClientApplication
                
            }
            if exists(cef_extensions.requestContext) {
                .event_data.request_context = cef_extensions.requestContext
                .event_data.cef_extensions.requestContext = del(.event_data.cef_extensions.requestContext)
            }
            if exists(cef_extensions.requestCookies) {
                .event_data.request_cookies = cef_extensions.requestCookies
                .event_data.cef_extensions.requestCookies = del(.event_data.cef_extensions.requestCookies)
            }
            if exists(cef_extensions.requestMethod) {
                .event_data.request_method = cef_extensions.requestMethod
                
            }
            if exists(cef_extensions.requestUrl) {
                .event_data.request_url = cef_extensions.requestUrl
                .event_data.cef_extensions.requestUrl = del(.event_data.cef_extensions.requestUrl)
            }
            
            # CEF-specific network fields
            if exists(cef_extensions.bytesIn) {
                .event_data.bytes_in = cef_extensions.bytesIn
                .event_data.cef_extensions.bytesIn = del(.event_data.cef_extensions.bytesIn)
            }
            if exists(cef_extensions.bytesOut) {
                .event_data.bytes_out = cef_extensions.bytesOut
                .event_data.cef_extensions.bytesOut = del(.event_data.cef_extensions.bytesOut)
            }
            if exists(cef_extensions.packetsIn) {
                .event_data.packets_in = cef_extensions.packetsIn
                .event_data.cef_extensions.packetsIn = del(.event_data.cef_extensions.packetsIn)
            }
            if exists(cef_extensions.packetsOut) {
                .event_data.packets_out = cef_extensions.packetsOut
                .event_data.cef_extensions.packetsOut = del(.event_data.cef_extensions.packetsOut)
            }
            
            # CEF-specific time fields
            if exists(cef_extensions.start) {
                .event_data.start_time = cef_extensions.start
                .event_data.cef_extensions.start = del(.event_data.cef_extensions.start)
            }
            if exists(cef_extensions.end) {
                .event_data.end_time = cef_extensions.end
                .event_data.cef_extensions.end = del(.event_data.cef_extensions.end)
            }
            if exists(cef_extensions.rt) {
                .event_data.receipt_time = cef_extensions.rt
                .event_data.cef_extensions.rt = del(.event_data.cef_extensions.rt)
            }
            if exists(cef_extensions.flexString1) {
                .event_data.flex_string1 = cef_extensions.flexString1
                .event_data.cef_extensions.flexString1 = del(.event_data.cef_extensions.flexString1)
            }
            if exists(cef_extensions.flexString2) {
                .event_data.flex_string2 = cef_extensions.flexString2
                .event_data.cef_extensions.flexString2 = del(.event_data.cef_extensions.flexString2)
            }
            if exists(cef_extensions.flexDate1) {
                .event_data.flex_date1 = cef_extensions.flexDate1
                .event_data.cef_extensions.flexDate1 = del(.event_data.cef_extensions.flexDate1)
            }
            if exists(cef_extensions.flexDate2) {
                .event_data.flex_date2 = cef_extensions.flexDate2
                .event_data.cef_extensions.flexDate2 = del(.event_data.cef_extensions.flexDate2)
            }
            if exists(cef_extensions.flexNumber1) {
                .event_data.flex_number1 = cef_extensions.flexNumber1
                .event_data.cef_extensions.flexNumber1 = del(.event_data.cef_extensions.flexNumber1)
            }
            if exists(cef_extensions.flexNumber2) {
                .event_data.flex_number2 = cef_extensions.flexNumber2
                .event_data.cef_extensions.flexNumber2 = del(.event_data.cef_extensions.flexNumber2)
            }
        }
    }
}

##################################################
### Event categorization
##################################################
if exists(.event.action) {
    action = to_string(.event.action) ?? ""
    
    if contains(action, "login") || contains(action, "authentication") {
        .event.category = ["authentication"]
        .event.type = ["start"]
    }
    
    if contains(action, "network") || contains(action, "connection") {
        .event.category = ["network"]
        .event.type = ["connection"]
    }
    
    if contains(action, "file") || contains(action, "access") {
        .event.category = ["file"]
        .event.type = ["access"]
    }
    
    if contains(action, "malware") || contains(action, "virus") {
        .event.category = ["malware"]
        .event.type = ["info"]
    }
    
    if contains(action, "intrusion") || contains(action, "attack") {
        .event.category = ["intrusion_detection"]
        .event.type = ["info"]
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
if exists(.source.user.name) { .related.user = push(.related.user, .source.user.name) }
if exists(.destination.user.name) { .related.user = push(.related.user, .destination.user.name) }
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
