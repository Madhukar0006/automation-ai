#!/usr/bin/env python3
"""
VRL Error Integration - Integrates error handling into the main VRL generation pipeline
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from vrl_error_handler import VRL_Error_Handler, VRL_Error, VRL_ERROR_TYPE
from enhanced_vrl_generator import Enhanced_VRL_Generator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VRL_Error_Integration:
    """Integrates VRL error handling into the main system"""
    
    def __init__(self):
        self.error_handler = VRL_Error_Handler()
        self.enhanced_generator = Enhanced_VRL_Generator()
        self.error_stats = {
            "total_generations": 0,
            "successful_generations": 0,
            "failed_generations": 0,
            "errors_fixed": 0,
            "common_errors": {}
        }
    
    def generate_vrl_with_error_handling(self, context_text: str, raw_log: str, dynamic_prefix: str = "") -> Dict[str, Any]:
        """Generate VRL with comprehensive error handling"""
        self.error_stats["total_generations"] += 1
        
        try:
            # Use enhanced generator
            result = self.enhanced_generator.generate_robust_vrl(context_text, raw_log, dynamic_prefix)
            
            if result["success"]:
                self.error_stats["successful_generations"] += 1
            else:
                self.error_stats["failed_generations"] += 1
            
            # Update error statistics
            self._update_error_stats(result["errors"])
            
            # Log the result
            self._log_generation_result(result)
            
            return result
            
        except Exception as e:
            logger.error(f"VRL generation failed: {str(e)}")
            self.error_stats["failed_generations"] += 1
            
            return {
                "success": False,
                "vrl_code": "",
                "errors": [{
                    "error_type": "SYSTEM_ERROR",
                    "error_code": "SYS_001",
                    "message": f"System error: {str(e)}",
                    "suggested_fix": "Check system configuration and try again"
                }],
                "fixes_applied": [],
                "attempts": 1,
                "final_validation": False
            }
    
    def validate_existing_vrl(self, vrl_code: str) -> Dict[str, Any]:
        """Validate existing VRL code"""
        is_valid, errors = self.error_handler.validate_vrl_syntax(vrl_code)
        
        return {
            "is_valid": is_valid,
            "errors": [self._error_to_dict(e) for e in errors],
            "error_count": len(errors),
            "error_report": self.error_handler.generate_error_report(errors)
        }
    
    def fix_existing_vrl(self, vrl_code: str) -> Dict[str, Any]:
        """Fix existing VRL code"""
        fixed_code, is_valid, errors = self.error_handler.auto_fix_vrl(vrl_code)
        
        return {
            "success": is_valid,
            "original_code": vrl_code,
            "fixed_code": fixed_code,
            "errors": [self._error_to_dict(e) for e in errors],
            "error_report": self.error_handler.generate_error_report(errors)
        }
    
    def batch_validate_vrl_files(self, vrl_files: List[str]) -> Dict[str, Any]:
        """Validate multiple VRL files"""
        results = {}
        
        for file_path in vrl_files:
            try:
                with open(file_path, 'r') as f:
                    vrl_code = f.read()
                
                validation_result = self.validate_existing_vrl(vrl_code)
                results[file_path] = validation_result
                
            except Exception as e:
                results[file_path] = {
                    "is_valid": False,
                    "errors": [{
                        "error_type": "FILE_ERROR",
                        "error_code": "FILE_001",
                        "message": f"Could not read file: {str(e)}",
                        "suggested_fix": "Check file path and permissions"
                    }],
                    "error_count": 1,
                    "error_report": f"File error: {str(e)}"
                }
        
        return results
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error handling statistics"""
        total = self.error_stats["total_generations"]
        success_rate = (self.error_stats["successful_generations"] / total * 100) if total > 0 else 0
        
        return {
            "total_generations": total,
            "successful_generations": self.error_stats["successful_generations"],
            "failed_generations": self.error_stats["failed_generations"],
            "success_rate": round(success_rate, 2),
            "errors_fixed": self.error_stats["errors_fixed"],
            "common_errors": self.error_stats["common_errors"]
        }
    
    def generate_error_handling_report(self) -> str:
        """Generate comprehensive error handling report"""
        stats = self.get_error_statistics()
        
        report = "📊 VRL Error Handling Report\n"
        report += "=" * 50 + "\n\n"
        
        report += f"Total Generations: {stats['total_generations']}\n"
        report += f"Successful: {stats['successful_generations']} ({stats['success_rate']}%)\n"
        report += f"Failed: {stats['failed_generations']}\n"
        report += f"Errors Fixed: {stats['errors_fixed']}\n\n"
        
        if stats['common_errors']:
            report += "🔍 Common Errors:\n"
            for error_type, count in stats['common_errors'].items():
                report += f"  • {error_type}: {count} occurrences\n"
            report += "\n"
        
        return report
    
    def _update_error_stats(self, errors: List[Dict[str, Any]]):
        """Update error statistics"""
        for error in errors:
            error_type = error.get("error_type", "UNKNOWN")
            if error_type in self.error_stats["common_errors"]:
                self.error_stats["common_errors"][error_type] += 1
            else:
                self.error_stats["common_errors"][error_type] = 1
        
        if errors:
            self.error_stats["errors_fixed"] += len(errors)
    
    def _log_generation_result(self, result: Dict[str, Any]):
        """Log VRL generation result"""
        if result["success"]:
            logger.info(f"VRL generation successful after {result['attempts']} attempts")
            if result["fixes_applied"]:
                logger.info(f"Applied fixes: {', '.join(result['fixes_applied'])}")
        else:
            logger.warning(f"VRL generation failed after {result['attempts']} attempts")
            if result["errors"]:
                for error in result["errors"]:
                    logger.warning(f"Error: {error['message']}")
    
    def _error_to_dict(self, error: VRL_Error) -> Dict[str, Any]:
        """Convert VRL_Error to dictionary"""
        return {
            "error_type": error.error_type.name,
            "error_code": error.error_code,
            "message": error.message,
            "line_number": error.line_number,
            "column": error.column,
            "context": error.context,
            "suggested_fix": error.suggested_fix,
            "severity": error.severity
        }

