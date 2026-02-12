# -*- coding: utf-8 -*-
"""
Sensor Fusion - 传感器融合模块
整合多源传感器数据，提供统一的环境感知
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json


class SensorType(Enum):
    """传感器类型枚举"""
    CAMERA = "camera"
    MICROPHONE = "microphone"
    LIDAR = "lidar"
    IMU = "imu"
    JOINT = "joint"
    FORCE = "force"
    TACTILE = "tactile"


@dataclass
class SensorReading:
    """传感器读数"""
    sensor_type: SensorType
    sensor_id: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'sensor_type': self.sensor_type.value,
            'sensor_id': self.sensor_id,
            'value': self.value,
            'timestamp': self.timestamp,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


@dataclass
class FusedPerception:
    """
    融合感知结果
    
    Attributes:
        timestamp: 时间戳
        objects: 检测到的对象（融合多传感器）
        speech: 语音识别结果
        scene_understanding: 场景理解
        robot_state: 机器人状态
        confidence: 整体置信度
    """
    timestamp: float = field(default_factory=time.time)
    objects: List[Dict] = field(default_factory=list)
    speech: Optional[str] = None
    scene_understanding: Dict = field(default_factory=dict)
    robot_state: Dict = field(default_factory=dict)
    confidence: float = 1.0
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp,
            'objects': self.objects,
            'speech': self.speech,
            'scene_understanding': self.scene_understanding,
            'robot_state': self.robot_state,
            'confidence': self.confidence,
            'metadata': self.metadata
        }


@dataclass
class FusionConfig:
    """融合配置"""
    fusion_rate: float = 10.0  # Hz
    history_size: int = 100
    confidence_threshold: float = 0.5
    temporal_window: float = 0.5  # 秒


class SensorFusion:
    """
    传感器融合模块
    
    整合多源传感器数据，提供统一的环境感知
    
    Features:
        - 多传感器数据整合
        - 时序对齐
        - 置信度加权
        - 异常检测
        - 历史数据管理
        - 场景理解
    """
    
    def __init__(self, config: Optional[FusionConfig] = None):
        """
        初始化传感器融合模块
        
        Args:
            config: 融合配置
        """
        self.config = config or FusionConfig()
        
        # 传感器数据存储
        self._sensor_readings: Dict[str, List[SensorReading]] = {}
        self._latest_readings: Dict[str, SensorReading] = {}
        
        # 感知模块引用
        self._asr_module = None
        self._vision_module = None
        self._joint_monitor = None
        
        # 融合结果
        self._fused_result: Optional[FusedPerception] = None
        
        # 回调
        self._fusion_callbacks: List[Callable] = []
        
        # 线程控制
        self._running = False
        self._fusion_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # 统计
        self._stats = {
            'readings_processed': 0,
            'fusion_cycles': 0,
            'objects_fused': 0
        }
    
    def register_asr(self, asr_module: Any):
        """注册ASR模块"""
        self._asr_module = asr_module
        print("[SensorFusion] ASR module registered")
    
    def register_vision(self, vision_module: Any):
        """注册视觉模块"""
        self._vision_module = vision_module
        print("[SensorFusion] Vision module registered")
    
    def register_joint_monitor(self, joint_monitor: Any):
        """注册关节监测器"""
        self._joint_monitor = joint_monitor
        print("[SensorFusion] Joint monitor registered")
    
    def add_sensor_reading(self, reading: SensorReading):
        """
        添加传感器读数
        
        Args:
            reading: 传感器读数
        """
        with self._lock:
            key = f"{reading.sensor_type.value}_{reading.sensor_id}"
            
            if key not in self._sensor_readings:
                self._sensor_readings[key] = []
            
            self._sensor_readings[key].append(reading)
            
            # 限制历史大小
            if len(self._sensor_readings[key]) > self.config.history_size:
                self._sensor_readings[key] = self._sensor_readings[key][-self.config.history_size:]
            
            self._latest_readings[key] = reading
            self._stats['readings_processed'] += 1
    
    def start_fusion(self):
        """启动融合"""
        self._running = True
        
        self._fusion_thread = threading.Thread(target=self._fusion_loop, daemon=True)
        self._fusion_thread.start()
        
        print("[SensorFusion] Started fusion")
    
    def stop_fusion(self):
        """停止融合"""
        self._running = False
        
        if self._fusion_thread:
            self._fusion_thread.join(timeout=2.0)
        
        print("[SensorFusion] Stopped fusion")
    
    def _fusion_loop(self):
        """融合循环"""
        while self._running:
            try:
                self._perform_fusion()
                time.sleep(1.0 / self.config.fusion_rate)
            except Exception as e:
                print(f"[SensorFusion] Fusion error: {e}")
                time.sleep(0.1)
    
    def _perform_fusion(self):
        """执行传感器融合"""
        current_time = time.time()
        
        # 收集时间窗口内的传感器数据
        temporal_data = self._collect_temporal_data(current_time)
        
        # 融合视觉数据
        visual_objects = self._fuse_visual_data(temporal_data)
        
        # 融合语音数据
        speech_result = self._fuse_speech_data(temporal_data)
        
        # 获取机器人状态
        robot_state = self._get_robot_state()
        
        # 场景理解
        scene_understanding = self._understand_scene(visual_objects, speech_result)
        
        # 创建融合结果
        self._fused_result = FusedPerception(
            timestamp=current_time,
            objects=visual_objects,
            speech=speech_result,
            scene_understanding=scene_understanding,
            robot_state=robot_state,
            confidence=self._calculate_confidence(visual_objects, speech_result)
        )
        
        self._stats['fusion_cycles'] += 1
        self._stats['objects_fused'] += len(visual_objects)
        
        # 触发回调
        self._trigger_fusion_callbacks()
    
    def _collect_temporal_data(self, current_time: float) -> Dict[str, List[SensorReading]]:
        """收集时间窗口内的数据"""
        temporal_data = {}
        window_start = current_time - self.config.temporal_window
        
        with self._lock:
            for key, readings in self._sensor_readings.items():
                temporal_data[key] = [
                    r for r in readings 
                    if r.timestamp >= window_start
                ]
        
        return temporal_data
    
    def _fuse_visual_data(self, temporal_data: Dict) -> List[Dict]:
        """融合视觉数据"""
        objects = []
        
        # 从视觉模块获取数据
        if self._vision_module:
            try:
                # 这里应该调用视觉模块的获取方法
                # result = await self._vision_module.detect(None)
                pass
            except Exception as e:
                print(f"[SensorFusion] Visual fusion error: {e}")
        
        # 从传感器读数中获取视觉数据
        for key, readings in temporal_data.items():
            if key.startswith('camera'):
                for reading in readings:
                    if isinstance(reading.value, dict) and 'objects' in reading.value:
                        for obj in reading.value['objects']:
                            objects.append({
                                **obj,
                                'source': key,
                                'timestamp': reading.timestamp
                            })
        
        # 对象去重和融合
        objects = self._deduplicate_objects(objects)
        
        return objects
    
    def _fuse_speech_data(self, temporal_data: Dict) -> Optional[str]:
        """融合语音数据"""
        # 从ASR模块获取数据
        if self._asr_module:
            # 这里应该获取ASR模块的最新结果
            pass
        
        # 从传感器读数中获取语音数据
        for key, readings in temporal_data.items():
            if key.startswith('microphone'):
                for reading in readings:
                    if isinstance(reading.value, dict) and 'text' in reading.value:
                        return reading.value['text']
        
        return None
    
    def _get_robot_state(self) -> Dict:
        """获取机器人状态"""
        state = {
            'timestamp': time.time(),
            'joints': {},
            'is_moving': False
        }
        
        if self._joint_monitor:
            state['joints'] = self._joint_monitor.get_joint_positions()
            state['is_moving'] = self._joint_monitor.is_moving()
        
        return state
    
    def _understand_scene(self, objects: List[Dict], speech: Optional[str]) -> Dict:
        """场景理解"""
        understanding = {
            'object_count': len(objects),
            'object_types': list(set(obj.get('label', 'unknown') for obj in objects)),
            'has_interaction_target': False,
            'speech_context': speech
        }
        
        # 分析场景中的交互目标
        interactive_objects = ['cup', 'bottle', 'door', 'chair', 'person']
        for obj in objects:
            if obj.get('label') in interactive_objects:
                understanding['has_interaction_target'] = True
                understanding['primary_target'] = obj
                break
        
        return understanding
    
    def _deduplicate_objects(self, objects: List[Dict]) -> List[Dict]:
        """对象去重"""
        if not objects:
            return []
        
        # 简单的去重逻辑：相同标签的对象取置信度最高的
        deduplicated = {}
        
        for obj in objects:
            label = obj.get('label', 'unknown')
            conf = obj.get('confidence', 0)
            
            if label not in deduplicated or conf > deduplicated[label].get('confidence', 0):
                deduplicated[label] = obj
        
        return list(deduplicated.values())
    
    def _calculate_confidence(self, objects: List[Dict], speech: Optional[str]) -> float:
        """计算整体置信度"""
        confidences = []
        
        for obj in objects:
            if 'confidence' in obj:
                confidences.append(obj['confidence'])
        
        if not confidences:
            return 0.5
        
        # 取平均置信度
        avg_confidence = sum(confidences) / len(confidences)
        
        # 如果有语音输入，略微提高置信度
        if speech:
            avg_confidence = min(1.0, avg_confidence + 0.1)
        
        return avg_confidence
    
    def _trigger_fusion_callbacks(self):
        """触发融合回调"""
        if self._fused_result is None:
            return
        
        for callback in self._fusion_callbacks:
            try:
                callback(self._fused_result)
            except Exception as e:
                print(f"[SensorFusion] Fusion callback error: {e}")
    
    async def perceive(self) -> FusedPerception:
        """
        执行感知（供大脑调用）
        
        Returns:
            融合感知结果
        """
        # 执行一次同步融合
        self._perform_fusion()
        
        if self._fused_result is None:
            return FusedPerception()
        
        return self._fused_result
    
    def get_latest_result(self) -> Optional[FusedPerception]:
        """获取最新的融合结果"""
        return self._fused_result
    
    def get_sensor_status(self) -> Dict[str, bool]:
        """获取传感器状态"""
        status = {
            'asr': self._asr_module is not None,
            'vision': self._vision_module is not None,
            'joint_monitor': self._joint_monitor is not None
        }
        
        with self._lock:
            for key in self._latest_readings:
                status[key] = True
        
        return status
    
    def add_fusion_callback(self, callback: Callable):
        """添加融合回调"""
        self._fusion_callbacks.append(callback)
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            'registered_sensors': list(self._sensor_readings.keys()),
            'fusion_rate': self.config.fusion_rate,
            'history_size': self.config.history_size
        }
    
    def clear_history(self):
        """清理历史数据"""
        with self._lock:
            self._sensor_readings.clear()
            self._latest_readings.clear()
    
    def simulate_reading(self, sensor_type: SensorType, sensor_id: str, value: Any):
        """
        模拟传感器读数（用于测试）
        
        Args:
            sensor_type: 传感器类型
            sensor_id: 传感器ID
            value: 读数值
        """
        reading = SensorReading(
            sensor_type=sensor_type,
            sensor_id=sensor_id,
            value=value,
            metadata={'simulated': True}
        )
        
        self.add_sensor_reading(reading)
