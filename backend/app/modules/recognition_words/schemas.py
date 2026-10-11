# -*- coding: utf-8 -*-
"""识别词生成器 Pydantic 模型。"""

from typing import Optional

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    filenames: list[str] = Field(default_factory=list, description="视频文件名列表（每行一个，支持完整路径）")
    tmdbid: str = "xxxx"
    mtype: str = Field(default="tv", pattern="^(tv|movie)$")
    season: str = "x"
    loose: bool = True
    boundary: bool = False
    keep_group: bool = False
    date_comment: bool = True
    anchors: Optional[list[str]] = Field(
        default=None,
        description="手动锚点（与 filenames 一一对应）；提供时跳过自动提取，为空串的行按空锚点处理",
    )


class AnchorRow(BaseModel):
    filename: str
    anchor: str
    valid: bool
    rule: str = ""


class GenerateResponse(BaseModel):
    rules_text: str
    rows: list[AnchorRow] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    hint: str = ""
