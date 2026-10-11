# -*- coding: utf-8 -*-
"""渲染词推送：Gitea 仓库文件的智能区块替换 + SYTMDB 剧集组覆盖写入。

移植自独立桌面工具 cure_splitter 的推送区段。
"""

from __future__ import annotations

import base64
import re
from typing import Optional
from urllib.parse import quote as _urlquote

import requests

AUTO_HEADER_RE = re.compile(r"^#\s*\[自动分季\].*?TMDB[:：]\s*(\d+)")


def _scan_blocks(lines: list) -> tuple:
    """扫描 [自动分季] 区块，返回 (区块列表, 非自动区块头行号列表)。

    区块 = 头部行起，到下一个 "#" 注释头行前（本工具生成的 "# 注意: …" 行不算边界）；
    区块列表元素为 (起始行, 结束行不含, tmdb_id)。
    """
    blocks: list = []
    manual_headers: list = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = AUTO_HEADER_RE.match(line)
        if m:
            j = i + 1
            while j < n and not (lines[j].startswith("#") and not lines[j].startswith("# 注意")):
                j += 1
            blocks.append((i, j, int(m.group(1))))
            i = j
        else:
            if line.startswith("#"):
                manual_headers.append(i)
            i += 1
    return blocks, manual_headers


def _block_end(lines: list, start: int) -> int:
    j = start + 1
    n = len(lines)
    while j < n and not (lines[j].startswith("#") and not lines[j].startswith("# 注意")):
        j += 1
    return j


def upsert_render_block(file_text: str, block_text: str,
                        force_manual: bool = False) -> tuple:
    """把一个 [自动分季] 渲染词区块写入汇总文件，返回 (新文本, 动作, 说明)。

    - replaced: 已有同 TMDB ID 的 [自动分季] 区块 → 原位整块替换（其余行原样保留）
    - conflict: 该 TMDB ID 只出现在手动维护的区块里 → 不动，返回说明交 UI 询问
      （force_manual=True 时直接替换那个手动区块）
    - appended: 文件里没有 → 追加到文末
    """
    tm = AUTO_HEADER_RE.match(block_text.strip())
    if not tm:
        raise ValueError("渲染词文本缺少 '# [自动分季] … TMDB:xx' 头部，无法定位区块")
    tmdb_id = int(tm.group(1))
    crlf = "\r\n" in file_text
    lines = file_text.replace("\r\n", "\n").splitlines()

    blocks, _ = _scan_blocks(lines)
    for start, end, bid in blocks:
        if bid == tmdb_id:
            body_end = end
            while body_end > start + 1 and not lines[body_end - 1].strip():
                body_end -= 1  # 原区块与下一节之间的空行留在原地
            new_lines = lines[:start] + block_text.strip("\n").splitlines() + lines[body_end:]
            text = "\n".join(new_lines).rstrip("\n") + "\n"
            return (text.replace("\n", "\r\n") if crlf else text), "replaced", f"TMDB:{tmdb_id} 区块"

    pat = re.compile(rf"tmdbid={tmdb_id}(?![0-9])")
    for idx, line in enumerate(lines):
        if any(s <= idx < e for s, e, _ in blocks):
            continue  # 其他番的自动区块里引用到本 ID（理论不该出现），跳过
        if pat.search(line):
            header_idx = idx
            while header_idx > 0 and not lines[header_idx].startswith("#"):
                header_idx -= 1
            if not force_manual:
                return file_text, "conflict", lines[header_idx].strip().lstrip("#").strip() or f"第 {header_idx + 1} 行"
            end = _block_end(lines, header_idx)
            body_end = end
            while body_end > header_idx + 1 and not lines[body_end - 1].strip():
                body_end -= 1
            new_lines = lines[:header_idx] + block_text.strip("\n").splitlines() + lines[body_end:]
            text = "\n".join(new_lines).rstrip("\n") + "\n"
            return (text.replace("\n", "\r\n") if crlf else text), "replaced", \
                f"手动区块“{lines[header_idx].strip().lstrip('#').strip()}”"

    text = file_text.replace("\r\n", "\n").rstrip("\n")
    text = (text + "\n" + block_text.strip("\n") + "\n") if text else (block_text.strip("\n") + "\n")
    return (text.replace("\n", "\r\n") if crlf else text), "appended", f"文件末尾（新增 TMDB:{tmdb_id} 区块）"


def gitea_api_headers(token: str, username: str = "") -> dict:
    """username 非空走 Basic 认证(账号+密码/令牌)，否则按纯访问令牌。"""
    h = {"Accept": "application/json"}
    if username:
        cred = base64.b64encode(f"{username}:{token}".encode("utf-8")).decode("ascii")
        h["Authorization"] = f"Basic {cred}"
    elif token:
        h["Authorization"] = f"token {token}"
    return h


def _gitea_contents_url(base: str, repo: str, path: str) -> str:
    repo_path = "/".join(_urlquote(x, safe="") for x in repo.strip("/").split("/"))
    file_path = "/".join(_urlquote(x, safe="") for x in path.strip("/").split("/"))
    return f"{base.rstrip('/')}/api/v1/repos/{repo_path}/contents/{file_path}"


