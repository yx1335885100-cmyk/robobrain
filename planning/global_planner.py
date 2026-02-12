# -*- coding: utf-8 -*-
"""
Global Planner - 全局规划器
负责长期目标的分解和全局任务规划
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json


class PlanStatus(Enum):
    """规划状态"""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class GlobalPlan:
    """全局规划"""
    id: str
    goal: str
    sub_goals: List[Dict] = field(default_factory=list)
    current_step: int = 0
    status: PlanStatus = PlanStatus.PENDING
    created_at: float = field(default_factory=time.time)
    estimated_duration: float = 0.0
    priority: int = 2
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'goal': self.goal,
            'sub_goals': self.sub_goals,
            'current_step': self.current_step,
            'status': self.status.value,
            'created_at': self.created_at,
            'estimated_duration': self.estimated_duration,
            'priority': self.priority
        }


class GlobalPlanner:
    """
    全局规划器
    
    负责长期目标的分解和全局任务规划
    
    Features:
        - 目标分解
        - 任务序列生成
        - 资源预估
        - 规划缓存
        - 动态调整
    """
    
    def __init__(self):
        """初始化全局规划器"""
        self._plans: Dict[str, GlobalPlan] = {}
        self._current_plan: Optional[GlobalPlan] = None
        
        # 目标模板库
        self._goal_templates: Dict[str, Dict] = self._init_goal_templates()
        
        # 规划历史
        self._planning_history: List[Dict] = []
        
        # 回调
        self._plan_callbacks: List[Any] = []
    
    def _init_goal_templates(self) -> Dict[str, Dict]:
        """初始化目标模板"""
        return {
            'fetch_object': {
                'sub_goals': [
                    {'type': 'perception', 'description': 'Locate the object'},
                    {'type': 'navigation', 'description': 'Navigate to object location'},
                    {'type': 'manipulation', 'description': 'Grasp the object'},
                    {'type': 'navigation', 'description': 'Return to original location'}
                ],
                'estimated_duration': 60.0
            },
            'explore_room': {
                'sub_goals': [
                    {'type': 'perception', 'description': 'Scan the environment'},
                    {'type': 'navigation', 'description': 'Navigate through the room'},
                    {'type': 'perception', 'description': 'Build room map'}
                ],
                'estimated_duration': 120.0
            },
            'deliver_object': {
                'sub_goals': [
                    {'type': 'perception', 'description': 'Locate the object'},
                    {'type': 'manipulation', 'description': 'Pick up the object'},
                    {'type': 'navigation', 'description': 'Navigate to target location'},
                    {'type': 'manipulation', 'description': 'Place the object'}
                ],
                'estimated_duration': 90.0
            },
            'follow_instruction': {
                'sub_goals': [
                    {'type': 'perception', 'description': 'Understand the instruction'},
                    {'type': 'planning', 'description': 'Generate action plan'},
                    {'type': 'execution', 'description': 'Execute the plan'}
                ],
                'estimated_duration': 45.0
            }
        }
    
    async def plan(self, goal: str, context: Optional[Dict] = None) -> GlobalPlan:
        """
        创建全局规划
        
        Args:
            goal: 目标描述
            context: 规划上下文
            
        Returns:
            全局规划对象
        """
        plan_id = f"plan_{int(time.time()*1000)}"
        
        # 分析目标类型
        goal_type = self._analyze_goal_type(goal)
        
        # 获取模板
        template = self._goal_templates.get(goal_type, self._goal_templates['follow_instruction'])
        
        # 创建规划
        plan = GlobalPlan(
            id=plan_id,
            goal=goal,
            sub_goals=template['sub_goals'].copy(),
            estimated_duration=template['estimated_duration']
        )
        
        # 根据上下文调整
        if context:
            plan = await self._adjust_plan_for_context(plan, context)
        
        # 存储
        self._plans[plan_id] = plan
        self._current_plan = plan
        
        # 记录历史
        self._planning_history.append({
            'timestamp': time.time(),
            'goal': goal,
            'plan_id': plan_id,
            'sub_goals_count': len(plan.sub_goals)
        })
        
        return plan
    
    def _analyze_goal_type(self, goal: str) -> str:
        """分析目标类型"""
        goal_lower = goal.lower()
        
        if any(word in goal_lower for word in ['拿', '取', 'fetch', 'get', 'bring']):
            return 'fetch_object'
        elif any(word in goal_lower for word in ['探索', 'explore', 'scan', '扫描']):
            return 'explore_room'
        elif any(word in goal_lower for word in ['送', '递', 'deliver', 'bring to']):
            return 'deliver_object'
        else:
            return 'follow_instruction'
    
    async def _adjust_plan_for_context(self, plan: GlobalPlan, context: Dict) -> GlobalPlan:
        """根据上下文调整规划"""
        # 检查机器人状态
        robot_state = context.get('robot_state', {})
        
        # 如果已经在目标位置附近，可以跳过导航步骤
        # 这里可以添加更多上下文相关的调整逻辑
        
        return plan
    
    def get_plan(self, plan_id: str) -> Optional[GlobalPlan]:
        """获取规划"""
        return self._plans.get(plan_id)
    
    def get_current_plan(self) -> Optional[GlobalPlan]:
        """获取当前规划"""
        return self._current_plan
    
    def update_plan_progress(self, plan_id: str, step: int) -> bool:
        """更新规划进度"""
        plan = self._plans.get(plan_id)
        if plan:
            plan.current_step = step
            return True
        return False
    
    def advance_plan(self, plan_id: str) -> bool:
        """推进规划"""
        plan = self._plans.get(plan_id)
        if plan and plan.current_step < len(plan.sub_goals):
            plan.current_step += 1
            return True
        return False
    
    def complete_plan(self, plan_id: str, success: bool = True):
        """完成规划"""
        plan = self._plans.get(plan_id)
        if plan:
            plan.status = PlanStatus.COMPLETED if success else PlanStatus.FAILED
            if plan_id == self._current_plan.id if self._current_plan else False:
                self._current_plan = None
    
    def abort_plan(self, plan_id: str):
        """中止规划"""
        plan = self._plans.get(plan_id)
        if plan:
            plan.status = PlanStatus.ABORTED
    
    def get_next_sub_goal(self, plan_id: str) -> Optional[Dict]:
        """获取下一个子目标"""
        plan = self._plans.get(plan_id)
        if plan and plan.current_step < len(plan.sub_goals):
            return plan.sub_goals[plan.current_step]
        return None
    
    def add_goal_template(self, name: str, template: Dict):
        """添加目标模板"""
        self._goal_templates[name] = template
    
    def get_planning_history(self, limit: int = 50) -> List[Dict]:
        """获取规划历史"""
        return self._planning_history[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        total = len(self._plans)
        completed = sum(1 for p in self._plans.values() if p.status == PlanStatus.COMPLETED)
        failed = sum(1 for p in self._plans.values() if p.status == PlanStatus.FAILED)
        
        return {
            'total_plans': total,
            'completed': completed,
            'failed': failed,
            'success_rate': completed / total if total > 0 else 0
        }
