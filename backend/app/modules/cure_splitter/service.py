# -*- coding: utf-8 -*-
"""番剧分季拆分服务：任务编排 + 集成配置组装。

原桌面工具的 SplitWorker(QThread).run() 主体抽成 run_split() 普通函数，
经 asyncio.to_thread 在后台线程执行；Qt 信号改为 log 回调写入内存任务注册表。
"""

from __future__ import annotations

import asyncio
import threading
import traceback
import uuid
from datetime import datetime
from typing import Callable, Optional

from app.core.config_manager import get_config
from app.utils.logger import logger

from .media_clients import (
    DEFAULT_TMDB_BASE,
    DEFAULT_TVDB_BASE,
    DEFAULT_TVDB_KEY,
    BangumiClient,
    TMDBClient,
    TVDBClient,
    load_cure_source,
)
from .push import (
    AUTO_HEADER_RE,
    gitea_get_file,
    gitea_list_dir,
    gitea_put_file,
    library_write_episodegroup,
    upsert_render_block,
)
from .splitter import (
    SeasonSplitter,
    build_finale_groups,
    generate_group_render_words,
    generate_render_words,
    groups_to_group_json,
    logic_to_group_json,
    mapping_to_json,
)

MAX_LOG_LINES = 5000
MAX_KEEP_TASKS = 20

_tasks: dict = {}
_tasks_lock = threading.Lock()


def _prune_tasks() -> None:
    """只保留最近 MAX_KEEP_TASKS 个任务。"""
    if len(_tasks) <= MAX_KEEP_TASKS:
        return
    ordered = sorted(_tasks.items(), key=lambda kv: kv[1]["created_at"])
    for key, _ in ordered[: len(ordered) - MAX_KEEP_TASKS]:
        _tasks.pop(key, None)


def _append_log(task: dict, level: str, message: str) -> None:
    entry = {"time": datetime.now().strftime("%H:%M:%S"), "level": level, "message": message}
    with _tasks_lock:
        task["logs"].append(entry)
        if len(task["logs"]) > MAX_LOG_LINES:
            del task["logs"][: len(task["logs"]) - MAX_LOG_LINES]


# ---------------------------------------------------------------------------
# 集成配置（来自系统设置 config.json）
# ---------------------------------------------------------------------------

def build_integration_settings() -> dict:
    """从系统设置组装拆分所需的集成配置；缺省时沿用上游 Go 版内置 TVDB Key。"""
    cfg = get_config()
    proxy_cfg = cfg.get("proxy") or {}
    gitea = dict(cfg.get("gitea") or {})
    github = dict(cfg.get("github") or {})
    sytmdb = dict(cfg.get("sytmdb") or {})
    return {
        "tmdb_key": (cfg.get("tmdb_api_key") or "").strip(),
        "tmdb_base": DEFAULT_TMDB_BASE,
        "tvdb_key": (cfg.get("tvdb_api_key") or "").strip() or DEFAULT_TVDB_KEY,
        "tvdb_base": DEFAULT_TVDB_BASE,
        "bangumi_token": (cfg.get("bangumi_api_token") or "").strip(),
        "proxy": (proxy_cfg.get("url") or "").strip() if proxy_cfg.get("enabled") else "",
        "gitea": {
            "base": (gitea.get("base") or "").strip().rstrip("/"),
            "username": (gitea.get("username") or "").strip(),
            "token": (gitea.get("token") or "").strip(),
            "repo": (gitea.get("repo") or "").strip().strip("/"),
            "branch": (gitea.get("branch") or "").strip() or "main",
            "file_path": (gitea.get("file_path") or "").strip().strip("/"),
        },
        "github": {
            "base": (github.get("base") or "").strip() or "https://api.github.com",
            "token": (github.get("token") or "").strip(),
            "repo": (github.get("repo") or "").strip().strip("/"),
            "branch": (github.get("branch") or "").strip() or "main",
            "file_path": (github.get("file_path") or "").strip().strip("/"),
        },
        "sytmdb": {
            "base": (sytmdb.get("base") or "").strip().rstrip("/"),
            "token": (sytmdb.get("token") or "").strip(),
        },
    }


PROVIDER_NAMES = {"gitea": "Gitea", "github": "GitHub"}


