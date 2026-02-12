# -*- coding: utf-8 -*-
"""
Navigation Tool - 导航工具
基础导航功能
"""

import time
import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func:
            return func
        return lambda f: f


@dataclass
class NavigationConfig:
    """导航配置"""
    max_velocity: float = 0.5
    max_acceleration: float = 0.5
    safety_distance: float = 0.3


class NavigationTool:
    """基础导航工具"""
    
    name = "navigation"
    description = "基础导航工具，用于控制机器人移动"
    
    def __init__(self, config: NavigationConfig = None):
        self.config = config or NavigationConfig()
        self._current_pose = [0.0, 0.0, 0.0]
    
    def move_to(self, target: List[float], speed: float = 0.5) -> Dict:
        """移动到目标位置"""
        distance = math.sqrt(
            (target[0] - self._current_pose[0])**2 +
            (target[1] - self._current_pose[1])**2
        )
        
        # 模拟移动
        move_time = distance / max(0.1, speed)
        time.sleep(min(move_time, 1.0))
        
        self._current_pose = target[:3]
        
        return {
            "success": True,
            "position": self._current_pose,
            "distance_traveled": distance
        }
    
    def move_forward(self, distance: float) -> Dict:
        """向前移动"""
        self._current_pose[0] += distance
        return {
            "success": True,
            "position": self._current_pose
        }
    
    def rotate(self, angle: float) -> Dict:
        """旋转"""
        self._current_pose[2] += angle
        return {
            "success": True,
            "orientation": self._current_pose[2]
        }
    
    def get_position(self) -> List[float]:
        """获取当前位置"""
        return self._current_pose.copy()


@tool
def navigation_tool(action: str, **kwargs) -> str:
    """
    基础导航工具。
    
    用于控制机器人的基本移动。
    
    Args:
        action: 动作类型 (move_to/move_forward/rotate)
        kwargs: 动作参数
    
    Returns:
        导航结果描述
    """
    nav = NavigationTool()
    
    if action == "move_to":
        target = kwargs.get("target", [1.0, 0.0, 0.0])
        result = nav.move_to(target, kwargs.get("speed", 0.5))
        return f"已移动到位置 {result['position']}"
    elif action == "move_forward":
        distance = kwargs.get("distance", 1.0)
        result = nav.move_forward(distance)
        return f"向前移动 {distance} 米"
    elif action == "rotate":
        angle = kwargs.get("angle", 0.0)
        result = nav.rotate(angle)
        return f"旋转 {angle} 弧度"
    else:
        return f"未知动作: {action}"
