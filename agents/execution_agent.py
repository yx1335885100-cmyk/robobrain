# -*- coding: utf-8 -*-
"""
Execution Agent - 执行 Agent
专门处理任务执行的 Agent
"""

from typing import Dict, List, Optional, Any
import time

from tools import VLNTool, VLATool


class ExecutionAgent:
    """
    执行 Agent
    
    专门处理执行相关任务：
    - 技能调用
    - 动作执行
    - 状态监控
    - 错误处理
    """
    
    def __init__(self, llm=None):
        """
        初始化执行 Agent
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        
        # 注册工具
        self._tools = {
            "vln": VLNTool(),
            "vla": VLATool()
        }
        
        self._execution_history: List[Dict] = []
    
    def register_tool(self, name: str, tool: Any):
        """注册工具"""
        self._tools[name] = tool
    
    def process(self, state: Dict) -> Dict:
        """
        处理执行任务
        
        Args:
            state: 当前状态
            
        Returns:
            执行结果
        """
        running_task = state.get("tasks", {}).get("running_task")
        
        if not running_task:
            return {"execution": {"is_executing": False}}
        
        # 执行任务
        result = self._execute_task(running_task)
        
        # 记录历史
        self._execution_history.append({
            "task": running_task,
            "result": result,
            "timestamp": time.time()
        })
        
        return {
            "execution": {
                "is_executing": False,
                "last_result": result,
                "current_skill": running_task.get("skill")
            }
        }
    
    def _execute_task(self, task: Dict) -> Dict:
        """执行任务"""
        skill_name = task.get("skill")
        parameters = task.get("parameters", {})
        
        tool = self._tools.get(skill_name)
        
        if tool is None:
            return {
                "success": False,
                "error": f"Tool not found: {skill_name}"
            }
        
        try:
            # 调用工具
            if skill_name == "vln":
                result = tool.execute(
                    instruction=parameters.get("instruction", ""),
                    speed=parameters.get("speed", 0.5)
                )
            elif skill_name == "vla":
                result = tool.execute(
                    instruction=parameters.get("instruction", ""),
                    action_type=parameters.get("action_type", "grasp")
                )
            else:
                result = tool(**parameters) if callable(tool) else {"success": False}
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取执行历史"""
        return self._execution_history[-limit:]
