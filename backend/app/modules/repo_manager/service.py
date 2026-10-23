# -*- coding: utf-8 -*-
"""仓库管理服务：目录扫描、路径白名单校验、状态汇总缓存、异步任务（克隆/批量拉取）。

安全边界（本模块跑在容器内、以 root 工作，必须守住）：
- 任何 git 操作前都用 :func:`validate` 把路径 realpath 后比对「仓库根目录」白名单，
  防止通过 ``../`` 或绝对路径操作到根目录之外；
- 克隆目标名不允许包含路径分隔符或 ``..``；
- 令牌只从 config.json 读取，且仅在目标主机与配置主机完全一致时注入（见 git_ops）。
"""

from __future__ import annotations

import asyncio
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.config_manager import get_config, save_config

from . import git_ops
from .git_ops import GitError

SETTINGS_KEY = "git_manager"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "roots": ["/vol1/1000/NVME"],          # 允许被管理的仓库根目录（白名单）
    "clone_dir": "/vol1/1000/NVME/repos",  # 一键克隆的默认落地目录
    "pinned": [],                          # 手动置顶的仓库绝对路径
    "scan_depth": 3,                       # 目录扫描深度（相对根目录）
    "max_repos": 300,
    "author_name": "",                     # 仓库未配置 user.name 时的兜底
    "author_email": "",
    # 提交者身份档案：[{id, label, provider(github|gitea|""), name, email}]
    # 典型用法：为 GitHub 和 Gitea 各建一个，克隆时按来源自动套用
    "identities": [],
}


def _normalize_identities(items: Any) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    seen: set = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        email = str(item.get("email") or "").strip()
        if not name and not email:
            continue
        provider = str(item.get("provider") or "").strip().lower()
        if provider not in ("github", "gitea"):
            provider = ""
        ident_id = str(item.get("id") or "").strip() or uuid.uuid4().hex[:8]
        if ident_id in seen:
            ident_id = uuid.uuid4().hex[:8]
        seen.add(ident_id)
        result.append({
            "id": ident_id,
            "label": str(item.get("label") or "").strip() or (provider or "身份"),
            "provider": provider,
            "name": name,
            "email": email,
        })
    return result

# 扫描时跳过的目录：VCS 元数据、依赖缓存、NAS 回收站
_SKIP_DIRS = {
    "node_modules", "__pycache__", ".venv", "venv", "env",
    "@eaDir", "#recycle", "lost+found", ".Trash", ".snapshot",
}

_CACHE_TTL = 8.0
_SEM = asyncio.Semaphore(4)


# ------------------------------------------------------------------ 配置

def get_settings() -> Dict[str, Any]:
    raw = get_config().get(SETTINGS_KEY)
    merged = dict(DEFAULT_SETTINGS)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if value is not None:
                merged[key] = value

    roots = []
    for item in merged.get("roots") or []:
        if isinstance(item, str) and item.strip():
            roots.append(item.strip())
    merged["roots"] = roots or list(DEFAULT_SETTINGS["roots"])

    try:
        merged["scan_depth"] = max(1, min(int(merged.get("scan_depth") or 3), 8))
    except (TypeError, ValueError):
        merged["scan_depth"] = 3
    merged["identities"] = _normalize_identities(merged.get("identities"))
    return merged


def save_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    cfg = get_config()
    current = dict(DEFAULT_SETTINGS)
    existing = cfg.get(SETTINGS_KEY)
    if isinstance(existing, dict):
        current.update({k: v for k, v in existing.items() if v is not None})

    for key, value in (patch or {}).items():
        if key in DEFAULT_SETTINGS:
            current[key] = value

    current["roots"] = [r.strip() for r in (current.get("roots") or [])
                        if isinstance(r, str) and r.strip()]
    current["identities"] = _normalize_identities(current.get("identities"))
    cfg[SETTINGS_KEY] = current
    save_config(cfg)
    _CACHE.clear()
    return get_settings()


# ------------------------------------------------------------------ 路径校验

def _real(path: str) -> str:
    return os.path.realpath(os.path.expanduser((path or "").strip()))


