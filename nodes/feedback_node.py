# -*- coding: utf-8 -*-
"""
Feedback Node - 反馈节点
负责处理执行反馈和决定下一步
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import RobotState, BrainPhase, TaskStatus, increment_iteration


@dataclass
class FeedbackConfig:
    """反馈配置"""
    enable_reflection: bool = True
    max_retries: int = 3
    reflection_threshold: float = 0.5


class FeedbackNode:
    """
    反馈节点
    
    负责：
    - 分析执行结果
    - 生成反馈报告
    - 决定是否需要重规划
    - 更新系统状态
    """
    
    def __init__(self, config: FeedbackConfig = None, llm=None):
        """初始化反馈节点"""
        self.config = config or FeedbackConfig()
        self.llm = llm
        self._callbacks: List[Callable] = []
    
    def __call__(self, state: RobotState) -> Dict:
        """LangGraph 节点入口"""
        return self.process(state)
    
    def process(self, state: RobotState) -> Dict:
        """
        处理反馈
        
        Args:
            state: 当前状态
            
        Returns:
            状态更新
        """
        # 1. 分析执行结果
        analysis = self._analyze_execution(state)
        
        # 2. 生成反馈
        feedback = self._generate_feedback(state, analysis)
        
        # 3. 决定下一步
        next_action = self._decide_next_action(state, analysis)
        
        # 4. 检查是否完成
        is_complete = self._check_completion(state)
        
        # 5. 构建状态更新
        updates = {
            "current_phase": BrainPhase.FEEDBACK.value,
            "last_update_time": time.time(),
            "execution": {
                **state["execution"],
                "feedback_messages": state["execution"]["feedback_messages"] + [feedback.get("message", "")]
            },
            "next_action": next_action,
            "iteration_count": state["iteration_count"] + 1,
            "next_node": self._determine_next_node(state, is_complete, analysis)
        }
        
        # 如果需要重规划
        if analysis.get("needs_replanning"):
            updates["has_error"] = False
            updates["error_message"] = None
        
        # 如果完成
        if is_complete:
            updates["current_phase"] = BrainPhase.IDLE.value
        
        self._trigger_callbacks(state, updates)
        
        return updates
    
    def _analyze_execution(self, state: RobotState) -> Dict:
        """分析执行结果"""
        last_result = state["execution"].get("last_result")
        
        analysis = {
            "success": True,
            "needs_replanning": False,
            "needs_retry": False,
            "issues": []
        }
        
        if last_result:
            if not last_result.get("success"):
                analysis["success"] = False
                
                error = last_result.get("error", "")
                
                # 判断是否可重试
                if "timeout" in error.lower():
                    analysis["needs_retry"] = True
                elif "collision" in error.lower():
                    analysis["needs_replanning"] = True
                else:
                    analysis["issues"].append(error)
        
        return analysis
    
    def _generate_feedback(self, state: RobotState, analysis: Dict) -> Dict:
        """生成反馈"""
        if analysis["success"]:
            message = "任务执行成功"
            if state["tasks"]["completed_tasks"]:
                completed_count = len(state["tasks"]["completed_tasks"])
                message = f"已完成 {completed_count} 个任务"
        else:
            message = f"执行遇到问题: {', '.join(analysis['issues'])}"
        
        return {
            "message": message,
            "success": analysis["success"],
            "timestamp": time.time()
        }
    
    def _decide_next_action(self, state: RobotState, analysis: Dict) -> str:
        """决定下一步动作"""
        if analysis["needs_retry"]:
            return "retry"
        elif analysis["needs_replanning"]:
            return "replan"
        elif state["tasks"]["pending_tasks"]:
            return "continue"
        elif state["tasks"]["running_task"]:
            return "execute"
        else:
            return "complete"
    
    def _check_completion(self, state: RobotState) -> bool:
        """检查是否完成"""
        # 没有待执行任务
        if not state["tasks"]["pending_tasks"]:
            # 没有正在执行的任务
            if not state["tasks"]["running_task"]:
                return True
        
        # 达到最大迭代次数
        if state["iteration_count"] >= state["max_iterations"]:
            return True
        
        return False
    
    def _determine_next_node(self, state: RobotState, is_complete: bool, 
                            analysis: Dict) -> str:
        """确定下一个节点"""
        if is_complete:
            return "end"
        
        if analysis["needs_replanning"]:
            return "planning"
        
        if state["tasks"]["pending_tasks"]:
            return "scheduling"
        
        return "end"
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, state: RobotState, updates: Dict):
        """触发回调"""
        for callback in self._callbacks:
            try:
                callback(state, updates)
            except Exception as e:
                print(f"[FeedbackNode] Callback error: {e}")


# ==================== LangGraph 节点函数 ====================

def feedback_node(state: RobotState) -> Dict:
    """LangGraph 反馈节点函数"""
    node = FeedbackNode()
    return node.process(state)
