# -*- coding: utf-8 -*-
"""番剧分季拆分主算法：并发拉原始季 → 同日去重 → 按播出日期摊平 → 按定义重灌切虚拟季，
以及渲染词 / 剧集组（TMDB episode group）生成。

移植自 CureTMDbAnime（Go）internal/processor/splitter.go 与独立桌面工具 cure_splitter。
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Optional

from .media_clients import (
    ANIME_GENRE_ID,
    TMDBClient,
    TVDBClient,
    BangumiClient,
    extract_season_number,
)
from .media_models import EpisodeMap, LogicSeries, SeriesEntry


def completeness_score(episode: dict) -> int:
    """集数据完整度评分：name+10 overview+8 still_path+5 vote_average+3 其余字段各+1。"""
    score = 0
    if episode.get("name"):
        score += 10
    if episode.get("overview"):
        score += 8
    if episode.get("still_path"):
        score += 5
    va = episode.get("vote_average")
    if isinstance(va, (int, float)) and va != 0:
        score += 3
    skip = {"name", "overview", "still_path", "vote_average", "air_date",
            "season_number", "episode_number", "id"}
    for k, v in episode.items():
        if k in skip:
            continue
        if v is None or isinstance(v, bool):
            continue
        if isinstance(v, str) and v == "":
            continue
        score += 1
    return score


@dataclass
class _AugEpisode:
    episode: dict
    season_idx: int
    ep_idx: int
    season_number: int

    def slot(self) -> tuple:
        return (self.season_idx, self.ep_idx)

    def is_earlier_than(self, other: "_AugEpisode") -> bool:
        return self.slot() < other.slot()

    def is_better_content_than(self, other: "_AugEpisode") -> bool:
        score, other_score = completeness_score(self.episode), completeness_score(other.episode)
        if score != other_score:
            return score > other_score
        return self.is_earlier_than(other)


def remove_duplicate_episodes(raw_seasons: list) -> list:
    """同 air_date 跨季去重：保留最早槽位的位置字段，内容取最完整者。"""
    by_air_date: dict = {}
    for season_idx, season in enumerate(raw_seasons):
        season_num = int(season.get("season_number") or 0)
        for ep_idx, ep in enumerate(season.get("episodes") or []):
            air = ep.get("air_date") or ""
            if not air:
                continue
            by_air_date.setdefault(air, []).append(_AugEpisode(ep, season_idx, ep_idx, season_num))

    to_remove: set = set()
    for group in by_air_date.values():
        if len(group) <= 1:
            continue
        keeper, best = group[0], group[0]
        cross_season = False
        for candidate in group[1:]:
            if candidate.season_number != keeper.season_number:
                cross_season = True
            if candidate.is_earlier_than(keeper):
                keeper = candidate
            if candidate.is_better_content_than(best):
                best = candidate
        if not cross_season:
            continue

        original = (keeper.episode.get("season_number"),
                    keeper.episode.get("episode_number"),
                    keeper.episode.get("id"))
        keeper.episode.update(best.episode)
        keeper.episode["season_number"] = original[0]
        keeper.episode["episode_number"] = original[1]
        keeper.episode["id"] = original[2]

        for candidate in group:
            if candidate.slot() != keeper.slot():
                to_remove.add(candidate.slot())

    result: list = []
    for season_idx, season in enumerate(raw_seasons):
        filtered = [
            ep for ep_idx, ep in enumerate(season.get("episodes") or [])
            if (season_idx, ep_idx) not in to_remove
        ]
        if not filtered:
            continue
        season["episodes"] = filtered
        result.append(season)
    return result


def first_air_year(air_date) -> Optional[int]:
    """'2026-04-05' → 2026；空或非日期开头返回 None。"""
    text = str(air_date or "").strip()
    if len(text) >= 4 and text[:4].isdigit():
        return int(text[:4])
    return None


def includes_rule_lines(tmdb_id: int, season_years: dict) -> list:
    """按虚拟季首播年份生成 includes 条件规则行。

    同一年份对应多个虚拟季时仅凭 includes 无法消歧，跳过并注释说明。
    """
    by_year: dict = {}
    for season_number in sorted(season_years):
        by_year.setdefault(int(season_years[season_number]), []).append(season_number)
    lines: list = []
    for year in sorted(by_year):
        seasons = by_year[year]
        if len(seasons) > 1:
            names = ",".join(f"S{s}" for s in seasons)
            lines.append(f"# 注意: 年份 {year} 对应多个虚拟季({names})，未生成 includes 规则")
            continue
        lines.append(f"@?{{[tmdbid={tmdb_id};type=tv;includes={year}]}} => {{[s={seasons[0]}]}}")
    return lines


def generate_render_words(tmdb_id: int, title: str, reference: str, org_map: dict,
                          season_years: Optional[dict] = None) -> str:
    """
    把逐集映射转换为项目渲染词(专家规则)文本块,含来源注释头。

    条件默认不带季号(s=):文件名里的季前缀不可靠(存在 S2E25 这类
    "季号 + 续位集号"的命名),以集号作为绝对定位依据。
    若不同原始季产生的集号区间重叠且目标不同(仅凭集号无法消歧),
    冲突段自动保留季限定并在注释中说明。

    season_years: 虚拟季号 → 首播年份；提供时按年份追加 includes 条件规则。
    """
    from datetime import date as _date

    per_orig: dict = {}
    for (orig_s, orig_e), (virt_s, virt_e) in org_map.items():
        if not isinstance(orig_s, int) or orig_s < 1:
            continue  # S0 / 电影条目无法用季集条件表达
        if not isinstance(orig_e, int) or orig_e < 1:
            continue
        per_orig.setdefault(orig_s, {})[orig_e] = (virt_s, virt_e)

    segments: list = []  # 需要生成规则的偏移段 (orig_s, a, b, virt_s, offset)
    claims: list = []    # 全部区间占用（含无偏移段），用于冲突检测

    for orig_s in sorted(per_orig):
        entries = sorted(per_orig[orig_s].items())

        def flush(orig_s: int, seg: list) -> None:
            if not seg:
                return
            a, b = seg[0][0], seg[-1][0]
            virt_s, virt_a = seg[0][1]
            offset = a - virt_a
            claims.append((orig_s, a, b, virt_s, offset))
            if virt_s == orig_s and offset == 0:
                return  # 无偏移:不生成规则,但区间已被原始季占用
            segments.append((orig_s, a, b, virt_s, offset))

        seg: list = []
        prev = None
        for oe, target in entries:
            if (prev is not None and oe == prev[0] + 1
                    and target[0] == prev[1][0]
                    and (oe - target[1]) == (prev[0] - prev[1][1])):
                seg.append((oe, target))
            else:
                flush(orig_s, seg)
                seg = [(oe, target)]
            prev = (oe, target)
        flush(orig_s, seg)

    rules: list = []
    ambiguous_any = False
    for seg in segments:
        os_, a, b, vs, off = seg
        # 与任何其他占用区间重叠且目标不同 → 仅凭集号无法消歧,保留季限定
        ambiguous = any(
            other != seg and not (b < other[1] or other[2] < a)
            and (vs, off) != (other[3], other[4])
            for other in claims
        )
        ambiguous_any = ambiguous_any or ambiguous
        cond = f"tmdbid={tmdb_id};type=tv;"
        if ambiguous:
            cond += f"s={os_};"
        cond += f"e={a}-{b}"
        mod = f"[s={vs};e=EP-{off}]" if off != 0 else f"[s={vs}]"
        rule = f"@?{{[{cond}]}} => {{{mod}}}"
        if rule not in rules:
            rules.append(rule)

    lines = [
        f"# [自动分季] {title or tmdb_id} TMDB:{tmdb_id} 依据={reference or '未知'} {_date.today().isoformat()}"
    ]
    if ambiguous_any:
        lines.append("# 注意: 存在跨季重叠的集号区间,冲突段已保留季限定(s=)")
    lines.extend(rules)
    if season_years:
        lines.extend(includes_rule_lines(tmdb_id, season_years))
    return "\n".join(lines)


def logic_to_group_json(logic: LogicSeries, tmdb_id: int) -> dict:
    """把拆分出的虚拟季导出为剧集组 JSON(与 episode_group_tool 输出同格式)。"""
    groups = []
    for season in logic.seasons:
        episodes = []
        idx = 0
        for order in sorted(season.episodes_map):
            em = season.episodes_map[order]
            if em.type != "tv":
                continue  # 剧集组无法表达电影条目
            episodes.append({
                "episode_number": em.episode_number,
                "season_number": em.season_num(),
                "order": idx,
            })
            idx += 1
        groups.append({
            "name": season.name or f"第 {season.season_number} 季",
            "air_date": season.air_date or "",
            "order": season.season_number,
            "episodes": episodes,
        })
    return {"description": "", "groups": groups, "id": str(tmdb_id)}


def build_finale_groups(raw_seasons: list, number_of_seasons: int) -> list:
    """以季结局(episode_type=finale)为界划分剧集组;finale 标记缺失且 TMDB 有多季时按季兜底。"""
    all_eps: list = []
    for season in raw_seasons:
        sn = int(season.get("season_number") or 0)
        for ep in season.get("episodes") or []:
            ep = dict(ep)
            ep["_season_number"] = sn
            if sn > 0:
                all_eps.append(ep)
    all_eps.sort(key=lambda e: (e["_season_number"], e.get("episode_number") or 0))
    if not all_eps:
        return []

    groups: list = []
    current: list = []
    idx = 1
    for ep in all_eps:
        current.append(ep)
        if ep.get("episode_type") == "finale":
            groups.append({"name": f"第 {idx} 季", "order": idx, "episodes": list(current)})
            current = []
            idx += 1
    if current:
        groups.append({"name": f"第 {idx} 季", "order": idx, "episodes": list(current)})

    # finale 标记缺失兜底:只划出一个组但 TMDB 有多季 → 直接按季分组
    if len(groups) == 1 and number_of_seasons > 1:
        per: dict = {}
        for ep in all_eps:
            per.setdefault(ep["_season_number"], []).append(ep)
        groups = [
            {"name": f"第 {sn} 季", "order": sn, "episodes": eps}
            for sn, eps in sorted(per.items())
        ]
    return groups


def groups_to_group_json(groups: list, tmdb_id: int) -> dict:
    """把分组结果转为剧集组 JSON。"""
    out_groups = []
    for g in groups:
        eps = g.get("episodes") or []
        episodes = [
            {
                "episode_number": e.get("episode_number"),
                "season_number": e.get("_season_number"),
                "order": i,
            }
            for i, e in enumerate(eps)
        ]
        first = eps[0] if eps else {}
        out_groups.append({
            "name": g.get("name"),
            "air_date": first.get("air_date") or "",
            "order": g.get("order"),
            "episodes": episodes,
        })
    return {"description": "", "groups": out_groups, "id": str(tmdb_id)}


def generate_group_render_words(tmdb_id: int, title: str, reference: str, groups: list) -> str:
    """
    按剧集组生成渲染词:第 i 组(i>0)的集号绝对窗口 [cum+1, cum+n] → [s=order;e=EP-cum]。

    窗口为全作累计集序,组间天然不重叠,因此条件无需季号限定,
    可同时命中 S2E13 这类"季号 + 续位集号"的命名(→ S2E1)。
    仅一个组时不生成。
    另按各组首播年份追加 includes 条件规则(含首个组)。
    """
    from datetime import date as _date

    if len(groups) <= 1:
        return ""
    lines = [
        f"# [自动分季] {title or tmdb_id} TMDB:{tmdb_id} 依据={reference or '未知'} {_date.today().isoformat()}"
    ]
    cumulative = 0
    for i, g in enumerate(groups):
        n = len(g.get("episodes") or [])
        if n <= 0:
            continue
        if i > 0:
            start, end = cumulative + 1, cumulative + n
            lines.append(
                f"@?{{[tmdbid={tmdb_id};type=tv;e={start}-{end}]}} => {{[s={g['order']};e=EP-{cumulative}]}}"
            )
        cumulative += n

    # 每组首播年份（按组内集顺序取第一个有日期的集）→ includes 条件规则
    season_years: dict = {}
    for g in groups:
        order = g.get("order")
        if not isinstance(order, int):
            continue
        for ep in g.get("episodes") or []:
            year = first_air_year(ep.get("air_date"))
            if year:
                season_years[order] = year
                break
    if season_years:
        lines.extend(includes_rule_lines(tmdb_id, season_years))
    return "\n".join(lines) if len(lines) > 1 else ""


class SeasonSplitter:
    def __init__(self, tmdb: TMDBClient, log: Callable = None):
        self.tmdb = tmdb
        self.log = log or (lambda level, msg: None)
        # 全量原始集查找表: "S{s}E{e}" -> 集数据（含 S0），用于季首播日期与展示
        self.raw_ep_lookup: dict = {}
        # 选中的分季依据名称（curetmdb/tvdb/bangumi），用于渲染词来源标注
        self.last_reference_name: str = ""

    # -- 参照获取 ------------------------------------------------------------

    def fetch_cure_tmdb_entry(self, source_data: dict, tmdb_id: int) -> Optional[SeriesEntry]:
        entry = source_data.get(str(tmdb_id))
        if isinstance(entry, dict) and entry.get("seasons"):
            self.last_reference_name = "curetmdb"
            self.log("INFO", f"分季依据选中: tmdbID={tmdb_id}, 依据=curetmdb")
            return SeriesEntry.decode(entry)
        return None

    def fetch_tvdb_entry(self, tvdb: TVDBClient, tvdb_id: int) -> Optional[SeriesEntry]:
        if tvdb_id > 0:
            return tvdb.get_series_entry(tvdb_id)
        return None

    def fetch_bangumi_entry(self, bangumi: BangumiClient, tv_show: dict) -> Optional[SeriesEntry]:
        original_name = tv_show.get("original_name") or ""
        first_air = tv_show.get("first_air_date") or ""
        items = bangumi.search(original_name, first_air)
        if not items:
            return None
        return bangumi.season_info(items[0])

    def handle_two_seasons_check(self, bangumi: BangumiClient, tv_show: dict) -> tuple:
        """TMDB 恰有 2 季时的 Bangumi 特殊检查。返回 (should_skip, error)。"""
        seasons = tv_show.get("seasons") or []

        def valid_seasons() -> list:
            out = []
            for s in seasons:
                num = s.get("season_number")
                cnt = s.get("episode_count")
                air = (s.get("air_date") or "").strip()
                if not isinstance(num, int) or num <= 0:
                    continue
                if not isinstance(cnt, (int, float)) or cnt <= 0:
                    continue
                if not air:
                    continue
                out.append(s)
            out.sort(key=lambda s: s["season_number"])
            prev = ""
            valid = []
            for s in out:
                air = s["air_date"].strip()
                if prev and air <= prev:
                    continue
                valid.append(s)
                prev = air
            return valid

        vs = valid_seasons()
        air_date = None
        if len(vs) >= 2:
            air_date = vs[1].get("air_date")
        if not air_date:
            for s in seasons:
                if s.get("season_number") == 2:
                    air_date = s.get("air_date")
                    break
        if not air_date:
            air_date = tv_show.get("first_air_date")
        if not air_date:
            return False, None

        try:
            items = bangumi.search(tv_show.get("original_name") or "", air_date)
        except Exception as e:
            self.log("ERROR", f"Bangumi API 搜索 seasonCount=2 失败: {e}")
            return False, None
        if not items:
            return False, None
        item = items[0]
        name_cn = item.get("name_cn") if isinstance(item.get("name_cn"), str) else None
        name = item.get("name") if isinstance(item.get("name"), str) else None
        if name_cn is None or name is None:
            return False, None

        season_num = extract_season_number(name_cn, name)
        if season_num != 1:
            return False, None

        bid = item.get("id")
        if not isinstance(bid, (int, float)):
            return False, None
        try:
            sequential = bangumi.is_first_episode_sequential(int(bid))
        except Exception as e:
            return False, e
        return (not sequential), None

    def fetch_series_entries_sequentially(
        self,
        tv_show: dict,
        source_data: dict,
        priority: list,
        tvdb: TVDBClient,
        bangumi: BangumiClient,
        force_reference: bool,
    ) -> Optional[SeriesEntry]:
        tmdb_id = int(tv_show.get("id"))
        entry = self.fetch_cure_tmdb_entry(source_data, tmdb_id)
        if entry is not None:
            return entry

        # 自动参照仅处理日本动画且有效季数 1~2 的剧集
        genre_ids = [g.get("id") for g in (tv_show.get("genres") or []) if isinstance(g, dict)]
        is_anime = ANIME_GENRE_ID in genre_ids
        is_jp = "JP" in (tv_show.get("origin_country") or [])
        if not force_reference and not (is_anime and is_jp):
            self.log("INFO", "非日本动画，跳过 TVDB/Bangumi 自动参照")
            return None

        valid_seasons_count = len(self._valid_seasons(tv_show))
        if not force_reference and (valid_seasons_count <= 0 or valid_seasons_count >= 3):
            self.log("INFO", f"有效季数={valid_seasons_count}，不在 1~2 范围，跳过自动参照")
            return None

        for reference in priority:
            self.log("INFO", f"分季依据尝试: tmdbID={tmdb_id}, 依据={reference}")
            entry: Optional[SeriesEntry] = None
            try:
                if reference == "bangumi":
                    if valid_seasons_count == 2 and not force_reference:
                        should_skip, check_err = self.handle_two_seasons_check(bangumi, tv_show)
                        if check_err is not None:
                            self.log("WARN", f"分季依据 bangumi 2季特殊检查失败，继续通用查询: {check_err}")
                        elif should_skip:
                            self.log("INFO", "2季特殊检查命中，视为无需拆分")
                            return None
                    entry = self.fetch_bangumi_entry(bangumi, tv_show)
                elif reference == "tvdb":
                    tvdb_id = int(((tv_show.get("external_ids") or {}).get("tvdb_id")) or 0)
                    entry = self.fetch_tvdb_entry(tvdb, tvdb_id)
            except Exception as e:
                self.log("WARN", f"分季依据 {reference} 获取信息失败: {e}")
                continue
            if entry is not None and entry.seasons:
                self.last_reference_name = reference
                self.log("INFO", f"分季依据选中: tmdbID={tmdb_id}, 依据={reference}")
                return entry
            self.log("INFO", f"分季依据返回空结果: tmdbID={tmdb_id}, 依据={reference}")

        self.log("INFO", f"分季依据均未返回结果: tmdbID={tmdb_id}")
        return None

    @staticmethod
    def _valid_seasons(tv_show: dict) -> list:
        seasons = []
        for s in tv_show.get("seasons") or []:
            num, cnt = s.get("season_number"), s.get("episode_count")
            air = (s.get("air_date") or "").strip()
            if not isinstance(num, int) or num <= 0:
                continue
            if not isinstance(cnt, (int, float)) or cnt <= 0:
                continue
            if not air:
                continue
            seasons.append(s)
        seasons.sort(key=lambda s: s["season_number"])
        prev, valid = "", []
        for s in seasons:
            air = s["air_date"].strip()
            if prev and air <= prev:
                continue
            valid.append(s)
            prev = air
        return valid

    # -- 主流程 --------------------------------------------------------------

    def fetch_seasons(self, tmdb_id: int, start: int, end: int) -> list:
        """并发拉取 TMDB 季详情 [start, end]，按季号排序（finale 分组用）。"""
        wanted = list(range(start, end + 1))
        raw: dict = {}

        def fetch(s: int) -> None:
            detail = self.tmdb.season_detail(tmdb_id, s)
            if detail:
                raw[s] = detail

        with ThreadPoolExecutor(max_workers=min(8, len(wanted) or 1)) as pool:
            list(pool.map(fetch, wanted))

        return [{**raw[s], "season_number": s} for s in sorted(raw)]

    def process_tv(
        self,
        tmdb_id: int,
        source_data: dict,
        priority: list,
        tvdb: TVDBClient,
        bangumi: BangumiClient,
        force_reference: bool,
    ) -> Optional[LogicSeries]:
        tv_show = self.tmdb.tv_detail(tmdb_id)
        if not tv_show:
            raise ValueError(f"TMDB ID {tmdb_id} 未找到剧集详情")

        series = self.fetch_series_entries_sequentially(
            tv_show, source_data, priority, tvdb, bangumi, force_reference,
        )
        if series is None:
            return None

        actual_counts = {
            int(s["season_number"]): int(s.get("episode_count") or 0)
            for s in (tv_show.get("seasons") or [])
            if isinstance(s.get("season_number"), int)
        }
        if not series.has_inconsistent(actual_counts):
            self.log("INFO", f"剧集结构一致，无需构建: tmdbID={tmdb_id}")
            return None

        return self.build_logic_series(tmdb_id, tv_show, series)

    # -- 构建逻辑季 ----------------------------------------------------------

    def _fetch_raw_seasons(self, tmdb_id: int, series: SeriesEntry, max_season: int) -> list:
        """并发拉取 TMDB 原始季详情（min_season..max_season），按季号排序保证确定性。"""
        wanted = list(range(series.min_season(), max_season + 1))
        raw: dict = {}

        def fetch(s: int) -> None:
            detail = self.tmdb.season_detail(tmdb_id, s)
            if detail:
                raw[s] = detail

        with ThreadPoolExecutor(max_workers=min(8, len(wanted) or 1)) as pool:
            list(pool.map(fetch, wanted))

        out = []
        for s in sorted(raw):
            detail = raw[s]
            detail.setdefault("season_number", s)
            out.append(detail)
        return out

    def build_logic_series(self, tmdb_id: int, tv_show: dict, series: SeriesEntry) -> LogicSeries:
        logic = LogicSeries(
            name=series.name,
            vote_average=float(tv_show.get("vote_average") or 0),
            poster_path=tv_show.get("poster_path"),
            overview=tv_show.get("overview"),
        )

        max_season = int(tv_show.get("number_of_seasons") or 0)
        raw_seasons = self._fetch_raw_seasons(tmdb_id, series, max_season)

        # 特殊季（S0）仅进入查找表，不参与摊平
        if series.has_any_special_season():
            detail = self.tmdb.season_detail(tmdb_id, 0)
            if detail:
                for ep in detail.get("episodes") or []:
                    sn, en = int(ep.get("season_number") or 0), int(ep.get("episode_number") or 0)
                    self.raw_ep_lookup[f"S{sn}E{en}"] = ep
                    if sn == 0:
                        self.raw_ep_lookup[f"S0E{en}"] = ep

        if max_season > 1:
            raw_seasons = remove_duplicate_episodes(raw_seasons)

        raw_eps = self._flatten_and_sort(raw_seasons)
        if not raw_eps:
            self.log("WARN", "摊平后无可用剧集，返回空逻辑季")
            return logic

        # 收集展示用查找表（含全部已拉取季）
        for season in raw_seasons:
            sn = int(season.get("season_number") or 0)
            for ep in season.get("episodes") or []:
                en = int(ep.get("episode_number") or 0)
                self.raw_ep_lookup.setdefault(f"S{sn}E{en}", ep)

        mapping = series.episode_mapping()
        missing_eps = series.missing_by_season()
        season_names = series.season_names()

        curr_s_idx = series.min_season()
        curr_missing = list(missing_eps.get(curr_s_idx, []))
        logic_ep_num = 0

        for i, ep in enumerate(raw_eps):
            season_num = int(ep.get("season_number") or 0)
            episode_num = int(ep.get("episode_number") or 0)
            if season_num != 0 or episode_num != 0:
                self.raw_ep_lookup[f"S{season_num}E{episode_num}"] = ep

            if curr_missing:
                logic_ep_num = curr_missing[0]
                curr_missing = curr_missing[1:]
            else:
                logic_ep_num += 1

            season_map = mapping.setdefault(curr_s_idx, {})
            season_map[logic_ep_num] = EpisodeMap(
                order=logic_ep_num,
                episode_number=episode_num,
                season_number=season_num,
                type="tv",
                tmdbid=tmdb_id,
            )

            is_last = i == len(raw_eps) - 1
            while (curr_s_idx in missing_eps and len(curr_missing) == 0) or is_last:
                if curr_s_idx not in season_names:
                    # Go 的 map 取缺失键返回空串不会崩;这里改用默认名并提示溢出
                    season_names[curr_s_idx] = f"第 {curr_s_idx} 季"
                    defined_max = max(season_names) if season_names else 0
                    self.log("WARN", f"原始集数超出分季定义覆盖(定义到 S{defined_max})，"
                                     f"季 {curr_s_idx} 的溢出集数使用默认季名")
                air_date, poster = self._first_episode_metadata(season_map)
                logic.add_season(season_names[curr_s_idx], air_date, curr_s_idx, season_map, poster)
                if is_last:
                    break
                curr_s_idx += 1
                curr_missing = list(missing_eps.get(curr_s_idx, []))
                logic_ep_num = 0

        return logic

    @staticmethod
    def _flatten_and_sort(raw_seasons: list) -> list:
        """全部集打平，按 air_date 升序（无日期的排最后）。"""
        all_eps: list = []
        for season in raw_seasons:
            sn = season.get("season_number")
            if sn is None:
                continue
            sn = int(sn)
            for ep in season.get("episodes") or []:
                ep["season_number"] = sn
                all_eps.append(ep)
        return sorted(all_eps, key=lambda e: (not bool(e.get("air_date")), e.get("air_date") or ""))

    def _first_episode_metadata(self, season_map: dict) -> tuple:
        if not season_map:
            return None, None
        min_order = min(season_map.keys())
        first = season_map[min_order]
        if first.season_num() < 0 and first.tmdbid is not None:
            movie = self.tmdb.movie_detail(first.tmdbid)
            if movie:
                return movie.get("air_date"), movie.get("still_path")
            return None, None
        found = self.raw_ep_lookup.get(f"S{first.season_num()}E{first.episode_num()}")
        if found:
            return found.get("air_date"), found.get("still_path")
        return None, None


def mapping_to_json(org_map: dict) -> dict:
    """逐集映射 → 与 Go 服务 /cache/mapping 接口相同的格式。"""
    out: dict = {}
    for (src_s, src_e), (dst_s, dst_e) in sorted(org_map.items()):
        out.setdefault(str(src_s), {})[str(src_e)] = {"season": dst_s, "episode": dst_e}
    return out


def logic_result_to_group_json_text(group_json: Optional[dict]) -> str:
    if not group_json:
        return ""
    return json.dumps(group_json, ensure_ascii=False, indent=2)
