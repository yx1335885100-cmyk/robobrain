# -*- coding: utf-8 -*-
"""
Humanoid Robot Brain - Perception Module
感知模块：包含ASR语音识别、视觉感知、传感器融合
"""

from .asr_module import ASRModule, SpeechRecognitionResult
from .vision_module import VisionModule, VisionResult
from .sensor_fusion import SensorFusion, FusedPerception

__all__ = [
    'ASRModule',
    'SpeechRecognitionResult',
    'VisionModule',
    'VisionResult',
    'SensorFusion',
    'FusedPerception'
]
