#!/usr/bin/env python3
"""
Simple and Accurate VRL Parser for IPA HTTPD Error Logs
"""

def create_simple_ipa_vrl():
    """Create a simple, accurate VRL parser for IPA HTTPD logs"""
    
    simple_vrl = """##################################################
## VRL Parser - IPA HTTPD Error Log
##################################################

### ECS defaults
if !exists(.observer.type) { .observer.type = "application" }
if !exists(.event.dataset) { .event.dataset = "ipa.httpd.error" }
.event.category = ["web", "authentication"]
.event.kind = "event"
.event.type = ["info"]

### Parse log message
raw = to_string(.message) ?? to_string(.) ?? ""

### Simple GROK pattern - focus on key fields only
pattern = "<%{POSINT:priority}>%{INT:version} %{TIMESTAMP_ISO8601:timestamp} %{HOSTNAME:hostname} %{WORD:appname} - - - \\[%{HTTPDATE:httpd_time}\\] \\[%{WORD:module}:%{WORD:level}\\] \\[pid %{INT:pid}:tid %{INT:tid}\\] \\[remote %{IP:remote_ip}:%{INT:remote_port}\\] %{WORD:service}: %{WORD:log_level}: \\[%{WORD:session}\\] %{EMAILADDRESS:user}: %{GREEDYDATA:message}"

parsed, err = parse_grok(raw, pattern)

### Error handling
if err != null {
  .error = "Failed to parse IPA HTTPD log"
  .event.outcome = "failure"
  .log.level = "error"
  . = compact(.)
  return
}

### Extract key fields with proper ECS mapping
### Timestamp (use syslog timestamp as primary)
if exists(parsed.timestamp) { .@timestamp = parse_timestamp(del(parsed.timestamp), "%Y-%m-%dT%H:%M:%S%.3f%z") ?? now() }

### Host information
if exists(parsed.hostname) { .host.name = del(parsed.hostname) }

### Service information
if exists(parsed.appname) { .service.name = del(parsed.appname) }
if exists(parsed.service) { .service.type = del(parsed.service) }

### Process information
if exists(parsed.pid) { .process.pid = to_int(del(parsed.pid)) ?? null }
if exists(parsed.tid) { .process.thread.id = to_int(del(parsed.tid)) ?? null }

### Network information (source of the request)
if exists(parsed.remote_ip) { .source.ip = del(parsed.remote_ip) }
if exists(parsed.remote_port) { .source.port = to_int(del(parsed.remote_port)) ?? null }

### User and authentication
if exists(parsed.user) { .user.email = del(parsed.user) }
if exists(parsed.session) { .session.id = del(parsed.session) }

### Log level and message
if exists(parsed.log_level) { .log.level = del(parsed.log_level) }
if exists(parsed.message) { .message = del(parsed.message) }

### Set event outcome based on log level
if exists(.log.level) {
  if .log.level == "ERROR" {
    .event.outcome = "failure"
  } else if .log.level == "INFO" {
    .event.outcome = "success"
  } else {
    .event.outcome = "unknown"
  }
}

### Final cleanup
. = compact(.)"""
    
    return simple_vrl

def create_manual_vrl():
    """Create a manual parsing approach for complex logs"""
    
    manual_vrl = """##################################################
## VRL Parser - IPA HTTPD Error Log (Manual Parsing)
##################################################

### ECS defaults
if !exists(.observer.type) { .observer.type = "application" }
if !exists(.event.dataset) { .event.dataset = "ipa.httpd.error" }
.event.category = ["web", "authentication"]
.event.kind = "event"
.event.type = ["info"]

### Parse log message
raw = to_string(.message) ?? to_string(.) ?? ""

### Manual parsing approach - more reliable for complex logs
### Extract syslog header
syslog_pattern = "<%{POSINT:priority}>%{INT:version} %{TIMESTAMP_ISO8601:timestamp} %{HOSTNAME:hostname} %{WORD:appname} - - - %{GREEDYDATA:httpd_log}"
syslog_parsed, syslog_err = parse_grok(raw, syslog_pattern)

if syslog_err != null {
  .error = "Failed to parse syslog header"
  .event.outcome = "failure"
  .log.level = "error"
  . = compact(.)
  return
}

### Extract HTTPD log part
httpd_pattern = "\\[%{HTTPDATE:httpd_time}\\] \\[%{WORD:module}:%{WORD:level}\\] \\[pid %{INT:pid}:tid %{INT:tid}\\] \\[remote %{IP:remote_ip}:%{INT:remote_port}\\] %{WORD:service}: %{WORD:log_level}: \\[%{WORD:session}\\] %{EMAILADDRESS:user}: %{GREEDYDATA:message}"
httpd_parsed, httpd_err = parse_grok(syslog_parsed.httpd_log, httpd_pattern)

if httpd_err != null {
  .error = "Failed to parse HTTPD log part"
  .event.outcome = "failure"
  .log.level = "error"
  . = compact(.)
  return
}

### Extract key fields with proper ECS mapping
### Timestamp (use syslog timestamp as primary)
if exists(syslog_parsed.timestamp) { .@timestamp = parse_timestamp(del(syslog_parsed.timestamp), "%Y-%m-%dT%H:%M:%S%.3f%z") ?? now() }

### Host information
if exists(syslog_parsed.hostname) { .host.name = del(syslog_parsed.hostname) }

### Service information
if exists(syslog_parsed.appname) { .service.name = del(syslog_parsed.appname) }
if exists(httpd_parsed.service) { .service.type = del(httpd_parsed.service) }

### Process information
if exists(httpd_parsed.pid) { .process.pid = to_int(del(httpd_parsed.pid)) ?? null }
if exists(httpd_parsed.tid) { .process.thread.id = to_int(del(httpd_parsed.tid)) ?? null }

### Network information (source of the request)
if exists(httpd_parsed.remote_ip) { .source.ip = del(httpd_parsed.remote_ip) }
if exists(httpd_parsed.remote_port) { .source.port = to_int(del(httpd_parsed.remote_port)) ?? null }

### User and authentication
if exists(httpd_parsed.user) { .user.email = del(httpd_parsed.user) }
if exists(httpd_parsed.session) { .session.id = del(httpd_parsed.session) }

### Log level and message
if exists(httpd_parsed.log_level) { .log.level = del(httpd_parsed.log_level) }
if exists(httpd_parsed.message) { .message = del(httpd_parsed.message) }

### Set event outcome based on log level
if exists(.log.level) {
  if .log.level == "ERROR" {
    .event.outcome = "failure"
  } else if .log.level == "INFO" {
    .event.outcome = "success"
  } else {
    .event.outcome = "unknown"
  }
}

### Final cleanup
. = compact(.)"""
    
    return manual_vrl

if __name__ == "__main__":
    print("🔧 Simple IPA VRL Parser")
    print("=" * 50)
    
    print("📝 Option 1: Simple Single GROK Pattern")
    print("-" * 30)
    simple_vrl = create_simple_ipa_vrl()
    print(simple_vrl[:500] + "...")
    
    print("\n📝 Option 2: Manual Two-Step Parsing")
    print("-" * 30)
    manual_vrl = create_manual_vrl()
    print(manual_vrl[:500] + "...")
    
    print("\n✅ Recommendations:")
    print("1. Try Option 1 first (simpler)")
    print("2. If that fails, use Option 2 (more reliable)")
    print("3. Both avoid the complex nested field issues")
    print("4. Both use proper ECS field mappings")

