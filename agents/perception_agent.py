# -*- coding: utf-8 -*-
"""
Perception Agent - 感知 Agent
专门处理感知任务的 Agent
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


PERCEPTION_SYSTEM_PROMPT = """你是一个机器人感知系统的专家 Agent。
你的职责是：
1. 分析和理解多模态感知数据（语音、视觉、触觉等）
2. 识别环境中的物体和场景
3. 理解用户的语音指令和意图
4. 提供结构化的感知结果

请始终以专业、准确的方式处理感知任务。"""


class PerceptionAgent:
    """
    感知 Agent
    
    专门处理感知相关任务：
    - 语音理解
    - 视觉分析
    - 意图识别
    - 场景理解
    """
    
    def __init__(self, llm=None):
        """
        初始化感知 Agent
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
        self._perception_history: List[Dict] = []
    
    def process(self, state: Dict) -> Dict:
        """
        处理感知任务
        
        Args:
            state: 当前状态
            
        Returns:
            感知结果
        """
        # 提取感知数据
        audio_input = state.get("user_input")
        perception_state = state.get("perception", {})
        
        # 使用 LLM 进行高级理解
        if self.llm and audio_input:
            understanding = self._understand_with_llm(audio_input, perception_state)
        else:
            understanding = self._basic_understanding(audio_input, perception_state)
        
        # 记录历史
        self._perception_history.append({
            "input": audio_input,
            "result": understanding,
            "timestamp": __import__('time').time()
        })
        
        return {
            "perception": {
                **perception_state,
                **understanding
            }
        }
    
    def _understand_with_llm(self, audio_input: str, perception_state: Dict) -> Dict:
        """使用 LLM 进行理解"""
        if not LANGCHAIN_AVAILABLE or not self.llm:
            return self._basic_understanding(audio_input, perception_state)
        
        try:
            messages = [
                SystemMessage(content=PERCEPTION_SYSTEM_PROMPT),
                HumanMessage(content=f"请分析以下输入并提取关键信息：\n\n输入：{audio_input}")
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "recognized_speech": audio_input,
                "understanding": response.content,
                "perception_confidence": 0.9
            }
        except Exception as e:
            print(f"[PerceptionAgent] LLM error: {e}")
            return self._basic_understanding(audio_input, perception_state)
    
    def _basic_understanding(self, audio_input: str, perception_state: Dict) -> Dict:
        """基本理解（无 LLM）"""
        return {
            "recognized_speech": audio_input,
            "perception_confidence": 0.8
        }
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取感知历史"""
        return self._perception_history[-limit:]
