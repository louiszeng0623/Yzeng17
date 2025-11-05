from playwright.sync_api import sync_playwright
import pandas as pd

TEAMS = {
    "chengdu": "https://www.dongqiudi.com/team/50076899.html",
    "inter": "https://www.dongqiudi.com/team/50001042.html",
}

def scrape(team, url, page):
    print(f"▶ 开始抓取 {team} …")
    page.goto(url, timeout=60000)
    page.wait_for_timeout(1500)

    # 点击“赛程”
    page.locator("text=赛程").click()
    page.wait_for_timeout(2000)

    # 等待比赛卡片加载
    page.wait_for_selector(".match-item", timeout=15000)

    items = page.locator(".match-item").all()
    data = []

    for item in items:
        try:
            date = item.locator(".match-time").inner_text().strip()
            event = item.locator(".match-name").inner_text().strip()
            home = item.locator(".team.home .team-name").inner_text().strip()
            score = item.locator(".score").inner_text().strip()
            away = item.locator(".team.away .team-name").inner_text().strip()
        except:
            continue

        data.append([date, event, home, score, away])

    df = pd.DataFrame(data, columns=["日期时间", "赛事", "主队", "比分", "客队"])
    df.to_csv(f"data/{team}.csv", index=False)

    print(f"✅ {team}.csv 抓取成功，共 {len(df)} 场")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for team, url in TEAMS.items():
        scrape(team, url, page)

    browser.close()
