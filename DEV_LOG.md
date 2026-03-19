# DEV_LOG.md

## 2026年3月19日

### 新增：CAE-CLI AI 模式功能

- **问题描述**：用户需要完整的 AI 模式功能，包括 llama-cpp-python 外部进程支持、流式输出、AI 解读、规则检测 + AI 诊断、优化建议生成、CadQuery 基础部件生成。

- **解决方法**：

  1. 新增 `cae/ai/` 模块，包含以下文件：
     - `llm_client.py` — LLMClient 管理 llama-cpp-python，支持 direct/server 两种模式
     - `stream_handler.py` — StreamHandler 使用 rich.live.Live 实时显示 SSE 流
     - `prompts.py` — Prompt 模板库（explain/diagnose/suggest）
     - `explain.py` — AI 结果解读，解析 .frd 文件提取节点/单元/位移/应力统计
     - `diagnose.py` — 规则检测 + AI 诊断，支持收敛性/网格质量/应力集中/位移范围检测
     - `suggest.py` — 优化建议生成，基于诊断结果的规则 + AI 混合建议
     - `cad_generator.py` — CadGenerator 参数化几何创建（梁/圆柱/板），懒加载 cadquery
     - `__init__.py` — 模块导出（懒加载 heavy dependencies）

  2. 更新 `pyproject.toml`：
     - 新增 `ai` 可选依赖：`requests>=2.31`, `cadquery>=2.4`

  3. 更新 `main.py`：
     - 新增 `suggest` 命令：`cae suggest <results_dir> [--no-ai] [--stream/--no-stream]`

- **解决效果**：
  - `explain`、`diagnose`、`suggest` 三个 AI 命令完整可用
  - Direct 模式省内存（推荐 8GB 以下机器使用）
  - Server 模式支持多并发请求
  - 模块懒加载，不安装 ai 依赖时不会报错
  - CadQuery 几何生成支持参数化部件创建

- **关键复用**：
  - `cae/solvers/base.py:SolveResult` — 参考 dataclass 封装模式
  - `cae/solvers/calculix.py` — 复用 subprocess 进程管理逻辑
  - `cae/config/__init__.py:settings` — 直接使用配置单例
  - `cae/viewer/__init__.py` — 参考懒加载 `__getattr__` 模式
  - `cae/viewer/frd_parser.py:parse_frd()` — 直接使用解析 .frd 文件

### 问题1：llama-cpp-python 版本兼容

- **问题描述**：
  - 初始安装的 llama-cpp-python 0.3.2 不支持 DeepSeek-R1-Distill-Qwen-7B-Q2_K 模型
  - 错误：`unknown pre-tokenizer type: 'deepseek-r1-qwen'`

- **解决方法**：
  ```bash
  pip install --upgrade llama-cpp-python
  ```
  升级到 0.3.16 后模型可正常加载。

### 问题2：Direct API vs Server API

- **问题描述**：
  - llama-server 模式需要 ~2.3GB logits buffer，在部分机器上内存不足
  - Server 模式启动失败：`ArrayMemoryError: Unable to allocate 2.32 GiB`

- **解决方法**：
  - 重构 `LLMClient` 支持 Direct 模式
  - Direct 模式直接调用 `llama_cpp.Llama`，内存效率更高
  - 默认使用 Direct 模式，设置 `use_server=True` 可切换到 Server 模式
  - 降低默认 context_size=2048 避免内存问题

### 测试结果

```bash
# 测试 explain
$ cae explain results/cantilever
Success: True
Summary: 网格信息里有2650个节点和10388个单元...（中文解读正常）

# 测试 diagnose
$ cae diagnose results/cantilever
Success: True
Issue count: 1
[warning] mesh_quality: 节点/单元比例过低 (0.26)

# 测试 suggest
$ cae suggest results/cantilever
Success: True
Suggestions count: 1
[2] 优化网格划分: 网格质量警告...
```
