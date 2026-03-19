# -*- coding: utf-8 -*-
"""
AI 模型安装器

从 GitHub Release 下载并安装 AI 模型（GGUF 格式）
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve
import ssl

# GitHub Release 地址
REPO_OWNER = "yd5768365-hue"
REPO_NAME = "cae-cli"
RELEASE_VERSION = "v1.0.0"


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    size_gb: float
    description: str
    filename: str


# 已知模型列表
KNOWN_MODELS: dict[str, ModelInfo] = {
    "deepseek-r1-distill-qwen-7b-q2_k": ModelInfo(
        name="deepseek-r1-distill-qwen-7b-q2_k",
        size_gb=2.8,
        description="DeepSeek R1 Distill Qwen 7B (Q2_K 量化，约 2.8GB)",
        filename="DeepSeek-R1-Distill-Qwen-7B-Q2_K.gguf",
    ),
    "deepseek-r1-distill-qwen-14b-q2_k": ModelInfo(
        name="deepseek-r1-distill-qwen-14b-q2_k",
        size_gb=5.5,
        description="DeepSeek R1 Distill Qwen 14B (Q2_K 量化，约 5.5GB)",
        filename="DeepSeek-R1-Distill-Qwen-14B-Q2_K.gguf",
    ),
}


@dataclass
class InstallResult:
    """安装结果"""
    success: bool
    method: str = ""
    install_path: Optional[Path] = None
    error_message: Optional[str] = None


class ModelInstaller:
    """AI 模型安装器"""

    def __init__(self):
        self.platform_name = platform.system().lower()
        # 模型安装到 ~/.cae-cli/models/
        self.cae_home = Path.home() / ".cae-cli"
        self.models_dir = self.cae_home / "models"

    def is_installed(self, model_name: str) -> bool:
        """检查模型是否已安装"""
        # 支持模糊匹配
        search_name = model_name.lower().replace("-", "_").replace(".gguf", "")

        for known_name, info in KNOWN_MODELS.items():
            if (search_name in known_name.replace("-", "_") or
                known_name.replace("-", "_") in search_name):
                model_path = self.models_dir / info.filename
                return model_path.exists()

        # 如果不在已知列表中，也检查文件名
        model_path = self.models_dir / model_name
        if not model_path.name.endswith(".gguf"):
            model_path = model_path.with_suffix(".gguf")
        return model_path.exists()

    def get_install_path(self, model_name: str) -> Path:
        """获取模型的安装路径"""
        for known_name, info in KNOWN_MODELS.items():
            if known_name.replace("-", "_") in model_name.lower().replace("-", "_"):
                return self.models_dir / info.filename
        # 默认使用原名
        path = self.models_dir / model_name
        if not path.suffix:
            path = path.with_suffix(".gguf")
        return path

    def activate(self, model_name: str) -> None:
        """激活模型（设置默认模型）"""
        from cae.config import settings
        settings.active_model = model_name

    def list_models(self) -> list[dict]:
        """列出所有已知模型"""
        return [
            {
                "name": info.name,
                "size_gb": info.size_gb,
                "description": info.description,
                "installed": self.is_installed(info.name),
            }
            for info in KNOWN_MODELS.values()
        ]

    def install(
        self,
        model_name: str,
        progress_callback: Optional[callable] = None,
    ) -> InstallResult:
        """
        安装模型

        Args:
            model_name: 模型名称（支持简写，如 deepseek-r1-7b）
            progress_callback: 进度回调函数 (percent: float, message: str)

        Returns:
            InstallResult
        """
        # 查找匹配的模型
        info = None
        search_name = model_name.lower().replace("-", "_").replace(".gguf", "")

        for known_name, model_info in KNOWN_MODELS.items():
            if (search_name in known_name.replace("-", "_") or
                known_name.replace("-", "_") in search_name or
                search_name in known_name):
                info = model_info
                model_name = known_name  # 使用正式名称
                break

        if info is None:
            # 未知模型，尝试直接下载
            info = ModelInfo(
                name=model_name,
                size_gb=0,
                description=f"自定义模型: {model_name}",
                filename=model_name if model_name.endswith(".gguf") else f"{model_name}.gguf",
            )

        model_path = self.models_dir / info.filename

        # 检查是否已安装
        if model_path.exists():
            return InstallResult(success=True, method="already_installed", install_path=model_path)

        # 确保目录存在
        self.models_dir.mkdir(parents=True, exist_ok=True)

        # 构建下载 URL
        download_url = (
            f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/download/"
            f"{RELEASE_VERSION}/{info.filename}"
        )

        try:
            if progress_callback:
                progress_callback(0.1, "正在下载模型...")

            # 下载文件
            self._download_file(download_url, model_path, progress_callback)

            # 验证下载
            if model_path.exists() and model_path.stat().st_size > 1024 * 1024:  # > 1MB
                if progress_callback:
                    progress_callback(1.0, "安装完成")
                return InstallResult(
                    success=True,
                    method="downloaded_from_github",
                    install_path=model_path,
                )
            else:
                if model_path.exists():
                    model_path.unlink()
                return InstallResult(
                    success=False,
                    error_message="下载的文件无效",
                )

        except Exception as e:
            # 清理可能存在的无效文件
            if model_path.exists():
                model_path.unlink()
            return InstallResult(success=False, error_message=str(e))

    def _download_file(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[callable] = None,
    ) -> None:
        """下载文件"""
        # 使用 curl 下载（更可靠，支持进度）
        try:
            # 检查是否有 curl
            result = subprocess.run(
                ["curl", "-L", "-o", str(dest), url, "--progress-bar", "--connect-timeout", "30"],
                capture_output=True,
                text=True,
                timeout=3600,  # 1 小时超时
            )
            if result.returncode != 0:
                raise RuntimeError(f"下载失败: {result.stderr}")
        except FileNotFoundError:
            # 回退到 urllib
            def report_progress(block_num, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = min(block_num * block_size / total_size * 0.9, 0.9)
                    progress_callback(percent, f"下载中... {block_num * block_size // (1024*1024)}MB")

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            urlretrieve(url, str(dest), reporthook=report_progress)

        except subprocess.TimeoutExpired:
            if dest.exists():
                dest.unlink()
            raise RuntimeError("下载超时，请检查网络连接")

    def uninstall(self, model_name: str) -> bool:
        """卸载模型"""
        model_path = self.get_install_path(model_name)
        try:
            if model_path.exists():
                model_path.unlink()
            return True
        except Exception:
            return False
