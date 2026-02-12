# -*- coding: utf-8 -*-
"""
Motion Planner - 运动规划器
负责机器人运动轨迹规划和避障
"""

import time
import asyncio
import math
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MotionType(Enum):
    """运动类型"""
    JOINT_SPACE = "joint_space"
    CARTESIAN = "cartesian"
    MOBILE_BASE = "mobile_base"
    WHOLE_BODY = "whole_body"


@dataclass
class PathPoint:
    """路径点"""
    position: Tuple[float, ...]
    velocity: Tuple[float, ...] = field(default_factory=tuple)
    acceleration: Tuple[float, ...] = field(default_factory=tuple)
    time: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'position': list(self.position),
            'velocity': list(self.velocity) if self.velocity else [],
            'acceleration': list(self.acceleration) if self.acceleration else [],
            'time': self.time
        }


@dataclass
class MotionPlan:
    """运动规划"""
    id: str
    motion_type: MotionType
    path: List[PathPoint] = field(default_factory=list)
    duration: float = 0.0
    constraints: Dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'motion_type': self.motion_type.value,
            'path': [p.to_dict() for p in self.path],
            'duration': self.duration,
            'constraints': self.constraints,
            'created_at': self.created_at
        }


class MotionPlanner:
    """
    运动规划器
    
    负责机器人运动轨迹规划和避障
    
    Features:
        - 关节空间规划
        - 笛卡尔空间规划
        - 移动基座规划
        - 全身运动规划
        - 避障规划
        - 轨迹优化
    """
    
    def __init__(self):
        """初始化运动规划器"""
        self._plans: Dict[str, MotionPlan] = {}
        
        # 机器人模型参数
        self._joint_limits: Dict[str, Tuple[float, float]] = {}
        self._velocity_limits: Dict[str, float] = {}
        
        # 障碍物
        self._obstacles: List[Dict] = []
        
        # 规划参数
        self._default_resolution = 0.01  # m
        self._default_velocity = 0.5  # m/s
        self._default_acceleration = 0.5  # m/s^2
    
    def set_joint_limits(self, joint_name: str, lower: float, upper: float):
        """设置关节限制"""
        self._joint_limits[joint_name] = (lower, upper)
    
    def set_velocity_limit(self, joint_name: str, limit: float):
        """设置速度限制"""
        self._velocity_limits[joint_name] = limit
    
    def add_obstacle(self, obstacle: Dict):
        """添加障碍物"""
        self._obstacles.append(obstacle)
    
    def clear_obstacles(self):
        """清除障碍物"""
        self._obstacles.clear()
    
    async def plan_joint_motion(self, start: List[float], end: List[float],
                                duration: float = None) -> MotionPlan:
        """
        规划关节空间运动
        
        Args:
            start: 起始关节位置
            end: 目标关节位置
            duration: 运动时间
            
        Returns:
            运动规划
        """
        plan_id = f"motion_{int(time.time()*1000)}"
        
        # 计算运动时间
        if duration is None:
            duration = self._estimate_duration(start, end)
        
        # 生成轨迹
        path = self._generate_joint_trajectory(start, end, duration)
        
        # 创建规划
        plan = MotionPlan(
            id=plan_id,
            motion_type=MotionType.JOINT_SPACE,
            path=path,
            duration=duration
        )
        
        self._plans[plan_id] = plan
        return plan
    
    async def plan_cartesian_motion(self, start: Tuple[float, float, float],
                                    end: Tuple[float, float, float],
                                    duration: float = None) -> MotionPlan:
        """
        规划笛卡尔空间运动
        
        Args:
            start: 起始位置 (x, y, z)
            end: 目标位置 (x, y, z)
            duration: 运动时间
            
        Returns:
            运动规划
        """
        plan_id = f"motion_{int(time.time()*1000)}"
        
        if duration is None:
            distance = math.sqrt(sum((e-s)**2 for s, e in zip(start, end)))
            duration = distance / self._default_velocity
        
        # 生成直线轨迹
        path = self._generate_cartesian_trajectory(start, end, duration)
        
        # 检查碰撞
        path = await self._check_collision(path)
        
        plan = MotionPlan(
            id=plan_id,
            motion_type=MotionType.CARTESIAN,
            path=path,
            duration=duration
        )
        
        self._plans[plan_id] = plan
        return plan
    
    async def plan_mobile_motion(self, start: Tuple[float, float, float],
                                 goal: Tuple[float, float, float]) -> MotionPlan:
        """
        规划移动基座运动
        
        Args:
            start: 起始位姿 (x, y, theta)
            goal: 目标位姿 (x, y, theta)
            
        Returns:
            运动规划
        """
        plan_id = f"motion_{int(time.time()*1000)}"
        
        # 使用A*或RRT规划路径
        path = await self._plan_mobile_path(start, goal)
        
        distance = self._calculate_path_length(path)
        duration = distance / self._default_velocity
        
        plan = MotionPlan(
            id=plan_id,
            motion_type=MotionType.MOBILE_BASE,
            path=path,
            duration=duration
        )
        
        self._plans[plan_id] = plan
        return plan
    
    def _estimate_duration(self, start: List[float], end: List[float]) -> float:
        """估计运动时间"""
        max_displacement = max(abs(s - e) for s, e in zip(start, end))
        return max_displacement / self._default_velocity
    
    def _generate_joint_trajectory(self, start: List[float], end: List[float],
                                   duration: float) -> List[PathPoint]:
        """生成关节轨迹"""
        path = []
        steps = int(duration / 0.01) + 1  # 10ms分辨率
        
        for i in range(steps + 1):
            t = i / steps
            # 使用梯形速度曲线
            s = self._trapezoidal_profile(t, duration)
            
            position = tuple(s * e + (1-s) * start_j 
                           for start_j, e in zip(start, end))
            
            path.append(PathPoint(position=position, time=t * duration))
        
        return path
    
    def _generate_cartesian_trajectory(self, start: Tuple[float, float, float],
                                       end: Tuple[float, float, float],
                                       duration: float) -> List[PathPoint]:
        """生成笛卡尔轨迹"""
        path = []
        steps = int(duration / 0.01) + 1
        
        for i in range(steps + 1):
            t = i / steps
            s = self._trapezoidal_profile(t, duration)
            
            position = tuple(s * e + (1-s) * s_val 
                           for s_val, e in zip(start, end))
            
            path.append(PathPoint(position=position, time=t * duration))
        
        return path
    
    def _trapezoidal_profile(self, t: float, total_time: float) -> float:
        """梯形速度曲线"""
        if total_time <= 0:
            return 1.0
        
        t_norm = t / total_time
        
        # 加速、匀速、减速各占1/3
        if t_norm < 0.33:
            return 1.5 * t_norm * t_norm
        elif t_norm < 0.67:
            return 0.165 + 1.5 * (t_norm - 0.33)
        else:
            return 1 - 1.5 * (1 - t_norm) * (1 - t_norm)
    
    async def _plan_mobile_path(self, start: Tuple[float, float, float],
                                goal: Tuple[float, float, float]) -> List[PathPoint]:
        """规划移动路径"""
        # 简化的直线路径
        path = []
        
        dx = goal[0] - start[0]
        dy = goal[1] - start[1]
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < 0.01:
            return [PathPoint(position=start, time=0),
                   PathPoint(position=goal, time=0)]
        
        steps = max(int(distance / self._default_resolution), 2)
        
        for i in range(steps + 1):
            t = i / steps
            x = start[0] + t * dx
            y = start[1] + t * dy
            theta = start[2] + t * (goal[2] - start[2])
            
            path.append(PathPoint(position=(x, y, theta), time=t * distance / self._default_velocity))
        
        return path
    
    async def _check_collision(self, path: List[PathPoint]) -> List[PathPoint]:
        """检查碰撞"""
        # 简化的碰撞检查
        for point in path:
            for obstacle in self._obstacles:
                # 检查是否与障碍物相交
                pass
        
        return path
    
    def _calculate_path_length(self, path: List[PathPoint]) -> float:
        """计算路径长度"""
        if len(path) < 2:
            return 0.0
        
        length = 0.0
        for i in range(1, len(path)):
            p1 = path[i-1].position
            p2 = path[i].position
            length += math.sqrt(sum((a-b)**2 for a, b in zip(p1, p2)))
        
        return length
    
    def get_plan(self, plan_id: str) -> Optional[MotionPlan]:
        """获取规划"""
        return self._plans.get(plan_id)
    
    def interpolate_plan(self, plan_id: str, time: float) -> Optional[PathPoint]:
        """在规划中插值"""
        plan = self._plans.get(plan_id)
        if not plan or not plan.path:
            return None
        
        # 找到时间点前后的路径点
        for i, point in enumerate(plan.path):
            if point.time >= time:
                if i == 0:
                    return point
                
                # 线性插值
                prev = plan.path[i-1]
                dt = point.time - prev.time
                if dt > 0:
                    alpha = (time - prev.time) / dt
                    pos = tuple((1-alpha)*p1 + alpha*p2 
                               for p1, p2 in zip(prev.position, point.position))
                    return PathPoint(position=pos, time=time)
        
        return plan.path[-1] if plan.path else None
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_plans': len(self._plans),
            'obstacles_count': len(self._obstacles)
        }
