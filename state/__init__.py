# -*- coding: utf-8 -*-
"""
State Definitions - LangGraph 状态定义
定义机器人智慧大脑的所有状态结构
"""

from typing import TypedDict, List, Dict, Optional, Any, Annotated
from dataclasses import dataclass, field
from enum import Enum
import operator
import time


class BrainPhase(Enum):
    """大脑阶段枚举"""
    IDLE = "idle"
    PERCEPTION = "perception"
    PLANNING = "planning"
    SCHEDULING = "scheduling"
    EXECUTION = "execution"
    FEEDBACK = "feedback"
    ERROR = "error"


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """任务优先级枚举"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


# ==================== 子状态定义 ====================

@dataclass
class JointState:
    """关节状态"""
    name: str
    position: float = 0.0
    velocity: float = 0.0
    effort: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class PerceptionData:
    """感知数据"""
    modality: str  # 'audio', 'visual', 'tactile'
    content: Any
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    skill: Optional[str] = None
    parameters: Dict = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


# ==================== LangGraph 状态定义 ====================

class PerceptionState(TypedDict):
    """感知状态 - LangGraph TypedDict"""
    # 原始感知数据
    audio_input: Optional[str]  # 语音输入文本
    visual_data: Optional[Dict]  # 视觉数据
    joint_states: Dict[str, float]  # 关节状态
    
    # 感知结果
    recognized_speech: Optional[str]
    detected_objects: List[Dict]
    scene_description: Optional[str]
    
    # 元数据
    perception_confidence: float
    last_perception_time: float


class TaskState(TypedDict):
    """任务状态 - LangGraph TypedDict"""
    # 任务队列
    pending_tasks: List[Dict]
    ready_tasks: List[Dict]
    running_task: Optional[Dict]
    completed_tasks: List[Dict]
    failed_tasks: List[Dict]
    
    # 当前任务
    current_task_id: Optional[str]
    current_task_status: str


class ExecutionState(TypedDict):
    """执行状态 - LangGraph TypedDict"""
    # 执行状态
    is_executing: bool
    current_skill: Optional[str]
    current_action: Optional[str]
    
    # 执行结果
    action_results: List[Dict]
    last_result: Optional[Dict]
    
    # 反馈
    feedback_messages: List[str]
    errors: List[str]


class MemoryState(TypedDict):
    """记忆状态 - LangGraph TypedDict"""
    # 对话历史
    conversation_history: List[Dict]
    
    # 任务历史
    task_history: List[Dict]
    
    # 学习记忆
    learned_patterns: Dict
    
    # 上下文
    current_context: Dict


# ==================== 主状态定义 ====================

class RobotState(TypedDict):
    """
    机器人主状态 - LangGraph 核心状态定义
    
    这个状态在整个图中流转，各个节点可以读取和更新状态
    """
    # ========== 基础信息 ==========
    session_id: str
    current_phase: str  # BrainPhase.value
    iteration_count: int
    max_iterations: int
    
    # ========== 用户输入 ==========
    user_input: Optional[str]
    goal: Optional[str]
    instruction: Optional[str]
    
    # ========== 感知状态 ==========
    perception: PerceptionState
    
    # ========== 任务状态 ==========
    tasks: TaskState
    
    # ========== 执行状态 ==========
    execution: ExecutionState
    
    # ========== 记忆状态 ==========
    memory: MemoryState
    
    # ========== 规划结果 ==========
    global_plan: List[Dict]
    local_plan: List[Dict]
    current_step: int
    
    # ========== 决策结果 ==========
    next_action: Optional[str]
    next_node: Optional[str]
    
    # ========== 错误处理 ==========
    has_error: bool
    error_message: Optional[str]
    retry_count: int
    
    # ========== 系统状态 ==========
    robot_mode: str  # 'autonomous', 'teleop', 'idle'
    battery_level: float
    is_moving: bool
    
    # ========== 元数据 ==========
    start_time: float
    last_update_time: float
    metadata: Dict


# ==================== 状态操作符 ====================

def merge_dicts(left: Dict, right: Dict) -> Dict:
    """合并字典的操作符"""
    return {**left, **right}


def append_to_list(left: List, right: List) -> List:
    """追加列表的操作符"""
    return left + right


# ==================== 状态初始化函数 ====================

def create_initial_state(session_id: str = "default") -> RobotState:
    """
    创建初始状态
    
    Args:
        session_id: 会话ID
        
    Returns:
        初始化的机器人状态
    """
    current_time = time.time()
    
    return RobotState(
        # 基础信息
        session_id=session_id,
        current_phase=BrainPhase.IDLE.value,
        iteration_count=0,
        max_iterations=10,
        
        # 用户输入
        user_input=None,
        goal=None,
        instruction=None,
        
        # 感知状态
        perception=PerceptionState(
            audio_input=None,
            visual_data=None,
            joint_states={},
            recognized_speech=None,
            detected_objects=[],
            scene_description=None,
            perception_confidence=0.0,
            last_perception_time=current_time
        ),
        
        # 任务状态
        tasks=TaskState(
            pending_tasks=[],
            ready_tasks=[],
            running_task=None,
            completed_tasks=[],
            failed_tasks=[],
            current_task_id=None,
            current_task_status="idle"
        ),
        
        # 执行状态
        execution=ExecutionState(
            is_executing=False,
            current_skill=None,
            current_action=None,
            action_results=[],
            last_result=None,
            feedback_messages=[],
            errors=[]
        ),
        
        # 记忆状态
        memory=MemoryState(
            conversation_history=[],
            task_history=[],
            learned_patterns={},
            current_context={}
        ),
        
        # 规划结果
        global_plan=[],
        local_plan=[],
        current_step=0,
        
        # 决策结果
        next_action=None,
        next_node=None,
        
        # 错误处理
        has_error=False,
        error_message=None,
        retry_count=0,
        
        # 系统状态
        robot_mode='autonomous',
        battery_level=1.0,
        is_moving=False,
        
        # 元数据
        start_time=current_time,
        last_update_time=current_time,
        metadata={}
    )


# ==================== 状态更新辅助函数 ====================

def update_phase(state: RobotState, new_phase: BrainPhase) -> RobotState:
    """更新大脑阶段"""
    return {
        **state,
        "current_phase": new_phase.value,
        "last_update_time": time.time()
    }


def add_task(state: RobotState, task: Dict) -> RobotState:
    """添加任务到队列"""
    pending_tasks = state["tasks"]["pending_tasks"] + [task]
    tasks = {**state["tasks"], "pending_tasks": pending_tasks}
    return {**state, "tasks": tasks}


def set_goal(state: RobotState, goal: str) -> RobotState:
    """设置目标"""
    return {
        **state,
        "goal": goal,
        "instruction": goal,
        "last_update_time": time.time()
    }


def set_perception_result(state: RobotState, result: Dict) -> RobotState:
    """设置感知结果"""
    perception = {**state["perception"], **result, "last_perception_time": time.time()}
    return {**state, "perception": perception}


def set_execution_result(state: RobotState, result: Dict) -> RobotState:
    """设置执行结果"""
    execution = {
        **state["execution"],
        "last_result": result,
        "action_results": state["execution"]["action_results"] + [result]
    }
    return {**state, "execution": execution}


def add_error(state: RobotState, error: str) -> RobotState:
    """添加错误"""
    return {
        **state,
        "has_error": True,
        "error_message": error,
        "execution": {
            **state["execution"],
            "errors": state["execution"]["errors"] + [error]
        }
    }


def clear_error(state: RobotState) -> RobotState:
    """清除错误"""
    return {
        **state,
        "has_error": False,
        "error_message": None
    }


def increment_iteration(state: RobotState) -> RobotState:
    """增加迭代次数"""
    return {
        **state,
        "iteration_count": state["iteration_count"] + 1,
        "last_update_time": time.time()
    }
