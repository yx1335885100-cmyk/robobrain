# -*- coding: utf-8 -*-
"""
Humanoid Robot Brain - Main Entry
人型机器人智慧大脑主入口

这是机器人智慧大脑的主程序入口，整合所有模块实现完整的认知闭环:
感知 -> 任务规划 -> 任务调度 -> 任务执行 -> 执行反馈 -> 规划调整
"""

import asyncio
import signal
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.brain import RobotBrain, BrainState
from core.task_manager import TaskManager, Task, TaskPriority, TaskStatus
from core.task_planner import TaskPlanner
from core.task_scheduler import TaskScheduler
from core.task_executor import TaskExecutor

from perception.asr_module import ASRModule
from perception.vision_module import VisionModule
from perception.sensor_fusion import SensorFusion

from ros2_interface.joint_monitor import JointMonitor
from ros2_interface.ros2_bridge import ROS2Bridge

from skills.vln_skill import VLNSkill
from skills.vla_skill import VLASkill
from skills.skill_registry import SkillRegistry, get_registry

from planning.global_planner import GlobalPlanner
from planning.local_planner import LocalPlanner
from planning.motion_planner import MotionPlanner

from execution.action_executor import ActionExecutor
from execution.feedback_handler import FeedbackHandler, FeedbackType

from utils.logger import get_logger
from utils.config import get_config


