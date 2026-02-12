# -*- coding: utf-8 -*-
"""
Perception Node - 感知节点
处理语音、视觉、关节状态等感知数据
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

# LangGraph 相关
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableLambda

# 状态定义
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from state import (
    RobotState, BrainPhase, PerceptionState,
    update_phase, set_perception_result
)


@dataclass
class PerceptionConfig:
    """感知配置"""
    enable_asr: bool = True
    enable_vision: bool = True
    enable_joint_monitor: bool = True
    fusion_method: str = "weighted_average"
    confidence_threshold: float = 0.5


class PerceptionNode:
    """
    感知节点
    
    处理多模态感知数据，包括：
    - 语音识别 (ASR)
    - 视觉感知 (Vision)
    - 关节状态监测
    - 传感器融合
    
    在 LangGraph 中，节点是一个接收状态并返回状态更新的函数
    """
    
    def __init__(self, config: PerceptionConfig = None, llm=None):
        """
        初始化感知节点
        
        Args:
            config: 感知配置
            llm: 大语言模型实例（用于高级理解）
        """
        self.config = config or PerceptionConfig()
        self.llm = llm
        
        # 感知模块（延迟初始化）
        self._asr_module = None
        self._vision_module = None
        self._joint_monitor = None
        
        # 回调
        self._callbacks: List[Callable] = []
    
    def initialize_modules(self, asr=None, vision=None, joint_monitor=None):
        """初始化感知模块"""
        self._asr_module = asr
        self._vision_module = vision
        self._joint_monitor = joint_monitor
    
    def __call__(self, state: RobotState) -> Dict:
        """
        执行感知（LangGraph 节点入口）
        
        Args:
            state: 当前机器人状态
            
        Returns:
            状态更新字典
        """
        return self.process(state)
    
    def process(self, state: RobotState) -> Dict:
        """
        处理感知
        
        Args:
            state: 当前状态
            
        Returns:
            状态更新
        """
        start_time = time.time()
        
        # 1. 收集感知数据
        perception_data = self._collect_perception_data(state)
        
        # 2. 处理语音输入
        speech_result = self._process_speech(state, perception_data)
        
        # 3. 处理视觉数据
        vision_result = self._process_vision(state, perception_data)
        
        # 4. 获取关节状态
        joint_result = self._process_joints(state, perception_data)
        
        # 5. 传感器融合
        fused_result = self._fuse_perceptions(
            speech_result, vision_result, joint_result
        )
        
        # 6. 使用 LLM 进行高级理解（如果有）
        if self.llm and fused_result.get("recognized_speech"):
            fused_result = self._enhance_with_llm(state, fused_result)
        
        # 7. 构建状态更新
        updates = {
            "current_phase": BrainPhase.PERCEPTION.value,
            "last_update_time": time.time(),
            "perception": {
                **state["perception"],
                **fused_result,
                "last_perception_time": time.time()
            }
        }
        
        # 触发回调
        self._trigger_callbacks(state, updates)
        
        return updates
    
    def _collect_perception_data(self, state: RobotState) -> Dict:
        """收集感知数据"""
        data = {
            "audio": None,
            "visual": None,
            "joints": {}
        }
        
        # 从状态中获取用户输入
        if state.get("user_input"):
            data["audio"] = state["user_input"]
        
        # 从模块获取数据（如果已初始化）
        if self._joint_monitor:
            data["joints"] = self._joint_monitor.get_joint_positions()
        
        return data
    
    def _process_speech(self, state: RobotState, data: Dict) -> Dict:
        """处理语音"""
        result = {
            "recognized_speech": None,
            "speech_confidence": 0.0
        }
        
        # 如果有用户输入，直接使用
        if state.get("user_input"):
            result["recognized_speech"] = state["user_input"]
            result["speech_confidence"] = 1.0
        
        # 如果有 ASR 模块，使用模块处理
        elif self._asr_module and data.get("audio"):
            # 这里应该调用 ASR 模块
            pass
        
        return result
    
    def _process_vision(self, state: RobotState, data: Dict) -> Dict:
        """处理视觉"""
        result = {
            "detected_objects": [],
            "scene_description": None,
            "vision_confidence": 0.0
        }
        
        # 如果有视觉模块，使用模块处理
        if self._vision_module:
            # 模拟视觉检测结果
            result["detected_objects"] = [
                {"label": "cup", "confidence": 0.95, "position": [0.4, 0.0, 0.8]},
                {"label": "table", "confidence": 0.89, "position": [0.5, 0.0, 0.0]}
            ]
            result["scene_description"] = "A room with a table and objects"
            result["vision_confidence"] = 0.9
        
        return result
    
    def _process_joints(self, state: RobotState, data: Dict) -> Dict:
        """处理关节状态"""
        result = {
            "joint_states": {},
            "is_moving": False
        }
        
        if data.get("joints"):
            result["joint_states"] = data["joints"]
        
        # 检查是否在运动
        if self._joint_monitor:
            result["is_moving"] = self._joint_monitor.is_moving()
        
        return result
    
    def _fuse_perceptions(self, speech: Dict, vision: Dict, joints: Dict) -> Dict:
        """融合感知结果"""
        # 计算综合置信度
        confidences = []
        if speech.get("speech_confidence", 0) > 0:
            confidences.append(speech["speech_confidence"])
        if vision.get("vision_confidence", 0) > 0:
            confidences.append(vision["vision_confidence"])
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "recognized_speech": speech.get("recognized_speech"),
            "detected_objects": vision.get("detected_objects", []),
            "scene_description": vision.get("scene_description"),
            "joint_states": joints.get("joint_states", {}),
            "perception_confidence": avg_confidence,
            "is_moving": joints.get("is_moving", False)
        }
    
    def _enhance_with_llm(self, state: RobotState, perception: Dict) -> Dict:
        """使用 LLM 增强感知理解"""
        if not self.llm:
            return perception
        
        try:
            # 构建提示
            prompt = f"""基于以下感知数据，理解用户的意图：

语音输入：{perception.get('recognized_speech', '无')}
检测到的物体：{perception.get('detected_objects', [])}
场景描述：{perception.get('scene_description', '无')}

请简要分析用户可能想要做什么。"""

            # 调用 LLM
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            if response:
                perception["llm_understanding"] = response.content
                perception["perception_confidence"] = min(1.0, perception.get("perception_confidence", 0) + 0.1)
        
        except Exception as e:
            print(f"[PerceptionNode] LLM enhancement error: {e}")
        
        return perception
    
    def add_callback(self, callback: Callable):
        """添加回调"""
        self._callbacks.append(callback)
    
    def _trigger_callbacks(self, state: RobotState, updates: Dict):
        """触发回调"""
        for callback in self._callbacks:
            try:
                callback(state, updates)
            except Exception as e:
                print(f"[PerceptionNode] Callback error: {e}")


# ==================== LangGraph 节点函数 ====================

def perception_node(state: RobotState) -> Dict:
    """
    LangGraph 感知节点函数
    
    这是一个可以直接用于 LangGraph 图定义的函数
    
    Args:
        state: 当前状态
        
    Returns:
        状态更新字典
    """
    node = PerceptionNode()
    return node.process(state)


# 创建 Runnable 版本（用于 LangChain 集成）
perception_runnable = RunnableLambda(perception_node)
