# -*- coding: utf-8 -*-
"""
Manipulation Tool - 操作工具
基础操作功能
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass, field

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func:
            return func
        return lambda f: f


@dataclass
class ManipulationState:
    """操作状态"""
    gripper_open: bool = True
    held_object: Optional[str] = None


class ManipulationTool:
    """基础操作工具"""
    
    name = "manipulation"
    description = "基础操作工具，用于控制机器人手臂和夹爪"
    
    def __init__(self):
        self._state = ManipulationState()
    
    def open_gripper(self) -> Dict:
        """打开夹爪"""
        self._state.gripper_open = True
        time.sleep(0.2)
        return {"success": True, "gripper_state": "open"}
    
    def close_gripper(self) -> Dict:
        """关闭夹爪"""
        self._state.gripper_open = False
        time.sleep(0.2)
        return {"success": True, "gripper_state": "closed"}
    
    def grasp(self, object_name: str) -> Dict:
        """抓取物体"""
        if not self._state.gripper_open:
            return {"success": False, "error": "Gripper not open"}
        
        time.sleep(0.3)
        self._state.gripper_open = False
        self._state.held_object = object_name
        
        return {
            "success": True,
            "object": object_name,
            "message": f"Grasped {object_name}"
        }
    
    def release(self) -> Dict:
        """释放物体"""
        if self._state.held_object is None:
            return {"success": False, "error": "No object held"}
        
        released = self._state.held_object
        self._state.gripper_open = True
        self._state.held_object = None
        
        return {
            "success": True,
            "released_object": released,
            "message": f"Released {released}"
        }
    
    def get_held_object(self) -> Optional[str]:
        """获取持有的物体"""
        return self._state.held_object


@tool
def manipulation_tool(action: str, **kwargs) -> str:
    """
    基础操作工具。
    
    用于控制机器人的夹爪和手臂操作。
    
    Args:
        action: 动作类型 (open_gripper/close_gripper/grasp/release)
        kwargs: 动作参数
    
    Returns:
        操作结果描述
    """
    manip = ManipulationTool()
    
    if action == "open_gripper":
        result = manip.open_gripper()
        return "夹爪已打开"
    elif action == "close_gripper":
        result = manip.close_gripper()
        return "夹爪已关闭"
    elif action == "grasp":
        object_name = kwargs.get("object_name", "目标物体")
        result = manip.grasp(object_name)
        return f"已抓取 {object_name}" if result["success"] else "抓取失败"
    elif action == "release":
        result = manip.release()
        return f"已释放 {result.get('released_object', '物体')}" if result["success"] else "释放失败"
    else:
        return f"未知动作: {action}"
