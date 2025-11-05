#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从懂球帝与直播吧抓取 成都蓉城 与 国际米兰 最新赛程
自动更新 CSV
作者：Louis Zeng 项目自动化版
"""

import requests, csv, re
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

def write_csv(path, rows):
    fieldnames = ["date", "time_local", "opponent", "home_away", "competition", "stadium"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ 写入 {path} 共 {len(rows)} 场比赛")

# =============== 成都蓉城 ===============
def fetch_chengdu():
    print("📦 正在抓取 成都蓉城 赛程（直播吧）...")
    url = "https://m.zhibo8.cc/news/web/zuqiu/2025-02-06/67a44b9d59a53native.htm"
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    text = soup.get_text()
    # 使用正则匹配类似 “3月2日 北京国安（主）19:35 中超联赛”
    pattern = re.compile(r"(\d+)月(\d+)日.*?([\u4e00-\u9fa5A-Za-z]+).*?(主|客).*?(\d{1,2}:\d{2})")
    matches = pattern.findall(text)

    rows = []
    for m in matches:
        month, day, opponent, home_away, time_local = m
        date = f"2025-{int(month):02d}-{int(day):02d}"
        rows.append({
            "date": date,
            "time_local": time_local,
            "opponent": opponent,
            "home_away": "Home" if home_away == "主" else "Away",
            "competition": "中超联赛",
            "stadium": "凤凰山体育公园专业足球场" if home_away == "主" else ""
        })
    return rows

# =============== 国际米兰 ===============
def fetch_inter():
    print("📦 正在抓取 国际米兰 赛程（懂球帝）...")
    url = "https://m.dongqiudi.com/article/5341689.html"
    r = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")

    text = soup.get_text()
    # 例如 “9月18日 03:00 阿贾克斯 vs 国际米兰”
    pattern = re.compile(r"(\d+)月(\d+)日\s+(\d{1,2}:\d{2}).*?(国际米兰|vs).*?([\u4e00-\u9fa5A-Za-z]+)")
    matches = pattern.findall(text)

    rows = []
    for m in matches:
        month, day, time_local, tag, opponent = m
        date = f"2025-{int(month):02d}-{int(day):02d}"
        home_away = "Away" if "vs 国际米兰" in text else "Home"
        rows.append({
            "date": date,
            "time_local": time_local,
            "opponent": opponent,
            "home_away": home_away,
            "competition": "欧冠联赛",
            "stadium": "圣西罗球场" if home_away == "Home" else ""
        })
    return rows

# =============== 主程序入口 ===============
def main():
    try:
        cd_rows = fetch_chengdu()
        inter_rows = fetch_inter()
        write_csv("data/chengdu.csv", cd_rows)
        write_csv("data/inter.csv", inter_rows)
        print("🎯 所有数据已抓取并写入 CSV")
    except Exception as e:
        print("❌ 抓取失败：", e)

if __name__ == "__main__":
    main()
