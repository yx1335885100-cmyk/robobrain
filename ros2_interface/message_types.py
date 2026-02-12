# -*- coding: utf-8 -*-
"""
Message Types - 消息类型定义
定义机器人智慧大脑使用的自定义消息类型
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import time
import json


@dataclass
class JointStateMsg:
    """
    关节状态消息
    
    Attributes:
        header: 消息头
        name: 关节名称列表
        position: 位置列表
        velocity: 速度列表
        effort: 力矩列表
    """
    header: Dict = field(default_factory=lambda: {'stamp': time.time(), 'frame_id': ''})
    name: List[str] = field(default_factory=list)
    position: List[float] = field(default_factory=list)
    velocity: List[float] = field(default_factory=list)
    effort: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'header': self.header,
            'name': self.name,
            'position': self.position,
            'velocity': self.velocity,
            'effort': self.effort
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'JointStateMsg':
        return cls(
            header=data.get('header', {}),
            name=data.get('name', []),
            position=data.get('position', []),
            velocity=data.get('velocity', []),
            effort=data.get('effort', [])
        )


@dataclass
class TaskStatusMsg:
    """
    任务状态消息
    
    Attributes:
        task_id: 任务ID
        task_name: 任务名称
        status: 任务状态
        progress: 进度
        result: 结果
        error: 错误信息
    """
    task_id: str = ""
    task_name: str = ""
    status: str = "pending"
    progress: float = 0.0
    result: Dict = field(default_factory=dict)
    error: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'task_id': self.task_id,
            'task_name': self.task_name,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskStatusMsg':
        return cls(
            task_id=data.get('task_id', ''),
            task_name=data.get('task_name', ''),
            status=data.get('status', 'pending'),
            progress=data.get('progress', 0.0),
            result=data.get('result', {}),
            error=data.get('error', ''),
            timestamp=data.get('timestamp', time.time())
        )


@dataclass
class PerceptionMsg:
    """
    感知消息
    
    Attributes:
        modality: 感知模态 (audio, visual, tactile, etc.)
        data: 感知数据
        metadata: 元数据
        confidence: 置信度
    """
    modality: str = ""
    data: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'modality': self.modality,
            'data': self.data,
            'metadata': self.metadata,
            'confidence': self.confidence,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PerceptionMsg':
        return cls(
            modality=data.get('modality', ''),
            data=data.get('data', {}),
            metadata=data.get('metadata', {}),
            confidence=data.get('confidence', 1.0),
            timestamp=data.get('timestamp', time.time())
        )


@dataclass
class ActionGoalMsg:
    """
    动作目标消息
    
    Attributes:
        action_name: 动作名称
        parameters: 动作参数
        constraints: 约束条件
        priority: 优先级
        timeout: 超时时间
    """
    action_name: str = ""
    parameters: Dict = field(default_factory=dict)
    constraints: Dict = field(default_factory=dict)
    priority: int = 2
    timeout: float = 30.0
    goal_id: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'action_name': self.action_name,
            'parameters': self.parameters,
            'constraints': self.constraints,
            'priority': self.priority,
            'timeout': self.timeout,
            'goal_id': self.goal_id,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ActionGoalMsg':
        return cls(
            action_name=data.get('action_name', ''),
            parameters=data.get('parameters', {}),
            constraints=data.get('constraints', {}),
            priority=data.get('priority', 2),
            timeout=data.get('timeout', 30.0),
            goal_id=data.get('goal_id', ''),
            timestamp=data.get('timestamp', time.time())
        )


@dataclass
class ActionResultMsg:
    """
    动作结果消息
    
    Attributes:
        goal_id: 目标ID
        status: 状态 (success, failure, aborted)
        result: 结果数据
        error: 错误信息
        execution_time: 执行时间
    """
    goal_id: str = ""
    status: str = "pending"
    result: Dict = field(default_factory=dict)
    error: str = ""
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'goal_id': self.goal_id,
            'status': self.status,
            'result': self.result,
            'error': self.error,
            'execution_time': self.execution_time,
            'timestamp': self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ActionResultMsg':
        return cls(
            goal_id=data.get('goal_id', ''),
            status=data.get('status', 'pending'),
            result=data.get('result', {}),
            error=data.get('error', ''),
            execution_time=data.get('execution_time', 0.0),
            timestamp=data.get('timestamp', time.time())
        )


@dataclass
class SkillRequestMsg:
    """
    技能请求消息
    
    Attributes:
        skill_name: 技能名称
        parameters: 技能参数
        context: 执行上下文
    """
    skill_name: str = ""
    parameters: Dict = field(default_factory=dict)
    context: Dict = field(default_factory=dict)
    request_id: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'skill_name': self.skill_name,
            'parameters': self.parameters,
            'context': self.context,
            'request_id': self.request_id,
            'timestamp': self.timestamp
        }


@dataclass
class SkillResponseMsg:
    """
    技能响应消息
    
    Attributes:
        request_id: 请求ID
        success: 是否成功
        result: 结果数据
        feedback: 反馈信息
    """
    request_id: str = ""
    success: bool = False
    result: Dict = field(default_factory=dict)
    feedback: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'request_id': self.request_id,
            'success': self.success,
            'result': self.result,
            'feedback': self.feedback,
            'timestamp': self.timestamp
        }


@dataclass
class PlanningRequestMsg:
    """
    规划请求消息
    
    Attributes:
        goal: 目标描述
        context: 规划上下文
        constraints: 约束条件
        strategy: 规划策略
    """
    goal: str = ""
    context: Dict = field(default_factory=dict)
    constraints: Dict = field(default_factory=dict)
    strategy: str = "hierarchical"
    request_id: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'goal': self.goal,
            'context': self.context,
            'constraints': self.constraints,
            'strategy': self.strategy,
            'request_id': self.request_id,
            'timestamp': self.timestamp
        }


@dataclass
class PlanningResultMsg:
    """
    规划结果消息
    
    Attributes:
        request_id: 请求ID
        success: 是否成功
        plan: 规划结果
        estimated_duration: 估计执行时间
    """
    request_id: str = ""
    success: bool = False
    plan: List[Dict] = field(default_factory=list)
    estimated_duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'request_id': self.request_id,
            'success': self.success,
            'plan': self.plan,
            'estimated_duration': self.estimated_duration,
            'timestamp': self.timestamp
        }


@dataclass
class FeedbackMsg:
    """
    反馈消息
    
    Attributes:
        feedback_type: 反馈类型
        source: 反馈来源
        content: 反馈内容
        severity: 严重程度
    """
    feedback_type: str = ""
    source: str = ""
    content: Dict = field(default_factory=dict)
    severity: str = "info"  # info, warning, error, critical
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'feedback_type': self.feedback_type,
            'source': self.source,
            'content': self.content,
            'severity': self.severity,
            'timestamp': self.timestamp
        }


@dataclass
class BrainStateMsg:
    """
    大脑状态消息
    
    Attributes:
        state: 当前状态
        current_task: 当前任务
        active_skills: 活跃技能
        resource_usage: 资源使用情况
    """
    state: str = "idle"
    current_task: str = ""
    active_skills: List[str] = field(default_factory=list)
    resource_usage: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'state': self.state,
            'current_task': self.current_task,
            'active_skills': self.active_skills,
            'resource_usage': self.resource_usage,
            'timestamp': self.timestamp
        }


def serialize_message(msg) -> str:
    """序列化消息为JSON字符串"""
    if hasattr(msg, 'to_dict'):
        return json.dumps(msg.to_dict())
    return json.dumps(msg)


def deserialize_message(msg_class, json_str: str):
    """从JSON字符串反序列化消息"""
    data = json.loads(json_str)
    if hasattr(msg_class, 'from_dict'):
        return msg_class.from_dict(data)
    return data
