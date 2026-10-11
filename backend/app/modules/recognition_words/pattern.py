# -*- coding: utf-8 -*-
"""正则构造：把锚点转为识别词匹配正则（绝对 / 宽松两种模式）。

移植自独立桌面工具「识别词生成器.py」的核心算法（build_pattern / add_boundary）。
"""

import re

# 宽松模式下互相等价的分隔符（空格/点/横线/下划线/间隔号/句读点/全半角冒号），允许省略或连用
BRACKET_OPEN_CLASS = r"[\[【]"
BRACKET_CLOSE_CLASS = r"[\]】]"


def add_boundary(pattern: str, anchor: str) -> str:
    """包裹 (?i)\\b...\\b 词边界；首/尾字符不是"单词字符"时该侧不加 \\b（加了也匹配不上）。"""
    prefix = ""
    suffix = ""
    if anchor and anchor[0].isalnum():
        prefix = r"\b"
    if anchor and anchor[-1].isalnum():
        suffix = r"\b"
    return f"(?i){prefix}{pattern}{suffix}"


def build_pattern(anchor: str, loose: bool, boundary: bool = False) -> str:
    """
    绝对模式：re.escape 逐字面匹配。
    宽松模式：词元之间用 .*? 连接——中间是符号、空格还是别的内容一概不管。
    boundary=True 时再包一层 (?i)\\b...\\b（大小写不敏感本就由识别引擎处理，(?i) 仅为兼容社区写法）。
    """
    if not loose:
        pattern = re.escape(anchor)
    else:
        tokens = [t for t in re.split(r"[\s._\-–—·・。、．:：]+", anchor) if t]
        parts = []
        for tok in tokens:
            esc = re.escape(tok)
            esc = esc.replace("\\[", BRACKET_OPEN_CLASS).replace("\\]", BRACKET_CLOSE_CLASS)
            parts.append(esc)
        pattern = ".*?".join(parts)
    return add_boundary(pattern, anchor) if boundary else pattern
