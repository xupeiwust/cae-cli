# cae-cli

> 轻量化 CAE 命令行工具 — 一条命令跑仿真，一个链接看结果

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CalculiX](https://img.shields.io/badge/CalculiX-2.22+-orange.svg)](https://www.calculix.org/)

机械系学生、小型实验室、装不动或买不起 ANSYS 的工程师的仿真工具。

---

## 快速开始

```bash
# 1. 安装
pip install cae-cli
cae install          # 安装 CalculiX 求解器

# 2. 生成模板文件
cae inp template cantilever_beam -o beam.inp

# 3. 求解
cae solve beam.inp

# 4. 查看结果
cae view results/     # 浏览器打开
```

---

## 核心功能

### 仿真全流程

| 步骤 | 命令 | 说明 |
|------|------|------|
| 划网格 | `cae mesh gen geometry.step -o mesh.inp` | Gmsh 自动网格划分 |
| 网格预览 | `cae mesh check mesh.inp` | CGX 风格 HTML 报告 |
| 执行求解 | `cae solve model.inp` | CalculiX 求解器 |
| 查看结果 | `cae view results/` | 浏览器 3D 可视化 |
| 一键运行 | `cae run geometry.step` | 网格 + 求解 + 可视化 |

### INP 文件处理

| 功能 | 命令 |
|------|------|
| 解析摘要 | `cae inp info model.inp` |
| 校验 | `cae inp check model.inp` |
| 修改参数 | `cae inp modify model.inp -k *ELASTIC --set "210000, 0.3"` |
| 显示块 | `cae inp show model.inp -k *MATERIAL` |
| 浏览关键词 | `cae inp list Step` |
| 生成模板 | `cae inp template cantilever_beam -o beam.inp` |
| AI 建议 | `cae inp suggest model.inp` |

### AI 助手

```bash
# 安装 AI 模型
cae model install deepseek-r1-7b

# AI 解读结果
cae explain results/

# AI 诊断问题
cae diagnose results/

# AI 优化建议
cae suggest results/
```

### 格式转换

```bash
cae convert results.frd -o output.vtu   # .frd → .vtu
cae convert mesh.msh -o output.inp      # .msh → .inp
```

---

## 安装

```bash
pip install cae-cli
pip install cae-cli[ai]    # AI 功能（可选）
pip install cae-cli[mesh]   # Gmsh 网格（可选）
```

**安装 CalculiX 求解器：**

```bash
cae install                # 自动下载（推荐）
# 或手动安装：
brew install calculix      # macOS
sudo apt install calculix-ccx  # Ubuntu
# Windows: https://calculix.org 下载并放到 PATH
```

---

## 命令参考

### cae solve

```bash
cae solve model.inp                    # 执行仿真
cae solve model.inp -o results/        # 指定输出目录
cae solve model.inp -s calculix        # 指定求解器
```

### cae mesh

```bash
cae mesh gen geometry.step -o mesh.inp           # 网格划分
cae mesh gen geometry.step -o mesh.inp --mesh-size=2.0  # 自定义网格尺寸
cae mesh check mesh.inp                          # 网格预览
```

### cae inp

```bash
cae inp info model.inp                  # 结构摘要
cae inp check model.inp                 # 校验必填参数
cae inp show model.inp -k *MATERIAL    # 显示关键词块
cae inp show model.inp -k *MATERIAL -n STEEL  # 按 NAME 查找
cae inp modify model.inp -k *ELASTIC --set "210000, 0.3"  # 修改参数
cae inp modify model.inp -k *STEP --delete  # 删除块
cae inp list                            # 关键词分类
cae inp list Mesh                       # Mesh 类关键词
cae inp list -k *BOUNDARY              # 关键词详情
cae inp template --list                 # 列出模板
cae inp template cantilever_beam -o beam.inp  # 生成文件
cae inp suggest model.inp               # AI 修改建议
```

### cae model

```bash
cae model list                          # 可用模型
cae model install deepseek-r1-7b        # 下载安装
cae model install deepseek-r1-7b --mirror https://hf-mirror.com  # 镜像
cae model info deepseek-r1-7b           # 模型信息
cae model uninstall deepseek-r1-7b     # 卸载
```

### cae test

```bash
cae test                                # 官方测试集（638 文件）
cae test --sample 20                    # 采样测试
cae test --quiet                        # 静默模式
```

### cae download

```bash
cae download "https://example.com/model.gguf" -o models/  # 任意 URL
```

### 其他

```bash
cae solvers              # 求解器状态
cae info                 # 配置信息
cae view results/        # 查看结果
```

---

## 内置模板

| 模板 | 命令 | 说明 |
|------|------|------|
| `cantilever_beam` | `cae inp template cantilever_beam -o beam.inp` | 悬臂梁（B32） |
| `flat_plate` | `cae inp template flat_plate -o plate.inp` | 平板（S4） |

**参数覆盖示例：**
```bash
cae inp template cantilever_beam -o beam.inp --L=200 --nodes=21 --load=500
cae inp template flat_plate -o plate.inp --Lx=150 --Ly=75 --pressure=2.0
```

---

## 内置 AI 模型

| 模型 | 大小 | 来源 |
|------|------|------|
| `deepseek-r1-7b` | 4.9 GB | huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-7B-GGUF |
| `deepseek-r1-14b` | 9.0 GB | huggingface.co/deepseek-ai/DeepSeek-R1-Distill-Qwen-14B-GGUF |
| `qwen2.5-7b` | 4.7 GB | huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF |

---

## 兼容性测试

使用 CalculiX 官方 `ccx_2.23.test` 测试集（638 个文件）验证：

| 阶段 | 内容 | 结果 |
|------|------|------|
| Phase 1 | `inp info` 解析 | **638/638 OK** |
| Phase 2 | `solve` 求解 | **8/10 OK** |
| Phase 3 | `convert` 转换 | **8/8 OK** |

**覆盖单元类型：** 实体（C3D4/6/8/15/20）、壳（S3/4/6/8）、梁（B31/32）、弹簧、热分析、接触、动力学、非线性

---

## 工作流程

```
.step 几何文件
    │
    ├─→ cae mesh gen ──→ .inp
    └─→ cae mesh check ──→ HTML 预览

.inp 文件  ──→ cae solve ──→ .frd + .dat
    │                        │
    │                        ├─→ cae view ──→ 浏览器
    │                        ├─→ cae explain ──→ AI 解读
    │                        ├─→ cae diagnose ──→ AI 诊断
    │                        └─→ cae convert ──→ .vtu

└─→ cae run ──→ mesh + solve + view（一键）
```

---

## 项目结构

```
cae-cli/
├── cae/
│   ├── main.py              # CLI 入口
│   ├── solvers/             # 求解器接口
│   ├── inp/                 # INP 处理（135 关键词）
│   ├── mesh/                # 网格处理
│   ├── viewer/              # 可视化（FRD/VTK）
│   ├── ai/                  # AI 功能
│   ├── installer/           # 安装器
│   └── config/              # 配置
├── test/                    # 测试模块
└── examples/                # 示例文件
```

---

## 技术栈

| 模块 | 技术 |
|------|------|
| CLI | Typer + Rich |
| 网格 | Gmsh 4.x |
| 求解器 | CalculiX 2.22+ |
| 格式转换 | meshio 5.x |
| 可视化 | ParaView Glance |
| AI | llama-cpp-python + DeepSeek R1 |
| 模板 | Jinja2 |

---

## 开发

```bash
git clone https://github.com/yd5768365-hue/cae-cli
cd cae-cli
pip install -e ".[dev]"

pytest tests/ -v          # 运行测试
ruff check cae/           # 代码检查
```

---

## License

MIT
