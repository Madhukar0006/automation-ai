from typing import Dict, Any
import re
import json
def _safe_json_loads(txt: str):
    """Parse LLM JSON output safely: strip fences, comments, trailing commas."""
    # strip code fences
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", txt.strip(), flags=re.S)
    # keep outermost object/array
    i, j = txt.find("{"), txt.rfind("}")
    ia, ja = txt.find("["), txt.rfind("]")
    if i != -1 and j != -1 and (ia == -1 or i < ia):
        txt = txt[i:j+1]
    elif ia != -1 and ja != -1:
        txt = txt[ia:ja+1]
    # remove comments
    txt = re.sub(r"//.*?$|/\*.*?\*/", "", txt, flags=re.M|re.S)
    # remove trailing commas
    txt = re.sub(r",\s*([}\]])", r"\1", txt)
    return json.loads(txt)

# Ensure we always defer to log_analyzer for log_format detection
try:
    import log_analyzer
except Exception:
    log_analyzer = None

from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain


def _ollama(model: str) -> Ollama:
    return Ollama(model=model)


def _infer_vendor_product_from_text(text: str) -> Dict[str, str]:
    """Lightweight heuristic mapping for vendor/product from raw text."""
    t = text.lower()
    vendor = None
    product = None
    if "cisco" in t:
        vendor = "Cisco"
        if any(k in t for k in ["asa", "%asa-"]):
            product = "ASA"
        elif any(k in t for k in ["dnac", "catalyst center", "dna center", "cisco dnac"]):
            product = "Catalyst Center"
        elif "ios" in t:
            product = "IOS"
    elif "fortinet" in t or "fortigate" in t:
        vendor = "Fortinet"
        product = "FortiGate"
    elif "palo alto" in t or "pan-os" in t or "panos" in t:
        vendor = "Palo Alto Networks"
        product = "PAN-OS"
    elif "azure" in t:
        vendor = "Microsoft"
        product = "Azure"
    return {"vendor": vendor, "product": product}


def _extract_syslog_program(line: str) -> str | None:
    """Extract syslog program/app name when present (RFC3164/RFC5424 variants)."""
    # RFC3164: <PRI>MMM DD HH:MM:SS HOST PROGRAM[pid]: message
    m = re.search(r"^<\d+>[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+\S+\s+([^:\[]+)(?:\[[^\]]+\])?:", line)
    if m:
        return m.group(1)
    # RFC5424: <PRI>VER TIMESTAMP HOST APPNAME PROCID MSGID [SD] MSG
    m = re.search(r"^<\d+>\d\s+\S+\s+\S+\s+(\S+)\s+\S+\s+\S+\s+", line)
    if m:
        return m.group(1)
    return None


