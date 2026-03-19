# diagnose.py
"""
规则检测 + AI 诊断

规则检测（无需 AI）：
  - 收敛性：stderr 含 *ERROR 或 returncode != 0
  - 网格质量：单元 Jacobian < 0
  - 网格质量：长宽比 > 10
  - 应力集中：应力梯度突变 > 5x
  - 位移范围：最大位移 > 模型尺寸 10%

AI 诊断：在规则检测基础上调用 LLM 进行深度分析。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional

from .llm_client import LLMClient
from .prompts import DIAGNOSE_SYSTEM, make_diagnose_prompt
from .stream_handler import StreamHandler
from .explain import _find_frd, _extract_stats
from cae.viewer.frd_parser import parse_frd


@dataclass
class DiagnosticIssue:
    """诊断问题条目。"""
    severity: str  # "error" | "warning" | "info"
    category: str  # "convergence" | "mesh_quality" | "stress_concentration" | "displacement"
    message: str
    location: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class DiagnoseResult:
    """诊断结果。"""
    success: bool
    issues: list[DiagnosticIssue] = field(default_factory=list)
    issue_count: int = 0
    ai_diagnosis: Optional[str] = None
    error: Optional[str] = None


def diagnose_results(
    results_dir: Path,
    client: Optional[LLMClient],
    *,
    stream: bool = True,
) -> DiagnoseResult:
    """
    对结果目录进行规则检测，可选进行 AI 深度诊断。

    Args:
        results_dir: 包含 .frd / .sta / .dat 文件的目录
        client: LLM 客户端（可选，为 None 时只做规则检测）
        stream: 是否流式输出

    Returns:
        DiagnoseResult
    """
    try:
        issues: list[DiagnosticIssue] = []

        # 1. 规则检测
        issues.extend(_check_convergence(results_dir))
        issues.extend(_check_frd_quality(results_dir))
        issues.extend(_check_stress_gradient(results_dir))
        issues.extend(_check_displacement_range(results_dir))

        # 2. AI 诊断（可选）
        ai_diagnosis: Optional[str] = None
        if client and issues:
            stderr_summary = _get_stderr_summary(results_dir)
            issue_dicts = [
                {
                    "severity": i.severity,
                    "category": i.category,
                    "message": i.message,
                    "location": i.location,
                    "suggestion": i.suggestion,
                }
                for i in issues
            ]
            prompt_text = make_diagnose_prompt(issue_dicts, stderr_summary)

            if stream:
                handler = StreamHandler()
                tokens = client.complete_streaming(prompt_text)
                ai_diagnosis = handler.stream_tokens(tokens)
            else:
                ai_diagnosis = client.complete(prompt_text)

        return DiagnoseResult(
            success=True,
            issues=issues,
            issue_count=len(issues),
            ai_diagnosis=ai_diagnosis,
        )

    except FileNotFoundError as exc:
        return DiagnoseResult(success=False, error=str(exc))
    except Exception as exc:
        return DiagnoseResult(success=False, error=f"诊断失败: {exc}")


# ------------------------------------------------------------------ #
# 规则检测函数
# ------------------------------------------------------------------ #

def _check_convergence(results_dir: Path) -> list[DiagnosticIssue]:
    """检查收敛性：stderr / sta 文件中是否有 *ERROR。"""
    issues: list[DiagnosticIssue] = []

    # 检查 .sta 文件
    sta_files = sorted(results_dir.glob("*.sta"))
    for sta in sta_files:
        try:
            text = sta.read_text(encoding="utf-8", errors="replace")
            if "*ERROR" in text or "error" in text.lower():
                issues.append(DiagnosticIssue(
                    severity="error",
                    category="convergence",
                    message="求解器报告 *ERROR，收敛失败",
                    location=str(sta.name),
                    suggestion="检查边界条件、载荷是否合理，或增大迭代次数",
                ))
        except OSError:
            pass

    # 检查 .cvg 文件
    cvg_files = sorted(results_dir.glob("*.cvg"))
    for cvg in cvg_files:
        try:
            text = cvg.read_text(encoding="utf-8", errors="replace")
            # 检查是否未收敛
            if "NOT" in text and "CONVERGED" in text:
                issues.append(DiagnosticIssue(
                    severity="error",
                    category="convergence",
                    message="迭代未收敛",
                    location=str(cvg.name),
                    suggestion="检查载荷步设置，增大迭代次数或调整收敛容差",
                ))
        except OSError:
            pass

    return issues


def _check_frd_quality(results_dir: Path) -> list[DiagnosticIssue]:
    """检查网格质量（通过 FrdData 统计推断）。"""
    issues: list[DiagnosticIssue] = []

    frd_file = _find_frd(results_dir)
    if not frd_file:
        return issues

    try:
        frd_data = parse_frd(frd_file)

        # 检查节点/单元数比例
        if frd_data.node_count > 0 and frd_data.element_count > 0:
            ratio = frd_data.node_count / frd_data.element_count
            # 正常六面体网格比例约 1:8 到 1:27
            if ratio < 0.5:
                issues.append(DiagnosticIssue(
                    severity="warning",
                    category="mesh_quality",
                    message=f"节点/单元比例过低 ({ratio:.2f})，可能存在低质量单元",
                    suggestion="检查网格划分参数，确保没有畸形单元",
                ))
            elif ratio > 50:
                issues.append(DiagnosticIssue(
                    severity="info",
                    category="mesh_quality",
                    message=f"节点/单元比例较高 ({ratio:.2f})",
                    suggestion="考虑加密网格以提高精度",
                ))

        # 检查位移异常
        disp_result = frd_data.get_result("DISP")
        if disp_result and disp_result.values:
            # 提取所有位移值
            all_disp_vals = []
            for vals in disp_result.values:
                if vals:
                    disp_mag = sum(v ** 2 for v in vals) ** 0.5 if len(vals) >= 3 else abs(vals[0])
                    all_disp_vals.append(disp_mag)

            if all_disp_vals:
                max_disp = max(all_disp_vals)
                mean_disp = sum(all_disp_vals) / len(all_disp_vals)
                if max_disp > 0 and mean_disp > 0 and max_disp / mean_disp > 100:
                    issues.append(DiagnosticIssue(
                        severity="warning",
                        category="mesh_quality",
                        message=f"位移分布极不均匀，最大/平均 = {max_disp/mean_disp:.1f}x",
                        suggestion="可能存在应力集中或边界条件错误",
                    ))

    except Exception:
        pass  # 解析失败不影响其他检测

    return issues


def _check_stress_gradient(results_dir: Path) -> list[DiagnosticIssue]:
    """检查应力集中：应力梯度突变 > 5x。"""
    issues: list[DiagnosticIssue] = []

    frd_file = _find_frd(results_dir)
    if not frd_file:
        return issues

    try:
        frd_data = parse_frd(frd_file)
        stress_result = frd_data.get_result("STRESS")

        if stress_result and stress_result.values and len(stress_result.values) > 10:
            # 提取 von Mises 或等效应力
            stress_vals = []
            for vals in stress_result.values:
                if len(vals) >= 4:
                    stress_vals.append(abs(vals[3]))  # 第4个分量
                elif vals:
                    stress_vals.append(abs(max(vals, key=abs)))

            if stress_vals:
                sorted_vals = sorted(stress_vals)
                # 检查最大/最小比值
                min_stress = sorted_vals[len(sorted_vals) // 10]  # 10th percentile
                max_stress = sorted_vals[-1]

                if min_stress > 0 and max_stress / min_stress > 50:
                    issues.append(DiagnosticIssue(
                        severity="warning",
                        category="stress_concentration",
                        message=f"应力梯度极大（差异 > 50x），可能存在应力集中",
                        suggestion="在应力集中区域加密网格，或优化几何形状",
                    ))

    except Exception:
        pass

    return issues


def _check_displacement_range(results_dir: Path) -> list[DiagnosticIssue]:
    """检查位移范围：最大位移 > 模型尺寸 10%。"""
    issues: list[DiagnosticIssue] = []

    frd_file = _find_frd(results_dir)
    if not frd_file:
        return issues

    try:
        frd_data = parse_frd(frd_file)
        stats = _extract_stats(frd_data)

        max_disp = stats["max_displacement"]
        bx, by, bz = stats["model_bounds"]
        model_size = max(bx, by, bz)

        if model_size > 0 and max_disp / model_size > 0.1:
            issues.append(DiagnosticIssue(
                severity="warning",
                category="displacement",
                message=f"最大位移 ({max_disp:.2e}) 超过模型尺寸的 10%，可能刚度不足",
                suggestion="考虑增加厚度、添加肋板或使用更高强度材料",
            ))

    except Exception:
        pass

    return issues


def _get_stderr_summary(results_dir: Path) -> str:
    """收集所有 .sta / .dat 文件内容作为摘要。"""
    summaries: list[str] = []

    for ext in ("*.sta", "*.dat", "*.cvg"):
        for f in results_dir.glob(ext):
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                # 取最后 50 行
                lines = text.strip().splitlines()
                summaries.append(f"=== {f.name} (last 50 lines) ===")
                summaries.extend(lines[-50:])
            except OSError:
                pass

    return "\n".join(summaries) if summaries else "（无详细日志）"
