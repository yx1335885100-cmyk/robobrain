# -*- coding: utf-8 -*-
"""
Feedback Handler - 反馈处理器
处理任务执行过程中的反馈和结果
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from queue import Queue


class FeedbackType(Enum):
    """反馈类型"""
    PROGRESS = "progress"
    STATUS = "status"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    RESULT = "result"


@dataclass
class Feedback:
    """反馈数据"""
    type: FeedbackType
    source: str
    message: str
    data: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    severity: int = 0  # 0=info, 1=warning, 2=error, 3=critical
    
    def to_dict(self) -> Dict:
        return {
            'type': self.type.value,
            'source': self.source,
            'message': self.message,
            'data': self.data,
            'timestamp': self.timestamp,
            'severity': self.severity
        }


class FeedbackHandler:
    """
    反馈处理器
    
    处理任务执行过程中的反馈和结果
    
    Features:
        - 反馈收集
        - 反馈分发
        - 错误处理
        - 警告管理
        - 反馈历史
        - 回调机制
    """
    
    def __init__(self, max_history: int = 1000):
        """
        初始化反馈处理器
        
        Args:
            max_history: 最大历史记录数
        """
        self._max_history = max_history
        
        # 反馈队列
        self._feedback_queue: Queue = Queue()
        
        # 反馈历史
        self._history: List[Feedback] = []
        
        # 回调
        self._callbacks: Dict[FeedbackType, List[Callable]] = {}
        self._global_callbacks: List[Callable] = []
        
        # 错误追踪
        self._errors: List[Feedback] = []
        self._warnings: List[Feedback] = []
        
        # 线程控制
        self._running = False
        self._lock = threading.RLock()
        
        # 统计
        self._stats = {
            'total_feedback': 0,
            'errors': 0,
            'warnings': 0
        }
    
    def start(self):
        """启动反馈处理器"""
        self._running = True
        print("[FeedbackHandler] Started")
    
    def stop(self):
        """停止反馈处理器"""
        self._running = False
        print("[FeedbackHandler] Stopped")
    
    def submit(self, feedback: Feedback):
        """
        提交反馈
        
        Args:
            feedback: 反馈数据
        """
        with self._lock:
            self._feedback_queue.put(feedback)
            self._history.append(feedback)
            self._stats['total_feedback'] += 1
            
            # 限制历史大小
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            
            # 错误追踪
            if feedback.type == FeedbackType.ERROR:
                self._errors.append(feedback)
                self._stats['errors'] += 1
            elif feedback.type == FeedbackType.WARNING:
                self._warnings.append(feedback)
                self._stats['warnings'] += 1
        
        # 触发回调
        self._trigger_callbacks(feedback)
    
    def submit_progress(self, source: str, progress: float, message: str = ""):
        """提交进度反馈"""
        self.submit(Feedback(
            type=FeedbackType.PROGRESS,
            source=source,
            message=message,
            data={'progress': progress}
        ))
    
    def submit_status(self, source: str, status: str, message: str = ""):
        """提交状态反馈"""
        self.submit(Feedback(
            type=FeedbackType.STATUS,
            source=source,
            message=message,
            data={'status': status}
        ))
    
    def submit_error(self, source: str, error: str, data: Dict = None, 
                    severity: int = 2):
        """提交错误反馈"""
        self.submit(Feedback(
            type=FeedbackType.ERROR,
            source=source,
            message=error,
            data=data or {},
            severity=severity
        ))
    
    def submit_warning(self, source: str, warning: str, data: Dict = None):
        """提交警告反馈"""
        self.submit(Feedback(
            type=FeedbackType.WARNING,
            source=source,
            message=warning,
            data=data or {},
            severity=1
        ))
    
    def submit_info(self, source: str, info: str, data: Dict = None):
        """提交信息反馈"""
        self.submit(Feedback(
            type=FeedbackType.INFO,
            source=source,
            message=info,
            data=data or {}
        ))
    
    def submit_result(self, source: str, result: Dict, message: str = ""):
        """提交结果反馈"""
        self.submit(Feedback(
            type=FeedbackType.RESULT,
            source=source,
            message=message,
            data=result
        ))
    
    def _trigger_callbacks(self, feedback: Feedback):
        """触发回调"""
        # 类型特定回调
        for callback in self._callbacks.get(feedback.type, []):
            try:
                callback(feedback)
            except Exception as e:
                print(f"[FeedbackHandler] Callback error: {e}")
        
        # 全局回调
        for callback in self._global_callbacks:
            try:
                callback(feedback)
            except Exception as e:
                print(f"[FeedbackHandler] Global callback error: {e}")
    
    def register_callback(self, feedback_type: FeedbackType, callback: Callable):
        """注册回调"""
        if feedback_type not in self._callbacks:
            self._callbacks[feedback_type] = []
        self._callbacks[feedback_type].append(callback)
    
    def register_global_callback(self, callback: Callable):
        """注册全局回调"""
        self._global_callbacks.append(callback)
    
    def get_history(self, limit: int = 100, feedback_type: FeedbackType = None) -> List[Feedback]:
        """获取反馈历史"""
        with self._lock:
            if feedback_type:
                return [f for f in self._history[-limit:] if f.type == feedback_type]
            return self._history[-limit:]
    
    def get_errors(self, limit: int = 50) -> List[Feedback]:
        """获取错误列表"""
        with self._lock:
            return self._errors[-limit:]
    
    def get_warnings(self, limit: int = 50) -> List[Feedback]:
        """获取警告列表"""
        with self._lock:
            return self._warnings[-limit:]
    
    def get_latest(self) -> Optional[Feedback]:
        """获取最新反馈"""
        with self._lock:
            return self._history[-1] if self._history else None
    
    def clear_history(self):
        """清除历史"""
        with self._lock:
            self._history.clear()
            self._errors.clear()
            self._warnings.clear()
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            'history_size': len(self._history),
            'queue_size': self._feedback_queue.qsize()
        }
    
    def has_pending_feedback(self) -> bool:
        """是否有待处理的反馈"""
        return not self._feedback_queue.empty()
    
    def get_next_feedback(self, timeout: float = None) -> Optional[Feedback]:
        """获取下一个反馈"""
        try:
            return self._feedback_queue.get(timeout=timeout)
        except:
            return None
