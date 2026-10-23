# -*- coding: utf-8 -*-
"""仓库管理 API 路由（页面：工具 → 代码仓库）。

鉴权由 app.main 的全局中间件统一处理（Bearer Token），这里不重复实现。
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from . import service
from .git_ops import GitError
from .schemas import (
    ApplyIdentityRequest,
    BranchCreateRequest,
    BranchDeleteRequest,
    BranchSwitchRequest,
    CloneRequest,
    CommitRequest,
    FileWriteRequest,
    PullRequest,
    PushRequest,
    ResolveRequest,
    SettingsPatch,
    StageRequest,
)

router = APIRouter()


async def _guard(coro):
    """把 GitError 统一翻译成 400 + 中文原因。"""
    try:
        return await coro
    except GitError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"操作失败：{exc}")


# ---------------------------------------------------------------- 仓库列表

@router.get("/repos", summary="扫描并列出所有受管仓库")
async def list_repos(force: bool = Query(False, description="跳过缓存重新计算")):
    return {"repos": await _guard(service.list_repos(force)), "roots": service.allowed_roots()}


@router.get("/status", summary="单个仓库的详细变更状态")
async def repo_status(path: str = Query(...)):
    real = await _guard(_validated(path))
    return await _guard(service.git_ops.status(real))


async def _validated(path: str) -> str:
    return service.validate(path)


# ---------------------------------------------------------------- 变更操作

@router.post("/stage", summary="暂存 / 取消暂存 / 丢弃")
async def stage(req: StageRequest):
    real = await _guard(_validated(req.path))
    await _guard(service.stage_paths(real, req.paths, req.action))
    return {"ok": True, "action": req.action, "count": len(req.paths)}


@router.post("/commit", summary="提交暂存区")
async def commit(req: CommitRequest):
    real = await _guard(_validated(req.path))
    message = (req.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="提交说明不能为空")
    return await _guard(service.commit_repo(real, message, amend=req.amend))


@router.post("/resolve", summary="冲突文件取我方/对方")
async def resolve(req: ResolveRequest):
    real = await _guard(_validated(req.path))
    full = os.path.join(real, req.file)
    if not os.path.realpath(full).startswith(real + os.sep):
        raise HTTPException(status_code=400, detail="文件路径非法")
    await _guard(service.git_ops.resolve_conflict(real, req.file, req.strategy))
    service.invalidate(real)
    return {"ok": True}


@router.get("/diff", summary="查看文件 diff")
async def diff(
    path: str = Query(...),
    file: str = Query(""),
    staged: bool = Query(False),
    untracked: bool = Query(False),
):
    real = await _guard(_validated(path))
    if file and not os.path.realpath(
        os.path.join(real, file)
    ).startswith(real + os.sep):
        raise HTTPException(status_code=400, detail="文件路径非法")
    text = await _guard(service.git_ops.diff(real, file, staged=staged, untracked=untracked))
    return {"diff": text}


@router.get("/identity", summary="读取该仓库实际使用的提交者身份")
async def get_identity(path: str = Query(...)):
    real = await _guard(_validated(path))
    return await _guard(service.get_repo_identity(real))


@router.post("/identity", summary="把身份档案（或手填姓名邮箱）写入该仓库的 .git/config")
async def set_identity(req: ApplyIdentityRequest):
    real = await _guard(_validated(req.path))
    return await _guard(
        service.apply_repo_identity(real, req.identity_id, req.name, req.email)
    )


# ---------------------------------------------------------------- 文件浏览

@router.get("/files", summary="列出仓库内某个目录")
async def list_files(path: str = Query(...), dir_path: str = Query("", alias="dir")):
    real = await _guard(_validated(path))
    return await _guard(asyncio.to_thread(service.list_repo_dir, real, dir_path))


@router.get("/files/content", summary="读取仓库内文件内容")
async def read_file(path: str = Query(...), file: str = Query(...)):
    real = await _guard(_validated(path))
    return await _guard(asyncio.to_thread(service.read_repo_file, real, file))


@router.put("/files/content", summary="保存仓库内文件（只写工作区，不自动 add）")
async def write_file(req: FileWriteRequest):
    real = await _guard(_validated(req.path))
    return await _guard(
        asyncio.to_thread(
            service.write_repo_file, real, req.file, req.content, req.encoding, req.eol
        )
    )


# ---------------------------------------------------------------- 远端同步

@router.post("/push", summary="推送到远端")
async def push(req: PushRequest):
    real = await _guard(_validated(req.path))
    return await _guard(service.push_repo(real, req.set_upstream, req.force))


@router.post("/pull", summary="从远端拉取")
async def pull(req: PullRequest):
    real = await _guard(_validated(req.path))
    return await _guard(service.pull_repo(real, req.rebase))


@router.post("/fetch", summary="仅 fetch（不改工作区）")
async def fetch(req: PullRequest):
    real = await _guard(_validated(req.path))
    await _guard(service.fetch_repo(real))
    return {"ok": True, "status": await _guard(service.repo_summary(real, force=True))}


@router.post("/fetch-all", summary="批量 fetch 所有仓库（异步任务）")
async def fetch_all():
    job_id = await _guard(service.start_fetch_all())
    return {"job_id": job_id}


# ---------------------------------------------------------------- 分支 / 历史

@router.get("/branches", summary="本地分支列表")
async def branches(path: str = Query(...)):
    real = await _guard(_validated(path))
    return {"branches": await _guard(service.git_ops.branches(real))}


@router.post("/branch/create", summary="新建分支")
async def branch_create(req: BranchCreateRequest):
    real = await _guard(_validated(req.path))
    await _guard(service.git_ops.create_branch(real, req.name, req.checkout))
    service.invalidate(real)
    return {"ok": True}


@router.post("/branch/switch", summary="切换分支")
async def branch_switch(req: BranchSwitchRequest):
    real = await _guard(_validated(req.path))
    await _guard(service.git_ops.switch_branch(real, req.name))
    service.invalidate(real)
    return {"ok": True}


@router.post("/branch/delete", summary="删除分支")
async def branch_delete(req: BranchDeleteRequest):
    real = await _guard(_validated(req.path))
    await _guard(service.git_ops.delete_branch(real, req.name, req.force))
    service.invalidate(real)
    return {"ok": True}


@router.get("/log", summary="最近提交")
async def log(path: str = Query(...), limit: int = Query(50, ge=1, le=200)):
    real = await _guard(_validated(path))
    return {"commits": await _guard(service.git_ops.log(real, limit))}


@router.get("/commit", summary="单个提交的详情与改动文件清单")
async def commit_detail(path: str = Query(...), rev: str = Query(...)):
    real = await _guard(_validated(path))
    return await _guard(service.git_ops.commit_detail(real, rev))


@router.get("/commit/diff", summary="某个提交里单个文件的 patch")
async def commit_diff(path: str = Query(...), rev: str = Query(...), file: str = Query("")):
    real = await _guard(_validated(path))
    if file and not os.path.realpath(
        os.path.join(real, file)
    ).startswith(real + os.sep):
        raise HTTPException(status_code=400, detail="文件路径非法")
    text = await _guard(service.git_ops.commit_file_diff(real, rev, file))
    return {"diff": text}


# ---------------------------------------------------------------- 克隆 / 任务

@router.post("/clone", summary="一键克隆（异步任务，返回 job_id）")
async def clone(req: CloneRequest):
    job_id = await _guard(
        service.start_clone(req.url, req.name, req.provider, req.target_dir, req.identity_id)
    )
    return {"job_id": job_id}


@router.get("/jobs/{job_id}", summary="查询任务进度")
async def job_status(job_id: str):
    job = service.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {
        "id": job["id"],
        "kind": job["kind"],
        "status": job["status"],
        "progress": job["progress"],
        "phase": job["phase"],
        "lines": job["lines"][-60:],
        "result": job["result"],
        "error": job["error"],
    }


@router.get("/providers/{provider}/repos", summary="拉取 GitHub / Gitea 账号下的仓库列表")
async def provider_repos(provider: str):
    return {"repos": await _guard(service.list_provider_repos(provider))}


# ---------------------------------------------------------------- 设置

@router.get("/settings", summary="读取仓库管理设置")
async def get_settings():
    settings = service.get_settings()
    return {"settings": settings, "roots": service.allowed_roots()}


@router.get("/browse", summary="浏览目录（用于选择仓库根目录 / 克隆落地目录）")
async def browse(path: str = Query("", description="要列出的目录，留空返回快捷入口")):
    return await _guard(service.browse(path))


@router.put("/settings", summary="更新仓库管理设置")
async def update_settings(patch: SettingsPatch):
    return {"settings": service.save_settings(patch.to_patch())}
