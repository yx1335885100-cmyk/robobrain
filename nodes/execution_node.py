# -*- coding: utf-8 -*-
"""
Execution Node - 执行节点
负责任务和技能的执行
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import RobotState, BrainPhase, TaskStatus


@dataclass
class ExecutionConfig:
    """执行配置"""
    timeout: float = 60.0
    max_retries: int = 3
    enable_feedback: bool = True


class ExecutionNode:
    """
    执行节点
    
    负责：
    - 技能调用
    - 动作执行
    - 执行监控
    - 结果收集
    """
    
    def __init__(self, config: ExecutionConfig = None):
        """初始化执行节点"""
        self.config = config or ExecutionConfig()
        
        # 技能注册表
        self._skills: Dict[str, Any] = {}
        
        # ROS2 桥接
        self._ros2_bridge = None
        
        # 回调
        self._callbacks: List[Callable] = []
    
    def register_skill(self, name: str, skill_class: Any):
        """注册技能"""
        self._skills[name] = skill_class
    
    def set_ros2_bridge(self, bridge: Any):
        """设置 ROS2 桥接"""
        self._ros2_bridge = bridge
    
    def __call__(self, state: RobotState) -> Dict:
        """LangGraph 节点入口"""
        return self.process(state)
    
    def process(self, state: RobotState) -> Dict:
        """
        处理执行
        
        Args:
            state: 当前状态
            
        Returns:
            状态更新
        """
        start_time = time.time()
        
        # 获取当前任务
        current_task = state["tasks"].get("running_task")
        
        if not current_task:
            return {
                "current_phase": BrainPhase.EXECUTION.value,
                "next_node": "feedback"
            }
        
        # 执行任务
        result = self._execute_task(current_task, state)
        
        # 构建状态更新
        execution_time = time.time() - start_time
        
        updates = {
            "current_phase": BrainPhase.EXECUTION.value,
            "last_update_time": time.time(),
            "execution": {
                **state["execution"],
                "is_executing": False,
                "current_skill": current_task.get("skill"),
                "last_result": result,
                "action_results": state["execution"]["action_results"] + [result]
            },
            "tasks": {
                **state["tasks"],
                "running_task": None,
                "current_task_status": "completed" if result.get("success") else "failed"
            },
            "next_node": "feedback"
        }
        
        # 如果执行成功，添加到已完成列表
        if result.get("success"):
            completed_task = {**current_task, "status": TaskStatus.COMPLETED.value}
            updates["tasks"]["completed_tasks"] = state["tasks"]["completed_tasks"] + [completed_task]
        else:
            failed_task = {**current_task, "status": TaskStatus.FAILED.value, "error": result.get("error")}
            updates["tasks"]["failed_tasks"] = state["tasks"]["failed_tasks"] + [failed_task]
            updates["has_error"] = True
            updates["error_message"] = result.get("error")
        
        self._trigger_callbacks(state, updates)
        
        return updates
    
    def _execute_task(self, task: Dict, state: RobotState) -> Dict:
        """
        执行任务
        
        Args:
            task: 任务定义
            state: 当前状态
            
        Returns:
            执行结果
        """
        skill_name = task.get("skill")
        parameters = task.get("parameters", {})
        
        # 获取技能
        skill_class = self._skills.get(skill_name)
        
        if skill_class is None:
            return self._simulate_execution(task)
        
        try:
            # 实例化技能
            if isinstance(skill_class, type):
                skill = skill_class()
            else:
                skill = skill_class
            
            # 执行技能
            if asyncio.iscoroutinefunction(skill.execute):
                # 异步执行
                loop = asyncio.new_event_loop()
                result = loop.run_until_complete(skill.execute(parameters, state))
                loop.close()
            else:
                result = skill.execute(parameters, state)
            
            # 处理结果
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result if isinstance(result, dict) else {'success': False}
            
            return result_dict
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _simulate_execution(self, task: Dict) -> Dict:
        """模拟执行（用于测试）"""
        skill_name = task.get("skill", "unknown")
        
        # 模拟执行时间
        time.sleep(0.1)
        
        # 根据技能类型返回模拟结果
        if skill_name == "vln":
            return {
                "success": True,
                "data": {
                    "final_position": [1.0, 2.0, 0.0],
                    "path_completed": True
                },
                "feedback": {"message": "Navigation completed successfully"}
            }
        elif skill_name == "vla":
            return {
                "success": True,
                "data": {
                    "action": "grasp",
                    "object": "target_object",
                    "final_pose": {"position": [0.4, 0.0, 0.8]}
                },
                "feedback": {"message": "Manipulation completed successfully"}
            }
        else:
            return {
                "success": True,
                "data": {},
                "feedback": {"message": f"Skill {skill_name} executed"}
            }
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, state: RobotState, updates: Dict):
        """触发回调"""
        for callback in self._callbacks:
            try:
                callback(state, updates)
            except Exception as e:
                print(f"[ExecutionNode] Callback error: {e}")


# ==================== LangGraph 节点函数 ====================

def execution_node(state: RobotState) -> Dict:
    """LangGraph 执行节点函数"""
    node = ExecutionNode()
    return node.process(state)
