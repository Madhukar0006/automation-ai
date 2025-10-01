"""
4-Agent Orchestration System
Coordinates Agent01, Agent02, Agent03, and Agent04 with feedback loops
Implements the workflow from the Excalidraw diagram
"""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Import our agents
from simple_agent import SimpleLogParsingAgent
from agent03_validator import Agent03_DockerValidator
from agent04_mapping_checker import Agent04_MappingChecker
from log_analyzer import identify_log_type
from complete_rag_system import CompleteRAGSystem


class AgentStatus(Enum):
    """Status of each agent"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AgentResult:
    """Result from an agent execution"""
    agent_id: str
    status: AgentStatus
    result: Dict[str, Any]
    error_message: Optional[str] = None
    execution_time: float = 0.0
    feedback: Optional[str] = None


@dataclass
class WorkflowState:
    """Current state of the 4-agent workflow"""
    workflow_id: str
    sample_log: str
    max_iterations: int = 3
    current_iteration: int = 0
    
    # Agent results
    agent01_result: Optional[AgentResult] = None
    agent02_result: Optional[AgentResult] = None
    agent03_result: Optional[AgentResult] = None
    agent04_result: Optional[AgentResult] = None
    
    # Feedback for regeneration
    agent03_feedback: Optional[str] = None
    agent04_feedback: Optional[str] = None
    
    # Final status
    workflow_completed: bool = False
    final_vrl: Optional[str] = None
    success: bool = False


class FourAgentOrchestrator:
    """Orchestrates the 4-agent workflow with feedback loops"""
    
    def __init__(self, rag_system: CompleteRAGSystem):
        self.rag_system = rag_system
        
        # Initialize agents
        self.agent01 = None  # Will be created with RAG function
        self.agent02 = None  # Will be created with RAG function
        self.agent03 = Agent03_DockerValidator()
        self.agent04 = Agent04_MappingChecker()
        
        # Workflow history
        self.workflow_history: List[WorkflowState] = []
    
    def execute_workflow(self, sample_log: str, max_iterations: int = 3) -> WorkflowState:
        """
        Execute the complete 4-agent workflow
        
        Args:
            sample_log: Raw log to process
            max_iterations: Maximum number of regeneration attempts
            
        Returns:
            Final workflow state
        """
        workflow_id = f"workflow_{int(time.time())}"
        state = WorkflowState(
            workflow_id=workflow_id,
            sample_log=sample_log,
            max_iterations=max_iterations
        )
        
        # Initialize agents with RAG
        self._initialize_agents()
        
        print(f"🚀 Starting 4-Agent Workflow: {workflow_id}")
        print(f"📝 Sample Log: {sample_log[:100]}...")
        
        # Main workflow loop with feedback
        while state.current_iteration < max_iterations and not state.workflow_completed:
            state.current_iteration += 1
            print(f"\n🔄 Iteration {state.current_iteration}/{max_iterations}")
            
            try:
                # Execute agents in sequence
                state = self._execute_agent_sequence(state)
                
                # Check if we need to regenerate
                if self._should_regenerate(state):
                    print("🔄 Regeneration needed - providing feedback to Agent02")
                    state = self._prepare_regeneration_feedback(state)
                else:
                    state.workflow_completed = True
                    state.success = True
                    print("✅ Workflow completed successfully!")
                    
            except Exception as e:
                print(f"❌ Workflow error: {str(e)}")
                state.workflow_completed = True
                state.success = False
                break
        
        # Store workflow history
        self.workflow_history.append(state)
        
        return state
    
    def _initialize_agents(self):
        """Initialize Agent01 and Agent02 with RAG system"""
        if not self.agent01 or not self.agent02:
            # Create RAG function for agents
            def rag_function(query: str, log_format: str = None) -> str:
                try:
                    if log_format:
                        # Search for format-specific snippets
                        results = self.rag_system.search_vrl_snippets(query, log_format=log_format)
                    else:
                        # General search
                        results = self.rag_system.search_vrl_snippets(query)
                    
                    if results and len(results) > 0:
                        # Combine top results
                        context_parts = []
                        for result in results[:3]:  # Top 3 results
                            context_parts.append(result.get('content', ''))
                        return "\n\n".join(context_parts)
                    else:
                        return "No relevant context found."
                except Exception as e:
                    return f"RAG search error: {str(e)}"
            
            # Initialize agents
            self.agent01 = SimpleLogParsingAgent(rag_function)
            self.agent02 = SimpleLogParsingAgent(rag_function)
    
    def _execute_agent_sequence(self, state: WorkflowState) -> WorkflowState:
        """Execute the sequence: Agent01 → Agent02 → Agent03 → Agent04"""
        
        # Agent01: Identify log type, format
        if not state.agent01_result:
            state.agent01_result = self._execute_agent01(state.sample_log)
        
        # Agent02: Build VRL Parser (with feedback if needed)
        if not state.agent02_result or self._should_regenerate_vrl(state):
            state.agent02_result = self._execute_agent02(
                state.sample_log, 
                state.agent01_result.result if state.agent01_result else {},
                state.agent03_feedback,
                state.agent04_feedback
            )
        
        # Agent03: Validate VRL via Docker
        if state.agent02_result and state.agent02_result.status == AgentStatus.COMPLETED:
            vrl_code = state.agent02_result.result.get('vrl_code', '')
            state.agent03_result = self._execute_agent03(vrl_code, state.sample_log)
            
            # Agent04: Check Mappings (only if validation passed)
            if state.agent03_result and state.agent03_result.result.get('valid', False):
                state.agent04_result = self._execute_agent04(vrl_code, state.sample_log, state.agent01_result.result if state.agent01_result else {})
        
        return state
    
    def _execute_agent01(self, sample_log: str) -> AgentResult:
        """Execute Agent01: Log identification"""
        print("🔍 Agent01: Identifying log type and format...")
        start_time = time.time()
        
        try:
            # Use log_analyzer for format detection
            log_format = identify_log_type(sample_log)
            
            # Use Agent01 for detailed classification
            classification = self.agent01.classify_log(sample_log)
            
            result = {
                "log_format": log_format,
                "classification": classification,
                "confidence": "high" if log_format != "unknown" else "low"
            }
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_id="Agent01",
                status=AgentStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                feedback=f"Identified as {log_format} format"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResult(
                agent_id="Agent01",
                status=AgentStatus.FAILED,
                result={},
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _execute_agent02(self, sample_log: str, agent01_result: Dict[str, Any], 
                        agent03_feedback: Optional[str], agent04_feedback: Optional[str]) -> AgentResult:
        """Execute Agent02: VRL generation with feedback"""
        print("🔧 Agent02: Building VRL parser...")
        start_time = time.time()
        
        try:
            # Prepare feedback context
            feedback_context = ""
            if agent03_feedback:
                feedback_context += f"Validation Feedback: {agent03_feedback}\n"
            if agent04_feedback:
                feedback_context += f"Mapping Feedback: {agent04_feedback}\n"
            
            # Generate VRL with feedback
            vrl_result = self.agent02.generate_vrl(sample_log, agent01_result, feedback_context)
            
            execution_time = time.time() - start_time
            
            return AgentResult(
                agent_id="Agent02",
                status=AgentStatus.COMPLETED,
                result=vrl_result,
                execution_time=execution_time,
                feedback="VRL generated with feedback integration"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResult(
                agent_id="Agent02",
                status=AgentStatus.FAILED,
                result={},
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _execute_agent03(self, vrl_code: str, sample_log: str) -> AgentResult:
        """Execute Agent03: VRL validation via Docker with comprehensive feedback"""
        print("🐳 Agent03: Validating VRL via Docker...")
        start_time = time.time()
        
        try:
            validation_result = self.agent03.validate_vrl(vrl_code, sample_log)
            
            execution_time = time.time() - start_time
            
            # Check if validation passed
            if validation_result.get('valid', False):
                print("✅ Agent03: VRL validation passed!")
                feedback = validation_result.get('feedback', 'VRL validation successful')
                status = AgentStatus.COMPLETED
            else:
                print("❌ Agent03: VRL validation failed!")
                feedback = validation_result.get('feedback', 'VRL validation failed')
                status = AgentStatus.FAILED
            
            return AgentResult(
                agent_id="Agent03",
                status=status,
                result=validation_result,
                execution_time=execution_time,
                feedback=feedback
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_feedback = f"❌ Agent03 Docker validation failed: {str(e)}\n"
            error_feedback += "🔧 Suggestions:\n"
            error_feedback += "- Check Docker is running\n"
            error_feedback += "- Verify docker-compose configuration\n"
            error_feedback += "- Check Vector configuration files\n"
            
            return AgentResult(
                agent_id="Agent03",
                status=AgentStatus.FAILED,
                result={"error": str(e)},
                error_message=str(e),
                execution_time=execution_time,
                feedback=error_feedback
            )
    
    def _execute_agent04(self, vrl_code: str, sample_log: str, agent01_result: Dict[str, Any]) -> AgentResult:
        """Execute Agent04: Mapping validation"""
        print("📊 Agent04: Checking VRL mappings...")
        start_time = time.time()
        
        try:
            log_format = agent01_result.get('log_format', 'unknown')
            mapping_result = self.agent04.check_vrl_mappings(vrl_code, sample_log, log_format)
            
            execution_time = time.time() - start_time
            feedback = self.agent04.get_mapping_feedback(mapping_result)
            
            return AgentResult(
                agent_id="Agent04",
                status=AgentStatus.COMPLETED,
                result=mapping_result,
                execution_time=execution_time,
                feedback=feedback
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResult(
                agent_id="Agent04",
                status=AgentStatus.FAILED,
                result={},
                error_message=str(e),
                execution_time=execution_time
            )
    
    def _should_regenerate(self, state: WorkflowState) -> bool:
        """Determine if VRL needs regeneration based on Agent03 and Agent04 results"""
        
        # Check Agent03 (validation)
        if state.agent03_result:
            if not state.agent03_result.result.get('valid', False):
                return True
        
        # Check Agent04 (mapping quality)
        if state.agent04_result:
            if state.agent04_result.result.get('needs_regeneration', False):
                return True
        
        return False
    
    def _should_regenerate_vrl(self, state: WorkflowState) -> bool:
        """Check if Agent02 needs to regenerate VRL"""
        # Regenerate if we have feedback from Agent03 or Agent04
        return bool(state.agent03_feedback or state.agent04_feedback)
    
    def _prepare_regeneration_feedback(self, state: WorkflowState) -> WorkflowState:
        """Prepare feedback for Agent02 regeneration"""
        
        # Collect feedback from Agent03 and Agent04
        if state.agent03_result:
            state.agent03_feedback = state.agent03_result.feedback
        
        if state.agent04_result:
            state.agent04_feedback = state.agent04_result.feedback
        
        # Reset Agent02 result to trigger regeneration
        state.agent02_result = None
        
        return state
    
    def get_workflow_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """Get a summary of the workflow execution"""
        
        summary = {
            "workflow_id": state.workflow_id,
            "success": state.success,
            "iterations": state.current_iteration,
            "total_time": sum([
                state.agent01_result.execution_time if state.agent01_result else 0,
                state.agent02_result.execution_time if state.agent02_result else 0,
                state.agent03_result.execution_time if state.agent03_result else 0,
                state.agent04_result.execution_time if state.agent04_result else 0
            ]),
            "agents": {
                "Agent01": {
                    "status": state.agent01_result.status.value if state.agent01_result else "not_run",
                    "result": state.agent01_result.result if state.agent01_result else {},
                    "feedback": state.agent01_result.feedback if state.agent01_result else None
                },
                "Agent02": {
                    "status": state.agent02_result.status.value if state.agent02_result else "not_run",
                    "result": state.agent02_result.result if state.agent02_result else {},
                    "feedback": state.agent02_result.feedback if state.agent02_result else None
                },
                "Agent03": {
                    "status": state.agent03_result.status.value if state.agent03_result else "not_run",
                    "result": state.agent03_result.result if state.agent03_result else {},
                    "feedback": state.agent03_result.feedback if state.agent03_result else None
                },
                "Agent04": {
                    "status": state.agent04_result.status.value if state.agent04_result else "not_run",
                    "result": state.agent04_result.result if state.agent04_result else {},
                    "feedback": state.agent04_result.feedback if state.agent04_result else None
                }
            },
            "final_vrl": state.final_vrl,
            "log_sample": state.sample_log
        }
        
        return summary


def create_four_agent_orchestrator(rag_system: CompleteRAGSystem) -> FourAgentOrchestrator:
    """Factory function to create the 4-agent orchestrator"""
    return FourAgentOrchestrator(rag_system)


# Test function
if __name__ == "__main__":
    # This would need a proper RAG system to test
    print("Four-Agent Orchestrator created successfully!")
    print("Use with: orchestrator.execute_workflow(sample_log)")

