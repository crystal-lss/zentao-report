"""
Playwright v3: 完整登录流程 + 等待页面渲染
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

DEPTS = [
    ("开发七室", 124),
    ("软件测试室", 129),
    ("视觉设计室", 31),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        # Step 1: 先用登录页面登录 (这会设置session cookie)
        print("Step 1: Login via web form...")
        await page.goto(f"{BASE}/user-login.html", timeout=30000, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # 截图看登录页面
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "debug_login.png"))
        
        # 填写登录表单
        await page.fill('input[name="account"]', '260298')
        await page.fill('input[name="password"]', 'Lss@530720')
        await page.click('button[type="submit"]')
        
        # 等待登录完成
        await page.wait_for_timeout(5000)
        print(f"Login URL: {page.url}")
        
        # Step 2: 导航到透视表
        print("\nStep 2: Navigate to pivot table...")
        await page.goto(f"{BASE}/pivot-preview-1-16441-worksummary.html", timeout=60000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # 诊断页面
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "debug_pivot.png"), full_page=True)
        
        # 检查页面元素
        info = await page.evaluate("""
            () => {
                const hasDept = !!document.querySelector('#dept');
                const hasTable = !!document.querySelector('#worksummary');
                const hasExport = !!document.querySelector('[data-target="#export"]');
                const bodyText = document.body?.innerText?.substring(0, 500);
                return {
                    hasDept, hasTable, hasExport,
                    url: window.location.href,
                    title: document.title,
                    bodyPreview: bodyText
                };
            }
        """)
        print(f"Page state: {info}")
        
        if not info['hasTable']:
            print("ERROR: Table not found! Page might need more time to render.")
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "debug_error.png"), full_page=True)
            await browser.close()
            return
        
        # Step 3: 分别处理每个部门
        for dept_name, dept_id in DEPTS:
            print(f"\n=== {dept_name} (dept={dept_id}) ===")
            
            # 用JS改变筛选并触发跳转
            await page.evaluate(f"""
                () => {{
                    document.querySelector('#dept').value = '{dept_id}';
                    changeParams();
                }}
            """)
            
            # 等待页面重新加载
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 检查表格
            rows = await page.evaluate("""
                () => document.querySelectorAll('#worksummary tbody tr').length
            """)
            print(f"  Rows after filter: {rows}")
            
            if rows == 0:
                continue
            
            # 导出
            download_promise = page.wait_for_download(timeout=30000)
            await page.evaluate("() => { exportData(); }")
            
            try:
                download = await download_promise
                filename = f"任务完成汇总表_{dept_name}.xlsx"
                filepath = os.path.join(OUTPUT_DIR, filename)
                await download.save_as(filepath)
                print(f"  Saved: {filepath}")
            except Exception as e:
                print(f"  Export failed: {e}")
        
        await browser.close()

asyncio.run(main())
