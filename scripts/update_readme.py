#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

README = Path("README.md")
ics_url = f"https://{Path.cwd().name}.github.io/{Path.cwd().name}/calendar.ics"  # Pages root 情况
# 如果你的 Pages 是 repo 名访问（例如用户名.github.io/仓库名/），可以手动改成：
# ics_url = "https://louiszeng0623.github.io/Yzeng17/calendar.ics"

content = f"""# GitHub iPhone 日历（自动更新）

- 覆盖：**成都蓉城**、**国际米兰**（中超/亚冠、意甲/欧冠/杯赛）
- 北京时间统一显示（Asia/Shanghai）
- 每天 **04:00** 自动更新

**iPhone 订阅：** 设置 → 日历 → 账户 → 添加订阅的日历 → 粘贴：
