# -*- coding: utf-8 -*-
"""
Task Executor - 任务执行器
支持任务编排、技能执行、动作执行、执行监控和反馈
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import traceback

from .task_manager import Task, TaskStatus


class ExecutionMode(Enum):
    """执行模式枚举"""
    SEQUENTIAL = "sequential"    # 顺序执行
    PARALLEL = "parallel"        # 并行执行
    PIPELINE = "pipeline"        # 流水线执行
    ADAPTIVE = "adaptive"        # 自适应执行


class ExecutionState(Enum):
    """执行状态枚举"""
    IDLE = "idle"
    PREPARING = "preparing"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """执行结果"""
    task_id: str
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    execution_time: float = 0.0
    feedback: Dict = field(default_factory=dict)


@dataclass
class ExecutionContext:
    """执行上下文"""
    task_id: str
    start_time: float = field(default_factory=time.time)
    current_action: str = ""
    progress: float = 0.0
    state: ExecutionState = ExecutionState.IDLE
    checkpoints: List[Dict] = field(default_factory=list)
    rollback_data: Dict = field(default_factory=dict)


class TaskExecutor:
    """
    任务执行器
    
    提供任务执行、编排、监控和反馈功能
    
    Features:
        - 多种执行模式（顺序、并行、流水线）
        - 技能调用和编排
        - 执行状态监控
        - 进度追踪
        - 错误处理和恢复
        - 执行反馈收集
        - 检查点和回滚机制
    """
    
    def __init__(self, execution_mode: str = 'sequential'):
        """
        初始化任务执行器
        
        Args:
            execution_mode: 执行模式
        """
        self.mode = ExecutionMode(execution_mode)
        
        # 技能注册表
        self._skills: Dict[str, Any] = {}
        
        # 执行上下文
        self._execution_contexts: Dict[str, ExecutionContext] = {}
        
        # 执行历史
        self._execution_history: List[ExecutionResult] = []
        self._max_history = 1000
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 执行回调
        self._pre_execution_callbacks: List[Callable] = []
        self._post_execution_callbacks: List[Callable] = []
        self._progress_callbacks: List[Callable] = []
        
        # ROS2相关
        self._ros2_bridge = None
        
        # 执行控制
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._cancellation_requested: Set[str] = set()
        
    def register_skill(self, name: str, skill_class: Any):
        """注册技能"""
        self._skills[name] = skill_class
        print(f"[TaskExecutor] Skill registered: {name}")
    
    def set_ros2_bridge(self, bridge: Any):
        """设置ROS2桥接"""
        self._ros2_bridge = bridge
    
    def add_pre_execution_callback(self, callback: Callable):
        """添加执行前回调"""
        self._pre_execution_callbacks.append(callback)
    
    def add_post_execution_callback(self, callback: Callable):
        """添加执行后回调"""
        self._post_execution_callbacks.append(callback)
    
    def add_progress_callback(self, callback: Callable):
        """添加进度更新回调"""
        self._progress_callbacks.append(callback)
    
    async def execute(self, task: Task, context: Any = None,
                     skill_registry: Dict = None,
                     ros2_bridge: Any = None) -> Dict:
        """
        执行任务
        
        Args:
            task: 要执行的任务
            context: 执行上下文
            skill_registry: 技能注册表
            ros2_bridge: ROS2桥接
            
        Returns:
            执行结果字典
        """
        print(f"[TaskExecutor] Executing task: {task.id} - {task.name}")
        
        start_time = time.time()
        execution_context = ExecutionContext(task_id=task.id)
        self._execution_contexts[task.id] = execution_context
        
        # 触发执行前回调
        await self._trigger_pre_execution_callbacks(task)
        
        try:
            execution_context.state = ExecutionState.PREPARING
            
            # 准备执行环境
            await self._prepare_execution(task, context)
            
            execution_context.state = ExecutionState.EXECUTING
            
            # 执行任务
            if task.skill:
                result = await self._execute_skill_task(task, context, skill_registry)
            elif 'action' in task.parameters:
                result = await self._execute_action_task(task, ros2_bridge)
            else:
                result = await self._execute_generic_task(task, context)
            
            # 更新执行状态
            execution_context.progress = 100.0
            execution_context.state = ExecutionState.COMPLETED
            
            execution_result = ExecutionResult(
                task_id=task.id,
                success=result.get('success', True),
                data=result.get('data'),
                error=result.get('error'),
                error_type=result.get('error_type'),
                execution_time=time.time() - start_time,
                feedback=result.get('feedback', {})
            )
            
        except asyncio.CancelledError:
            execution_context.state = ExecutionState.CANCELLED
            execution_result = ExecutionResult(
                task_id=task.id,
                success=False,
                error="Task cancelled",
                error_type="CancellationError",
                execution_time=time.time() - start_time
            )
            
        except Exception as e:
            execution_context.state = ExecutionState.FAILED
            execution_result = ExecutionResult(
                task_id=task.id,
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                execution_time=time.time() - start_time,
                feedback={'traceback': traceback.format_exc()}
            )
        
        # 记录历史
        self._execution_history.append(execution_result)
        if len(self._execution_history) > self._max_history:
            self._execution_history = self._execution_history[-self._max_history:]
        
        # 触发执行后回调
        await self._trigger_post_execution_callbacks(task, execution_result)
        
        return {
            'success': execution_result.success,
            'data': execution_result.data,
            'error': execution_result.error,
            'error_type': execution_result.error_type,
            'execution_time': execution_result.execution_time,
            'feedback': execution_result.feedback
        }
    
    async def _prepare_execution(self, task: Task, context: Any):
        """准备执行环境"""
        # 创建检查点
        checkpoint = {
            'timestamp': time.time(),
            'task_id': task.id,
            'type': 'pre_execution'
        }
        
        if self._execution_contexts.get(task.id):
            self._execution_contexts[task.id].checkpoints.append(checkpoint)
    
    async def _execute_skill_task(self, task: Task, context: Any,
                                  skill_registry: Dict) -> Dict:
        """执行技能任务"""
        skill_name = task.skill
        skill_params = task.parameters
        
        # 获取技能实例
        skill_class = None
        if skill_registry and skill_name in skill_registry:
            skill_class = skill_registry[skill_name]
        elif skill_name in self._skills:
            skill_class = self._skills[skill_name]
        
        if skill_class is None:
            return {
                'success': False,
                'error': f'Skill not found: {skill_name}',
                'error_type': 'SkillNotFoundError'
            }
        
        try:
            # 实例化技能
            if isinstance(skill_class, type):
                skill = skill_class()
            else:
                skill = skill_class
            
            # 执行技能
            print(f"[TaskExecutor] Executing skill: {skill_name}")
            
            if asyncio.iscoroutinefunction(skill.execute):
                result = await skill.execute(skill_params, context)
            else:
                result = skill.execute(skill_params, context)
            
            # 更新进度
            await self._update_progress(task.id, 100.0)
            
            # 处理SkillResult对象或字典
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            else:
                result_dict = result if isinstance(result, dict) else {'success': False, 'error': 'Invalid result type'}
            
            return {
                'success': result_dict.get('success', True),
                'data': result_dict.get('data'),
                'error': result_dict.get('error'),
                'error_type': result_dict.get('error_type'),
                'feedback': result_dict.get('feedback', {})
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    async def _execute_action_task(self, task: Task, ros2_bridge: Any) -> Dict:
        """执行动作任务"""
        action_name = task.parameters.get('action')
        action_params = task.parameters.get('parameters', {})
        
        print(f"[TaskExecutor] Executing action: {action_name}")
        
        if ros2_bridge is None:
            return {
                'success': False,
                'error': 'ROS2 bridge not available',
                'error_type': 'BridgeNotAvailableError'
            }
        
        try:
            # 通过ROS2桥接执行动作
            result = await ros2_bridge.execute_action(action_name, action_params)
            
            await self._update_progress(task.id, 100.0)
            
            return {
                'success': result.get('success', True),
                'data': result.get('data'),
                'error': result.get('error'),
                'feedback': result.get('feedback', {})
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    async def _execute_generic_task(self, task: Task, context: Any) -> Dict:
        """执行通用任务"""
        print(f"[TaskExecutor] Executing generic task: {task.name}")
        
        # 模拟任务执行
        await asyncio.sleep(0.1)
        
        await self._update_progress(task.id, 100.0)
        
        return {
            'success': True,
            'data': {'message': f'Task {task.name} completed'},
            'feedback': {}
        }
    
    async def _update_progress(self, task_id: str, progress: float):
        """更新执行进度"""
        if task_id in self._execution_contexts:
            self._execution_contexts[task_id].progress = progress
        
        # 触发进度回调
        for callback in self._progress_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, progress)
                else:
                    callback(task_id, progress)
            except Exception as e:
                print(f"[TaskExecutor] Progress callback error: {e}")
    
    async def _trigger_pre_execution_callbacks(self, task: Task):
        """触发执行前回调"""
        for callback in self._pre_execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task)
                else:
                    callback(task)
            except Exception as e:
                print(f"[TaskExecutor] Pre-execution callback error: {e}")
    
    async def _trigger_post_execution_callbacks(self, task: Task, result: ExecutionResult):
        """触发执行后回调"""
        for callback in self._post_execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task, result)
                else:
                    callback(task, result)
            except Exception as e:
                print(f"[TaskExecutor] Post-execution callback error: {e}")
    
    async def execute_batch(self, tasks: List[Task], mode: str = None) -> List[Dict]:
        """
        批量执行任务
        
        Args:
            tasks: 任务列表
            mode: 执行模式覆盖
            
        Returns:
            执行结果列表
        """
        execution_mode = ExecutionMode(mode) if mode else self.mode
        
        if execution_mode == ExecutionMode.PARALLEL:
            return await self._execute_parallel(tasks)
        elif execution_mode == ExecutionMode.PIPELINE:
            return await self._execute_pipeline(tasks)
        else:
            return await self._execute_sequential(tasks)
    
    async def _execute_sequential(self, tasks: List[Task]) -> List[Dict]:
        """顺序执行任务"""
        results = []
        for task in tasks:
            result = await self.execute(task)
            results.append(result)
            
            # 如果任务失败，决定是否继续
            if not result.get('success'):
                # 可以添加重试逻辑或停止执行
                pass
        
        return results
    
    async def _execute_parallel(self, tasks: List[Task]) -> List[Dict]:
        """并行执行任务"""
        execution_tasks = [self.execute(task) for task in tasks]
        results = await asyncio.gather(*execution_tasks, return_exceptions=True)
        
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    'success': False,
                    'error': str(result),
                    'error_type': type(result).__name__
                })
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _execute_pipeline(self, tasks: List[Task]) -> List[Dict]:
        """流水线执行任务"""
        results = []
        previous_result = None
        
        for task in tasks:
            # 将前一个任务的结果作为输入
            if previous_result:
                task.parameters['previous_result'] = previous_result
            
            result = await self.execute(task)
            results.append(result)
            previous_result = result
            
            # 流水线中如果某步骤失败，停止流水线
            if not result.get('success'):
                break
        
        return results
    
    def get_execution_context(self, task_id: str) -> Optional[ExecutionContext]:
        """获取执行上下文"""
        return self._execution_contexts.get(task_id)
    
    def get_execution_progress(self, task_id: str) -> float:
        """获取执行进度"""
        context = self._execution_contexts.get(task_id)
        return context.progress if context else 0.0
    
    def get_execution_state(self, task_id: str) -> ExecutionState:
        """获取执行状态"""
        context = self._execution_contexts.get(task_id)
        return context.state if context else ExecutionState.IDLE
    
    def cancel_execution(self, task_id: str) -> bool:
        """
        取消任务执行
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        if task_id in self._running_tasks:
            self._cancellation_requested.add(task_id)
            self._running_tasks[task_id].cancel()
            
            if task_id in self._execution_contexts:
                self._execution_contexts[task_id].state = ExecutionState.CANCELLED
            
            return True
        
        return False
    
    def pause_execution(self, task_id: str) -> bool:
        """暂停执行"""
        if task_id in self._execution_contexts:
            self._execution_contexts[task_id].state = ExecutionState.PAUSED
            return True
        return False
    
    def resume_execution(self, task_id: str) -> bool:
        """恢复执行"""
        if task_id in self._execution_contexts:
            context = self._execution_contexts[task_id]
            if context.state == ExecutionState.PAUSED:
                context.state = ExecutionState.EXECUTING
                return True
        return False
    
    def create_checkpoint(self, task_id: str, data: Dict = None) -> bool:
        """创建检查点"""
        if task_id not in self._execution_contexts:
            return False
        
        checkpoint = {
            'timestamp': time.time(),
            'task_id': task_id,
            'type': 'user_created',
            'data': data or {}
        }
        
        self._execution_contexts[task_id].checkpoints.append(checkpoint)
        return True
    
    def rollback_to_checkpoint(self, task_id: str, checkpoint_index: int = -1) -> bool:
        """回滚到检查点"""
        context = self._execution_contexts.get(task_id)
        if not context or not context.checkpoints:
            return False
        
        if abs(checkpoint_index) >= len(context.checkpoints):
            return False
        
        checkpoint = context.checkpoints[checkpoint_index]
        print(f"[TaskExecutor] Rolling back task {task_id} to checkpoint at {checkpoint['timestamp']}")
        
        # 这里可以实现具体的回滚逻辑
        return True
    
    def get_execution_history(self, limit: int = 100) -> List[ExecutionResult]:
        """获取执行历史"""
        return self._execution_history[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取执行统计"""
        if not self._execution_history:
            return {
                'total_executed': 0,
                'success_rate': 0,
                'average_execution_time': 0
            }
        
        total = len(self._execution_history)
        successful = sum(1 for r in self._execution_history if r.success)
        avg_time = sum(r.execution_time for r in self._execution_history) / total
        
        return {
            'total_executed': total,
            'successful': successful,
            'failed': total - successful,
            'success_rate': successful / total if total > 0 else 0,
            'average_execution_time': avg_time,
            'active_executions': len([c for c in self._execution_contexts.values() 
                                     if c.state == ExecutionState.EXECUTING])
        }
    
    def clear_history(self):
        """清理执行历史"""
        self._execution_history.clear()
        self._execution_contexts.clear()
