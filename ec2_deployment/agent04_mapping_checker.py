"""
Agent04 - VRL Mapping Checker
Validates ECS compliance and mapping quality of generated VRL
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class MappingIssue:
    """Represents a mapping issue found in VRL"""
    issue_type: str  # 'missing_field', 'incorrect_mapping', 'poor_quality', 'ecs_violation'
    field_name: str
    description: str
    severity: str  # 'low', 'medium', 'high', 'critical'
    suggested_fix: Optional[str] = None


class Agent04_MappingChecker:
    """Agent04: Checks VRL mappings for ECS compliance and quality"""
    
    def __init__(self):
        # Standard ECS fields that should be prioritized
        self.ecs_priority_fields = {
            'event': ['kind', 'category', 'action', 'outcome', 'type', 'id', 'created'],
            'source': ['ip', 'port', 'domain', 'user', 'process'],
            'destination': ['ip', 'port', 'domain', 'user', 'process'],
            'host': ['name', 'ip', 'mac', 'os', 'architecture'],
            'user': ['name', 'id', 'email', 'domain'],
            'process': ['name', 'pid', 'executable', 'command_line'],
            'file': ['name', 'path', 'extension', 'size', 'hash'],
            'network': ['protocol', 'transport', 'direction'],
            'url': ['original', 'domain', 'path', 'query'],
            'http': ['request', 'response', 'version', 'method'],
            'tls': ['version', 'cipher', 'subject', 'issuer'],
            'observer': ['type', 'vendor', 'product', 'version']
        }
        
        # Common log fields that should be mapped
        self.common_log_fields = [
            'timestamp', 'time', 'date', 'datetime',
            'ip', 'src_ip', 'dst_ip', 'source_ip', 'dest_ip',
            'port', 'src_port', 'dst_port',
            'user', 'username', 'user_name',
            'action', 'event', 'message', 'log_level',
            'host', 'hostname', 'server',
            'protocol', 'method', 'uri', 'url'
        ]
    
    def check_vrl_mappings(self, vrl_code: str, sample_log: str = "", 
                          log_format: str = "unknown") -> Dict[str, Any]:
        """
        Check VRL mappings for ECS compliance and quality
        
        Args:
            vrl_code: VRL code to analyze
            sample_log: Original log sample for context
            log_format: Detected log format
            
        Returns:
            Dict with mapping analysis results
        """
        issues = []
        
        # Extract field mappings from VRL
        mappings = self._extract_field_mappings(vrl_code)
        
        # Check for missing critical ECS fields
        missing_issues = self._check_missing_ecs_fields(mappings, log_format)
        issues.extend(missing_issues)
        
        # Check for incorrect field mappings
        incorrect_issues = self._check_incorrect_mappings(mappings, sample_log)
        issues.extend(incorrect_issues)
        
        # Check mapping quality
        quality_issues = self._check_mapping_quality(mappings, sample_log)
        issues.extend(quality_issues)
        
        # Check ECS compliance
        ecs_issues = self._check_ecs_compliance(mappings)
        issues.extend(ecs_issues)
        
        # Calculate overall score
        score = self._calculate_mapping_score(issues, mappings)
        
        return {
            "status": "success",
            "mapping_score": score,
            "total_issues": len(issues),
            "critical_issues": len([i for i in issues if i.severity == "critical"]),
            "high_issues": len([i for i in issues if i.severity == "high"]),
            "medium_issues": len([i for i in issues if i.severity == "medium"]),
            "low_issues": len([i for i in issues if i.severity == "low"]),
            "issues": [self._issue_to_dict(i) for i in issues],
            "mappings_found": len(mappings),
            "ecs_compliance": self._calculate_ecs_compliance(mappings),
            "needs_regeneration": score < 70 or len([i for i in issues if i.severity in ["critical", "high"]]) > 0
        }
    
    def _extract_field_mappings(self, vrl_code: str) -> Dict[str, str]:
        """Extract field mappings from VRL code"""
        mappings = {}
        
        # Look for ECS field assignments
        ecs_pattern = r'\.([a-z_]+(?:\.[a-z_]+)*)\s*=\s*([^;\n]+)'
        matches = re.findall(ecs_pattern, vrl_code)
        
        for field, value in matches:
            # Clean up the value (remove quotes, etc.)
            clean_value = re.sub(r'^["\']|["\']$', '', value.strip())
            mappings[field] = clean_value
        
        return mappings
    
    def _check_missing_ecs_fields(self, mappings: Dict[str, str], log_format: str) -> List[MappingIssue]:
        """Check for missing critical ECS fields"""
        issues = []
        
        # Required fields for most logs
        required_fields = ['event.kind', 'event.category']
        
        # Format-specific required fields
        if log_format in ['syslog', 'cef', 'leef']:
            required_fields.extend(['source.ip', 'event.created'])
        elif log_format == 'json':
            required_fields.extend(['event_data'])
        elif log_format == 'clf':
            required_fields.extend(['source.ip', 'destination.ip', 'url.original'])
        
        for field in required_fields:
            if field not in mappings:
                severity = "high" if field.startswith('event.') else "medium"
                issues.append(MappingIssue(
                    issue_type="missing_field",
                    field_name=field,
                    description=f"Missing required ECS field: {field}",
                    severity=severity,
                    suggested_fix=f"Add mapping for {field}"
                ))
        
        return issues
    
    def _check_incorrect_mappings(self, mappings: Dict[str, str], sample_log: str) -> List[MappingIssue]:
        """Check for obviously incorrect field mappings"""
        issues = []
        
        # Check for empty or invalid values
        for field, value in mappings.items():
            if not value or value in ['null', 'undefined', '']:
                issues.append(MappingIssue(
                    issue_type="incorrect_mapping",
                    field_name=field,
                    description=f"Field {field} has empty or invalid value: {value}",
                    severity="medium",
                    suggested_fix=f"Provide a valid value for {field}"
                ))
            
            # Check for hardcoded values that should be dynamic
            if field.startswith('source.ip') and value not in sample_log:
                if not any(char in value for char in ['.', ':', '[']):  # Not an IP
                    issues.append(MappingIssue(
                        issue_type="incorrect_mapping",
                        field_name=field,
                        description=f"source.ip appears to be hardcoded: {value}",
                        severity="high",
                        suggested_fix="Extract IP from log content dynamically"
                    ))
        
        return issues
    
    def _check_mapping_quality(self, mappings: Dict[str, str], sample_log: str) -> List[MappingIssue]:
        """Check overall mapping quality"""
        issues = []
        
        # Check if key fields from the log are being mapped
        log_lower = sample_log.lower()
        mapped_fields = set(mappings.keys())
        
        # Look for unmapped important fields in the log
        for field in self.common_log_fields:
            if field in log_lower and not any(field in mapped_field for mapped_field in mapped_fields):
                issues.append(MappingIssue(
                    issue_type="poor_quality",
                    field_name=field,
                    description=f"Important field '{field}' found in log but not mapped to ECS",
                    severity="medium",
                    suggested_fix=f"Consider mapping '{field}' to appropriate ECS field"
                ))
        
        # Check for too many unmapped fields
        if len(mappings) < 3:
            issues.append(MappingIssue(
                issue_type="poor_quality",
                field_name="overall",
                description="Very few fields mapped - parser may be too minimal",
                severity="high",
                suggested_fix="Extract more fields from the log"
            ))
        
        return issues
    
    def _check_ecs_compliance(self, mappings: Dict[str, str]) -> List[MappingIssue]:
        """Check ECS schema compliance"""
        issues = []
        
        for field in mappings.keys():
            # Check if field follows ECS naming conventions
            if not re.match(r'^[a-z_]+(\.[a-z_]+)*$', field):
                issues.append(MappingIssue(
                    issue_type="ecs_violation",
                    field_name=field,
                    description=f"Field name '{field}' doesn't follow ECS naming conventions",
                    severity="medium",
                    suggested_fix="Use lowercase with underscores and dots for ECS compliance"
                ))
            
            # Check for non-standard field names that should be in event_data
            if not any(field.startswith(prefix) for prefix in self.ecs_priority_fields.keys()):
                if not field.startswith('event_data.'):
                    issues.append(MappingIssue(
                        issue_type="ecs_violation",
                        field_name=field,
                        description=f"Non-ECS field '{field}' should be in event_data namespace",
                        severity="low",
                        suggested_fix=f"Move to event_data.{field}"
                    ))
        
        return issues
    
    def _calculate_mapping_score(self, issues: List[MappingIssue], mappings: Dict[str, str]) -> int:
        """Calculate overall mapping quality score (0-100)"""
        if not mappings:
            return 0
        
        base_score = min(len(mappings) * 5, 50)  # Max 50 points for field count
        
        # Deduct points for issues
        for issue in issues:
            if issue.severity == "critical":
                base_score -= 20
            elif issue.severity == "high":
                base_score -= 10
            elif issue.severity == "medium":
                base_score -= 5
            elif issue.severity == "low":
                base_score -= 2
        
        # Bonus for ECS compliance
        ecs_fields = sum(1 for field in mappings.keys() 
                        if any(field.startswith(prefix) for prefix in self.ecs_priority_fields.keys()))
        if ecs_fields > 0:
            base_score += min(ecs_fields * 3, 30)  # Max 30 bonus points
        
        return max(0, min(100, base_score))
    
    def _calculate_ecs_compliance(self, mappings: Dict[str, str]) -> float:
        """Calculate ECS compliance percentage"""
        if not mappings:
            return 0.0
        
        ecs_fields = sum(1 for field in mappings.keys() 
                        if any(field.startswith(prefix) for prefix in self.ecs_priority_fields.keys()))
        
        return (ecs_fields / len(mappings)) * 100
    
    def _issue_to_dict(self, issue: MappingIssue) -> Dict[str, str]:
        """Convert MappingIssue to dictionary"""
        result = {
            "type": issue.issue_type,
            "field": issue.field_name,
            "description": issue.description,
            "severity": issue.severity
        }
        if issue.suggested_fix:
            result["suggested_fix"] = issue.suggested_fix
        return result
    
    def get_mapping_feedback(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate human-readable feedback for Agent02 to improve mappings
        
        Args:
            analysis_result: Result from check_vrl_mappings()
            
        Returns:
            Feedback string for VRL improvement
        """
        score = analysis_result["mapping_score"]
        issues = analysis_result["issues"]
        
        feedback_parts = [f"📊 Mapping Analysis Score: {score}/100"]
        
        if score >= 80:
            feedback_parts.append("✅ Good mapping quality!")
        elif score >= 60:
            feedback_parts.append("⚠️ Moderate mapping quality - some improvements needed")
        else:
            feedback_parts.append("❌ Poor mapping quality - significant improvements needed")
        
        # Group issues by severity
        critical_issues = [i for i in issues if i["severity"] == "critical"]
        high_issues = [i for i in issues if i["severity"] == "high"]
        
        if critical_issues:
            feedback_parts.append("\n🚨 Critical Issues:")
            for issue in critical_issues[:3]:  # Show top 3
                feedback_parts.append(f"- {issue['description']}")
        
        if high_issues:
            feedback_parts.append("\n⚠️ High Priority Issues:")
            for issue in high_issues[:3]:  # Show top 3
                feedback_parts.append(f"- {issue['description']}")
        
        ecs_compliance = analysis_result["ecs_compliance"]
        feedback_parts.append(f"\n📋 ECS Compliance: {ecs_compliance:.1f}%")
        
        if analysis_result["needs_regeneration"]:
            feedback_parts.append("\n🔄 Recommendation: Regenerate VRL with better field mappings")
        
        return "\n".join(feedback_parts)


def create_agent04() -> Agent04_MappingChecker:
    """Factory function to create Agent04"""
    return Agent04_MappingChecker()


# Test function
if __name__ == "__main__":
    test_vrl = """
.event.kind = "event"
.event.category = ["unknown"]
.source.ip = "192.168.1.1"
.event_data = {}
"""
    
    agent04 = create_agent04()
    result = agent04.check_vrl_mappings(test_vrl, "192.168.1.1 user login", "syslog")
    print(json.dumps(result, indent=2))