def _contents_url(base: str, repo: str, path: str, provider: str = "gitea") -> str:
    """Contents API 地址：gitea 与 _gitea_contents_url 一致（/api/v1 前缀）；
    github 用 api.github.com（无前缀），私有部署 GHES 自动补 /api/v3。"""
    base = base.rstrip("/")
    if provider == "gitea":
        base += "/api/v1"
    elif provider == "github" and "api.github.com" not in base and not base.endswith("/api/v3"):
        base += "/api/v3"
    repo_path = "/".join(_urlquote(x, safe="") for x in repo.strip("/").split("/"))
    file_path = "/".join(_urlquote(x, safe="") for x in path.strip("/").split("/"))
    return f"{base}/repos/{repo_path}/contents/{file_path}"


def _contents_headers(token: str, username: str, provider: str = "gitea") -> dict:
    """gitea 与原版一致；github 统一 Bearer PAT。"""
    if provider == "github":
        h = {"Accept": "application/vnd.github+json"}
        if token:
            h["Authorization"] = f"Bearer {token}"
        return h
    return gitea_api_headers(token, username)


def gitea_list_dir(base: str, repo: str, branch: str, dir_path: str,
                   token: str, username: str = "", include_dirs: bool = False,
                   provider: str = "gitea") -> list:
    """列出仓库目录内容；目录不存在返回空表。dir_path 为空表示仓库根目录。

    include_dirs=False（默认，与原版一致）仅返回文件路径列表；
    include_dirs=True 时返回 [{"path": ..., "type": "file"|"dir"}]，供网页端逐级浏览目录。
    provider='gitea'（默认）与原版行为一致；provider='github' 走 GitHub Contents API（结构相同）。
    """
    r = requests.get(_contents_url(base, repo, dir_path, provider), params={"ref": branch},
                     headers=_contents_headers(token, username, provider), timeout=(10, 30))
    if r.status_code == 404:
        return []
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        data = [data]
    if include_dirs:
        return [{"path": e.get("path") or "", "type": e.get("type") or ""}
                for e in data
                if isinstance(e, dict) and e.get("type") in ("file", "dir")]
    return [e.get("path") or "" for e in data
            if isinstance(e, dict) and e.get("type") == "file"]


def gitea_get_file(base: str, repo: str, branch: str, path: str, token: str,
                   username: str = "", provider: str = "gitea") -> tuple:
    """读取仓库文件，返回 (文本, sha)；文件不存在返回 (None, None)。

    github 下超过 1MB 的文件 Contents API 不内联返回内容，自动降级用 raw 媒体类型重取。
    """
    url = _contents_url(base, repo, path, provider)
    headers = _contents_headers(token, username, provider)
    r = requests.get(url, params={"ref": branch}, headers=headers, timeout=(10, 30))
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    data = r.json()
    raw = data.get("content") or ""
    if not raw and (data.get("size") or 0) > 0:
        if provider == "github":
            r2 = requests.get(url, params={"ref": branch},
                              headers={**headers, "Accept": "application/vnd.github.raw"},
                              timeout=(10, 30))
            r2.raise_for_status()
            return r2.text, data.get("sha")
        raise ValueError("文件过大，Gitea 未返回内容（contents API 限制）")
    content = base64.b64decode(raw).decode("utf-8")
    return content, data.get("sha")


def gitea_put_file(base: str, repo: str, branch: str, path: str, token: str,
                   content_text: str, sha: Optional[str], message: str,
                   username: str = "", provider: str = "gitea") -> dict:
    """创建/更新仓库文件（一次调用 = 一次 commit）。请求体两种平台完全一致。"""
    body: dict = {
        "content": base64.b64encode(content_text.encode("utf-8")).decode("ascii"),
        "branch": branch,
        "message": message,
    }
    if sha:
        body["sha"] = sha
    r = requests.put(_contents_url(base, repo, path, provider), json=body,
                     headers=_contents_headers(token, username, provider), timeout=(10, 30))
    r.raise_for_status()
    return r.json() if r.content else {}


def library_write_episodegroup(base: str, token: str, tmdb_id: int, groups: list) -> dict:
    """把剧集组覆盖写入 SYTMDB 服务：文件不存在先 POST 创建，再 PUT 完整 groups。"""
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    url = f"{base.rstrip('/')}/api/tv/{tmdb_id}/episodegroup"
    r = requests.get(url, headers=headers, timeout=(10, 30))
    if r.status_code != 200:
        rp = requests.post(url, headers=headers, timeout=(10, 30))
        if rp.status_code >= 400:
            raise RuntimeError(f"创建剧集组文件失败 (HTTP {rp.status_code}): {rp.text[:300]}")
    rw = requests.put(url, headers=headers, json={"groups": groups}, timeout=(10, 30))
    if rw.status_code >= 400:
        raise RuntimeError(f"写入剧集组失败 (HTTP {rw.status_code}): {rw.text[:300]}")
    return rw.json() if rw.content else {}
