# -*- coding: utf-8 -*-
import re
import json
import csv
import requests
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

CST = timezone(timedelta(hours=8))  # Asia/Shanghai

TEAMS = {
    "chengdu": {
        "name": "成都蓉城",
        "id": "50076899",
        "page": "https://www.dongqiudi.com/team/50076899.html",
        # 备用移动页（有时更容易拿到 JSON）
        "mobile": "https://m.dongqiudi.com/team/50076899.html",
    },
    "inter": {
        "name": "国际米兰",
        "id": "50001042",
        "page": "https://www.dongqiudi.com/team/50001042.html",
        "mobile": "https://m.dongqiudi.com/team/50001042.html",
    },
}

UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

def fetch_text(url: str) -> str:
    r = requests.get(url, headers=UA, timeout=20)
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text

def find_embedded_json(html: str) -> List[Dict[str, Any]]:
    """
    从 HTML 中提取内嵌 JSON（适配 Nuxt/React 常见写法），
    然后递归搜索所有“像比赛对象”的结构。
    """
    candidates = []

    # 常见：window.__NUXT__= {...};
    m = re.search(r"window\.__NUXT__\s*=\s*(\{.*?\});", html, re.S)
    if m:
        candidates.append(m.group(1))

    # 另一种：__INITIAL_STATE__ = {...};
    m2 = re.search(r"__INITIAL_STATE__\s*=\s*(\{.*?\});", html, re.S)
    if m2:
        candidates.append(m2.group(1))

    # 还有些站点把 JSON 放到 <script type="application/json">...</script>
    for s in re.findall(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
                        html, re.S):
        candidates.append(s.strip())

    objs = []
    for raw in candidates:
        try:
            # 某些末尾可能多了分号
            raw2 = raw.strip().rstrip(";")
            data = json.loads(raw2)
            objs.append(data)
        except Exception:
            # 再加一层降噪：去掉多余的注释/末尾逗号等（有限尝试）
            try:
                raw3 = re.sub(r"//.*", "", raw, flags=re.M)
                data = json.loads(raw3.strip().rstrip(";"))
                objs.append(data)
            except Exception:
                continue

    # 递归把“比赛对象”抠出来
    matches = []
    def walk(x: Any):
        if isinstance(x, dict):
            keys = set(x.keys())
            # 典型字段组合（尽量放宽）
            if {"matchTime", "homeTeam", "awayTeam"}.issubset(keys) or \
               {"matchTime", "competitionName"}.issubset(keys) or \
               {"homeTeam", "awayTeam", "competitionName"}.issubset(keys):
                matches.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    for obj in objs:
        walk(obj)

    return matches

def to_rows(items: List[Dict[str, Any]]) -> List[List[str]]:
    rows = []
    for m in items:
        # 时间：可能是时间戳（秒/毫秒），也可能是字符串
        dt_raw = m.get("matchTime") or m.get("time") or m.get("matchDate")
        dt_str = ""
        if isinstance(dt_raw, (int, float)):
            # 秒或毫秒：>= 10^12 认为是毫秒
            if dt_raw > 10**12:
                dt = datetime.fromtimestamp(dt_raw / 1000, tz=CST)
            else:
                dt = datetime.fromtimestamp(dt_raw, tz=CST)
            dt_str = dt.strftime("%Y-%m-%d %H:%M")
        elif isinstance(dt_raw, str):
            dt_str = dt_raw.strip()
        else:
            dt_str = ""

        comp = (
            m.get("competitionName")
            or (m.get("competition") or {}).get("name")
            or m.get("leagueName")
            or ""
        )

        def team_name(t):
            if isinstance(t, dict):
                return t.get("name") or t.get("teamName") or t.get("shortName") or ""
            if isinstance(t, str):
                return t
            return ""

        home = team_name(m.get("homeTeam") or m.get("home"))
        away = team_name(m.get("awayTeam") or m.get("away"))

        score = m.get("fullScore") or m.get("score") or ""

        # 保底：两队名至少有一个不为空
        if home or away:
            rows.append([dt_str, comp, home, score, away])
    # 去重 + 按时间排序
    uniq = []
    seen = set()
    for r in rows:
        key = tuple(r)
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    uniq.sort(key=lambda x: x[0])
    return uniq

def scrape_team(team_key: str) -> bool:
    t = TEAMS[team_key]
    print(f"▶ 抓取 {t['name']} …")
    for url in [t["page"], t["mobile"]]:
        try:
            html = fetch_text(url)
            items = find_embedded_json(html)
            rows = to_rows(items)
            if rows:
                out = f"data/{team_key}.csv"
                with open(out, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow(["时间", "赛事", "主队", "比分", "客队"])
                    w.writerows(rows)
                print(f"✅ {t['name']} CSV 已更新 → {out}，共 {len(rows)} 场")
                return True
            else:
                print(f"⚠️ {t['name']}：该页面未提取到内嵌 JSON，换下一个 URL 试试…")
        except Exception as e:
            print(f"⚠️ {t['name']}：{url} 抓取异常：{e}")
    print(f"❌ {t['name']}：两个页面都未提取到赛程")
    return False

if __name__ == "__main__":
    ok1 = scrape_team("chengdu")
    ok2 = scrape_team("inter")
    # 不中断后续步骤，让 ICS 脚本去处理（空表也能跑，只是结果为空）

