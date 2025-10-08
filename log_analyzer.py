import re
import json

# --- REGEX Definitions for Common Log Formats ---
# Syslog (RFC 5424 and classic BSD format)
SYSLOG_REGEX = re.compile(r'<\d{1,3}>\d\s+\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[\+\-]\d{2}:\d{2})?\s+\w+')
# RFC5424-like without explicit version digit after PRI (tolerate devices omitting it)
SYSLOG_RFC5424_NO_VER = re.compile(r'^<\d{1,3}>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[\+\-]\d{2}:\d{2})?\s+')
SYSLOG_CLASSIC_REGEX = re.compile(r'<\d{1,3}>\w{3}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}\s\w+')
# Classic RFC3164 without PRI header
SYSLOG_NO_PRI_REGEX = re.compile(r'^\w{3}\s+\d{1,2}\s\d{2}:\d{2}:\d{2}\s')
# RFC6587 Octet-Counting syslog: length prefix followed by PRI/version
SYSLOG_OCTET_REGEX = re.compile(r'^\d+\s*<\d{1,3}>\d')

# CheckPoint specific patterns
CHECKPOINT_REGEX = re.compile(r'<\d{1,3}>\d\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[\+\-]\d{2}:\d{2})?\s+\w+.*CheckPoint.*\[.*origin.*product.*\]')
CHECKPOINT_SIMPLE = re.compile(r'CheckPoint.*\[.*origin.*product.*\]')

# Common Event Format (CEF) - looks for the initial "CEF:0|"
CEF_REGEX = re.compile(r'CEF:0\|')

# Log Event Extended Format (LEEF) - starts with "LEEF:1.0|" or "LEEF:2.0|"
LEEF_REGEX = re.compile(r'LEEF:[12]\.0\|')

# Common Log Format (CLF) for web servers
CLF_REGEX = re.compile(r'(\S+)\s(\S+)\s(\S+)\s\[([^\]]+)\]\s"([^"]+)"\s(\d{3})\s(\d+|-)')

# Enhanced Key-Value Pair regex that handles quoted values
KV_REGEX = re.compile(r'(\w+)=(?:"([^"]*)"|([^=\s]+))')

# --- Helper Functions ---
def is_json(line):
    """Checks if a string is valid JSON."""
    try:
        json.loads(line)
        return True
    except ValueError:
        return False

def is_ajson(obj):
    """Placeholder function to check for 'ajson' (ArcSight JSON) format."""
    # This is a custom check. For example, it might look for specific
    # ArcSight keys at the top level of the JSON object.
    if isinstance(obj, dict):
        return 'Arcsight' in obj.get('Product', '')
    return False

# --- The Main Identification Function ---
def identify_log_type(line):
    """
    Identifies the fundamental format of a raw log line by checking for
    universal formats first before falling back to vendor-specific patterns.
    """
    line = line.strip()
    if not line:
        return "empty"
        
    # 1. Check for JSON first, as it's the most structured.
    if is_json(line):
        obj = json.loads(line)
        # Check for ArcSight JSON as a sub-type
        if is_ajson(obj):
            return "ajson"
        else:
            return "json"
            
    # 2. Check for standardized text formats (CEF, LEEF).
    if re.match(CEF_REGEX, line):
        return "cef"
    if re.match(LEEF_REGEX, line):
        return "leef"

    # 3. Check for Syslog variants. This is crucial for many device types.
    if (re.match(SYSLOG_REGEX, line)
        or re.match(SYSLOG_RFC5424_NO_VER, line)
        or re.match(SYSLOG_CLASSIC_REGEX, line)
        or re.match(SYSLOG_NO_PRI_REGEX, line)
        or re.match(SYSLOG_OCTET_REGEX, line)):
        # Now, check for vendor-specific signatures within the syslog
        if re.search(CHECKPOINT_SIMPLE, line):
            return "checkpoint"
        # Add other vendor checks here (e.g., for Cisco, Palo Alto)
        # if 'ASA' in line: return "cisco_asa"
        
        # If no vendor signature, it's generic syslog
        return "syslog"
    
    # 3b. Check for Cisco ASA logs without syslog header (common format)
    if re.search(r'%ASA-\d+-\d+:', line):
        return "syslog"
    
    # 3c. Check for other vendor logs without syslog header
    if re.search(r'%[A-Z]+-\d+-\d+:', line):
        return "syslog"
        
    # 4. Check for web server formats.
    if re.match(CLF_REGEX, line):
        return "clf"
        
    # 5. Fallback to key-value if multiple pairs are found.
    if len(re.findall(KV_REGEX, line)) > 2: # Require at least 3 key-value pairs
        return "keyvalue"
        
    # 6. If none of the above, it's an unknown raw format.
    return "unknown"

# --- VRL Pattern Generator ---
def get_vrl_pattern():
    """Returns the comprehensive VRL pattern for log format detection and parsing"""
    return """
# VRL patterns are now in separate files:
# - data/commansineppets.vrl (common patterns)
# - data/eventcreatedsinppets.vrl (timestamp patterns) 
# - data/syslogsinppets.vrl (syslog-specific patterns)
"""
