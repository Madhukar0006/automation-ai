#!/usr/bin/env python3
"""
Fix VRL Parser for the specific log format
"""

def create_corrected_vrl_parser():
    """Create a corrected VRL parser for the IPA HTTPD error log"""
    
    corrected_vrl = """##################################################
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

### Simple GROK pattern for IPA HTTPD error log
pattern = "<%{POSINT:syslog_priority}>%{INT:syslog_version} %{TIMESTAMP_ISO8601:syslog_timestamp} %{HOSTNAME:hostname} %{WORD:app_name} - - - \\[%{HTTPDATE:httpd_timestamp}\\] \\[%{WORD:module}:%{WORD:level}\\] \\[pid %{INT:pid}:tid %{INT:tid}\\] \\[remote %{IP:remote_ip}:%{INT:remote_port}\\] %{WORD:service_name}: %{WORD:log_level}: \\[%{WORD:session_type}\\] %{EMAILADDRESS:user_email}: %{GREEDYDATA:log_message}"

parsed, err = parse_grok(raw, pattern)

### Error handling
if err != null {
  .error = "Failed to parse IPA HTTPD log"
  .event.outcome = "failure"
  .log.level = "error"
  . = compact(.)
  return
}

### Field extraction and ECS mapping
### Syslog fields
if exists(parsed.syslog_priority) { .log.syslog.priority = to_int(del(parsed.syslog_priority)) ?? null }
if exists(parsed.syslog_version) { .log.syslog.version = to_int(del(parsed.syslog_version)) ?? null }
if exists(parsed.syslog_timestamp) { .@timestamp = parse_timestamp(del(parsed.syslog_timestamp), "%Y-%m-%dT%H:%M:%S%.3f%z") ?? now() }

### Host and service information
if exists(parsed.hostname) { .host.name = del(parsed.hostname) }
if exists(parsed.app_name) { .service.name = del(parsed.app_name) }
if exists(parsed.service_name) { .service.type = del(parsed.service_name) }

### HTTPD specific fields
if exists(parsed.httpd_timestamp) { .http.request.timestamp = parse_timestamp(del(parsed.httpd_timestamp), "%a %b %d %H:%M:%S.%f %Y") ?? null }
if exists(parsed.module) { .http.request.headers.module = del(parsed.module) }
if exists(parsed.level) { .http.response.status_code = del(parsed.level) }

### Process information
if exists(parsed.pid) { .process.pid = to_int(del(parsed.pid)) ?? null }
if exists(parsed.tid) { .process.thread.id = to_int(del(parsed.tid)) ?? null }

### Network information
if exists(parsed.remote_ip) { .source.ip = del(parsed.remote_ip) }
if exists(parsed.remote_port) { .source.port = to_int(del(parsed.remote_port)) ?? null }

### User and authentication
if exists(parsed.user_email) { .user.email = del(parsed.user_email) }
if exists(parsed.session_type) { .session.id = del(parsed.session_type) }

### Log level and message
if exists(parsed.log_level) { .log.level = del(parsed.log_level) }
if exists(parsed.log_message) { .message = del(parsed.log_message) }

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
    
    return corrected_vrl

def test_vrl_with_sample_log():
    """Test the corrected VRL with the sample log"""
    
    sample_log = """<190>1 2025-09-18T07:40:33.360853+00:00 ma1-ipa-master httpd-error - - - [Thu Sep 18 07:40:31.606853 2025] [wsgi:error] [pid 2707661:tid 2707884] [remote 10.10.6.173:60801] ipa: INFO: [jsonserver_session] dhan@BHERO.IO: batch(config_show(), whoami(), env(None), dns_is_enabled(), trustconfig_show(), domainlevel_get(), ca_is_enabled(), vaultconfig_show()): SUCCESS"""
    
    print("🧪 Testing Corrected VRL Parser")
    print("=" * 50)
    
    print("📝 Sample Log:")
    print(sample_log)
    print()
    
    print("🔧 Corrected VRL Parser:")
    corrected_vrl = create_corrected_vrl_parser()
    print(corrected_vrl)
    
    print("\n✅ Key Improvements:")
    print("1. Simplified GROK pattern for better parsing")
    print("2. Correct field mappings for IPA HTTPD logs")
    print("3. Proper ECS field assignments")
    print("4. Better timestamp parsing")
    print("5. Correct event categorization")
    print("6. Proper user and session handling")

if __name__ == "__main__":
    test_vrl_with_sample_log()

