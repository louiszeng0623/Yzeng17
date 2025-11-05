#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

# 你当前仓库的 Pages 访问路径是 用户名.github.io/仓库名/
# 为了稳妥，这里直接写死成你的仓库地址；如果以后换仓库名再改这里即可。
ICS_URL = "https://louiszeng0623.github.io/Yzeng17/calendar.ics"

README = Path("README.md")

lines = []
lines.append("# GitHub iPhone 日历（自动更新）\n")
lines.append("- 覆盖：**成都蓉城**、**国际米兰**（中超/亚冠、意甲/欧冠/杯赛）\n")
lines.append("- 北京时间统一显示（Asia/Shanghai）\n")
lines.append("- 每天 **04:00** 自动更新\n")
lines.append("\n")
lines.append("**iPhone 订阅：** 设置 → 日历 → 账户 → 添加订阅的日历 → 粘贴：\n")
lines.append("\n```\n")
lines.append(ICS_URL + "\n")
lines.append("```\n\n")
lines.append("如果出现 404：到仓库 **Settings → Pages** 开启 Pages，Source 选 `Deploy from a branch`，分支选 `main /(root)`。\n")

content = "".join(lines)

README.write_text(content, encoding="utf-8")
print("✅ 更新 README.md 完成")