def classify_log_lc(raw_log: str, dynamic_prefix: str = "") -> Dict[str, Any]:
    template = (
        (dynamic_prefix + "\n\n") if dynamic_prefix else ""
    ) + (
        "You are an expert log classifier. Return ONLY a JSON object with keys: "
        "log_type, log_format, log_source, product, vendor.\n"
        "Analyze this log and fill values. If unknown, use null.\n"
        "Log:\n{log}\n"
    )
    chain = LLMChain(llm=_ollama("llama3.2:latest"), prompt=PromptTemplate.from_template(template))
    out = chain.run({"log": raw_log}).strip()
    
    # Clean the output
    out = re.sub(r"^```(?:json)?", "", out).strip()
    out = re.sub(r"```$", "", out).strip()
    
    # Find JSON object
    brace_start = out.find("{")
    brace_end = out.rfind("}")
    
    result: Dict[str, Any]
    if brace_start >= 0 and brace_end > brace_start:
        json_str = out[brace_start:brace_end + 1]
        try:
            result = _safe_json_loads(json_str)
        except json.JSONDecodeError:
            result = {}
    else:
        result = {}

    # Normalize and enrich using deterministic detectors
    detected_format = None
    if log_analyzer is not None:
        try:
            detected_format = log_analyzer.identify_log_type(raw_log)
        except Exception:
            detected_format = None

    # Ensure keys exist
    for k in ["log_type", "log_format", "log_source", "product", "vendor"]:
        result.setdefault(k, None)

    # Force log_format from detector (lowercase), ensure 'json' stays lowercase
    if detected_format:
        result["log_format"] = detected_format.lower()

    # If syslog and missing log_source, extract program/app name
    if (result.get("log_format") == "syslog" or (raw_log.startswith("<") and ":" in raw_log)) and not result.get("log_source"):
        prog = _extract_syslog_program(raw_log)
        if prog:
            result["log_source"] = prog

    # Vendor/product heuristics (e.g., Cisco)
    vp = _infer_vendor_product_from_text(raw_log)
    if not result.get("vendor") and vp.get("vendor"):
        result["vendor"] = vp["vendor"]
    if not result.get("product") and vp.get("product"):
        result["product"] = vp["product"]
    # If vendor is Cisco but product still empty, default product to Cisco
    if (result.get("vendor") or "").lower() == "cisco" and not result.get("product"):
        result["product"] = "Cisco"

    # Final normalization: replace None with "unknown" to avoid NULL in UI
    normalized: Dict[str, Any] = {}
    for k, v in result.items():
        if v is None:
            normalized[k] = "unknown"
        elif isinstance(v, str):
            # Trim and keep json lowercase
            vv = v.strip()
            normalized[k] = vv.lower() if (k == "log_format") else vv
        else:
            normalized[k] = v

    return normalized


def generate_ecs_json_lc(context_text: str, raw_log: str, dynamic_prefix: str = "") -> Dict[str, Any]:
    """Generate ECS JSON with robust error handling and automated parsing"""
    try:
        # Use a more specific prompt for better JSON output
        template = (
            (dynamic_prefix + "\n\n") if dynamic_prefix else ""
        ) + (
            "You are an expert log parser. Convert this log to ECS JSON format.\n"
            "IMPORTANT: Return ONLY valid JSON. No explanations, no markdown, no code blocks.\n"
            "Required fields: @timestamp, event.original, event.category, message\n"
            "Context:\n{ctx}\n\nLog to parse:\n{log}\n\n"
            "Return only the JSON object:"
        )
        
        chain = LLMChain(llm=_ollama("llama3.2:latest"), prompt=PromptTemplate.from_template(template))
        out = chain.run({"ctx": context_text, "log": raw_log}).strip()
        
        # Automated JSON extraction and cleaning
        return _extract_and_clean_json(out, raw_log)
        
    except Exception as e:
        # Fallback to automated ECS generation
        return _generate_fallback_ecs(raw_log, str(e))


