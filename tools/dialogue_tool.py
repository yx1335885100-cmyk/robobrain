# -*- coding: utf-8 -*-
"""
Dialogue Tool - 对话工具
语音交互功能
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, **kwargs):
        if func:
            return func
        return lambda f: f


class DialogueTool:
    """对话工具"""
    
    name = "dialogue"
    description = "对话工具，用于语音交互"
    
    def __init__(self):
        self._conversation_history = []
    
    def speak(self, message: str) -> Dict:
        """说话"""
        # 模拟说话时间
        speak_time = len(message) * 0.05
        time.sleep(min(speak_time, 2.0))
        
        self._conversation_history.append({
            "role": "assistant",
            "content": message,
            "timestamp": time.time()
        })
        
        return {
            "success": True,
            "spoken": message,
            "duration": speak_time
        }
    
    def listen(self, timeout: float = 5.0) -> Dict:
        """监听"""
        # 模拟监听
        time.sleep(0.5)
        
        return {
            "success": True,
            "heard": "模拟的语音输入",
            "confidence": 0.95
        }
    
    def respond(self, query: str, response: str) -> Dict:
        """响应"""
        self._conversation_history.append({
            "role": "user",
            "content": query,
            "timestamp": time.time()
        })
        
        result = self.speak(response)
        
        return {
            "success": True,
            "query": query,
            "response": response
        }
    
    def get_history(self, limit: int = 10):
        """获取对话历史"""
        return self._conversation_history[-limit:]


@tool
def dialogue_tool(action: str, **kwargs) -> str:
    """
    对话工具。
    
    用于语音交互和对话。
    
    Args:
        action: 动作类型 (speak/listen/respond)
        kwargs: 动作参数
    
    Returns:
        对话结果描述
    """
    dialogue = DialogueTool()
    
    if action == "speak":
        message = kwargs.get("message", "")
        result = dialogue.speak(message)
        return f"已说：{message}"
    elif action == "listen":
        result = dialogue.listen()
        return f"听到：{result['heard']}"
    elif action == "respond":
        query = kwargs.get("query", "")
        response = kwargs.get("response", "")
        result = dialogue.respond(query, response)
        return f"回答：{response}"
    else:
        return f"未知动作: {action}"