class HumanoidRobotBrain:
    """
    人型机器人智慧大脑
    
    整合所有模块，提供完整的机器人智能控制能力
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化机器人智慧大脑
        
        Args:
            config_path: 配置文件路径
        """
        self.logger = get_logger('robot_brain')
        self.config = get_config()
        
        # 加载配置
        if config_path:
            self.config.load(config_path)
        self.config.load_from_env()
        
        self.logger.info("Initializing Humanoid Robot Brain...")
        
        # 初始化核心大脑
        self.brain = RobotBrain(self.config.get_section('brain'))
        
        # 初始化感知模块
        self._init_perception()
        
        # 初始化ROS2接口
        self._init_ros2()
        
        # 初始化技能
        self._init_skills()
        
        # 初始化规划模块
        self._init_planning()
        
        # 初始化执行模块
        self._init_execution()
        
        # 运行状态
        self._running = False
        
        self.logger.info("Humanoid Robot Brain initialized successfully")
    
    def _init_perception(self):
        """初始化感知模块"""
        self.logger.info("Initializing perception modules...")
        
        # ASR模块
        asr_config = self.config.get('perception.asr', {})
        self.asr = ASRModule()
        self.asr.initialize()
        
        # 视觉模块
        vision_config = self.config.get('perception.vision', {})
        self.vision = VisionModule()
        self.vision.initialize()
        
        # 传感器融合
        self.sensor_fusion = SensorFusion()
        self.sensor_fusion.register_asr(self.asr)
        self.sensor_fusion.register_vision(self.vision)
        
        # 注册到大脑
        self.brain.register_perception_module('asr', self.asr)
        self.brain.register_perception_module('vision', self.vision)
        
        self.logger.info("Perception modules initialized")
    
    def _init_ros2(self):
        """初始化ROS2接口"""
        self.logger.info("Initializing ROS2 interface...")
        
        # ROS2桥接
        ros2_config = self.config.get_section('ros2')
        self.ros2_bridge = ROS2Bridge(ros2_config.get('node_name', 'robot_brain'))
        self.ros2_bridge.initialize()
        
        # 关节监测器
        joint_update_rate = ros2_config.get('joint_update_rate', 100)
        self.joint_monitor = JointMonitor(update_rate=joint_update_rate)
        self.joint_monitor.initialize_ros2()
        
        # 注册到大脑
        self.brain.register_ros2_bridge(self.ros2_bridge)
        self.brain.register_joint_monitor(self.joint_monitor)
        self.sensor_fusion.register_joint_monitor(self.joint_monitor)
        
        self.logger.info("ROS2 interface initialized")
    
    def _init_skills(self):
        """初始化技能"""
        self.logger.info("Initializing skills...")
        
        # 获取技能注册表
        self.skill_registry = get_registry()
        
        # VLN技能
        self.vln_skill = VLNSkill()
        self.vln_skill.set_ros2_bridge(self.ros2_bridge)
        self.vln_skill.set_joint_monitor(self.joint_monitor)
        self.brain.register_skill('vln', VLNSkill)
        
        # VLA技能
        self.vla_skill = VLASkill()
        self.vla_skill.set_vision_module(self.vision)
        self.vla_skill.set_ros2_bridge(self.ros2_bridge)
        self.vla_skill.set_joint_monitor(self.joint_monitor)
        self.brain.register_skill('vla', VLASkill)
        
        self.logger.info("Skills initialized")
    
    def _init_planning(self):
        """初始化规划模块"""
        self.logger.info("Initializing planning modules...")
        
        self.global_planner = GlobalPlanner()
        self.local_planner = LocalPlanner()
        self.motion_planner = MotionPlanner()
        
        self.logger.info("Planning modules initialized")
    
    def _init_execution(self):
        """初始化执行模块"""
        self.logger.info("Initializing execution modules...")
        
        self.action_executor = ActionExecutor()
        self.action_executor.set_ros2_bridge(self.ros2_bridge)
        
        self.feedback_handler = FeedbackHandler()
        
        # 注册反馈回调
        self.feedback_handler.register_global_callback(self._on_feedback)
        
        self.logger.info("Execution modules initialized")
    
    def _on_feedback(self, feedback):
        """处理反馈"""
        if feedback.type == FeedbackType.ERROR:
            self.logger.error(f"Feedback error from {feedback.source}: {feedback.message}")
        elif feedback.type == FeedbackType.WARNING:
            self.logger.warning(f"Feedback warning from {feedback.source}: {feedback.message}")
        else:
            self.logger.info(f"Feedback from {feedback.source}: {feedback.message}")
    
    async def start(self):
        """启动机器人智慧大脑"""
        self.logger.info("Starting Humanoid Robot Brain...")
        self._running = True
        
        # 启动感知模块
        self.asr.start_listening()
        self.vision.start_capture()
        self.sensor_fusion.start_fusion()
        
        # 启动关节监测
        self.joint_monitor.start_monitoring()
        
        # 启动ROS2
        self.ros2_bridge.start_spinning()
        
        # 启动反馈处理
        self.feedback_handler.start()
        
        self.logger.info("Humanoid Robot Brain started")
        
        # 启动主循环
        await self._main_loop()
    
    async def _main_loop(self):
        """主循环"""
        while self._running:
            try:
                # 执行认知循环
                await self.brain.cognitive_cycle()
                
                # 短暂休眠
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                await asyncio.sleep(1)
    
    def stop(self):
        """停止机器人智慧大脑"""
        self.logger.info("Stopping Humanoid Robot Brain...")
        self._running = False
        
        # 停止各模块
        self.brain.stop()
        self.asr.stop_listening()
        self.vision.stop_capture()
        self.sensor_fusion.stop_fusion()
        self.joint_monitor.stop_monitoring()
        self.ros2_bridge.shutdown()
        self.feedback_handler.stop()
        
        self.logger.info("Humanoid Robot Brain stopped")
    
    async def submit_goal(self, goal: str) -> str:
        """
        提交目标
        
        Args:
            goal: 目标描述
            
        Returns:
            任务ID
        """
        self.logger.info(f"Submitting goal: {goal}")
        return await self.brain.submit_goal(goal)
    
    async def execute_skill(self, skill_name: str, parameters: dict) -> dict:
        """
        直接执行技能
        
        Args:
            skill_name: 技能名称
            parameters: 技能参数
            
        Returns:
            执行结果
        """
        self.logger.info(f"Executing skill: {skill_name}")
        return await self.brain.execute_skill(skill_name, parameters)
    
    def get_status(self) -> dict:
        """获取系统状态"""
        status = {
            'brain': self.brain.get_status(),
            'perception': {
                'asr': self.asr.get_statistics(),
                'vision': self.vision.get_statistics(),
                'fusion': self.sensor_fusion.get_statistics()
            },
            'ros2': {
                'bridge': self.ros2_bridge.get_status(),
                'joints': self.joint_monitor.get_statistics()
            },
            'skills': self.skill_registry.get_statistics(),
            'execution': {
                'actions': self.action_executor.get_statistics(),
                'feedback': self.feedback_handler.get_statistics()
            }
        }
        return status
    
    def get_joint_states(self) -> dict:
        """获取关节状态"""
        return self.brain.get_joint_states()


