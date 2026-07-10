"""
Playwright final attempt: 通过BI应用入口进入透视表
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            accept_downloads=True,
            viewport={'width': 1920, 'height': 1080},
        )
        page = await context.new_page()
        
        # 登录
        await page.goto(f"{BASE}/user-login.html", timeout=30000)
        await page.wait_for_timeout(2000)
        await page.fill('input[name="account"]', '260298')
        await page.fill('input[name="password"]', 'Lss@530720')
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)
        print(f"Login: {page.url}")
        
        # 直接访问透视表（尝试不同的URL格式）
        urls = [
            f"{BASE}/pivot-preview-1-16441-worksummary.html",
            f"{BASE}/index.php?m=pivot&f=preview&dimension=1&group=16441&method=worksummary",
        ]
        
        for url in urls:
            print(f"\nTrying: {url}")
            await page.goto(url, timeout=60000, wait_until='load')
            await page.wait_for_timeout(10000)
            
            has_table = await page.evaluate("""
                () => {
                    const t = document.querySelector('#worksummary');
                    return !!t;
                }
            """)
            title = await page.title()
            body = await page.evaluate("() => document.body?.innerText?.substring(0, 200)")
            
            print(f"  Title: {title}")
            print(f"  Has table: {has_table}")
            print(f"  Body: {body[:100]}")
            
            if has_table:
                print(f"  SUCCESS! Trying export...")
                try:
                    async with page.expect_download(timeout=30000) as dl:
                        await page.evaluate("() => exportData()")
                    download = await dl.value
                    path = os.path.join(OUTPUT_DIR, f"pivot_export_final.xlsx")
                    await download.save_as(path)
                    print(f"  Exported: {path}")
                    await browser.close()
                    return
                except Exception as e:
                    print(f"  Export failed: {e}")
        
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "final_debug.png"), full_page=True)
        await browser.close()

asyncio.run(main())
