import os
import json
import subprocess
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class HexStrikeEvolutionEngine:
    """
    Handles dynamic learning and execution of any system tool.
    Allows HexStrike to 'evolve' by learning how to use new tools on the fly.
    """
    def __init__(self, storage_dir: str = None):
        if storage_dir is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            storage_dir = os.path.join(base_dir, "data", "evolution")
            
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.learned_tools_file = self.storage_dir / "learned_tools.json"
        self.learned_tools = self._load_learned_tools()

    def _load_learned_tools(self) -> Dict[str, Any]:
        if self.learned_tools_file.exists():
            try:
                with open(self.learned_tools_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def _save_learned_tools(self):
        with open(self.learned_tools_file, 'w') as f:
            json.dump(self.learned_tools, f, indent=4)

    def discover_tool(self, tool_name: str) -> Dict[str, Any]:
        """Check if a tool is installed and learn its usage."""
        if tool_name in self.learned_tools:
            return self.learned_tools[tool_name]

        # Check if installed
        try:
            path_check = subprocess.run(["which", tool_name], capture_output=True, text=True, timeout=5)
            if path_check.returncode != 0:
                return {"error": f"Tool '{tool_name}' not found on the system."}
            
            tool_path = path_check.stdout.strip()
            
            # Learn from --help
            help_output = ""
            try:
                help_check = subprocess.run([tool_name, "--help"], capture_output=True, text=True, timeout=10)
                help_output = help_check.stdout if help_check.stdout else help_check.stderr
            except Exception:
                pass
                
            # Learn from man page if help was insufficient
            man_output = ""
            if not help_output or len(help_output) < 50:
                try:
                    man_check = subprocess.run(["man", tool_name], capture_output=True, text=True, timeout=10)
                    man_output = man_check.stdout
                except Exception:
                    pass
            
            profile = {
                "name": tool_name,
                "path": tool_path,
                "learned_at": __import__("datetime").datetime.now().isoformat(),
                "help_summary": help_output[:2000] if help_output else man_output[:2000]
            }
            
            self.learned_tools[tool_name] = profile
            self.save_profile(tool_name, profile)
            
            return profile
        except Exception as e:
            return {"error": f"Failed to learn tool '{tool_name}': {str(e)}"}

    def save_profile(self, tool_name: str, profile: dict):
        self.learned_tools[tool_name] = profile
        self._save_learned_tools()
        
    def list_learned_tools(self) -> List[str]:
        return list(self.learned_tools.keys())

    def execute_arbitrary_tool(self, tool_name: str, args: List[str]) -> Dict[str, Any]:
        """Execute a tool, learning it first if necessary."""
        if tool_name not in self.learned_tools:
            discovery = self.discover_tool(tool_name)
            if "error" in discovery:
                return discovery
        
        try:
            cmd = [tool_name] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {
                "tool": tool_name,
                "command": " ".join(cmd),
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Tool '{tool_name}' execution timed out."}
        except Exception as e:
            return {"error": f"Failed to execute '{tool_name}': {str(e)}"}

class ExploitChainEngine:
    """
    Advanced Correlation and Chaining Engine (NeuroSploit/Pentest-AI inspired).
    Maps outputs of tools automatically to the inputs of the next phase.
    """
    def __init__(self):
        self.rules = self._load_rules()
        
    def _load_rules(self) -> List[Dict[str, Any]]:
        # Predefined correlation logic
        return [
            {
                "trigger_tool": "nmap",
                "condition": lambda output: "80/tcp" in output or "443/tcp" in output,
                "next_action": "feroxbuster",
                "reasoning": "Web ports discovered, initiating directory brute-forcing."
            },
            {
                "trigger_tool": "feroxbuster",
                "condition": lambda output: ".php?" in output or ".aspx?" in output,
                "next_action": "sqlmap",
                "reasoning": "Dynamic endpoints discovered, testing for SQL injection."
            },
            {
                "trigger_tool": "nuclei",
                "condition": lambda output: "[critical]" in output or "[high]" in output,
                "next_action": "metasploit_auto",
                "reasoning": "High/Critical vulnerabilities found, preparing exploit chain."
            }
        ]

    def correlate_and_suggest(self, tool_name: str, tool_output: str) -> List[Dict[str, Any]]:
        """Analyze tool output and suggest the next chained tools."""
        suggestions = []
        for rule in self.rules:
            if rule["trigger_tool"] == tool_name:
                try:
                    if rule["condition"](tool_output):
                        suggestions.append({
                            "suggested_tool": rule["next_action"],
                            "reason": rule["reasoning"]
                        })
                except Exception as e:
                    logger.error(f"Error evaluating rule for {tool_name}: {e}")
        return suggestions

# Singleton instances
_evolution_engine = None
_chain_engine = None

def get_evolution_engine() -> HexStrikeEvolutionEngine:
    global _evolution_engine
    if _evolution_engine is None:
        _evolution_engine = HexStrikeEvolutionEngine()
    return _evolution_engine

def get_chain_engine() -> ExploitChainEngine:
    global _chain_engine
    if _chain_engine is None:
        _chain_engine = ExploitChainEngine()
    return _chain_engine
