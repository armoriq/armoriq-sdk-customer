"""
Simple data models for ArmorIQ Customer SDK
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class Action:
    """Represents a single action in a plan"""
    tool: str
    params: Dict[str, Any]
    description: Optional[str] = None


@dataclass
class Plan:
    """Represents an execution plan for one or more tools"""
    goal: str
    actions: List[Action]
    plan_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary format"""
        return {
            "goal": self.goal,
            "actions": [
                {
                    "tool": action.tool,
                    "params": action.params,
                    **({"description": action.description} if action.description else {})
                }
                for action in self.actions
            ],
            **({"plan_id": self.plan_id} if self.plan_id else {})
        }


@dataclass
class Token:
    """Represents an access token for tool invocation"""
    token_string: str
    expires_at: Optional[str] = None
    plan_id: Optional[str] = None
    
    def __str__(self) -> str:
        return self.token_string


@dataclass
class ToolResult:
    """Represents the result of a tool invocation"""
    success: bool
    data: Any
    error: Optional[str] = None
    tool_name: Optional[str] = None
    
    def __bool__(self) -> bool:
        """Allow using result in boolean context"""
        return self.success