def allowed_roots() -> List[str]:
    return [_real(r) for r in get_settings()["roots"] if os.path.isdir(_real(r))]


def _inside_roots(real_path: str) -> bool:
    return any(
        real_path == root or real_path.startswith(root + os.sep)
        for root in allowed_roots()
    )


def validate(path: str) -> str:
    """把外部传入的路径解析为真实路径，并校验它确实是白名单内的 git 仓库。"""
    real = _real(path)
    if not real or not os.path.isdir(real):
        raise GitError("目录不存在或不可访问")
    if not _inside_roots(real):
        raise GitError("该路径不在「允许的仓库根目录」内，已拒绝操作")
    if not os.path.exists(os.path.join(real, ".git")):
        raise GitError("该目录不是 git 仓库")
    return real


# ------------------------------------------------------------------ 扫描

def _scan_sync() -> List[str]:
    settings = get_settings()
    depth = settings["scan_depth"]
    limit = int(settings.get("max_repos") or 300)

    found: List[str] = []
    for root in allowed_roots():
        for dirpath, dirnames, filenames in os.walk(root):
            rel = os.path.relpath(dirpath, root)
            level = 0 if rel == "." else rel.count(os.sep) + 1

            if ".git" in dirnames or ".git" in filenames:
                found.append(dirpath)
                dirnames[:] = []
                if len(found) >= limit:
                    return found
                continue

            if level >= depth:
                dirnames[:] = []
                continue
            dirnames[:] = sorted(
                d for d in dirnames
                if not d.startswith(".") and d not in _SKIP_DIRS
            )
    return found


_CACHE: Dict[str, Dict[str, Any]] = {}


async def repo_summary(path: str, force: bool = False) -> Dict[str, Any]:
    now = time.time()
    cached = _CACHE.get(path)
    if cached and not force and now - cached["ts"] < _CACHE_TTL:
        return cached["data"]

    empty_counts = {"staged": 0, "unstaged": 0, "untracked": 0, "conflict": 0}
    try:
        async with _SEM:
            st = await git_ops.status(path)
        branch = st["branch"]
        data = {
            "path": path,
            "name": os.path.basename(path),
            "ok": True,
            "branch": branch["head"] or "(detached)",
            "detached": branch["detached"],
            "upstream": branch["upstream"],
            "ahead": branch["ahead"],
            "behind": branch["behind"],
            "counts": st["counts"],
            "dirty": any(st["counts"].values()),
        }
    except GitError as exc:
        data = {
            "path": path, "name": os.path.basename(path), "ok": False,
            "branch": "", "detached": False, "upstream": "",
            "ahead": 0, "behind": 0, "counts": dict(empty_counts),
            "dirty": False, "error": exc.message,
        }

    _CACHE[path] = {"ts": now, "data": data}
    return data


def invalidate(path: Optional[str] = None) -> None:
    if path:
        _CACHE.pop(path, None)
    else:
        _CACHE.clear()


async def list_repos(force: bool = False) -> List[Dict[str, Any]]:
    settings = get_settings()
    paths = await asyncio.to_thread(_scan_sync)

    pinned = [p for p in (settings.get("pinned") or []) if isinstance(p, str) and os.path.isdir(p)]
    ordered = list(dict.fromkeys(pinned + paths))

    summaries = await asyncio.gather(*(repo_summary(p, force) for p in ordered))
    pinned_set = set(pinned)
    for item in summaries:
        item["pinned"] = item["path"] in pinned_set
    # 有改动 / 有落后 的排前面，其余按名字
    summaries.sort(key=lambda r: (
        not r.get("pinned"), not r.get("dirty"), r.get("behind", 0) == 0, r["name"].lower()
    ))
    return summaries


# ------------------------------------------------------------------ 目录浏览

# 目录选择器的快捷入口（只用于快速跳转，不构成访问限制）
_BROWSE_START = ["/vol1", "/mnt", "/data", "/volume1", "/home", "/opt"]


def browse_shortcuts() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []
    seen = set()

    def add(label: str, path: str) -> None:
        real = _real(path)
        if real in seen or not os.path.isdir(real):
            return
        seen.add(real)
        items.append({"label": label, "path": real})

    for root in allowed_roots():
        add(os.path.basename(root.rstrip("/")) or root, root)
    for base in _BROWSE_START:
        add(base, base)
    add("/", "/")
    return items


