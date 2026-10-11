# -*- coding: utf-8 -*-
"""番剧分季拆分的外部 API 客户端：TMDB / TVDB / Bangumi / CureTMDb 规则表。

移植自 CureTMDbAnime（Go）与独立桌面工具 cure_splitter 的客户端区段，
Bangumi 季号提取 1:1 对应 internal/references/bangumi.go。
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import quote as _urlquote

import requests

from .media_models import SeasonEntry, SeriesEntry

DEFAULT_CURE_SOURCE = "https://raw.githubusercontent.com/wikrin/CureTMDb/main/tv.json"
DEFAULT_TMDB_BASE = "https://api.themoviedb.org/3"
DEFAULT_TMDB_LANGUAGE = "zh-CN"
# 上游 Go 版内置的 TVDB v4 默认 Key，可在系统集成配置里覆盖
DEFAULT_TVDB_BASE = "https://api4.thetvdb.com/v4"
DEFAULT_TVDB_KEY = "d3158670-26f0-48bb-9267-2f63781dca6b"
DEFAULT_BANGUMI_BASE = "https://api.bgm.tv"

ANIME_GENRE_ID = 16
TMDB_TIMEOUT = 25
TVDB_TIMEOUT = 25
BANGUMI_TIMEOUT = 25


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------

def log_default(level: str, message: str) -> None:
    print(f"[{level}] {message}")


def strip_punctuations_spaces(text: str) -> str:
    """等价 Go 的 [\\p{P}\\p{S}\\s}] 清洗：去掉标点、符号与空白。"""
    out = []
    for ch in text:
        if ch.isspace():
            continue
        cat = unicodedata.category(ch)
        if cat.startswith("P") or cat.startswith("S"):
            continue
        out.append(ch)
    return "".join(out)


# ---------------------------------------------------------------------------
# Bangumi 季号提取（1:1 移植自 internal/references/bangumi.go）
# ---------------------------------------------------------------------------

_RE_CHINESE_SEASON = re.compile(r"[第\s]*([一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾0-9]+)\s*(?:季|期)")
_RE_ROMAN_SEASON = re.compile(r"(?i)(?:Season|S)\s*([IVXLCDM]+)")
_RE_ENGLISH_SEASON = re.compile(r"(?:Season|S)\s*([0-9]+)")
_RE_ORDINAL_SEASON = re.compile(r"([0-9]{1,2})(?:st|nd|rd|th)\s+season")
_RE_FULL_CHINESE = re.compile(r"^[零一二三四五六七八九十壹贰叁肆伍陆柒捌玖拾]+$")
_RE_FULL_ROMAN = re.compile(r"^[IVXLCDM]+$")

_CN_DIGITS = {"零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
              "七": 7, "八": 8, "九": 9, "壹": 1, "贰": 2, "叁": 3, "肆": 4,
              "伍": 5, "陆": 6, "柒": 7, "捌": 8, "玖": 9}
_CN_UNITS = {"十": 10, "拾": 10}
_ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def number_converter(s: str) -> int:
    """把数字字符串（阿拉伯/中文/罗马）转换为整数，失败返回 0。"""
    try:
        return int(s)
    except (TypeError, ValueError):
        pass

    if s and _RE_FULL_CHINESE.match(s):
        result, temp = 0, 0
        for r in s:
            if r in _CN_DIGITS:
                temp = _CN_DIGITS[r]
            elif r in _CN_UNITS:
                if temp == 0:
                    temp = 1
                result += temp * _CN_UNITS[r]
                temp = 0
            else:
                return 0
        result += temp
        return result

    if s:
        s_upper = s.upper()
        if _RE_FULL_ROMAN.match(s_upper):
            total, prev = 0, 0
            for ch in reversed(s_upper):
                curr = _ROMAN_VALUES[ch]
                if curr < prev:
                    total -= curr
                else:
                    total += curr
                prev = curr
            if total != 0:
                return total
    return 0


def extract_season_number(name_cn: str, name: str) -> int:
    """从 Bangumi 标题提取季号；正则顺序与 Go 一致：中文 → 罗马 → 英文 → 序数词。"""
    patterns = (_RE_CHINESE_SEASON, _RE_ROMAN_SEASON, _RE_ENGLISH_SEASON, _RE_ORDINAL_SEASON)

    def parse(text: str) -> int:
        if not text:
            return 0
        for pat in patterns:
            m = pat.search(text)
            if m:
                num = number_converter(m.group(1))
                if num != 0:
                    return num
                # 匹配成功但无法转换，Go 侧返回默认季号 1
                return 1
        return 0

    num = parse(name_cn)
    if num != 0:
        return num
    num = parse(name)
    if num != 0:
        return num
    return 1


# ---------------------------------------------------------------------------
# API 客户端
# ---------------------------------------------------------------------------

def build_proxies(proxy: str) -> Optional[dict]:
    proxy = (proxy or "").strip()
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


class TMDBClient:
    def __init__(self, api_key: str, base: str, language: str, proxy: str, log: Callable):
        if not api_key:
            raise ValueError("未配置 TMDB API Key")
        self.session = requests.Session()
        self.session.proxies = build_proxies(proxy)
        self.api_key = api_key
        self.base = base.rstrip("/") or DEFAULT_TMDB_BASE
        self.language = language or DEFAULT_TMDB_LANGUAGE
        self.log = log

    def _get(self, path: str, **params) -> Optional[dict]:
        params["api_key"] = self.api_key
        params.setdefault("language", self.language)
        resp = self.session.get(f"{self.base}{path}", params=params, timeout=TMDB_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def tv_detail(self, tmdb_id: int) -> Optional[dict]:
        # 与 Go 上游一致：强制 append external_ids 以取得 tvdb_id
        return self._get(f"/tv/{tmdb_id}", append_to_response="external_ids")

    def season_detail(self, tmdb_id: int, season: int) -> Optional[dict]:
        try:
            return self._get(f"/tv/{tmdb_id}/season/{season}")
        except requests.HTTPError as e:
            self.log("WARN", f"获取 TMDB 季详情失败: ID={tmdb_id} 季={season}: {e}")
            return None

    def movie_detail(self, movie_id: int) -> Optional[dict]:
        try:
            return self._get(f"/movie/{movie_id}")
        except requests.HTTPError as e:
            self.log("WARN", f"获取 TMDB 电影详情失败: ID={movie_id}: {e}")
            return None


class TVDBClient:
    def __init__(self, api_key: str, base: str, proxy: str, log: Callable):
        self.session = requests.Session()
        self.session.proxies = build_proxies(proxy)
        self.api_key = (api_key or "").strip()
        self.base = base.rstrip("/") or DEFAULT_TVDB_BASE
        self.log = log
        self._token: str = ""

    def get_series_entry(self, tvdb_id: int) -> Optional[SeriesEntry]:
        if not self.api_key:
            self.log("WARN", "TVDB API Key 未配置，跳过 TVDB 系列数据查询")
            return None
        if not self._token:
            resp = self.session.post(f"{self.base}/login", json={"apikey": self.api_key}, timeout=TVDB_TIMEOUT)
            resp.raise_for_status()
            token = (resp.json().get("data") or {}).get("token")
            if not token:
                raise ValueError("TVDB 登录响应缺少 token")
            self._token = token
            self.log("INFO", "TVDB token 获取成功")

        resp = self.session.get(
            f"{self.base}/series/{tvdb_id}/episodes/official/eng",
            params={"page": "0"},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=TVDB_TIMEOUT,
        )
        resp.raise_for_status()
        data = (resp.json() or {}).get("data") or {}
        episodes = data.get("episodes") or []
        if not episodes:
            self.log("INFO", f"TVDB {tvdb_id} 未返回剧集数据")
            return None

        counts: dict = {}
        for ep in episodes:
            season_number = int(ep.get("seasonNumber") or 0)
            number = int(ep.get("number") or 0)
            if season_number <= 0 or number <= 0:
                continue
            counts[season_number] = counts.get(season_number, 0) + 1
        if not counts:
            self.log("WARN", f"TVDB {tvdb_id} 返回 {len(episodes)} 集但没有可用季信息")
            return None

        seasons = [SeasonEntry(season_number=n, episode_count=c) for n, c in sorted(counts.items())]
        for s in seasons:
            self.log("INFO", f"{data.get('name', '')} 季 {s.season_number}，集数: {s.episode_count}")
        return SeriesEntry(name=data.get("name"), seasons=seasons)


class BangumiClient:
    UA = "cure_splitter (https://github.com/wikrin/CureTMDbAnime)"

    def __init__(self, base: str, proxy: str, log: Callable, token: str = ""):
        self.session = requests.Session()
        self.session.proxies = build_proxies(proxy)
        self.session.headers["User-Agent"] = self.UA
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        self.base = (base.rstrip("/") + "/") if (base or "").strip() else DEFAULT_BANGUMI_BASE
        self.log = log

    def _invoke(self, method: str, endpoint: str, **kwargs) -> Any:
        resp = self.session.request(method, f"{self.base}{endpoint}", timeout=BANGUMI_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def search(self, title: str, air_date: str) -> list:
        """按原名 + 首播日期 ±10 天窗口搜索动画条目。"""
        if not title or not air_date:
            return []
        from datetime import date, timedelta

        d = date.fromisoformat(air_date)
        start = (d - timedelta(days=10)).isoformat()
        end = (d + timedelta(days=10)).isoformat()
        body = {
            "keyword": strip_punctuations_spaces(title),
            "sort": "match",
            "filter": {"type": [2], "air_date": [f">={start}", f"<={end}"]},
        }
        resp = self._invoke("POST", "v0/search/subjects", json=body)
        data = (resp or {}).get("data")
        if not isinstance(data, list):
            raise ValueError("Bangumi 搜索响应 data 字段格式错误")
        return [item for item in data if isinstance(item, dict)]

    def detail(self, bid: int) -> Optional[dict]:
        return self._invoke("GET", f"v0/subjects/{bid}")

    def subjects(self, bid: int) -> list:
        resp = self._invoke("GET", f"v0/subjects/{bid}/subjects")
        if isinstance(resp, list):
            data = resp
        elif isinstance(resp, dict):
            data = resp.get("")
            if not isinstance(data, list):
                raise ValueError("Bangumi 相关条目响应格式错误")
        else:
            raise ValueError("Bangumi 相关条目响应格式错误")
        return [item for item in data if isinstance(item, dict)]

    def episodes(self, bid: int) -> list:
        resp = self._invoke("GET", "v0/episodes", params={"subject_id": bid})
        data = (resp or {}).get("data")
        if not isinstance(data, list):
            raise ValueError("Bangumi 剧集列表响应 data 字段格式错误")
        return [item for item in data if isinstance(item, dict)]

    def get_all_sequels(self, bid: int) -> list:
        """沿"续集"关系递归收集整个系列的条目 ID（前序遍历）。"""
        seen: set = set()
        sequence: list = []

        def walk(current: int) -> None:
            if current in seen:
                return
            seen.add(current)
            sequence.append(current)
            try:
                related = self.subjects(current)
            except Exception as e:
                self.log("ERROR", f"获取 Bangumi {current} 相关条目失败: {e}")
                return
            for item in related:
                if item.get("relation") == "续集":
                    rid = item.get("id")
                    if isinstance(rid, (int, float)):
                        walk(int(rid))

        walk(bid)
        self.log("INFO", f"Bangumi ID {bid} 续集条目: {sequence}")
        return sequence

    def is_first_episode_sequential(self, sid: int) -> bool:
        """首集的 sort 与 ep 是否相等（不等说明该条目不是从第 1 集开始）。"""
        episodes = self.episodes(sid)
        if not episodes:
            raise ValueError(f"Bangumi ID '{sid}' 剧集列表为空")
        ep0 = episodes[0]
        sort_val, ep_val = ep0.get("sort"), ep0.get("ep")
        if not isinstance(sort_val, (int, float)) or not isinstance(ep_val, (int, float)):
            return False
        return int(sort_val) == int(ep_val)

    def season_info(self, item: dict) -> Optional[SeriesEntry]:
        """把 Bangumi 系列条目转成分季定义。"""
        bid = item.get("id")
        if not isinstance(bid, (int, float)):
            return None
        sids = self.get_all_sequels(int(bid))
        if len(sids) < 2:
            self.log("INFO", "Bangumi 系列仅一个条目，不进行拆分")
            return None

        bgm_seasons: dict = {}
        for sid in sids:
            try:
                d = self.detail(sid)
            except Exception as e:
                self.log("ERROR", f"获取 Bangumi ID {sid} 详情失败: {e}")
                continue
            if not d:
                self.log("WARN", f"Bangumi ID {sid} 详情为空")
                continue
            platform = d.get("platform")
            if platform in ("剧场版", "OVA"):
                self.log("INFO", f"{d.get('name_cn')} ID={sid} platform={platform}，跳过处理")
                continue

            name_cn = d.get("name_cn") if isinstance(d.get("name_cn"), str) else ""
            name = d.get("name") if isinstance(d.get("name"), str) else ""
            num = extract_season_number(name_cn, name)

            eps = 12
            for key in ("eps", "total_episodes"):
                val = d.get(key)
                if isinstance(val, (int, float)) and val > 0:
                    eps = int(val)
                    break

            if num not in bgm_seasons:
                bgm_seasons[num] = SeasonEntry(season_number=num, episode_count=eps, name=name_cn)
                continue

            try:
                sequential = self.is_first_episode_sequential(sid)
            except Exception as e:
                self.log("ERROR", f"{e}")
                bgm_seasons[num].episode_count += eps
                continue
            if sequential:
                new_num = max(bgm_seasons) + 1
                bgm_seasons[new_num] = SeasonEntry(season_number=new_num, episode_count=eps, name=name_cn)
            else:
                bgm_seasons[num].episode_count += eps

        seasons = [bgm_seasons[k] for k in sorted(bgm_seasons)]
        return SeriesEntry(name=item.get("name_cn"), seasons=seasons)


def load_cure_source(source: str, proxy: str, log: Callable) -> dict:
    """加载 CureTMDb 规则表：支持 http(s) URL 或本地文件路径。"""
    source = (source or "").strip()
    if not source:
        return {}
    if source.startswith("http://") or source.startswith("https://"):
        resp = requests.get(source, proxies=build_proxies(proxy), timeout=30)
        resp.raise_for_status()
        return resp.json()
    text = Path(source).read_text(encoding="utf-8")
    return json.loads(text)
