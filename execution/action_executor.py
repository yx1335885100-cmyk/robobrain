# -*- coding: utf-8 -*-
"""
Action Executor - 动作执行器
负责动作的具体执行和监控
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading


class ActionStatus(Enum):
    """动作状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ActionExecution:
    """动作执行记录"""
    action_id: str
    action_type: str
    status: ActionStatus = ActionStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Dict = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            'action_id': self.action_id,
            'action_type': self.action_type,
            'status': self.status.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'result': self.result,
            'error': self.error
        }


class ActionExecutor:
    """
    动作执行器
    
    负责动作的具体执行和监控
    
    Features:
        - 动作执行
        - 状态监控
        - 超时处理
        - 错误恢复
        - 执行日志
    """
    
    def __init__(self):
        """初始化动作执行器"""
        self._executions: Dict[str, ActionExecution] = []
        self._current_execution: Optional[ActionExecution] = None
        
        # 动作处理器
        self._action_handlers: Dict[str, Callable] = {}
        
        # ROS2接口
        self._ros2_bridge = None
        
        # 回调
        self._completion_callbacks: List[Callable] = []
        
        # 统计
        self._stats = {
            'total_executed': 0,
            'successful': 0,
            'failed': 0
        }
        
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """注册默认动作处理器"""
        self._action_handlers['move_to'] = self._handle_move_to
        self._action_handlers['grasp'] = self._handle_grasp
        self._action_handlers['place'] = self._handle_place
        self._action_handlers['perceive'] = self._handle_perceive
        self._action_handlers['speak'] = self._handle_speak
        self._action_handlers['wait'] = self._handle_wait
    
    def set_ros2_bridge(self, bridge: Any):
        """设置ROS2桥接"""
        self._ros2_bridge = bridge
    
    def register_handler(self, action_type: str, handler: Callable):
        """注册动作处理器"""
        self._action_handlers[action_type] = handler
    
    async def execute(self, action: Dict, context: Optional[Dict] = None) -> Dict:
        """
        执行动作
        
        Args:
            action: 动作定义
            context: 执行上下文
            
        Returns:
            执行结果
        """
        action_id = action.get('id', f"action_{int(time.time()*1000)}")
        action_type = action.get('type', 'unknown')
        
        execution = ActionExecution(
            action_id=action_id,
            action_type=action_type,
            status=ActionStatus.RUNNING,
            start_time=time.time()
        )
        
        self._current_execution = execution
        self._stats['total_executed'] += 1
        
        try:
            # 获取处理器
            handler = self._action_handlers.get(action_type)
            
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    result = await handler(action, context)
                else:
                    result = handler(action, context)
            else:
                result = await self._handle_unknown(action, context)
            
            execution.status = ActionStatus.COMPLETED
            execution.result = result
            self._stats['successful'] += 1
            
        except asyncio.CancelledError:
            execution.status = ActionStatus.CANCELLED
            execution.error = "Action cancelled"
            
        except Exception as e:
            execution.status = ActionStatus.FAILED
            execution.error = str(e)
            self._stats['failed'] += 1
            result = {'success': False, 'error': str(e)}
        
        execution.end_time = time.time()
        self._executions.append(execution)
        self._current_execution = None
        
        # 触发完成回调
        for callback in self._completion_callbacks:
            try:
                callback(execution)
            except Exception as e:
                print(f"[ActionExecutor] Completion callback error: {e}")
        
        return {
            'success': execution.status == ActionStatus.COMPLETED,
            'result': execution.result,
            'error': execution.error,
            'duration': execution.end_time - execution.start_time if execution.end_time else 0
        }
    
    async def _handle_move_to(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理移动动作"""
        params = action.get('params', {})
        target = params.get('target')
        speed = params.get('speed', 0.5)
        
        # 模拟移动
        await asyncio.sleep(0.5)
        
        return {
            'success': True,
            'position': target,
            'message': f'Moved to {target} at speed {speed}'
        }
    
    async def _handle_grasp(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理抓取动作"""
        params = action.get('params', {})
        obj = params.get('object', 'unknown')
        
        await asyncio.sleep(0.3)
        
        return {
            'success': True,
            'object': obj,
            'message': f'Grasped {obj}'
        }
    
    async def _handle_place(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理放置动作"""
        params = action.get('params', {})
        position = params.get('position')
        
        await asyncio.sleep(0.3)
        
        return {
            'success': True,
            'position': position,
            'message': 'Object placed'
        }
    
    async def _handle_perceive(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理感知动作"""
        params = action.get('params', {})
        target = params.get('target', 'scene')
        
        await asyncio.sleep(0.2)
        
        return {
            'success': True,
            'target': target,
            'objects_detected': [],
            'message': f'Perceived {target}'
        }
    
    async def _handle_speak(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理语音动作"""
        params = action.get('params', {})
        message = params.get('message', '')
        
        await asyncio.sleep(len(message) * 0.05)  # 模拟说话时间
        
        return {
            'success': True,
            'message': message,
            'spoken': True
        }
    
    async def _handle_wait(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理等待动作"""
        params = action.get('params', {})
        duration = params.get('duration', 1.0)
        
        await asyncio.sleep(duration)
        
        return {
            'success': True,
            'waited': duration
        }
    
    async def _handle_unknown(self, action: Dict, context: Optional[Dict]) -> Dict:
        """处理未知动作"""
        return {
            'success': False,
            'error': f"Unknown action type: {action.get('type')}"
        }
    
    def add_completion_callback(self, callback: Callable):
        """添加完成回调"""
        self._completion_callbacks.append(callback)
    
    def get_current_execution(self) -> Optional[ActionExecution]:
        """获取当前执行"""
        return self._current_execution
    
    def get_execution_history(self, limit: int = 50) -> List[ActionExecution]:
        """获取执行历史"""
        return self._executions[-limit:]
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            'success_rate': self._stats['successful'] / self._stats['total_executed'] 
                           if self._stats['total_executed'] > 0 else 0
        }
