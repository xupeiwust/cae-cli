# -*- coding: utf-8 -*-
"""
AI 模型安装器（占位）
"""
from pathlib import Path


class ModelInstaller:
    """AI 模型安装器"""

    KNOWN_MODELS = {}

    def is_installed(self, model_name: str) -> bool:
        """检查模型是否已安装"""
        return False

    def activate(self, model_name: str) -> None:
        """激活模型"""
        pass

    def install(self, model_name: str, progress_callback=None):
        """安装模型"""
        pass