def _repo_settings(provider: str) -> dict:
    """取指定推送目标（gitea/github）的仓库配置并做基础校验。"""
    name = PROVIDER_NAMES.get(provider)
    if not name:
        raise ValueError(f"不支持的仓库类型: {provider}")
    st = build_integration_settings()[provider]
    if not st["base"] or not st["repo"]:
        raise ValueError(f"未配置{name}地址和仓库，请先在「设置 → 第三方 API 集成」填写")
    if provider == "github":
        if not st["token"]:
            raise ValueError("未配置 GitHub 访问令牌（PAT，需 Contents 读写权限）")
    elif not st["token"] and not st["username"]:
        raise ValueError(f"未配置{name}登录信息（用户名 + 密码/令牌，或访问令牌）")
    return st


def _parse_priority(priority_text: str) -> list:
    text = (priority_text or "").strip()
    if text.startswith("仅"):
        return [text.replace("仅", "").strip()]
    return [x.strip() for x in text.split(",") if x.strip()]


# ---------------------------------------------------------------------------
# 拆分主流程（原 SplitWorker.run 主体）
# ---------------------------------------------------------------------------

def run_split(settings: dict, tmdb_id: int, log: Callable) -> dict:
    """执行一次拆分，返回结果字典；异常向上抛出由调用方记录。"""
    tmdb = TMDBClient(settings["tmdb_key"], settings["tmdb_base"], settings["language"],
                      settings["proxy"], log)
    tvdb = TVDBClient(settings["tvdb_key"], settings["tvdb_base"], settings["proxy"], log)
    bangumi = BangumiClient("https://api.bgm.tv", settings["proxy"], log,
                            token=settings.get("bangumi_token", ""))

    # 外部规则表(开关控制,默认关闭走 TVDB/Bangumi)
    source_data: dict = {}
    if settings.get("use_source"):
        log("INFO", f"加载 CureTMDb 规则表: {settings.get('source') or '(未设置)'}")
        try:
            source_data = load_cure_source(settings.get("source", ""), settings["proxy"], log)
        except Exception as e:
            log("WARN", f"规则表加载失败，按空表继续: {e}")
        log("INFO", f"规则表条目数: {len(source_data)}")
    else:
        log("INFO", "外部分季规则表未启用，按优先级走 TVDB/Bangumi")

    priority = settings["priority"]
    splitter = SeasonSplitter(tmdb, log)
    tv_show = tmdb.tv_detail(tmdb_id)
    if not tv_show:
        raise ValueError(f"TMDB ID {tmdb_id} 未找到剧集详情")
    title = tv_show.get("name") or tv_show.get("original_name") or ""
    log("INFO", f"目标: {title} (TMDB {tmdb_id})")

    series = splitter.fetch_series_entries_sequentially(
        tv_show, source_data, priority, tvdb, bangumi, settings["force_reference"],
    )
    actual_counts = {
        int(s["season_number"]): int(s.get("episode_count") or 0)
        for s in (tv_show.get("seasons") or [])
        if isinstance(s.get("season_number"), int)
    }
    need_split = series is not None and series.has_inconsistent(actual_counts)

    result: dict = {
        "tmdb_id": tmdb_id,
        "title": title,
        "reference": "",
        "split_done": False,
        "definition_rows": [],
        "season_rows": [],
        "episode_rows": [],
        "render_words": "",
        "group_json": None,
        "mapping_json": None,
        "logic_json": None,
    }

    if not need_split:
        # 无需拆分(或无分季依据) → 以"季结局(finale)"为界兜底分组，仍产出剧集组+渲染词
        reason = "TMDB 实际结构与分季定义一致，无需拆分" if series is not None \
            else "未找到可用的分季依据"
        log("INFO", f"{reason}，改用 finale 分组生成剧集组与渲染词")
        result["reference"] = "finale"
        number_of_seasons = int(tv_show.get("number_of_seasons") or 0)
        raw_seasons = splitter.fetch_seasons(tmdb_id, 1, number_of_seasons)
        groups = build_finale_groups(raw_seasons, number_of_seasons)
        if not groups:
            log("WARN", "无可用剧集，无法分组")
            return result
        result["group_json"] = groups_to_group_json(groups, tmdb_id)
        result["render_words"] = generate_group_render_words(tmdb_id, title, "finale", groups)
        for g in groups:
            log("INFO", f"剧集组 {g['name']} 共 {len(g['episodes'])} 集")
        for g in groups:
            for idx, ep in enumerate(g["episodes"]):
                result["episode_rows"].append({
                    "season": g["order"], "episode": idx + 1,
                    "org_season": ep.get("_season_number"),
                    "org_episode": ep.get("episode_number"),
                    "type": "tv",
                    "air_date": ep.get("air_date") or "",
                    "name": ep.get("name") or "",
                })
        return result

    ref_names = {s.season_number: s.episode_count for s in series.seasons}
    log("INFO", f"分季定义: {ref_names}")
    result["definition_rows"] = [
        {
            "season_number": s.season_number,
            "name": s.name or f"第 {s.season_number} 季",
            "episode_count": s.episode_count,
            "include_desc": "、".join(
                f"order={i.order} count={i.count} ←S{i.season_number}E{i.episode_number}"
                for i in s.include
            ) or "—",
        }
        for s in series.seasons
    ]

    logic = splitter.build_logic_series(tmdb_id, tv_show, series)
    result["reference"] = splitter.last_reference_name or "未知"
    result["split_done"] = True

    org_map = logic.org_map()
    log("INFO", f"拆分完成: 共 {len(logic.seasons)} 个虚拟季 / {len(org_map)} 集映射")
    result["group_json"] = logic_to_group_json(logic, tmdb_id)
    skipped_movies = sum(1 for season in logic.seasons
                         for em in season.episodes_map.values() if em.type != "tv")
    if skipped_movies:
        log("WARN", f"剧集组已跳过 {skipped_movies} 个电影条目(剧集组无法表达)")

    for season in logic.seasons:
        log("INFO",
            f"虚拟季 S{season.season_number} 《{season.name}》 "
            f"共 {season.episode_count()} 集, 首播 {season.air_date or '未知'}")
        result["season_rows"].append({
            "season_number": season.season_number,
            "name": season.name or "",
            "episode_count": season.episode_count(),
            "air_date": season.air_date or "未知",
        })

    for season in logic.seasons:
        for order in sorted(season.episodes_map):
            em = season.episodes_map[order]
            raw = splitter.raw_ep_lookup.get(f"S{em.season_num()}E{em.episode_num()}") or {}
            label = "(电影)" if em.type == "movie" else (raw.get("name") or "")
            result["episode_rows"].append({
                "season": season.season_number,
                "episode": order,
                "org_season": em.season_num(),
                "org_episode": em.episode_num(),
                "type": em.type,
                "air_date": raw.get("air_date") or ("" if em.type == "tv" else "—"),
                "name": label,
            })

    result["render_words"] = generate_render_words(tmdb_id, title, result["reference"], org_map)
    result["mapping_json"] = mapping_to_json(org_map)
    result["logic_json"] = logic.to_json()
    return result


