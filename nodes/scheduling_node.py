# -*- coding: utf-8 -*-
"""
Scheduling Node - 调度节点
负责任务调度和优先级管理
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import RobotState, BrainPhase, TaskStatus


@dataclass
class SchedulingConfig:
    """调度配置"""
    algorithm: str = "priority_based"  # priority_based, fifo, round_robin
    max_concurrent: int = 1
    enable_aging: bool = True
    starvation_threshold: float = 60.0


class SchedulingNode:
    """
    调度节点
    
    负责：
    - 任务优先级排序
    - 依赖关系解析
    - 资源分配
    - 任务队列管理
    """
    
    def __init__(self, config: SchedulingConfig = None):
        """初始化调度节点"""
        self.config = config or SchedulingConfig()
        self._callbacks: List[Callable] = []
    
    def __call__(self, state: RobotState) -> Dict:
        """LangGraph 节点入口"""
        return self.process(state)
    
    def process(self, state: RobotState) -> Dict:
        """
        处理调度
        
        Args:
            state: 当前状态
            
        Returns:
            状态更新
        """
        # 1. 获取待调度任务
        pending_tasks = state["tasks"]["pending_tasks"]
        
        if not pending_tasks:
            return {
                "current_phase": BrainPhase.SCHEDULING.value,
                "next_node": "feedback"
            }
        
        # 2. 应用调度算法
        scheduled = self._schedule_tasks(pending_tasks)
        
        # 3. 检查依赖
        ready_tasks = self._check_dependencies(scheduled, state)
        
        # 4. 选择下一个执行任务
        next_task = self._select_next_task(ready_tasks)
        
        # 5. 构建状态更新
        updates = {
            "current_phase": BrainPhase.SCHEDULING.value,
            "last_update_time": time.time(),
            "tasks": {
                **state["tasks"],
                "pending_tasks": [t for t in pending_tasks if t["id"] != next_task["id"]] if next_task else pending_tasks,
                "ready_tasks": ready_tasks,
                "running_task": next_task,
                "current_task_id": next_task["id"] if next_task else None,
                "current_task_status": "ready" if next_task else "idle"
            },
            "next_node": "execution" if next_task else "feedback"
        }
        
        self._trigger_callbacks(state, updates)
        
        return updates
    
    def _schedule_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """调度任务排序"""
        if self.config.algorithm == "priority_based":
            return sorted(tasks, key=lambda t: t.get("priority", 2))
        elif self.config.algorithm == "fifo":
            return sorted(tasks, key=lambda t: t.get("created_at", 0))
        else:
            return tasks
    
    def _check_dependencies(self, tasks: List[Dict], state: RobotState) -> List[Dict]:
        """检查任务依赖"""
        completed_ids = {t["id"] for t in state["tasks"]["completed_tasks"]}
        
        ready = []
        for task in tasks:
            deps = task.get("dependencies", [])
            if all(dep_id in completed_ids for dep_id in deps):
                ready.append(task)
        
        return ready
    
    def _select_next_task(self, ready_tasks: List[Dict]) -> Optional[Dict]:
        """选择下一个执行任务"""
        if ready_tasks:
            return ready_tasks[0]
        return None
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, state: RobotState, updates: Dict):
        """触发回调"""
        for callback in self._callbacks:
            try:
                callback(state, updates)
            except Exception as e:
                print(f"[SchedulingNode] Callback error: {e}")


# ==================== LangGraph 节点函数 ====================

def scheduling_node(state: RobotState) -> Dict:
    """LangGraph 调度节点函数"""
    node = SchedulingNode()
    return node.process(state)
