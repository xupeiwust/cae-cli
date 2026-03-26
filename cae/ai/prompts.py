# prompts.py
"""
Prompt 模板库

为 explain / diagnose / suggest 提供结构化 prompt 模板。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PromptTemplate:
    """Prompt 模板，包含系统提示和用户提示格式。"""
    system: str
    user_template: str


# ------------------------------------------------------------------ #
# explain 模板
# ------------------------------------------------------------------ #

EXPLAIN_SYSTEM = """你是一位资深的有限元分析（FEA）工程师，擅长解读 CalculiX 仿真结果。
请基于以下仿真统计数据，用简洁专业的语言总结分析结果。
语言：中文（技术术语可保留英文缩写）。

输出要求：
1. 摘要（3-5句话）：整体性能评价
2. 关键发现（3-5条）：最重要的位移/应力结果
3. 位移摘要：最大值、位置、是否合理
4. 应力摘要：最大值、位置、是否超过材料极限
5. 警告（如有）：需要关注的潜在问题

请客观、专业地分析，不要虚构数据。"""


def make_explain_prompt(
    node_count: int,
    element_count: int,
    max_displacement: float,
    max_displacement_node: int,
    max_stress: float,
    max_stress_element: int,
    stress_component: str,
    material_yield: float,
    model_bounds: tuple[float, float, float],
) -> str:
    """生成解释结果的 prompt。"""
    bx, by, bz = model_bounds
    model_size = max(bx, by, bz)

    return f"""## 仿真结果数据

### 网格信息
- 节点数：{node_count}
- 单元数：{element_count}

### 位移结果
- 最大位移：{max_displacement:.6e}（节点 {max_displacement_node}）
- 模型特征尺寸：{model_size:.6e}
- 最大位移/模型尺寸比：{max_displacement/model_size:.4%}

### 应力结果
- 最大{stress_component}应力：{max_stress:.6e}（单元 {max_stress_element}）
- 材料屈服强度（假设）：{material_yield:.6e}
- 应力/屈服比：{max_stress/material_yield:.4f}

请解读以上数据，给出结构性能评价。"""


# ------------------------------------------------------------------ #
# diagnose 模板
# ------------------------------------------------------------------ #

DIAGNOSE_SYSTEM = """你是一位资深的有限元分析（FEA）工程师，擅长诊断 CalculiX 仿真中的错误和警告。

## CalculiX 核心知识速查

### 单元类型与自由度
- **实体单元（C3D*）**：只有位移自由度 D1-D3
- **壳单元（S*、M3D*）**：5或6个自由度（D1-D3位移 + D4-D6转动），约束时需注意完整约束所有自由度
- **梁单元（B*）**：6个自由度，截面属性通过 *BEAM SECTION 定义
- **弹簧单元（SPRING*）**：可压缩或只拉不压，节点必须属于某个实体单元

### 常见错误模式（来自 CalculiX 源码硬编码）
1. **RHS only consists of 0.0**：载荷向量为零，通常是耦合约束配置错误
   - *COUPLING + *DISTRIBUTING 必须用 *DLOAD，不能用 *CLOAD
   - 或载荷方向与约束自由度冲突
2. **zero pivot / singular matrix**：边界条件不完整导致刚体运动
3. **not converged**：收敛困难，尝试减小初始步长
4. **negative jacobian**：单元畸形或翻转

### 板壳弯曲结果验证
四边形壳单元（S4/S4R）在均布载荷下应有平滑碗状变形，若呈尖刺/波形说明边界条件错误。

### 单位一致性（最常见的错误）
- 材料 E 用 MPa，几何必须用 mm，载荷用 N
- 应力结果 MPa，位移结果 mm
- 检验：E=210000 MPa，1N/mm²=1MPa

### 应力/应变分量顺序（CalculiX 输出）
- 应力：SXX, SYY, SZZ, SXY, SYZ, SZX
- 应变：EXX, EYY, EZZ, EXY, EYZ, EZX
- von Mises 应力在第4个位置

### CalculiX 应变输出规则
- *STEP, NLGEOM：格林/拉格朗日应变（大变形分析）
- 无 NLGEOM：线性（小变形）欧拉应变

## 诊断输出要求

请按以下格式回答：

### 1. 问题定位
- **类别**：收敛/材料/单位/边界/网格/接触/载荷
- **严重程度**：error（必须修复）/ warning（建议修复）/ info（参考）

### 2. 根因分析
- 直接原因（来自 stderr 或规则检测）
- 间接原因（可能是导致直接原因的上游问题）

### 3. 修复建议
**必须具体可操作，优先给出可直接复制粘贴的代码片段**

示例：
```
在 *STATIC 后添加初始步长参数：
*STATIC
0.01, 1.0
```

## 重要约束

