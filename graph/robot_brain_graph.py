# -*- coding: utf-8 -*-
"""
Robot Brain Graph - 机器人大脑工作流图
使用 LangGraph 构建完整的认知闭环
"""

import time
from typing import Dict, List, Optional, Any, Callable, TypedDict, Annotated
from IPython.display import Image, display

# LangGraph 核心导入
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.prebuilt import ToolNode
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("[Warning] LangGraph not available. Install with: pip install langgraph")

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import (
    RobotState, BrainPhase, create_initial_state,
    update_phase, increment_iteration
)
from nodes import (
    perception_node,
    planning_node,
    scheduling_node,
    execution_node,
    feedback_node,
    route_next_node,
    route_after_perception,
    route_after_planning,
    route_after_scheduling,
    route_after_execution,
    route_after_feedback
)


class RobotBrainGraph:
    """
    机器人智慧大脑图
    
    使用 LangGraph 构建的认知闭环工作流
    
    图结构：
    START -> perception -> planning -> scheduling -> execution -> feedback -> END
                ↑                                                        |
                |___________________________<___________________________|
    
    特点：
    - 基于状态的流转
    - 条件边路由
    - 支持检查点
    - 支持人机交互
    """
    
    def __init__(self, llm=None, checkpointer=None):
        """
        初始化机器人智慧大脑图
        
        Args:
            llm: 大语言模型实例
            checkpointer: 检查点保存器
        """
        self.llm = llm
        self.checkpointer = checkpointer or (MemorySaver() if LANGGRAPH_AVAILABLE else None)
        
        # 构建图
        self._graph = None
        self._compiled = False
        
        if LANGGRAPH_AVAILABLE:
            self._build_graph()
    
    def _build_graph(self):
        """构建 LangGraph 图"""
        # 创建状态图
        workflow = StateGraph(RobotState)
        
        # 添加节点
        workflow.add_node("perception", perception_node)
        workflow.add_node("planning", planning_node)
        workflow.add_node("scheduling", scheduling_node)
        workflow.add_node("execution", execution_node)
        workflow.add_node("feedback", feedback_node)
        
        # 设置入口点
        workflow.set_entry_point("perception")
        
        # 添加边（线性流程）
        workflow.add_edge("perception", "planning")
        workflow.add_edge("planning", "scheduling")
        workflow.add_edge("scheduling", "execution")
        workflow.add_edge("execution", "feedback")
        
        # 添加条件边（从反馈节点出发）
        workflow.add_conditional_edges(
            "feedback",
            route_next_node,
            {
                "perception": "perception",
                "planning": "planning",
                "scheduling": "scheduling",
                "execution": "execution",
                "feedback": "feedback",
                "end": END
            }
        )
        
        # 编译图
        self._graph = workflow.compile(checkpointer=self.checkpointer)
        self._compiled = True
        
        print("[RobotBrainGraph] Graph built and compiled successfully")
    
    def run(self, user_input: str, session_id: str = "default", 
            config: Dict = None) -> Dict:
        """
        运行机器人智慧大脑
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            config: 运行配置
            
        Returns:
            最终状态
        """
        if not self._compiled:
            print("[RobotBrainGraph] Graph not compiled")
            return {}
        
        # 创建初始状态
        initial_state = create_initial_state(session_id)
        initial_state["user_input"] = user_input
        initial_state["instruction"] = user_input
        initial_state["goal"] = user_input
        
        # 配置
        run_config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        if config:
            run_config.update(config)
        
        # 运行图
        try:
            result = self._graph.invoke(initial_state, run_config)
            return result
        except Exception as e:
            print(f"[RobotBrainGraph] Run error: {e}")
            return {"error": str(e)}
    
    async def arun(self, user_input: str, session_id: str = "default",
                   config: Dict = None) -> Dict:
        """
        异步运行机器人智慧大脑
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            config: 运行配置
            
        Returns:
            最终状态
        """
        if not self._compiled:
            print("[RobotBrainGraph] Graph not compiled")
            return {}
        
        # 创建初始状态
        initial_state = create_initial_state(session_id)
        initial_state["user_input"] = user_input
        initial_state["instruction"] = user_input
        initial_state["goal"] = user_input
        
        # 配置
        run_config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        if config:
            run_config.update(config)
        
        # 异步运行图
        try:
            result = await self._graph.ainvoke(initial_state, run_config)
            return result
        except Exception as e:
            print(f"[RobotBrainGraph] Async run error: {e}")
            return {"error": str(e)}
    
    def stream(self, user_input: str, session_id: str = "default",
               config: Dict = None):
        """
        流式运行机器人智慧大脑
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            config: 运行配置
            
        Yields:
            状态更新
        """
        if not self._compiled:
            print("[RobotBrainGraph] Graph not compiled")
            return
        
        # 创建初始状态
        initial_state = create_initial_state(session_id)
        initial_state["user_input"] = user_input
        initial_state["instruction"] = user_input
        initial_state["goal"] = user_input
        
        # 配置
        run_config = {
            "configurable": {
                "thread_id": session_id
            }
        }
        if config:
            run_config.update(config)
        
        # 流式运行
        try:
            for event in self._graph.stream(initial_state, run_config):
                yield event
        except Exception as e:
            print(f"[RobotBrainGraph] Stream error: {e}")
            yield {"error": str(e)}
    
    def get_graph_image(self) -> Optional[Any]:
        """
        获取图的图像表示
        
        Returns:
            图像对象（如果可用）
        """
        if not self._compiled or not LANGGRAPH_AVAILABLE:
            return None
        
        try:
            return Image(self._graph.get_graph().draw_mermaid_png())
        except Exception as e:
            print(f"[RobotBrainGraph] Failed to generate graph image: {e}")
            return None
    
    def get_graph_mermaid(self) -> str:
        """
        获取图的 Mermaid 表示
        
        Returns:
            Mermaid 格式的图描述
        """
        if not self._compiled or not LANGGRAPH_AVAILABLE:
            return ""
        
        try:
            return self._graph.get_graph().draw_mermaid()
        except Exception as e:
            print(f"[RobotBrainGraph] Failed to generate mermaid: {e}")
            return self._get_default_mermaid()
    
    def _get_default_mermaid(self) -> str:
        """获取默认的 Mermaid 图描述"""
        return """
```mermaid
graph TD
    START([START]) --> perception[感知节点<br/>Perception]
    perception --> planning[规划节点<br/>Planning]
    planning --> scheduling[调度节点<br/>Scheduling]
    scheduling --> execution[执行节点<br/>Execution]
    execution --> feedback[反馈节点<br/>Feedback]
    
    feedback -->|继续| perception
    feedback -->|重规划| planning
    feedback -->|完成| END([END])
    
    style START fill:#90EE90
    style END fill:#FFB6C1
    style perception fill:#87CEEB
    style planning fill:#DDA0DD
    style scheduling fill:#F0E68C
    style execution fill:#FFA07A
    style feedback fill:#98FB98
```
"""


def create_robot_brain_graph(llm=None, checkpointer=None) -> RobotBrainGraph:
    """
    创建机器人智慧大脑图
    
    Args:
        llm: 大语言模型实例
        checkpointer: 检查点保存器
        
    Returns:
        RobotBrainGraph 实例
    """
    return RobotBrainGraph(llm=llm, checkpointer=checkpointer)


def run_robot_brain(user_input: str, llm=None, session_id: str = "default") -> Dict:
    """
    运行机器人智慧大脑的便捷函数
    
    Args:
        user_input: 用户输入
        llm: 大语言模型实例
        session_id: 会话ID
        
    Returns:
        最终状态
    """
    graph = create_robot_brain_graph(llm=llm)
    return graph.run(user_input, session_id=session_id)
