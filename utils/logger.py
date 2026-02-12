# -*- coding: utf-8 -*-
"""
Logger - 日志工具
提供统一的日志记录功能
"""

import time
import logging
import sys
from typing import Dict, Optional, Any
from datetime import datetime
import json
import threading


class Logger:
    """
    日志记录器
    
    提供统一的日志记录功能
    
    Features:
        - 多级别日志
        - 格式化输出
        - 文件记录
        - 结构化日志
        - 日志过滤
    """
    
    _instances: Dict[str, 'Logger'] = {}
    _lock = threading.Lock()
    
    def __new__(cls, name: str = 'robot_brain'):
        if name not in cls._instances:
            with cls._lock:
                if name not in cls._instances:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instances[name] = instance
        return cls._instances[name]
    
    def __init__(self, name: str = 'robot_brain'):
        if self._initialized:
            return
        
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        self._logger.addHandler(console_handler)
        
        # 日志缓存
        self._log_cache: list = []
        self._cache_size = 1000
        
        self._initialized = True
    
    def set_level(self, level: str):
        """设置日志级别"""
        level_map = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        self._logger.setLevel(level_map.get(level.lower(), logging.INFO))
    
    def debug(self, message: str, **kwargs):
        """记录调试信息"""
        self._log('DEBUG', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """记录信息"""
        self._log('INFO', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告"""
        self._log('WARNING', message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误"""
        self._log('ERROR', message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误"""
        self._log('CRITICAL', message, **kwargs)
    
    def _log(self, level: str, message: str, **kwargs):
        """内部日志方法"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'extra': kwargs
        }
        
        # 添加到缓存
        self._log_cache.append(log_entry)
        if len(self._log_cache) > self._cache_size:
            self._log_cache.pop(0)
        
        # 输出日志
        log_method = getattr(self._logger, level.lower())
        extra_str = f" | {json.dumps(kwargs)}" if kwargs else ""
        log_method(f"{message}{extra_str}")
    
    def get_logs(self, level: str = None, limit: int = 100) -> list:
        """获取日志"""
        logs = self._log_cache[-limit:]
        if level:
            logs = [l for l in logs if l['level'] == level.upper()]
        return logs
    
    def clear_logs(self):
        """清除日志缓存"""
        self._log_cache.clear()


def get_logger(name: str = 'robot_brain') -> Logger:
    """获取日志记录器实例"""
    return Logger(name)
