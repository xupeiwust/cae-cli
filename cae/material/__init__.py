"""
Material 材料模块

提供材料属性定义，包括弹性、塑性、超弹性等。

类层次：
  Elastic       # 弹性材料
  Plastic       # 塑性材料
  CyclicHardening  # 循环硬化

参考 pygccx model_keywords/elastic.py, plastic.py 设计
"""
from __future__ import annotations

from cae.material.elastic import Elastic
from cae.material.plastic import Plastic, CyclicHardening

__all__ = [
    "Elastic",
    "Plastic",
    "CyclicHardening",
]
