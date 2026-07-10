"""
Playwright v5: 完整流程 + 更长等待 + 调试
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        # 登录
        print("Login via form...")
        await page.goto(f"{BASE}/user-login.html", timeout=30000, wait_until='networkidle')
        await page.wait_for_timeout(3000)
        
        await page.fill('input[name="account"]', '260298')
        await page.fill('input[name="password"]', 'Lss@530720')
        await page.click('button[type="submit"]')
        await page.wait_for_timeout(5000)
        print(f"After login URL: {page.url}")
        
        # 导航到透视表
        print("Navigate to pivot...")
        await page.goto(f"{BASE}/pivot-preview-1-16441-worksummary.html", 
                       timeout=60000, wait_until='networkidle')
        
        # 等待更长时间让JS渲染
        print("Waiting 10s for JS rendering...")
        await page.wait_for_timeout(10000)
        
        # 检查是否有table
        html_snippet = await page.evaluate("""
            () => document.querySelector('#mainContent')?.innerHTML?.substring(0, 500) || 'no #mainContent'
        """)
        print(f"Main content: {html_snippet[:300]}")
        
        # 检查是否有worksummary table
        has_table = await page.evaluate("""
            () => {
                const t = document.querySelector('#worksummary');
                console.log('worksummary:', t);
                return !!t;
            }
        """)
        print(f"Has #worksummary: {has_table}")
        
        # 检查完整页面body
        body_text = await page.evaluate("() => document.body.innerText.substring(0, 500)")
        print(f"Body text: {body_text[:300]}")
        
        if not has_table:
            print("Still no table. Saving debug info...")
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "v5_screenshot.png"), full_page=True)
            with open(os.path.join(OUTPUT_DIR, "v5_page.html"), 'w') as f:
                f.write(await page.content())
            print("Saved v5_screenshot.png and v5_page.html")
        else:
            # 导出
            print("Table found! Exporting...")
            download_promise = page.wait_for_download(timeout=30000)
            await page.evaluate("() => { exportData(); }")
            download = await download_promise
            filepath = os.path.join(OUTPUT_DIR, "任务完成汇总表_默认.xlsx")
            await download.save_as(filepath)
            print(f"Saved: {filepath}")
        
        await browser.close()

asyncio.run(main())