# Integration with existing lc_bridge
def patch_lc_bridge_with_error_handling():
    """Patch lc_bridge to use error handling"""
    try:
        import lc_bridge
        from vrl_error_integration import VRL_Error_Integration
        
        # Create error integration instance
        error_integration = VRL_Error_Integration()
        
        # Store original function
        original_generate_vrl_lc = lc_bridge.generate_vrl_lc
        
        def enhanced_generate_vrl_lc(context_text: str, raw_log: str, dynamic_prefix: str = "") -> str:
            """Enhanced VRL generation with error handling"""
            result = error_integration.generate_vrl_with_error_handling(context_text, raw_log, dynamic_prefix)
            
            if result["success"]:
                return result["vrl_code"]
            else:
                # Return minimal VRL as fallback
                return error_integration.enhanced_generator._generate_minimal_vrl(raw_log)
        
        # Replace the function
        lc_bridge.generate_vrl_lc = enhanced_generate_vrl_lc
        
        logger.info("Successfully patched lc_bridge with error handling")
        return error_integration
        
    except Exception as e:
        logger.error(f"Failed to patch lc_bridge: {str(e)}")
        return None

# Example usage and testing
if __name__ == "__main__":
    integration = VRL_Error_Integration()
    
    # Test VRL generation with error handling
    test_log = '192.168.0.5 - - [03/Sep/2025:14:25:33 +0000] "GET /index.html HTTP/1.1" 200 1234 "http://example.com" "Mozilla/5.0" EXTRA-JUNK'
    
    print("Testing VRL Error Integration...")
    print("=" * 50)
    
    result = integration.generate_vrl_with_error_handling("test context", test_log)
    
    print("Generation Result:")
    print(f"Success: {result['success']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Final Validation: {result['final_validation']}")
    
    if result['fixes_applied']:
        print(f"Fixes Applied: {', '.join(result['fixes_applied'])}")
    
    if result['errors']:
        print(f"Errors: {len(result['errors'])}")
        for error in result['errors']:
            print(f"  - {error['error_type']}: {error['message']}")
    
    # Generate statistics report
    print("\n" + integration.generate_error_handling_report())

