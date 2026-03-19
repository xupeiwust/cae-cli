"""
Inp 模块 — Abaqus/CalculiX .inp 文件解析与修改

基于 cae-master 的 Block 解析思路，支持：
  - 解析 .inp 文件为 Block 列表
  - 按关键词/名称精确定位修改
  - 保留原始格式（注释、空行）重新生成

关键词定义来源：kw_list.json（从 cae-master kw_list.xml 转换）
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

__all__ = [
    "Block",
    "InpParser",
    "InpModifier",
    "load_kw_list",
]

# ------------------------------------------------------------------ #
# 数据结构
# ------------------------------------------------------------------ #

# 懒加载 kw_list
_kw_list: Optional[dict] = None


def load_kw_list() -> dict:
    """加载关键词定义列表（kw_list.json）。"""
    global _kw_list
    if _kw_list is None:
        kw_path = Path(__file__).parent / "kw_list.json"
        with open(kw_path, encoding="utf-8") as f:
            _kw_list = json.load(f)
    return _kw_list


@dataclass
class Block:
    """
    关键词块，保留原始 INP 文本。

    Attributes:
        keyword_name: 关键词名称，如 "*BOUNDARY", "*STEP"
        comments: 注释行列表（含 "**" 前缀）
        lead_line: 关键词定义行（含参数）
        data_lines: 数据行列表
    """

    keyword_name: str
    comments: list[str] = field(default_factory=list)
    lead_line: str = ""
    data_lines: list[str] = field(default_factory=list)

    # 解析后的参数 {参数名: 值}
    _params: dict[str, str] = field(default_factory=dict, repr=False)

    def get_inp_code(self) -> list[str]:
        """重新生成 INP 代码行。"""
        lines = []
        lines.extend(self.comments)
        lines.append(self.lead_line)
        lines.extend(self.data_lines)
        return lines

    def get_param(self, name: str) -> Optional[str]:
        """获取关键词参数值（不区分大小写）。"""
        return self._params.get(name.upper())

    def set_param(self, name: str, value: str) -> None:
        """设置关键词参数值。"""
        # 修改 lead_line 中的参数
        name_upper = name.upper()
        # 匹配 NAME=value 或 NAME= value 或 NAME value
        pattern = rf"({re.escape(name)})[\s=].*?(?=,|\s*?$|\*)"
        if re.search(pattern, self.lead_line, re.IGNORECASE):
            self.lead_line = re.sub(
                pattern,
                f"{name}={value}",
                self.lead_line,
                flags=re.IGNORECASE,
            )
        else:
            # 参数不存在，追加到 lead_line 末尾
            sep = "," if not self.lead_line.rstrip().endswith(",") else ""
            self.lead_line = f"{self.lead_line}{sep} {name}={value}"
        self._params[name_upper] = value

    def update_data_line(self, index: int, new_line: str) -> None:
        """更新指定索引的数据行。"""
        if 0 <= index < len(self.data_lines):
            self.data_lines[index] = new_line


# ------------------------------------------------------------------ #
# 解析器
# ------------------------------------------------------------------ #

# 关键词行匹配：*KEYWORD 或 *KEYWORD,param1=value,param2=value
_KEYWORD_RE = re.compile(r"^\*[\w\s-]+")


class InpParser:
    """
    .inp 文件解析器。

    解析流程：
      1. read_lines()       — 递归读取文件（含 *INCLUDE）
      2. split_on_blocks()  — 分割为 Block 列表
      3. parse_params()      — 解析每块的关键词参数

    Usage:
        parser = InpParser()
        blocks = parser.parse("model.inp")
        for block in blocks:
            print(block.keyword_name, block.get_param("NAME"))
    """

    def __init__(self):
        self.keyword_blocks: list[Block] = []

    def parse(self, inp_file: Path) -> list[Block]:
        """解析 .inp 文件，返回 Block 列表。"""
        if not inp_file.exists():
            raise FileNotFoundError(f"文件不存在: {inp_file}")

        inp_doc = self._read_lines(inp_file)
        self.split_on_blocks(inp_doc)
        for block in self.keyword_blocks:
            self._parse_params(block)
        return self.keyword_blocks

    def parse_string(self, inp_text: str) -> list[Block]:
        """解析 INP 文本字符串。"""
        inp_doc = inp_text.splitlines()
        self.split_on_blocks(inp_doc)
        for block in self.keyword_blocks:
            self._parse_params(block)
        return self.keyword_blocks

    def _read_lines(self, inp_file: Path) -> list[str]:
        """递归读取 INP 文件及 *INCLUDE 文件。"""
        lines = []
        with open(inp_file, encoding="utf-8", errors="ignore") as f:
            for raw_line in f:
                line = raw_line.rstrip()
                lines.append(line)

                # 处理 *INCLUDE
                if re.match(r"^\s*\*INCLUDE", line, re.IGNORECASE):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        inc_path = Path(inp_file.parent) / parts[1].strip()
                        if inc_path.exists():
                            lines.extend(self._read_lines(inc_path))
        return lines

    def split_on_blocks(self, inp_doc: list[str]) -> None:
        """将 INP 文档分割为关键词块列表。"""
        self.keyword_blocks = []
        i = 0
        n = len(inp_doc)

        while i < n:
            match = _KEYWORD_RE.match(inp_doc[i])
            if match is not None:
                keyword_name = match.group(0).strip()

                # 前置注释
                comments = []
                counter = 0
                while i - counter - 1 >= 0 and inp_doc[i - counter - 1].startswith("**"):
                    counter += 1
                    comments.insert(0, inp_doc[i - counter])

                # Lead line（支持多行逗号续接）
                lead_line = inp_doc[i].rstrip()
                j = i + 1
                while lead_line.endswith(","):
                    if j >= n:
                        break
                    lead_line = lead_line + " " + inp_doc[j].rstrip()
                    j += 1

                i = j
                start = i

                # 数据行直到下一关键词
                while i < n:
                    if _KEYWORD_RE.match(inp_doc[i]):
                        i -= 1
                        break
                    i += 1

                end = i if i < n else n - 1
                if end < start:
                    end = start

                data_lines = inp_doc[start : end + 1]

                block = Block(
                    keyword_name=keyword_name.upper(),
                    comments=comments,
                    lead_line=lead_line,
                    data_lines=data_lines,
                )
                self.keyword_blocks.append(block)

            i += 1

    def _parse_params(self, block: Block) -> None:
        """从 lead_line 解析关键词参数，存入 block._params。"""
        # 去掉首尾空白，移除前导 *
        line = block.lead_line.strip().lstrip("*")
        # 去掉末尾逗号
        if line.endswith(","):
            line = line[:-1]

        # 按逗号分割
        parts = line.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # 查找 NAME=value 或 NAME=value, 模式
            eq_match = re.match(r"^([\w-]+)\s*=\s*(.*)$", part, re.IGNORECASE)
            if eq_match:
                key = eq_match.group(1).upper()
                val = eq_match.group(2).strip()
                block._params[key] = val


# ------------------------------------------------------------------ #
# 修改器
# ------------------------------------------------------------------ #

# 需要唯一名称的关键词
_NAME_KEYWORDS = {
    "*MATERIAL",
    "*STEP",
    "*BOUNDARY",
    "*LOAD",
    "*CLOAD",
    "*DLOAD",
    "*ELSET",
    "*NSET",
    "*SURFACE",
    "*AMPLITUDE",
    "*PART",
    "*ASSEMBLY",
    "*INSTANCE",
    "*SOLID SECTION",
    "*BEAM SECTION",
    "*SHELL SECTION",
    "*NODE",
    "*ELEMENT",
}


class InpModifier:
    """
    .inp 文件修改器。

    支持按关键词类型 + 参数条件精确定位修改，
    保留原始格式不变。

    Usage:
        mod = InpModifier("model.inp")
        # 修改材料名称
        mod.update_blocks(
            keyword="*MATERIAL",
            params={"NAME": "STEEL"},
            data_transformer=lambda lines: replace_values(lines, "E", 210000)
        )
        mod.write("model_modified.inp")
    """

    def __init__(self, inp_file: Optional[Path] = None):
        self.blocks: list[Block] = []
        self._source_text: list[str] = []
        if inp_file is not None:
            self.load(inp_file)

    def load(self, inp_file: Path) -> None:
        """加载 .inp 文件。"""
        parser = InpParser()
        self.blocks = parser.parse(inp_file)
        # 保留原始文本行（用于保留注释、空行格式）
        with open(inp_file, encoding="utf-8", errors="ignore") as f:
            self._source_text = f.readlines()

    def find_blocks(
        self,
        keyword: Optional[str] = None,
        name: Optional[str] = None,
        name_param: str = "NAME",
    ) -> list[Block]:
        """
        查找匹配的 Block。

        Args:
            keyword: 关键词名称（不区分大小写），如 "*MATERIAL"
            name: NAME 参数值，精确匹配
            name_param: 名称参数名，默认 "NAME"

        Returns:
            匹配的 Block 列表
        """
        results = []
        for block in self.blocks:
            if keyword is not None and block.keyword_name.upper() != keyword.upper():
                continue
            if name is not None:
                block_name = block.get_param(name_param)
                if block_name is None or block_name.upper() != name.upper():
                    continue
            results.append(block)
        return results

    def find_block(
        self,
        keyword: Optional[str] = None,
        name: Optional[str] = None,
        name_param: str = "NAME",
    ) -> Optional[Block]:
        """查找单个匹配的 Block。"""
        results = self.find_blocks(keyword=keyword, name=name, name_param=name_param)
        return results[0] if results else None

    def update_blocks(
        self,
        keyword: str,
        params: Optional[dict[str, str]] = None,
        name: Optional[str] = None,
        name_param: str = "NAME",
        data_transformer: Optional[callable] = None,
    ) -> int:
        """
        更新所有匹配的 Block。

        Args:
            keyword: 关键词名称
            params: 要修改的参数 {参数名: 新值}
            name: NAME 参数值（精确匹配）
            name_param: 名称参数名
            data_transformer: 数据行变换函数 (list[str]) -> list[str]

        Returns:
            更新的块数量
        """
        blocks = self.find_blocks(keyword=keyword, name=name, name_param=name_param)
        for block in blocks:
            if params:
                for k, v in params.items():
                    block.set_param(k, v)
            if data_transformer is not None:
                block.data_lines = data_transformer(block.data_lines)
        return len(blocks)

    def insert_block(
        self,
        block: Block,
        after_keyword: Optional[str] = None,
        after_name: Optional[str] = None,
        at_end: bool = False,
    ) -> None:
        """
        插入新的 Block。

        Args:
            block: 要插入的 Block
            after_keyword: 插入到指定关键词之后
            after_name: 插入到指定 NAME 之后
            at_end: 插入到末尾
        """
        if at_end:
            self.blocks.append(block)
            return

        # 找到插入位置
        target_name = after_name
        target_keyword = after_keyword
        insert_idx = len(self.blocks)

        for i, b in enumerate(self.blocks):
            if target_keyword is not None and b.keyword_name.upper() != target_keyword.upper():
                continue
            if target_name is not None:
                bname = b.get_param("NAME")
                if bname is None or bname.upper() != target_name.upper():
                    continue
            insert_idx = i + 1

        self.blocks.insert(insert_idx, block)

    def delete_blocks(
        self,
        keyword: Optional[str] = None,
        name: Optional[str] = None,
        name_param: str = "NAME",
    ) -> int:
        """删除所有匹配的 Block。返回删除数量。"""
        to_delete = self.find_blocks(keyword=keyword, name=name, name_param=name_param)
        for b in to_delete:
            self.blocks.remove(b)
        return len(to_delete)

    def generate(self) -> list[str]:
        """重新生成 INP 文件所有行。"""
        lines = []
        for block in self.blocks:
            lines.extend(block.get_inp_code())
        return lines

    def write(self, output_path: Path) -> None:
        """将修改后的 INP 写入文件。"""
        lines = self.generate()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")


# ------------------------------------------------------------------ #
# 辅助函数
# ------------------------------------------------------------------ #

def replace_values(
    lines: list[str],
    column_key: str,
    new_value: float,
    columns: Optional[dict[str, int]] = None,
) -> list[str]:
    """
    替换数据行中的值。

    Args:
        lines: 数据行列表
        column_key: 列名（如 "E" 代表弹性模量）
        new_value: 新值
        columns: {列名: 索引} 映射，默认使用常见 INP 格式

    Returns:
        替换后的行列表
    """
    # 默认列索引（1-based 在 header 中定义）
    # 这里简单处理：直接替换第 column_idx 个数值
    col_idx = _get_column_index(column_key, columns)
    result = []
    for line in lines:
        if not line.strip() or line.strip().startswith("**"):
            result.append(line)
            continue
        numbers = re.findall(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", line)
        if len(numbers) > col_idx:
            # 简单替换第 col_idx 个数值
            parts = re.split(r"([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)", line)
            count = 0
            new_parts = []
            for part in parts:
                if re.match(r"[-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", part):
                    if count == col_idx:
                        new_parts.append(str(new_value))
                    else:
                        new_parts.append(part)
                    count += 1
                else:
                    new_parts.append(part)
            result.append("".join(new_parts))
        else:
            result.append(line)
    return result


def _get_column_index(column_key: str, columns: Optional[dict[str, int]]) -> int:
    """获取列索引。"""
    if columns and column_key in columns:
        return columns[column_key]
    # 常见列名映射（0-based）
    COMMON_COLUMNS = {
        "E": 0,  # 弹性模量
        "NU": 1,  # 泊松比
        "RHO": 2,  # 密度
    }
    return COMMON_COLUMNS.get(column_key.upper(), 0)
