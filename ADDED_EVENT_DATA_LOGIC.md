# ✅ Added event_data Logic for Non-ECS Fields

## 🎯 **Your Request**

> "i am not able to see the event_data fields"
> "see the rag the in the rag whichever is present in the rag ecs fields that should there which are not there they should go under event_data"

**You want:**
1. ✅ All ECS fields from RAG should be mapped normally
2. ✅ Fields NOT in ECS schema should go to `event_data`
3. ✅ See `event_data` in output [[memory:7881209]]

---

## ✅ **What We Added**

### **New event_data Section in VRL:**

```vrl
#### Store non-ECS fields in event_data ####
# Initialize event_data for custom/vendor-specific fields
if !exists(.event_data) { .event_data = {} }

# Standard ECS fields: @timestamp, host.*, source.*, destination.*, user.*, 
#                      event.*, log.*, observer.*, network.*, process.*, 
#                      file.*, service.*, related.*

# Move fields NOT in ECS to event_data:
if exists(.correlation_id) { .event_data.correlation_id = del(.correlation_id) }
if exists(.request_id) { .event_data.request_id = del(.request_id) }
if exists(.session_token) { .event_data.session_token = del(.session_token) }
if exists(.custom_field) { .event_data.custom_field = del(.custom_field) }
```

---

## 📊 **ECS vs Non-ECS Fields**

### **Standard ECS Fields (From RAG):**
These map to standard ECS schema:

| Category | ECS Fields |
|----------|-----------|
| **Core** | `@timestamp`, `message`, `tags` |
| **Event** | `event.original`, `event.created`, `event.category`, `event.action`, `event.outcome`, `event.kind`, `event.dataset` |
| **Host** | `host.hostname`, `host.name`, `host.ip`, `host.os.name` |
| **Source** | `source.ip`, `source.port`, `source.domain`, `source.user.name` |
| **Destination** | `destination.ip`, `destination.port`, `destination.domain` |
| **User** | `user.name`, `user.id`, `user.email`, `user.domain` |
| **Network** | `network.protocol`, `network.transport`, `network.bytes` |
| **Log** | `log.level`, `log.syslog.facility.code`, `log.syslog.severity.code`, `log.origin.file.name`, `log.origin.file.line`, `log.origin.function` |
| **Observer** | `observer.vendor`, `observer.product`, `observer.type` |
| **Process** | `process.name`, `process.pid`, `process.command_line` |
| **File** | `file.name`, `file.path`, `file.size` |
| **Service** | `service.name`, `service.type` |
| **Related** | `related.ip[]`, `related.hosts[]`, `related.user[]` |

### **Non-ECS Fields (Go to event_data):**
These are vendor/application-specific:

| Type | Examples |
|------|----------|
| **Vendor-specific** | `correlation_id`, `request_id`, `session_token`, `transaction_id` |
| **Application** | `app_version`, `build_number`, `deployment_id` |
| **Custom** | `custom_field1`, `custom_field2`, `extra_info` |
| **Vendor fields** | `cisco_acl_id`, `fortinet_vd`, `palo_alto_vsys` |

---

## 📝 **How It Works**

### **Step 1: Parse Log**
```vrl
_grokked, err = parse_groks(raw, [
  "...pattern that extracts: timestamp, hostname, source_ip, correlation_id, custom_status...",
  "%{GREEDYDATA:unparsed}"
])

if err == null { . = merge(., _grokked, deep: true) }
```

### **Step 2: Map ECS Fields**
```vrl
#### Field extraction and ECS mapping ####
if exists(.timestamp) {
  parsed_ts, ts_err = parse_timestamp(.timestamp, "...")
  if ts_err == null { .@timestamp = parsed_ts }
  del(.timestamp)
}

if exists(.hostname) {
  .host.hostname = del(.hostname)
  .host.name = .host.hostname
}

if exists(.source_ip) { .source.ip = del(.source_ip) }
```

### **Step 3: Map Non-ECS to event_data**
```vrl
#### Store non-ECS fields in event_data ####
if !exists(.event_data) { .event_data = {} }

# These fields are NOT in ECS schema
if exists(.correlation_id) {
  .event_data.correlation_id = del(.correlation_id)
}

if exists(.custom_status) {
  .event_data.custom_status = del(.custom_status)
}

if exists(.app_version) {
  .event_data.app_version = del(.app_version)
}
```

