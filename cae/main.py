# CLI 入口
"""
cae-cli 主入口
CLI 框架：Typer + Rich

已实现命令：
  cae solve [FILE]        — 调用 CalculiX 执行仿真         （第一周）
  cae solvers             — 列出已注册求解器及安装状态      （第一周）
  cae info                — 显示配置路径信息                （第一周）
  cae view [RESULTS_DIR]  — 浏览器查看 VTK 仿真结果        （第二周）
  cae convert [FRD_FILE]  — 手动转换 .frd → .vtu           （第二周）
  cae mesh [GEO_FILE]     — 交互式网格划分（Gmsh）          （第三周）
  cae run [MODEL_FILE]    — 全流程一键运行                  （第三周）

后续周次将补充：
  cae install / cae explain / cae diagnose / cae suggest
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich import box

from cae.config import settings
from cae.solvers.registry import get_solver, list_solvers

# ------------------------------------------------------------------ #
# App 初始化
# ------------------------------------------------------------------ #

app = typer.Typer(
    name="cae",
    help="轻量化 CAE 命令行工具 — 一条命令跑仿真，一个链接看结果",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

console = Console()
err_console = Console(stderr=True, style="bold red")

# ------------------------------------------------------------------ #
# cae solve
# ------------------------------------------------------------------ #

@app.command()
def solve(
    inp_file: Optional[Path] = typer.Argument(
        None,
        help=".inp 输入文件路径（交互模式下可省略）",
        show_default=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="结果输出目录（默认 results/<job_name>/）",
        show_default=False,
    ),
    solver: str = typer.Option(
        None,
        "--solver", "-s",
        help="求解器名称（默认使用配置中的 default_solver）",
        show_default=False,
    ),
    timeout: int = typer.Option(
        3600,
        "--timeout",
        help="求解超时秒数",
    ),
) -> None:
    """
    [bold]执行 FEA 仿真求解[/bold]

    \b
    示例：
      cae solve bracket.inp
      cae solve bracket.inp --output ./my_results
      cae solve  （纯交互模式）
    """
    console.print()
    console.print(Panel.fit(
        "[bold cyan]cae solve[/bold cyan] — FEA 仿真求解",
        border_style="cyan",
    ))
    console.print()

    # ---- 交互式获取输入文件 ----
    if inp_file is None:
        raw = typer.prompt("  请输入 .inp 文件路径")
        inp_file = Path(raw.strip())

    # ---- 校验文件存在 ----
    if not inp_file.exists():
        err_console.print(f"\n  文件不存在: {inp_file}\n")
        raise typer.Exit(1)

    # ---- 交互式获取输出目录 ----
    if output is None:
        default_out = settings.default_output_dir / inp_file.stem
        raw_out = typer.prompt(
            f"  输出目录",
            default=str(default_out),
        )
        output = Path(raw_out.strip())

    # ---- 交互式选择求解器 ----
    if solver is None:
        solver = settings.default_solver

    console.print()

    # ---- 实例化求解器 ----
    try:
        solver_instance = get_solver(solver)
    except ValueError as exc:
        err_console.print(f"\n  {exc}\n")
        raise typer.Exit(1)

    # ---- 检查安装状态 ----
    if not solver_instance.check_installation():
        console.print(
            f"  [bold red]未找到求解器 '{solver}'[/bold red]\n"
            "  请先运行 [bold]`cae install`[/bold] 安装 CalculiX。\n"
        )
        raise typer.Exit(1)

    version = solver_instance.get_version()
    console.print(f"  使用求解器: [green]{solver}[/green]"
                  + (f"  [dim]({version})[/dim]" if version else ""))
    console.print(f"  输入文件:   [cyan]{inp_file}[/cyan]")
    console.print(f"  输出目录:   [cyan]{output}[/cyan]")
    console.print()

    # ---- 执行求解（带进度条）----
    result = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task("  [bold yellow]求解中...[/bold yellow]", total=None)
        result = solver_instance.solve(
            inp_file.resolve(),
            output.resolve(),
            timeout=timeout,
        )
        progress.update(task, completed=True)

    # ---- 显示结果 ----
    console.print()
    _print_solve_result(result, inp_file)


def _print_solve_result(result, inp_file: Path) -> None:
    """渲染求解结果摘要。"""
    from cae.solvers.base import SolveResult

    if result.success:
        console.print(Panel(
            f"[bold green]求解完成！[/bold green]  耗时 {result.duration_str}",
            border_style="green",
            expand=False,
        ))
        console.print()

        # 输出文件表格
        table = Table(
            "文件", "大小", box=box.SIMPLE, show_header=True,
            header_style="bold dim",
        )
        for f in result.output_files:
            size = _fmt_size(f.stat().st_size) if f.exists() else "-"
            table.add_row(str(f.name), size)

        console.print("  [bold]输出文件:[/bold]")
        console.print(table)

        if result.frd_file:
            console.print(
                f"  查看结果: [bold]`cae view {result.output_dir}`[/bold]"
            )
        if result.warnings:
            console.print(
                f"\n  [yellow]警告: {len(result.warnings)} 条[/yellow]"
                " — 运行 [bold]`cae diagnose`[/bold] 查看详情"
            )
        console.print(
            "\n  输入 [bold]`cae explain`[/bold] 让 AI 解读结果\n"
        )

    else:
        console.print(Panel(
            f"[bold red]求解失败[/bold red]  耗时 {result.duration_str}",
            border_style="red",
            expand=False,
        ))
        console.print()
        if result.error_message:
            console.print("  [bold]错误信息:[/bold]")
            for line in result.error_message.strip().splitlines():
                console.print(f"  [red]{line}[/red]")
        console.print(
            "\n  运行 [bold]`cae diagnose`[/bold] 让 AI 诊断问题\n"
        )
        raise typer.Exit(1)


# ------------------------------------------------------------------ #
# cae solvers
# ------------------------------------------------------------------ #

@app.command(name="solvers")
def list_solvers_cmd() -> None:
    """列出所有已注册求解器及其安装状态。"""
    console.print()
    table = Table(
        "名称", "状态", "版本", "支持格式", "描述",
        box=box.ROUNDED,
        header_style="bold cyan",
    )

    for info in list_solvers():
        status = "[green]已安装[/green]" if info["installed"] else "[red]未安装[/red]"
        version = info["version"] or "-"
        fmts = ", ".join(info["formats"])
        table.add_row(
            f"[bold]{info['name']}[/bold]",
            status,
            version,
            fmts,
            info["description"],
        )

    console.print(table)
    console.print()


# ------------------------------------------------------------------ #
# cae info
# ------------------------------------------------------------------ #

@app.command()
def info() -> None:
    """显示 cae-cli 配置路径与版本信息。"""
    console.print()
    console.print(Panel.fit("[bold cyan]cae-cli 配置信息[/bold cyan]", border_style="cyan"))
    console.print()

    rows = [
        ("配置目录", str(settings.config_dir)),
        ("数据目录", str(settings.data_dir)),
        ("求解器目录", str(settings.solvers_dir)),
        ("模型目录", str(settings.models_dir)),
        ("默认求解器", settings.default_solver),
        ("当前 AI 模型", settings.active_model or "（未设置）"),
    ]

    table = Table(box=box.SIMPLE, show_header=False)
    table.add_column(style="bold dim", no_wrap=True)
    table.add_column()
    for k, v in rows:
        table.add_row(k, v)

    console.print(table)
    console.print()


# ------------------------------------------------------------------ #
# 占位命令（后续周次实现）
# ------------------------------------------------------------------ #

@app.command()
def run(
    model_file: Optional[Path] = typer.Argument(
        None,
        help="模型文件路径（.step/.brep/.iges → 自动划网格；.inp → 直接求解）",
        show_default=False,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="结果输出目录（默认 results/<name>/）",
    ),
    quality: str = typer.Option(
        "medium", "--quality", "-q",
        help="网格精度 [coarse/medium/fine]",
    ),
    solver_name: str = typer.Option(
        None, "--solver", "-s",
        help="求解器名称",
    ),
    timeout: int = typer.Option(3600, "--timeout", help="求解超时秒数"),
    no_view: bool = typer.Option(False, "--no-view", help="完成后不启动可视化"),
) -> None:
    """
    [bold]全流程一键运行[/bold] — 网格 → 求解 → 可视化

    \b
    .step / .brep / .iges 文件：自动划网格 + 求解 + 查看结果
    .inp 文件：跳过划网格，直接求解 + 查看结果

    示例：
      cae run bracket.step
      cae run bracket.inp --quality fine
      cae run               （纯交互模式）
    """
    from cae.mesh.gmsh_runner import (
        MeshQuality, mesh_geometry, check_gmsh, SUPPORTED_GEO_FORMATS,
    )
    from cae.solvers.registry import get_solver
    from cae.viewer.vtk_export import frd_to_vtu

    console.print()
    console.print(Panel.fit(
        "[bold cyan]cae run[/bold cyan] — 全流程仿真",
        border_style="cyan",
    ))
    console.print()

    # ---- 获取输入文件 ----
    if model_file is None:
        raw = typer.prompt("  请输入模型文件路径")
        model_file = Path(raw.strip())

    if not model_file.exists():
        err_console.print(f"\n  文件不存在: {model_file}\n")
        raise typer.Exit(1)

    # ---- 判断是否需要划网格 ----
    ext = model_file.suffix.lower()
    needs_mesh = ext in SUPPORTED_GEO_FORMATS and ext != ".inp"
    is_inp = ext == ".inp"

    if not needs_mesh and not is_inp:
        err_console.print(
            f"\n  不支持的格式 '{ext}'\n"
            f"  几何格式: {', '.join(SUPPORTED_GEO_FORMATS.keys())}\n"
            f"  网格格式: .inp\n"
        )
        raise typer.Exit(1)

    # ---- 输出目录 ----
    if output is None:
        default_out = settings.default_output_dir / model_file.stem
        raw_out = typer.prompt("  输出目录", default=str(default_out))
        output = Path(raw_out.strip()).resolve()

    output.mkdir(parents=True, exist_ok=True)

    # ---- 求解器 ----
    solver_name = solver_name or settings.default_solver
    try:
        solver_instance = get_solver(solver_name)
    except ValueError as exc:
        err_console.print(f"\n  {exc}\n")
        raise typer.Exit(1)

    if not solver_instance.check_installation():
        err_console.print(
            f"\n  求解器 '{solver_name}' 未安装\n"
            "  请运行: [bold]cae install[/bold]\n"
        )
        raise typer.Exit(1)

    total_steps = 3 if needs_mesh else 2
    step_n = 0

    def step(label: str) -> None:
        nonlocal step_n
        step_n += 1
        console.print(f"  [{step_n}/{total_steps}] {label}")

    inp_file: Optional[Path] = None

    # ================================================================
    # 阶段 1：划网格（仅几何文件）
    # ================================================================
    if needs_mesh:
        if not check_gmsh():
            err_console.print(
                "\n  未找到 gmsh，无法自动划网格\n"
                "  请运行: [bold]pip install gmsh[/bold]\n"
                "  或者先在 CAD 软件中导出 .inp 文件，再用 cae solve\n"
            )
            raise typer.Exit(1)

        try:
            q = MeshQuality(quality.strip().lower())
        except ValueError:
            q = MeshQuality.MEDIUM

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"  [{1}/{total_steps}] 划分网格...",
                total=None,
            )
            mesh_result = mesh_geometry(
                model_file.resolve(),
                output,
                quality=q,
                output_format=".inp",
            )
            progress.update(task, completed=True)

        if not mesh_result.success:
            console.print(f"  网格划分失败: {mesh_result.error}\n")
            raise typer.Exit(1)

        console.print(
            f"  网格完成  "
            f"节点: {mesh_result.node_count}  "
            f"单元: {mesh_result.element_count}  "
            f"耗时: {mesh_result.duration_str}"
        )
        inp_file = mesh_result.inp_file
        step_n = 1

    else:
        inp_file = model_file.resolve()

    # ================================================================
    # 阶段 2：求解
    # ================================================================
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"  [{step_n+1}/{total_steps}] 求解中...",
            total=None,
        )
        solve_result = solver_instance.solve(inp_file, output, timeout=timeout)
        progress.update(task, completed=True)

    if not solve_result.success:
        console.print(f"  求解失败: {solve_result.error_message}\n")
        raise typer.Exit(1)

    console.print(
        f"  求解完成  耗时: {solve_result.duration_str}"
    )
    step_n += 1

    # ================================================================
    # 阶段 3：生成可视化
    # ================================================================
    vtu_file: Optional[Path] = None
    if solve_result.frd_file:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"  [{step_n+1}/{total_steps}] 生成可视化...",
                total=None,
            )
            vtk_result = frd_to_vtu(solve_result.frd_file, output)
            progress.update(task, completed=True)

        if vtk_result.success:
            console.print(f"  可视化文件生成完成")
            vtu_file = vtk_result.vtu_file
        else:
            console.print(f"  VTK 转换失败: {vtk_result.error}")

    # ================================================================
    # 完成摘要
    # ================================================================
    console.print()
    console.print(Panel(
        f"[bold green]全流程完成！[/bold green]",
        border_style="green",
        expand=False,
    ))
    console.print()

    if vtu_file and not no_view:
        console.print(f"  查看结果: [bold]`cae view {output}`[/bold]")
    if solve_result.warnings:
        console.print(f"  警告: {len(solve_result.warnings)} 条 — 运行 `cae diagnose` 查看")
    console.print(f"\n  输入 [bold]`cae explain {output}`[/bold] 让 AI 解读结果\n")

    # 自动启动浏览器
    if not no_view and vtu_file:
        _launch_viewer = typer.confirm("  现在打开结果查看器？", default=True)
        if _launch_viewer:
            from cae.viewer.server import start_server
            try:
                server, url, files = start_server(output, open_browser=True, auto_convert=False)
                console.print(f"\n  可视化: [bold cyan]{url}[/bold cyan]  (Ctrl+C 退出)\n")
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    server.shutdown()
                    console.print("\n  服务已停止\n")
            except Exception as exc:
                console.print(f"  无法启动查看器: {exc}\n")


@app.command()
def mesh(
    geo_file: Optional[Path] = typer.Argument(
        None,
        help="几何文件路径（.step / .brep / .iges / .geo）",
        show_default=False,
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="网格输出目录（默认 results/<name>/）",
    ),
    quality: str = typer.Option(
        "medium", "--quality", "-q",
        help="网格精度 [coarse/medium/fine]",
    ),
    fmt: str = typer.Option(
        "inp", "--format", "-f",
        help="输出格式 [inp/msh/vtu]",
    ),
    order: int = typer.Option(
        1, "--order",
        help="单元阶次（1=线性, 2=二次）",
    ),
    no_optimize: bool = typer.Option(
        False, "--no-optimize",
        help="跳过网格质量优化",
    ),
) -> None:
    """
    [bold]交互式网格划分[/bold]（Gmsh）

    \b
    示例：
      cae mesh bracket.step
      cae mesh bracket.step --quality fine --format inp
      cae mesh                （纯交互模式）
    """
    from cae.mesh.gmsh_runner import (
        MeshQuality, mesh_geometry, check_gmsh, get_gmsh_version,
        SUPPORTED_GEO_FORMATS,
    )

    console.print()
    console.print(Panel.fit(
        "[bold cyan]cae mesh[/bold cyan] — 网格划分（Gmsh）",
        border_style="cyan",
    ))
    console.print()

    # ---- 检查 Gmsh ----
    if not check_gmsh():
        err_console.print(
            "\n  未找到 gmsh\n"
            "  请运行: [bold]pip install gmsh[/bold]\n"
        )
        raise typer.Exit(1)

    gmsh_ver = get_gmsh_version()
    console.print(f"  Gmsh 版本: [green]{gmsh_ver}[/green]")
    console.print()

    # ---- 交互式获取几何文件 ----
    if geo_file is None:
        fmts = " / ".join(SUPPORTED_GEO_FORMATS.keys())
        raw = typer.prompt(f"  请输入几何文件路径 ({fmts})")
        geo_file = Path(raw.strip())

    if not geo_file.exists():
        err_console.print(f"\n  文件不存在: {geo_file}\n")
        raise typer.Exit(1)

    # ---- 交互式精度选择 ----
    quality_raw = typer.prompt(
        "  网格精度 [coarse/medium/fine]",
        default=quality,
    )
    try:
        q = MeshQuality(quality_raw.strip().lower())
    except ValueError:
        err_console.print(f"\n  无效精度 '{quality_raw}'，可选: coarse / medium / fine\n")
        raise typer.Exit(1)

    # ---- 输出目录 ----
    if output is None:
        default_out = settings.default_output_dir / geo_file.stem
        raw_out = typer.prompt("  输出目录", default=str(default_out))
        output = Path(raw_out.strip())

    out_ext = f".{fmt.lstrip('.')}"

    console.print()
    console.print(f"  输入几何: [cyan]{geo_file}[/cyan]")
    console.print(f"  精度:     [cyan]{q.label_cn}[/cyan] (lc_factor={q.lc_factor})")
    console.print(f"  输出格式: [cyan]{out_ext}[/cyan]")
    console.print(f"  输出目录: [cyan]{output}[/cyan]")
    console.print()

    # ---- 执行划分 ----
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  划分网格中...", total=None)
        result = mesh_geometry(
            geo_file.resolve(),
            output.resolve(),
            quality=q,
            output_format=out_ext,
            element_order=order,
            optimize=not no_optimize,
        )
        progress.update(task, completed=True)

    console.print()
    if result.success:
        console.print(Panel(
            f"[bold green]网格划分完成！[/bold green]  耗时 {result.duration_str}",
            border_style="green",
            expand=False,
        ))
        console.print()
        console.print(f"  节点数:   [bold]{result.node_count}[/bold]")
        console.print(f"  单元数:   [bold]{result.element_count}[/bold]")
        console.print(f"  输出文件: [cyan]{result.mesh_file}[/cyan]")

        if result.mesh_file and result.mesh_file.suffix == ".msh":
            console.print(
                f"\n  转换为 CalculiX 格式: "
                f"[bold]`cae convert {result.mesh_file} --to inp`[/bold]"
            )
        elif result.inp_file:
            console.print(
                f"\n  下一步求解: [bold]`cae solve {result.inp_file}`[/bold]"
            )
        console.print()
    else:
        console.print(Panel(
            f"[bold red]网格划分失败[/bold red]",
            border_style="red",
            expand=False,
        ))
        if result.error:
            console.print(f"\n  {result.error}\n")
        raise typer.Exit(1)


@app.command()
def view(
    results_dir: Optional[Path] = typer.Argument(
        None,
        help="包含 .vtu / .frd 文件的结果目录",
        show_default=False,
    ),
    port: int = typer.Option(8888, "--port", "-p", help="HTTP 服务端口"),
    no_browser: bool = typer.Option(False, "--no-browser", help="不自动打开浏览器"),
    no_convert: bool = typer.Option(False, "--no-convert", help="跳过 .frd → .vtu 自动转换"),
) -> None:
    """
    [bold]在浏览器中查看仿真结果[/bold]（ParaView Glance）

    \b
    示例：
      cae view results/bracket
      cae view results/ --port 9000
      cae view          （交互模式，提示输入路径）
    """
    from cae.viewer.server import start_server
    from cae.viewer.vtk_export import frd_to_vtu

    console.print()
    console.print(Panel.fit(
        "[bold cyan]cae view[/bold cyan] — 仿真结果可视化",
        border_style="cyan",
    ))
    console.print()

    # ---- 交互式获取目录 ----
    if results_dir is None:
        raw = typer.prompt("  请输入结果目录路径")
        results_dir = Path(raw.strip())

    if not results_dir.exists():
        err_console.print(f"\n  目录不存在: {results_dir}\n")
        raise typer.Exit(1)

    # ---- 检查 / 转换文件 ----
    vtu_files = list(results_dir.glob("*.vtu")) + list(results_dir.glob("*.vtk"))
    frd_files = list(results_dir.glob("*.frd"))

    if not vtu_files and not frd_files:
        err_console.print(
            f"\n  目录中没有 .vtu / .vtk / .frd 文件\n"
            f"  目录: {results_dir}\n"
            "  提示：先运行 [bold]`cae solve`[/bold] 生成结果\n"
        )
        raise typer.Exit(1)

    if not no_convert and frd_files and not vtu_files:
        console.print(f"  发现 [cyan]{len(frd_files)}[/cyan] 个 .frd 文件，正在转换为 VTK...")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            for frd in frd_files:
                task = progress.add_task(f"  转换 {frd.name}", total=None)
                result = frd_to_vtu(frd, results_dir)
                if result.success:
                    progress.update(task, description=f"  {frd.name}", completed=True)
                    console.print(
                        f"    节点: {result.node_count}  "
                        f"单元: {result.element_count}  "
                        f"字段: {', '.join(result.fields) or '-'}"
                    )
                else:
                    progress.update(task, description=f"  {frd.name}", completed=True)
                    err_console.print(f"    转换失败: {result.error}")
        console.print()
        vtu_files = list(results_dir.glob("*.vtu"))

    # ---- 启动服务器 ----
    try:
        server, url, files = start_server(
            results_dir,
            port=port,
            auto_convert=not no_convert,
            open_browser=not no_browser,
        )
    except FileNotFoundError as exc:
        err_console.print(f"\n  {exc}\n")
        raise typer.Exit(1)
    except RuntimeError as exc:
        err_console.print(f"\n  {exc}\n")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold green]可视化服务已启动[/bold green]\n\n"
        f"  URL : [bold cyan]{url}[/bold cyan]\n"
        f"  文件: {', '.join(f.name for f in files)}\n\n"
        f"  按 Ctrl+C 停止服务",
        border_style="green",
        expand=False,
    ))
    console.print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        console.print("\n  服务已停止\n")


@app.command()
def convert(
    frd_file: Optional[Path] = typer.Argument(
        None,
        help=".frd 结果文件路径",
        show_default=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="输出目录（默认与 .frd 同目录）",
    ),
) -> None:
    """
    [bold]手动将 .frd 结果转换为 .vtu[/bold]（供 ParaView / `cae view` 使用）

    \b
    示例：
      cae convert results/bracket.frd
      cae convert results/bracket.frd --output ./vtk_out
    """
    from cae.viewer.vtk_export import frd_to_vtu

    console.print()

    if frd_file is None:
        raw = typer.prompt("  请输入 .frd 文件路径")
        frd_file = Path(raw.strip())

    if not frd_file.exists():
        err_console.print(f"\n  文件不存在: {frd_file}\n")
        raise typer.Exit(1)

    out_dir = output or frd_file.parent
    console.print(f"  转换: [cyan]{frd_file.name}[/cyan] -> [cyan]{out_dir}[/cyan]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  转换中...", total=None)
        result = frd_to_vtu(frd_file, out_dir)
        progress.update(task, completed=True)

    console.print()
    if result.success:
        console.print(f"  转换完成：{result.vtu_file}")
        console.print(f"     节点: {result.node_count}  单元: {result.element_count}")
        if result.fields:
            console.print(f"     字段: {', '.join(result.fields)}")
        console.print(f"\n  查看: [bold]`cae view {out_dir}`[/bold]\n")
    else:
        err_console.print(f"\n  转换失败: {result.error}\n")
        raise typer.Exit(1)


@app.command()
def install(
    solver_only: bool = typer.Option(False, "--solver-only", help="只安装 CalculiX"),
    model_only:  bool = typer.Option(False, "--model-only",  help="只安装默认 AI 模型"),
    model_name:  str  = typer.Option("deepseek-r1-7b", "--model", help="指定模型名称"),
) -> None:
    """
    [bold]下载并安装 CalculiX 求解器 + AI 模型[/bold]

    \b
    示例：
      cae install                        # 全部安装
      cae install --solver-only          # 只装求解器
      cae install --model deepseek-r1-14b
    """
    from cae.installer.solver_installer import SolverInstaller
    from cae.installer.model_installer import ModelInstaller

    console.print()
    console.print(Panel.fit("[bold cyan]cae install[/bold cyan] — 安装求解器与 AI 模型", border_style="cyan"))
    console.print()

    # ---- 安装 CalculiX ----
    if not model_only:
        console.print("  [bold]安装 CalculiX 求解器[/bold]")
        installer = SolverInstaller()

        if installer.is_installed():
            console.print("  CalculiX 已安装\n")
        else:
            with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                          TimeElapsedColumn(), console=console) as progress:
                task = progress.add_task("  下载中...", total=None)

                def _solver_progress(pct: float, msg: str) -> None:
                    progress.update(task, description=f"  {msg}")

                result = installer.install(progress_callback=_solver_progress)

            if result.success:
                console.print(f"  CalculiX 安装成功  方式: {result.method}\n")
            else:
                console.print(f"  CalculiX 安装失败\n  {result.error_message}\n")

    # ---- 安装 AI 模型 ----
    if not solver_only:
        console.print("  [bold]安装 AI 模型[/bold]")
        mi = ModelInstaller()

        if mi.is_installed(model_name):
            console.print(f"  模型已安装: {model_name}\n")
            mi.activate(model_name)
        else:
            from cae.installer.model_installer import KNOWN_MODELS
            meta = KNOWN_MODELS.get(model_name, {})
            size = meta.get("size_gb", "?")
            console.print(f"  模型: [cyan]{model_name}[/cyan]  大小: ~{size} GB")
            console.print("  这可能需要几分钟，取决于网络速度...\n")

            with Progress(SpinnerColumn(), TextColumn("{task.description}"),
                          TimeElapsedColumn(), console=console) as progress:
                task = progress.add_task("  下载中...", total=None)

                def _model_progress(pct: float, msg: str) -> None:
                    progress.update(task, description=f"  {msg}")

                result = mi.install(model_name, progress_callback=_model_progress)

            if result.success:
                console.print(f"  模型安装成功: {model_name}\n")
            else:
                console.print(f"  模型安装失败\n  {result.error_message}\n")

    console.print("  现在可以运行 [bold]`cae solve`[/bold] 开始仿真\n")


@app.command()
def explain(
    results_dir: Optional[Path] = typer.Argument(None, help="结果目录"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="流式输出"),
) -> None:
    """[bold]AI 解读仿真结果[/bold]"""
    from cae.ai.explain import explain_results
    from cae.ai.llm_client import LLMClient

    console.print()
    console.print(Panel.fit("[bold cyan]cae explain[/bold cyan] — AI 结果解读", border_style="cyan"))
    console.print()

    if results_dir is None:
        raw = typer.prompt("  请输入结果目录路径")
        results_dir = Path(raw.strip())

    client = LLMClient()
    if not client.is_running():
        console.print("  llama-server 未运行，尝试自动启动...")
        if not client.start_server():
            err_console.print(
                "\n  无法启动 AI 服务。请先运行 [bold]`cae install`[/bold] 安装模型。\n"
            )
            raise typer.Exit(1)

    console.print("  AI 正在分析，请稍候...\n")
    result = explain_results(results_dir, client, stream=stream)

    if not result.success:
        err_console.print(f"\n  {result.error}\n")
        raise typer.Exit(1)

    if not stream:
        console.print(Panel(result.summary, title="AI 解读", border_style="green"))
    console.print()


@app.command()
def diagnose(
    results_dir: Optional[Path] = typer.Argument(None, help="结果目录"),
    no_ai: bool = typer.Option(False, "--no-ai", help="只做规则检测，跳过 AI"),
    stream: bool = typer.Option(True, "--stream/--no-stream"),
) -> None:
    """[bold]AI 诊断仿真问题[/bold]"""
    from cae.ai.diagnose import diagnose_results
    from cae.ai.llm_client import LLMClient

    console.print()
    console.print(Panel.fit("[bold cyan]cae diagnose[/bold cyan] — AI 问题诊断", border_style="cyan"))
    console.print()

    if results_dir is None:
        raw = typer.prompt("  请输入结果目录路径")
        results_dir = Path(raw.strip())

    client = None
    if not no_ai:
        client = LLMClient()
        if not client.is_running():
            console.print("  llama-server 未运行，仅执行规则检测\n")
            client = None

    result = diagnose_results(results_dir, client, stream=stream)

    if not result.success:
        err_console.print(f"\n  {result.error}\n")
        raise typer.Exit(1)

    # 显示规则检测结果
    if result.issues:
        console.print(f"  规则检测：发现 {result.issue_count} 个问题")
        for iss in result.issues[:10]:
            icon = "X" if iss.severity == "error" else "!"
            console.print(f"  [{icon}] [{iss.category}] {iss.message[:80]}")
            if iss.suggestion:
                console.print(f"     -> {iss.suggestion}")
        console.print()
    else:
        console.print("  规则检测未发现明显问题\n")

    if result.ai_diagnosis and not stream:
        console.print(Panel(result.ai_diagnosis, title="AI 诊断", border_style="yellow"))

    console.print()


# ------------------------------------------------------------------ #
# 工具函数
# ------------------------------------------------------------------ #

def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


# ------------------------------------------------------------------ #
# 入口
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    app()
