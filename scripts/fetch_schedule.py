#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
示例爬虫：抓取成都蓉城和国际米兰赛程并保存为 CSV。
需要安装 requests、beautifulsoup4。
请根据网页实际结构完善 parse 函数。
"""

import csv
import requests
from bs4 import BeautifulSoup

def fetch_chengdu():
    # 示例地址：懂球帝文章或球天下体育
    url = "https://www.qtx.com/csl/267887.html"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    # TODO: 根据页面结构提取 2025 中超赛程和亚冠赛程
    # 此处仅写入现有手动整理的数据
    schedule = [
        # (date, time, opponent, home/away, competition, stadium)
        ("2025-02-22","19:35","武汉三镇","Home","Chinese Super League","成都凤凰山专业足球场"),
        # ... 全部 30 场中超 + 8 场亚冠
    ]
    with open("data/chengdu.csv","w",newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date","time_local","opponent","home_away","competition","stadium"])
        writer.writerows(schedule)

def fetch_inter():
    # 示例：可以从 ESPN 或 Inter 官方网站抓取 2025-26 全部赛程
    url = "https://www.espn.com/soccer/team/fixtures/_/id/110/internazionale"
    resp = requests.get(url, timeout=10)
    soup = BeautifulSoup(resp.text, "html.parser")
    # TODO: 按需解析意甲、意大利杯、超级杯、欧冠等比赛信息
    schedule = [
        ("2025-01-12","22:00","Venezia","Away","Serie A",""),
        # ... 完整比赛列表
    ]
    with open("data/inter.csv","w",newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date","time_local","opponent","home_away","competition","stadium"])
        writer.writerows(schedule)

if __name__ == "__main__":
    fetch_chengdu()
    fetch_inter()
    print("Fetched schedules into CSV.")
