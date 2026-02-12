# -*- coding: utf-8 -*-
"""
VLA Tool - 视觉语言操作工具
LangChain/LangGraph 兼容的工具定义
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field

try:
    from langchain_core.tools import tool
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    def tool(func=None, **kwargs):
        if func:
            return func
        return lambda f: f


class VLAInput(BaseModel):
    """VLA 工具输入模式"""
    instruction: str = Field(description="自然语言操作指令")
    target_object: Optional[str] = Field(default=None, description="目标物体")
    action_type: Optional[str] = Field(default="grasp", description="动作类型：grasp/place/push")


class VLAOutput(BaseModel):
    """VLA 工具输出模式"""
    success: bool = Field(description="是否成功")
    action: str = Field(description="执行的动作")
    object_manipulated: Optional[str] = Field(default=None, description="操作的对象")
    message: str = Field(description="结果消息")


@dataclass
class ManipulationState:
    """操作状态"""
    gripper_open: bool = True
    held_object: Optional[str] = None
    end_effector_position: List[float] = field(default_factory=lambda: [0.4, 0.0, 0.8])


class VLATool:
    """
    视觉语言操作工具
    
    实现基于视觉和语言指令的机器人操作能力
    
    Features:
        - 自然语言指令理解
        - 物体识别与定位
        - 抓取/放置/推动操作
        - 力反馈处理
    """
    
    name: str = "vla_manipulation"
    description: str = """
    视觉语言操作工具。
    用于根据自然语言指令执行机器人操作任务。
    
    输入参数：
    - instruction: 自然语言操作指令（如"拿那个杯子"）
    - target_object: 目标物体名称（可选）
    - action_type: 动作类型 grasp/place/push（默认grasp）
    
    返回：
    - success: 是否成功
    - action: 执行的动作
    - object_manipulated: 操作的对象
    """
    
    def __init__(self):
        """初始化 VLA 工具"""
        self._state = ManipulationState()
    
    def __call__(self, instruction: str, target_object: str = None,
                 action_type: str = "grasp") -> Dict:
        """执行操作"""
        return self.execute(instruction, target_object, action_type)
    
    def execute(self, instruction: str, target_object: str = None,
                action_type: str = "grasp") -> Dict:
        """
        执行操作
        
        Args:
            instruction: 操作指令
            target_object: 目标物体
            action_type: 动作类型
            
        Returns:
            执行结果
        """
        start_time = time.time()
        
        # 1. 解析动作类型
        parsed_action = self._parse_action_type(instruction, action_type)
        
        # 2. 解析目标物体
        parsed_object = self._parse_target_object(instruction, target_object)
        
        # 3. 执行操作
        if parsed_action == "grasp":
            result = self._execute_grasp(parsed_object)
        elif parsed_action == "place":
            result = self._execute_place(parsed_object)
        elif parsed_action == "push":
            result = self._execute_push(parsed_object)
        else:
            result = {
                "success": False,
                "action": parsed_action,
                "object_manipulated": None,
                "message": f"未知动作类型: {parsed_action}"
            }
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def _parse_action_type(self, instruction: str, action_type: str) -> str:
        """解析动作类型"""
        instruction_lower = instruction.lower()
        
        if any(word in instruction_lower for word in ['抓', '拿', '取', 'grasp', 'pick', 'get']):
            return "grasp"
        elif any(word in instruction_lower for word in ['放', '放置', 'place', 'put']):
            return "place"
        elif any(word in instruction_lower for word in ['推', 'push']):
            return "push"
        
        return action_type
    
    def _parse_target_object(self, instruction: str, target_object: str) -> str:
        """解析目标物体"""
        if target_object:
            return target_object
        
        objects = ['杯子', 'cup', '瓶子', 'bottle', '盒子', 'box', '手机', 'phone']
        instruction_lower = instruction.lower()
        
        for obj in objects:
            if obj in instruction_lower:
                return obj
        
        return "目标物体"
    
    def _execute_grasp(self, target_object: str) -> Dict:
        """执行抓取"""
        if not self._state.gripper_open:
            return {
                "success": False,
                "action": "grasp",
                "object_manipulated": None,
                "message": "夹爪未打开，无法抓取"
            }
        
        # 模拟抓取
        time.sleep(0.5)
        
        self._state.gripper_open = False
        self._state.held_object = target_object
        
        return {
            "success": True,
            "action": "grasp",
            "object_manipulated": target_object,
            "message": f"成功抓取 {target_object}"
        }
    
    def _execute_place(self, target_object: str) -> Dict:
        """执行放置"""
        if self._state.held_object is None:
            return {
                "success": False,
                "action": "place",
                "object_manipulated": None,
                "message": "没有持有物体，无法放置"
            }
        
        # 模拟放置
        time.sleep(0.3)
        
        placed_object = self._state.held_object
        self._state.gripper_open = True
        self._state.held_object = None
        
        return {
            "success": True,
            "action": "place",
            "object_manipulated": placed_object,
            "message": f"成功放置 {placed_object}"
        }
    
    def _execute_push(self, target_object: str) -> Dict:
        """执行推动"""
        time.sleep(0.3)
        
        return {
            "success": True,
            "action": "push",
            "object_manipulated": target_object,
            "message": f"成功推动 {target_object}"
        }
    
    def get_held_object(self) -> Optional[str]:
        """获取持有的物体"""
        return self._state.held_object
    
    def is_gripper_open(self) -> bool:
        """夹爪是否打开"""
        return self._state.gripper_open


@tool
def vla_tool(instruction: str, target_object: str = None, 
             action_type: str = "grasp") -> str:
    """
    视觉语言操作工具。
    
    用于根据自然语言指令执行机器人操作任务。
    
    Args:
        instruction: 自然语言操作指令（如"拿那个杯子"）
        target_object: 目标物体名称（可选）
        action_type: 动作类型 grasp/place/push（默认grasp）
    
    Returns:
        操作结果的描述
    """
    vla = VLATool()
    result = vla.execute(instruction, target_object, action_type)
    
    if result["success"]:
        return f"操作成功！已执行 {result['action']} 动作，对象：{result['object_manipulated']}"
    else:
        return f"操作失败：{result['message']}"
