# -*- coding: utf-8 -*-
"""
Local Planner - 局部规划器
负责短期动作序列生成和实时规划调整
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import math


@dataclass
class LocalPlan:
    """局部规划"""
    id: str
    parent_plan_id: str
    actions: List[Dict] = field(default_factory=list)
    current_action_index: int = 0
    constraints: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'parent_plan_id': self.parent_plan_id,
            'actions': self.actions,
            'current_action_index': self.current_action_index,
            'constraints': self.constraints,
            'created_at': self.created_at
        }


class LocalPlanner:
    """
    局部规划器
    
    负责短期动作序列生成和实时规划调整
    
    Features:
        - 动作序列生成
        - 实时调整
        - 约束处理
        - 动作依赖管理
        - 重规划
    """
    
    def __init__(self):
        """初始化局部规划器"""
        self._local_plans: Dict[str, LocalPlan] = {}
        
        # 动作库
        self._action_library = self._init_action_library()
        
        # 约束处理器
        self._constraints: Dict = {}
    
    def _init_action_library(self) -> Dict[str, Dict]:
        """初始化动作库"""
        return {
            'move_to': {
                'params': ['target', 'speed'],
                'preconditions': ['can_move'],
                'duration': 5.0
            },
            'grasp': {
                'params': ['object', 'approach_direction'],
                'preconditions': ['hand_empty', 'object_reachable'],
                'duration': 3.0
            },
            'place': {
                'params': ['position', 'orientation'],
                'preconditions': ['holding_object'],
                'duration': 3.0
            },
            'perceive': {
                'params': ['target', 'mode'],
                'preconditions': [],
                'duration': 1.0
            },
            'speak': {
                'params': ['message'],
                'preconditions': [],
                'duration': 2.0
            },
            'wait': {
                'params': ['duration'],
                'preconditions': [],
                'duration': 1.0
            }
        }
    
    async def plan(self, sub_goal: Dict, context: Optional[Dict] = None,
                  parent_plan_id: str = "") -> LocalPlan:
        """
        创建局部规划
        
        Args:
            sub_goal: 子目标
            context: 规划上下文
            parent_plan_id: 父规划ID
            
        Returns:
            局部规划对象
        """
        plan_id = f"local_{int(time.time()*1000)}"
        
        # 根据子目标类型生成动作序列
        actions = await self._generate_actions(sub_goal, context)
        
        # 应用约束
        actions = self._apply_constraints(actions, context)
        
        # 创建规划
        plan = LocalPlan(
            id=plan_id,
            parent_plan_id=parent_plan_id,
            actions=actions,
            constraints=context.get('constraints', {}) if context else {}
        )
        
        self._local_plans[plan_id] = plan
        
        return plan
    
    async def _generate_actions(self, sub_goal: Dict, context: Optional[Dict]) -> List[Dict]:
        """生成动作序列"""
        goal_type = sub_goal.get('type', 'unknown')
        description = sub_goal.get('description', '')
        
        actions = []
        
        if goal_type == 'perception':
            actions = [
                {'type': 'perceive', 'params': {'target': 'scene', 'mode': 'full'}},
            ]
        
        elif goal_type == 'navigation':
            actions = [
                {'type': 'perceive', 'params': {'target': 'environment', 'mode': 'scan'}},
                {'type': 'move_to', 'params': {'target': 'goal', 'speed': 0.5}}
            ]
        
        elif goal_type == 'manipulation':
            actions = [
                {'type': 'perceive', 'params': {'target': 'object', 'mode': 'locate'}},
                {'type': 'move_to', 'params': {'target': 'object', 'speed': 0.3}},
                {'type': 'grasp', 'params': {'object': 'target'}},
            ]
        
        elif goal_type == 'execution':
            actions = [
                {'type': 'perceive', 'params': {'target': 'environment', 'mode': 'check'}},
                {'type': 'move_to', 'params': {'target': 'execution_point', 'speed': 0.3}},
            ]
        
        else:
            # 默认动作序列
            actions = [
                {'type': 'perceive', 'params': {}},
                {'type': 'wait', 'params': {'duration': 1.0}}
            ]
        
        # 添加动作ID和依赖
        for i, action in enumerate(actions):
            action['id'] = f"action_{i}"
            action['dependencies'] = [f"action_{i-1}"] if i > 0 else []
            action['status'] = 'pending'
        
        return actions
    
    def _apply_constraints(self, actions: List[Dict], context: Optional[Dict]) -> List[Dict]:
        """应用约束"""
        if not context:
            return actions
        
        constraints = context.get('constraints', {})
        
        # 速度约束
        max_velocity = constraints.get('max_velocity', 1.0)
        for action in actions:
            if action['type'] == 'move_to':
                action['params']['speed'] = min(
                    action['params'].get('speed', 0.5),
                    max_velocity
                )
        
        # 碰撞避免
        if constraints.get('avoid_collisions', True):
            for action in actions:
                action['params']['avoid_collisions'] = True
        
        return actions
    
    def get_plan(self, plan_id: str) -> Optional[LocalPlan]:
        """获取规划"""
        return self._local_plans.get(plan_id)
    
    def get_next_action(self, plan_id: str) -> Optional[Dict]:
        """获取下一个动作"""
        plan = self._local_plans.get(plan_id)
        if plan and plan.current_action_index < len(plan.actions):
            return plan.actions[plan.current_action_index]
        return None
    
    def advance_action(self, plan_id: str) -> bool:
        """推进动作"""
        plan = self._local_plans.get(plan_id)
        if plan and plan.current_action_index < len(plan.actions):
            plan.actions[plan.current_action_index]['status'] = 'completed'
            plan.current_action_index += 1
            return True
        return False
    
    async def replan(self, plan_id: str, reason: str, context: Dict) -> Optional[LocalPlan]:
        """
        重新规划
        
        Args:
            plan_id: 规划ID
            reason: 重规划原因
            context: 新上下文
            
        Returns:
            新的局部规划
        """
        old_plan = self._local_plans.get(plan_id)
        if not old_plan:
            return None
        
        # 创建新的子目标
        new_sub_goal = {
            'type': 'recovery',
            'description': f'Replan due to: {reason}'
        }
        
        # 生成新的规划
        return await self.plan(new_sub_goal, context, old_plan.parent_plan_id)
    
    def set_constraint(self, name: str, value: Any):
        """设置约束"""
        self._constraints[name] = value
    
    def get_constraints(self) -> Dict:
        """获取约束"""
        return self._constraints.copy()
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_local_plans': len(self._local_plans),
            'active_plans': sum(1 for p in self._local_plans.values() 
                               if p.current_action_index < len(p.actions))
        }
