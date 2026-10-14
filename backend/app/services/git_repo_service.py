# -*- coding: utf-8 -*-
"""代码仓库归档下载：Gitea / GitHub 两个 provider 通用。

功能与桌面版 gitea_downloader 一致：列出账号可见的仓库，把 tar.gz / zip 归档拉回本地。

两个平台的接口差异都在 PROVIDERS 里收敛掉了：

  | 项目     | Gitea                                | GitHub                                  |
  |----------|--------------------------------------|-----------------------------------------|
  | 列仓库   | GET {base}/api/v1/user/repos         | GET {base}/user/repos                   |
  | 翻页     | page + limit（上限 50）              | page + per_page（上限 100）             |
  | 归档     | /repos/{o}/{r}/archive/{ref}.tar.gz  | /repos/{o}/{r}/tarball/{ref}            |
  | 认证     | Basic(用户名:令牌) 或 `token` 头     | Bearer 令牌                             |

连接信息复用「设置 → 第三方 API 集成」里的 Gitea / GitHub 配置。

注意：只下载仓库归档（代码、分支、tag、历史），**不含** issues / PR /
用户 / 附件等数据库内容。要完整实例备份得用 `gitea dump`，那是另一条路。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List
from urllib.parse import quote

import httpx

from app.core.config_manager import get_config
from app.modules.cure_splitter.push import gitea_api_headers
from app.utils.http_client import get_async_client
from app.utils.logger import logger

MAX_PAGES = 200                       # 兜底，防止异常情况下翻页死循环
ARCHIVE_FORMATS = ("tar.gz", "zip")
PROGRESS_STEP = 100 * 1024 * 1024     # 每 100MB 打一条进度日志
DEFAULT_PAGE_SIZE = 50


def _enc(value: Any) -> str:
    return quote(str(value), safe="")


# --------------------------------------------------------------- 认证头
def _gitea_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    # 沿用 cure_splitter 的约定：有用户名走 Basic，否则走 token 头
    return gitea_api_headers(cfg["token"], cfg["username"])


def _github_headers(cfg: Dict[str, Any]) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if cfg["token"]:
        headers["Authorization"] = f"Bearer {cfg['token']}"
    return headers


# --------------------------------------------------------------- 地址构造
def _gitea_api_base(base: str) -> str:
    return f"{base.rstrip('/')}/api/v1"


def _github_api_base(base: str) -> str:
    """github.com 直接用；私有部署 GHES 自动补 /api/v3（与 cure_splitter 一致）。"""
    base = base.rstrip("/")
    if "api.github.com" in base or base.endswith("/api/v3"):
        return base
    return base + "/api/v3"


def _gitea_archive_url(api: str, base: str, owner: str, repo: str, ref: str, fmt: str) -> str:
    return f"{api}/repos/{_enc(owner)}/{_enc(repo)}/archive/{_enc(ref)}.{fmt}"


def _gitea_web_archive(base: str, owner: str, repo: str, ref: str, fmt: str) -> str:
    """老版本 Gitea 没有 API 归档接口时的回退地址（对应桌面脚本的做法）。"""
    return f"{base}/{_enc(owner)}/{_enc(repo)}/archive/{_enc(ref)}.{fmt}"


def _github_archive_url(api: str, base: str, owner: str, repo: str, ref: str, fmt: str) -> str:
    kind = "zipball" if fmt == "zip" else "tarball"
    return f"{api}/repos/{_enc(owner)}/{_enc(repo)}/{kind}/{_enc(ref)}"


PROVIDERS: Dict[str, Dict[str, Any]] = {
    "gitea": {
        "label": "Gitea",
        "config_key": "gitea",
        "page_size": 50,
        "requires_auth": False,        # 用户名或令牌任一即可
        "api_base": _gitea_api_base,
        "list_params": lambda page, size: {"page": page, "limit": size},
        "headers": _gitea_headers,
        "archive_url": _gitea_archive_url,
        "web_archive": _gitea_web_archive,
    },
    "github": {
        "label": "GitHub",
        "config_key": "github",
        "page_size": 100,              # GitHub 的 per_page 上限就是 100
        "requires_auth": True,         # GitHub 必须带令牌
        "api_base": _github_api_base,
        "list_params": lambda page, size: {
            "page": page,
            "per_page": size,
            "sort": "updated",
            "affiliation": "owner,collaborator,organization_member",
        },
        "headers": _github_headers,
        "archive_url": _github_archive_url,
        "web_archive": None,           # GitHub 不需要回退，tarball/zipball 一直都有
    },
}


def humanize_error(e: Exception, label: str = "Gitea") -> str:
    """把底层异常翻译成用户能看懂的话。"""
    text = str(e)

    # SSL 必须先判：httpx 会把证书错误包在 ConnectError 里，
    # 否则会被下面的"无法连接"分支吞掉，提示就指错方向了。
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text:
        return f"SSL 证书校验失败：自签名证书的实例请在「设置 → {label} 仓库集成」勾选「忽略 SSL 证书验证」"

    if isinstance(e, httpx.ConnectTimeout):
        return f"连接 {label} 超时，请检查网络或服务状态"
    if isinstance(e, httpx.ConnectError):
        return f"无法连接到 {label}，请检查地址是否正确、服务是否在线（或网络能否访问外网）"
    if isinstance(e, httpx.ReadTimeout):
        return f"{label} 响应超时，请稍后重试"
    if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
        code = e.response.status_code
        if code == 401:
            return f"认证失败（401）：{label} 账号或令牌不正确；开启了两步验证的账号必须用访问令牌"
        if code == 403:
            if label == "GitHub":
                return "没有权限或被限流（403）：检查令牌是否具备 repo 读取权限，或稍后重试（GitHub 有调用频率限制）"
            return "没有权限（403）：当前账号无权访问该仓库"
        if code == 404:
            return f"接口或仓库不存在（404）：请确认 {label} 地址与服务版本"
        return f"{label} 返回 HTTP {code}"
    return text


class GitRepoService:
    """Gitea / GitHub 通用的仓库归档下载。"""

    # --------------------------------------------------------------- 配置
    @staticmethod
    def _spec(provider: str) -> Dict[str, Any]:
        spec = PROVIDERS.get(provider)
        if not spec:
            raise Exception(f"不支持的仓库服务: {provider}")
        return spec

    @classmethod
    def load_config(cls, provider: str) -> Dict[str, Any]:
        """读取并校验连接配置；缺失时直接抛异常（不要等任务跑到一半才失败）。"""
        spec = cls._spec(provider)
        label = spec["label"]
        cfg = get_config().get(spec["config_key"]) or {}

        base = (cfg.get("base") or "").strip().rstrip("/")
        if provider == "github" and not base:
            base = "https://api.github.com"
        if not base:
            raise Exception(f"未配置 {label} 服务地址（设置 → 第三方 API 集成 → {label} 仓库集成）")
        if not base.startswith(("http://", "https://")):
            base = "https://" + base

        token = (cfg.get("token") or "").strip()
        username = (cfg.get("username") or "").strip()

        if spec["requires_auth"] and not token:
            raise Exception(f"未配置 {label} 访问令牌（设置 → 第三方 API 集成 → {label} 仓库集成）")
        if not spec["requires_auth"] and not token and not username:
            raise Exception(f"未配置 {label} 账号或访问令牌")

        return {
            "provider": provider,
            "label": label,
            "base": base,
            "api": spec["api_base"](base),
            "username": username,
            "token": token,
            "no_ssl": bool(cfg.get("no_ssl")),
        }

    @staticmethod
    def _client(cfg: Dict[str, Any], timeout: float) -> httpx.AsyncClient:
        # 自建实例多在局域网，强制直连、不走全局代理
        spec = PROVIDERS[cfg["provider"]]
        return get_async_client(
            timeout=timeout,
            headers=spec["headers"](cfg),
            use_proxy=False,
            verify=not cfg["no_ssl"],
        )

    # --------------------------------------------------------------- 列仓库
    @classmethod
    async def list_repos(cls, provider: str) -> List[Dict[str, Any]]:
        """账号可见的所有仓库（自己创建的、协作的、所在组织的）。"""
        spec = cls._spec(provider)
        cfg = cls.load_config(provider)
        label = spec["label"]
        size = spec.get("page_size") or DEFAULT_PAGE_SIZE

        repos: List[Dict[str, Any]] = []
        seen = set()

        try:
            async with cls._client(cfg, 30.0) as client:
                for page in range(1, MAX_PAGES + 1):
                    resp = await client.get(
                        f"{cfg['api']}/user/repos",
                        params=spec["list_params"](page, size),
                    )
                    resp.raise_for_status()
                    batch = resp.json()
                    if not isinstance(batch, list):
                        raise Exception(f"{label} 返回了异常内容：{str(batch)[:200]}")

                    fresh = [r for r in batch if r.get("id") not in seen]
                    if not fresh:
                        break
                    seen.update(r.get("id") for r in fresh)
                    repos.extend(fresh)

                    if len(batch) < size:      # 最后一页
                        break
        except Exception as e:
            raise Exception(humanize_error(e, label))

        return repos

    # --------------------------------------------------------------- 下载
    @classmethod
    async def download_archive(
        cls,
        cfg: Dict[str, Any],
        owner: str,
        repo: str,
        ref: str,
        fmt: str,
        dest_path: str,
    ) -> str:
        """把某个仓库的归档下载到 dest_path（先写 .part，成功后再改名）。"""
        if fmt not in ARCHIVE_FORMATS:
            raise Exception(f"不支持的归档格式: {fmt}")

        provider = cfg["provider"]
        spec = cls._spec(provider)
        label = spec["label"]

        ref = (ref or "").strip() or "main"
        api_url = spec["archive_url"](cfg["api"], cfg["base"], owner, repo, ref, fmt)
        web_url = (
            spec["web_archive"](cfg["base"], owner, repo, ref, fmt)
            if spec["web_archive"] else None
        )

        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        tmp_path = dest_path + ".part"
        written = 0
        next_log = PROGRESS_STEP

        try:
            async with cls._client(cfg, 120.0) as client:
                resp = await client.send(client.build_request("GET", api_url), stream=True)
                try:
                    if resp.status_code == 404 and web_url:
                        # 老版本 Gitea 没有 API 归档接口，回退网页下载地址
                        await resp.aclose()
                        params = {"token": cfg["token"]} if cfg["token"] else None
                        resp = await client.send(
                            client.build_request("GET", web_url, params=params), stream=True
                        )

                    resp.raise_for_status()

                    with open(tmp_path, "wb") as fh:
                        async for chunk in resp.aiter_bytes(256 * 1024):
                            if not chunk:
                                continue
                            fh.write(chunk)
                            written += len(chunk)
                            if written >= next_log:
                                logger.info(
                                    f"⬇️ [{label}] {owner}/{repo} 已下载 {written // (1024 * 1024)} MB"
                                )
                                next_log += PROGRESS_STEP
                finally:
                    await resp.aclose()

            os.replace(tmp_path, dest_path)
            return dest_path
        except Exception as e:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise Exception(humanize_error(e, label))
