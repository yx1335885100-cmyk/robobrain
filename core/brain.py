# -*- coding: utf-8 -*-
"""
Robot Brain - 机器人智慧大脑主控制器
负责协调查知、规划、调度、执行等所有模块，实现完整的认知闭环
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
from queue import Queue
import json

# 导入内部模块
from .task_manager import TaskManager, Task, TaskStatus, TaskPriority
from .task_planner import TaskPlanner
from .task_scheduler import TaskScheduler
from .task_executor import TaskExecutor


class BrainState(Enum):
    """大脑状态枚举"""
    IDLE = "idle"                    # 空闲状态
    PERCEIVING = "perceiving"        # 感知中
    PLANNING = "planning"            # 规划中
    SCHEDULING = "scheduling"        # 调度中
    EXECUTING = "executing"          # 执行中
    REFLECTING = "reflecting"        # 反思/反馈处理中
    ERROR = "error"                  # 错误状态
    SHUTDOWN = "shutdown"            # 关闭状态


@dataclass
class PerceptionData:
    """感知数据结构"""
    timestamp: float
    modality: str  # 'audio', 'visual', 'tactile', 'joint_state'
    data: Any
    metadata: Dict = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """执行上下文"""
    current_task: Optional[Task] = None
    current_skill: Optional[str] = None
    perception_buffer: List[PerceptionData] = field(default_factory=list)
    feedback_queue: Queue = field(default_factory=Queue)
    global_plan: List[Dict] = field(default_factory=list)
    local_plan: List[Dict] = field(default_factory=list)


class RobotBrain:
    """
    机器人智慧大脑主控制器
    
    实现完整的认知闭环：
    感知 -> 任务规划 -> 任务调度 -> 任务编排 -> 任务执行 -> 执行反馈 -> 规划调整
    
    Attributes:
        state: 当前大脑状态
        task_manager: 任务管理器
        task_planner: 任务规划器
        task_scheduler: 任务调度器
        task_executor: 任务执行器
        perception_modules: 感知模块字典
        skill_registry: 技能注册表
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化机器人智慧大脑
        
        Args:
            config: 配置字典，包含各模块参数
        """
        self.config = config or self._default_config()
        self.state = BrainState.IDLE
        self.execution_context = ExecutionContext()
        
        # 初始化核心组件
        self.task_manager = TaskManager(
            max_concurrent_tasks=self.config.get('max_concurrent_tasks', 5)
        )
        self.task_planner = TaskPlanner(
            planning_strategy=self.config.get('planning_strategy', 'hierarchical')
        )
        self.task_scheduler = TaskScheduler(
            scheduling_algorithm=self.config.get('scheduling_algorithm', 'priority_based')
        )
        self.task_executor = TaskExecutor(
            execution_mode=self.config.get('execution_mode', 'sequential')
        )
        
        # 感知模块注册
        self.perception_modules: Dict[str, Any] = {}
        self.perception_callbacks: Dict[str, List[Callable]] = {}
        
        # 技能注册
        self.skill_registry: Dict[str, Any] = {}
        
        # ROS2接口
        self.ros2_bridge = None
        self.joint_monitor = None
        
        # 运行控制
        self._running = False
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._cognitive_thread: Optional[threading.Thread] = None
        
        # 回调注册
        self._state_change_callbacks: List[Callable] = []
        self._task_complete_callbacks: List[Callable] = []
        
        # 性能监控
        self._performance_metrics = {
            'perception_latency': [],
            'planning_latency': [],
            'execution_latency': [],
            'total_cycle_time': []
        }
        
    def _default_config(self) -> Dict:
        """获取默认配置"""
        return {
            'max_concurrent_tasks': 5,
            'planning_strategy': 'hierarchical',
            'scheduling_algorithm': 'priority_based',
            'execution_mode': 'sequential',
            'perception_buffer_size': 100,
            'feedback_timeout': 30.0,
            'joint_update_rate': 100,  # Hz
            'enable_reflection': True,
            'max_planning_iterations': 10
        }
    
    def register_perception_module(self, name: str, module: Any, 
                                   callbacks: Optional[List[Callable]] = None):
        """
        注册感知模块
        
        Args:
            name: 模块名称 (如 'asr', 'vision', 'joint_state')
            module: 感知模块实例
            callbacks: 感知数据回调函数列表
        """
        self.perception_modules[name] = module
        self.perception_callbacks[name] = callbacks or []
        print(f"[Brain] Registered perception module: {name}")
    
    def register_skill(self, name: str, skill_class: Any):
        """
        注册技能
        
        Args:
            name: 技能名称 (如 'vln', 'vla', 'grasp')
            skill_class: 技能类
        """
        self.skill_registry[name] = skill_class
        self.task_executor.register_skill(name, skill_class)
        print(f"[Brain] Registered skill: {name}")
    
    def register_ros2_bridge(self, bridge: Any):
        """注册ROS2桥接"""
        self.ros2_bridge = bridge
        print("[Brain] Registered ROS2 bridge")
    
    def register_joint_monitor(self, monitor: Any):
        """注册关节监测器"""
        self.joint_monitor = monitor
        print("[Brain] Registered joint monitor")
    
    def add_state_change_callback(self, callback: Callable):
        """添加状态变化回调"""
        self._state_change_callbacks.append(callback)
    
    def add_task_complete_callback(self, callback: Callable):
        """添加任务完成回调"""
        self._task_complete_callbacks.append(callback)
    
    async def _set_state(self, new_state: BrainState):
        """设置大脑状态并触发回调"""
        old_state = self.state
        self.state = new_state
        
        # 触发状态变化回调
        for callback in self._state_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(old_state, new_state)
                else:
                    callback(old_state, new_state)
            except Exception as e:
                print(f"[Brain] State change callback error: {e}")
        
        print(f"[Brain] State changed: {old_state.value} -> {new_state.value}")
    
    async def perceive(self) -> List[PerceptionData]:
        """
        执行感知阶段
        
        从所有注册的感知模块收集数据，进行传感器融合
        
        Returns:
            感知数据列表
        """
        await self._set_state(BrainState.PERCEIVING)
        start_time = time.time()
        
        perception_results = []
        
        # 并行收集所有感知模块的数据
        perception_tasks = []
        for name, module in self.perception_modules.items():
            if hasattr(module, 'perceive'):
                perception_tasks.append(self._collect_perception(name, module))
        
        if perception_tasks:
            perception_results = await asyncio.gather(*perception_tasks, return_exceptions=True)
            perception_results = [r for r in perception_results if not isinstance(r, Exception)]
        
        # 更新执行上下文的感知缓冲区
        self.execution_context.perception_buffer.extend(perception_results)
        
        # 保持缓冲区大小限制
        buffer_size = self.config.get('perception_buffer_size', 100)
        if len(self.execution_context.perception_buffer) > buffer_size:
            self.execution_context.perception_buffer = \
                self.execution_context.perception_buffer[-buffer_size:]
        
        # 记录性能指标
        latency = time.time() - start_time
        self._performance_metrics['perception_latency'].append(latency)
        
        return perception_results
    
    async def _collect_perception(self, name: str, module: Any) -> PerceptionData:
        """从单个感知模块收集数据"""
        try:
            data = await module.perceive() if asyncio.iscoroutinefunction(module.perceive) \
                   else module.perceive()
            
            perception_data = PerceptionData(
                timestamp=time.time(),
                modality=name,
                data=data,
                metadata={'module': name}
            )
            
            # 触发感知回调
            for callback in self.perception_callbacks.get(name, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(perception_data)
                    else:
                        callback(perception_data)
                except Exception as e:
                    print(f"[Brain] Perception callback error for {name}: {e}")
            
            return perception_data
            
        except Exception as e:
            print(f"[Brain] Perception error for {name}: {e}")
            return None
    
    async def plan(self, perception_data: List[PerceptionData], 
                   goal: Optional[str] = None) -> List[Dict]:
        """
        执行规划阶段
        
        基于感知数据和目标进行任务规划
        
        Args:
            perception_data: 感知数据列表
            goal: 目标描述
            
        Returns:
            规划的任务列表
        """
        await self._set_state(BrainState.PLANNING)
        start_time = time.time()
        
        # 提取关键信息
        context = self._build_planning_context(perception_data)
        
        # 全局规划
        global_plan = await self.task_planner.plan_global(
            goal=goal,
            context=context,
            current_state=self._get_robot_state()
        )
        self.execution_context.global_plan = global_plan
        
        # 局部规划
        local_plan = await self.task_planner.plan_local(
            global_plan=global_plan,
            context=context,
            constraints=self._get_constraints()
        )
        self.execution_context.local_plan = local_plan
        
        # 将规划结果转换为任务
        tasks = []
        for plan_item in local_plan:
            task = Task(
                id=f"task_{int(time.time()*1000)}_{len(tasks)}",
                name=plan_item.get('name', 'unnamed_task'),
                description=plan_item.get('description', ''),
                priority=TaskPriority(plan_item.get('priority', 2)),
                skill=plan_item.get('skill'),
                parameters=plan_item.get('parameters', {}),
                dependencies=plan_item.get('dependencies', [])
            )
            tasks.append(task)
        
        # 记录性能指标
        latency = time.time() - start_time
        self._performance_metrics['planning_latency'].append(latency)
        
        return tasks
    
    async def schedule(self, tasks: List[Task]) -> List[Task]:
        """
        执行调度阶段
        
        对任务进行优先级排序和依赖解析
        
        Args:
            tasks: 待调度的任务列表
            
        Returns:
            调度后的任务列表
        """
        await self._set_state(BrainState.SCHEDULING)
        
        # 将任务添加到任务管理器
        for task in tasks:
            self.task_manager.add_task(task)
        
        # 执行任务调度
        scheduled_tasks = await self.task_scheduler.schedule(
            self.task_manager.get_pending_tasks()
        )
        
        return scheduled_tasks
    
    async def execute(self, task: Task) -> Dict:
        """
        执行任务
        
        Args:
            task: 要执行的任务
            
        Returns:
            执行结果
        """
        await self._set_state(BrainState.EXECUTING)
        start_time = time.time()
        
        self.execution_context.current_task = task
        
        # 更新任务状态
        self.task_manager.update_task_status(task.id, TaskStatus.RUNNING)
        
        try:
            # 执行任务
            result = await self.task_executor.execute(
                task=task,
                context=self.execution_context,
                skill_registry=self.skill_registry,
                ros2_bridge=self.ros2_bridge
            )
            
            # 更新任务状态
            self.task_manager.update_task_status(
                task.id, 
                TaskStatus.COMPLETED if result.get('success') else TaskStatus.FAILED
            )
            
            # 触发任务完成回调
            for callback in self._task_complete_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(task, result)
                    else:
                        callback(task, result)
                except Exception as e:
                    print(f"[Brain] Task complete callback error: {e}")
            
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            self.task_manager.update_task_status(task.id, TaskStatus.FAILED)
        
        # 记录性能指标
        latency = time.time() - start_time
        self._performance_metrics['execution_latency'].append(latency)
        
        return result
    
    async def reflect(self, task: Task, result: Dict) -> Dict:
        """
        执行反思/反馈阶段
        
        分析执行结果，决定是否需要重新规划
        
        Args:
            task: 执行的任务
            result: 执行结果
            
        Returns:
            反思结果，包含是否需要重新规划等决策
        """
        await self._set_state(BrainState.REFLECTING)
        
        reflection = {
            'task_id': task.id,
            'success': result.get('success', False),
            'needs_replanning': False,
            'feedback': {},
            'adjustments': []
        }
        
        if not result.get('success'):
            # 分析失败原因
            error_analysis = await self._analyze_failure(task, result)
            reflection['feedback'] = error_analysis
            
            # 决定是否需要重新规划
            if error_analysis.get('recoverable', True):
                reflection['needs_replanning'] = True
                reflection['adjustments'] = error_analysis.get('suggestions', [])
        
        # 将反馈加入队列
        self.execution_context.feedback_queue.put(reflection)
        
        return reflection
    
    def _build_planning_context(self, perception_data: List[PerceptionData]) -> Dict:
        """构建规划上下文"""
        context = {
            'timestamp': time.time(),
            'perception_summary': {},
            'joint_states': {},
            'environment': {}
        }
        
        for data in perception_data:
            if data is None:
                continue
                
            if data.modality == 'audio':
                context['perception_summary']['speech'] = data.data
            elif data.modality == 'visual':
                context['perception_summary']['vision'] = data.data
            elif data.modality == 'joint_state':
                context['joint_states'] = data.data
        
        return context
    
    def _get_robot_state(self) -> Dict:
        """获取机器人当前状态"""
        state = {
            'joint_positions': {},
            'joint_velocities': {},
            'end_effector_pose': {},
            'battery_level': 1.0,
            'is_moving': False
        }
        
        if self.joint_monitor:
            state['joint_positions'] = self.joint_monitor.get_joint_positions()
            state['joint_velocities'] = self.joint_monitor.get_joint_velocities()
            state['is_moving'] = self.joint_monitor.is_moving()
        
        return state
    
    def _get_constraints(self) -> Dict:
        """获取执行约束"""
        return {
            'max_velocity': 1.0,
            'max_acceleration': 0.5,
            'avoid_collisions': True,
            'respect_joint_limits': True
        }
    
    async def _analyze_failure(self, task: Task, result: Dict) -> Dict:
        """分析任务失败原因"""
        analysis = {
            'error_type': result.get('error_type', 'unknown'),
            'error_message': result.get('error', 'Unknown error'),
            'recoverable': True,
            'suggestions': []
        }
        
        error = result.get('error', '')
        
        # 简单的错误分类和恢复建议
        if 'timeout' in error.lower():
            analysis['error_type'] = 'timeout'
            analysis['suggestions'] = [
                {'action': 'retry', 'parameters': {'timeout': 60}},
                {'action': 'adjust_plan', 'parameters': {'split_task': True}}
            ]
        elif 'collision' in error.lower():
            analysis['error_type'] = 'collision'
            analysis['suggestions'] = [
                {'action': 'replan_path', 'parameters': {'avoid_obstacles': True}},
                {'action': 'adjust_velocity', 'parameters': {'velocity_scale': 0.5}}
            ]
        elif 'joint_limit' in error.lower():
            analysis['error_type'] = 'joint_limit'
            analysis['suggestions'] = [
                {'action': 'adjust_pose', 'parameters': {}},
                {'action': 'use_alternative_config', 'parameters': {}}
            ]
        
        return analysis
    
    async def cognitive_cycle(self, goal: Optional[str] = None):
        """
        执行一个完整的认知循环
        
        感知 -> 规划 -> 调度 -> 执行 -> 反思
        
        Args:
            goal: 可选的目标描述
        """
        cycle_start = time.time()
        
        try:
            # 1. 感知阶段
            perception_data = await self.perceive()
            
            # 2. 规划阶段
            tasks = await self.plan(perception_data, goal)
            
            # 3. 调度阶段
            scheduled_tasks = await self.schedule(tasks)
            
            # 4. 执行阶段
            for task in scheduled_tasks:
                result = await self.execute(task)
                
                # 5. 反思阶段
                if self.config.get('enable_reflection', True):
                    reflection = await self.reflect(task, result)
                    
                    # 如果需要重新规划
                    if reflection.get('needs_replanning'):
                        adjustments = reflection.get('adjustments', [])
                        for adjustment in adjustments:
                            # 应用调整并重新规划
                            await self._apply_adjustment(adjustment)
                            new_tasks = await self.plan(perception_data, goal)
                            await self.schedule(new_tasks)
            
            # 记录总周期时间
            cycle_time = time.time() - cycle_start
            self._performance_metrics['total_cycle_time'].append(cycle_time)
            
        except Exception as e:
            await self._set_state(BrainState.ERROR)
            print(f"[Brain] Cognitive cycle error: {e}")
            raise
    
    async def _apply_adjustment(self, adjustment: Dict):
        """应用调整"""
        action = adjustment.get('action')
        params = adjustment.get('parameters', {})
        
        if action == 'retry':
            print(f"[Brain] Applying adjustment: retry with params {params}")
        elif action == 'replan_path':
            print(f"[Brain] Applying adjustment: replan path with params {params}")
        elif action == 'adjust_velocity':
            print(f"[Brain] Applying adjustment: adjust velocity with params {params}")
    
    async def run(self):
        """
        启动大脑主循环
        
        持续执行认知循环，直到收到停止信号
        """
        self._running = True
        print("[Brain] Starting main cognitive loop...")
        
        while self._running:
            try:
                await self.cognitive_cycle()
                await asyncio.sleep(0.1)  # 避免CPU过度占用
            except Exception as e:
                print(f"[Brain] Error in cognitive cycle: {e}")
                await self._set_state(BrainState.ERROR)
                await asyncio.sleep(1)  # 错误恢复延迟
        
        await self._set_state(BrainState.SHUTDOWN)
        print("[Brain] Main cognitive loop stopped")
    
    def stop(self):
        """停止大脑运行"""
        self._running = False
        print("[Brain] Stop signal received")
    
    async def submit_goal(self, goal: str, priority: int = 2) -> str:
        """
        提交新目标
        
        Args:
            goal: 目标描述
            priority: 优先级 (1=高, 2=中, 3=低)
            
        Returns:
            任务ID
        """
        # 创建高层任务
        task = Task(
            id=f"goal_{int(time.time()*1000)}",
            name=f"Goal: {goal}",
            description=goal,
            priority=TaskPriority(priority),
            parameters={'goal': goal}
        )
        
        self.task_manager.add_task(task)
        print(f"[Brain] New goal submitted: {goal}")
        
        return task.id
    
    def get_status(self) -> Dict:
        """获取大脑状态信息"""
        return {
            'state': self.state.value,
            'current_task': self.execution_context.current_task.id if self.execution_context.current_task else None,
            'pending_tasks': len(self.task_manager.get_pending_tasks()),
            'running_tasks': len(self.task_manager.get_running_tasks()),
            'completed_tasks': len(self.task_manager.get_completed_tasks()),
            'registered_skills': list(self.skill_registry.keys()),
            'registered_perception_modules': list(self.perception_modules.keys()),
            'performance_metrics': {
                k: sum(v[-10:])/len(v[-10:]) if v else 0 
                for k, v in self._performance_metrics.items()
            }
        }
    
    def get_joint_states(self) -> Dict:
        """获取当前关节状态"""
        if self.joint_monitor:
            return {
                'positions': self.joint_monitor.get_joint_positions(),
                'velocities': self.joint_monitor.get_joint_velocities(),
                'efforts': self.joint_monitor.get_joint_efforts(),
                'timestamps': self.joint_monitor.get_timestamps()
            }
        return {}
    
    async def execute_skill(self, skill_name: str, parameters: Dict) -> Dict:
        """
        直接执行技能
        
        Args:
            skill_name: 技能名称
            parameters: 技能参数
            
        Returns:
            执行结果
        """
        if skill_name not in self.skill_registry:
            return {'success': False, 'error': f'Skill {skill_name} not registered'}
        
        task = Task(
            id=f"skill_{int(time.time()*1000)}",
            name=f"Direct skill execution: {skill_name}",
            skill=skill_name,
            parameters=parameters
        )
        
        return await self.execute(task)
