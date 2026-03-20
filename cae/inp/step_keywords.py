"""
Step Keywords 载荷步关键词模块

提供 Step 内使用的载荷、边界条件等关键词类。

类层次：
  Cload    # 集中载荷
  Dload    # 分布载荷
  Boundary # 边界条件

参考 pygccx step_keywords/cload.py, dload.py, boundary.py 设计
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Any, Union

from cae.enums import LoadOp, DloadType
from cae._utils import f2s


@dataclass
class Cload:
    """
    集中载荷（CLOAD）。

    在节点上施加集中力或集中位移。

    Args:
        node_ids: 节点 ID 集合或单个节点 ID
        dofs: 自由度字典，key=DOF编号(1-6)，value=幅值
            例如：{3: 1.0} 表示 z 方向 1.0
        op: 操作选项（MOD=修改，NEW=新建）
        amplitude_name: 幅值名称
        time_delay: 时间延迟
        name: 载荷名称
        desc: 描述文本

    Example:
        >>> # 节点 1,2,3 的 z 方向施加 1.0
        >>> c = Cload(node_ids={1, 2, 3}, dofs={3: 1.0})
        >>> # 多个方向
        >>> c = Cload(node_ids=100, dofs={1: 10.0, 2: -5.0, 6: 0.5})
    """

    node_ids: Union[set[int], int]
    """节点 ID 集合或单个节点 ID"""
    dofs: dict[int, float]
    """自由度字典，key=DOF编号，value=幅值"""
    op: LoadOp = LoadOp.MOD
    """操作选项"""
    amplitude_name: Optional[str] = None
    """幅值名称"""
    time_delay: Optional[float] = None
    """时间延迟"""
    name: str = ""
    """载荷名称"""
    desc: str = ""

    def to_inp_lines(self) -> list[str]:
        """转换为 INP 文件行。"""
        lines = []

        # CLOAD 行
        line = "*CLOAD"
        if self.op != LoadOp.MOD:
            line += f",OP={self.op.value}"
        if self.amplitude_name:
            line += f",AMPLITUDE={self.amplitude_name}"
        if self.time_delay is not None:
            line += f",TIME DELAY={f2s(self.time_delay)}"
        lines.append(line)
        if self.desc:
            lines.append(f"** {self.desc}")

        # 载荷行
        if isinstance(self.node_ids, set):
            nid_list = sorted(self.node_ids)
        elif isinstance(self.node_ids, (list, tuple)):
            nid_list = self.node_ids
        else:
            nid_list = [self.node_ids]

        for nid in nid_list:
            for dof in sorted(self.dofs.keys()):
                mag = self.dofs[dof]
                lines.append(f"{nid},{dof},{f2s(mag)}")

        return lines

    def __str__(self) -> str:
        return "\n".join(self.to_inp_lines())


@dataclass
class Dload:
    """
    分布载荷（DLOAD）。

    在单元或单元集上施加分布载荷。

    Args:
        elset_name: 单元集名称（用于标识施加载荷的区域）
        load_type: 分布载荷类型（GRAV/CENTRIF/NEWTON/P1-P6）
        magnitude: 载荷参数
            - GRAV: (grav_factor, dir_x, dir_y, dir_z)
            - CENTRIF: (omega_sq, point_x, point_y, point_z, dir_x, dir_y, dir_z)
            - NEWTON: 无参数
            - P1-P6: pressure_value
        op: 操作选项
        amplitude_name: 幅值名称
        time_delay: 时间延迟
        name: 载荷名称
        desc: 描述文本

    Example:
        >>> # 重力载荷
        >>> d = Dload(elset_name='EALL', load_type=DloadType.GRAV,
        ...           magnitude=(9.81, 0, 0, -1))
        >>> # 离心力
        >>> d = Dload(elset_name='ROTOR', load_type=DloadType.CENTRIF,
        ...           magnitude=(1000, 0, 0, 0, 0, 0, 1))
        >>> # 面载荷
        >>> d = Dload(elset_name='FACE_SURF', load_type=DloadType.P2,
        ...           magnitude=(-1.0))  # 压力值
    """

    elset_name: str
    """单元集名称"""
    load_type: DloadType
    """分布载荷类型"""
    magnitude: tuple[float, ...]
    """载荷参数（取决于 load_type）"""
    op: LoadOp = LoadOp.MOD
    """操作选项"""
    amplitude_name: Optional[str] = None
    """幅值名称"""
    time_delay: Optional[float] = None
    """时间延迟"""
    name: str = ""
    """载荷名称"""
    desc: str = ""

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if self.time_delay is not None and self.amplitude_name is None:
            raise ValueError("amplitude_name 不能为 None when time_delay is set")

        lt = self.load_type
        mag = self.magnitude

        if lt == DloadType.NEWTON:
            if len(mag) != 0:
                raise ValueError("NEWTON 类型不需要 magnitude 参数")
        elif lt == DloadType.GRAV:
            if len(mag) != 4:
                raise ValueError("GRAV 类型需要 4 个参数 (factor, dx, dy, dz)")
            # 检查方向向量是否归一化
            vector = mag[1:]
            norm_sq = sum(v * v for v in vector)
            if abs(norm_sq - 1.0) > 1e-7:
                raise ValueError(f"GRAV 方向向量必须归一化，当前 norm={norm_sq**0.5}")
        elif lt == DloadType.CENTRIF:
            if len(mag) != 7:
                raise ValueError("CENTRIF 类型需要 7 个参数")
            # 检查旋转轴向量是否归一化
            vector = mag[4:]
            norm_sq = sum(v * v for v in vector)
            if abs(norm_sq - 1.0) > 1e-7:
                raise ValueError(f"CENTRIF 旋转轴向量必须归一化")
        elif lt in (DloadType.P1, DloadType.P2, DloadType.P3,
                    DloadType.P4, DloadType.P5, DloadType.P6):
            if len(mag) != 1:
                raise ValueError(f"Px 类型需要 1 个参数（压力值），当前 {len(mag)} 个")

    def to_inp_lines(self) -> list[str]:
        """转换为 INP 文件行。"""
        lines = []

        # DLOAD 行
        line = "*DLOAD"
        if self.op != LoadOp.MOD:
            line += f",OP={self.op.value}"
        if self.amplitude_name:
            line += f",AMPLITUDE={self.amplitude_name}"
        if self.time_delay is not None:
            line += f",TIME DELAY={f2s(self.time_delay)}"
        lines.append(line)
        if self.desc:
            lines.append(f"** {self.desc}")

        # 载荷行
        line = f"{self.elset_name},{self.load_type.value}"
        if self.load_type != DloadType.NEWTON:
            line += "," + ",".join(f2s(v) for v in self.magnitude)
        lines.append(line)

        return lines

    def __str__(self) -> str:
        return "\n".join(self.to_inp_lines())


@dataclass
class Boundary:
    """
    边界条件（BOUNDARY）。

    施加位移约束或速度/加速度边界条件。

    Args:
        node_ids: 节点 ID 集合或单个节点 ID
        dofs: 边界条件字典
            - 固定: key=DOF编号, value=None
            - 给定值: key=DOF编号, value=数值
            DOF: 1-6 = UX, UY, UZ, ROTX, ROTY, ROTZ
        op: 操作选项
        amplitude_name: 幅值名称
        time_delay: 时间延迟
        fixed: 是否冻结前一步变形
        submodel: 是否为子模型
        step: 子模型步选择
        data_set: 子模型数据集选择
        name: 边界条件名称
        desc: 描述文本

    Example:
        >>> # 完全固定
        >>> b = Boundary(node_ids={1, 2, 3}, dofs={1: None, 2: None, 3: None})
        >>> # 固定 + 给定位移
        >>> b = Boundary(node_ids=100, dofs={1: 0, 2: 0, 3: 0.1})  # z 方向 0.1
        >>> # 仅固定某些方向
        >>> b = Boundary(node_ids='NSET_FIXED', dofs={3: None})  # z 方向固定
    """

    node_ids: Union[set[int], int, str]
    """节点 ID 集合、单节点 ID 或节点集名称字符串"""
    dofs: dict[int, Optional[float]]
    """自由度字典，key=DOF编号(1-6)，value=None(固定)或数值"""
    op: LoadOp = LoadOp.MOD
    """操作选项"""
    amplitude_name: Optional[str] = None
    """幅值名称"""
    time_delay: Optional[float] = None
    """时间延迟"""
    fixed: bool = False
    """是否冻结前一步变形"""
    submodel: bool = False
    """是否为子模型"""
    step: Optional[int] = None
    """子模型步选择"""
    data_set: Optional[int] = None
    """子模型数据集选择"""
    name: str = ""
    """边界条件名称"""
    desc: str = ""

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        if self.time_delay is not None and self.amplitude_name is None:
            raise ValueError("amplitude_name 不能为 None when time_delay is set")
        if self.submodel and self.amplitude_name is not None:
            raise ValueError("submodel 和 amplitude_name 不能同时设置")
        if self.submodel and self.step is None and self.data_set is None:
            raise ValueError("submodel=True 时必须指定 step 或 data_set")
        if not self.submodel and self.step is not None:
            raise ValueError("submodel=False 时 step 必须为 None")
        if not self.submodel and self.data_set is not None:
            raise ValueError("submodel=False 时 data_set 必须为 None")
        if self.step is not None and self.data_set is not None:
            raise ValueError("step 和 data_set 不能同时设置")

    def to_inp_lines(self) -> list[str]:
        """转换为 INP 文件行。"""
        lines = []

        # BOUNDARY 行
        line = "*BOUNDARY"
        if self.op != LoadOp.MOD:
            line += f",OP={self.op.value}"
        if self.amplitude_name:
            line += f",AMPLITUDE={self.amplitude_name}"
        if self.time_delay is not None:
            line += f",TIME DELAY={f2s(self.time_delay)}"
        if self.fixed:
            line += ",FIXED"
        if self.submodel:
            line += ",SUBMODEL"
            if self.step is not None:
                line += f",STEP={self.step}"
            if self.data_set is not None:
                line += f",DATA SET={self.data_set}"
        lines.append(line)
        if self.desc:
            lines.append(f"** {self.desc}")

        # 边界条件行
        if isinstance(self.node_ids, str):
            # 节点集名称
            nid_list = [self.node_ids]
        elif isinstance(self.node_ids, set):
            nid_list = sorted(self.node_ids)
        elif isinstance(self.node_ids, (list, tuple)):
            nid_list = self.node_ids
        else:
            nid_list = [self.node_ids]

        for nid in nid_list:
            for dof in sorted(self.dofs.keys()):
                val = self.dofs[dof]
                if val is None:
                    lines.append(f"{nid},{dof}")
                else:
                    lines.append(f"{nid},{dof},{f2s(val)}")

        return lines

    def __str__(self) -> str:
        return "\n".join(self.to_inp_lines())
