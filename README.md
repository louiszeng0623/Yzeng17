# ⚽ 足球赛程自动同步 iOS 日历

本仓库自动从懂球帝获取实时赛程，并生成苹果系统可直接订阅的 `.ics` 日历文件。

### ✅ 支持球队
- 成都蓉城
- 国际米兰

### 📱 iOS / Mac 一键订阅地址

| 球队 | 订阅链接 |
|------|---------|
| 成都蓉城 | https://raw.githubusercontent.com/louiszeng0623/Yzeng17/main/calendar_chengdu.ics |
| 国际米兰 | https://raw.githubusercontent.com/louiszeng0623/Yzeng17/main/calendar_inter.ics |

### 📝 使用方法（iPhone）
1. 复制对应订阅链接
2. 打开 **设置**
3. 进入 **日历 → 账户 → 添加账户 → 其它**
4. 选择 **添加订阅日历**
5. 粘贴链接 → **下一步 → 完成**

### 🔄 自动更新机制
本仓库使用 GitHub Actions，每 6 小时自动更新一次赛程并同步到日历文件，无需手动维护。

---
