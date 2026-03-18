# CalculiX 实现
"""
CalculiX 求解器实现
支持 Abaqus 兼容的 .inp 格式，输出 .frd（结果）和 .dat（数据）文件。

二进制查找优先级：
  1. ~/.local/share/cae-cli/solvers/calculix/ccx  （cae install 安装的）
  2. 系统 PATH 中的 ccx / ccx_2.21 等
  3. WSL 中的 ccx（如果可用）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from .base import BaseSolver, SolveResult
from ..config import settings

# CalculiX 输出中标志错误的关键词
_ERROR_MARKERS = ("*ERROR", "Error in ", "error in ", "FATAL", "fatal error")
# 标志警告的关键词
_WARN_MARKERS = ("*WARNING", "Warning", "warning:")

# 系统 PATH 中常见的 CalculiX 可执行文件名
_CCX_NAMES = ["ccx", "ccx_2.21", "ccx_2.20", "ccx_2.19", "ccx_2.18", "CalculiX"]


class CalculixSolver(BaseSolver):
    """
    CalculiX FEA 求解器封装。

    CalculiX 命令行用法：
        ccx -i <job_name>
    其中 <job_name> 是不含 .inp 后缀的文件名。
    求解器在当前工作目录下生成同名的 .frd / .dat / .cvg / .sta 文件。
    """

    name = "calculix"
    description = "CalculiX — 开源 FEA 求解器，兼容 Abaqus .inp 格式"

    # ------------------------------------------------------------------ #
    # 二进制查找
    # ------------------------------------------------------------------ #

    def _find_binary(self) -> Optional[Path]:
        # 1. cae install 安装的捆绑二进制
        for candidate in [
            settings.solvers_dir / "calculix" / "ccx",
            settings.solvers_dir / "calculix" / "ccx.exe",  # Windows
        ]:
            if candidate.is_file():
                return candidate

        # 2. 系统 PATH
        for name in _CCX_NAMES:
            found = shutil.which(name)
            if found:
                return Path(found)

        # 3. WSL 中的 ccx
        wsl_ccx = self._find_wsl_ccx()
        if wsl_ccx:
            return wsl_ccx

        return None

    def _find_wsl_ccx(self) -> Optional[Path]:
        """检测 WSL 中是否安装了 ccx"""
        try:
            result = subprocess.run(
                ["wsl", "-e", "which", "ccx"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                # 返回特殊标记表示使用 WSL
                return Path("WSL:ccx")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def _is_wsl(self, binary: Path) -> bool:
        """检查是否使用 WSL"""
        return str(binary).startswith("WSL:")

    # ------------------------------------------------------------------ #
    # BaseSolver 接口实现
    # ------------------------------------------------------------------ #

    def check_installation(self) -> bool:
        return self._find_binary() is not None

    def get_version(self) -> Optional[str]:
        binary = self._find_binary()
        if not binary:
            return None
        try:
            # ccx 无参数运行时会打印版本到 stderr 然后以非零退出
            proc = subprocess.run(
                [str(binary)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            output = proc.stdout + proc.stderr
            for line in output.splitlines():
                low = line.lower()
                if "calculix" in low and (
                    "version" in low or "." in line
                ):
                    return line.strip()
            return "unknown"
        except (subprocess.TimeoutExpired, OSError):
            return None

    def supported_formats(self) -> list[str]:
        return [".inp"]

    def solve(
        self,
        inp_file: Path,
        output_dir: Path,
        *,
        timeout: int = 3600,
        **kwargs,
    ) -> SolveResult:
        """
        调用 CalculiX 执行静力/热力/动力学仿真。

        CalculiX 要求：
        - 以 output_dir 为 CWD 运行（输出文件落地在此）
        - 需要把 .inp 文件复制/硬链接到 output_dir
        """
        # --- 前置检查 ---
        binary = self._find_binary()
        if not binary:
            return self._error_result(
                output_dir,
                "找不到 CalculiX 可执行文件。\n"
                "请运行 `cae install` 安装，或手动安装后确保 `ccx` 在 PATH 中。",
            )

        ok, msg = self.validate_input(inp_file)
        if not ok:
            return self._error_result(output_dir, msg)

        # --- 准备工作目录 ---
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        job_name = inp_file.stem
        inp_dest = output_dir / inp_file.name

        # 仅当源文件和目标不同时才复制
        if inp_dest.resolve() != inp_file.resolve():
            shutil.copy2(inp_file, inp_dest)

        # --- 运行 CalculiX ---
        start = time.monotonic()
        is_wsl = self._is_wsl(binary)

        try:
            if is_wsl:
                # 使用 WSL 运行
                # 需要将路径转换为 WSL 路径格式
                wsl_input = inp_dest.as_posix().replace("D:", "/mnt/d")
                wsl_output = output_dir.as_posix().replace("D:", "/mnt/d")
                cmd = ["wsl", "-e", "bash", "-c", f"cd {wsl_output} && ccx -i {job_name}"]
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
            else:
                # 直接运行
                cmd = [str(binary), "-i", job_name]
                proc = subprocess.run(
                    cmd,
                    cwd=str(output_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                )
        except subprocess.TimeoutExpired:
            return self._error_result(
                output_dir,
                f"求解超时（超过 {timeout}s）。可用 --timeout 参数调大限制。",
                duration=time.monotonic() - start,
            )
        except OSError as exc:
            return self._error_result(
                output_dir,
                f"无法启动求解器: {exc}",
                duration=time.monotonic() - start,
            )

        duration = time.monotonic() - start

        # --- 解析输出 ---
        combined = proc.stdout + proc.stderr
        errors = self._extract_lines(combined, _ERROR_MARKERS)
        warnings = self._extract_lines(combined, _WARN_MARKERS)

        # 收集输出文件（排除复制进来的 .inp）
        output_files = sorted(
            f for f in output_dir.iterdir()
            if f.is_file() and f.name != inp_file.name
        )

        # 成功判定：returncode=0 且无 *ERROR 且生成了 .frd
        has_frd = any(f.suffix == ".frd" for f in output_files)
        success = proc.returncode == 0 and not errors and has_frd

        error_message: Optional[str] = None
        if errors:
            error_message = "\n".join(errors[:3])  # 最多显示前三条
        elif proc.returncode != 0 and not has_frd:
            error_message = f"求解器退出码: {proc.returncode}，未生成结果文件。"

        return SolveResult(
            success=success,
            output_dir=output_dir,
            output_files=output_files,
            stdout=proc.stdout,
            stderr=proc.stderr,
            returncode=proc.returncode,
            duration_seconds=duration,
            error_message=error_message,
            warnings=warnings[:10],  # 最多保留 10 条警告
        )

    # ------------------------------------------------------------------ #
    # 私有工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_lines(text: str, markers: tuple[str, ...]) -> list[str]:
        """从输出文本中提取包含特定标记的行。"""
        return [
            line.strip()
            for line in text.splitlines()
            if any(m in line for m in markers)
        ]

    @staticmethod
    def _error_result(
        output_dir: Path,
        message: str,
        duration: float = 0.0,
    ) -> SolveResult:
        return SolveResult(
            success=False,
            output_dir=output_dir,
            output_files=[],
            stdout="",
            stderr="",
            returncode=-1,
            duration_seconds=duration,
            error_message=message,
        )
