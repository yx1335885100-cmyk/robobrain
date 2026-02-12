# -*- coding: utf-8 -*-
"""
Config - 配置管理
提供统一的配置管理功能
"""

import os
import json
from typing import Dict, Optional, Any
import threading


class Config:
    """
    配置管理器
    
    提供统一的配置管理功能
    
    Features:
        - 配置加载
        - 配置验证
        - 默认值
        - 环境变量支持
        - 热重载
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config: Dict = {}
        self._defaults = self._get_defaults()
        self._config.update(self._defaults)
        
        self._initialized = True
    
    def _get_defaults(self) -> Dict:
        """获取默认配置"""
        return {
            # 大脑配置
            'brain': {
                'max_concurrent_tasks': 5,
                'planning_strategy': 'hierarchical',
                'scheduling_algorithm': 'priority_based',
                'execution_mode': 'sequential',
                'enable_reflection': True,
                'max_planning_iterations': 10
            },
            
            # ROS2配置
            'ros2': {
                'node_name': 'robot_brain',
                'joint_update_rate': 100
            },
            
            # 感知配置
            'perception': {
                'asr': {
                    'sample_rate': 16000,
                    'language': 'zh-CN'
                },
                'vision': {
                    'width': 640,
                    'height': 480,
                    'fps': 30
                },
                'fusion_rate': 10
            },
            
            # 规划配置
            'planning': {
                'global_planner': {
                    'max_sub_goals': 10
                },
                'local_planner': {
                    'action_resolution': 0.1
                },
                'motion_planner': {
                    'default_velocity': 0.5,
                    'default_acceleration': 0.5,
                    'collision_check': True
                }
            },
            
            # 执行配置
            'execution': {
                'action_timeout': 60.0,
                'max_retries': 3
            },
            
            # 日志配置
            'logging': {
                'level': 'INFO',
                'file': None
            }
        }
    
    def load(self, config_path: str) -> bool:
        """
        从文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            是否加载成功
        """
        try:
            if not os.path.exists(config_path):
                print(f"[Config] Config file not found: {config_path}")
                return False
            
            with open(config_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            
            self._merge_config(loaded)
            print(f"[Config] Loaded configuration from {config_path}")
            return True
            
        except Exception as e:
            print(f"[Config] Failed to load config: {e}")
            return False
    
    def load_from_env(self):
        """从环境变量加载配置"""
        # ROS2节点名
        if 'ROBOT_BRAIN_NODE' in os.environ:
            self._config['ros2']['node_name'] = os.environ['ROBOT_BRAIN_NODE']
        
        # 日志级别
        if 'ROBOT_BRAIN_LOG_LEVEL' in os.environ:
            self._config['logging']['level'] = os.environ['ROBOT_BRAIN_LOG_LEVEL']
        
        # 最大并发任务
        if 'ROBOT_BRAIN_MAX_TASKS' in os.environ:
            self._config['brain']['max_concurrent_tasks'] = \
                int(os.environ['ROBOT_BRAIN_MAX_TASKS'])
    
    def _merge_config(self, new_config: Dict):
        """合并配置"""
        def merge(base: Dict, update: Dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge(base[key], value)
                else:
                    base[key] = value
        
        merge(self._config, new_config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持点号分隔的路径）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_section(self, section: str) -> Dict:
        """获取配置节"""
        return self._config.get(section, {})
    
    def get_all(self) -> Dict:
        """获取所有配置"""
        return self._config.copy()
    
    def save(self, config_path: str) -> bool:
        """
        保存配置到文件
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            是否保存成功
        """
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Config] Failed to save config: {e}")
            return False


def get_config() -> Config:
    """获取配置实例"""
    return Config()
