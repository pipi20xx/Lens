# -*- coding: utf-8 -*-
"""Gitea 仓库归档下载：列出账号可见的仓库，并把 tar.gz / zip 归档拉回本地。

与「设置 → 第三方 API 集成 → Gitea 仓库集成」共用同一份连接配置
（base / username / token），认证方式沿用 cure_splitter 的约定：
填了用户名走 Basic 认证，否则走 `token` 头。

注意这里只下载仓库归档（代码、分支、tag、历史），**不含** issues / PR /
用户 / 附件等数据库内容。要完整实例备份得用 `gitea dump`，那是另一条路。
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

from app.core.config_manager import get_config
from app.modules.cure_splitter.push import gitea_api_headers
from app.utils.http_client import get_async_client
from app.utils.logger import logger

PAGE_SIZE = 50
MAX_PAGES = 200                       # 兜底，防止异常情况下翻页死循环
ARCHIVE_FORMATS = ("tar.gz", "zip")
PROGRESS_STEP = 100 * 1024 * 1024     # 每 100MB 打一条进度日志


def _enc(value: Any) -> str:
    return quote(str(value), safe="")


def humanize_error(e: Exception) -> str:
    """把底层异常翻译成用户能看懂的话。"""
    text = str(e)

    # SSL 必须先判：httpx 会把证书错误包在 ConnectError 里，
    # 否则会被下面的"无法连接"分支吞掉，提示就指错方向了。
    if "CERTIFICATE_VERIFY_FAILED" in text or "certificate verify failed" in text:
        return "SSL 证书校验失败：自签名证书的实例请在「设置 → Gitea 仓库集成」勾选「忽略 SSL 证书验证」"

    if isinstance(e, httpx.ConnectTimeout):
        return "连接 Gitea 超时，请检查网络或服务状态"
    if isinstance(e, httpx.ConnectError):
        return "无法连接到 Gitea 服务器，请检查地址是否正确、服务是否在线"
    if isinstance(e, httpx.ReadTimeout):
        return "Gitea 响应超时，请稍后重试"
    if isinstance(e, httpx.HTTPStatusError) and e.response is not None:
        code = e.response.status_code
        if code == 401:
            return "认证失败（401）：账号或令牌不正确；开启了两步验证的账号必须用访问令牌"
        if code == 403:
            return "没有权限（403）：当前账号无权访问该仓库"
        if code == 404:
            return "接口或仓库不存在（404）：请确认 Gitea 地址与版本"
        return f"Gitea 返回 HTTP {code}"
    return text


class GiteaService:
    # ------------------------------------------------------------- 连接配置
    @staticmethod
    def load_config() -> Dict[str, Any]:
        """读取并校验 Gitea 连接配置；缺失时直接抛异常（不要让任务跑到一半才失败）。"""
        cfg = get_config().get("gitea") or {}
        base = (cfg.get("base") or "").strip().rstrip("/")
        if not base:
            raise Exception("未配置 Gitea 服务地址（设置 → 第三方 API 集成 → Gitea 仓库集成）")
        if not base.startswith(("http://", "https://")):
            base = "https://" + base

        token = (cfg.get("token") or "").strip()
        username = (cfg.get("username") or "").strip()
        if not token and not username:
            raise Exception("未配置 Gitea 账号或访问令牌")

        return {
            "base": base,
            "api": f"{base}/api/v1",
            "username": username,
            "token": token,
            "no_ssl": bool(cfg.get("no_ssl")),
        }

    @staticmethod
    def _client(cfg: Dict[str, Any], timeout: float) -> httpx.AsyncClient:
        # Gitea 一般是局域网自建，强制直连、不走全局代理
        return get_async_client(
            timeout=timeout,
            headers=gitea_api_headers(cfg["token"], cfg["username"]),
            use_proxy=False,
            verify=not cfg["no_ssl"],
        )

    # --------------------------------------------------------------- 列仓库
    @classmethod
    async def list_repos(cls) -> List[Dict[str, Any]]:
        """当前账号拥有或可访问的所有仓库（自己创建的、协作的、所在组织的）。"""
        cfg = cls.load_config()
        repos: List[Dict[str, Any]] = []
        seen = set()

        try:
            async with cls._client(cfg, 30.0) as client:
                for page in range(1, MAX_PAGES + 1):
                    resp = await client.get(
                        f"{cfg['api']}/user/repos",
                        params={"page": page, "limit": PAGE_SIZE},
                    )
                    resp.raise_for_status()
                    batch = resp.json()
                    if not isinstance(batch, list):
                        raise Exception(f"Gitea 返回了异常内容：{str(batch)[:200]}")

                    fresh = [r for r in batch if r.get("id") not in seen]
                    if not fresh:
                        break
                    seen.update(r.get("id") for r in fresh)
                    repos.extend(fresh)

                    total = resp.headers.get("X-Total-Count")
                    if (total and len(repos) >= int(total)) or len(batch) < PAGE_SIZE:
                        break
        except Exception as e:
            raise Exception(humanize_error(e))

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

        ref = (ref or "").strip() or "HEAD"
        api_url = f"{cfg['api']}/repos/{_enc(owner)}/{_enc(repo)}/archive/{_enc(ref)}.{fmt}"
        # 老版本 Gitea 没有 API 归档接口，回退到网页下载地址
        web_url = f"{cfg['base']}/{_enc(owner)}/{_enc(repo)}/archive/{_enc(ref)}.{fmt}"

        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        tmp_path = dest_path + ".part"
        written = 0
        next_log = PROGRESS_STEP

        try:
            async with cls._client(cfg, 120.0) as client:
                resp = await client.send(client.build_request("GET", api_url), stream=True)
                try:
                    if resp.status_code == 404:
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
                                    f"⬇️ [Gitea] {owner}/{repo} 已下载 {written // (1024 * 1024)} MB"
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
            raise Exception(humanize_error(e))
