#!/usr/bin/env python3
"""
Vendor-Specific Parser Router
Routes to the appropriate parser based on detected vendor and product
"""

def get_parser_by_vendor(vendor: str, product: str = "", log_format: str = "") -> str:
    """
    Get the appropriate parser based on vendor, product, and log format
    
    Args:
        vendor: Detected vendor (e.g., "checkpoint", "cisco", "fortinet")
        product: Detected product (e.g., "asa", "fortigate")
        log_format: Log format (e.g., "syslog", "cef", "json")
    
    Returns:
        VRL parser string for the specific vendor/product combination
    """
    
    vendor_lower = vendor.lower()
    product_lower = product.lower()
    
    # CheckPoint parsers
    if vendor_lower in ["checkpoint", "check point"]:
        try:
            from checkpoint_parser import generate_checkpoint_parser
            return generate_checkpoint_parser()
        except ImportError:
            # Fallback to generic syslog if CheckPoint parser not available
            from compact_syslog_parser import generate_compact_syslog_parser
            return generate_compact_syslog_parser()
    
    # Cisco parsers
    elif vendor_lower == "cisco":
        try:
            from cisco_parser import generate_cisco_parser
            return generate_cisco_parser()
        except ImportError:
            # Fallback to generic syslog if Cisco parser not available
            from compact_syslog_parser import generate_compact_syslog_parser
            return generate_compact_syslog_parser()
    
    # Fortinet parsers
    elif vendor_lower in ["fortinet", "fortigate"]:
        try:
            from fortinet_parser import generate_fortinet_parser
            return generate_fortinet_parser()
        except ImportError:
            # Fallback to generic syslog if Fortinet parser not available
            from compact_syslog_parser import generate_compact_syslog_parser
            return generate_compact_syslog_parser()
    
    # Palo Alto parsers (future implementation)
    elif vendor_lower in ["paloalto", "palo alto"]:
        # TODO: Implement Palo Alto parser
        from compact_syslog_parser import generate_compact_syslog_parser
        return generate_compact_syslog_parser()
    
    # SonicWall parsers (future implementation)
    elif vendor_lower in ["sonicwall", "sonicos"]:
        # TODO: Implement SonicWall parser
        from compact_syslog_parser import generate_compact_syslog_parser
        return generate_compact_syslog_parser()
    
    # OpenSSH parsers (future implementation)
    elif vendor_lower in ["openssh", "ssh"]:
        # TODO: Implement OpenSSH parser
        from compact_syslog_parser import generate_compact_syslog_parser
        return generate_compact_syslog_parser()
    
    # Format-based routing for unknown vendors
    elif log_format.lower() == "cef":
        try:
            from optimized_cef_parser_robust import generate_robust_cef_parser
            return generate_robust_cef_parser()
        except ImportError:
            from enhanced_grok_parser import generate_enhanced_grok_cef_vrl
            return generate_enhanced_grok_cef_vrl()
    
    elif log_format.lower() == "json":
        try:
            from optimized_json_parser import generate_optimized_json_parser
            return generate_optimized_json_parser()
        except ImportError:
            from enhanced_grok_parser import generate_enhanced_grok_json_vrl
            return generate_enhanced_grok_json_vrl()
    
    # Default to generic syslog parser
    else:
        try:
            from compact_syslog_parser import generate_compact_syslog_parser
            return generate_compact_syslog_parser()
        except ImportError:
            from enhanced_grok_parser import generate_enhanced_grok_syslog_vrl
            return generate_enhanced_grok_syslog_vrl()


def get_parser_info(vendor: str, product: str = "", log_format: str = "") -> dict:
    """
    Get parser information for the selected parser
    
    Returns:
        Dictionary with parser metadata
    """
    vendor_lower = vendor.lower()
    
    parser_info = {
        "vendor": vendor,
        "product": product,
        "log_format": log_format,
        "parser_type": "generic"
    }
    
    if vendor_lower in ["checkpoint", "check point"]:
        parser_info["parser_type"] = "checkpoint_specialized"
        parser_info["description"] = "CheckPoint Firewall Parser - Optimized for CheckPoint syslog format"
    elif vendor_lower == "cisco":
        parser_info["parser_type"] = "cisco_specialized"
        parser_info["description"] = "Cisco Parser - Supports ASA, IOS, Nexus logs"
    elif vendor_lower in ["fortinet", "fortigate"]:
        parser_info["parser_type"] = "fortinet_specialized"
        parser_info["description"] = "Fortinet FortiGate Parser - Optimized for FortiGate logs"
    elif log_format.lower() == "cef":
        parser_info["parser_type"] = "cef_specialized"
        parser_info["description"] = "CEF Parser - Common Event Format parser"
    elif log_format.lower() == "json":
        parser_info["parser_type"] = "json_specialized"
        parser_info["description"] = "JSON Parser - Structured JSON log parser"
    else:
        parser_info["parser_type"] = "syslog_generic"
        parser_info["description"] = "Generic Syslog Parser - Standard syslog format parser"
    
    return parser_info


# Test function
if __name__ == "__main__":
    # Test different vendor routing
    test_cases = [
        ("checkpoint", "smartdefence", "syslog"),
        ("cisco", "asa", "syslog"),
        ("fortinet", "fortigate", "syslog"),
        ("unknown", "unknown", "cef"),
        ("unknown", "unknown", "json"),
        ("unknown", "unknown", "syslog")
    ]
    
    for vendor, product, log_format in test_cases:
        parser = get_parser_by_vendor(vendor, product, log_format)
        info = get_parser_info(vendor, product, log_format)
        
        print(f"Vendor: {vendor}, Product: {product}, Format: {log_format}")
        print(f"Parser Type: {info['parser_type']}")
        print(f"Description: {info['description']}")
        print(f"Parser Length: {len(parser)} characters")
        print("-" * 50)