# ---------------------------------------------------------------------------
# 任务 API
# ---------------------------------------------------------------------------

async def start_split(req) -> str:
    settings = build_integration_settings()
    if not settings["tmdb_key"]:
        raise ValueError("未配置 TMDB API Key，请先在「设置 → 第三方 API 集成」填写")
    run_settings = {
        **settings,
        "language": (req.language or "zh-CN").strip() or "zh-CN",
        "source": (req.source or "").strip(),
        "use_source": req.use_source,
        "priority": _parse_priority(req.priority),
        "force_reference": req.force_reference,
    }

    task_id = uuid.uuid4().hex[:12]
    task = {
        "task_id": task_id,
        "status": "running",
        "logs": [],
        "error": None,
        "result": None,
        "created_at": datetime.now().timestamp(),
    }
    with _tasks_lock:
        _tasks[task_id] = task
        _prune_tasks()

    def _log(level: str, message: str) -> None:
        _append_log(task, level, message)

    def _worker() -> None:
        try:
            _log("INFO", f"开始拆分 TMDB {req.tmdb_id}（参照优先级: {run_settings['priority']}）")
            result = run_split(run_settings, req.tmdb_id, _log)
            task["result"] = result
            task["status"] = "done"
            logger.info(f"✅ 分季拆分完成: {result.get('title')} (TMDB {req.tmdb_id})")
        except Exception as e:
            _log("ERROR", f"拆分失败: {e}")
            _log("ERROR", traceback.format_exc())
            task["error"] = str(e)
            task["status"] = "failed"
            logger.error(f"❌ 分季拆分失败: TMDB {req.tmdb_id}: {e}")

    asyncio.get_running_loop().run_in_executor(None, _worker)
    return task_id


def get_task_status(task_id: str) -> Optional[dict]:
    task = _tasks.get(task_id)
    if not task:
        return None
    return {
        "task_id": task_id,
        "status": task["status"],
        "logs": task["logs"],
        "error": task["error"],
    }


def get_task_result(task_id: str) -> Optional[dict]:
    task = _tasks.get(task_id)
    if not task:
        return None
    return task["result"]


# ---------------------------------------------------------------------------
# Gitea / GitHub 仓库推送 + SYTMDB 写入
# ---------------------------------------------------------------------------

