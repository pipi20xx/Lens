# -*- coding: utf-8 -*-
"""番剧分季拆分 API 路由。"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from . import service
from .schemas import (
    GiteaListDirRequest,
    GiteaPushRequest,
    SplitRunRequest,
    StartTaskResponse,
    SytmdbWriteRequest,
    TaskStatusResponse,
)

router = APIRouter()


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="任务不存在")


@router.post("/split", response_model=StartTaskResponse, summary="开始分季拆分（后台任务）")
async def start_split(req: SplitRunRequest):
    try:
        task_id = await service.start_split(req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return StartTaskResponse(task_id=task_id)


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse, summary="查询任务状态与日志")
async def task_status(task_id: str):
    data = service.get_task_status(task_id)
    if data is None:
        raise _not_found()
    return data


@router.get("/tasks/{task_id}/result", summary="获取拆分结果")
async def task_result(task_id: str):
    result = service.get_task_result(task_id)
    if result is None:
        raise _not_found()
    return result


@router.post("/gitea/list-dir", summary="列出仓库（Gitea/GitHub）目录内容")
async def gitea_list_dir(req: GiteaListDirRequest):
    try:
        files = await asyncio.to_thread(service.list_gitea_files, req.dir_path, req.provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取文件列表失败: {e}")
    return {"files": files}


@router.post("/gitea/push", summary="推送渲染词到仓库（Gitea/GitHub）")
async def gitea_push(req: GiteaPushRequest):
    try:
        data = await asyncio.to_thread(
            service.push_render_words, req.task_id, req.file_path, req.force_manual,
            req.content, req.provider,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gitea 推送失败: {e}")
    return data


@router.post("/sytmdb/write", summary="剧集组覆盖写入 SYTMDB")
async def sytmdb_write(req: SytmdbWriteRequest):
    try:
        data = await asyncio.to_thread(service.write_sytmdb, req.task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"SYTMDB 写入失败: {e}")
    return data
