from __future__ import annotations

import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from curl_cffi import requests

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
UTC_TZ = ZoneInfo("UTC")


class CrawlerError(RuntimeError):
    """Pinnacle 資料抓取或解析失敗。"""


class PinnacleCrawler:
    def __init__(self, api_key: str | None = None) -> None:
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://www.pinnacle.com/",
            "x-api-key": api_key
            or os.getenv("PINNACLE_API_KEY")
            or "VjI6d2ViLWRlc2t0b3A6Z3Vlc3Q6Z3Vlc3Q=",
        }
        self.matchups_url = (
            "https://guest.api.arcadia.pinnacle.com/0.1/sports/33/"
            "matchups?withSpecials=false"
        )
        self.odds_url = (
            "https://guest.api.arcadia.pinnacle.com/0.1/sports/33/markets/"
            "straight?primaryOnly=false&withSpecials=false"
        )

    def _get_json(self, url: str) -> list[dict[str, Any]]:
        try:
            response = requests.get(
                url,
                headers=self.headers,
                impersonate="chrome110",
                timeout=25,
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise CrawlerError(f"Pinnacle 資料抓取失敗：{exc}") from exc

        if not isinstance(data, list):
            raise CrawlerError("Pinnacle 回傳格式異常，預期為陣列資料。")
        return data

    def fetch_data(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """同時取得網球對戰資料與獨贏賠率資料。"""
        return self._get_json(self.matchups_url), self._get_json(self.odds_url)

    @staticmethod
    def convert_odds(american: Any) -> float | str:
        """將美式賠率轉成十進位賠率。"""
        if american in ("鎖盤中", None):
            return "鎖盤中"

        try:
            value = float(american)
            if value == 0:
                return "鎖盤中"
            decimal = (
                (value / 100.0) + 1.0
                if value > 0
                else (100.0 / abs(value)) + 1.0
            )
            return round(decimal, 3)
        except (TypeError, ValueError, ZeroDivisionError):
            return "鎖盤中"

    @staticmethod
    def parse_time(item: dict[str, Any]) -> tuple[str, datetime | None]:
        """解析 Pinnacle UTC 時間並轉成台灣時間。"""
        utc_time = item.get("startTime")
        if not utc_time:
            for period in item.get("periods", []):
                if period.get("period") == 0:
                    utc_time = period.get("cutoffAt")
                    break

        if not utc_time:
            return "未知", None

        try:
            parsed = datetime.fromisoformat(str(utc_time).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC_TZ)
            taipei_time = parsed.astimezone(TAIPEI_TZ)
            return taipei_time.strftime("%Y-%m-%d %H:%M"), taipei_time
        except (TypeError, ValueError):
            return "時間錯誤", None

    @staticmethod
    def is_doubles_match(league_name: Any, participant_names: list[Any]) -> bool:
        """判斷是否為雙打；聯賽含 Doubles／雙打或選手名稱含斜線即淘汰。"""
        league_text = str(league_name or "")
        if "doubles" in league_text.casefold() or "雙打" in league_text:
            return True

        return any("/" in str(name or "") for name in participant_names)

    def get_matches(
        self,
        *,
        filter_enabled: bool = True,
        min_odds: float = 1.5,
        max_odds: float = 1.7,
    ) -> list[dict[str, Any]]:
        """抓取、排除雙打、整理、篩選並依開賽時間排序。"""
        if min_odds <= 1 or max_odds <= 1:
            raise ValueError("賠率必須大於 1。")
        if min_odds > max_odds:
            raise ValueError("最低賠率不可高於最高賠率。")

        matchups, odds = self.fetch_data()

        odds_map: dict[Any, dict[str, float | str]] = {}
        for market in odds:
            if market.get("type") != "moneyline" or market.get("period") != 0:
                continue

            prices = {
                price.get("designation"): price.get("price")
                for price in market.get("prices", [])
                if isinstance(price, dict)
            }
            odds_map[market.get("matchupId")] = {
                "home": self.convert_odds(prices.get("home")),
                "away": self.convert_odds(prices.get("away")),
            }

        rows: list[dict[str, Any]] = []
        for matchup in matchups:
            matchup_id = matchup.get("id")
            participant_items = [
                participant
                for participant in matchup.get("participants", [])
                if isinstance(participant, dict)
            ]
            participants = {
                participant.get("alignment"): participant.get("name")
                for participant in participant_items
            }
            league_name = matchup.get("league", {}).get("name") or "未知"

            # 在建立畫面資料與 today_matches.json 之前直接排除所有雙打賽事。
            if self.is_doubles_match(
                league_name,
                [participant.get("name") for participant in participant_items],
            ):
                continue

            start_text, start_dt = self.parse_time(matchup)
            market_odds = odds_map.get(
                matchup_id,
                {"home": "鎖盤中", "away": "鎖盤中"},
            )

            home_odds = market_odds["home"]
            away_odds = market_odds["away"]

            if filter_enabled:
                home_match = (
                    isinstance(home_odds, float)
                    and min_odds <= home_odds <= max_odds
                )
                away_match = (
                    isinstance(away_odds, float)
                    and min_odds <= away_odds <= max_odds
                )
                if not (home_match or away_match):
                    continue

            rows.append(
                {
                    "_sort_time": (
                        start_dt.isoformat()
                        if start_dt
                        else "9999-12-31T23:59:59+08:00"
                    ),
                    "日期時間": start_text,
                    "聯賽": league_name,
                    "主場": participants.get("home") or "未知",
                    "客場": participants.get("away") or "未知",
                    "主場賠率": home_odds,
                    "客場賠率": away_odds,
                }
            )

        rows.sort(key=lambda row: row["_sort_time"])

        numbered_rows: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            row.pop("_sort_time", None)
            numbered_rows.append({"項次": index, **row})

        return numbered_rows