def browse_dirs(path: str = "", limit: int = 500) -> Dict[str, Any]:
    """列出某目录下的子目录，供前端「选择文件夹」使用。"""
    raw = (path or "").strip()
    target = _real(raw)
    # 没有指定路径（或路径已失效）时，从配置的仓库根目录开始
    if not raw or not os.path.isdir(target):
        shortcuts = browse_shortcuts()
        target = shortcuts[0]["path"] if shortcuts else "/"

    entries: List[Dict[str, Any]] = []
    try:
        with os.scandir(target) as scan:
            for entry in scan:
                try:
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                except OSError:
                    continue
                if entry.name.startswith("."):
                    continue
                full = os.path.join(target, entry.name)
                entries.append({
                    "name": entry.name,
                    "path": full,
                    "is_git": os.path.exists(os.path.join(full, ".git")),
                    "in_roots": _inside_roots(full),
                })
                if len(entries) >= limit:
                    break
    except PermissionError:
        raise GitError("没有权限读取该目录")
    except FileNotFoundError:
        raise GitError("目录不存在")

    entries.sort(key=lambda e: e["name"].lower())
    parent = os.path.dirname(target)
    return {
        "path": target,
        "parent": "" if parent == target else parent,
        "entries": entries,
        "shortcuts": browse_shortcuts(),
        "is_git": os.path.exists(os.path.join(target, ".git")),
        "in_roots": _inside_roots(target),
    }


async def browse(path: str = "") -> Dict[str, Any]:
    return await asyncio.to_thread(browse_dirs, path)


# ------------------------------------------------------------------ 异步任务

