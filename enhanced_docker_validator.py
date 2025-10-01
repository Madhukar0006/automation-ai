"""
Enhanced Docker VRL Validator
Comprehensive validation system with feedback loops for Agent03
"""

import subprocess
import tempfile
import os
import json
import re
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime


class EnhancedDockerValidator:
    """Enhanced Docker-based VRL validator with comprehensive feedback"""
    
    def __init__(self, 
                 docker_compose_path: str = "docker/docker-compose-test.yaml",
                 vrl_output_path: str = "docker/vector_config/parser.vrl",
                 config_path: str = "docker/vector_config/config.yaml",
                 test_log_path: str = "docker/vector_logs/test.log"):
        
        self.docker_compose_path = docker_compose_path
        self.vrl_output_path = vrl_output_path
        self.config_path = config_path
        self.test_log_path = test_log_path
        
        # Validation history for feedback loops
        self.validation_history: List[Dict[str, Any]] = []
    
    def validate_vrl_comprehensive(self, vrl_code: str, sample_log: str = None) -> Dict[str, Any]:
        """
        Comprehensive VRL validation with detailed feedback
        
        Args:
            vrl_code: VRL code to validate
            sample_log: Optional sample log for testing
            
        Returns:
            Dict with comprehensive validation results
        """
        validation_id = f"validation_{int(datetime.now().timestamp())}"
        
        try:
            # Step 1: Syntax validation
            syntax_result = self._validate_vrl_syntax(vrl_code)
            
            # Step 2: Docker validation
            docker_result = self._validate_vrl_docker(vrl_code)
            
            # Step 3: Test with sample log if provided
            test_result = None
            if sample_log:
                test_result = self._test_vrl_with_sample(vrl_code, sample_log)
            
            # Step 4: Generate comprehensive feedback
            feedback = self._generate_comprehensive_feedback(
                syntax_result, docker_result, test_result, vrl_code
            )
            
            # Combine results
            result = {
                "validation_id": validation_id,
                "status": "success" if docker_result["valid"] else "failed",
                "valid": docker_result["valid"],
                "syntax_valid": syntax_result["valid"],
                "docker_valid": docker_result["valid"],
                "test_valid": test_result["valid"] if test_result else None,
                "error_message": docker_result.get("error", ""),
                "syntax_errors": syntax_result.get("errors", []),
                "docker_errors": docker_result.get("error", ""),
                "test_errors": test_result.get("error", "") if test_result else "",
                "feedback": feedback,
                "vrl_file_path": self.vrl_output_path,
                "config_path": self.config_path,
                "validation_command": docker_result.get("command", ""),
                "output": docker_result.get("output", ""),
                "timestamp": datetime.now().isoformat()
            }
            
            # Store in history for feedback loops
            self.validation_history.append(result)
            
            return result
            
        except Exception as e:
            error_result = {
                "validation_id": validation_id,
                "status": "error",
                "valid": False,
                "error_message": str(e),
                "feedback": f"❌ Validation failed with error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
            self.validation_history.append(error_result)
            return error_result
    
    def _validate_vrl_syntax(self, vrl_code: str) -> Dict[str, Any]:
        """Basic VRL syntax validation"""
        errors = []
        
        # Check for basic VRL structure
        if not vrl_code.strip():
            errors.append("VRL code is empty")
        
        # Check for required patterns
        required_patterns = [
            (r'\.event\.', "Missing .event. field assignments"),
            (r'parse_', "Missing parser function (parse_groks, parse_json, etc.)"),
        ]
        
        for pattern, message in required_patterns:
            if not re.search(pattern, vrl_code):
                errors.append(message)
        
        # Check for common syntax issues
        if vrl_code.count('{') != vrl_code.count('}'):
            errors.append("Mismatched curly braces")
        
        if vrl_code.count('(') != vrl_code.count(')'):
            errors.append("Mismatched parentheses")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def _validate_vrl_docker(self, vrl_code: str) -> Dict[str, Any]:
        """Validate VRL using Docker and Vector CLI"""
        try:
            # Write VRL to file and update config
            self._write_vrl_to_file(vrl_code)
            
            # Run Docker validation
            cmd = [
                "docker", "compose", 
                "-f", self.docker_compose_path,
                "run", "--rm", 
                "parser-package"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "valid": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
                "command": " ".join(cmd),
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "valid": False,
                "output": "",
                "error": "Validation timed out after 30 seconds",
                "command": " ".join(cmd),
                "return_code": -1
            }
        except Exception as e:
            return {
                "valid": False,
                "output": "",
                "error": f"Docker validation failed: {str(e)}",
                "command": "",
                "return_code": -1
            }
    
    def _test_vrl_with_sample(self, vrl_code: str, sample_log: str) -> Dict[str, Any]:
        """Test VRL with sample log data"""
        try:
            # Write sample log to test file
            with open(self.test_log_path, 'w') as f:
                f.write(sample_log)
            
            # Update config for testing
            self._update_config_for_testing()
            
            # Run test
            cmd = [
                "docker", "compose", 
                "-f", self.docker_compose_path,
                "run", "--rm", 
                "parser-package"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "valid": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else "",
                "command": " ".join(cmd)
            }
            
        except Exception as e:
            return {
                "valid": False,
                "output": "",
                "error": f"Test failed: {str(e)}",
                "command": ""
            }
    
    def _write_vrl_to_file(self, vrl_code: str) -> None:
        """Write VRL code to file and update Vector config"""
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.vrl_output_path), exist_ok=True)
        
        # Write VRL code to parser file
        with open(self.vrl_output_path, 'w') as f:
            f.write(vrl_code)
        
        # Update the config.yaml with the VRL code
        self._update_config_with_vrl(vrl_code)
    
    def _update_config_with_vrl(self, vrl_code: str) -> None:
        """Update Vector config with VRL code"""
        try:
            # Read current config
            with open(self.config_path, 'r') as f:
                config_content = f.read()
            
            # Create VRL section
            vrl_section = f"""      # VRL Parser Code - Generated by Agent03
      # Validation timestamp: {datetime.now().isoformat()}
      
{vrl_code}
      
      # Ensure required ECS fields
      if !exists(."event.kind") {{
        .event.kind = "event"
      }}
      if !exists(."event.category") {{
        .event.category = ["unknown"]
      }}
      if !exists(."event.created") {{
        .event.created = now()
      }}
      if !exists(."@timestamp") {{
        .@timestamp = now()
      }}"""
            
            # Replace the source section in config
            updated_config = re.sub(
                r'source: \|.*?(?=sinks:)',
                f'source: |\n{vrl_section}\n',
                config_content,
                flags=re.DOTALL
            )
            
            # Write updated config
            with open(self.config_path, 'w') as f:
                f.write(updated_config)
                
        except Exception as e:
            print(f"Warning: Could not update config with VRL code: {e}")
    
    def _update_config_for_testing(self) -> None:
        """Update config to use file input for testing"""
        try:
            with open(self.config_path, 'r') as f:
                config_content = f.read()
            
            # Replace stdin with file input for testing
            file_input_config = f"""
sources:
  file_input:
    type: file
    include: ["{self.test_log_path}"]
    read_from: beginning
"""
            
            updated_config = re.sub(
                r'sources:.*?transforms:',
                f'{file_input_config}\ntransforms:',
                config_content,
                flags=re.DOTALL
            )
            
            # Update transform input
            updated_config = updated_config.replace(
                'inputs: ["stdin_input"]',
                'inputs: ["file_input"]'
            )
            
            with open(self.config_path, 'w') as f:
                f.write(updated_config)
                
        except Exception as e:
            print(f"Warning: Could not update config for testing: {e}")
    
    def _generate_comprehensive_feedback(self, syntax_result: Dict, docker_result: Dict, 
                                       test_result: Optional[Dict], vrl_code: str) -> str:
        """Generate comprehensive feedback for VRL improvement"""
        feedback_parts = []
        
        # Overall status
        if docker_result["valid"]:
            feedback_parts.append("✅ VRL validation passed successfully!")
        else:
            feedback_parts.append("❌ VRL validation failed!")
        
        # Syntax feedback
        if not syntax_result["valid"]:
            feedback_parts.append("\n🔍 Syntax Issues:")
            for error in syntax_result.get("errors", []):
                feedback_parts.append(f"  - {error}")
        
        # Docker validation feedback
        if not docker_result["valid"]:
            feedback_parts.append("\n🐳 Docker Validation Errors:")
            error_msg = docker_result.get("error", "")
            
            # Parse specific error types
            if "syntax error" in error_msg.lower():
                feedback_parts.append("  - Fix VRL syntax errors")
            if "parse_grok" in error_msg.lower():
                feedback_parts.append("  - Verify Grok patterns are valid")
            if "undefined variable" in error_msg.lower():
                feedback_parts.append("  - Ensure all variables are properly defined")
            if "field" in error_msg.lower() and "not found" in error_msg.lower():
                feedback_parts.append("  - Check field references")
            
            if error_msg:
                feedback_parts.append(f"  - Error details: {error_msg[:200]}...")
        
        # Test feedback
        if test_result and not test_result["valid"]:
            feedback_parts.append("\n🧪 Test Results:")
            feedback_parts.append(f"  - Test failed: {test_result.get('error', 'Unknown error')}")
        
        # General recommendations
        feedback_parts.append("\n💡 Recommendations:")
        
        # Check for common VRL patterns
        if "parse_groks" not in vrl_code and "parse_json" not in vrl_code and "parse_syslog" not in vrl_code:
            feedback_parts.append("  - Add a primary parser (parse_groks, parse_json, or parse_syslog)")
        
        if ".event.created" not in vrl_code:
            feedback_parts.append("  - Add .event.created field assignment")
        
        if "compact(" not in vrl_code:
            feedback_parts.append("  - Add compact() call at the end")
        
        return "\n".join(feedback_parts)
    
    def get_validation_feedback(self, validation_result: Dict[str, Any]) -> str:
        """Get human-readable feedback from validation results"""
        return validation_result.get("feedback", "No feedback available")
    
    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Get validation history for debugging"""
        return self.validation_history
    
    def clear_history(self) -> None:
        """Clear validation history"""
        self.validation_history = []


def create_enhanced_docker_validator() -> EnhancedDockerValidator:
    """Factory function to create enhanced Docker validator"""
    return EnhancedDockerValidator()


# Test function
if __name__ == "__main__":
    # Test with a sample VRL
    test_vrl = """
# Test VRL for validation
.event.kind = "event"
.event.category = ["authentication"]
.event.type = ["start"]
.event.created = now()
.message = .
"""
    
    validator = create_enhanced_docker_validator()
    result = validator.validate_vrl_comprehensive(test_vrl, "Sample log line")
    print(json.dumps(result, indent=2))

