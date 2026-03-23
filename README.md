# cae-cli

> **轻量化 CAE 命令行工具** — 一条命令跑仿真，一个链接看结果

<p align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![PyPI](https://img.shields.io/badge/PyPI-cae--cxx%20v1.2.5-blue.svg)](https://pypi.org/project/cae-cxx/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Test](https://img.shields.io/badge/Tests-112%20passed-brightgreen.svg)](#兼容性验证)
[![CalculiX](https://img.shields.io/badge/CalculiX-2.22+-orange.svg)](https://www.calculix.org/)

</p>

**机械学生 | 独立工程师 | 小型实验室** — 用不起 ANSYS/Abaqus 的替代方案

---

## 目录

- [新增功能](#新增功能)
- [快速开始](#快速开始)
- [核心能力](#核心能力)
- [安装](#安装)
- [命令速查](#命令速查)
- [内置模板](#内置模板)
- [Python API](#python-api)
- [AI 模型](#ai-模型)
- [FAQ](#faq)
- [项目结构](#项目结构)
- [开发](#开发)

---

## 新增功能

### v1.2.5 (2026-03)

**Bug 修复**：
- 修复 FRD 解析器无法正确解析科学计数法数字
- 修复 -4 行字段名解析错误
- 修复 VTK 导出时 values 字典访问错误
- 移除硬编码路径，改用 Path(__file__) 相对定位
- 修复 Ctrl+C 无法退出可视化服务（ThreadingTCPServer）

### v1.3.0 (开发中)

**协议接口**：所有关键词类实现 `IKeyword` 协议，支持类型检查和 IDE 自动补全

**材料模型**：
- `HyperElastic` — 超弹性材料（Mooney-Rivlin / Ogden / Yeoh / Arruda-Boyce）
- `Plastic` — 塑性材料（等向/运动/组合硬化 + 循环硬化）

**接触分析**：
- `SurfaceInteraction` / `SurfaceBehavior` / `Friction` — 完整接触定义
- `ContactPair` — 接触对（NODE_TO_SURFACE / SURFACE_TO_SURFACE）
- `Tie` — 绑定接触
- `Gap` / `GapUnit` — 间隙单元

**约束**：
- `Coupling` — KINEMATIC / DISTRIBUTING 耦合
- `Mpc` — MPC 多点约束（BEAM / PLANE / STRAIGHT / MEANROT / DIST）
- `Equation` — 线性方程约束 + `EquationFactory` 工厂方法

**载荷**：
- `Amplitude` — 载荷-时间幅值曲线
- `Cload` / `Dload` / `Boundary` — 载荷和边界条件

---

---

## 快速开始

```bash
# 1. 安装 (30 秒)
pip install cae-cxx && cae install

# 2. 生成悬臂梁模板
cae inp template cantilever_beam -o beam.inp

# 3. 求解 + 查看结果
cae solve beam.inp && cae view results/
```

**输出示例：**

```
╭───────────────────────╮
║  求解完成！  0.1s   ║
╰───────────────────────╯

  achtel2.cvg   278 B
  achtel2.dat   16 KB
  achtel2.frd   24 KB
  achtel2.sta   173 B
```

浏览器自动打开 ParaView Glance 显示位移 / 应力云图

---

## 核心能力

### 仿真全流程

| 功能 | 命令 | 说明 |
|:----:|------|------|
| 🔲 网格划分 | `cae mesh gen geo.step -o mesh.inp` | Gmsh 自动网格 |
| 👁 网格预览 | `cae mesh check mesh.inp` | HTML 报告 |
| ⚡ 执行仿真 | `cae solve model.inp` | CalculiX 求解 |
| 🌐 3D 可视化 | `cae view results/` | 浏览器打开 |
| 🚀 一键运行 | `cae run geo.step` | 全自动 |

### INP 文件处理

| 功能 | 命令 |
|------|------|
| 📋 结构摘要 | `cae inp info model.inp` |
| ✔️ 校验 | `cae inp check model.inp` |
| 👁 显示块 | `cae inp show model.inp -k *MATERIAL -n STEEL` |
| ✏️ 修改 | `cae inp modify model.inp -k *ELASTIC --set "210000, 0.3"` |
| 📚 关键词浏览 | `cae inp list Mesh` |
| 📝 模板生成 | `cae inp template cantilever_beam -o model.inp` |
| 🤖 AI 建议 | `cae inp suggest model.inp` |

### AI 助手

| 功能 | 命令 | 说明 |
|------|------|------|
| 📥 安装模型 | `cae model install deepseek-r1-7b` | ~5 GB |
| 📊 AI 解读 | `cae explain results/` | 位移/应力分析 |
| 🔍 AI 诊断 | `cae diagnose results/` | 收敛性/网格质量 |
| 💡 AI 建议 | `cae suggest results/` | 优化方案 |
| 📄 PDF 报告 | `cae report results/` | 最大位移/应力/安全系数/云图，一键发给导师 |

### 格式转换

```
.frd → .vtu    cae convert result.frd -o out.vtu
.msh → .inp    cae convert mesh.msh -o out.inp
.dat → .csv    cae convert result.dat -o out.csv
```

---

## 安装

```bash
# 基础安装
pip install cae-cxx

# 完整安装（含 AI + 网格 + PDF 报告）
pip install cae-cxx[ai,mesh,report]

# 仅安装 PDF 报告支持
pip install cae-cxx[report]
```

### 安装求解器

| 系统 | 一键安装 | 手动安装 |
|------|----------|----------|
| Windows | `cae install` | [calculix.org](https://calculix.org) |
| macOS | `cae install` | `brew install calculix` |
| Ubuntu | `cae install` | `sudo apt install calculix-ccx` |

---

## 命令速查

### `cae solve` — 求解

```bash
cae solve model.inp                    # 标准求解
cae solve model.inp -o results/      # 输出到目录
cae solve model.inp -t 3600          # 超时 1 小时
```

### `cae mesh` — 网格

```bash
cae mesh gen geo.step -o mesh.inp              # 生成网格
cae mesh gen geo.step -o mesh.inp -s 2.0      # 网格尺寸
cae mesh gen geo.step -o mesh.inp --order 2   # 二阶单元
cae mesh check mesh.inp                        # 预览网格
```

### `cae inp` — INP 文件

```bash
cae inp info model.inp                       # 结构摘要
cae inp check model.inp                      # 校验
cae inp show model.inp -k *MATERIAL         # 显示块
cae inp modify model.inp -k *ELASTIC --set "210000, 0.3"  # 修改
cae inp list                                 # 关键词分类
cae inp list Mesh                            # Mesh 类关键词
cae inp list -k *BOUNDARY                   # 关键词详情
cae inp template --list                      # 模板列表
cae inp template cantilever_beam -o beam.inp # 生成
cae inp suggest model.inp                    # AI 建议
```

### `cae model` — AI 模型

```bash
cae model list                                      # 模型列表
cae model install deepseek-r1-7b                    # 安装
cae model install deepseek-r1-7b -m hf-mirror.com  # 镜像
cae model info deepseek-r1-7b                       # 信息
cae model uninstall deepseek-r1-7b                  # 卸载
```

### `cae test` — 测试

```bash
cae test                     # 官方测试集（638 文件）
cae test --sample 20        # 采样 20 个
cae test --quiet             # 静默
```

### `cae report` — PDF 报告

```bash
cae report results/                         # 生成报告（默认输出到 results/report_*.pdf）
cae report results/ -o report.pdf           # 指定输出路径
cae report results/ -i model.inp           # 附带 INP 材料属性
cae report results/ -y 350 -j beam_test     # 手动指定屈服强度和工况名
cae report results/ -s 100                  # 调整变形放大倍数（云图）
```

> 需要 weasyprint：`pip install cae-cxx[report]`

### 其他命令

```bash
cae run geo.step             # 一键运行
cae view results/            # 查看结果
cae convert file.frd -o.vtu  # 格式转换
cae solvers                  # 求解器状态
cae info                     # 配置信息
cae download URL -o path/    # 下载文件
```

---

## 内置模板

| 模板 | 命令 | 单元 | 典型应用 |
|------|------|------|----------|
| 悬臂梁 | `cantilever_beam` | B32 | 桥梁、建筑梁 |
| 平板 | `flat_plate` | S4 | 板壳结构 |

```bash
# 参数覆盖示例
cae inp template cantilever_beam -o beam.inp --L=500 --nodes=21 --load=1000
cae inp template flat_plate -o plate.inp --Lx=200 --Ly=100 --pressure=5.0
```

---

## Python API

除了命令行，cae-cli 还提供完整的 Python API：

```python
from cae.inp import ModelBuilder, StaticStep
from cae.material import Elastic, Plastic
from cae.contact import ContactPair, SurfaceInteraction, SurfaceBehavior
from cae.enums import ContactType, PressureOverclosure, HardeningRule

# 构建模型
model = ModelBuilder()
model.add_node(1, (0, 0, 0))
model.add_node(2, (100, 0, 0))
model.add_element("C3D8", [1, 2, 3, 4, 5, 6, 7, 8])

# 添加材料（塑性）
elastic = Elastic(params=(210000, 0.3))
plastic = Plastic(stress=[200, 250], strain=[0, 0.1], hardening=HardeningRule.ISOTROPIC)
model.add_material("STEEL", elastic, plastic)

# 添加接触
si = SurfaceInteraction(name="STEEL_CONTACT")
sb = SurfaceBehavior(pressure_overclosure=PressureOverclosure.EXPONENTIAL, c0=0.05, p0=5e7)
cp = ContactPair(interaction=si, type=ContactType.SURFACE_TO_SURFACE, dep_surf=..., ind_surf=...)

# 添加载荷步
step = StaticStep(time_period=1.0, nlgeom=True)
step.add_boundary(nodes={1}, dofs={1: 0, 2: 0, 3: 0})
step.add_load(nodes={2}, dofs={3: -1000})

# 输出 INP
print(model.to_inp())
```

---

| 模型 | 大小 | 量化 | 最低显存 | 来源 |
|------|------|------|----------|------|
| `deepseek-r1-7b` | 4.9 GB | Q4_K_M | 6 GB | HuggingFace |
| `deepseek-r1-14b` | 9.0 GB | Q4_K_M | 8 GB | HuggingFace |
| `qwen2.5-7b` | 4.7 GB | Q4_K_M | 6 GB | HuggingFace |

> 💡 国内用户添加 `--mirror https://hf-mirror.com` 加速下载

---

## FAQ

**Q: 支持 Windows 吗？**
> ✅ 支持，Windows 10/11 + Python 3.10+

**Q: 和 ANSYS/Abaqus 有什么区别？**

| 对比 | cae-cxx | ANSYS/Abaqus |
|------|---------|--------------|
| 价格 | 免费 | 几万~几十万/年 |
| 功能 | 核心 FEA | 完整多物理场 |
| 门槛 | 命令行 | GUI 交互 |
| 适用 | 简单结构/学习 | 复杂工程 |

**Q: 支持 GUI 吗？**
> 结果可通过浏览器 3D 可视化（ParaView Glance），核心操作仍是命令行

**Q: 计算精度如何？**
> 使用与 ANSYS/Abaqus 相同的 CalculiX 求解器，638 个官方测试用例 100% 通过

**Q: 模型文件多大？**
> AI 模型约 5 GB（Q4 量化），CalculiX 求解器约 50 MB

---

## 兼容性验证

使用 **CalculiX 官方 ccx_2.23.test 测试集**（638 个 .inp 文件）：

| 测试 | 通过率 | 说明 |
|------|--------|------|
| INP 解析 | ✅ 638/638 (100%) | 100% |
| 求解执行 | ✅ 8/10 | 声学分析除外 |
| 格式转换 | ✅ 8/8 (100%) | 100% |

**覆盖单元类型：**
- 实体单元：C3D4/6/8/15/20（含二阶）
- 壳单元：S3/4/6/8（含减缩积分）
- 梁单元：B31/B32
- 弹簧单元：Spring1~Spring7
- 接触分析：Contact1~19、Mortar
- 热分析：稳态/瞬态/热-结构耦合
- 动力学：模态/频率响应/瞬态响应
- 非线性：几何非线性/材料非线性

---

## 项目结构

```
cae-cli/
├── cae/
│   ├── main.py              # CLI 入口 (Typer)
│   ├── enums.py             # 枚举定义 (50+ 类型)
│   ├── _utils.py            # 工具函数 (f2s 格式化)
│   ├── protocols.py         # 接口协议 (IKeyword/IStep)
│   ├── solvers/             # 求解器接口
│   │   ├── base.py         # 抽象基类
│   │   └── calculix.py     # CalculiX 实现
│   ├── inp/                 # INP 文件处理
│   │   ├── kw_list.json    # 135 关键词参数
│   │   ├── kw_tree.json    # 关键词分类
│   │   ├── template.py     # Jinja2 模板
│   │   ├── model_builder.py # Python 类模板 (CantileverBeam/FlatPlate)
│   │   ├── step_keywords.py # 载荷步关键词 (Amplitude/CLOAD/DLOAD/BOUNDARY/Coupling)
│   │   ├── equation.py     # 方程约束 (Equation/EQUATION)
│   │   └── steps.py        # 载荷步类 (Static/Dynamic/Frequency/Buckle)
│   ├── mesh/                # 网格处理
│   │   ├── element.py       # 单元类型定义
│   │   ├── surface.py       # 接触面/载荷面定义
│   │   ├── gmsh_runner.py  # Gmsh API
│   │   └── converter.py    # meshio 转换
│   ├── contact/             # 接触分析
│   │   ├── surface_interaction.py  # 表面相互作用
│   │   ├── surface_behavior.py     # 表面行为 (压力过盈)
│   │   ├── friction.py             # 摩擦模型
│   │   ├── contact_pair.py         # 接触对
│   │   ├── tie.py                  # 绑定接触
│   │   └── gap.py                  # 间隙单元 (Gap/GapUnit)
│   ├── coupling/            # 耦合约束
│   │   ├── coupling.py      # KINEMATIC/DISTRIBUTING 耦合
│   │   └── mpc.py           # MPC 多点约束
│   ├── material/            # 材料模型
│   │   ├── elastic.py       # 弹性模型 (ISO/ORTHO/ANISO)
│   │   ├── plastic.py       # 塑性模型 (等向/运动/组合硬化)
│   │   └── hyperelastic.py  # 超弹性模型 (Mooney-Rivlin/Arruda-Boyce/Ogden/Yeoh)
│   ├── viewer/              # 可视化
│   │   ├── frd_parser.py    # FRD 解析
│   │   ├── dat_parser.py    # DAT 解析
│   │   ├── _utils.py       # 应力工具 (von_mises/主应力/剪切应力)
│   │   ├── vtk_export.py    # VTK 导出
│   │   ├── pyvista_renderer.py  # PyVista 渲染引擎
│   │   ├── mesh_check.py    # 网格预览 HTML
│   │   ├── html_generator.py    # HTML 报告生成器
│   │   └── pdf_report.py    # PDF 报告生成器
│   ├── ai/                  # AI 功能
│   │   ├── llm_client.py    # LLM 接口
│   │   ├── explain.py       # 结果解读
│   │   ├── diagnose.py       # 问题诊断
│   │   └── suggest.py        # 优化建议
│   └── installer/           # 安装器
│       ├── solver_installer.py
│       └── model_installer.py
├── tests/                  # 测试用例 (112 passed)
└── examples/              # 示例文件
```

---

## 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| CLI | Typer + Rich | 命令行 + 美化输出 |
| 网格 | Gmsh 4.x | 自动网格划分 |
| 求解器 | CalculiX 2.22+ | 开源 FEA |
| 格式 | meshio 5.x | 多格式转换 |
| 可视化 | ParaView Glance | Web 3D  viewer |
| AI | llama-cpp-python | 本地 LLM |
| 模板 | Jinja2 | 参数化生成 |

---

## 开发

```bash
# 克隆
git clone https://github.com/yd5768365-hue/cae-cli
cd cae-cli

# 安装开发版
pip install -e ".[dev]"

# 测试
pytest tests/ -v

# 代码检查
ruff check cae/
```

---

## License

MIT
