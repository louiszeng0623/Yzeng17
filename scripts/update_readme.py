#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, csv

ROOT = os.getenv("GITHUB_REPOSITORY", "")
USER = ROOT.split("/")[0] if "/" in ROOT else "<your_user>"
REPO = ROOT.split("/")[1] if "/" in ROOT else "<your_repo>"
PAGES = f"https://{USER}.github.io/{REPO}"

def count_csv(path):
    try:
        with open(path, encoding="utf-8") as f:
            r = csv.reader(f)
            rows = list(r)
        return max(0, len(rows)-1)
    except:
        return 0

def main():
    ch = count_csv("data/chengdu.csv")
    it = count_csv("data/inter.csv")
    md = f"""# GitHub iPhone 日历订阅（成都蓉城 & 国际米兰）

- 📅 订阅链接（直接粘贴到 iPhone「设置 → 日历 → 账户 → 添加订阅的日历」）  
  `{PAGES}/calendar.ics`

- 📊 当前赛程条数：  
  - 成都蓉城：**{ch}**  
  - 国际米兰：**{it}**

- 🔄 自动更新：每天北京时间 04:00 爬取（直播吧 → 懂球帝网页 → 懂球帝 API），失败会保留上一版数据。

- 🌐 在线预览主页：{PAGES}

> 如果你想增加球队，只需在 `scripts/fetch_schedule.py` 的 `TEAMS` 里按同样格式新增一个条目即可。
"""
    with open("README.md","w",encoding="utf-8") as f:
        f.write(md)
    print("README.md 已更新")

if __name__ == "__main__":
    main()