**只使用 CalculiX 语法，禁止使用 Abaqus 专有卡片**
- ❌ `*CONTACT CONTROLS`、`*SURFACE INTERACTION` 参数名错误
- ❌ `*STATIC,0.01,1.0` 卡片名与参数之间不能有逗号
- ✅ 正确：`*STATIC` 后换行写参数

请直接回答，不要泛泛而谈。"""


def make_diagnose_prompt(
    rule_issues: list[dict],
    stderr_snippets: str = "",
    stderr_summary: str = "",
    similar_cases: Optional[list[dict]] = None,
    physical_data: str = "",
) -> str:
    """生成诊断的 prompt。

    三层精准摘要：
    1. 规则检测结果：问题描述（诊断结论）
    2. stderr 相关片段：规则层定位到的具体行（直接证据）
    3. 关键物理数据：节点数、位移、应力等（辅助判断）
    """
    issues_text = "\n".join(
        f"- [{i['severity']}] {i['category']}: {i['message']}"
        for i in rule_issues
    ) if rule_issues else "无明显规则违规。"

    # 相似案例信息
    cases_text = ""
    if similar_cases:
        cases_text = "\n\n### 相似参考案例\n"
        for case in similar_cases[:3]:
            cases_text += f"""- **{case['name']}** (相似度: {case['similarity_score']}%)
  - 单元类型: {case['element_type']}, 问题类型: {case['problem_type']}, 边界: {case['boundary_type']}
  - 预期位移范围: {case.get('expected_disp_max', 'N/A')}
  - 预期应力范围: {case.get('expected_stress_max', 'N/A')}
"""
    else:
        cases_text = "\n\n### 相似参考案例\n（无可用参考案例）"

    # 物理数据
    physical_text = ""
    if physical_data:
        physical_text = f"\n### 关键物理数据\n{physical_data}\n"

    # stderr 片段（直接证据）
    snippets_text = ""
    if stderr_snippets:
        snippets_text = f"\n### stderr 直接证据\n{stderr_snippets}\n"

    return f"""## 诊断摘要

### 规则检测结果
{issues_text}
{cases_text}{physical_text}{snippets_text}

### 求解器收敛指标
{stderr_summary}

请基于以上三层信息进行分析：
1. 规则检测结果告诉你诊断结论
2. stderr 直接证据是规则定位到的具体错误行
3. 物理数据帮助判断问题严重程度

不要读取任何原始文件，只基于上述信息回答。"""


# ------------------------------------------------------------------ #
# suggest 模板
# ------------------------------------------------------------------ #

SUGGEST_SYSTEM = """你是一位资深 FEA 优化工程师，擅长给出结构优化建议。

请基于以下诊断信息，按优先级给出 3-5 条优化建议。
每条建议包含：
- 类别（material / mesh / boundary / geometry）
- 优先级（1=最高，5=最低）
- 标题
- 描述
- 预期改进效果
- 实现难度（easy / medium / hard）

语言：中文
输出格式：JSON 数组

示例：
[
  {{"category": "mesh", "priority": 1, "title": "加密应力集中区域网格",
    "description": "...", "expected_improvement": "应力精度提升 20%",
    "implementation_difficulty": "medium"}}
]"""


def make_suggest_prompt(
    rule_issues: list[dict],
    ai_diagnosis: str,
    max_stress: float,
    max_displacement: float,
    material_yield: float,
) -> str:
    """生成优化建议的 prompt。"""
    issues_text = "\n".join(
        f"- [{i['severity']}] {i['category']}: {i['message']}"
        for i in rule_issues
    ) if rule_issues else "无明显规则违规。"

    stress_ratio = max_stress / material_yield if material_yield > 0 else 0

    return f"""## 当前状态摘要

### 关键指标
- 最大位移：{max_displacement:.6e}
- 最大应力：{max_stress:.6e}
- 应力/屈服比：{stress_ratio:.2f}

### 发现的问题
{issues_text}

### AI 诊断结果
{ai_diagnosis or "（无 AI 诊断）"}

请给出优化建议，专注于提升结构性能和可靠性。"""


# ------------------------------------------------------------------ #
# CAD 生成模板
# ------------------------------------------------------------------ #

CAD_SYSTEM = """你是一位 CadQuery 专家，擅长生成参数化几何代码。

请生成 CadQuery Python 代码，创建以下几何部件：
- 梁（Beam）：指定长度、宽度、高度、圆角半径
- 圆柱（Cylinder）：指定半径、高度、角度
- 板（Plate）：指定长度、宽度、厚度

要求：
1. 使用 CadQuery 2.x API
2. 导出函数 create_<type>(params) -> Workplane
3. 支持 export_step() 和 export_inp() 导出
4. 代码可直接运行

输出格式：纯 Python 代码块，不要解释。"""
