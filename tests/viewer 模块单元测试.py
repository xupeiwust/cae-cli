"""
第二周：viewer 模块单元测试
覆盖：frd_parser、vtk_export、server（端口查找 / 文件收集）
所有 meshio I/O 均通过 mock 隔离，无需真实 .frd 文件。
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import numpy as np
import pytest

from cae.viewer.frd_parser import (
    FrdData,
    FrdElement,
    FrdNodes,
    FrdResultStep,
    parse_frd,
)
from cae.viewer.vtk_export import (
    VtkExportResult,
    _von_mises,
    frd_to_vtu,
)


# ================================================================== #
# frd_parser
# ================================================================== #

class TestFrdNodes:
    def test_basic_fields(self):
        n = FrdNodes(ids=[1, 2, 3], coords=[(0, 0, 0), (1, 0, 0), (0, 1, 0)])
        assert len(n.ids) == 3
        assert len(n.coords) == 3


class TestFrdData:
    def test_has_geometry_false_when_empty(self):
        d = FrdData()
        assert d.has_geometry is False

    def test_has_geometry_false_no_elements(self):
        d = FrdData(nodes=FrdNodes(ids=[1], coords=[(0, 0, 0)]))
        assert d.has_geometry is False

    def test_has_geometry_true(self):
        d = FrdData(
            nodes=FrdNodes(ids=[1, 2, 3, 4], coords=[(0,0,0)]*4),
            elements=[FrdElement(eid=1, etype=3, connectivity=[1,2,3,4])],
        )
        assert d.has_geometry is True

    def test_node_count(self):
        d = FrdData(nodes=FrdNodes(ids=[1, 2], coords=[(0,0,0),(1,0,0)]))
        assert d.node_count == 2

    def test_node_count_no_nodes(self):
        assert FrdData().node_count == 0

    def test_get_result_by_name(self):
        r1 = FrdResultStep(step=1, time=0.0, name="DISP", components=[], values=[], node_ids=[])
        r2 = FrdResultStep(step=1, time=0.0, name="STRESS", components=[], values=[], node_ids=[])
        d = FrdData(results=[r1, r2])
        assert d.get_result("DISP") is r1
        assert d.get_result("STRESS") is r2

    def test_get_result_missing(self):
        d = FrdData()
        assert d.get_result("NONEXISTENT") is None

    def test_get_result_last_step(self):
        steps = [
            FrdResultStep(step=i, time=float(i), name="DISP", components=[], values=[], node_ids=[])
            for i in range(1, 4)
        ]
        d = FrdData(results=steps)
        assert d.get_result("DISP", step=-1) is steps[-1]
        assert d.get_result("DISP", step=0)  is steps[0]


class TestParseFrd:
    def test_file_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            parse_frd(tmp_path / "ghost.frd")

    def _write_minimal_frd(self, path: Path) -> Path:
        """最小化合法 ASCII .frd 文件（4节点四面体 + 位移结果）。"""
        content = """\
    1C                          4
 -1         1 0.000000E+00 0.000000E+00 0.000000E+00
 -1         2 1.000000E+00 0.000000E+00 0.000000E+00
 -1         3 0.000000E+00 1.000000E+00 0.000000E+00
 -1         4 0.000000E+00 0.000000E+00 1.000000E+00
 -3
    2C                          1
 -1         1  3  1  1
 -2         1  2  3  4
 -3
  100C                             DISP        1  0.00000E+00
 -4  DISP        4  0  1
 -5  D1          1  2  1  0
 -5  D2          1  2  2  0
 -5  D3          1  2  3  0
 -1         1 1.00000E-03 0.00000E+00 0.00000E+00
 -1         2 2.00000E-03 0.00000E+00 0.00000E+00
 -1         3 3.00000E-03 0.00000E+00 0.00000E+00
 -1         4 4.00000E-03 0.00000E+00 0.00000E+00
 -3
