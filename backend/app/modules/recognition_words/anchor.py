# -*- coding: utf-8 -*-
"""锚点提取：从视频文件名中截掉集数及之后的内容，保留稳定标题前缀。

移植自独立桌面工具「识别词生成器.py」的核心算法（build_anchor / is_anchor_valid）。
"""

import os
import re

VIDEO_EXT_RE = re.compile(r"\.(mp4|mkv|avi|ts|flv|mov|webm|m2ts|rmvb|iso)$", re.I)
GROUP_PREFIX_RE = re.compile(r"^(?:\s*[\[【(（][^\]】)）]{1,40}[\]】)（(]?)+")
EPISODE_CUT_PATTERNS = [
    r"\s*[-–—_]\s*\d{1,4}\b",            # " - 01"
    r"\s*S\d{1,3}\s*E\d{1,3}\b",         # S01E01
    r"\s*EP?\s*\d{1,4}\b",               # EP01 / E01
    r"\s*第\s*\d{1,4}\s*[集话回話]",       # 第01话
    r"\s*\[\d{1,4}\]",                   # [01]
    r"\s*\d{1,4}\b",                     # 裸数字（兜底，最后尝试）
]
TRAILING_JUNK_RE = re.compile(r"[\s\[\(（【\-_·.]+$")
CJK_TEXT_RE = re.compile(r"[\u4e00-\u9fa5\u3040-\u30ff\uac00-\ud7afa-zA-Z]{2,}")


def build_anchor(filename: str, keep_group: bool = False) -> str:
    """参考"智能记忆"指纹思路：截掉集数及之后的所有内容，保留稳定标题前缀。"""
    name = os.path.basename(filename.strip().strip("'\""))
    name = VIDEO_EXT_RE.sub("", name)
    if not keep_group:
        name = GROUP_PREFIX_RE.sub("", name)

    # 按优先级找到第一个"集数/季"特征并截断，之后的集数、分辨率、技术标记全部丢弃。
    # 下划线会让 \b 失效（_ 属于单词字符），先在空格归一化副本上定位，索引一一对应切回原串
    normalized = name.replace("_", " ")
    for pat in EPISODE_CUT_PATTERNS:
        m = re.search(pat, normalized, flags=re.I)
        if m:
            name = name[: m.start()]
            break

    # 去掉截断后残留的空括号壳和尾部符号
    name = re.sub(r"[\[【(（][\s\-_.]*[\]】)）]", " ", name)
    name = TRAILING_JUNK_RE.sub("", name)
    name = re.sub(r"\s{2,}", " ", name).strip(" -_.·")
    return name.strip()


def is_anchor_valid(anchor: str) -> bool:
    """过短的锚点会误伤其他文件，要求至少 2 个连续文字字符。"""
    return bool(CJK_TEXT_RE.search(anchor))
