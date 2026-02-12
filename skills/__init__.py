# -*- coding: utf-8 -*-
"""
Humanoid Robot Brain - Skills Module
技能模块：包含VLN、VLA等Skills基类和注册机制
"""

from .base_skill import BaseSkill, SkillResult, SkillStatus
from .vln_skill import VLNSkill
from .vla_skill import VLASkill
from .skill_registry import SkillRegistry

__all__ = [
    'BaseSkill',
    'SkillResult',
    'SkillStatus',
    'VLNSkill',
    'VLASkill',
    'SkillRegistry'
]
