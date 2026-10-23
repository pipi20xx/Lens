# -*- coding: utf-8 -*-
"""仓库管理模块的数据模型。"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field


class RepoPath(BaseModel):
    path: str = Field(..., description="仓库绝对路径（必须在允许的根目录内）")


class StageRequest(RepoPath):
    action: str = Field(..., pattern="^(stage|unstage|discard)$")
    paths: List[str] = Field(default_factory=list)


class CommitRequest(RepoPath):
    message: str = ""
    amend: bool = False


class PushRequest(RepoPath):
    set_upstream: bool = False
    force: bool = False


class PullRequest(RepoPath):
    rebase: bool = False


class CloneRequest(BaseModel):
    url: str
    name: str = ""
    provider: str = ""
    proxy_mode: str = Field("", description="clone proxy: auto / on / off, empty = use repo settings default")
    target_dir: str = Field("", description="克隆落地目录，留空则用设置里的默认值")
    identity_id: str = Field("", description="克隆后套用的身份档案 id，留空则按来源 provider 自动匹配")


class ApplyIdentityRequest(RepoPath):
    identity_id: str = ""
    name: str = ""
    email: str = ""


class FileWriteRequest(RepoPath):
    file: str = Field(..., description="仓库内的相对路径")
    content: str = ""
    encoding: str = Field("", description="留空或不在白名单内则按 utf-8 写入")
    eol: str = Field("", description="原文件的换行风格：lf / crlf / cr，留空按 lf")


class ReplaceRequest(RepoPath):
    query: str = ""
    replacement: str = ""
    case: bool = False
    whole: bool = False
    regex: bool = False
    file: str = Field("", description="只替换这个文件；留空表示全仓库")


class BranchCreateRequest(RepoPath):
    name: str
    checkout: bool = True


class BranchSwitchRequest(RepoPath):
    name: str


class BranchDeleteRequest(RepoPath):
    name: str
    force: bool = False


class ResolveRequest(RepoPath):
    file: str
    strategy: str = Field(default="ours", pattern="^(ours|theirs)$")


class SettingsPatch(BaseModel):
    roots: List[str] | None = None
    clone_dir: str | None = None
    pinned: List[str] | None = None
    scan_depth: int | None = None
    author_name: str | None = None
    author_email: str | None = None
    identities: List[Dict[str, Any]] | None = None
    clone_proxy: str | None = None

    def to_patch(self) -> Dict[str, Any]:
        return {k: v for k, v in self.model_dump().items() if v is not None}
