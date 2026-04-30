# cae-cli 桌面版

`cae-gui` 是 `cae-cli` 的 Tauri + Vue 3 桌面壳。它的核心不是复刻网页，而是把本机 `cae` CLI、诊断 JSON、Docker 状态、模型配置和项目文件扫描整合成一个 **AI 诊断工作台**。

## 当前定位

- **AI 诊断页**：选择真实 `.inp` 文件，运行 `cae diagnose --json`，查看规则命中、案例召回、LLM 状态和修正建议。
- **诊断驾驶舱**：读取 `cae gui snapshot --json`，展示项目快照、诊断流水线、真实置信度和证据来源。
- **求解证据**：围绕 CalculiX / Docker 求解输出，展示日志、结果文件和运行状态。
- **容器环境**：检测 WSL2 Docker、镜像目录和本机求解器状态。

桌面端应始终优先展示真实项目数据。临时占位内容只能用于空状态，不能冒充诊断结果。

## 数据链路

```text
Vue 页面
    ↓
useCaeCli
    ↓
Tauri Shell allowlist
    ↓
本机 cae CLI
    ↓
cae diagnose --json / cae gui snapshot --json
```

关键命令：

```powershell
cae diagnose examples/simple_beam.inp --json
cae gui snapshot --project-root E:\cae-cli --inp examples/simple_beam.inp --json
```

置信度、风险评分、诊断流水线和“查看依据”必须来自 JSON 字段，例如：

- `issues[].evidence_score`
- `issues[].evidence_source_trust`
- `issues[].evidence_support_count`
- `issues[].evidence_line`
- `summary.risk_score`
- `summary.execution_plan`
- `similar_cases`

## 开发运行

先在仓库根目录安装 Python 包：

```powershell
pip install -e ".[dev,ai,mesh,report,mcp]"
```

再进入桌面端目录：

```powershell
cd cae-gui
npm install
npm run dev
npm run tauri dev
```

如果 PowerShell venv 激活被拦截：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## 打包

优先构建 NSIS 安装包：

```powershell
npm run tauri build -- --bundles nsis
```

构建产物：

```text
src-tauri/target/release/bundle/nsis/CAE 工具箱_0.1.0_x64-setup.exe
```

免安装可执行文件：

```text
src-tauri/target/release/cae-gui.exe
```

Windows 如果命中了系统 `link.exe` 而不是 MSVC 链接器，使用 Visual Studio Build Tools 环境：

```powershell
cmd /d /s /c '"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" && npx tauri build --bundles nsis'
```

MSI 依赖 WiX。当前更稳定的发布产物是 NSIS `.exe` 安装包。

## 开发约束

- 不把演示数据伪装成真实结果。
- 新增 CLI 调用前，需要同步更新 `src-tauri/capabilities/default.json`。
- UI 文案保持中文，核心诊断字段保留英文 key，方便和 CLI JSON 对齐。
- 文件选择、模型切换、置信度详情是核心路径，改动后必须手动验证。