class JobStore:
    """内存任务表（克隆、批量拉取这类长操作靠它推进度）。"""

    MAX_JOBS = 40

    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}

    def create(self, kind: str, **meta: Any) -> str:
        job_id = uuid.uuid4().hex[:12]
        self._jobs[job_id] = {
            "id": job_id, "kind": kind, "status": "running",
            "lines": [], "progress": 0, "phase": "",
            "result": None, "error": "", "started": time.time(),
            "finished": 0.0, **meta,
        }
        self._prune()
        return job_id

    def log(self, job_id: str, line: str) -> None:
        job = self._jobs.get(job_id)
        if not job or not line:
            return
        job["lines"].append(line)
        if len(job["lines"]) > 500:
            del job["lines"][:-500]
        percent = git_ops.progress_of(line)
        if percent is not None:
            job["progress"] = percent
            job["phase"] = line.split(":")[0].strip()
        elif "remote:" in line:
            job["phase"] = line.replace("remote:", "").strip()[:80]

    def finish(self, job_id: str, result: Any = None) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.update(status="done", result=result, progress=100, finished=time.time())

    def fail(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job:
            job.update(status="failed", error=error, finished=time.time())

    def set_progress(self, job_id: str, percent: int, phase: str = "") -> None:
        job = self._jobs.get(job_id)
        if job:
            job["progress"] = max(0, min(100, int(percent)))
            if phase:
                job["phase"] = phase

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self._jobs.get(job_id)

    def _prune(self) -> None:
        if len(self._jobs) <= self.MAX_JOBS:
            return
        finished = sorted(
            (j for j in self._jobs.values() if j["status"] != "running"),
            key=lambda j: j["started"],
        )
        for job in finished[: len(self._jobs) - self.MAX_JOBS]:
            self._jobs.pop(job["id"], None)


jobs = JobStore()


# ------------------------------------------------------------------ 操作封装

def _auth_env_for(repo: str, url: str) -> Optional[Dict[str, str]]:
    return git_ops.auth_env_for_url(url, get_config())


async def _remote_url(repo: str) -> str:
    try:
        return await git_ops.remote_url(repo)
    except Exception:
        return ""


async def push_repo(repo: str, set_upstream: bool = False,
                    force: bool = False) -> Dict[str, Any]:
    url = await _remote_url(repo)
    result = await git_ops.push(
        repo, set_upstream=set_upstream, force=force, auth_env=_auth_env_for(repo, url)
    )
    invalidate(repo)
    return result


async def pull_repo(repo: str, rebase: bool = False) -> Dict[str, Any]:
    url = await _remote_url(repo)
    result = await git_ops.pull(repo, rebase=rebase, auth_env=_auth_env_for(repo, url))
    invalidate(repo)
    return result


async def fetch_repo(repo: str) -> None:
    url = await _remote_url(repo)
    await git_ops.fetch(repo, auth_env=_auth_env_for(repo, url))
    invalidate(repo)


async def commit_repo(repo: str, message: str, amend: bool = False) -> Dict[str, Any]:
    settings = get_settings()
    result = await git_ops.commit(
        repo, message, amend=amend,
        author_name=(settings.get("author_name") or "").strip(),
        author_email=(settings.get("author_email") or "").strip(),
    )
    invalidate(repo)
    return result


# ------------------------------------------------------------------ 提交者身份

async def get_repo_identity(path: str) -> Dict[str, Any]:
    """给出这个仓库实际会用谁提交：仓库级 > 容器内 git 配置 > 设置里的兜底。"""
    settings = get_settings()
    info = await git_ops.get_identity(path)
    local = info["local"]
    resolved = info["resolved"]
    effective = info["effective"]
    fallback = {
        "name": (settings.get("author_name") or "").strip(),
        "email": (settings.get("author_email") or "").strip(),
    }

    if local.get("name") and local.get("email"):
        source, display = "repo", local
    elif resolved.get("name") and resolved.get("email"):
        source, display = "git-global", resolved
    elif fallback["name"] and fallback["email"]:
        source, display = "settings", fallback
    elif effective:
        source, display = "git-global", effective
    else:
        source, display = "none", {"name": "", "email": ""}

    return {
        "local": local,
        "resolved": resolved,
        "effective": effective,
        "fallback": fallback,
        "source": source,
        "display": display,
        "identities": settings.get("identities") or [],
    }


async def apply_repo_identity(path: str, identity_id: str = "",
                              name: str = "", email: str = "") -> Dict[str, Any]:
    """把某个身份档案（或手填的姓名邮箱）写进该仓库的 .git/config。"""
    settings = get_settings()
    if identity_id:
        profile = next(
            (i for i in (settings.get("identities") or []) if i.get("id") == identity_id), None
        )
        if not profile:
            raise GitError("身份档案不存在，可能已被删除")
        name, email = profile.get("name", ""), profile.get("email", "")

    name = (name or "").strip()
    email = (email or "").strip()

    if name and email:
        if "@" not in email:
            raise GitError("邮箱格式不正确")
    elif name or email:
        raise GitError("姓名和邮箱需要同时填写；两个都留空表示清除该仓库的身份设置")

    await git_ops.set_identity(path, name, email)
    invalidate(path)
    result = await get_repo_identity(path)
    result["message"] = "已清除本仓库身份（回落到兜底设置）" if not name else "已更新本仓库提交者身份"
    return result


def _auto_identity_for(provider: str, identity_id: str = "") -> Optional[Dict[str, str]]:
    profiles = get_settings().get("identities") or []
    if identity_id:
        chosen = next((p for p in profiles if p.get("id") == identity_id), None)
        if chosen:
            return chosen
    if not provider:
        return None
    return next(
        (p for p in profiles
         if p.get("provider") == provider and p.get("name") and p.get("email")),
        None,
    )


async def stage_paths(repo: str, paths: List[str], action: str) -> None:
    if not paths:
        raise GitError("没有选中任何文件")
    if action == "stage":
        await git_ops.stage(repo, paths)
    elif action == "unstage":
        await git_ops.unstage(repo, paths)
    elif action == "discard":
        await git_ops.discard(repo, paths)
    else:
        raise GitError(f"未知操作: {action}")
    invalidate(repo)


def _repo_name_from_url(url: str) -> str:
    tail = (url or "").rstrip("/").split("/")[-1]
    tail = tail.split(":")[-1]
    if tail.endswith(".git"):
        tail = tail[:-4]
    return re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "-", tail).strip("-") or "repo"


