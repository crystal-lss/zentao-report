"""
Playwright v8: 使用WebKit浏览器，非headless模式
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

async def main():
    async with async_playwright() as p:
        # 尝试WebKit浏览器
        browser = await p.webkit.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        # 登录
        print("Login...")
        await page.goto(f"{BASE}/user-login.html", timeout=30000, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        await page.fill('input[name="account"]', '260298')
        await page.fill('input[name="password"]', 'Lss@530720')
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)
        
        # 导航到透视表
        print("Navigate to pivot...")
        await page.goto(f"{BASE}/pivot-preview-1-16441-worksummary.html", 
                       timeout=60000, wait_until='load')
        await page.wait_for_timeout(8000)
        
        # 检查是否有表格
        has_table = await page.evaluate("() => !!document.querySelector('#worksummary')")
        body_text = await page.evaluate("() => document.body?.innerText?.substring(0, 200)")
        print(f"Has table: {has_table}")
        print(f"Body: {body_text}")
        
        if has_table:
            print("Table found! Exporting...")
            async with page.expect_download(timeout=30000) as download_info:
                await page.evaluate("() => { if (typeof exportData === 'function') exportData(); }")
            download = await download_info.value
            filepath = os.path.join(OUTPUT_DIR, "pivot_export_webkit.xlsx")
            await download.save_as(filepath)
            print(f"Saved: {filepath}")
        else:
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "webkit_debug.png"), full_page=True)
        
        await browser.close()

asyncio.run(main())