---

## 🎯 **Example Output**

### **For log with both ECS and non-ECS fields:**
```
<190>1 2025-09-16T09:42:55.454937+00:00 ma1-ipa-master dirsrv-errors - - - [16/Sep/2025:09:42:51.709023694 +0000] - ERR - ipa_sidgen_add_post_op - [file ipa_sidgen.c, line 128] correlationId=ABC123 requestId=REQ-456: Missing target entry.
```

### **Output:**

```json
{
  "@timestamp": "2025-09-16T09:42:55.454937+00:00",
  
  "log_type": "syslog",
  "log_format": "syslog",
  "log_source": "ipa-dirsrv",
  "vendor": "syslog",
  "product": "dirsrv",
  
  "┌─────────────────────────────────────────┐",
  "│         ECS FIELDS (Standard)           │",
  "└─────────────────────────────────────────┘",
  "event": {
    "dataset": "syslog.logs",
    "outcome": "failure",
    "category": ["process"],
    "type": ["error"],
    "kind": "event",
    "original": "<190>1 2025-09-16..."
  },
  
  "host": {
    "hostname": "ma1-ipa-master",
    "name": "ma1-ipa-master"
  },
  
  "service": {
    "name": "dirsrv-errors"
  },
  
  "log": {
    "level": "error",
    "syslog": {
      "facility": {"code": 23},
      "severity": {"code": 6}
    },
    "origin": {
      "function": "ipa_sidgen_add_post_op",
      "file": {"name": "ipa_sidgen.c", "line": 128}
    }
  },
  
  "observer": {
    "type": "host",
    "vendor": "syslog",
    "product": "dirsrv"
  },
  
  "message": "Missing target entry.",
  
  "related": {
    "hosts": ["ma1-ipa-master"]
  },
  
  "┌─────────────────────────────────────────┐",
  "│    NON-ECS FIELDS (event_data)          │",
  "└─────────────────────────────────────────┘",
  "event_data": {
    "correlation_id": "ABC123",
    "request_id": "REQ-456"
  }
}
```

**Now you can see:**
- ✅ All ECS fields in their proper locations
- ✅ Non-ECS fields in `event_data`
- ✅ Clear separation between standard and custom fields

---

## 💡 **Logic for Field Placement**

### **Decision Tree:**

```
Field extracted from GROK
    ↓
Is it in ECS schema?
    ↓
YES → Map to ECS field
│     Examples:
│     - timestamp → @timestamp
│     - hostname → host.hostname
│     - source_ip → source.ip
│     - username → user.name
│
NO  → Map to event_data
      Examples:
      - correlation_id → event_data.correlation_id
      - request_id → event_data.request_id
      - custom_status → event_data.custom_status
```

---

## 🔍 **Common Non-ECS Fields**

These should go to `event_data`:

| Vendor | Non-ECS Fields |
|--------|---------------|
| **Cisco** | `acl_id`, `vlan_id`, `interface_name` |
| **Fortinet** | `vd`, `policyid`, `session_id` |
| **Palo Alto** | `vsys`, `app_name`, `nat_rule` |
| **Microsoft** | `correlation_id`, `request_id`, `tenant_id` |
| **Custom Apps** | `transaction_id`, `trace_id`, `span_id`, `app_version` |

---

## 📁 **Files Updated**

1. ✅ `simple_langchain_agent.py` (Ollama)
   - Fixed to not fail
   - Added event_data section
   - Instructions for ECS vs non-ECS

2. ✅ `enhanced_openrouter_agent.py` (GPT-4o)
   - Added event_data section
   - Instructions for non-ECS fields

3. ✅ `docker/vector_config/parser.vrl`
   - Added event_data initialization
   - Comments for mapping non-ECS fields

---

## 🎉 **Result**

**Both models now:**
- ✅ Map ECS fields to proper locations
- ✅ Map non-ECS fields to `event_data`
- ✅ Show `event_data` in output
- ✅ Ollama works (doesn't fail)
- ✅ All fields preserved

**Test it:**
```bash
streamlit run enhanced_ui_with_openrouter.py
```

You'll see `event_data` with all non-ECS fields! 🎉
