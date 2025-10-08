#!/usr/bin/env python3
"""
Demo: Fixing Ollama to Generate Different Parsers for Different Logs
"""

def show_old_vs_new_approach():
    print('🔍 DEMO: Old vs New Ollama Approach')
    print('=' * 60)
    
    # Test logs
    logs = [
        {
            'name': 'IPA HTTPD Log',
            'content': '<190>1 2025-09-18T07:40:33.360853+00:00 ma1-ipa-master httpd-error - - - [Thu Sep 18 07:40:31.606853 2025] [wsgi:error] [pid 2707661:tid 2707884] [remote 10.10.6.173:60801] ipa: INFO: [jsonserver_session] dhan@BHERO.IO: batch(config_show(), whoami(), env(None), dns_is_enabled(), trustconfig_show(), domainlevel_get(), ca_is_enabled(), vaultconfig_show()): SUCCESS'
        },
        {
            'name': 'CEF Security Log',
            'content': 'CEF:0|CheckPoint|VPN-1|R80.10|Alert|CheckPoint|3|rt=Sep 18 2025 07:40:33 dst=192.168.1.100 src=10.10.6.173 spt=60801 dpt=443 proto=tcp act=drop'
        },
        {
            'name': 'JSON Application Log',
            'content': '{"timestamp":"2025-09-18T07:40:33.360853Z","level":"INFO","host":"firewall.example.com","service":"auth","user":"admin","message":"User authentication successful"}'
        }
    ]
    
    print('❌ OLD APPROACH (Same parser for everything):')
    print('=' * 50)
    old_parser = '''##################################################
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
. = compact(., string: true, array: true, object: true, null: true)'''
    
    print(old_parser)
    print()
    
    print('✅ NEW APPROACH (Custom parsers for each log):')
    print('=' * 50)
    
    for i, log in enumerate(logs, 1):
        print(f'{i}. {log["name"]}:')
        print(f'   Log: {log["content"][:80]}...')
        
        # Analyze the log
        analysis = analyze_log_structure(log["content"])
        print(f'   Analysis: {analysis.split(chr(10))[0]}...')
        
        # Show what the custom parser should look like
        if log["name"] == "IPA HTTPD Log":
            print('   Custom Parser: IPA-specific GROK patterns, HTTPD fields, user email extraction')
        elif log["name"] == "CEF Security Log":
            print('   Custom Parser: CEF-specific parsing, security fields, IP/port extraction')
        elif log["name"] == "JSON Application Log":
            print('   Custom Parser: JSON parsing, application fields, structured data extraction')
        
        print()
    
    print('🎯 KEY DIFFERENCES:')
    print('❌ OLD: Same generic parse_syslog() for everything')
    print('✅ NEW: Custom GROK patterns for each log structure')
    print('❌ OLD: Same field mappings for all logs')
    print('✅ NEW: Different field mappings based on log analysis')
    print('❌ OLD: Same ECS fields for all logs')
    print('✅ NEW: Different ECS fields based on log content')

def analyze_log_structure(log_content: str) -> str:
    """Simple log analysis"""
    import re
    
    analysis = []
    analysis.append(f"Length: {len(log_content)} chars")
    
    if log_content.startswith('<'):
        analysis.append("Type: Syslog")
    elif log_content.startswith('CEF:'):
        analysis.append("Type: CEF")
    elif log_content.startswith('{'):
        analysis.append("Type: JSON")
    
    # Look for IPs
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ips = re.findall(ip_pattern, log_content)
    if ips:
        analysis.append(f"IPs: {len(ips)}")
    
    # Look for emails
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, log_content)
    if emails:
        analysis.append(f"Emails: {len(emails)}")
    
    return ', '.join(analysis)

if __name__ == "__main__":
    show_old_vs_new_approach()

