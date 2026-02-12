# -*- coding: utf-8 -*-
"""
Task Planner - 任务规划器
支持全局规划、局部规划、层次化规划、基于目标的任务分解
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class PlanningStrategy(Enum):
    """规划策略枚举"""
    HIERARCHICAL = "hierarchical"    # 层次化规划
    SEQUENTIAL = "sequential"        # 顺序规划
    PARALLEL = "parallel"            # 并行规划
    HTN = "htn"                      # 分层任务网络
    GOAP = "goap"                    # 目标导向行动规划


class TaskType(Enum):
    """任务类型枚举"""
    NAVIGATION = "navigation"        # 导航任务
    MANIPULATION = "manipulation"    # 操作任务
    PERCEPTION = "perception"        # 感知任务
    COMMUNICATION = "communication"  # 通信任务
    COGNITION = "cognition"          # 认知任务
    SKILL = "skill"                  # 技能任务
    COMPOSITE = "composite"          # 复合任务


@dataclass
class PlanningContext:
    """规划上下文"""
    timestamp: float = field(default_factory=time.time)
    robot_state: Dict = field(default_factory=dict)
    environment: Dict = field(default_factory=dict)
    perception_summary: Dict = field(default_factory=dict)
    constraints: Dict = field(default_factory=dict)
    available_skills: List[str] = field(default_factory=list)
    history: List[Dict] = field(default_factory=list)


@dataclass
class Action:
    """动作定义"""
    name: str
    preconditions: Dict = field(default_factory=dict)
    effects: Dict = field(default_factory=dict)
    cost: float = 1.0
    duration: float = 1.0
    skill: Optional[str] = None
    parameters: Dict = field(default_factory=dict)


@dataclass
class Goal:
    """目标定义"""
    name: str
    description: str
    conditions: Dict = field(default_factory=dict)
    priority: int = 2
    deadline: Optional[float] = None


class TaskPlanner:
    """
    任务规划器
    
    提供全局规划、局部规划、任务分解、路径规划等功能
    
    Features:
        - 全局任务规划（长期目标分解）
        - 局部任务规划（短期行动计划）
        - 层次化任务网络（HTN）
        - 目标导向行动规划（GOAP）
        - 任务依赖分析
        - 资源约束处理
        - 动态重规划
    """
    
    def __init__(self, planning_strategy: str = 'hierarchical'):
        """
        初始化任务规划器
        
        Args:
            planning_strategy: 规划策略
        """
        self.strategy = PlanningStrategy(planning_strategy)
        
        # 动作库
        self._actions: Dict[str, Action] = {}
        self._register_default_actions()
        
        # 任务模板库
        self._task_templates: Dict[str, Dict] = {}
        self._register_default_templates()
        
        # 技能映射
        self._skill_mappings: Dict[str, str] = {}
        
        # 规划缓存
        self._planning_cache: Dict[str, List] = {}
        
        # 规划历史
        self._planning_history: List[Dict] = []
        
    def _register_default_actions(self):
        """注册默认动作"""
        # 导航动作
        self._actions['navigate_to'] = Action(
            name='navigate_to',
            preconditions={'can_move': True},
            effects={'at_location': True},
            cost=2.0,
            duration=5.0,
            skill='vln'
        )
        
        # 视觉定位导航动作
        self._actions['vln_navigate'] = Action(
            name='vln_navigate',
            preconditions={'has_visual_target': True},
            effects={'at_target': True},
            cost=3.0,
            duration=8.0,
            skill='vln'
        )
        
        # 视觉语言操作动作
        self._actions['vla_manipulate'] = Action(
            name='vla_manipulate',
            preconditions={'at_target': True, 'has_object': True},
            effects={'object_manipulated': True},
            cost=2.5,
            duration=4.0,
            skill='vla'
        )
        
        # 抓取动作
        self._actions['grasp'] = Action(
            name='grasp',
            preconditions={'hand_empty': True, 'object_reachable': True},
            effects={'object_grasped': True, 'hand_empty': False},
            cost=1.5,
            duration=2.0,
            skill='grasp'
        )
        
        # 放置动作
        self._actions['place'] = Action(
            name='place',
            preconditions={'object_grasped': True},
            effects={'object_placed': True, 'hand_empty': True},
            cost=1.5,
            duration=2.0,
            skill='place'
        )
        
        # 感知动作
        self._actions['perceive'] = Action(
            name='perceive',
            preconditions={},
            effects={'environment_known': True},
            cost=0.5,
            duration=1.0,
            skill='perception'
        )
        
        # 语音识别动作
        self._actions['listen'] = Action(
            name='listen',
            preconditions={},
            effects={'speech_recognized': True},
            cost=0.3,
            duration=0.5,
            skill='asr'
        )
        
        # 语音合成动作
        self._actions['speak'] = Action(
            name='speak',
            preconditions={'has_message': True},
            effects={'message_spoken': True},
            cost=0.3,
            duration=1.0,
            skill='tts'
        )
        
        # 等待动作
        self._actions['wait'] = Action(
            name='wait',
            preconditions={},
            effects={},
            cost=0.1,
            duration=1.0
        )
        
        # 观察动作
        self._actions['observe'] = Action(
            name='observe',
            preconditions={},
            effects={'scene_observed': True},
            cost=0.5,
            duration=2.0,
            skill='vision'
        )
        
    def _register_default_templates(self):
        """注册默认任务模板"""
        # 导航到位置模板
        self._task_templates['navigate'] = {
            'type': TaskType.NAVIGATION,
            'subtasks': [
                {'name': 'perceive_environment', 'action': 'perceive'},
                {'name': 'plan_path', 'action': 'navigate_to'},
                {'name': 'execute_navigation', 'action': 'vln_navigate'}
            ]
        }
        
        # 抓取物体模板
        self._task_templates['pick_up'] = {
            'type': TaskType.MANIPULATION,
            'subtasks': [
                {'name': 'locate_object', 'action': 'observe'},
                {'name': 'approach_object', 'action': 'navigate_to'},
                {'name': 'grasp_object', 'action': 'grasp'}
            ]
        }
        
        # 放置物体模板
        self._task_templates['put_down'] = {
            'type': TaskType.MANIPULATION,
            'subtasks': [
                {'name': 'locate_target', 'action': 'observe'},
                {'name': 'approach_target', 'action': 'navigate_to'},
                {'name': 'place_object', 'action': 'place'}
            ]
        }
        
        # 搬运物体模板
        self._task_templates['transport'] = {
            'type': TaskType.COMPOSITE,
            'subtasks': [
                {'name': 'pick_up_phase', 'template': 'pick_up'},
                {'name': 'transport_phase', 'template': 'navigate'},
                {'name': 'put_down_phase', 'template': 'put_down'}
            ]
        }
        
        # 交互对话模板
        self._task_templates['interact'] = {
            'type': TaskType.COMMUNICATION,
            'subtasks': [
                {'name': 'listen_to_user', 'action': 'listen'},
                {'name': 'process_request', 'action': 'perceive'},
                {'name': 'respond_to_user', 'action': 'speak'}
            ]
        }
        
        # VLN任务模板
        self._task_templates['vln_task'] = {
            'type': TaskType.SKILL,
            'subtasks': [
                {'name': 'observe_scene', 'action': 'observe'},
                {'name': 'parse_instruction', 'action': 'listen'},
                {'name': 'visual_navigation', 'action': 'vln_navigate'}
            ]
        }
        
        # VLA任务模板
        self._task_templates['vla_task'] = {
            'type': TaskType.SKILL,
            'subtasks': [
                {'name': 'perceive_target', 'action': 'observe'},
                {'name': 'parse_instruction', 'action': 'listen'},
                {'name': 'visual_manipulation', 'action': 'vla_manipulate'}
            ]
        }
    
    def register_action(self, action: Action):
        """注册动作"""
        self._actions[action.name] = action
    
    def register_template(self, name: str, template: Dict):
        """注册任务模板"""
        self._task_templates[name] = template
    
    def register_skill_mapping(self, action_name: str, skill_name: str):
        """注册动作到技能的映射"""
        self._skill_mappings[action_name] = skill_name
    
    async def plan_global(self, goal: Optional[str], context: Dict, 
                         current_state: Dict) -> List[Dict]:
        """
        执行全局规划
        
        将高层目标分解为子目标序列
        
        Args:
            goal: 目标描述
            context: 规划上下文
            current_state: 当前机器人状态
            
        Returns:
            全局规划任务列表
        """
        print(f"[TaskPlanner] Starting global planning for goal: {goal}")
        
        start_time = time.time()
        
        # 解析目标
        parsed_goal = self._parse_goal(goal) if goal else None
        
        # 选择规划策略
        if self.strategy == PlanningStrategy.HIERARCHICAL:
            plan = await self._hierarchical_planning(parsed_goal, context, current_state)
        elif self.strategy == PlanningStrategy.HTN:
            plan = await self._htn_planning(parsed_goal, context, current_state)
        elif self.strategy == PlanningStrategy.GOAP:
            plan = await self._goap_planning(parsed_goal, context, current_state)
        else:
            plan = await self._sequential_planning(parsed_goal, context, current_state)
        
        # 记录规划历史
        self._planning_history.append({
            'timestamp': time.time(),
            'goal': goal,
            'strategy': self.strategy.value,
            'plan_length': len(plan),
            'planning_time': time.time() - start_time
        })
        
        return plan
    
    async def plan_local(self, global_plan: List[Dict], context: Dict,
                        constraints: Dict) -> List[Dict]:
        """
        执行局部规划
        
        将全局任务细化为可执行的动作序列
        
        Args:
            global_plan: 全局规划任务列表
            context: 规划上下文
            constraints: 执行约束
            
        Returns:
            局部规划动作列表
        """
        print(f"[TaskPlanner] Starting local planning for {len(global_plan)} global tasks")
        
        local_plan = []
        
        for i, global_task in enumerate(global_plan):
            # 分解任务
            subtasks = await self._decompose_task(global_task, context, constraints)
            
            # 添加执行顺序和依赖
            for j, subtask in enumerate(subtasks):
                subtask['global_task_index'] = i
                subtask['local_task_index'] = j
                
                # 设置依赖关系
                if j > 0:
                    subtask['dependencies'] = [f"subtask_{i}_{j-1}"]
                elif i > 0:
                    subtask['dependencies'] = [f"subtask_{i-1}_end"]
                
                subtask['id'] = f"subtask_{i}_{j}"
                local_plan.append(subtask)
        
        # 应用约束优化
        local_plan = self._apply_constraints(local_plan, constraints)
        
        return local_plan
    
    async def _hierarchical_planning(self, goal: Goal, context: Dict, 
                                    current_state: Dict) -> List[Dict]:
        """层次化规划"""
        if not goal:
            return []
        
        plan = []
        
        # 根据目标类型选择模板
        template_name = self._match_template_for_goal(goal)
        
        if template_name and template_name in self._task_templates:
            template = self._task_templates[template_name]
            
            # 展开模板
            plan = self._expand_template(template, goal, context)
        else:
            # 基于目标生成规划
            plan = await self._generate_plan_from_goal(goal, context, current_state)
        
        return plan
    
    async def _htn_planning(self, goal: Goal, context: Dict, 
                           current_state: Dict) -> List[Dict]:
        """分层任务网络规划"""
        if not goal:
            return []
        
        # HTN方法：递归分解复合任务
        plan = []
        
        # 识别初始复合任务
        initial_tasks = self._identify_initial_tasks(goal)
        
        for task in initial_tasks:
            decomposed = await self._decompose_htn_task(task, context, current_state)
            plan.extend(decomposed)
        
        return plan
    
    async def _goap_planning(self, goal: Goal, context: Dict,
                            current_state: Dict) -> List[Dict]:
        """目标导向行动规划"""
        if not goal:
            return []
        
        # GOAP：从目标状态反向搜索
        plan = []
        current_world_state = self._get_world_state(current_state, context)
        goal_state = goal.conditions
        
        # 反向搜索
        search_result = self._backward_search(current_world_state, goal_state)
        
        if search_result:
            plan = search_result
        
        return plan
    
    async def _sequential_planning(self, goal: Goal, context: Dict,
                                   current_state: Dict) -> List[Dict]:
        """顺序规划"""
        if not goal:
            return []
        
        # 简单的顺序任务生成
        plan = []
        
        # 解析目标中的动作序列
        actions = self._extract_actions_from_goal(goal)
        
        for i, action_name in enumerate(actions):
            if action_name in self._actions:
                action = self._actions[action_name]
                plan.append({
                    'name': f'task_{i}_{action_name}',
                    'description': f'Execute {action_name}',
                    'action': action_name,
                    'skill': action.skill,
                    'parameters': action.parameters,
                    'priority': 2,
                    'dependencies': [f'task_{i-1}_{actions[i-1]}'] if i > 0 else []
                })
        
        return plan
    
    def _parse_goal(self, goal_str: str) -> Goal:
        """解析目标字符串"""
        # 简单的目标解析
        goal = Goal(
            name=goal_str[:50],  # 截取前50字符作为名称
            description=goal_str,
            conditions={'goal_achieved': True},
            priority=2
        )
        
        # 尝试识别目标类型
        if '导航' in goal_str or 'navigate' in goal_str.lower():
            goal.conditions['at_location'] = True
        elif '抓取' in goal_str or 'grasp' in goal_str.lower() or 'pick' in goal_str.lower():
            goal.conditions['object_grasped'] = True
        elif '放置' in goal_str or 'place' in goal_str.lower() or 'put' in goal_str.lower():
            goal.conditions['object_placed'] = True
        elif '搬' in goal_str or 'transport' in goal_str.lower():
            goal.conditions['object_transported'] = True
        
        return goal
    
    def _match_template_for_goal(self, goal: Goal) -> Optional[str]:
        """为目标匹配合适的模板"""
        desc = goal.description.lower()
        
        if 'vln' in desc or '视觉语言导航' in desc:
            return 'vln_task'
        elif 'vla' in desc or '视觉语言操作' in desc:
            return 'vla_task'
        elif '导航' in desc or 'navigate' in desc or '到' in desc:
            return 'navigate'
        elif '抓取' in desc or 'grasp' in desc or '拿起' in desc:
            return 'pick_up'
        elif '放置' in desc or 'place' in desc or '放下' in desc:
            return 'put_down'
        elif '搬运' in desc or 'transport' in desc:
            return 'transport'
        elif '对话' in desc or 'interact' in desc:
            return 'interact'
        
        return None
    
    def _expand_template(self, template: Dict, goal: Goal, context: Dict) -> List[Dict]:
        """展开任务模板"""
        plan = []
        subtasks = template.get('subtasks', [])
        
        for i, subtask in enumerate(subtasks):
            task_item = {
                'name': subtask.get('name', f'subtask_{i}'),
                'description': f'Part of {goal.name}',
                'type': template.get('type', TaskType.COMPOSITE).value,
                'priority': goal.priority,
                'dependencies': []
            }
            
            # 处理嵌套模板
            if 'template' in subtask:
                nested_template = self._task_templates.get(subtask['template'])
                if nested_template:
                    nested_plan = self._expand_template(nested_template, goal, context)
                    plan.extend(nested_plan)
                    continue
            
            # 处理动作
            if 'action' in subtask:
                action_name = subtask['action']
                if action_name in self._actions:
                    action = self._actions[action_name]
                    task_item['action'] = action_name
                    task_item['skill'] = action.skill
                    task_item['parameters'] = action.parameters.copy()
                    task_item['estimated_duration'] = action.duration
            
            task_item['id'] = f"task_{i}_{task_item['name']}"
            plan.append(task_item)
        
        # 设置依赖关系
        for i in range(1, len(plan)):
            plan[i]['dependencies'] = [plan[i-1]['id']]
        
        return plan
    
    async def _generate_plan_from_goal(self, goal: Goal, context: Dict,
                                       current_state: Dict) -> List[Dict]:
        """从目标生成规划"""
        plan = []
        
        # 基于目标条件选择合适的动作序列
        goal_conditions = goal.conditions
        
        # 感知阶段
        if 'environment_known' not in current_state:
            plan.append({
                'id': 'task_0_perceive',
                'name': 'perceive_environment',
                'description': 'Perceive the current environment',
                'action': 'perceive',
                'skill': 'perception',
                'priority': goal.priority,
                'dependencies': []
            })
        
        # 导航阶段
        if 'at_location' in goal_conditions or 'at_target' in goal_conditions:
            plan.append({
                'id': f'task_{len(plan)}_navigate',
                'name': 'navigate_to_target',
                'description': 'Navigate to the target location',
                'action': 'vln_navigate',
                'skill': 'vln',
                'priority': goal.priority,
                'dependencies': [plan[-1]['id']] if plan else []
            })
        
        # 操作阶段
        if 'object_grasped' in goal_conditions or 'object_manipulated' in goal_conditions:
            plan.append({
                'id': f'task_{len(plan)}_manipulate',
                'name': 'manipulate_object',
                'description': 'Perform manipulation task',
                'action': 'vla_manipulate',
                'skill': 'vla',
                'priority': goal.priority,
                'dependencies': [plan[-1]['id']] if plan else []
            })
        
        return plan
    
    async def _decompose_task(self, task: Dict, context: Dict, 
                             constraints: Dict) -> List[Dict]:
        """分解任务"""
        # 检查是否有对应模板
        template_name = task.get('template')
        if template_name and template_name in self._task_templates:
            template = self._task_templates[template_name]
            return self._expand_template(template, Goal(name=task['name'], description=''), context)
        
        # 返回原子任务
        return [task]
    
    async def _decompose_htn_task(self, task: Dict, context: Dict,
                                  current_state: Dict) -> List[Dict]:
        """HTN任务分解"""
        # 检查任务类型
        task_type = task.get('type')
        
        if task_type == TaskType.COMPOSITE.value:
            # 复合任务需要进一步分解
            subtasks = []
            for subtask_def in task.get('subtasks', []):
                decomposed = await self._decompose_htn_task(subtask_def, context, current_state)
                subtasks.extend(decomposed)
            return subtasks
        else:
            # 原子任务直接返回
            return [task]
    
    def _identify_initial_tasks(self, goal: Goal) -> List[Dict]:
        """识别初始任务"""
        return [{
            'name': 'achieve_goal',
            'description': goal.description,
            'type': TaskType.COMPOSITE.value,
            'goal_conditions': goal.conditions
        }]
    
    def _get_world_state(self, current_state: Dict, context: Dict) -> Dict:
        """获取世界状态"""
        world_state = {
            'can_move': True,
            'hand_empty': True,
            'environment_known': False,
            'speech_recognized': False,
            'at_location': False,
            'object_grasped': False
        }
        
        # 更新已知状态
        world_state.update(current_state)
        world_state.update(context.get('perception_summary', {}))
        
        return world_state
    
    def _backward_search(self, initial_state: Dict, goal_state: Dict) -> Optional[List[Dict]]:
        """反向搜索规划"""
        # 简化的GOAP反向搜索
        plan = []
        current_state = goal_state.copy()
        
        max_iterations = 20
        iteration = 0
        
        while not self._state_satisfied(initial_state, current_state) and iteration < max_iterations:
            # 找到能满足当前状态的动作
            action_found = False
            
            for action_name, action in self._actions.items():
                if self._effects_match(action.effects, current_state):
                    plan.insert(0, {
                        'name': action_name,
                        'action': action_name,
                        'skill': action.skill,
                        'parameters': action.parameters,
                        'priority': 2,
                        'dependencies': []
                    })
                    
                    # 更新当前状态
                    current_state.update(action.preconditions)
                    action_found = True
                    break
            
            if not action_found:
                break
            
            iteration += 1
        
        return plan if self._state_satisfied(initial_state, current_state) else None
    
    def _state_satisfied(self, target: Dict, current: Dict) -> bool:
        """检查状态是否满足"""
        for key, value in target.items():
            if key in current and current[key] != value:
                return False
        return True
    
    def _effects_match(self, effects: Dict, state: Dict) -> bool:
        """检查效果是否匹配状态"""
        for key, value in effects.items():
            if key in state and state[key] == value:
                return True
        return False
    
    def _extract_actions_from_goal(self, goal: Goal) -> List[str]:
        """从目标中提取动作序列"""
        actions = []
        desc = goal.description.lower()
        
        # 简单的关键词匹配
        if 'perceive' in desc or '感知' in desc:
            actions.append('perceive')
        if 'navigate' in desc or '导航' in desc:
            actions.append('vln_navigate')
        if 'grasp' in desc or '抓取' in desc:
            actions.append('grasp')
        if 'place' in desc or '放置' in desc:
            actions.append('place')
        if 'manipulate' in desc or '操作' in desc:
            actions.append('vla_manipulate')
        
        return actions if actions else ['perceive']
    
    def _apply_constraints(self, plan: List[Dict], constraints: Dict) -> List[Dict]:
        """应用约束优化规划"""
        for task in plan:
            # 应用速度约束
            if 'max_velocity' in constraints:
                task['parameters'] = task.get('parameters', {})
                task['parameters']['max_velocity'] = constraints['max_velocity']
            
            # 应用碰撞避免约束
            if constraints.get('avoid_collisions', True):
                task['parameters'] = task.get('parameters', {})
                task['parameters']['avoid_collisions'] = True
        
        return plan
    
    def get_action_library(self) -> Dict[str, Action]:
        """获取动作库"""
        return self._actions.copy()
    
    def get_task_templates(self) -> Dict[str, Dict]:
        """获取任务模板"""
        return self._task_templates.copy()
    
    def get_planning_history(self) -> List[Dict]:
        """获取规划历史"""
        return self._planning_history.copy()
    
    def clear_cache(self):
        """清理规划缓存"""
        self._planning_cache.clear()
