# -*- coding: utf-8 -*-
"""
Humanoid Robot Brain - LangGraph Version
人型机器人智慧大脑 - LangGraph 版本

基于 LangGraph 框架的完整认知闭环实现：
感知 -> 规划 -> 调度 -> 执行 -> 反馈 -> 调整

支持两种模式：
1. LangGraph 模式（需要安装 langgraph）
2. 模拟模式（无需额外依赖）
"""

import asyncio
import time
import sys
import os

# 检查依赖是否可用
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    print("[Info] LangGraph not installed. Running in simulation mode.")
    print("[Info] Install with: pip install langgraph langchain-core")

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入核心模块
from state import (
    RobotState, BrainPhase, create_initial_state,
    update_phase, increment_iteration
)
from tools import VLNTool, VLATool, NavigationTool, ManipulationTool
from agents import PerceptionAgent, PlanningAgent, ExecutionAgent, SupervisorAgent


class SimpleStateGraph:
    """
    简化的状态图（不依赖 LangGraph）
    """
    
    def __init__(self, state_schema):
        self._nodes = {}
        self._edges = {}
        self._entry_point = None
        self._state_schema = state_schema
    
    def add_node(self, name: str, func):
        self._nodes[name] = func
    
    def add_edge(self, from_node: str, to_node: str):
        if from_node not in self._edges:
            self._edges[from_node] = []
        self._edges[from_node].append(("edge", to_node))
    
    def add_conditional_edges(self, from_node: str, condition_func, edges: dict):
        if from_node not in self._edges:
            self._edges[from_node] = []
        self._edges[from_node].append(("conditional", condition_func, edges))
    
    def set_entry_point(self, node_name: str):
        self._entry_point = node_name
    
    def set_finish_point(self, node_name: str):
        self._finish_point = node_name
    
    def compile(self, checkpointer=None):
        return self
    
    def invoke(self, initial_state: dict, config: dict = None) -> dict:
        """执行图"""
        state = initial_state.copy()
        current_node = self._entry_point
        max_iterations = state.get("max_iterations", 10)
        iteration = 0
        
        while current_node and iteration < max_iterations:
            # 执行节点
            if current_node in self._nodes:
                node_func = self._nodes[current_node]
                updates = node_func(state)
                state.update(updates)
                state["iteration_count"] = iteration + 1
            
            # 查找下一个节点
            if current_node in self._edges:
                for edge in self._edges[current_node]:
                    if edge[0] == "edge":
                        current_node = edge[1]
                        break
                    elif edge[0] == "conditional":
                        condition_func = edge[1]
                        edges = edge[2]
                        next_node_name = condition_func(state)
                        current_node = edges.get(next_node_name, "end")
                        if current_node == "end":
                            return state
                        break
            else:
                break
            
            iteration += 1
        
        return state