def _extract_and_clean_json(text: str, original_log: str) -> Dict[str, Any]:
    """Extract and clean JSON from LLM output with multiple fallback strategies"""
    import json
    import re
    from datetime import datetime
    
    # Strategy 1: Direct JSON parsing
    try:
        return _safe_json_loads(text)
    except:
        pass
    
    # Strategy 2: Remove markdown and code blocks
    cleaned = re.sub(r"^```(?:json)?", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()
    
    try:
        return _safe_json_loads(cleaned)
    except:
        pass
    
    # Strategy 3: Extract JSON object between braces
    brace_start = cleaned.find("{")
    brace_end = cleaned.rfind("}")
    
    if brace_start >= 0 and brace_end > brace_start:
        json_str = cleaned[brace_start:brace_end + 1]
        try:
            return _safe_json_loads(json_str)
        except:
            pass
    
    # Strategy 4: Fix common JSON issues
    try:
        # Fix common issues
        fixed_json = _fix_common_json_issues(cleaned)
        return _safe_json_loads(fixed_json)
    except:
        pass
    
    # Strategy 5: Generate structured ECS from log content
    return _generate_structured_ecs(original_log, text)


def _fix_common_json_issues(json_str: str) -> str:
    """Fix common JSON formatting issues"""
    import re
    
    # Remove trailing commas
    json_str = re.sub(r',\s*}', '}', json_str)
    json_str = re.sub(r',\s*]', ']', json_str)
    
    # Fix unquoted keys
    json_str = re.sub(r'(\w+):', r'"\1":', json_str)
    
    # Fix single quotes to double quotes
    json_str = json_str.replace("'", '"')
    
    # Remove comments
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    
    return json_str


def _generate_structured_ecs(original_log: str, llm_output: str) -> Dict[str, Any]:
    """Generate structured ECS JSON from log content"""
    from datetime import datetime
    import re
    
    # Extract timestamp if present
    timestamp = datetime.now().isoformat() + "Z"
    timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})', original_log)
    if timestamp_match:
        timestamp = timestamp_match.group(1).replace(' ', 'T') + 'Z'
    
    # Extract IP addresses
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ips = re.findall(ip_pattern, original_log)
    
    # Extract usernames (common patterns)
    user_pattern = r'(?:user|username|account)[\s:=]+([a-zA-Z0-9_-]+)'
    user_match = re.search(user_pattern, original_log, re.IGNORECASE)
    username = user_match.group(1) if user_match else None
    
    # Determine event category
    category = "unknown"
    if any(word in original_log.lower() for word in ['login', 'auth', 'password']):
        category = "authentication"
    elif any(word in original_log.lower() for word in ['connection', 'tcp', 'udp', 'network']):
        category = "network"
    elif any(word in original_log.lower() for word in ['error', 'failed', 'denied']):
        category = "error"
    
    # Build ECS structure
    ecs_json = {
        "@timestamp": timestamp,
        "event": {
            "original": original_log,
            "created": timestamp,
            "category": category
        },
        "message": original_log
    }
    
    # Add extracted fields
    if ips:
        if len(ips) >= 2:
            ecs_json["source"] = {"ip": ips[0]}
            ecs_json["destination"] = {"ip": ips[1]}
        else:
            ecs_json["source"] = {"ip": ips[0]}
    
    if username:
        ecs_json["user"] = {"name": username}
    
    # Add LLM insights if available
    if llm_output and len(llm_output) > 10:
        ecs_json["event"]["reason"] = f"LLM analysis: {llm_output[:200]}..."
    
    return ecs_json


def _generate_fallback_ecs(original_log: str, error_msg: str) -> Dict[str, Any]:
    """Generate fallback ECS JSON when all else fails"""
    from datetime import datetime
    
    return {
        "@timestamp": datetime.now().isoformat() + "Z",
        "event": {
            "original": original_log,
            "created": datetime.now().isoformat() + "Z",
            "category": "unknown",
            "reason": f"Automated parsing error: {error_msg}"
        },
        "message": original_log,
        "error": {
            "message": error_msg,
            "type": "parsing_error"
        }
    }


def generate_vrl_lc(context_text: str, raw_log: str, dynamic_prefix: str = "") -> str:
    """Generate VRL parser using perfect simple templates"""
    try:
        # Use simple agent with perfect VRL generation
        from simple_langchain_agent import SimpleLogParsingAgent
        from complete_rag_system import CompleteRAGSystem
        
        rag = CompleteRAGSystem()
        agent = SimpleLogParsingAgent(rag)
        result = agent.generate_vrl_parser(raw_log)
        
        if result["success"]:
            return result["vrl_code"]
        else:
            # Fallback to automated VRL generation
            return _generate_fallback_vrl(raw_log, result.get("error", "Unknown error"))
        
    except Exception as e:
        # Fallback to automated VRL generation
        return _generate_fallback_vrl(raw_log, str(e))


