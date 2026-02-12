# -*- coding: utf-8 -*-
"""
Planning Agent - 规划 Agent
专门处理任务规划的 Agent
"""

from typing import Dict, List, Optional, Any
import json

try:
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


PLANNING_SYSTEM_PROMPT = """你是一个机器人任务规划专家 Agent。
你的职责是：
1. 分析用户指令和目标
2. 将高层目标分解为可执行的子任务
3. 确定任务执行的顺序和依赖关系
4. 分配适当的技能和资源

请以 JSON 格式输出任务规划。"""


class PlanningAgent:
    """
    规划 Agent
    
    专门处理规划相关任务：
    - 目标分解
    - 任务排序
    - 资源分配
    - 约束处理
    """
    
    def __init__(self, llm=None):
        """
        初始化规划 Agent
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        self._plan_history: List[Dict] = []
    
    def process(self, state: Dict) -> Dict:
        """
        处理规划任务
        
        Args:
            state: 当前状态
            
        Returns:
            规划结果
        """
        goal = state.get("goal") or state.get("user_input")
        perception = state.get("perception", {})
        
        if self.llm:
            plan = self._plan_with_llm(goal, perception)
        else:
            plan = self._plan_with_rules(goal, perception)
        
        # 记录历史
        self._plan_history.append({
            "goal": goal,
            "plan": plan,
            "timestamp": __import__('time').time()
        })
        
        return {
            "global_plan": plan.get("tasks", []),
            "tasks": {
                **state.get("tasks", {}),
                "pending_tasks": plan.get("tasks", [])
            }
        }
    
    def _plan_with_llm(self, goal: str, perception: Dict) -> Dict:
        """使用 LLM 进行规划"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return self._plan_with_rules(goal, perception)
        
        try:
            prompt = f"""根据以下信息制定任务规划：

目标：{goal}
感知信息：{json.dumps(perception, ensure_ascii=False)}

请输出 JSON 格式的任务列表：
{{
    "tasks": [
        {{
            "name": "任务名称",
            "skill": "技能名称",
            "parameters": {{}},
            "priority": 1-3
        }}
    ]
}}"""

            response = self.llm.invoke([
                SystemMessage(content=PLANNING_SYSTEM_PROMPT),
                HumanMessage(content=prompt)
            ])
            
            # 解析响应
            content = response.content
            if "```json" in content:
                json_str = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                json_str = content.split("```")[1].split("```")[0]
            else:
                json_str = content
            
            return json.loads(json_str.strip())
            
        except Exception as e:
            print(f"[PlanningAgent] LLM planning error: {e}")
            return self._plan_with_rules(goal, perception)
    
    def _plan_with_rules(self, goal: str, perception: Dict) -> Dict:
        """基于规则的规划"""
        import time
        
        tasks = []
        goal_lower = (goal or "").lower()
        
        if any(word in goal_lower for word in ['导航', '去', 'navigate']):
            tasks.append({
                "id": f"task_{int(time.time()*1000)}",
                "name": "navigation",
                "skill": "vln",
                "parameters": {"instruction": goal},
                "priority": 1
            })
        elif any(word in goal_lower for word in ['抓', '拿', 'grasp']):
            tasks.append({
                "id": f"task_{int(time.time()*1000)}",
                "name": "manipulation",
                "skill": "vla",
                "parameters": {"instruction": goal},
                "priority": 1
            })
        else:
            tasks.append({
                "id": f"task_{int(time.time()*1000)}",
                "name": "general",
                "skill": "vla",
                "parameters": {"instruction": goal},
                "priority": 2
            })
        
        return {"tasks": tasks}
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取规划历史"""
        return self._plan_history[-limit:]
