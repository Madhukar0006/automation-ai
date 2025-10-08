#!/usr/bin/env python3
"""
VRL Syntax Converter
Converts AI-generated pseudo-VRL code to proper VRL syntax
"""

import re

class VRLSyntaxConverter:
    """Converts invalid VRL syntax to proper VRL syntax"""
    
    def __init__(self):
        self.conversion_rules = [
            # Convert split() functions
            (r'split\(([^,]+),\s*"([^"]+)"\)\[(\d+)\]', self._convert_split),
            # Convert map() functions
            (r'map\(([^,]+),\s*([^)]+)\)', self._convert_map),
            # Convert .set() functions
            (r'\.set\(([^,]+),\s*([^)]+)\)', self._convert_set),
            # Convert object literals
            (r'(\w+)\s*=\s*\{([^}]+)\}', self._convert_object),
            # Convert to_number() to to_int()
            (r'to_number\(', 'to_int('),
        ]
    
    def convert_to_vrl(self, pseudo_vrl: str, log_profile: dict = None) -> str:
        """Convert pseudo-VRL code to proper VRL syntax"""
        
        # Clean up the input
        vrl_code = pseudo_vrl.strip()
        
        # Remove code blocks and explanations
        vrl_code = re.sub(r'```vrl\n?', '', vrl_code)
        vrl_code = re.sub(r'```\n?', '', vrl_code)
        vrl_code = re.sub(r'Here is.*?requirements:\n?', '', vrl_code)
        vrl_code = re.sub(r'This code.*?$', '', vrl_code, flags=re.DOTALL)
        
        # Apply conversion rules
        for pattern, converter in self.conversion_rules:
            vrl_code = re.sub(pattern, converter, vrl_code)
        
        # Generate proper VRL parser with log profile
        return self._generate_proper_vrl(vrl_code, log_profile)
    
    def _convert_split(self, match) -> str:
        """Convert split() function to VRL syntax"""
        var_name = match.group(1)
        delimiter = match.group(2)
        index = int(match.group(3))
        
        if delimiter == ";":
            # For CheckPoint logs with semicolon delimiter
            if index == 1:
                return 'grok_match, err = parse_grok(raw_message, "flags:\\"([^\\"]+)\\";")'
            elif index == 2:
                return 'grok_match, err = parse_grok(raw_message, "ifdir:\\"([^\\"]+)\\";")'
            elif index == 3:
                return 'grok_match, err = parse_grok(raw_message, "ifname:\\"([^\\"]+)\\";")'
            elif index == 4:
                return 'grok_match, err = parse_grok(raw_message, "loguid:\\"([^\\"]+)\\";")'
            elif index == 5:
                return 'grok_match, err = parse_grok(raw_message, "origin:\\"([^\\"]+)\\";")'
        
        return f'# Converted: {match.group(0)}'
    
    def _convert_map(self, match) -> str:
        """Convert map() function to VRL syntax"""
        source = match.group(1).strip()
        target = match.group(2).strip()
        
        return f'if exists({source}) {{ {target} = {source} }}'
    
    def _convert_set(self, match) -> str:
        """Convert .set() function to VRL syntax"""
        field = match.group(1).strip()
        value = match.group(2).strip()
        
        return f'{field} = {value}'
    
    def _convert_object(self, match) -> str:
        """Convert object literal to VRL syntax"""
        var_name = match.group(1)
        content = match.group(2)
        
        # Convert to individual field assignments
        lines = []
        for line in content.split(','):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                lines.append(f'.event_data.{key} = {value}')
        
        return '\n'.join(lines)
    
    def _generate_proper_vrl(self, converted_code: str, log_profile: dict = None) -> str:
        """Generate proper VRL parser for CheckPoint logs"""
        
        # Default values
        observer_type = "ngfw"
        observer_vendor = "CheckPoint"
        observer_product = "SmartDefence/Firewall"
        
        # Use log profile if available
        if log_profile:
            # Map log_type to observer.type
            log_type = log_profile.get('log_type', 'Security')
            if log_type.lower() == 'security':
                observer_type = "ngfw"  # Next Generation Firewall
            elif log_type.lower() == 'network':
                observer_type = "network"
            elif log_type.lower() == 'system':
                observer_type = "system"
            elif log_type.lower() == 'application':
                observer_type = "application"
            
            # Use vendor and product from profile
            observer_vendor = log_profile.get('vendor', 'CheckPoint').title()
            observer_product = log_profile.get('product', 'SmartDefence/Firewall')
        
        # Generate dynamic parser based on vendor and log format
        vendor_lower = observer_vendor.lower()
        dataset_name = f"{vendor_lower}.logs"
        
        # Determine parsing logic based on vendor
        if "checkpoint" in vendor_lower:
            parsing_section = self._generate_checkpoint_parsing()
            event_category = '["network", "security"]'
        elif "cisco" in vendor_lower:
            parsing_section = self._generate_cisco_parsing()
            event_category = '["network", "security"]'
        elif "fortinet" in vendor_lower:
            parsing_section = self._generate_fortinet_parsing()
            event_category = '["network", "security"]'
        else:
            parsing_section = self._generate_generic_parsing()
            event_category = '["application"]'
        
        return f"""
##################################################
## AI-Generated {observer_vendor} Parser - Converted to VRL
##################################################

### ECS observer defaults for {observer_vendor}
.observer.type = "{observer_type}"
.observer.vendor = "{observer_vendor}"
.observer.product = "{observer_product}"

### ECS event defaults
.event.dataset = "{dataset_name}"
.event.category = {event_category}
.event.type = ["info"]
.event.kind = "event"

##################################################
### Parse {observer_vendor} Message
##################################################
raw_message = to_string(.message) ?? ""

{parsing_section}

##################################################
### Timestamps and Metadata
##################################################
if !exists(.@timestamp) {{ .@timestamp = now() }}
if !exists(.event.created) {{ .event.created = now() }}

.log.original = raw_message

##################################################
### Compact final object
##################################################
. = compact(., null: true)
"""


# Test the converter
if __name__ == "__main__":
    converter = VRLSyntaxConverter()
    
    # Test with the AI-generated pseudo-VRL
    pseudo_vrl = '''
    raw_message = to_string(.message) ?? ""
    
    flags = split(raw_message, ";")[1]
    ifdir = split(raw_message, ";")[2]
    ifname = split(raw_message, ";")[3]
    loguid = split(raw_message, ";")[4]
    origin = split(raw_message, ";")[5]
    
    map(origin, .source.ip)
    
    .set(.observer.vendor, "Checkpoint")
    
    event_data = {
      flags: to_number(flags),
      ifdir: ifdir,
      ifname: ifname,
      loguid: loguid,
      product: split(raw_message, ";")[6],
      sequencenum: split(raw_message, ";")[7],
      version: split(raw_message, ";")[8],
      sys_message: split(raw_message, ";")[9]
    }
    '''
    
    proper_vrl = converter.convert_to_vrl(pseudo_vrl)
    print("Converted VRL:")
    print(proper_vrl)
