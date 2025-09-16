"""
Simplified Log Parsing Agent Framework
A working implementation without complex Pydantic issues
"""

from typing import Dict, Any, List, Optional
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import json
import re


class SimpleLogParsingAgent:
    """Simplified agent for log parsing using LangChain patterns"""
    
    def __init__(self, rag_function, classification_model: str = "llama3.2:latest", 
                 vrl_model: str = "phi3:mini"):
        self.rag_function = rag_function
        self.classification_model = classification_model
        self.vrl_model = vrl_model
        
        # Initialize LLMs
        self.classification_llm = Ollama(model=classification_model)
        self.vrl_llm = Ollama(model=vrl_model)
        
        # Create prompts
        self.classification_prompt = PromptTemplate.from_template(
            "You are an expert log classifier. Return ONLY a JSON object with keys: "
            "log_type, log_format, log_source, product, vendor.\n"
            "Analyze this log and fill values. If unknown, use null.\n"
            "Log:\n{log}\n"
        )
        
        self.ecs_json_prompt = PromptTemplate.from_template(
            "You are Agent A. Produce a VALID ECS JSON object from the raw log. "
            "Return ONLY JSON. No comments.\nContext:\n{ctx}\nLog:\n{log}\n"
        )
        
        self.vrl_prompt = PromptTemplate.from_template(
            "You are Agent B. Generate Vector Remap Language (VRL) to parse the log.\n"
            "Rules:\n"
            "- Output ONLY valid VRL code. No JSON, no explanation, no markdown fences.\n"
            "- Use the field name 'event_data' (with underscore) for intermediate/vendor keys.\n"
            "- Follow professional style like the provided reference examples (no comments about ECS fields).\n"
            "- Do NOT emit map literal blocks like 'event_data { \"k\" => \"v\" }'.\n"
            "  Instead, write assignments per line: .event_data.k = \"v\".\n"
            "- Do not include lines like 'ECS Field', 'Type', 'Description' or any schema prose.\n"
            "Context:\n{ctx}\nLog:\n{log}\n"
        )
        
        # Create chains using RunnableSequence (replaces deprecated LLMChain)
        self.classification_chain = self.classification_prompt | self.classification_llm
        self.ecs_json_chain = self.ecs_json_prompt | self.classification_llm
        self.vrl_chain = self.vrl_prompt | self.vrl_llm
    
    def identify_log(self, raw_log: str) -> Dict[str, Any]:
        """Step 1: Identify log type, format, source, vendor, product using log_analyzer"""
        try:
            # Use the hybrid classification from lc_bridge that includes log_analyzer
            from lc_bridge import classify_log_lc
            return classify_log_lc(raw_log)
        except Exception as e:
            return {"error": f"Log identification failed: {str(e)}"}
    
    def get_rag_context(self, log_profile: Dict[str, Any]) -> str:
        """Step 2: Retrieve relevant context from RAG system"""
        try:
            return self.rag_function(log_profile)
        except Exception as e:
            return f"RAG context retrieval failed: {str(e)}"
    
    def generate_ecs_json(self, context: str, raw_log: str) -> Dict[str, Any]:
        """Step 3a: Generate ECS JSON"""
        try:
            result = self.ecs_json_chain.invoke({"ctx": context, "log": raw_log}).strip()
            # Clean and validate JSON
            cleaned = re.sub(r"^```(?:json)?", "", result).strip()
            brace = cleaned.find("{")
            if brace > 0:
                cleaned = cleaned[brace:]
            return json.loads(cleaned)
        except Exception as e:
            return {"error": f"ECS JSON generation failed: {str(e)}"}
    
    def generate_vrl(self, context: str, raw_log: str) -> str:
        """Step 3b: Generate VRL parser"""
        try:
            result = self.vrl_chain.invoke({"ctx": context, "log": raw_log}).strip()
            return self._sanitize_vrl_output(result)
        except Exception as e:
            return f"VRL generation failed: {str(e)}"
    
    def _sanitize_vrl_output(self, vrl_output: str) -> str:
        """Clean VRL output to remove non-VRL content"""
        lines = vrl_output.split('\n')
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
                not line.startswith('The VRL')):
                vrl_lines.append(line)
        
        return '\n'.join(vrl_lines)
    
    def parse_log(self, raw_log: str, output_type: str = "auto") -> Dict[str, Any]:
        """
        Complete log parsing workflow
        
        Args:
            raw_log: Raw log line to parse
            output_type: "auto", "json", or "vrl"
        
        Returns:
            Dictionary with parsing results
        """
        steps = []
        result = {
            "success": False,
            "raw_log": raw_log,
            "output_type": output_type,
            "steps": steps,
            "final_output": None
        }
        
        try:
            # Step 1: Identify log
            steps.append("🔍 Identifying log type...")
            log_profile = self.identify_log(raw_log)
            if "error" in log_profile:
                result["error"] = log_profile["error"]
                return result
            
            steps.append(f"✅ Identified: {log_profile}")
            result["log_profile"] = log_profile
            
            # Step 2: Get RAG context
            steps.append("📚 Retrieving RAG context...")
            context = self.get_rag_context(log_profile)
            steps.append(f"✅ Context retrieved: {len(context)} characters")
            result["context"] = context
            
            # Step 3: Generate output based on type
            if output_type == "json" or (output_type == "auto" and log_profile.get("log_format") == "json"):
                steps.append("📋 Generating ECS JSON...")
                ecs_json = self.generate_ecs_json(context, raw_log)
                if "error" in ecs_json:
                    result["error"] = ecs_json["error"]
                    return result
                result["final_output"] = ecs_json
                steps.append("✅ ECS JSON generated")
            else:
                steps.append("⚙️ Generating VRL parser...")
                vrl_code = self.generate_vrl(context, raw_log)
                result["final_output"] = vrl_code
                steps.append("✅ VRL parser generated")
            
            result["success"] = True
            
        except Exception as e:
            result["error"] = f"Parsing workflow failed: {str(e)}"
        
        return result
    
    def stream_parse(self, raw_log: str, output_type: str = "auto"):
        """
        Stream the parsing process for real-time updates
        
        Args:
            raw_log: Raw log line to parse
            output_type: "auto", "json", or "vrl"
        
        Yields:
            Dictionary with streaming updates
        """
        yield {"step": "🔍 Starting log parsing workflow...", "raw_log": raw_log}
        
        # Step 1: Identify log
        yield {"step": "🔍 Identifying log type...", "raw_log": raw_log}
        log_profile = self.identify_log(raw_log)
        if "error" in log_profile:
            yield {"error": log_profile["error"], "raw_log": raw_log}
            return
        
        yield {"step": f"✅ Identified: {log_profile}", "log_profile": log_profile, "raw_log": raw_log}
        
        # Step 2: Get RAG context
        yield {"step": "📚 Retrieving RAG context...", "raw_log": raw_log}
        context = self.get_rag_context(log_profile)
        yield {"step": f"✅ Context retrieved: {len(context)} characters", "context": context, "raw_log": raw_log}
        
        # Step 3: Generate output
        if output_type == "json" or (output_type == "auto" and log_profile.get("log_format") == "json"):
            yield {"step": "📋 Generating ECS JSON...", "raw_log": raw_log}
            ecs_json = self.generate_ecs_json(context, raw_log)
            if "error" in ecs_json:
                yield {"error": ecs_json["error"], "raw_log": raw_log}
                return
            yield {"step": "✅ ECS JSON generated", "final_output": ecs_json, "raw_log": raw_log}
        else:
            yield {"step": "⚙️ Generating VRL parser...", "raw_log": raw_log}
            vrl_code = self.generate_vrl(context, raw_log)
            yield {"step": "✅ VRL parser generated", "final_output": vrl_code, "raw_log": raw_log}


def create_simple_agent(rag_function, **kwargs) -> SimpleLogParsingAgent:
    """
    Factory function to create a simple log parsing agent
    
    Args:
        rag_function: Function that takes log profile and returns RAG context
        **kwargs: Additional arguments for agent configuration
    
    Returns:
        Configured SimpleLogParsingAgent instance
    """
    return SimpleLogParsingAgent(rag_function, **kwargs)
