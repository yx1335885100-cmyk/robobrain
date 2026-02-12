# -*- coding: utf-8 -*-
"""
Decision Node - 决策节点
负责路由和条件分支
"""

import time
from typing import Dict, List, Optional, Any, Callable, Literal
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import RobotState, BrainPhase


# 定义可能的下一个节点类型
NextNode = Literal["perception", "planning", "scheduling", "execution", "feedback", "end"]


class DecisionNode:
    """
    决策节点
    
    负责：
    - 路由决策
    - 条件分支
    - 状态检查
    - 流程控制
    """
    
    def __init__(self):
        """初始化决策节点"""
        self._callbacks: List[Callable] = []
    
    def __call__(self, state: RobotState) -> str:
        """LangGraph 条件边入口"""
        return self.route(state)
    
    def route(self, state: RobotState) -> str:
        """
        路由决策
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        # 检查错误状态
        if state.get("has_error"):
            if state.get("retry_count", 0) < 3:
                return "planning"  # 重试
            else:
                return "end"  # 放弃
        
        # 检查是否有明确的下一个节点
        if state.get("next_node"):
            return state["next_node"]
        
        # 基于当前阶段决策
        current_phase = state.get("current_phase", BrainPhase.IDLE.value)
        
        phase_routing = {
            BrainPhase.IDLE.value: "perception",
            BrainPhase.PERCEPTION.value: "planning",
            BrainPhase.PLANNING.value: "scheduling",
            BrainPhase.SCHEDULING.value: "execution",
            BrainPhase.EXECUTION.value: "feedback",
            BrainPhase.FEEDBACK.value: self._route_after_feedback(state)
        }
        
        return phase_routing.get(current_phase, "end")
    
    def _route_after_feedback(self, state: RobotState) -> str:
        """反馈后的路由"""
        # 检查是否完成
        if not state["tasks"]["pending_tasks"] and not state["tasks"]["running_task"]:
            return "end"
        
        # 检查是否需要重规划
        if state.get("next_action") == "replan":
            return "planning"
        
        # 继续下一个任务
        if state["tasks"]["pending_tasks"]:
            return "scheduling"
        
        return "end"


def decision_node(state: RobotState) -> str:
    """
    LangGraph 决策节点函数
    
    用于条件边路由
    """
    node = DecisionNode()
    return node.route(state)


def route_next_node(state: RobotState) -> str:
    """
    路由到下一个节点
    
    这是用于 LangGraph 条件边的路由函数
    
    Args:
        state: 当前状态
        
    Returns:
        下一个节点名称
    """
    # 优先使用状态中指定的下一个节点
    if state.get("next_node"):
        next_node = state["next_node"]
        # 重置 next_node
        if next_node != "end":
            return next_node
        return next_node
    
    # 检查迭代次数
    if state["iteration_count"] >= state["max_iterations"]:
        return "end"
    
    # 基于任务状态路由
    if state["tasks"]["pending_tasks"]:
        return "scheduling"
    
    if state["tasks"]["running_task"]:
        return "execution"
    
    # 默认结束
    return "end"


# ==================== 具体路由函数 ====================

def route_after_perception(state: RobotState) -> str:
    """感知后路由"""
    if state["perception"].get("recognized_speech"):
        return "planning"
    return "perception"  # 继续感知


def route_after_planning(state: RobotState) -> str:
    """规划后路由"""
    if state["tasks"]["pending_tasks"]:
        return "scheduling"
    return "feedback"


def route_after_scheduling(state: RobotState) -> str:
    """调度后路由"""
    if state["tasks"]["running_task"]:
        return "execution"
    return "feedback"


def route_after_execution(state: RobotState) -> str:
    """执行后路由"""
    return "feedback"


def route_after_feedback(state: RobotState) -> str:
    """反馈后路由"""
    next_action = state.get("next_action")
    
    if next_action == "retry":
        return "execution"
    elif next_action == "replan":
        return "planning"
    elif next_action == "continue":
        return "scheduling"
    elif next_action == "complete":
        return "end"
    
    # 检查是否还有任务
    if state["tasks"]["pending_tasks"]:
        return "scheduling"
    
    return "end"
