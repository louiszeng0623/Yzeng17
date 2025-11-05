# -*- coding: utf-8 -*-
"""
稳健抓取方案（不走任何API）：
- 1st 优先抓 直播吧数据 的球队页（需要点击“赛程”Tab 才出现表格）
- 兜底：把页面完整 HTML 抓下来，再用 BS4 从 table 里抠
- 全流程超时、重试、失败截图、双站点回退
"""

import csv
import time
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

TEAMS = [
    {
        "key": "chengdu",
        "name": "成都蓉城",
        # 直播吧数据（必须点“赛程”）
        "zhibo8": "https://data.zhibo8.cc/html/team.html?match=&team=成都蓉城",
        # 懂球帝（作为二级兜底，结构也会出现table）
        "dongqiudi": "https://www.dongqiudi.com/team/50076899.html",
        "out": "data/chengdu.csv",
    },
    {
        "key": "inter",
        "name": "国际米兰",
        "zhibo8": "https://data.zhibo8.cc/html/team.html?match=&team=国际米兰",
        "dongqiudi": "https://www.dongqiudi.com/team/50001042.html",
        "out": "data/inter.csv",
    },
]

HEADLESS = True
WAIT = 60000  # 60s

def rows_from_table_html(html: str) -> List[List[str]]:
    """无视样式/隐藏列，直接从 table 取干净文本"""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = []
    for tr in table.find_all("tr"):
        tds = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        # 简单的赛程行：日期、赛事、主队、比分/VS、客队……（直播吧基本符合）
        if len(tds) >= 5 and ("vs" in " ".join(tds).lower() or "VS" in tds or "–" in tds or "-" in tds):
            # 尝试抽取常见五列：时间 赛事 主队 比分 客队
            # 直播吧列顺序大致：时间 | 赛事 | 主队 | 比分 | 客队 | 场地/轮次...
            date = tds[0]
            comp = tds[1]
            home = tds[2]
            score = tds[3]
            away = tds[4]
            rows.append([date, comp, home, score, away])
    return rows

def normalize(rows: List[List[str]]) -> List[List[str]]:
    """把“时间”规范成 YYYY-MM-DD HH:MM（直播吧通常是 MM-DD HH:MM）"""
    out = []
    now_year = datetime.now().year
    for r in rows:
        if len(r) < 5:
            continue
        dt_raw, comp, home, score, away = r[:5]
        dt_raw = dt_raw.replace(".", "-").replace("/", "-").strip()
        dt_fmt = dt_raw
        # 兼容 "MM-DD HH:MM"
        try:
            if len(dt_raw) in (11,12):  # "05-14 19:35"
                t = datetime.strptime(dt_raw, "%m-%d %H:%M").replace(year=now_year)
                dt_fmt = t.strftime("%Y-%m-%d %H:%M")
            elif len(dt_raw) >= 16:     # "2025-05-14 19:35"
                t = datetime.strptime(dt_raw[:16], "%Y-%m-%d %H:%M")
                dt_fmt = t.strftime("%Y-%m-%d %H:%M")
        except Exception:
            # 保底不改
            pass
        out.append([dt_fmt, comp, home, score, away])
    # 去重 + 按时间排序
    uniq = []
    seen = set()
    for r in out:
        k = tuple(r)
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    uniq.sort(key=lambda x: x[0])
    return uniq

def save_csv(path: str, rows: List[List[str]]):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["时间", "赛事", "主队", "比分", "客队"])
        w.writerows(rows)

def grab_with_playwright(team, url, tab_texts):
    """
    到页面后点击“赛程/赛程赛果/比赛”等 tab，再等 table 出来。
    tab_texts: 针对不同站点可能用不同文案
    返回：table 元素的 outerHTML
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=HEADLESS,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
            ],
        )
        ctx = browser.new_context(
            viewport={"width": 1400, "height": 900},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"),
            locale="zh-CN",
        )
        page = ctx.new_page()
        page.set_default_timeout(WAIT)

        try:
            page.goto(url, wait_until="domcontentloaded")
            # 页面可能还在懒加载，稍等一下
            page.wait_for_load_state("networkidle", timeout=WAIT)

            # 先试直接找到表格
            try:
                table = page.locator("table").first
                table.wait_for(state="visible", timeout=5000)
                html = table.evaluate("e => e.outerHTML")
                return html
            except PWTimeout:
                pass

            # 点击“赛程/赛程赛果/比赛”等 Tab
            clicked = False
            for txt in tab_texts:
                loc = page.get_by_text(txt, exact=False)
                if loc.count():
                    try:
                        loc.first.click()
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                # 备用：试点包含“程”的 li
                try:
                    page.locator("li:has-text('程')").first.click()
                    clicked = True
                except Exception:
                    pass

            # 再等表格
            table = page.locator("table").first
            table.wait_for(state="visible", timeout=WAIT)
            html = table.evaluate("e => e.outerHTML")
            return html

        except Exception as e:
            # 失败截图到 docs/ 方便排查
            ts = int(time.time())
            page.screenshot(path=f"docs/{team['key']}_fail_{ts}.png", full_page=True)
            print(f"⚠️ {team['name']} 抓取失败: {e}")
            return ""

        finally:
            ctx.close()
            browser.close()

def fetch_one(team) -> bool:
    print(f"▶ 抓取 {team['name']}")

    # 1) 直播吧（优先）
    html = grab_with_playwright(
        team,
        team["zhibo8"],
        tab_texts=["赛程", "赛程赛果", "比赛"],
    )
    rows = rows_from_table_html(html) if html else []

    # 2) 懂球帝（兜底：有时也会给出 table）
    if not rows:
        html = grab_with_playwright(
            team,
            team["dongqiudi"],
            tab_texts=["赛程", "赛程赛果", "比赛", "赛历"],
        )
        if html:
            rows = rows_from_table_html(html)

    rows = normalize(rows)
    save_csv(team["out"], rows)
    print(f"✅ {team['name']} 共 {len(rows)} 场 → {team['out']}")
    return len(rows) > 0

if __name__ == "__main__":
    ok_all = True
    for t in TEAMS:
        ok = fetch_one(t)
        ok_all = ok_all and ok
    # 不 raise，让后续 ICS 也能正常生成（即使 0 场）