def _generate_vrl_from_template(log_profile: Dict[str, Any], raw_log: str, reference_vrl: str) -> str:
    """Generate VRL from template based on log profile and reference"""
    vendor = (log_profile.get("vendor") or "unknown").lower()
    product = (log_profile.get("product") or "unknown").lower()
    log_type = (log_profile.get("log_type") or "unknown").lower()
    
    # Determine event category based on log content
    category = "unknown"
    if any(word in raw_log.lower() for word in ['login', 'auth', 'password', 'user']):
        category = "authentication"
    elif any(word in raw_log.lower() for word in ['connection', 'tcp', 'udp', 'network', 'built']):
        category = "network"
    elif any(word in raw_log.lower() for word in ['error', 'failed', 'denied', 'blocked']):
        category = "error"
    elif any(word in raw_log.lower() for word in ['firewall', 'asa', 'fortinet', 'palo']):
        category = "security"
    
    # Generate clean VRL based on log type
    if log_type == "asa" or "cisco" in vendor:
        return _generate_cisco_asa_vrl(raw_log, category, vendor, product)
    elif "json" in log_type.lower() or raw_log.strip().startswith('{'):
        return _generate_json_vrl(raw_log, category, vendor, product)
    elif "syslog" in log_type or raw_log.startswith('<') or raw_log.startswith('%'):
        return _generate_syslog_vrl(raw_log, category, vendor, product)
    elif (("http" in log_type.lower() or "access" in log_type.lower()) if log_type else False) or ("apache" in product.lower() if product else False) or ("nginx" in product.lower() if product else False) or ("apache" in vendor.lower() if vendor else False) or ('GET' in raw_log and 'HTTP' in raw_log):
        return _generate_apache_vrl(raw_log, category, vendor, product)
    else:
        return _generate_generic_vrl(raw_log, category, vendor, product)

def _generate_apache_vrl(raw_log: str, category: str, vendor: str, product: str) -> str:
    """Generate VRL for Apache/Nginx access logs"""
    return f"""
.event.kind = "event"
.event.category = ["web"]
.observer.vendor = "{vendor}"
.observer.product = "{product}"
.observer.type = "web-server"
.event.dataset = "{vendor}.{product}"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Parse Apache access log format
if exists(.event.original) {{
  # Extract client IP
  if .event.original matches /^(\\d+\\.\\d+\\.\\d+\\.\\d+)/ {{
    .source.ip = $1
  }}
  
  # Extract timestamp
  if .event.original matches /\\[(\\d{2}\\/[A-Za-z]{3}\\/\\d{4}:\\d{2}:\\d{2}:\\d{2} [+-]\\d{4})\\]/ {{
    .@timestamp = parse_timestamp!($1, format: "%d/%b/%Y:%H:%M:%S %z")
  }}
  
  # Extract HTTP method
  if .event.original matches /"([A-Z]+) / {{
    .http.request.method = $1
  }}
  
  # Extract request URI
  if .event.original matches /"[A-Z]+ ([^ ]+) HTTP/ {{
    .url.original = $1
  }}
  
  # Extract HTTP version
  if .event.original matches /HTTP\\/(\\d\\.\\d)/ {{
    .http.version = $1
  }}
  
  # Extract status code
  if .event.original matches /" \\d+ (\\d{3}) / {{
    .http.response.status_code = to_int!($1)
  }}
  
  # Extract response size
  if .event.original matches /" \\d+ \\d{3} (\\d+) / {{
    .http.response.body.bytes = to_int!($1)
  }}
  
  # Extract referer
  if .event.original matches /" ([^"]+) " "([^"]+)"$/ {{
    .http.request.referrer = $1
    .user_agent.original = $2
  }}
  
  # Set event action and outcome
  .event.action = "http_request"
  .event.outcome = if .http.response.status_code >= 200 && .http.response.status_code < 300 {{ "success" }} else if .http.response.status_code >= 400 {{ "failure" }} else {{ "unknown" }}
}}

# HTTP-specific processing
if exists(.http.request.method) {{ .http.request.method = .http.request.method | upcase }}
if exists(.http.response.status_code) {{
  .http.response.status_class = if .http.response.status_code >= 200 && .http.response.status_code < 300 {{ "2xx" }} else if .http.response.status_code >= 300 && .http.response.status_code < 400 {{ "3xx" }} else if .http.response.status_code >= 400 && .http.response.status_code < 500 {{ "4xx" }} else if .http.response.status_code >= 500 {{ "5xx" }} else {{ "unknown" }}
}}

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""

def _generate_cisco_asa_vrl(raw_log: str, category: str, vendor: str, product: str) -> str:
    """Generate VRL for Cisco ASA logs"""
    return f"""
