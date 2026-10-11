# -*- coding: utf-8 -*-
"""番剧分季拆分的数据模型（dataclass）。

移植自 CureTMDbAnime（Go）internal/model/entry.go、logic.go，
对应独立桌面工具 cure_splitter 的数据模型区段。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EpisodeMap:
    order: int
    episode_number: Optional[int]
    season_number: Optional[int]
    type: str = "tv"
    tmdbid: Optional[int] = None

    def season_num(self) -> int:
        return self.season_number if self.season_number is not None else -1

    def episode_num(self) -> int:
        if self.episode_number is not None and (self.type == "tv" or self.episode_number > 0):
            return self.episode_number
        return self.tmdbid if self.tmdbid is not None else 0

    def mapping_key(self) -> tuple:
        return (self.season_num(), self.episode_num())

    def to_json(self) -> dict:
        data = {"order": self.order, "type": self.type}
        if self.episode_number is not None:
            data["episode_number"] = self.episode_number
        if self.season_number is not None:
            data["season_number"] = self.season_number
        if self.tmdbid is not None:
            data["tmdbid"] = self.tmdbid
        return data


@dataclass
class IncludeEntry:
    order: int
    count: int = 1
    episode_number: Optional[int] = None
    season_number: Optional[int] = None
    type: str = ""
    tmdbid: Optional[int] = None

    def apply_defaults(self) -> None:
        if self.count == 0:
            self.count = 1
        if not self.type:
            if self.episode_number is None and self.season_number is None and self.tmdbid is not None:
                self.type = "movie"
            else:
                self.type = "tv"

    def is_special_season(self) -> bool:
        return self.type == "tv" and self.episode_number is not None and self.season_number == 0

    @classmethod
    def decode(cls, data: dict) -> "IncludeEntry":
        entry = cls(
            order=int(data.get("order") or 0),
            count=int(data.get("count") or 0),
            episode_number=data.get("episode_number"),
            season_number=data.get("season_number"),
            type=data.get("type") or "",
            tmdbid=data.get("tmdbid"),
        )
        entry.apply_defaults()
        return entry


@dataclass
class SeasonEntry:
    season_number: int
    episode_count: int
    name: Optional[str] = None
    include: list = field(default_factory=list)

    def has_special_season(self) -> bool:
        return any(item.is_special_season() for item in self.include)

    def episode_count_valid(self, actual_counts: dict) -> bool:
        """TMDB 实际集数 <= 定义集数 视为有效；该季在 TMDB 不存在也视为有效。"""
        actual = actual_counts.get(self.season_number)
        if actual is None:
            return True
        return actual <= self.episode_count

    def included_episodes(self) -> dict:
        result: dict = {}
        for item in self.include:
            for e in range(item.count):
                order = e + item.order
                ep_num = e
                if item.episode_number is not None:
                    ep_num += item.episode_number
                result[order] = EpisodeMap(
                    order=order,
                    episode_number=ep_num,
                    season_number=item.season_number,
                    type=item.type,
                    tmdbid=item.tmdbid,
                )
        return result

    def missing_episodes(self) -> list:
        """定义顺序(1..episode_count)中未被 include 覆盖的编号，多余项做抵消修剪。"""
        current: set = set()
        for item in self.include:
            for order in range(item.order, item.order + item.count):
                current.add(order)

        all_expected = set(range(1, self.episode_count + 1))
        extra = current - all_expected
        missing = sorted(all_expected - current)

        if extra:
            if len(missing) > len(extra):
                return missing[: len(missing) - len(extra)]
            return []
        return missing

    @classmethod
    def decode(cls, data: dict) -> "SeasonEntry":
        return cls(
            season_number=int(data.get("season_number") or 0),
            episode_count=int(data.get("episode_count") or 0),
            name=data.get("name"),
            include=[IncludeEntry.decode(x) for x in (data.get("include") or []) if isinstance(x, dict)],
        )


@dataclass
class SeriesEntry:
    """分季定义：[{season_number, episode_count}]，来自 CureTMDb / TVDB / Bangumi。"""

    name: Optional[str]
    seasons: list

    def min_season(self) -> int:
        if not self.seasons:
            return 1
        return min(s.season_number for s in self.seasons)

    def has_any_special_season(self) -> bool:
        return any(s.has_special_season() for s in self.seasons)

    def season(self, num: int) -> Optional[SeasonEntry]:
        for s in self.seasons:
            if s.season_number == num:
                return s
        return None

    def has_inconsistent(self, actual_counts: dict) -> bool:
        """任一定义季的 TMDB 实际集数超出定义集数 → 需要拆分。"""
        return any(not s.episode_count_valid(actual_counts) for s in self.seasons)

    def season_names(self) -> dict:
        return {
            s.season_number: (s.name if s.name else f"第 {s.season_number} 季")
            for s in self.seasons
        }

    def missing_by_season(self) -> dict:
        return {s.season_number: s.missing_episodes() for s in self.seasons}

    def episode_mapping(self) -> dict:
        mapping: dict = {}
        for s in self.seasons:
            included = s.included_episodes()
            if included:
                mapping[s.season_number] = included
        return mapping

    @classmethod
    def decode(cls, data: dict) -> "SeriesEntry":
        return cls(
            name=data.get("name"),
            seasons=[SeasonEntry.decode(x) for x in (data.get("seasons") or []) if isinstance(x, dict)],
        )


@dataclass
class LogicSeason:
    name: Optional[str]
    air_date: Optional[str]
    season_number: int
    episodes_map: dict
    poster_path: Optional[str] = None

    def episode_count(self) -> int:
        return len(self.episodes_map)

    def org_map(self) -> dict:
        """原始坐标 → 逻辑坐标；电影条目的原始坐标为 (-1, tmdbid)。"""
        result: dict = {}
        for order, em in self.episodes_map.items():
            result[em.mapping_key()] = (self.season_number, order)
        return result


@dataclass
class LogicSeries:
    name: Optional[str]
    vote_average: float
    poster_path: Optional[str]
    overview: Optional[str]
    seasons: list = field(default_factory=list)

    def add_season(self, name: str, air_date, season_number: int,
                   episodes_map: dict, poster_path) -> None:
        self.seasons.append(LogicSeason(
            name=name,
            air_date=air_date,
            season_number=season_number,
            episodes_map=episodes_map,
            poster_path=poster_path or self.poster_path,
        ))

    def season_info(self, num: int) -> Optional[LogicSeason]:
        for s in self.seasons:
            if s.season_number == num:
                return s
        return None

    def org_map(self) -> dict:
        result: dict = {}
        for season in self.seasons:
            result.update(season.org_map())
        return result

    def to_json(self) -> dict:
        return {
            "name": self.name,
            "vote_average": self.vote_average,
            "poster_path": self.poster_path,
            "overview": self.overview,
            "seasons": [
                {
                    "name": s.name,
                    "air_date": s.air_date,
                    "season_number": s.season_number,
                    "poster_path": s.poster_path,
                    "episodes_map": {str(order): em.to_json() for order, em in sorted(s.episodes_map.items())},
                }
                for s in self.seasons
            ],
        }