async def start_clone(url: str, name: str = "", provider: str = "",
                      target_dir: str = "", identity_id: str = "") -> str:
    url = (url or "").strip()
    if not url:
        raise GitError("请填写仓库地址")
    if not (url.startswith(("http://", "https://", "git@", "ssh://"))):
        raise GitError("无法识别的仓库地址（需要 http(s) 或 ssh）")

    settings = get_settings()
    clone_dir = _real((target_dir or "").strip() or settings.get("clone_dir") or "")
    if not clone_dir:
        raise GitError("未设置克隆目录")
    # 先做白名单校验再建目录，避免在允许范围之外留下空目录
    if not _inside_roots(clone_dir):
        raise GitError("克隆目录必须位于「允许的仓库根目录」内")
    os.makedirs(clone_dir, exist_ok=True)

    repo_name = (name or "").strip() or _repo_name_from_url(url)
    if "/" in repo_name or "\\" in repo_name or repo_name in (".", ".."):
        raise GitError("仓库名非法")
    dest = os.path.join(clone_dir, repo_name)
    if os.path.exists(dest) and os.listdir(dest):
        raise GitError(f"目标目录已存在且非空：{dest}")

    job_id = jobs.create("clone", target=dest, url=url)
    auth_env = git_ops.auth_env_for_url(url, get_config())

    async def runner() -> None:
        try:
            await git_ops.clone(url, dest, auth_env=auth_env,
                                on_line=lambda line: jobs.log(job_id, line))

            # 克隆完成后按「来源 provider」自动套用对应的提交者身份
            detected = provider or git_ops.provider_for_url(url, get_config())
            profile = _auto_identity_for(detected, identity_id)
            if profile and profile.get("name") and profile.get("email"):
                await git_ops.set_identity(dest, profile["name"], profile["email"])
                jobs.log(job_id, f"已套用提交者身份：{profile['name']} <{profile['email']}>")

            invalidate()
            jobs.finish(job_id, {"path": dest, "name": repo_name,
                                 "identity": profile["label"] if profile else ""})
        except GitError as exc:
            jobs.fail(job_id, exc.message)
        except Exception as exc:  # noqa: BLE001
            jobs.fail(job_id, str(exc))

    asyncio.create_task(runner())
    return job_id


async def start_fetch_all() -> str:
    repos = [r["path"] for r in await list_repos() if r.get("ok")]
    job_id = jobs.create("fetch_all", total=len(repos))

    async def runner() -> None:
        ok = failed = 0
        for index, path in enumerate(repos, start=1):
            jobs.log(job_id, f"[{index}/{len(repos)}] {os.path.basename(path)}")
            jobs.set_progress(job_id, int((index - 1) * 100 / max(1, len(repos))),
                              f"{os.path.basename(path)}")
            try:
                await fetch_repo(path)
                ok += 1
            except GitError as exc:
                failed += 1
                jobs.log(job_id, f"  ↳ 失败：{exc.message}")
            jobs.set_progress(job_id, int(index * 100 / max(1, len(repos))),
                              f"已完成 {index}/{len(repos)}")
        invalidate()
        jobs.finish(job_id, {"ok": ok, "failed": failed, "total": len(repos)})

    asyncio.create_task(runner())
    return job_id


async def list_provider_repos(provider: str) -> List[Dict[str, Any]]:
    """复用现有 GitHub / Gitea 集成，只做字段归一化。"""
    from app.services.git_repo_service import GitRepoService

    if provider not in ("gitea", "github"):
        raise GitError("不支持的仓库服务")
    raw = await GitRepoService.list_repos(provider)
    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        result.append({
            "name": item.get("name") or "",
            "full_name": item.get("full_name") or item.get("name") or "",
            "description": item.get("description") or "",
            "private": bool(item.get("private")),
            "clone_url": item.get("clone_url") or "",
            "ssh_url": item.get("ssh_url") or "",
            "updated": item.get("updated_at") or item.get("updated") or "",
            "default_branch": item.get("default_branch") or "",
        })
    result.sort(key=lambda r: r["updated"], reverse=True)
    return result
