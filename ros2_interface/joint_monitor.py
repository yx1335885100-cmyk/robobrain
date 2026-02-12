# -*- coding: utf-8 -*-
"""
Joint Monitor - 关节状态监测器
基于ROS2的机器人所有关节状态实时监测
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import json


class JointType(Enum):
    """关节类型枚举"""
    REVOLUTE = "revolute"      # 旋转关节
    PRISMATIC = "prismatic"    # 移动关节
    CONTINUOUS = "continuous"  # 连续旋转关节
    FIXED = "fixed"            # 固定关节
    PLANAR = "planar"          # 平面关节


@dataclass
class JointState:
    """
    关节状态数据结构
    
    Attributes:
        name: 关节名称
        position: 关节位置（弧度或米）
        velocity: 关节速度
        effort: 关节力矩/力
        timestamp: 时间戳
    """
    name: str
    position: float = 0.0
    velocity: float = 0.0
    effort: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'position': self.position,
            'velocity': self.velocity,
            'effort': self.effort,
            'timestamp': self.timestamp
        }


@dataclass
class JointLimits:
    """关节限制"""
    name: str
    lower: float = -3.14159
    upper: float = 3.14159
    velocity_limit: float = 1.0
    effort_limit: float = 100.0


@dataclass
class JointGroup:
    """关节组"""
    name: str
    joints: List[str]
    joint_types: List[JointType] = field(default_factory=list)


class JointMonitor:
    """
    关节状态监测器
    
    基于ROS2订阅关节状态话题，实时监测所有关节状态
    
    Features:
        - 实时关节状态监测
        - 关节限制检查
        - 关节组管理
        - 异常检测
        - 历史数据记录
        - 状态回调机制
    """
    
    def __init__(self, update_rate: float = 100.0):
        """
        初始化关节监测器
        
        Args:
            update_rate: 更新频率（Hz）
        """
        self.update_rate = update_rate
        self.update_period = 1.0 / update_rate
        
        # 关节状态存储
        self._joint_states: Dict[str, JointState] = {}
        self._joint_limits: Dict[str, JointLimits] = {}
        self._joint_groups: Dict[str, JointGroup] = {}
        
        # 历史数据（需要在_initialize_humanoid_joints之前初始化）
        self._history_size = 1000
        self._state_history: Dict[str, deque] = {}
        
        # 关节配置（人形机器人典型配置）
        self._initialize_humanoid_joints()
        
        # 异常检测
        self._anomaly_thresholds = {
            'velocity': 5.0,      # rad/s
            'effort': 200.0,      # Nm or N
            'position_error': 0.5  # rad
        }
        
        # 回调
        self._state_callbacks: List[Callable] = []
        self._anomaly_callbacks: List[Callable] = []
        
        # 线程控制
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # ROS2相关
        self._ros2_node = None
        self._subscription = None
        
        # 统计信息
        self._stats = {
            'updates_received': 0,
            'anomalies_detected': 0,
            'last_update_time': 0
        }
        
    def _initialize_humanoid_joints(self):
        """初始化人形机器人关节配置"""
        # 头部关节
        head_joints = ['head_pan', 'head_tilt']
        for name in head_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=-1.57, upper=1.57,
                velocity_limit=2.0, effort_limit=50.0
            )
        
        self._joint_groups['head'] = JointGroup(
            name='head',
            joints=head_joints,
            joint_types=[JointType.REVOLUTE, JointType.REVOLUTE]
        )
        
        # 左臂关节
        left_arm_joints = [
            'left_shoulder_pitch', 'left_shoulder_roll', 'left_shoulder_yaw',
            'left_elbow_pitch', 'left_wrist_roll', 'left_wrist_pitch'
        ]
        for name in left_arm_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=-3.14, upper=3.14,
                velocity_limit=3.0, effort_limit=100.0
            )
        
        self._joint_groups['left_arm'] = JointGroup(
            name='left_arm',
            joints=left_arm_joints,
            joint_types=[JointType.REVOLUTE] * 6
        )
        
        # 右臂关节
        right_arm_joints = [
            'right_shoulder_pitch', 'right_shoulder_roll', 'right_shoulder_yaw',
            'right_elbow_pitch', 'right_wrist_roll', 'right_wrist_pitch'
        ]
        for name in right_arm_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=-3.14, upper=3.14,
                velocity_limit=3.0, effort_limit=100.0
            )
        
        self._joint_groups['right_arm'] = JointGroup(
            name='right_arm',
            joints=right_arm_joints,
            joint_types=[JointType.REVOLUTE] * 6
        )
        
        # 左手关节
        left_hand_joints = [
            f'left_finger_{i}' for i in range(5)
        ]
        for name in left_hand_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=0.0, upper=1.0,
                velocity_limit=2.0, effort_limit=20.0
            )
        
        self._joint_groups['left_hand'] = JointGroup(
            name='left_hand',
            joints=left_hand_joints,
            joint_types=[JointType.REVOLUTE] * 5
        )
        
        # 右手关节
        right_hand_joints = [
            f'right_finger_{i}' for i in range(5)
        ]
        for name in right_hand_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=0.0, upper=1.0,
                velocity_limit=2.0, effort_limit=20.0
            )
        
        self._joint_groups['right_hand'] = JointGroup(
            name='right_hand',
            joints=right_hand_joints,
            joint_types=[JointType.REVOLUTE] * 5
        )
        
        # 躯干关节
        torso_joints = ['torso_pitch', 'torso_roll', 'torso_yaw']
        for name in torso_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=-0.5, upper=0.5,
                velocity_limit=1.0, effort_limit=200.0
            )
        
        self._joint_groups['torso'] = JointGroup(
            name='torso',
            joints=torso_joints,
            joint_types=[JointType.REVOLUTE] * 3
        )
        
        # 左腿关节
        left_leg_joints = [
            'left_hip_pitch', 'left_hip_roll', 'left_hip_yaw',
            'left_knee_pitch', 'left_ankle_pitch', 'left_ankle_roll'
        ]
        for name in left_leg_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=-2.0, upper=2.0,
                velocity_limit=5.0, effort_limit=300.0
            )
        
        self._joint_groups['left_leg'] = JointGroup(
            name='left_leg',
            joints=left_leg_joints,
            joint_types=[JointType.REVOLUTE] * 6
        )
        
        # 右腿关节
        right_leg_joints = [
            'right_hip_pitch', 'right_hip_roll', 'right_hip_yaw',
            'right_knee_pitch', 'right_ankle_pitch', 'right_ankle_roll'
        ]
        for name in right_leg_joints:
            self._joint_states[name] = JointState(name=name)
            self._joint_limits[name] = JointLimits(
                name=name,
                lower=-2.0, upper=2.0,
                velocity_limit=5.0, effort_limit=300.0
            )
        
        self._joint_groups['right_leg'] = JointGroup(
            name='right_leg',
            joints=right_leg_joints,
            joint_types=[JointType.REVOLUTE] * 6
        )
        
        # 初始化历史数据缓冲区
        for joint_name in self._joint_states:
            self._state_history[joint_name] = deque(maxlen=self._history_size)
    
    def initialize_ros2(self, node=None):
        """
        初始化ROS2连接
        
        Args:
            node: ROS2节点实例（可选）
        """
        try:
            import rclpy
            from sensor_msgs.msg import JointState as JointStateMsg
            
            if node is None:
                rclpy.init()
                from rclpy.node import Node
                self._ros2_node = Node('joint_monitor')
            else:
                self._ros2_node = node
            
            # 订阅关节状态话题
            self._subscription = self._ros2_node.create_subscription(
                JointStateMsg,
                '/joint_states',
                self._joint_state_callback,
                10
            )
            
            print(f"[JointMonitor] ROS2 initialized, subscribed to /joint_states")
            
        except ImportError:
            print("[JointMonitor] ROS2 not available, running in simulation mode")
            self._ros2_node = None
    
    def _joint_state_callback(self, msg):
        """ROS2关节状态回调"""
        with self._lock:
            for i, name in enumerate(msg.name):
                if name in self._joint_states:
                    state = self._joint_states[name]
                    state.position = msg.position[i] if i < len(msg.position) else 0.0
                    state.velocity = msg.velocity[i] if i < len(msg.velocity) else 0.0
                    state.effort = msg.effort[i] if i < len(msg.effort) else 0.0
                    state.timestamp = time.time()
                    
                    # 记录历史
                    self._state_history[name].append(state.to_dict())
                    
                    # 检测异常
                    self._check_anomalies(name)
            
            self._stats['updates_received'] += 1
            self._stats['last_update_time'] = time.time()
            
            # 触发状态回调
            self._trigger_state_callbacks()
    
    def _check_anomalies(self, joint_name: str):
        """检查关节状态异常"""
        state = self._joint_states[joint_name]
        limits = self._joint_limits.get(joint_name)
        
        if limits is None:
            return
        
        anomalies = []
        
        # 检查位置限制
        if state.position < limits.lower or state.position > limits.upper:
            anomalies.append({
                'type': 'position_limit_violation',
                'joint': joint_name,
                'value': state.position,
                'limits': (limits.lower, limits.upper)
            })
        
        # 检查速度异常
        if abs(state.velocity) > self._anomaly_thresholds['velocity']:
            anomalies.append({
                'type': 'velocity_anomaly',
                'joint': joint_name,
                'value': state.velocity,
                'threshold': self._anomaly_thresholds['velocity']
            })
        
        # 检查力矩异常
        if abs(state.effort) > self._anomaly_thresholds['effort']:
            anomalies.append({
                'type': 'effort_anomaly',
                'joint': joint_name,
                'value': state.effort,
                'threshold': self._anomaly_thresholds['effort']
            })
        
        if anomalies:
            self._stats['anomalies_detected'] += 1
            self._trigger_anomaly_callbacks(anomalies)
    
    def _trigger_state_callbacks(self):
        """触发状态更新回调"""
        for callback in self._state_callbacks:
            try:
                callback(self._joint_states)
            except Exception as e:
                print(f"[JointMonitor] State callback error: {e}")
    
    def _trigger_anomaly_callbacks(self, anomalies: List[Dict]):
        """触发异常回调"""
        for callback in self._anomaly_callbacks:
            try:
                callback(anomalies)
            except Exception as e:
                print(f"[JointMonitor] Anomaly callback error: {e}")
    
    def add_state_callback(self, callback: Callable):
        """添加状态更新回调"""
        self._state_callbacks.append(callback)
    
    def add_anomaly_callback(self, callback: Callable):
        """添加异常检测回调"""
        self._anomaly_callbacks.append(callback)
    
    def start_monitoring(self):
        """启动监测"""
        self._running = True
        
        if self._ros2_node is None:
            # 模拟模式：启动模拟线程
            self._monitor_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self._monitor_thread.start()
            print("[JointMonitor] Started in simulation mode")
        else:
            # ROS2模式：启动spin线程
            self._monitor_thread = threading.Thread(target=self._ros2_spin_loop, daemon=True)
            self._monitor_thread.start()
            print("[JointMonitor] Started with ROS2")
    
    def stop_monitoring(self):
        """停止监测"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        print("[JointMonitor] Stopped")
    
    def _simulation_loop(self):
        """模拟数据生成循环"""
        import math
        import random
        
        while self._running:
            with self._lock:
                current_time = time.time()
                
                for name, state in self._joint_states.items():
                    # 生成模拟关节状态
                    base_freq = 0.1
                    phase = current_time * base_freq
                    
                    # 添加一些随机变化
                    state.position = math.sin(phase) * 0.5 + random.uniform(-0.05, 0.05)
                    state.velocity = math.cos(phase) * 0.5 * base_freq + random.uniform(-0.1, 0.1)
                    state.effort = random.uniform(-10, 10)
                    state.timestamp = current_time
                    
                    # 记录历史
                    self._state_history[name].append(state.to_dict())
                
                self._stats['updates_received'] += 1
                self._stats['last_update_time'] = current_time
                
                # 触发回调
                self._trigger_state_callbacks()
            
            time.sleep(self.update_period)
    
    def _ros2_spin_loop(self):
        """ROS2 spin循环"""
        import rclpy
        while self._running:
            rclpy.spin_once(self._ros2_node, timeout_sec=0.1)
    
    def get_joint_state(self, joint_name: str) -> Optional[JointState]:
        """获取单个关节状态"""
        return self._joint_states.get(joint_name)
    
    def get_joint_positions(self) -> Dict[str, float]:
        """获取所有关节位置"""
        with self._lock:
            return {name: state.position for name, state in self._joint_states.items()}
    
    def get_joint_velocities(self) -> Dict[str, float]:
        """获取所有关节速度"""
        with self._lock:
            return {name: state.velocity for name, state in self._joint_states.items()}
    
    def get_joint_efforts(self) -> Dict[str, float]:
        """获取所有关节力矩"""
        with self._lock:
            return {name: state.effort for name, state in self._joint_states.items()}
    
    def get_timestamps(self) -> Dict[str, float]:
        """获取所有关节时间戳"""
        with self._lock:
            return {name: state.timestamp for name, state in self._joint_states.items()}
    
    def get_joint_group_state(self, group_name: str) -> Dict[str, JointState]:
        """获取关节组状态"""
        group = self._joint_groups.get(group_name)
        if group is None:
            return {}
        
        with self._lock:
            return {name: self._joint_states[name] for name in group.joints 
                    if name in self._joint_states}
    
    def get_all_joint_states(self) -> Dict[str, JointState]:
        """获取所有关节状态"""
        with self._lock:
            return self._joint_states.copy()
    
    def get_joint_names(self) -> List[str]:
        """获取所有关节名称"""
        return list(self._joint_states.keys())
    
    def get_joint_groups(self) -> Dict[str, JointGroup]:
        """获取所有关节组"""
        return self._joint_groups.copy()
    
    def get_joint_limits(self, joint_name: str) -> Optional[JointLimits]:
        """获取关节限制"""
        return self._joint_limits.get(joint_name)
    
    def get_all_joint_limits(self) -> Dict[str, JointLimits]:
        """获取所有关节限制"""
        return self._joint_limits.copy()
    
    def get_history(self, joint_name: str, limit: int = 100) -> List[Dict]:
        """获取关节状态历史"""
        if joint_name not in self._state_history:
            return []
        
        with self._lock:
            return list(self._state_history[joint_name])[-limit:]
    
    def is_moving(self, threshold: float = 0.01) -> bool:
        """检查是否有关节在运动"""
        with self._lock:
            for state in self._joint_states.values():
                if abs(state.velocity) > threshold:
                    return True
        return False
    
    def get_end_effector_pose(self, arm: str = 'left') -> Dict:
        """
        获取末端执行器位姿（简化版本）
        
        Args:
            arm: 手臂选择 ('left' or 'right')
            
        Returns:
            位姿字典
        """
        # 这里应该使用正运动学计算
        # 简化版本返回占位数据
        group_name = f'{arm}_arm'
        group_states = self.get_joint_group_state(group_name)
        
        return {
            'position': [0.3, 0.2 if arm == 'left' else -0.2, 0.8],
            'orientation': [0, 0, 0, 1],
            'joints_used': list(group_states.keys())
        }
    
    def set_joint_position(self, joint_name: str, position: float):
        """设置关节位置（用于模拟）"""
        with self._lock:
            if joint_name in self._joint_states:
                self._joint_states[joint_name].position = position
                self._joint_states[joint_name].timestamp = time.time()
    
    def set_anomaly_threshold(self, parameter: str, value: float):
        """设置异常检测阈值"""
        if parameter in self._anomaly_thresholds:
            self._anomaly_thresholds[parameter] = value
    
    def get_statistics(self) -> Dict:
        """获取监测统计信息"""
        return {
            'total_joints': len(self._joint_states),
            'total_groups': len(self._joint_groups),
            'updates_received': self._stats['updates_received'],
            'anomalies_detected': self._stats['anomalies_detected'],
            'last_update_time': self._stats['last_update_time'],
            'update_rate': self.update_rate,
            'is_moving': self.is_moving()
        }
    
    def export_state(self) -> str:
        """导出当前状态为JSON"""
        with self._lock:
            export_data = {
                'timestamp': time.time(),
                'joints': {name: state.to_dict() for name, state in self._joint_states.items()},
                'statistics': self.get_statistics()
            }
        return json.dumps(export_data, indent=2)
    
    def get_state_summary(self) -> Dict:
        """获取状态摘要"""
        with self._lock:
            positions = self.get_joint_positions()
            velocities = self.get_joint_velocities()
            efforts = self.get_joint_efforts()
            
            return {
                'joint_count': len(self._joint_states),
                'avg_velocity': sum(abs(v) for v in velocities.values()) / len(velocities) if velocities else 0,
                'max_velocity': max(abs(v) for v in velocities.values()) if velocities else 0,
                'avg_effort': sum(abs(e) for e in efforts.values()) / len(efforts) if efforts else 0,
                'max_effort': max(abs(e) for e in efforts.values()) if efforts else 0,
                'position_range': {
                    name: (limits.lower, limits.upper, positions.get(name, 0))
                    for name, limits in self._joint_limits.items()
                }
            }
