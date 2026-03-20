"""
Contact 接触模块

提供接触对、绑定、摩擦等接触相关类的实现。

类层次：
  SurfaceInteraction     # 表面相互作用
    ├── SurfaceBehavior  # 表面行为（压力-间隙）
    └── Friction         # 摩擦

  ContactPair           # 接触对
  Tie                   # 绑定接触

参考 pygccx model_keywords/contact_*.py 设计
"""
from __future__ import annotations

from cae.contact.surface_interaction import SurfaceInteraction
from cae.contact.surface_behavior import SurfaceBehavior
from cae.contact.friction import Friction
from cae.contact.contact_pair import ContactPair
from cae.contact.tie import Tie

__all__ = [
    "SurfaceInteraction",
    "SurfaceBehavior",
    "Friction",
    "ContactPair",
    "Tie",
]