def list_gitea_files(dir_path: str = "", provider: str = "gitea") -> list:
    st = _repo_settings(provider)
    # 返回文件与子目录（网页端逐级浏览），目录在前、按名称排序
    entries = gitea_list_dir(st["base"], st["repo"], st["branch"], (dir_path or "").strip().strip("/"),
                             st["token"], st.get("username", ""), include_dirs=True,
                             provider=provider)
    dirs = sorted((e for e in entries if e["type"] == "dir"), key=lambda e: e["path"])
    files = sorted((e for e in entries if e["type"] == "file"), key=lambda e: e["path"])
    return dirs + files


def push_render_words(task_id: str, file_path: str = "", force_manual: bool = False,
                      content: str = "", provider: str = "gitea") -> dict:
    task = _tasks.get(task_id)
    if not task or not task.get("result"):
        raise ValueError("任务不存在或尚未完成拆分")
    # 优先使用前端提交的（可能被手动编辑过的）文本，为空则回退到任务生成结果
    block_text = (content or "").strip() or (task["result"].get("render_words") or "").strip()
    if not block_text:
        raise ValueError("当前任务没有可推送的渲染词")

    m = AUTO_HEADER_RE.match(block_text)
    if not m:
        raise ValueError("渲染词文本缺少 '# [自动分季] … TMDB:xx' 头部，无法定位区块")
    tmdb_id = int(m.group(1))
    title = task["result"].get("title") or f"TMDB {tmdb_id}"

    st = _repo_settings(provider)
    name = PROVIDER_NAMES[provider]
    path = (file_path or "").strip().strip("/") or st["file_path"]
    if not path:
        raise ValueError(f"未配置{name}渲染词文件路径，请先在「设置 → 第三方 API 集成」填写或临时选择")

    import requests as _requests

    username = st.get("username", "")
    content, sha = gitea_get_file(st["base"], st["repo"], st["branch"], path,
                                  st["token"], username, provider=provider)
    content = content if content is not None else ""
    new_text, action, info = upsert_render_block(content, block_text, force_manual=force_manual)
    if action == "conflict":
        return {"action": "conflict", "info": info}

    # 手动区块冲突重推或远端刚被更新时，重试（重新读取 sha）
    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            message = (f"[Lens] 更新分季渲染词: {title} (TMDB:{tmdb_id})"
                       if action == "replaced" else
                       f"[Lens] 新增分季渲染词: {title} (TMDB:{tmdb_id})")
            resp = gitea_put_file(st["base"], st["repo"], st["branch"], path,
                                  st["token"], new_text, sha, message, username,
                                  provider=provider)
            commit = ((resp or {}).get("commit") or {}).get("sha") or ""
            verb = {"replaced": "已替换区块", "appended": "已追加到文末"}.get(action, "已写入")
            logger.info(f"📤 {name} {verb}: {st['repo']}/{path}（{info}）提交 {commit[:7]}")
            return {"action": action, "info": info, "commit": commit,
                    "message": f"{verb}：{info}（{name} {st['repo']}/{path}，分支 {st['branch']}）"}
        except _requests.HTTPError as e:
            sc = e.response.status_code if e.response is not None else 0
            if sc in (409, 422) and attempt < 2:
                content, sha = gitea_get_file(st["base"], st["repo"], st["branch"], path,
                                              st["token"], username, provider=provider)
                content = content if content is not None else ""
                new_text, action, info = upsert_render_block(content, block_text,
                                                             force_manual=force_manual)
                if action == "conflict":
                    return {"action": "conflict", "info": info}
                last_err = e
                continue
            raise
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"{PROVIDER_NAMES[provider]} 推送失败：重试次数耗尽")


def write_sytmdb(task_id: str) -> dict:
    task = _tasks.get(task_id)
    if not task or not task.get("result"):
        raise ValueError("任务不存在或尚未完成拆分")
    group_json = task["result"].get("group_json")
    groups = (group_json or {}).get("groups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("当前任务没有可写入的剧集组")

    tmdb_id = task["result"]["tmdb_id"]
    st = build_integration_settings()["sytmdb"]
    if not st["base"] or not st["token"]:
        raise ValueError("未配置 SYTMDB 服务地址和 API Token，请先在「设置 → 第三方 API 集成」填写")

    resp = library_write_episodegroup(st["base"], st["token"], tmdb_id, groups) or {}
    ok = bool(resp.get("success", True))
    message = resp.get("message") or "写入成功"
    logger.info(f"📤 SYTMDB 写入 TMDB {tmdb_id} 剧集组（{len(groups)} 组）: {message}")
    return {"ok": ok, "message": message, "groups": len(groups), "tmdb_id": tmdb_id}