.event.kind = "event"
.event.category = ["{category}"]
.observer.vendor = "{vendor}"
.observer.product = "{product}"
.observer.type = "firewall"
.event.dataset = "{vendor}.{product}"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Parse Cisco ASA log format
if exists(.event.original) {{
  # Extract connection ID
  if .event.original matches /connection (\\d+)/ {{
    .event_data.connection_id = $1
  }}
  
  # Extract source IP
  if .event.original matches /outside:([\\d.]+)/ {{
    .source.ip = $1
  }}
  
  # Extract destination IP  
  if .event.original matches /inside:([\\d.]+)/ {{
    .destination.ip = $1
  }}
  
  # Extract ports
  if .event.original matches /outside:[\\d.]+\\/(\\d+)/ {{
    .source.port = to_int!($1)
  }}
  
  if .event.original matches /inside:[\\d.]+\\/(\\d+)/ {{
    .destination.port = to_int!($1)
  }}
  
  # Extract protocol
  if .event.original matches /(TCP|UDP) connection/ {{
    .network.protocol = $1
  }}
  
  # Set action
  if .event.original matches /Built outbound/ {{
    .event.action = "connection_established"
  }}
}}

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""

def _generate_json_vrl(raw_log: str, category: str, vendor: str, product: str) -> str:
    """Generate VRL for JSON logs"""
    return f"""
.event.kind = "event"
.event.category = ["{category}"]
.observer.vendor = "{vendor}"
.observer.product = "{product}"
.observer.type = "application"
.event.dataset = "{vendor}.{product}"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Parse JSON log
if exists(.event.original) {{
  parsed = parse_json(.event.original)
  if is_object(parsed) {{
    .event_data = merge(.event_data, parsed, deep: true)
    
    # Map common JSON fields to ECS
    if exists(.event_data.timestamp) {{ .@timestamp = parse_timestamp(.event_data.timestamp, "%Y-%m-%dT%H:%M:%SZ") }}
    if exists(.event_data.level) {{ .log.level = del(.event_data.level) }}
    if exists(.event_data.user) {{ .user.name = del(.event_data.user) }}
    if exists(.event_data.ip) {{ .source.ip = del(.event_data.ip) }}
    if exists(.event_data.message) {{ .message = del(.event_data.message) }}
  }}
}}

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""

def _generate_syslog_vrl(raw_log: str, category: str, vendor: str, product: str) -> str:
    """Generate VRL for syslog"""
    return f"""
.event.kind = "event"
.event.category = ["{category}"]
.observer.vendor = "{vendor}"
.observer.product = "{product}"
.observer.type = "system"
.event.dataset = "{vendor}.{product}"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Parse syslog
if exists(.event.original) {{
  parsed = parse_syslog(.event.original)
  if is_object(parsed) {{
    .event_data = merge(.event_data, parsed, deep: true)
    
    # Map syslog fields to ECS
    if exists(.event_data.timestamp) {{ .@timestamp = .event_data.timestamp }}
    if exists(.event_data.hostname) {{ .host.name = del(.event_data.hostname) }}
    if exists(.event_data.program) {{ .process.name = del(.event_data.program) }}
    if exists(.event_data.severity) {{ .log.level = del(.event_data.severity) }}
  }}
}}

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""

