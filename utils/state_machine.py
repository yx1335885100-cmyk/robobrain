# -*- coding: utf-8 -*-
"""
State Machine - 状态机
提供状态管理和转换功能
"""

import time
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
import threading


@dataclass
class State:
    """状态定义"""
    name: str
    on_enter: Optional[Callable] = None
    on_exit: Optional[Callable] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Transition:
    """转换定义"""
    from_state: str
    to_state: str
    condition: Optional[Callable] = None
    on_transition: Optional[Callable] = None
    priority: int = 0


class StateMachine:
    """
    状态机
    
    提供状态管理和转换功能
    
    Features:
        - 状态定义
        - 转换规则
        - 条件转换
        - 回调支持
        - 状态历史
    """
    
    def __init__(self, initial_state: str = "idle"):
        """
        初始化状态机
        
        Args:
            initial_state: 初始状态
        """
        self._states: Dict[str, State] = {}
        self._transitions: List[Transition] = []
        self._current_state: str = initial_state
        
        # 状态历史
        self._history: List[Dict] = []
        self._max_history = 100
        
        # 回调
        self._state_change_callbacks: List[Callable] = []
        
        # 线程安全
        self._lock = threading.RLock()
        
        # 添加初始状态
        self.add_state(State(name=initial_state))
    
    def add_state(self, state: State):
        """添加状态"""
        with self._lock:
            self._states[state.name] = state
    
    def add_transition(self, transition: Transition):
        """添加转换"""
        with self._lock:
            self._transitions.append(transition)
            # 按优先级排序
            self._transitions.sort(key=lambda t: -t.priority)
    
    def get_state(self) -> str:
        """获取当前状态"""
        return self._current_state
    
    def can_transition_to(self, target_state: str) -> bool:
        """检查是否可以转换到目标状态"""
        for transition in self._transitions:
            if transition.from_state == self._current_state and \
               transition.to_state == target_state:
                if transition.condition is None or transition.condition():
                    return True
        return False
    
    def transition(self, target_state: str, force: bool = False) -> bool:
        """
        执行状态转换
        
        Args:
            target_state: 目标状态
            force: 是否强制转换
            
        Returns:
            是否转换成功
        """
        with self._lock:
            if not force and not self.can_transition_to(target_state):
                return False
            
            old_state = self._current_state
            
            # 执行退出回调
            if old_state in self._states and self._states[old_state].on_exit:
                try:
                    self._states[old_state].on_exit()
                except Exception as e:
                    print(f"[StateMachine] On exit error: {e}")
            
            # 执行转换回调
            for transition in self._transitions:
                if transition.from_state == old_state and \
                   transition.to_state == target_state:
                    if transition.on_transition:
                        try:
                            transition.on_transition()
                        except Exception as e:
                            print(f"[StateMachine] On transition error: {e}")
                    break
            
            # 更新状态
            self._current_state = target_state
            
            # 执行进入回调
            if target_state in self._states and self._states[target_state].on_enter:
                try:
                    self._states[target_state].on_enter()
                except Exception as e:
                    print(f"[StateMachine] On enter error: {e}")
            
            # 记录历史
            self._history.append({
                'from': old_state,
                'to': target_state,
                'timestamp': time.time(),
                'forced': force
            })
            
            if len(self._history) > self._max_history:
                self._history.pop(0)
            
            # 触发回调
            for callback in self._state_change_callbacks:
                try:
                    callback(old_state, target_state)
                except Exception as e:
                    print(f"[StateMachine] State change callback error: {e}")
            
            return True
    
    def get_available_transitions(self) -> List[str]:
        """获取可用的转换目标"""
        available = []
        for transition in self._transitions:
            if transition.from_state == self._current_state:
                if transition.condition is None or transition.condition():
                    available.append(transition.to_state)
        return available
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取历史"""
        return self._history[-limit:]
    
    def add_state_change_callback(self, callback: Callable):
        """添加状态变化回调"""
        self._state_change_callbacks.append(callback)
    
    def reset(self, initial_state: str = "idle"):
        """重置状态机"""
        with self._lock:
            self._current_state = initial_state
            self._history.clear()
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'current_state': self._current_state,
            'states': list(self._states.keys()),
            'available_transitions': self.get_available_transitions()
        }
