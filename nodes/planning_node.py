# -*- coding: utf-8 -*-
"""
Planning Node - 规划节点
负责任务规划和分解
"""

import time
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableLambda

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import (
    RobotState, BrainPhase, TaskStatus, TaskPriority,
    update_phase, add_task
)


@dataclass
class PlanningConfig:
    """规划配置"""
    strategy: str = "hierarchical"  # hierarchical, htn, goap
    max_subtasks: int = 10
    use_llm: bool = True
    planning_timeout: float = 30.0


# 任务模板
TASK_TEMPLATES = {
    "navigate": {
        "type": "navigation",
        "skill": "vln",
        "subtasks": ["perceive_environment", "plan_path", "execute_navigation"]
    },
    "grasp": {
        "type": "manipulation",
        "skill": "vla",
        "subtasks": ["locate_object", "approach_object", "grasp_object"]
    },
    "place": {
        "type": "manipulation",
        "skill": "vla",
        "subtasks": ["locate_target", "approach_target", "place_object"]
    },
    "interact": {
        "type": "communication",
        "skill": "dialogue",
        "subtasks": ["listen", "process", "respond"]
    }
}

# 规划提示模板
PLANNING_PROMPT = """你是一个机器人任务规划专家。根据用户的指令，制定详细的执行计划。

用户指令：{instruction}

当前感知信息：
- 语音输入：{speech}
- 检测到的物体：{objects}
- 场景描述：{scene}

请按以下 JSON 格式输出任务规划：
{{
    "analysis": "对指令的分析",
    "tasks": [
        {{
            "name": "任务名称",
            "skill": "使用的技能(vln/vla/dialogue)",
            "parameters": {{}},
            "priority": 1-3,
            "description": "任务描述"
        }}
    ],
    "estimated_duration": "预估时间（秒）"
}}

只输出 JSON，不要其他内容。"""


