# -*- coding: utf-8 -*-
"""
VLN Tool - 视觉语言导航工具
LangChain/LangGraph 兼容的工具定义
"""

import time
import math
from typing import Dict, List, Optional, Any, Type
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

# LangChain 工具导入
try:
    from langchain_core.tools import tool, BaseTool
    from langchain_core.callbacks import CallbackManagerForToolRun
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    # 创建一个简单的装饰器作为后备
    def tool(func=None, **kwargs):
        if func:
            return func
        return lambda f: f


class VLNInput(BaseModel):
    """VLN 工具输入模式"""
    instruction: str = Field(description="自然语言导航指令")
    target_location: Optional[str] = Field(default=None, description="目标位置（可选）")
    speed: float = Field(default=0.5, description="移动速度 (0.1-1.0)")


class VLNOutput(BaseModel):
    """VLN 工具输出模式"""
    success: bool = Field(description="是否成功")
    final_position: List[float] = Field(description="最终位置 [x, y, z]")
    path_completed: bool = Field(description="路径是否完成")
    message: str = Field(description="结果消息")


@dataclass
class NavigationState:
    """导航状态"""
    current_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    target_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    is_navigating: bool = False
    path_progress: float = 0.0


class VLNTool:
    """
    视觉语言导航工具
    
    实现基于视觉和语言指令的机器人导航能力
    
    Features:
        - 自然语言指令理解
        - 目标位置解析
        - 路径规划
        - 导航执行
    """
    
    name: str = "vln_navigation"
    description: str = """
    视觉语言导航工具。
    用于根据自然语言指令导航机器人到目标位置。
    
    输入参数：
    - instruction: 自然语言导航指令（如"导航到厨房"、"向前走两米"）
    - target_location: 目标位置名称（可选）
    - speed: 移动速度 0.1-1.0（默认0.5）
    
    返回：
    - success: 是否成功
    - final_position: 最终位置
    - path_completed: 是否完成路径
    """
    
    def __init__(self):
        """初始化 VLN 工具"""
        self._state = NavigationState()
        self._location_map = {
            "厨房": [3.0, 2.0, 0.0],
            "客厅": [5.0, 0.0, 0.0],
            "卧室": [2.0, 5.0, 0.0],
            "门口": [0.0, -2.0, 0.0],
            "kitchen": [3.0, 2.0, 0.0],
            "living_room": [5.0, 0.0, 0.0],
            "bedroom": [2.0, 5.0, 0.0],
            "door": [0.0, -2.0, 0.0]
        }
    
    def __call__(self, instruction: str, target_location: str = None, 
                 speed: float = 0.5) -> Dict:
        """
        执行导航
        
        Args:
            instruction: 导航指令
            target_location: 目标位置
            speed: 移动速度
            
        Returns:
            执行结果
        """
        return self.execute(instruction, target_location, speed)
    
    def execute(self, instruction: str, target_location: str = None,
                speed: float = 0.5) -> Dict:
        """
        执行导航
        
        Args:
            instruction: 导航指令
            target_location: 目标位置
            speed: 移动速度
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        # 1. 解析目标位置
        target_pos = self._parse_target(instruction, target_location)
        
        if target_pos is None:
            return {
                "success": False,
                "final_position": self._state.current_position,
                "path_completed": False,
                "message": "无法识别目标位置"
            }
        
        # 2. 模拟导航
        self._state.target_position = target_pos
        self._state.is_navigating = True
        
        # 计算距离和导航时间
        distance = self._calculate_distance(
            self._state.current_position, target_pos
        )
        nav_time = distance / max(0.1, min(1.0, speed))
        
        # 模拟导航过程
        time.sleep(min(nav_time, 1.0))  # 最多等待1秒
        
        # 3. 更新位置
        self._state.current_position = target_pos
        self._state.is_navigating = False
        self._state.path_progress = 100.0
        
        execution_time = time.time() - start_time
        
        return {
            "success": True,
            "final_position": self._state.current_position,
            "path_completed": True,
            "message": f"成功导航到目标位置，耗时 {execution_time:.2f} 秒"
        }
    
    def _parse_target(self, instruction: str, target_location: str = None) -> Optional[List[float]]:
        """解析目标位置"""
        # 优先使用指定的目标位置
        if target_location:
            return self._location_map.get(target_location, [1.0, 1.0, 0.0])
        
        # 从指令中解析
        instruction_lower = instruction.lower()
        
        for location, pos in self._location_map.items():
            if location in instruction_lower:
                return pos
        
        # 默认位置
        return [1.0, 1.0, 0.0]
    
    def _calculate_distance(self, pos1: List[float], pos2: List[float]) -> float:
        """计算两点距离"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(pos1[:2], pos2[:2])))
    
    def get_current_position(self) -> List[float]:
        """获取当前位置"""
        return self._state.current_position
    
    def set_current_position(self, position: List[float]):
        """设置当前位置"""
        self._state.current_position = position


# 创建 LangChain 工具函数
@tool
def vln_tool(instruction: str, target_location: str = None, speed: float = 0.5) -> str:
    """
    视觉语言导航工具。
    
    用于根据自然语言指令导航机器人到目标位置。
    
    Args:
        instruction: 自然语言导航指令（如"导航到厨房"）
        target_location: 目标位置名称（可选）
        speed: 移动速度 0.1-1.0（默认0.5）
    
    Returns:
        导航结果的描述
    """
    vln = VLNTool()
    result = vln.execute(instruction, target_location, speed)
    
    if result["success"]:
        return f"导航成功！已到达位置 {result['final_position']}"
    else:
        return f"导航失败：{result['message']}"


# 创建 LangChain StructuredTool
if LANGCHAIN_AVAILABLE:
    from langchain_core.tools import StructuredTool
    
    vln_structured_tool = StructuredTool.from_function(
        func=vln_tool,
        name="vln_navigation",
        description="视觉语言导航工具，用于根据自然语言指令导航机器人"
    )