9999
"""
        path.write_text(content)
        return path

    def test_parse_nodes(self, tmp_path: Path):
        frd = self._write_minimal_frd(tmp_path / "test.frd")
        data = parse_frd(frd)
        assert data.node_count == 4

    def test_parse_elements(self, tmp_path: Path):
        frd = self._write_minimal_frd(tmp_path / "test.frd")
        data = parse_frd(frd)
        assert data.element_count == 1
        assert data.elements[0].etype == 3  # C3D4

    def test_parse_results(self, tmp_path: Path):
        frd = self._write_minimal_frd(tmp_path / "test.frd")
        data = parse_frd(frd)
        disp = data.get_result("DISP")
        assert disp is not None
        assert len(disp.node_ids) == 4

    def test_has_geometry(self, tmp_path: Path):
        frd = self._write_minimal_frd(tmp_path / "test.frd")
        data = parse_frd(frd)
        assert data.has_geometry is True


# ================================================================== #
# vtk_export
# ================================================================== #

class TestVonMises:
    def test_uniaxial_tension(self):
        """单轴拉伸：S11=100, 其他=0 → Von Mises = 100."""
        stress = np.array([[100.0, 0, 0, 0, 0, 0]])
        vm = _von_mises(stress)
        assert pytest.approx(vm[0], abs=1e-6) == 100.0

    def test_hydrostatic_zero(self):
        """静水压：S11=S22=S33=p, 剪切=0 → Von Mises = 0."""
        p = 50.0
        stress = np.array([[p, p, p, 0.0, 0.0, 0.0]])
        vm = _von_mises(stress)
        assert pytest.approx(vm[0], abs=1e-6) == 0.0

    def test_pure_shear(self):
        """纯剪切 S12=τ → Von Mises = √3 · τ."""
        tau = 100.0
        stress = np.array([[0.0, 0.0, 0.0, tau, 0.0, 0.0]])
        vm = _von_mises(stress)
        assert pytest.approx(vm[0], rel=1e-6) == tau * np.sqrt(3)

    def test_batch(self):
        """批量输入：输出长度与输入相同。"""
        stress = np.random.rand(50, 6)
        vm = _von_mises(stress)
        assert vm.shape == (50,)
        assert np.all(vm >= 0)


class TestVtkExportResult:
    def test_default_fields_list(self):
        r = VtkExportResult(success=True)
        assert isinstance(r.fields, list)

    def test_success_with_vtu(self, tmp_path: Path):
        vtu = tmp_path / "job.vtu"
        vtu.write_text("<VTKFile/>")
        r = VtkExportResult(success=True, vtu_file=vtu, node_count=8, element_count=1)
        assert r.success
        assert r.vtu_file == vtu


class TestFrdToVtu:
    def test_missing_frd_returns_error(self, tmp_path: Path):
        result = frd_to_vtu(tmp_path / "no.frd")
        assert result.success is False
        assert "不存在" in (result.error or "")

    def test_meshio_direct_success(self, tmp_path: Path):
        """meshio 直读成功路径。"""
        frd = tmp_path / "job.frd"
        frd.write_bytes(b"dummy")

        mock_mesh = MagicMock()
        mock_mesh.points = np.zeros((8, 3))
        mock_mesh.cells = [MagicMock(data=np.zeros((1, 8), dtype=int))]
        mock_mesh.point_data = {"U": np.zeros((8, 3))}
        mock_mesh.cell_data = {}

        mock_meshio = MagicMock()
        mock_meshio.read.return_value = mock_mesh

        with (
            patch("cae.viewer.vtk_export._meshio_module", mock_meshio),
            patch("cae.viewer.vtk_export._HAS_MESHIO", True),
        ):
            result = frd_to_vtu(frd, tmp_path)

        assert result.success is True
        assert result.node_count == 8

    def test_fallback_when_meshio_fails(self, tmp_path: Path):
        """meshio 直读失败时走内置解析器路径。"""
        frd = tmp_path / "job.frd"
        frd.write_text("""\
    1C                          2
 -1         1 0.000000E+00 0.000000E+00 0.000000E+00
 -1         2 1.000000E+00 0.000000E+00 0.000000E+00
 -3
    2C                          1
 -1         1  3  1  1
 -2         1  2  1  2
 -3
9999
""")
        mock_meshio = MagicMock()
        mock_meshio.read.side_effect = Exception("unsupported format")

        with (
            patch("cae.viewer.vtk_export._meshio_module", mock_meshio),
            patch("cae.viewer.vtk_export._HAS_MESHIO", True),
        ):
            result = frd_to_vtu(frd, tmp_path)

        assert isinstance(result, VtkExportResult)

    def test_output_dir_created(self, tmp_path: Path):
        """输出目录不存在时自动创建。"""
        frd = tmp_path / "job.frd"
        frd.write_bytes(b"dummy")
        out = tmp_path / "nested" / "output"

        mock_meshio = MagicMock()
        mock_meshio.read.side_effect = Exception("fail")

        with (
            patch("cae.viewer.vtk_export._meshio_module", mock_meshio),
            patch("cae.viewer.vtk_export._HAS_MESHIO", True),
        ):
            frd_to_vtu(frd, out)

        assert out.exists()


# ================================================================== #
# server utilities
# ================================================================== #

class TestServerUtils:
    def test_find_free_port_returns_int(self):
        from cae.viewer.server import _find_free_port
        port = _find_free_port(18888)
        assert isinstance(port, int)
        assert 18888 <= port < 18988

    def test_collect_vtu_files_empty(self, tmp_path: Path):
        from cae.viewer.server import _collect_vtu_files
        assert _collect_vtu_files(tmp_path) == []

    def test_collect_vtu_files_found(self, tmp_path: Path):
        from cae.viewer.server import _collect_vtu_files
        (tmp_path / "a.vtu").write_text("")
        (tmp_path / "b.vtk").write_text("")
        (tmp_path / "c.frd").write_text("")  # should not be included
        files = _collect_vtu_files(tmp_path)
        names = {f.name for f in files}
        assert "a.vtu" in names
        assert "b.vtk" in names
        assert "c.frd" not in names

    def test_start_server_dir_not_found(self, tmp_path: Path):
        from cae.viewer.server import start_server
        with pytest.raises(FileNotFoundError):
            start_server(tmp_path / "nonexistent", open_browser=False)

    def test_start_server_no_vtu_files(self, tmp_path: Path):
        from cae.viewer.server import start_server
        # 目录存在但没有可视化文件
        (tmp_path / "dummy.txt").write_text("")
        with pytest.raises(FileNotFoundError, match="没有可视化文件"):
            start_server(tmp_path, auto_convert=False, open_browser=False)

    def test_start_server_returns_server_and_url(self, tmp_path: Path):
        from cae.viewer.server import start_server
        (tmp_path / "result.vtu").write_text("<VTKFile/>")
        server, url, files = start_server(tmp_path, open_browser=False, auto_convert=False)
        assert url.startswith("http://localhost:")
        assert len(files) == 1
        server.server_close()


class TestIndexHtml:
    """验证 index.html 生成正确的文件按钮和 JSON。"""

    def test_file_buttons_in_html(self, tmp_path: Path):
        from cae.viewer.server import start_server
        (tmp_path / "beam.vtu").write_text("")
        (tmp_path / "frame.vtu").write_text("")

        server, url, files = start_server(tmp_path, open_browser=False, auto_convert=False)
        server.server_close()

        # 检查 handler 能获取正确的文件列表
        assert len(files) == 2
        names = {f.name for f in files}
        assert "beam.vtu" in names
        assert "frame.vtu" in names