# -*- coding: utf-8 -*-
"""
Base Skill - 技能基类
定义所有技能的通用接口和功能
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading


class SkillStatus(Enum):
    """技能状态枚举"""
    IDLE = "idle"
    PREPARING = "preparing"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SkillResult:
    """
    技能执行结果
    
    Attributes:
        success: 是否成功
        data: 结果数据
        error: 错误信息
        error_type: 错误类型
        feedback: 反馈信息
        execution_time: 执行时间
    """
    success: bool = False
    data: Dict = field(default_factory=dict)
    error: Optional[str] = None
    error_type: Optional[str] = None
    feedback: Dict = field(default_factory=dict)
    execution_time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'error_type': self.error_type,
            'feedback': self.feedback,
            'execution_time': self.execution_time
        }


@dataclass
class SkillContext:
    """
    技能执行上下文
    
    Attributes:
        robot_state: 机器人状态
        perception_data: 感知数据
        environment: 环境信息
        constraints: 约束条件
    """
    robot_state: Dict = field(default_factory=dict)
    perception_data: Dict = field(default_factory=dict)
    environment: Dict = field(default_factory=dict)
    constraints: Dict = field(default_factory=dict)
    history: List[Dict] = field(default_factory=list)


class BaseSkill:
    """
    技能基类
    
    定义所有技能的通用接口和功能
    
    Attributes:
        name: 技能名称
        description: 技能描述
        version: 版本号
        status: 当前状态
    """
    
    def __init__(self, name: str, description: str = "", version: str = "1.0.0"):
        """
        初始化技能
        
        Args:
            name: 技能名称
            description: 技能描述
            version: 版本号
        """
        self.name = name
        self.description = description
        self.version = version
        self.status = SkillStatus.IDLE
        
        # 执行上下文
        self._context: Optional[SkillContext] = None
        self._parameters: Dict = {}
        
        # 进度追踪
        self._progress: float = 0.0
        self._start_time: Optional[float] = None
        
        # 回调
        self._progress_callbacks: List[Callable] = []
        self._feedback_callbacks: List[Callable] = []
        
        # 线程控制
        self._lock = threading.RLock()
        self._cancellation_requested = False
        
        # ROS2接口
        self._ros2_bridge = None
        self._joint_monitor = None
        
    def set_ros2_bridge(self, bridge: Any):
        """设置ROS2桥接"""
        self._ros2_bridge = bridge
    
    def set_joint_monitor(self, monitor: Any):
        """设置关节监测器"""
        self._joint_monitor = monitor
    
    def add_progress_callback(self, callback: Callable):
        """添加进度回调"""
        self._progress_callbacks.append(callback)
    
    def add_feedback_callback(self, callback: Callable):
        """添加反馈回调"""
        self._feedback_callbacks.append(callback)
    
    def _update_progress(self, progress: float, message: str = ""):
        """更新进度"""
        with self._lock:
            self._progress = progress
        
        for callback in self._progress_callbacks:
            try:
                callback(progress, message)
            except Exception as e:
                print(f"[{self.name}] Progress callback error: {e}")
    
    def _send_feedback(self, feedback_type: str, data: Dict):
        """发送反馈"""
        feedback = {
            'skill': self.name,
            'type': feedback_type,
            'data': data,
            'timestamp': time.time()
        }
        
        for callback in self._feedback_callbacks:
            try:
                callback(feedback)
            except Exception as e:
                print(f"[{self.name}] Feedback callback error: {e}")
    
    async def execute(self, parameters: Dict, context: Any = None) -> SkillResult:
        """
        执行技能
        
        Args:
            parameters: 技能参数
            context: 执行上下文
            
        Returns:
            执行结果
        """
        self._start_time = time.time()
        self._parameters = parameters
        self._cancellation_requested = False
        self._progress = 0.0
        
        # 验证参数
        validation_result = self.validate_parameters(parameters)
        if not validation_result['valid']:
            return SkillResult(
                success=False,
                error=validation_result['error'],
                error_type='ValidationError'
            )
        
        try:
            self.status = SkillStatus.PREPARING
            
            # 准备阶段
            await self.prepare(parameters, context)
            
            if self._cancellation_requested:
                self.status = SkillStatus.CANCELLED
                return SkillResult(success=False, error='Cancelled during preparation')
            
            self.status = SkillStatus.EXECUTING
            
            # 执行阶段
            result = await self.run(parameters, context)
            
            # 计算执行时间
            execution_time = time.time() - self._start_time
            
            if self._cancellation_requested:
                self.status = SkillStatus.CANCELLED
                return SkillResult(
                    success=False,
                    error='Cancelled during execution',
                    execution_time=execution_time
                )
            
            if result.success:
                self.status = SkillStatus.COMPLETED
                self._progress = 100.0
            else:
                self.status = SkillStatus.FAILED
            
            result.execution_time = execution_time
            return result
            
        except asyncio.CancelledError:
            self.status = SkillStatus.CANCELLED
            return SkillResult(
                success=False,
                error='Skill execution cancelled',
                error_type='CancellationError',
                execution_time=time.time() - self._start_time
            )
            
        except Exception as e:
            self.status = SkillStatus.FAILED
            import traceback
            return SkillResult(
                success=False,
                error=str(e),
                error_type=type(e).__name__,
                feedback={'traceback': traceback.format_exc()},
                execution_time=time.time() - self._start_time
            )
    
    def validate_parameters(self, parameters: Dict) -> Dict:
        """
        验证参数
        
        Args:
            parameters: 参数字典
            
        Returns:
            验证结果 {'valid': bool, 'error': str}
        """
        return {'valid': True}
    
    async def prepare(self, parameters: Dict, context: Any):
        """
        准备阶段
        
        子类可以重写此方法实现准备工作
        
        Args:
            parameters: 参数
            context: 上下文
        """
        self._update_progress(0.0, "Preparing...")
        await asyncio.sleep(0.1)  # 给出时间让状态更新
    
    async def run(self, parameters: Dict, context: Any) -> SkillResult:
        """
        执行阶段
        
        子类必须重写此方法实现具体功能
        
        Args:
            parameters: 参数
            context: 上下文
            
        Returns:
            执行结果
        """
        raise NotImplementedError("Subclasses must implement run()")
    
    def cancel(self):
        """请求取消"""
        self._cancellation_requested = True
    
    def pause(self):
        """暂停"""
        if self.status == SkillStatus.EXECUTING:
            self.status = SkillStatus.PAUSED
    
    def resume(self):
        """恢复"""
        if self.status == SkillStatus.PAUSED:
            self.status = SkillStatus.EXECUTING
    
    def get_status(self) -> SkillStatus:
        """获取当前状态"""
        return self.status
    
    def get_progress(self) -> float:
        """获取当前进度"""
        return self._progress
    
    def get_info(self) -> Dict:
        """获取技能信息"""
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'status': self.status.value,
            'progress': self._progress
        }
    
    def get_required_resources(self) -> Dict:
        """
        获取所需资源
        
        Returns:
            资源需求字典
        """
        return {
            'sensors': [],
            'actuators': [],
            'compute': 0.5,
            'memory': 256
        }
    
    def get_timeout(self) -> float:
        """获取超时时间"""
        return 60.0
    
    @staticmethod
    def get_parameter_schema() -> Dict:
        """
        获取参数模式
        
        Returns:
            JSON Schema格式的参数定义
        """
        return {
            'type': 'object',
            'properties': {}
        }
