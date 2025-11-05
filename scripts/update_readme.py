#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

PAGES_BASE = os.getenv("GITHUB_PAGES_BASE", "").strip()
# 如果没配置环境变量，就按 github.io 的标准路径推断
if not PAGES_BASE:
    # 例如： https://louiszeng0623.github.io/Yzeng17/
    user = os.getenv("GITHUB_REPOSITORY_OWNER", "")
    repo = os.getenv("GITHUB_REPOSITORY", "").split("/")[-1] if os.getenv("GITHUB_REPOSITORY") else ""
    if user and repo:
        PAGES_BASE = f"https://{user}.github.io/{repo}/"

ics_url = f"{PAGES_BASE}calendar.ics" if PAGES_BASE else "（请在 Settings → Pages 启用后自动生成）"

md = f"""# GitHub iPhone 订阅日历（成都蓉城 + 国际米兰）

- 更新时间：自动（每天凌晨 04:00 北京时间）
- iPhone 订阅链接（点开复制）：  
  **{ics_url}**

## 包含赛事
- 成都蓉城：中超/足协杯/亚冠（含网页回退）
- 国际米兰：意甲/欧冠/杯赛（含网页回退）

## 数据来源与容错
1. 懂球帝 App API（带 UA 伪装与自动重试）
2. 懂球帝球队网页（解析内嵌 JSON）
3. 直播吧 data 站球队页（解析表格）
> 若某天所有来源都失败，会保留上一次的 CSV，以保证手机日历不清空。

---

**订阅方法（iPhone）**  
设置 → 日历 → 账户 → 添加订阅的日历 → 粘贴上面的链接 → 保存。
"""

with open("README.md","w",encoding="utf-8") as f:
    f.write(md)
print("README.md updated.")
