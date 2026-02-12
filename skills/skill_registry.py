# -*- coding: utf-8 -*-
"""
Skill Registry - 技能注册表
管理所有可用技能的注册、发现和实例化
"""

import time
from typing import Dict, List, Optional, Any, Type, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import importlib


@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    description: str
    version: str
    author: str = ""
    tags: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    resource_requirements: Dict = field(default_factory=dict)
    parameter_schema: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'author': self.author,
            'tags': self.tags,
            'dependencies': self.dependencies,
            'resource_requirements': self.resource_requirements,
            'parameter_schema': self.parameter_schema
        }


@dataclass
class SkillEntry:
    """技能注册条目"""
    skill_class: Type
    metadata: SkillMetadata
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    is_singleton: bool = False
    created_at: float = field(default_factory=time.time)
    last_used: float = 0.0
    use_count: int = 0


class SkillRegistry:
    """
    技能注册表
    
    管理所有可用技能的注册、发现和实例化
    
    Features:
        - 技能注册与注销
        - 技能发现与查询
        - 技能实例化
        - 技能依赖管理
        - 技能生命周期管理
        - 动态技能加载
    """
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化技能注册表"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self._skills: Dict[str, SkillEntry] = {}
        self._skill_aliases: Dict[str, str] = {}
        self._categories: Dict[str, List[str]] = {}
        
        # 回调
        self._on_register_callbacks: List[Callable] = []
        self._on_unregister_callbacks: List[Callable] = []
        
        # 统计
        self._stats = {
            'total_registered': 0,
            'total_created': 0,
            'total_errors': 0
        }
        
        self._initialized = True
        
        # 注册内置技能
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        """注册内置技能"""
        # VLN技能
        try:
            from .vln_skill import VLNSkill
            self.register_skill(
                VLNSkill,
                metadata=SkillMetadata(
                    name='vln',
                    description='Vision-Language Navigation skill',
                    version='1.0.0',
                    tags=['navigation', 'vision', 'language'],
                    resource_requirements={
                        'sensors': ['camera', 'lidar'],
                        'actuators': ['base']
                    }
                )
            )
        except ImportError:
            pass
        
        # VLA技能
        try:
            from .vla_skill import VLASkill
            self.register_skill(
                VLASkill,
                metadata=SkillMetadata(
                    name='vla',
                    description='Vision-Language Action skill',
                    version='1.0.0',
                    tags=['manipulation', 'vision', 'language'],
                    resource_requirements={
                        'sensors': ['camera'],
                        'actuators': ['arm', 'hand']
                    }
                )
            )
        except ImportError:
            pass
    
    def register_skill(self, skill_class: Type, metadata: Optional[SkillMetadata] = None,
                      factory: Optional[Callable] = None, is_singleton: bool = False,
                      aliases: Optional[List[str]] = None) -> bool:
        """
        注册技能
        
        Args:
            skill_class: 技能类
            metadata: 技能元数据（可选）
            factory: 工厂函数（可选）
            is_singleton: 是否单例
            aliases: 别名列表
            
        Returns:
            是否注册成功
        """
        with self._lock:
            try:
                # 提取技能名称
                skill_name = metadata.name if metadata else getattr(skill_class, 'name', skill_class.__name__)
                
                # 创建元数据
                if metadata is None:
                    metadata = SkillMetadata(
                        name=skill_name,
                        description=getattr(skill_class, 'description', ''),
                        version=getattr(skill_class, 'version', '1.0.0'),
                        resource_requirements=getattr(skill_class, 'get_required_resources', lambda: {})()
                    )
                
                # 创建条目
                entry = SkillEntry(
                    skill_class=skill_class,
                    metadata=metadata,
                    factory=factory,
                    is_singleton=is_singleton
                )
                
                self._skills[skill_name] = entry
                self._stats['total_registered'] += 1
                
                # 注册别名
                if aliases:
                    for alias in aliases:
                        self._skill_aliases[alias] = skill_name
                
                # 更新分类
                for tag in metadata.tags:
                    if tag not in self._categories:
                        self._categories[tag] = []
                    self._categories[tag].append(skill_name)
                
                # 触发回调
                self._trigger_register_callbacks(skill_name, metadata)
                
                print(f"[SkillRegistry] Registered skill: {skill_name}")
                return True
                
            except Exception as e:
                print(f"[SkillRegistry] Failed to register skill: {e}")
                self._stats['total_errors'] += 1
                return False
    
    def unregister_skill(self, name: str) -> bool:
        """
        注销技能
        
        Args:
            name: 技能名称
            
        Returns:
            是否注销成功
        """
        with self._lock:
            if name not in self._skills:
                return False
            
            entry = self._skills.pop(name)
            
            # 移除别名
            aliases_to_remove = [k for k, v in self._skill_aliases.items() if v == name]
            for alias in aliases_to_remove:
                self._skill_aliases.pop(alias)
            
            # 更新分类
            for tag in entry.metadata.tags:
                if tag in self._categories:
                    self._categories[tag] = [s for s in self._categories[tag] if s != name]
            
            # 触发回调
            self._trigger_unregister_callbacks(name, entry.metadata)
            
            print(f"[SkillRegistry] Unregistered skill: {name}")
            return True
    
    def get_skill(self, name: str, **kwargs) -> Optional[Any]:
        """
        获取技能实例
        
        Args:
            name: 技能名称
            **kwargs: 传递给技能构造函数的参数
            
        Returns:
            技能实例或None
        """
        with self._lock:
            # 检查别名
            actual_name = self._skill_aliases.get(name, name)
            
            if actual_name not in self._skills:
                return None
            
            entry = self._skills[actual_name]
            
            # 更新统计
            entry.last_used = time.time()
            entry.use_count += 1
            
            # 单例模式
            if entry.is_singleton:
                if entry.instance is None:
                    entry.instance = self._create_instance(entry, **kwargs)
                    self._stats['total_created'] += 1
                return entry.instance
            
            # 创建新实例
            instance = self._create_instance(entry, **kwargs)
            self._stats['total_created'] += 1
            return instance
    
    def _create_instance(self, entry: SkillEntry, **kwargs) -> Any:
        """创建技能实例"""
        if entry.factory:
            return entry.factory(**kwargs)
        else:
            return entry.skill_class(**kwargs)
    
    def has_skill(self, name: str) -> bool:
        """检查技能是否存在"""
        actual_name = self._skill_aliases.get(name, name)
        return actual_name in self._skills
    
    def get_skill_metadata(self, name: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        actual_name = self._skill_aliases.get(name, name)
        entry = self._skills.get(actual_name)
        return entry.metadata if entry else None
    
    def list_skills(self) -> List[str]:
        """列出所有技能名称"""
        return list(self._skills.keys())
    
    def list_skills_by_tag(self, tag: str) -> List[str]:
        """按标签列出技能"""
        return self._categories.get(tag, [])
    
    def get_all_metadata(self) -> Dict[str, Dict]:
        """获取所有技能元数据"""
        return {
            name: entry.metadata.to_dict()
            for name, entry in self._skills.items()
        }
    
    def search_skills(self, query: str) -> List[str]:
        """
        搜索技能
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的技能名称列表
        """
        query_lower = query.lower()
        matches = []
        
        for name, entry in self._skills.items():
            # 搜索名称
            if query_lower in name.lower():
                matches.append(name)
                continue
            
            # 搜索描述
            if query_lower in entry.metadata.description.lower():
                matches.append(name)
                continue
            
            # 搜索标签
            for tag in entry.metadata.tags:
                if query_lower in tag.lower():
                    matches.append(name)
                    break
        
        return matches
    
    def get_skills_requiring_resource(self, resource: str) -> List[str]:
        """获取需要特定资源的技能"""
        matches = []
        
        for name, entry in self._skills.items():
            resources = entry.metadata.resource_requirements
            
            # 检查传感器
            if resource in resources.get('sensors', []):
                matches.append(name)
                continue
            
            # 检查执行器
            if resource in resources.get('actuators', []):
                matches.append(name)
        
        return matches
    
    def add_on_register_callback(self, callback: Callable):
        """添加注册回调"""
        self._on_register_callbacks.append(callback)
    
    def add_on_unregister_callback(self, callback: Callable):
        """添加注销回调"""
        self._on_unregister_callbacks.append(callback)
    
    def _trigger_register_callbacks(self, name: str, metadata: SkillMetadata):
        """触发注册回调"""
        for callback in self._on_register_callbacks:
            try:
                callback(name, metadata)
            except Exception as e:
                print(f"[SkillRegistry] Register callback error: {e}")
    
    def _trigger_unregister_callbacks(self, name: str, metadata: SkillMetadata):
        """触发注销回调"""
        for callback in self._on_unregister_callbacks:
            try:
                callback(name, metadata)
            except Exception as e:
                print(f"[SkillRegistry] Unregister callback error: {e}")
    
    def load_skill_from_module(self, module_path: str, skill_class_name: str,
                               metadata: Optional[SkillMetadata] = None) -> bool:
        """
        从模块加载技能
        
        Args:
            module_path: 模块路径
            skill_class_name: 技能类名
            metadata: 元数据（可选）
            
        Returns:
            是否加载成功
        """
        try:
            module = importlib.import_module(module_path)
            skill_class = getattr(module, skill_class_name)
            
            return self.register_skill(skill_class, metadata)
            
        except Exception as e:
            print(f"[SkillRegistry] Failed to load skill from module: {e}")
            self._stats['total_errors'] += 1
            return False
    
    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            'total_registered': len(self._skills),
            'total_aliases': len(self._skill_aliases),
            'total_categories': len(self._categories),
            'total_created': self._stats['total_created'],
            'total_errors': self._stats['total_errors']
        }
    
    def get_skill_usage_stats(self, name: str) -> Optional[Dict]:
        """获取技能使用统计"""
        actual_name = self._skill_aliases.get(name, name)
        entry = self._skills.get(actual_name)
        
        if entry is None:
            return None
        
        return {
            'name': name,
            'use_count': entry.use_count,
            'last_used': entry.last_used,
            'created_at': entry.created_at
        }
    
    def clear(self):
        """清空注册表"""
        with self._lock:
            self._skills.clear()
            self._skill_aliases.clear()
            self._categories.clear()
            print("[SkillRegistry] Registry cleared")
    
    def export_registry(self) -> Dict:
        """导出注册表"""
        return {
            'skills': self.get_all_metadata(),
            'aliases': self._skill_aliases.copy(),
            'categories': {k: v.copy() for k, v in self._categories.items()},
            'statistics': self.get_statistics()
        }
    
    def import_registry(self, data: Dict, skill_classes: Optional[Dict[str, Type]] = None):
        """
        导入注册表
        
        Args:
            data: 注册表数据
            skill_classes: 技能类映射
        """
        # 这里需要技能类的实际引用才能完成导入
        pass


# 全局注册表实例
registry = SkillRegistry()


def get_registry() -> SkillRegistry:
    """获取全局注册表实例"""
    return registry
