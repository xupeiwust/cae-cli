# cae-cli

> 轻量化 CAE 命令行工具 — 一条命令跑仿真，一个链接看结果

机械系学生、小型实验室、装不动或买不起 ANSYS 的工程师的仿真工具。

```
$ cae solve bracket.inp
  输出目录 [results/bracket]:
  求解器 [calculix]:

  使用求解器: calculix  (v2.21)
  输入文件:   bracket.inp
  输出目录:   results/bracket

  ⠿ 求解中...  0:00:03

  ╭─────────────────────────────────╮
  │ ✅ 求解完成！  耗时 3.2s         │
  ╰─────────────────────────────────╯

  输出文件:
   bracket.frd   2.4 MB
   bracket.dat   12 KB

  📊 查看结果: `cae view results/bracket`
  💡 输入 `cae explain` 让 AI 解读结果
```

---

## 核心理念

工具只负责**调用求解器**和**展示结果**。前处理（建模、定义工况、设置边界条件）由用户在熟悉的 CAD 软件中完成，导出 `.inp` 或 `.step` 文件交给 `cae-cli` 处理。

---

## 安装

```bash
pip install cae-cli          # 安装 CLI
cae install                  # 下载 CalculiX 求解器（第四周实现）
```

**手动安装 CalculiX（当前阶段）**

```bash
# macOS (Homebrew)
brew install calculix

# Ubuntu / Debian
sudo apt install calculix-ccx

# 或者手动编译后将 ccx 放入 PATH
```

---

## 快速上手

```bash
# 用示例文件测试
cae solve examples/simple_beam.inp

# 查看所有可用命令
cae --help

# 检查求解器安装状态
cae solvers
```

---

## 命令一览

| 命令 | 说明 | 状态 |
|------|------|------|
| `cae solve [file.inp]` | 执行 FEA 仿真 | ✅ 第一周 |
| `cae solvers` | 列出求解器状态 | ✅ 第一周 |
| `cae info` | 显示配置路径 | ✅ 第一周 |
| `cae view [results/]` | 浏览器查看结果 | 🚧 第二周 |
| `cae mesh` | 交互式划网格 | 🚧 第三周 |
| `cae run [model.step]` | 全流程一键运行 | 🚧 第三周 |
| `cae install` | 安装 CalculiX + 模型 | 🚧 第四周 |
| `cae explain [results/]` | AI 解读结果 | 🚧 第五周 |
| `cae diagnose [results/]` | AI 诊断问题 | 🚧 第五周 |
| `cae suggest [results/]` | AI 优化建议 | 🚧 第五周 |

---

## 技术选型

| 模块 | 选择 |
|------|------|
| 语言 | Python 3.10+ |
| CLI 框架 | Typer + Rich |
| 网格 | Gmsh |
| 求解器 | CalculiX |
| 格式转换 | meshio |
| 可视化 | ParaView Glance |
| AI 模型 | llama.cpp + DeepSeek R1 7B GGUF |

---

## 扩展求解器

新增求解器只需两步，其他代码不动：

```python
# 1. cae/solvers/openfoam.py
from .base import BaseSolver, SolveResult

class OpenFoamSolver(BaseSolver):
    name = "openfoam"
    ...

# 2. cae/solvers/registry.py
SOLVERS = {
    "calculix": CalculixSolver,
    "openfoam": OpenFoamSolver,  # ← 加这一行
}
```

---

## 开发

```bash
git clone https://github.com/yourname/cae-cli
cd cae-cli
pip install -e ".[dev]"

# 运行测试
pytest

# 检查代码风格
ruff check cae/
```

---

## 六周开发计划

| 周次 | 目标 | 状态 |
|------|------|------|
| 第一周 | 建仓库 + `cae solve` 调通 CalculiX | ✅ |
| 第二周 | 结果转 VTK + ParaView Glance 跑通 | 🚧 |
| 第三周 | `cae mesh` 调通 Gmsh + `cae run` 全流程 | 🚧 |
| 第四周 | `cae install` 自动安装 + 打包发布 | 🚧 |
| 第五周 | AI explain/diagnose 接入 llama.cpp | 🚧 |
| 第六周 | 测试 + 文档 + 第一个真实用例跑通 | 🚧 |

---

## License

MIT