class HumanoidRobotBrainLangGraph:
    """
    人型机器人智慧大脑 - LangGraph 版本
    
    支持 LangGraph 和模拟两种模式
    """
    
    def __init__(self, llm=None, config: dict = None):
        """
        初始化机器人智慧大脑
        
        Args:
            llm: 大语言模型实例
            config: 配置字典
        """
        self.llm = llm
        self.config = config or {}
        self.langgraph_available = LANGGRAPH_AVAILABLE
        
        # 初始化工具
        self._init_tools()
        
        # 初始化 Agent
        self._init_agents()
        
        # 创建图
        self.graph = self._create_graph()
        
        print(f"[HumanoidRobotBrain-LangGraph] Initialized (LangGraph: {LANGGRAPH_AVAILABLE})")
    
    def _init_tools(self):
        """初始化工具"""
        self.vln_tool = VLNTool()
        self.vla_tool = VLATool()
        self.navigation_tool = NavigationTool()
        self.manipulation_tool = ManipulationTool()
    
    def _init_agents(self):
        """初始化 Agent"""
        self.perception_agent = PerceptionAgent(self.llm)
        self.planning_agent = PlanningAgent(self.llm)
        self.execution_agent = ExecutionAgent(self.llm)
        self.supervisor_agent = SupervisorAgent(self.llm)
    
    def _create_graph(self):
        """创建图"""
        if LANGGRAPH_AVAILABLE:
            return self._create_langgraph()
        else:
            return self._create_simple_graph()
    
    def _create_langgraph(self):
        """创建 LangGraph 图"""
        from langgraph.graph import StateGraph, END
        
        workflow = StateGraph(RobotState)
        
        # 添加节点
        workflow.add_node("perception", self._perception_node)
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("scheduling", self._scheduling_node)
        workflow.add_node("execution", self._execution_node)
        workflow.add_node("feedback", self._feedback_node)
        
        # 设置入口
        workflow.set_entry_point("perception")
        
        # 添加边
        workflow.add_edge("perception", "planning")
        workflow.add_edge("planning", "scheduling")
        workflow.add_edge("scheduling", "execution")
        workflow.add_edge("execution", "feedback")
        
        # 条件边
        workflow.add_conditional_edges(
            "feedback",
            self._route_next,
            {
                "perception": "perception",
                "planning": "planning",
                "scheduling": "scheduling",
                "execution": "execution",
                "end": END
            }
        )
        
        return workflow.compile()
    
    def _create_simple_graph(self):
        """创建简化图"""
        workflow = SimpleStateGraph(RobotState)
        
        # 添加节点
        workflow.add_node("perception", self._perception_node)
        workflow.add_node("planning", self._planning_node)
        workflow.add_node("scheduling", self._scheduling_node)
        workflow.add_node("execution", self._execution_node)
        workflow.add_node("feedback", self._feedback_node)
        
        # 设置入口
        workflow.set_entry_point("perception")
        
        # 添加边
        workflow.add_edge("perception", "planning")
        workflow.add_edge("planning", "scheduling")
        workflow.add_edge("scheduling", "execution")
        workflow.add_edge("execution", "feedback")
        
        # 条件边
        workflow.add_conditional_edges(
            "feedback",
            self._route_next,
            {
                "perception": "perception",
                "planning": "planning",
                "scheduling": "scheduling",
                "execution": "execution",
                "end": "end"
            }
        )
        
        return workflow
    
    def _perception_node(self, state: dict) -> dict:
        """感知节点"""
        return self.perception_agent.process(state)
    
    def _planning_node(self, state: dict) -> dict:
        """规划节点"""
        return self.planning_agent.process(state)
    
    def _scheduling_node(self, state: dict) -> dict:
        """调度节点"""
        tasks = state.get("tasks", {}).get("pending_tasks", [])
        if tasks:
            return {
                "tasks": {
                    **state.get("tasks", {}),
                    "running_task": tasks[0],
                    "pending_tasks": tasks[1:]
                }
            }
        return {}
    
    def _execution_node(self, state: dict) -> dict:
        """执行节点"""
        return self.execution_agent.process(state)
    
    def _feedback_node(self, state: dict) -> dict:
        """反馈节点"""
        last_result = state.get("execution", {}).get("last_result", {})
        
        # 更新任务状态
        running_task = state.get("tasks", {}).get("running_task")
        if running_task:
            if last_result.get("success"):
                completed = state.get("tasks", {}).get("completed_tasks", [])
                completed.append({**running_task, "status": "completed"})
                return {
                    "tasks": {
                        **state.get("tasks", {}),
                        "running_task": None,
                        "completed_tasks": completed
                    }
                }
            else:
                failed = state.get("tasks", {}).get("failed_tasks", [])
                failed.append({**running_task, "status": "failed"})
                return {
                    "tasks": {
                        **state.get("tasks", {}),
                        "running_task": None,
                        "failed_tasks": failed
                    },
                    "has_error": True,
                    "error_message": last_result.get("error")
                }
        
        return {}
    
    def _route_next(self, state: dict) -> str:
        """路由决策"""
        # 检查迭代次数
        if state.get("iteration_count", 0) >= state.get("max_iterations", 10):
            return "end"
        
        # 检查是否还有任务
        if state.get("tasks", {}).get("pending_tasks"):
            return "scheduling"
        
        # 检查是否有运行中的任务
        if state.get("tasks", {}).get("running_task"):
            return "execution"
        
        return "end"
    
    def run(self, user_input: str, session_id: str = None) -> dict:
        """运行"""
        session_id = session_id or f"session_{int(time.time())}"
        
        print(f"\n[HumanoidRobotBrain] Processing: {user_input}")
        
        # 创建初始状态
        initial_state = create_initial_state(session_id)
        initial_state["user_input"] = user_input
        initial_state["goal"] = user_input
        
        # 执行图
        result = self.graph.invoke(initial_state)
        
        return result
    
    def stream(self, user_input: str, session_id: str = None):
        """流式运行"""
        result = self.run(user_input, session_id)
        yield {"final": result}


def run_demo():
    """运行演示"""
    print("=" * 70)
    print("  Humanoid Robot Brain - LangGraph Version")
    print("  人型机器人智慧大脑 - LangGraph 版本演示")
    print("=" * 70)
    
    # 创建大脑实例
    brain = HumanoidRobotBrainLangGraph()
    
    print("\n" + "-" * 50)
    print("Demo 1: VLN Navigation")
    print("-" * 50)
    result = brain.run("导航到厨房")
    last_result = result.get('execution', {}).get('last_result', {})
    print(f"Success: {last_result.get('success', False)}")
    print(f"Message: {last_result.get('message', 'N/A')}")
    
    print("\n" + "-" * 50)
    print("Demo 2: VLA Manipulation")
    print("-" * 50)
    result = brain.run("帮我拿那个杯子")
    last_result = result.get('execution', {}).get('last_result', {})
    print(f"Success: {last_result.get('success', False)}")
    print(f"Message: {last_result.get('message', 'N/A')}")
    
    print("\n" + "-" * 50)
    print("Demo 3: System Status")
    print("-" * 50)
    print(f"Total iterations: {result.get('iteration_count', 0)}")
    print(f"Completed tasks: {len(result.get('tasks', {}).get('completed_tasks', []))}")
    print(f"Failed tasks: {len(result.get('tasks', {}).get('failed_tasks', []))}")
    
    print("\n" + "=" * 70)
    print("  Demo Completed!")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Humanoid Robot Brain - LangGraph Version')
    parser.add_argument('--demo', action='store_true', help='Run demo mode')
    parser.add_argument('--input', type=str, help='Single input to process')
    
    args = parser.parse_args()
    
    if args.input:
        brain = HumanoidRobotBrainLangGraph()
        result = brain.run(args.input)
        print(f"\nResult: {result}")
    else:
        run_demo()