async def main():
    """主函数"""
    print("=" * 60)
    print("  Humanoid Robot Brain - 智慧大脑系统")
    print("=" * 60)
    
    # 创建机器人智慧大脑
    robot_brain = HumanoidRobotBrain()
    
    # 设置信号处理
    def signal_handler(sig, frame):
        print("\nReceived shutdown signal...")
        robot_brain.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 启动系统
        await robot_brain.start()
    except KeyboardInterrupt:
        print("\nKeyboard interrupt received...")
    finally:
        robot_brain.stop()


def run_demo():
    """运行演示"""
    async def demo():
        print("\n" + "=" * 60)
        print("  Running Demo - Humanoid Robot Brain")
        print("=" * 60 + "\n")
        
        # 创建大脑实例
        brain = HumanoidRobotBrain()
        
        # 启动系统
        print("[Demo] Starting system...")
        
        # 启动感知
        brain.asr.start_listening()
        brain.vision.start_capture()
        brain.sensor_fusion.start_fusion()
        brain.joint_monitor.start_monitoring()
        
        print("\n[Demo] System initialized")
        print("[Demo] Testing capabilities...\n")
        
        # 测试1：提交导航目标
        print("-" * 40)
        print("Test 1: VLN Navigation")
        print("-" * 40)
        result = await brain.execute_skill('vln', {
            'instruction': '导航到厨房'
        })
        print(f"VLN Result: {result}\n")
        
        # 测试2：提交操作目标
        print("-" * 40)
        print("Test 2: VLA Manipulation")
        print("-" * 40)
        result = await brain.execute_skill('vla', {
            'instruction': '帮我拿杯子'
        })
        print(f"VLA Result: {result}\n")
        
        # 测试3：查看关节状态
        print("-" * 40)
        print("Test 3: Joint State Monitoring")
        print("-" * 40)
        joint_states = brain.get_joint_states()
        print(f"Joint positions: {list(joint_states.get('positions', {}).keys())[:5]}...")
        print(f"Is moving: {joint_states.get('is_moving', False)}\n")
        
        # 测试4：模拟语音输入
        print("-" * 40)
        print("Test 4: ASR Simulation")
        print("-" * 40)
        asr_result = brain.asr.simulate_speech("请帮我打开灯")
        print(f"ASR Result: {asr_result.text}\n")
        
        # 测试5：系统状态
        print("-" * 40)
        print("Test 5: System Status")
        print("-" * 40)
        status = brain.get_status()
        print(f"Brain state: {status['brain']['state']}")
        print(f"Registered skills: {status['brain']['registered_skills']}")
        print(f"Perception modules: {status['brain']['registered_perception_modules']}\n")
        
        # 停止系统
        print("[Demo] Stopping system...")
        brain.stop()
        
        print("\n" + "=" * 60)
        print("  Demo completed successfully!")
        print("=" * 60 + "\n")
    
    # 运行演示
    asyncio.run(demo())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Humanoid Robot Brain')
    parser.add_argument('--demo', action='store_true', help='Run demo mode')
    parser.add_argument('--config', type=str, help='Config file path')
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo()
    else:
        asyncio.run(main())