def _generate_generic_vrl(raw_log: str, category: str, vendor: str, product: str) -> str:
    """Generate generic VRL for unknown log types"""
    return f"""
.event.kind = "event"
.event.category = ["{category}"]
.observer.vendor = "{vendor}"
.observer.product = "{product}"
.observer.type = "unknown"
.event.dataset = "{vendor}.{product}"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Basic parsing attempt
if exists(.event.original) {{
  # Try key-value parsing
  kvs = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
  if is_object(kvs) {{
    .event_data = merge(.event_data, kvs, deep: true)
  }}
  
  # Extract IP addresses
  if .event.original matches /(\\d{{1,3}}\\.\\d{{1,3}}\\.\\d{{1,3}}\\.\\d{{1,3}})/ {{
    .source.ip = $1
  }}
}}

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""

def _get_reference_vrl_for_log(log_profile: Dict[str, Any], raw_log: str) -> str:
    """Get appropriate reference VRL example based on log profile"""
    vendor = log_profile.get("vendor", "").lower()
    product = log_profile.get("product", "").lower()
    log_format = log_profile.get("log_format", "").lower()
    
    # Map log types to reference examples
    reference_mapping = {
        "cisco": "fortinet_fortigate_professional.vrl",  # Use Fortinet as template for network devices
        "fortinet": "fortinet_fortigate_professional.vrl",
        "fortigate": "fortinet_fortigate_professional.vrl",
        "palo": "palo_alto_professional.vrl",
        "palo_alto": "palo_alto_professional.vrl",
        "aws": "aws_elb_professional.vrl",
        "elb": "aws_elb_professional.vrl",
        "apache": "apache_access_professional.vrl"
    }
    
    # Try to find matching reference
    reference_file = None
    for key, filename in reference_mapping.items():
        if key in vendor or key in product or key in log_format:
            reference_file = filename
            break
    
    # Default to Fortinet if no match
    if not reference_file:
        reference_file = "fortinet_fortigate_professional.vrl"
    
    # Load the reference file
    try:
        reference_path = f"data/reference_examples/{reference_file}"
        with open(reference_path, 'r') as f:
            return f.read()
    except Exception as e:
        # Return a basic template if file not found
        return _get_basic_vrl_template()


def _get_basic_vrl_template() -> str:
    """Get basic VRL template when reference files are not available"""
    return """
