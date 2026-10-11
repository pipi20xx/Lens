# -*- coding: utf-8 -*-
"""番剧分季拆分 Pydantic 模型。

集成配置（TMDB/TVDB/Bangumi Key、代理、Gitea、SYTMDB）全部来自系统设置
（config.json），接口只接收运行参数。
"""

from typing import Optional

from pydantic import BaseModel, Field


class SplitRunRequest(BaseModel):
    tmdb_id: int = Field(..., description="TMDB 剧集 ID")
    language: str = "zh-CN"
    source: str = Field(default="", description="外部分季规则表：http(s) URL 或本地 JSON 路径")
    use_source: bool = Field(default=False, description="启用外部分季规则表（优先级最高）")
    priority: str = Field(default="tvdb, bangumi",
                          description="参照优先级：tvdb, bangumi / bangumi, tvdb / 仅 tvdb / 仅 bangumi")
    force_reference: bool = Field(default=False, description="忽略自动参照条件（非日漫也尝试）")


class LogEntry(BaseModel):
    time: str
    level: str
    message: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str = Field(..., description="running / done / failed")
    logs: list[LogEntry] = Field(default_factory=list)
    error: Optional[str] = None


class StartTaskResponse(BaseModel):
    task_id: str


class GiteaListDirRequest(BaseModel):
    dir_path: str = Field(default="", description="仓库目录（空 = 根目录）")
    provider: str = Field(default="gitea", pattern="^(gitea|github)$", description="仓库类型")


class GiteaPushRequest(BaseModel):
    task_id: str
    file_path: str = Field(default="", description="渲染词文件路径；空则使用系统设置里对应仓库类型的文件路径")
    force_manual: bool = Field(default=False, description="渲染词出现在手动区块时强制替换")
    content: str = Field(default="", description="渲染词文本；空则使用任务结果中的生成文本（支持前端手动编辑后再推送）")
    provider: str = Field(default="gitea", pattern="^(gitea|github)$", description="仓库类型")


class SytmdbWriteRequest(BaseModel):
    task_id: str
