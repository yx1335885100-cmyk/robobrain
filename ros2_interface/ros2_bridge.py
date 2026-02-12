# -*- coding: utf-8 -*-
"""
ROS2 Bridge - ROS2桥接器
提供与ROS2系统的通信接口，支持话题发布/订阅、服务调用、动作执行
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import json


class MessageType(Enum):
    """消息类型枚举"""
    TOPIC = "topic"
    SERVICE = "service"
    ACTION = "action"
    PARAM = "parameter"


@dataclass
class TopicConfig:
    """话题配置"""
    name: str
    msg_type: str
    direction: str  # 'publish' or 'subscribe'
    qos_profile: int = 10


@dataclass
class ServiceConfig:
    """服务配置"""
    name: str
    srv_type: str
    direction: str  # 'client' or 'server'


@dataclass
class ActionConfig:
    """动作配置"""
    name: str
    action_type: str
    direction: str  # 'client' or 'server'


class ROS2Bridge:
    """
    ROS2桥接器
    
    提供与ROS2系统的统一通信接口
    
    Features:
        - 话题发布和订阅
        - 服务客户端和服务端
        - 动作客户端和服务端
        - 参数管理
        - 消息转换
        - 异步操作支持
    """
    
    def __init__(self, node_name: str = 'robot_brain'):
        """
        初始化ROS2桥接器
        
        Args:
            node_name: ROS2节点名称
        """
        self.node_name = node_name
        
        # ROS2相关
        self._node = None
        self._rclpy_initialized = False
        
        # 发布者和订阅者
        self._publishers: Dict[str, Any] = {}
        self._subscribers: Dict[str, Any] = {}
        self._topic_configs: Dict[str, TopicConfig] = {}
        
        # 服务
        self._service_clients: Dict[str, Any] = {}
        self._service_servers: Dict[str, Any] = {}
        self._service_configs: Dict[str, ServiceConfig] = {}
        
        # 动作
        self._action_clients: Dict[str, Any] = {}
        self._action_servers: Dict[str, Any] = {}
        self._action_configs: Dict[str, ActionConfig] = {}
        
        # 回调存储
        self._subscription_callbacks: Dict[str, Callable] = {}
        self._service_callbacks: Dict[str, Callable] = {}
        self._action_feedback_callbacks: Dict[str, Callable] = {}
        self._action_result_callbacks: Dict[str, Callable] = {}
        
        # 消息缓存
        self._message_cache: Dict[str, List] = {}
        self._cache_size = 100
        
        # 线程控制
        self._running = False
        self._spin_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # 统计信息
        self._stats = {
            'messages_published': 0,
            'messages_received': 0,
            'services_called': 0,
            'actions_executed': 0
        }
        
        # 模拟模式
        self._simulation_mode = False
    
    def initialize(self) -> bool:
        """
        初始化ROS2
        
        Returns:
            是否初始化成功
        """
        try:
            import rclpy
            from rclpy.node import Node
            
            if not rclpy.ok():
                rclpy.init()
                self._rclpy_initialized = True
            
            self._node = Node(self.node_name)
            print(f"[ROS2Bridge] ROS2 initialized with node: {self.node_name}")
            
            return True
            
        except ImportError:
            print("[ROS2Bridge] ROS2 not available, running in simulation mode")
            self._simulation_mode = True
            return False
        except Exception as e:
            print(f"[ROS2Bridge] Initialization failed: {e}")
            self._simulation_mode = True
            return False
    
    def shutdown(self):
        """关闭ROS2"""
        self._running = False
        
        if self._spin_thread:
            self._spin_thread.join(timeout=2.0)
        
        if self._node:
            self._node.destroy_node()
        
        if self._rclpy_initialized:
            try:
                import rclpy
                rclpy.shutdown()
            except:
                pass
        
        print("[ROS2Bridge] Shutdown complete")
    
    def start_spinning(self):
        """启动ROS2 spin线程"""
        self._running = True
        
        if self._simulation_mode:
            print("[ROS2Bridge] Running in simulation mode, no spinning needed")
            return
        
        self._spin_thread = threading.Thread(target=self._spin_loop, daemon=True)
        self._spin_thread.start()
        print("[ROS2Bridge] Started spinning")
    
    def _spin_loop(self):
        """ROS2 spin循环"""
        import rclpy
        while self._running:
            rclpy.spin_once(self._node, timeout_sec=0.1)
    
    # ==================== 话题相关 ====================
    
    def create_publisher(self, topic_name: str, msg_type: str, qos: int = 10) -> bool:
        """
        创建发布者
        
        Args:
            topic_name: 话题名称
            msg_type: 消息类型字符串
            qos: QoS配置
            
        Returns:
            是否创建成功
        """
        config = TopicConfig(
            name=topic_name,
            msg_type=msg_type,
            direction='publish',
            qos_profile=qos
        )
        
        if self._simulation_mode:
            self._topic_configs[topic_name] = config
            self._publishers[topic_name] = None
            return True
        
        try:
            msg_class = self._import_message_type(msg_type)
            publisher = self._node.create_publisher(msg_class, topic_name, qos)
            
            self._publishers[topic_name] = publisher
            self._topic_configs[topic_name] = config
            
            print(f"[ROS2Bridge] Created publisher for topic: {topic_name}")
            return True
            
        except Exception as e:
            print(f"[ROS2Bridge] Failed to create publisher: {e}")
            return False
    
    def create_subscription(self, topic_name: str, msg_type: str, 
                           callback: Callable, qos: int = 10) -> bool:
        """
        创建订阅者
        
        Args:
            topic_name: 话题名称
            msg_type: 消息类型字符串
            callback: 回调函数
            qos: QoS配置
            
        Returns:
            是否创建成功
        """
        config = TopicConfig(
            name=topic_name,
            msg_type=msg_type,
            direction='subscribe',
            qos_profile=qos
        )
        
        self._subscription_callbacks[topic_name] = callback
        
        if self._simulation_mode:
            self._topic_configs[topic_name] = config
            self._subscribers[topic_name] = None
            return True
        
        try:
            msg_class = self._import_message_type(msg_type)
            
            def wrapped_callback(msg):
                self._stats['messages_received'] += 1
                self._cache_message(topic_name, msg)
                callback(msg)
            
            subscription = self._node.create_subscription(
                msg_class, topic_name, wrapped_callback, qos
            )
            
            self._subscribers[topic_name] = subscription
            self._topic_configs[topic_name] = config
            
            print(f"[ROS2Bridge] Created subscription for topic: {topic_name}")
            return True
            
        except Exception as e:
            print(f"[ROS2Bridge] Failed to create subscription: {e}")
            return False
    
    def publish(self, topic_name: str, message: Dict) -> bool:
        """
        发布消息
        
        Args:
            topic_name: 话题名称
            message: 消息字典
            
        Returns:
            是否发布成功
        """
        if self._simulation_mode:
            self._stats['messages_published'] += 1
            return True
        
        if topic_name not in self._publishers:
            print(f"[ROS2Bridge] Publisher not found: {topic_name}")
            return False
        
        try:
            publisher = self._publishers[topic_name]
            config = self._topic_configs[topic_name]
            msg_class = self._import_message_type(config.msg_type)
            
            msg = self._dict_to_msg(message, msg_class)
            publisher.publish(msg)
            
            self._stats['messages_published'] += 1
            return True
            
        except Exception as e:
            print(f"[ROS2Bridge] Failed to publish: {e}")
            return False
    
    # ==================== 服务相关 ====================
    
    def create_service_client(self, service_name: str, srv_type: str) -> bool:
        """
        创建服务客户端
        
        Args:
            service_name: 服务名称
            srv_type: 服务类型字符串
            
        Returns:
            是否创建成功
        """
        config = ServiceConfig(
            name=service_name,
            srv_type=srv_type,
            direction='client'
        )
        
        if self._simulation_mode:
            self._service_configs[service_name] = config
            self._service_clients[service_name] = None
            return True
        
        try:
            srv_class = self._import_message_type(srv_type)
            client = self._node.create_client(srv_class, service_name)
            
            self._service_clients[service_name] = client
            self._service_configs[service_name] = config
            
            print(f"[ROS2Bridge] Created service client: {service_name}")
            return True
            
        except Exception as e:
            print(f"[ROS2Bridge] Failed to create service client: {e}")
            return False
    
    async def call_service(self, service_name: str, request: Dict, 
                          timeout: float = 5.0) -> Dict:
        """
        调用服务
        
        Args:
            service_name: 服务名称
            request: 请求字典
            timeout: 超时时间
            
        Returns:
            响应字典
        """
        if self._simulation_mode:
            self._stats['services_called'] += 1
            return {'success': True, 'simulation': True}
        
        if service_name not in self._service_clients:
            return {'success': False, 'error': 'Service client not found'}
        
        try:
            client = self._service_clients[service_name]
            config = self._service_configs[service_name]
            
            # 等待服务可用
            if not client.wait_for_service(timeout_sec=timeout):
                return {'success': False, 'error': 'Service not available'}
            
            # 创建请求
            srv_module = self._import_module(config.srv_type)
            req = self._dict_to_msg(request, srv_module.Request)
            
            # 异步调用
            future = client.call_async(req)
            
            # 等待结果
            rclpy.spin_until_future_complete(self._node, future, timeout_sec=timeout)
            
            if future.done():
                response = future.result()
                self._stats['services_called'] += 1
                return self._msg_to_dict(response)
            else:
                return {'success': False, 'error': 'Service call timeout'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ==================== 动作相关 ====================
    
    def create_action_client(self, action_name: str, action_type: str) -> bool:
        """
        创建动作客户端
        
        Args:
            action_name: 动作名称
            action_type: 动作类型字符串
            
        Returns:
            是否创建成功
        """
        config = ActionConfig(
            name=action_name,
            action_type=action_type,
            direction='client'
        )
        
        if self._simulation_mode:
            self._action_configs[action_name] = config
            self._action_clients[action_name] = None
            return True
        
        try:
            from rclpy.action import ActionClient
            action_class = self._import_message_type(action_type)
            
            client = ActionClient(self._node, action_class, action_name)
            
            self._action_clients[action_name] = client
            self._action_configs[action_name] = config
            
            print(f"[ROS2Bridge] Created action client: {action_name}")
            return True
            
        except Exception as e:
            print(f"[ROS2Bridge] Failed to create action client: {e}")
            return False
    
    async def execute_action(self, action_name: str, goal: Dict,
                            feedback_callback: Callable = None,
                            timeout: float = 30.0) -> Dict:
        """
        执行动作
        
        Args:
            action_name: 动作名称
            goal: 目标字典
            feedback_callback: 反馈回调
            timeout: 超时时间
            
        Returns:
            结果字典
        """
        if self._simulation_mode:
            self._stats['actions_executed'] += 1
            # 模拟动作执行
            await asyncio.sleep(1.0)
            return {'success': True, 'simulation': True}
        
        if action_name not in self._action_clients:
            return {'success': False, 'error': 'Action client not found'}
        
        try:
            from rclpy.action import ActionClient
            
            client = self._action_clients[action_name]
            config = self._action_configs[action_name]
            
            # 等待服务器可用
            if not client.wait_for_server(timeout_sec=timeout):
                return {'success': False, 'error': 'Action server not available'}
            
            # 创建目标
            action_module = self._import_module(config.action_type)
            goal_msg = self._dict_to_msg(goal, action_module.Goal())
            
            # 发送目标
            send_goal_future = client.send_goal_async(
                goal_msg,
                feedback_callback=feedback_callback
            )
            
            # 等待目标接受
            rclpy.spin_until_future_complete(
                self._node, send_goal_future, timeout_sec=timeout
            )
            
            if not send_goal_future.done():
                return {'success': False, 'error': 'Goal send timeout'}
            
            goal_handle = send_goal_future.result()
            
            if not goal_handle.accepted:
                return {'success': False, 'error': 'Goal rejected'}
            
            # 等待结果
            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(
                self._node, result_future, timeout_sec=timeout
            )
            
            if result_future.done():
                result = result_future.result().result
                self._stats['actions_executed'] += 1
                return self._msg_to_dict(result)
            else:
                return {'success': False, 'error': 'Action timeout'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def cancel_action(self, action_name: str) -> bool:
        """取消动作"""
        if self._simulation_mode:
            return True
        
        # TODO: 实现动作取消逻辑
        return False
    
    # ==================== 辅助方法 ====================
    
    def _import_message_type(self, type_str: str):
        """导入消息类型"""
        parts = type_str.split('/')
        if len(parts) == 3:
            package, module, msg_name = parts
        elif len(parts) == 2:
            package, msg_name = parts
            module = 'msg'
        else:
            raise ValueError(f"Invalid message type: {type_str}")
        
        module_path = f"{package}.{module}"
        msg_module = __import__(module_path, fromlist=[msg_name])
        return getattr(msg_module, msg_name)
    
    def _import_module(self, type_str: str):
        """导入模块"""
        parts = type_str.split('/')
        if len(parts) >= 2:
            package = parts[0]
            module = parts[1] if len(parts) > 2 else 'msg'
            module_path = f"{package}.{module}"
            return __import__(module_path, fromlist=['*'])
        return None
    
    def _dict_to_msg(self, data: Dict, msg_class):
        """字典转消息"""
        msg = msg_class()
        
        for key, value in data.items():
            if hasattr(msg, key):
                setattr(msg, key, value)
        
        return msg
    
    def _msg_to_dict(self, msg) -> Dict:
        """消息转字典"""
        result = {}
        
        for field in msg.get_fields_and_field_types():
            value = getattr(msg, field)
            result[field] = value
        
        return result
    
    def _cache_message(self, topic_name: str, msg):
        """缓存消息"""
        if topic_name not in self._message_cache:
            self._message_cache[topic_name] = []
        
        self._message_cache[topic_name].append({
            'timestamp': time.time(),
            'data': self._msg_to_dict(msg)
        })
        
        # 限制缓存大小
        if len(self._message_cache[topic_name]) > self._cache_size:
            self._message_cache[topic_name] = self._message_cache[topic_name][-self._cache_size:]
    
    def get_cached_messages(self, topic_name: str, limit: int = 10) -> List[Dict]:
        """获取缓存消息"""
        if topic_name not in self._message_cache:
            return []
        return self._message_cache[topic_name][-limit:]
    
    # ==================== 参数相关 ====================
    
    def get_parameter(self, name: str, default: Any = None) -> Any:
        """获取参数"""
        if self._simulation_mode or not self._node:
            return default
        
        try:
            param = self._node.get_parameter(name)
            return param.value
        except:
            return default
    
    def set_parameter(self, name: str, value: Any) -> bool:
        """设置参数"""
        if self._simulation_mode or not self._node:
            return False
        
        try:
            from rclpy.parameter import Parameter
            param = Parameter(name, value=value)
            self._node.set_parameters([param])
            return True
        except:
            return False
    
    # ==================== 状态和统计 ====================
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'simulation_mode': self._simulation_mode,
            'messages_published': self._stats['messages_published'],
            'messages_received': self._stats['messages_received'],
            'services_called': self._stats['services_called'],
            'actions_executed': self._stats['actions_executed'],
            'publishers': list(self._publishers.keys()),
            'subscribers': list(self._subscribers.keys()),
            'service_clients': list(self._service_clients.keys()),
            'action_clients': list(self._action_clients.keys())
        }
    
    def get_status(self) -> Dict:
        """获取桥接状态"""
        return {
            'node_name': self.node_name,
            'initialized': self._node is not None or self._simulation_mode,
            'simulation_mode': self._simulation_mode,
            'running': self._running,
            'topics': {
                'publishers': len(self._publishers),
                'subscribers': len(self._subscribers)
            },
            'services': len(self._service_clients),
            'actions': len(self._action_clients)
        }
    
    def simulate_receive_message(self, topic_name: str, message: Dict):
        """模拟接收消息（用于测试）"""
        if topic_name in self._subscription_callbacks:
            callback = self._subscription_callbacks[topic_name]
            callback(message)
            self._stats['messages_received'] += 1