.event.kind = "event"
.event.category = ["network", "security"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "firewall"
.event.dataset = "unknown.logs"

if exists(.message) && is_string(.message) {
  .event.original = del(.message)
}

# Parse key-value pairs if present
kvs = parse_key_value(.event.original, field_delimiter: ",", key_value_delimiter: "=")
if is_object(kvs) { .event_data = merge(.event_data, kvs, deep: true) }

# Extract common fields
if exists(.event_data.srcip) { .source.ip = del(.event_data.srcip) }
if exists(.event_data.dstip) { .destination.ip = del(.event_data.dstip) }
if exists(.event_data.sport) { .source.port = to_int!(del(.event_data.sport)) }
if exists(.event_data.dport) { .destination.port = to_int!(del(.event_data.dport)) }
if exists(.event_data.action) { .event.action = del(.event_data.action) }

.related.ip = unique(compact([.source.ip, .destination.ip]))
. = compact(., string: true, array: true, object: true, null: true)
"""


def _clean_vrl_output(vrl_output: str) -> str:
    """Clean VRL output to remove non-VRL content and fix common issues"""
    # Pre-sanitize common LLM artifacts that break VRL
    sanitized = vrl_output
    # Drop any line that includes the LLM's placeholder error note
    sanitized = "\n".join(
        line for line in sanitized.split('\n')
        if 'Missing some input keys' not in line
    )
    # Normalize placeholder maps like { "k" => "v" }
    sanitized = re.sub(r'event_data\s*\{\s*"k"\s*=>\s*"v"\s*\}', '.event_data = {}', sanitized)
    sanitized = re.sub(r'\{\s*"k"\s*=>\s*"v"\s*\}', '{}', sanitized)
    # Drop any line that still contains Ruby-style hash rocket '=>' (not valid VRL)
    sanitized = "\n".join(line for line in sanitized.split('\n') if '=>' not in line)

    lines = sanitized.split('\n')
    vrl_lines = []
    
    for line in lines:
        line = line.strip()
        # Skip empty lines, comments, and non-VRL content
        if (line and 
            not line.startswith('#') and 
            not line.startswith('//') and
            not line.startswith('```') and
            not line.startswith('ECS') and
            not line.startswith('Type:') and
            not line.startswith('Description:') and
            not line.startswith('Generated VRL') and
            not line.startswith('Here is') and
            not line.startswith('The VRL') and
            not line.startswith('Based on') and
            not line.startswith('Following') and
            not line.startswith('Rules:') and
            not line.startswith('IMPORTANT:') and
            not line.startswith('You are') and
            not line.startswith('Missing some input keys') and
            not line.startswith('1.') and
            not line.startswith('2.') and
            not line.startswith('3.') and
            not line.startswith('4.')):
            
            # Fix common VRL syntax issues
            line = _fix_vrl_syntax(line)
            if line:  # Only add non-empty lines
                vrl_lines.append(line)
    
    # If we have very few lines or the output looks malformed, return a basic fallback
    if len(vrl_lines) < 3 or any('Missing some input keys' in line for line in vrl_lines):
        return _generate_basic_vrl()
    
    # Validate that we have proper VRL structure
    vrl_text = '\n'.join(vrl_lines)
    if not _validate_vrl_structure(vrl_text):
        return _generate_basic_vrl()
    
    return vrl_text

def _validate_vrl_structure(vrl_text: str) -> bool:
    """Validate that VRL has proper structure"""
    # Check for essential VRL elements
    essential_elements = [
        ".event.kind",
        ".event.category",
        ".observer"
    ]
    
    found_elements = sum(1 for element in essential_elements if element in vrl_text)
    
    # Check for malformed syntax
    malformed_patterns = [
        "if exists(.event_data.srcip) { .event_data.srcip = del(.event_data.srcip) }",  # Self-referencing
        "if exists(.event_data.dstip) { .event_data.dstip = del(.event_data.dstip) }",  # Self-referencing
        "connection_id:",
        "event_type:",
        "dstIpv4:",
        "sourceIpv4:"
    ]
    
    has_malformed = any(pattern in vrl_text for pattern in malformed_patterns)
    
    return found_elements >= 2 and not has_malformed

def _fix_vrl_syntax(line: str) -> str:
    """Fix common VRL syntax issues"""
    # Fix incomplete lines
    if line.endswith(';') and not line.startswith('.'):
        return line
    
    # Fix malformed variable assignments
    if '=' in line and not line.startswith('.'):
        # Try to fix common patterns
        if 'srcip' in line and '=' in line:
            line = '.event_data.srcip = ' + line.split('=')[1].strip()
        elif 'dstip' in line and '=' in line:
            line = '.event_data.dstip = ' + line.split('=')[1].strip()
    
    return line

def _generate_basic_vrl() -> str:
    """Generate a basic, valid VRL parser"""
    return """
.event.kind = "event"
.event.category = ["network"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "unknown"
.event.dataset = "unknown.logs"

if exists(.message) && is_string(.message) {
  .event.original = del(.message)
}

# Basic parsing attempt
if exists(.event.original) {
  kvs = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
  if is_object(kvs) {
    .event_data = merge(.event_data, kvs, deep: true)
  }
}
"""


def _generate_fallback_vrl(raw_log: str, error_msg: str) -> str:
    """Generate fallback VRL when all else fails"""
    return f"""
# Fallback VRL Parser
# Error: {error_msg}

.event.kind = "event"
.event.category = ["unknown"]
.observer.vendor = "unknown"
.observer.product = "unknown"
.observer.type = "unknown"
.event.dataset = "unknown.logs"

if exists(.message) && is_string(.message) {{
  .event.original = del(.message)
}}

# Basic parsing attempt
kvs = parse_key_value(.event.original, field_delimiter: " ", key_value_delimiter: "=")
if is_object(kvs) {{ .event_data = merge(.event_data, kvs, deep: true) }}

. = compact(., string: true, array: true, object: true, null: true)
"""


