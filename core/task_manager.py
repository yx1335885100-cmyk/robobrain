# -*- coding: utf-8 -*-
"""
Task Manager - 多任务管理器
支持多任务并发执行、任务优先级管理、任务依赖管理、任务状态追踪
"""

import time
import asyncio
from typing import Dict, List, Optional, Set, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import threading
import uuid


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 等待执行
    READY = "ready"              # 就绪（依赖已满足）
    RUNNING = "running"          # 执行中
    PAUSED = "paused"            # 已暂停
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消


class TaskPriority(Enum):
    """任务优先级枚举"""
    CRITICAL = 0    # 关键任务
    HIGH = 1        # 高优先级
    MEDIUM = 2      # 中优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


@dataclass
class Task:
    """
    任务数据结构
    
    Attributes:
        id: 任务唯一标识
        name: 任务名称
        description: 任务描述
        status: 任务状态
        priority: 任务优先级
        skill: 关联的技能名称
        parameters: 任务参数
        dependencies: 依赖任务ID列表
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        result: 执行结果
        error: 错误信息
        retry_count: 重试次数
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        progress: 执行进度 (0-100)
        subtasks: 子任务列表
        parent_id: 父任务ID
        metadata: 元数据
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    skill: Optional[str] = None
    parameters: Dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 60.0
    progress: float = 0.0
    subtasks: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'skill': self.skill,
            'parameters': self.parameters,
            'dependencies': self.dependencies,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'result': self.result,
            'error': self.error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'timeout': self.timeout,
            'progress': self.progress,
            'subtasks': self.subtasks,
            'parent_id': self.parent_id,
            'metadata': self.metadata
        }


class TaskManager:
    """
    多任务管理器
    
    提供任务的创建、调度、状态管理、依赖解析等功能
    
    Features:
        - 多任务并发管理
        - 优先级队列调度
        - 任务依赖解析
        - 任务状态追踪
        - 任务重试机制
        - 任务取消和暂停
        - 任务执行历史
    """
    
    def __init__(self, max_concurrent_tasks: int = 5):
        """
        初始化任务管理器
        
        Args:
            max_concurrent_tasks: 最大并发任务数
        """
        self.max_concurrent_tasks = max_concurrent_tasks
        
        # 任务存储
        self._tasks: Dict[str, Task] = {}
        self._task_queue: List[Task] = []  # 待调度队列
        
        # 状态索引
        self._status_index: Dict[TaskStatus, Set[str]] = defaultdict(set)
        self._priority_index: Dict[TaskPriority, Set[str]] = defaultdict(set)
        
        # 依赖管理
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)  # task_id -> dependent_task_ids
        self._reverse_dependency: Dict[str, Set[str]] = defaultdict(set)  # task_id -> tasks_that_depend_on_it
        
        # 执行历史
        self._history: List[Dict] = []
        self._max_history_size = 1000
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 回调注册
        self._status_callbacks: Dict[TaskStatus, List[Callable]] = defaultdict(list)
        
    def add_task(self, task: Task) -> str:
        """
        添加任务
        
        Args:
            task: 任务对象
            
        Returns:
            任务ID
        """
        with self._lock:
            # 存储任务
            self._tasks[task.id] = task
            
            # 更新索引
            self._status_index[task.status].add(task.id)
            self._priority_index[task.priority].add(task.id)
            
            # 建立依赖关系
            for dep_id in task.dependencies:
                if dep_id in self._tasks:
                    self._dependency_graph[task.id].add(dep_id)
                    self._reverse_dependency[dep_id].add(task.id)
            
            # 检查是否可以立即就绪
            if self._check_dependencies_satisfied(task):
                task.status = TaskStatus.READY
                self._update_status_index(task.id, TaskStatus.PENDING, TaskStatus.READY)
            
            # 加入待调度队列
            self._task_queue.append(task)
            
            # 记录历史
            self._add_history('add', task)
            
            print(f"[TaskManager] Task added: {task.id} - {task.name}")
            
            return task.id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务对象或None
        """
        return self._tasks.get(task_id)
    
    def update_task_status(self, task_id: str, new_status: TaskStatus, 
                          error: Optional[str] = None) -> bool:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            new_status: 新状态
            error: 错误信息（可选）
            
        Returns:
            是否更新成功
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            old_status = task.status
            task.status = new_status
            
            # 更新索引
            self._update_status_index(task_id, old_status, new_status)
            
            # 更新时间戳
            if new_status == TaskStatus.RUNNING:
                task.started_at = time.time()
            elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = time.time()
            
            # 记录错误
            if error:
                task.error = error
            
            # 记录历史
            self._add_history('status_change', task, {
                'old_status': old_status.value,
                'new_status': new_status.value
            })
            
            # 触发回调
            self._trigger_callbacks(new_status, task)
            
            # 如果任务完成，检查依赖它的任务是否可以就绪
            if new_status == TaskStatus.COMPLETED:
                self._check_dependent_tasks(task_id)
            
            return True
    
    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """
        更新任务进度
        
        Args:
            task_id: 任务ID
            progress: 进度 (0-100)
            
        Returns:
            是否更新成功
        """
        task = self._tasks.get(task_id)
        if task:
            task.progress = max(0, min(100, progress))
            return True
        return False
    
    def set_task_result(self, task_id: str, result: Dict) -> bool:
        """
        设置任务结果
        
        Args:
            task_id: 任务ID
            result: 结果字典
            
        Returns:
            是否设置成功
        """
        task = self._tasks.get(task_id)
        if task:
            task.result = result
            return True
        return False
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        return self.update_task_status(task_id, TaskStatus.CANCELLED)
    
    def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否暂停成功
        """
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.RUNNING:
            return False
        
        return self.update_task_status(task_id, TaskStatus.PAUSED)
    
    def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否恢复成功
        """
        task = self._tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        return self.update_task_status(task_id, TaskStatus.READY)
    
    def retry_task(self, task_id: str) -> bool:
        """
        重试任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否可以重试
        """
        task = self._tasks.get(task_id)
        if not task:
            return False
        
        if task.status != TaskStatus.FAILED:
            return False
        
        if task.retry_count >= task.max_retries:
            print(f"[TaskManager] Task {task_id} has reached max retries")
            return False
        
        task.retry_count += 1
        return self.update_task_status(task_id, TaskStatus.PENDING)
    
    def get_pending_tasks(self) -> List[Task]:
        """获取待执行任务列表"""
        return [self._tasks[tid] for tid in self._status_index[TaskStatus.PENDING] 
                if tid in self._tasks]
    
    def get_ready_tasks(self) -> List[Task]:
        """获取就绪任务列表"""
        return [self._tasks[tid] for tid in self._status_index[TaskStatus.READY] 
                if tid in self._tasks]
    
    def get_running_tasks(self) -> List[Task]:
        """获取执行中任务列表"""
        return [self._tasks[tid] for tid in self._status_index[TaskStatus.RUNNING] 
                if tid in self._tasks]
    
    def get_completed_tasks(self) -> List[Task]:
        """获取已完成任务列表"""
        return [self._tasks[tid] for tid in self._status_index[TaskStatus.COMPLETED] 
                if tid in self._tasks]
    
    def get_failed_tasks(self) -> List[Task]:
        """获取失败任务列表"""
        return [self._tasks[tid] for tid in self._status_index[TaskStatus.FAILED] 
                if tid in self._tasks]
    
    def get_tasks_by_priority(self, priority: TaskPriority) -> List[Task]:
        """按优先级获取任务"""
        return [self._tasks[tid] for tid in self._priority_index[priority] 
                if tid in self._tasks]
    
    def get_next_task(self) -> Optional[Task]:
        """
        获取下一个可执行的任务
        
        基于优先级和依赖关系选择
        
        Returns:
            任务对象或None
        """
        with self._lock:
            # 获取所有就绪的任务
            ready_tasks = self.get_ready_tasks()
            
            if not ready_tasks:
                # 检查是否有依赖已满足的pending任务
                pending_tasks = self.get_pending_tasks()
                for task in pending_tasks:
                    if self._check_dependencies_satisfied(task):
                        task.status = TaskStatus.READY
                        self._update_status_index(task.id, TaskStatus.PENDING, TaskStatus.READY)
                        ready_tasks.append(task)
            
            if not ready_tasks:
                return None
            
            # 按优先级排序
            ready_tasks.sort(key=lambda t: t.priority.value)
            
            # 检查并发限制
            running_count = len(self.get_running_tasks())
            if running_count >= self.max_concurrent_tasks:
                return None
            
            return ready_tasks[0]
    
    def can_execute_more(self) -> bool:
        """检查是否可以执行更多任务"""
        return len(self.get_running_tasks()) < self.max_concurrent_tasks
    
    def get_task_dependencies(self, task_id: str) -> List[str]:
        """获取任务的依赖列表"""
        return list(self._dependency_graph.get(task_id, []))
    
    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """获取依赖于指定任务的任务列表"""
        return list(self._reverse_dependency.get(task_id, []))
    
    def add_dependency(self, task_id: str, depends_on: str) -> bool:
        """
        添加任务依赖
        
        Args:
            task_id: 任务ID
            depends_on: 依赖的任务ID
            
        Returns:
            是否添加成功
        """
        with self._lock:
            if task_id not in self._tasks or depends_on not in self._tasks:
                return False
            
            # 检查是否会形成循环依赖
            if self._would_create_cycle(task_id, depends_on):
                print(f"[TaskManager] Cannot add dependency: would create cycle")
                return False
            
            self._dependency_graph[task_id].add(depends_on)
            self._reverse_dependency[depends_on].add(task_id)
            self._tasks[task_id].dependencies.append(depends_on)
            
            return True
    
    def remove_dependency(self, task_id: str, depends_on: str) -> bool:
        """移除任务依赖"""
        with self._lock:
            if task_id not in self._tasks:
                return False
            
            self._dependency_graph[task_id].discard(depends_on)
            self._reverse_dependency[depends_on].discard(task_id)
            
            if depends_on in self._tasks[task_id].dependencies:
                self._tasks[task_id].dependencies.remove(depends_on)
            
            return True
    
    def _check_dependencies_satisfied(self, task: Task) -> bool:
        """检查任务依赖是否都已满足"""
        for dep_id in task.dependencies:
            dep_task = self._tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    def _check_dependent_tasks(self, completed_task_id: str):
        """检查依赖于已完成任务的其他任务是否可以就绪"""
        dependent_ids = self._reverse_dependency.get(completed_task_id, set())
        
        for dep_task_id in dependent_ids:
            dep_task = self._tasks.get(dep_task_id)
            if dep_task and dep_task.status == TaskStatus.PENDING:
                if self._check_dependencies_satisfied(dep_task):
                    dep_task.status = TaskStatus.READY
                    self._update_status_index(dep_task_id, TaskStatus.PENDING, TaskStatus.READY)
                    print(f"[TaskManager] Task {dep_task_id} is now ready")
    
    def _would_create_cycle(self, task_id: str, depends_on: str) -> bool:
        """检查添加依赖是否会形成循环"""
        visited = set()
        stack = [depends_on]
        
        while stack:
            current = stack.pop()
            if current == task_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            
            for dep in self._dependency_graph.get(current, set()):
                stack.append(dep)
        
        return False
    
    def _update_status_index(self, task_id: str, old_status: TaskStatus, new_status: TaskStatus):
        """更新状态索引"""
        self._status_index[old_status].discard(task_id)
        self._status_index[new_status].add(task_id)
    
    def _add_history(self, action: str, task: Task, extra: Optional[Dict] = None):
        """添加历史记录"""
        record = {
            'timestamp': time.time(),
            'action': action,
            'task_id': task.id,
            'task_name': task.name,
            'status': task.status.value,
            'extra': extra or {}
        }
        
        self._history.append(record)
        
        # 保持历史记录大小
        if len(self._history) > self._max_history_size:
            self._history = self._history[-self._max_history_size:]
    
    def _trigger_callbacks(self, status: TaskStatus, task: Task):
        """触发状态变更回调"""
        for callback in self._status_callbacks.get(status, []):
            try:
                callback(task)
            except Exception as e:
                print(f"[TaskManager] Callback error: {e}")
    
    def register_status_callback(self, status: TaskStatus, callback: Callable):
        """注册状态变更回调"""
        self._status_callbacks[status].append(callback)
    
    def get_statistics(self) -> Dict:
        """获取任务统计信息"""
        return {
            'total_tasks': len(self._tasks),
            'pending': len(self._status_index[TaskStatus.PENDING]),
            'ready': len(self._status_index[TaskStatus.READY]),
            'running': len(self._status_index[TaskStatus.RUNNING]),
            'paused': len(self._status_index[TaskStatus.PAUSED]),
            'completed': len(self._status_index[TaskStatus.COMPLETED]),
            'failed': len(self._status_index[TaskStatus.FAILED]),
            'cancelled': len(self._status_index[TaskStatus.CANCELLED]),
            'max_concurrent': self.max_concurrent_tasks
        }
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """获取历史记录"""
        return self._history[-limit:]
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        with self._lock:
            completed_ids = list(self._status_index[TaskStatus.COMPLETED])
            for task_id in completed_ids:
                task = self._tasks.pop(task_id, None)
                if task:
                    self._priority_index[task.priority].discard(task_id)
                    self._dependency_graph.pop(task_id, None)
                    self._reverse_dependency.pop(task_id, None)
            
            self._status_index[TaskStatus.COMPLETED].clear()
            print(f"[TaskManager] Cleared {len(completed_ids)} completed tasks")
    
    def create_subtask(self, parent_id: str, name: str, **kwargs) -> Task:
        """
        创建子任务
        
        Args:
            parent_id: 父任务ID
            name: 子任务名称
            **kwargs: 其他任务参数
            
        Returns:
            子任务对象
        """
        parent = self._tasks.get(parent_id)
        if not parent:
            raise ValueError(f"Parent task {parent_id} not found")
        
        subtask = Task(
            name=name,
            parent_id=parent_id,
            priority=parent.priority,
            **kwargs
        )
        
        parent.subtasks.append(subtask.id)
        self.add_task(subtask)
        
        return subtask
    
    def get_task_tree(self, task_id: str) -> Dict:
        """获取任务树结构"""
        task = self._tasks.get(task_id)
        if not task:
            return {}
        
        tree = task.to_dict()
        tree['subtasks'] = []
        
        for subtask_id in task.subtasks:
            tree['subtasks'].append(self.get_task_tree(subtask_id))
        
        return tree
    
    def get_all_tasks(self) -> List[Task]:
        """获取所有任务"""
        return list(self._tasks.values())
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """按状态获取任务"""
        return [self._tasks[tid] for tid in self._status_index[status] 
                if tid in self._tasks]
    
    def get_active_task_count(self) -> int:
        """获取活跃任务数量"""
        return len(self._status_index[TaskStatus.RUNNING]) + \
               len(self._status_index[TaskStatus.READY]) + \
               len(self._status_index[TaskStatus.PENDING])
