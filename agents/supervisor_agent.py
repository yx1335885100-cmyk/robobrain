# -*- coding: utf-8 -*-
"""
Supervisor Agent - 监督 Agent
协调所有 Agent 的中央控制器
"""

from typing import Dict, List, Optional, Any
import time

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

from .perception_agent import PerceptionAgent
from .planning_agent import PlanningAgent
from .execution_agent import ExecutionAgent


SUPERVISOR_SYSTEM_PROMPT = """你是机器人系统的中央监督 Agent。
你的职责是：
1. 协调各个专业 Agent 的工作
2. 监控整体系统状态
3. 处理异常情况
4. 确保任务顺利完成

你需要做出明智的决策来优化系统性能。"""


class SupervisorAgent:
    """
    监督 Agent
    
    作为中央协调器：
    - 协调各 Agent
    - 监控系统状态
    - 处理异常
    - 优化决策
    """
    
    def __init__(self, llm=None):
        """
        初始化监督 Agent
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        
        # 初始化子 Agent
        self.perception_agent = PerceptionAgent(llm)
        self.planning_agent = PlanningAgent(llm)
        self.execution_agent = ExecutionAgent(llm)
        
        # 监督状态
        self._supervision_log: List[Dict] = []
        self._current_focus: Optional[str] = None
    
    def process(self, state: Dict) -> Dict:
        """
        处理监督任务
        
        Args:
            state: 当前状态
            
        Returns:
            监督决策
        """
        # 分析当前状态
        analysis = self._analyze_state(state)
        
        # 决定下一步行动
        decision = self._make_decision(state, analysis)
        
        # 记录监督日志
        self._supervision_log.append({
            "state_analysis": analysis,
            "decision": decision,
            "timestamp": time.time()
        })
        
        return {
            "next_action": decision.get("action"),
            "next_node": decision.get("node"),
            "supervisor_analysis": analysis
        }
    
    def _analyze_state(self, state: Dict) -> Dict:
        """分析状态"""
        analysis = {
            "has_error": state.get("has_error", False),
            "pending_tasks": len(state.get("tasks", {}).get("pending_tasks", [])),
            "iteration": state.get("iteration_count", 0),
            "current_phase": state.get("current_phase", "idle")
        }
        
        # 使用 LLM 进行深度分析
        if self.llm and analysis["has_error"]:
            analysis["llm_insight"] = self._get_llm_insight(state)
        
        return analysis
    
    def _make_decision(self, state: Dict, analysis: Dict) -> Dict:
        """做出决策"""
        if analysis["has_error"]:
            return {
                "action": "handle_error",
                "node": "feedback",
                "reason": "Error detected, routing to feedback"
            }
        
        if analysis["pending_tasks"] > 0:
            return {
                "action": "continue",
                "node": "scheduling",
                "reason": "Pending tasks available"
            }
        
        if analysis["iteration"] >= state.get("max_iterations", 10):
            return {
                "action": "complete",
                "node": "end",
                "reason": "Max iterations reached"
            }
        
        return {
            "action": "continue",
            "node": "perception",
            "reason": "Continue cognitive cycle"
        }
    
    def _get_llm_insight(self, state: Dict) -> str:
        """使用 LLM 获取洞察"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return ""
        
        try:
            error_msg = state.get("error_message", "Unknown error")
            response = self.llm.invoke([
                SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
                HumanMessage(content=f"分析错误并提供解决建议：{error_msg}")
            ])
            return response.content
        except Exception as e:
            return f"LLM insight error: {e}"
    
    def coordinate(self, agent_name: str, state: Dict) -> Dict:
        """
        协调特定 Agent
        
        Args:
            agent_name: Agent 名称
            state: 当前状态
            
        Returns:
            Agent 处理结果
        """
        if agent_name == "perception":
            return self.perception_agent.process(state)
        elif agent_name == "planning":
            return self.planning_agent.process(state)
        elif agent_name == "execution":
            return self.execution_agent.process(state)
        else:
            return {}
    
    def get_supervision_log(self, limit: int = 10) -> List[Dict]:
        """获取监督日志"""
        return self._supervision_log[-limit:]
