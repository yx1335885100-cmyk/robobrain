# -*- coding: utf-8 -*-
"""
Task Scheduler - 任务调度器
支持优先级调度、资源感知调度、截止时间调度、多策略调度
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from collections import defaultdict
import heapq

from .task_manager import Task, TaskStatus, TaskPriority


class SchedulingAlgorithm(Enum):
    """调度算法枚举"""
    FIFO = "fifo"                      # 先进先出
    PRIORITY_BASED = "priority_based"  # 优先级调度
    ROUND_ROBIN = "round_robin"        # 时间片轮转
    SJF = "sjf"                        # 短作业优先
    EDF = "edf"                        # 最早截止时间优先
    RESOURCE_AWARE = "resource_aware"  # 资源感知调度
    ADAPTIVE = "adaptive"              # 自适应调度


@dataclass
class ResourceProfile:
    """资源配置"""
    cpu_cores: int = 4
    memory_mb: int = 2048
    gpu_available: bool = True
    sensors_available: List[str] = field(default_factory=lambda: ['camera', 'microphone', 'lidar'])
    actuators_available: List[str] = field(default_factory=lambda: ['left_arm', 'right_arm', 'head', 'base'])


@dataclass
class TaskResource:
    """任务资源需求"""
    cpu_usage: float = 0.5
    memory_mb: int = 256
    requires_gpu: bool = False
    required_sensors: List[str] = field(default_factory=list)
    required_actuators: List[str] = field(default_factory=list)


@dataclass
class SchedulingDecision:
    """调度决策"""
    task_id: str
    scheduled_time: float
    priority: int
    reason: str
    resource_allocation: Dict = field(default_factory=dict)


class TaskScheduler:
    """
    任务调度器
    
    提供多种调度算法，支持资源感知和约束处理
    
    Features:
        - 多种调度算法（优先级、FIFO、EDF等）
        - 资源感知调度
        - 任务依赖解析
        - 负载均衡
        - 调度决策追踪
        - 动态优先级调整
    """
    
    def __init__(self, scheduling_algorithm: str = 'priority_based'):
        """
        初始化任务调度器
        
        Args:
            scheduling_algorithm: 调度算法
        """
        self.algorithm = SchedulingAlgorithm(scheduling_algorithm)
        
        # 资源配置
        self.resources = ResourceProfile()
        self.resource_usage: Dict[str, float] = defaultdict(float)
        
        # 任务资源映射
        self._task_resources: Dict[str, TaskResource] = {}
        self._register_default_task_resources()
        
        # 调度队列
        self._schedule_queue: List[Task] = []
        self._scheduled_tasks: List[Task] = []
        
        # 调度历史
        self._scheduling_history: List[SchedulingDecision] = []
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 调度回调
        self._pre_scheduling_callbacks: List[Callable] = []
        self._post_scheduling_callbacks: List[Callable] = []
        
        # 时间片（用于Round Robin）
        self._time_slice = 1.0  # 秒
        
        # 动态优先级参数
        self._aging_factor = 0.1  # 老化因子
        self._starvation_threshold = 60.0  # 饥饿阈值（秒）
        
    def _register_default_task_resources(self):
        """注册默认任务资源需求"""
        # VLN任务资源需求
        self._task_resources['vln'] = TaskResource(
            cpu_usage=0.8,
            memory_mb=512,
            requires_gpu=True,
            required_sensors=['camera'],
            required_actuators=['base']
        )
        
        # VLA任务资源需求
        self._task_resources['vla'] = TaskResource(
            cpu_usage=0.7,
            memory_mb=512,
            requires_gpu=True,
            required_sensors=['camera'],
            required_actuators=['left_arm', 'right_arm']
        )
        
        # 感知任务资源需求
        self._task_resources['perception'] = TaskResource(
            cpu_usage=0.5,
            memory_mb=256,
            requires_gpu=False,
            required_sensors=['camera', 'microphone'],
            required_actuators=[]
        )
        
        # ASR任务资源需求
        self._task_resources['asr'] = TaskResource(
            cpu_usage=0.3,
            memory_mb=128,
            requires_gpu=False,
            required_sensors=['microphone'],
            required_actuators=[]
        )
        
        # TTS任务资源需求
        self._task_resources['tts'] = TaskResource(
            cpu_usage=0.2,
            memory_mb=64,
            requires_gpu=False,
            required_sensors=[],
            required_actuators=['speaker']
        )
        
        # 抓取任务资源需求
        self._task_resources['grasp'] = TaskResource(
            cpu_usage=0.4,
            memory_mb=128,
            requires_gpu=False,
            required_sensors=['camera'],
            required_actuators=['left_arm', 'right_arm']
        )
        
        # 导航任务资源需求
        self._task_resources['navigation'] = TaskResource(
            cpu_usage=0.6,
            memory_mb=256,
            requires_gpu=False,
            required_sensors=['lidar', 'camera'],
            required_actuators=['base']
        )
    
    def register_task_resource(self, skill_name: str, resource: TaskResource):
        """注册任务资源需求"""
        self._task_resources[skill_name] = resource
    
    def set_resources(self, resources: ResourceProfile):
        """设置系统资源"""
        self.resources = resources
    
    def add_pre_scheduling_callback(self, callback: Callable):
        """添加调度前回调"""
        self._pre_scheduling_callbacks.append(callback)
    
    def add_post_scheduling_callback(self, callback: Callable):
        """添加调度后回调"""
        self._post_scheduling_callbacks.append(callback)
    
    async def schedule(self, tasks: List[Task]) -> List[Task]:
        """
        执行任务调度
        
        Args:
            tasks: 待调度的任务列表
            
        Returns:
            调度后的任务列表
        """
        print(f"[TaskScheduler] Scheduling {len(tasks)} tasks using {self.algorithm.value} algorithm")
        
        # 触发调度前回调
        for callback in self._pre_scheduling_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tasks)
                else:
                    callback(tasks)
            except Exception as e:
                print(f"[TaskScheduler] Pre-scheduling callback error: {e}")
        
        # 选择调度算法
        if self.algorithm == SchedulingAlgorithm.FIFO:
            scheduled = await self._fifo_schedule(tasks)
        elif self.algorithm == SchedulingAlgorithm.PRIORITY_BASED:
            scheduled = await self._priority_schedule(tasks)
        elif self.algorithm == SchedulingAlgorithm.ROUND_ROBIN:
            scheduled = await self._round_robin_schedule(tasks)
        elif self.algorithm == SchedulingAlgorithm.SJF:
            scheduled = await self._sjf_schedule(tasks)
        elif self.algorithm == SchedulingAlgorithm.EDF:
            scheduled = await self._edf_schedule(tasks)
        elif self.algorithm == SchedulingAlgorithm.RESOURCE_AWARE:
            scheduled = await self._resource_aware_schedule(tasks)
        elif self.algorithm == SchedulingAlgorithm.ADAPTIVE:
            scheduled = await self._adaptive_schedule(tasks)
        else:
            scheduled = await self._priority_schedule(tasks)
        
        # 更新调度历史
        for task in scheduled:
            decision = SchedulingDecision(
                task_id=task.id,
                scheduled_time=time.time(),
                priority=task.priority.value,
                reason=f"Scheduled by {self.algorithm.value}"
            )
            self._scheduling_history.append(decision)
        
        # 触发调度后回调
        for callback in self._post_scheduling_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(scheduled)
                else:
                    callback(scheduled)
            except Exception as e:
                print(f"[TaskScheduler] Post-scheduling callback error: {e}")
        
        self._scheduled_tasks = scheduled
        return scheduled
    
    async def _fifo_schedule(self, tasks: List[Task]) -> List[Task]:
        """FIFO调度"""
        # 按创建时间排序
        sorted_tasks = sorted(tasks, key=lambda t: t.created_at)
        
        # 检查依赖
        scheduled = []
        for task in sorted_tasks:
            if self._check_dependencies_met(task, scheduled):
                scheduled.append(task)
        
        return scheduled
    
    async def _priority_schedule(self, tasks: List[Task]) -> List[Task]:
        """优先级调度"""
        with self._lock:
            # 应用老化机制防止饥饿
            aged_tasks = self._apply_aging(tasks)
            
            # 按优先级排序（数字越小优先级越高）
            sorted_tasks = sorted(aged_tasks, key=lambda t: (t.priority.value, t.created_at))
            
            # 检查依赖和资源
            scheduled = []
            used_resources = defaultdict(set)
            
            for task in sorted_tasks:
                # 检查依赖
                if not self._check_dependencies_met(task, scheduled):
                    continue
                
                # 检查资源
                if self._check_resources_available(task, used_resources):
                    scheduled.append(task)
                    self._allocate_resources(task, used_resources)
            
            return scheduled
    
    async def _round_robin_schedule(self, tasks: List[Task]) -> List[Task]:
        """时间片轮转调度"""
        # 对所有任务进行轮转调度
        scheduled = []
        remaining = list(tasks)
        
        while remaining:
            for task in remaining[:]:
                if self._check_dependencies_met(task, scheduled):
                    scheduled.append(task)
                    remaining.remove(task)
                    
                    # 限制每次调度的任务数
                    if len(scheduled) >= self._get_max_concurrent():
                        return scheduled
        
        return scheduled
    
    async def _sjf_schedule(self, tasks: List[Task]) -> List[Task]:
        """短作业优先调度"""
        # 按估计执行时间排序
        sorted_tasks = sorted(tasks, key=lambda t: t.timeout)
        
        scheduled = []
        for task in sorted_tasks:
            if self._check_dependencies_met(task, scheduled):
                scheduled.append(task)
        
        return scheduled
    
    async def _edf_schedule(self, tasks: List[Task]) -> List[Task]:
        """最早截止时间优先调度"""
        # 按截止时间排序（如果有的话）
        def get_deadline(task: Task) -> float:
            return task.metadata.get('deadline', float('inf'))
        
        sorted_tasks = sorted(tasks, key=get_deadline)
        
        scheduled = []
        for task in sorted_tasks:
            if self._check_dependencies_met(task, scheduled):
                scheduled.append(task)
        
        return scheduled
    
    async def _resource_aware_schedule(self, tasks: List[Task]) -> List[Task]:
        """资源感知调度"""
        with self._lock:
            scheduled = []
            used_resources = defaultdict(set)
            
            # 按优先级预排序
            sorted_tasks = sorted(tasks, key=lambda t: t.priority.value)
            
            for task in sorted_tasks:
                # 检查依赖
                if not self._check_dependencies_met(task, scheduled):
                    continue
                
                # 检查资源可用性
                if self._check_resources_available(task, used_resources):
                    scheduled.append(task)
                    self._allocate_resources(task, used_resources)
            
            return scheduled
    
    async def _adaptive_schedule(self, tasks: List[Task]) -> List[Task]:
        """自适应调度"""
        # 根据当前系统状态选择最佳调度策略
        system_load = self._calculate_system_load()
        
        if system_load < 0.3:
            # 低负载：使用FIFO
            return await self._fifo_schedule(tasks)
        elif system_load < 0.7:
            # 中等负载：使用优先级调度
            return await self._priority_schedule(tasks)
        else:
            # 高负载：使用资源感知调度
            return await self._resource_aware_schedule(tasks)
    
    def _apply_aging(self, tasks: List[Task]) -> List[Task]:
        """应用老化机制防止饥饿"""
        current_time = time.time()
        
        for task in tasks:
            wait_time = current_time - task.created_at
            
            # 如果等待时间超过阈值，提升优先级
            if wait_time > self._starvation_threshold:
                aging_boost = int(wait_time * self._aging_factor)
                task.metadata['aging_boost'] = aging_boost
        
        return tasks
    
    def _check_dependencies_met(self, task: Task, scheduled: List[Task]) -> bool:
        """检查任务依赖是否满足"""
        if not task.dependencies:
            return True
        
        scheduled_ids = {t.id for t in scheduled}
        
        for dep_id in task.dependencies:
            if dep_id not in scheduled_ids:
                return False
        
        return True
    
    def _check_resources_available(self, task: Task, used_resources: Dict) -> bool:
        """检查资源是否可用"""
        resource_req = self._get_task_resource(task)
        
        # 检查传感器资源
        for sensor in resource_req.required_sensors:
            if sensor in used_resources['sensors']:
                return False
        
        # 检查执行器资源
        for actuator in resource_req.required_actuators:
            if actuator in used_resources['actuators']:
                return False
        
        # 检查CPU和内存
        total_cpu = sum(self._get_task_resource(t).cpu_usage for t in used_resources.get('tasks', []))
        if total_cpu + resource_req.cpu_usage > self.resources.cpu_cores:
            return False
        
        return True
    
    def _allocate_resources(self, task: Task, used_resources: Dict):
        """分配资源"""
        resource_req = self._get_task_resource(task)
        
        # 标记传感器使用
        for sensor in resource_req.required_sensors:
            used_resources['sensors'].add(sensor)
        
        # 标记执行器使用
        for actuator in resource_req.required_actuators:
            used_resources['actuators'].add(actuator)
        
        # 记录任务使用资源
        used_resources['tasks'].append(task)
    
    def _get_task_resource(self, task: Task) -> TaskResource:
        """获取任务资源需求"""
        if task.skill and task.skill in self._task_resources:
            return self._task_resources[task.skill]
        
        # 默认资源需求
        return TaskResource()
    
    def _get_max_concurrent(self) -> int:
        """获取最大并发任务数"""
        return self.resources.cpu_cores
    
    def _calculate_system_load(self) -> float:
        """计算系统负载"""
        # 简化的负载计算
        cpu_load = self.resource_usage.get('cpu', 0) / self.resources.cpu_cores
        memory_load = self.resource_usage.get('memory', 0) / self.resources.memory_mb
        
        return (cpu_load + memory_load) / 2
    
    def update_resource_usage(self, resource_type: str, usage: float):
        """更新资源使用情况"""
        self.resource_usage[resource_type] = usage
    
    def get_resource_status(self) -> Dict:
        """获取资源状态"""
        return {
            'total_resources': {
                'cpu_cores': self.resources.cpu_cores,
                'memory_mb': self.resources.memory_mb,
                'gpu_available': self.resources.gpu_available,
                'sensors': self.resources.sensors_available,
                'actuators': self.resources.actuators_available
            },
            'current_usage': dict(self.resource_usage),
            'load': self._calculate_system_load()
        }
    
    def get_scheduling_history(self, limit: int = 100) -> List[SchedulingDecision]:
        """获取调度历史"""
        return self._scheduling_history[-limit:]
    
    def reschedule(self, tasks: List[Task], reason: str = "reschedule") -> List[Task]:
        """
        重新调度任务
        
        Args:
            tasks: 待重新调度的任务
            reason: 重调度原因
            
        Returns:
            重新调度后的任务列表
        """
        print(f"[TaskScheduler] Rescheduling {len(tasks)} tasks. Reason: {reason}")
        
        # 清理之前调度中已完成的任务
        pending_tasks = [t for t in tasks if t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]]
        
        # 异步调度
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.schedule(pending_tasks))
    
    def prioritize_task(self, task_id: str, new_priority: TaskPriority) -> bool:
        """
        动态调整任务优先级
        
        Args:
            task_id: 任务ID
            new_priority: 新优先级
            
        Returns:
            是否调整成功
        """
        for task in self._schedule_queue:
            if task.id == task_id:
                task.priority = new_priority
                task.metadata['priority_changed'] = True
                print(f"[TaskScheduler] Task {task_id} priority changed to {new_priority.value}")
                return True
        
        return False
    
    def get_scheduled_tasks(self) -> List[Task]:
        """获取已调度任务列表"""
        return self._scheduled_tasks.copy()
    
    def get_statistics(self) -> Dict:
        """获取调度统计"""
        if not self._scheduling_history:
            return {
                'total_scheduled': 0,
                'algorithm': self.algorithm.value,
                'average_scheduling_time': 0
            }
        
        priorities = defaultdict(int)
        for decision in self._scheduling_history:
            priorities[decision.priority] += 1
        
        return {
            'total_scheduled': len(self._scheduling_history),
            'algorithm': self.algorithm.value,
            'priority_distribution': dict(priorities),
            'resource_status': self.get_resource_status()
        }
    
    def clear_history(self):
        """清理调度历史"""
        self._scheduling_history.clear()
        self._scheduled_tasks.clear()