class PlanningNode:
    """
    规划节点
    
    负责任务规划和分解：
    - 理解用户意图
    - 分解高层目标
    - 生成任务序列
    - 分配任务优先级
    """
    
    def __init__(self, config: PlanningConfig = None, llm=None):
        """
        初始化规划节点
        
        Args:
            config: 规划配置
            llm: 大语言模型实例
        """
        self.config = config or PlanningConfig()
        self.llm = llm
        
        # 任务模板
        self._templates = TASK_TEMPLATES.copy()
        
        # 回调
        self._callbacks: List[Callable] = []
    
    def __call__(self, state: RobotState) -> Dict:
        """LangGraph 节点入口"""
        return self.process(state)
    
    def process(self, state: RobotState) -> Dict:
        """
        处理规划
        
        Args:
            state: 当前状态
            
        Returns:
            状态更新
        """
        start_time = time.time()
        
        # 1. 分析目标
        goal = self._analyze_goal(state)
        
        # 2. 生成规划
        if self.config.use_llm and self.llm:
            plan = self._plan_with_llm(state, goal)
        else:
            plan = self._plan_with_templates(state, goal)
        
        # 3. 创建任务
        tasks = self._create_tasks(plan)
        
        # 4. 构建状态更新
        updates = {
            "current_phase": BrainPhase.PLANNING.value,
            "last_update_time": time.time(),
            "global_plan": plan.get("tasks", []),
            "local_plan": self._decompose_tasks(tasks),
            "tasks": {
                **state["tasks"],
                "pending_tasks": tasks
            }
        }
        
        self._trigger_callbacks(state, updates)
        
        return updates
    
    def _analyze_goal(self, state: RobotState) -> str:
        """分析目标"""
        # 优先使用用户输入
        if state.get("user_input"):
            return state["user_input"]
        
        # 其次使用目标
        if state.get("goal"):
            return state["goal"]
        
        # 使用语音识别结果
        if state["perception"].get("recognized_speech"):
            return state["perception"]["recognized_speech"]
        
        return "等待指令"
    
    def _plan_with_llm(self, state: RobotState, goal: str) -> Dict:
        """使用 LLM 进行规划"""
        if not self.llm:
            return self._plan_with_templates(state, goal)
        
        try:
            # 构建提示
            prompt = PLANNING_PROMPT.format(
                instruction=goal,
                speech=state["perception"].get("recognized_speech", "无"),
                objects=json.dumps(state["perception"].get("detected_objects", []), ensure_ascii=False),
                scene=state["perception"].get("scene_description", "无")
            )
            
            # 调用 LLM
            response = self.llm.invoke([
                SystemMessage(content="你是一个专业的机器人任务规划专家。"),
                HumanMessage(content=prompt)
            ])
            
            # 解析响应
            content = response.content
            
            # 尝试提取 JSON
            try:
                # 查找 JSON 块
                if "```json" in content:
                    json_str = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    json_str = content.split("```")[1].split("```")[0]
                else:
                    json_str = content
                
                plan = json.loads(json_str.strip())
                return plan
            except json.JSONDecodeError:
                # 解析失败，使用模板规划
                return self._plan_with_templates(state, goal)
                
        except Exception as e:
            print(f"[PlanningNode] LLM planning error: {e}")
            return self._plan_with_templates(state, goal)
    
    def _plan_with_templates(self, state: RobotState, goal: str) -> Dict:
        """使用模板进行规划"""
        goal_lower = goal.lower()
        
        tasks = []
        
        # 导航任务
        if any(word in goal_lower for word in ['导航', '去', '走到', 'navigate', 'go to']):
            template = self._templates["navigate"]
            tasks.append({
                "name": "navigation_task",
                "skill": template["skill"],
                "parameters": {"instruction": goal},
                "priority": 1,
                "description": f"导航任务：{goal}"
            })
        
        # 抓取任务
        elif any(word in goal_lower for word in ['抓', '拿', '取', 'grasp', 'pick', 'get']):
            template = self._templates["grasp"]
            tasks.append({
                "name": "grasp_task",
                "skill": template["skill"],
                "parameters": {"instruction": goal},
                "priority": 1,
                "description": f"抓取任务：{goal}"
            })
        
        # 放置任务
        elif any(word in goal_lower for word in ['放', '放置', 'place', 'put']):
            template = self._templates["place"]
            tasks.append({
                "name": "place_task",
                "skill": template["skill"],
                "parameters": {"instruction": goal},
                "priority": 1,
                "description": f"放置任务：{goal}"
            })
        
        # 对话任务
        elif any(word in goal_lower for word in ['说', '告诉', 'speak', 'tell', '回答']):
            template = self._templates["interact"]
            tasks.append({
                "name": "dialogue_task",
                "skill": template["skill"],
                "parameters": {"instruction": goal},
                "priority": 2,
                "description": f"对话任务：{goal}"
            })
        
        # 默认任务
        else:
            tasks.append({
                "name": "general_task",
                "skill": "vla",
                "parameters": {"instruction": goal},
                "priority": 2,
                "description": f"执行任务：{goal}"
            })
        
        return {
            "analysis": f"基于指令 '{goal}' 的任务规划",
            "tasks": tasks,
            "estimated_duration": len(tasks) * 5
        }
    
    def _create_tasks(self, plan: Dict) -> List[Dict]:
        """创建任务列表"""
        tasks = []
        
        for i, task_def in enumerate(plan.get("tasks", [])):
            task = {
                "id": f"task_{int(time.time()*1000)}_{i}",
                "name": task_def.get("name", f"task_{i}"),
                "skill": task_def.get("skill"),
                "parameters": task_def.get("parameters", {}),
                "priority": task_def.get("priority", 2),
                "status": TaskStatus.PENDING.value,
                "description": task_def.get("description", ""),
                "dependencies": [],
                "created_at": time.time()
            }
            tasks.append(task)
        
        return tasks
    
    def _decompose_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """分解任务为动作序列"""
        local_plan = []
        
        for task in tasks:
            # 添加主任务
            local_plan.append({
                "task_id": task["id"],
                "action": "execute_skill",
                "skill": task["skill"],
                "parameters": task["parameters"],
                "status": "pending"
            })
        
        return local_plan
    
    def add_template(self, name: str, template: Dict):
        """添加任务模板"""
        self._templates[name] = template
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, state: RobotState, updates: Dict):
        """触发回调"""
        for callback in self._callbacks:
            try:
                callback(state, updates)
            except Exception as e:
                print(f"[PlanningNode] Callback error: {e}")


# ==================== LangGraph 节点函数 ====================

def planning_node(state: RobotState) -> Dict:
    """
    LangGraph 规划节点函数
    """
    node = PlanningNode()
    return node.process(state)


planning_runnable = RunnableLambda(planning_node)
