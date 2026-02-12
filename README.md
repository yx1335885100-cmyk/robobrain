# Humanoid Robot Brain

人型机器人智慧大脑系统 - 一个完整的机器人认知架构实现

## 项目概述

本项目是一个人型机器人智慧大脑系统，实现了完整的认知闭环：

```
感知 → 任务规划 → 任务调度 → 任务执行 → 执行反馈 → 规划调整
```

## 核心能力

### 1. 多任务管理能力
- 任务创建、调度、状态管理
- 优先级队列调度
- 任务依赖解析
- 任务重试机制

### 2. ROS2关节状态监测
- 实时关节状态监测
- 关节限制检查
- 异常检测
- 人形机器人关节配置（头、双臂、双手、躯干、双腿）

### 3. 任务规划能力
- 全局规划（长期目标分解）
- 局部规划（短期行动计划）
- 层次化任务网络（HTN）
- 目标导向行动规划（GOAP）

### 4. 任务调度能力
- 优先级调度
- 资源感知调度
- 时间片轮转
- 自适应调度

### 5. Skills能力支持
- VLN（视觉语言导航）
- VLA（视觉语言操作）
- 技能注册与管理

### 6. 完整认知闭环
- ASR语音感知
- 视觉感知
- 传感器融合
- 动作执行
- 反馈处理

## 项目结构

```
humanoid_robot_brain/
├── core/                   # 核心模块
│   ├── brain.py           # 大脑主控制器
│   ├── task_manager.py    # 任务管理器
│   ├── task_planner.py    # 任务规划器
│   ├── task_scheduler.py  # 任务调度器
│   └── task_executor.py   # 任务执行器
├── perception/            # 感知模块
│   ├── asr_module.py     # 语音识别
│   ├── vision_module.py  # 视觉感知
│   └── sensor_fusion.py  # 传感器融合
├── ros2_interface/        # ROS2接口
│   ├── joint_monitor.py  # 关节监测
│   ├── ros2_bridge.py    # ROS2桥接
│   └── message_types.py  # 消息类型
├── skills/               # 技能模块
│   ├── base_skill.py     # 技能基类
│   ├── vln_skill.py      # VLN技能
│   ├── vla_skill.py      # VLA技能
│   └── skill_registry.py # 技能注册表
├── planning/             # 规划模块
│   ├── global_planner.py # 全局规划
│   ├── local_planner.py  # 局部规划
│   └── motion_planner.py # 运动规划
├── execution/            # 执行模块
│   ├── action_executor.py   # 动作执行器
│   └── feedback_handler.py  # 反馈处理器
├── utils/                # 工具模块
│   ├── logger.py        # 日志工具
│   ├── state_machine.py # 状态机
│   └── config.py        # 配置管理
├── config/              # 配置文件
│   └── default_config.json
├── main.py              # 主入口
└── requirements.txt     # 依赖
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行演示

```bash
python main.py --demo
```

### 运行主程序

```bash
python main.py
```

## 使用示例

```python
from main import HumanoidRobotBrain
import asyncio

async def example():
    # 创建大脑实例
    brain = HumanoidRobotBrain()
    
    # 启动系统
    # await brain.start()
    
    # 执行VLN导航
    result = await brain.execute_skill('vln', {
        'instruction': '导航到厨房'
    })
    
    # 执行VLA操作
    result = await brain.execute_skill('vla', {
        'instruction': '帮我拿杯子'
    })
    
    # 获取关节状态
    joints = brain.get_joint_states()
    
    # 停止系统
    brain.stop()

asyncio.run(example())
```

## 系统要求

- Python 3.7+
- ROS2 (可选，用于真实机器人)
- CUDA (可选，用于GPU加速)

## 许可证

MIT License
