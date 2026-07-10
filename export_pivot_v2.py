"""
Playwright脚本v2：通过JS触发changeParams来切换部门筛选并导出
"""
import asyncio
import base64
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
        
        # 登录
        await page.goto(f"{BASE}/api.php/v2/users/login", timeout=30000)
        login_result = await page.evaluate("""
            async () => {
                const resp = await fetch('/api.php/v2/users/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({account: '260298', password: 'Lss@530720'})
                });
                return await resp.json();
            }
        """)
        print(f"Login: {login_result.get('status')}")
        
        # 导航到透视表页面
        await page.goto(f"{BASE}/pivot-preview-1-16441-worksummary.html", timeout=60000, wait_until='networkidle')
        
        # 检查页面初始状态
        info = await page.evaluate("""
            () => {
                const deptVal = document.querySelector('#dept')?.value;
                const table = document.querySelector('#worksummary');
                const rows = table ? table.querySelectorAll('tbody tr').length : 0;
                return {dept: deptVal, rows: rows};
            }
        """)
        print(f"Initial state: dept={info['dept']}, rows={info['rows']}")
        
        for dept_name, dept_id in DEPTS:
            print(f"\n=== {dept_name} (dept={dept_id}) ===")
            
            # 用JS改变筛选条件并触发changeParams
            await page.evaluate(f"""
                () => {{
                    // 设置部门
                    const deptSelect = document.querySelector('#dept');
                    if (deptSelect) deptSelect.value = '{dept_id}';
                    
                    // 设置日期
                    const beginPicker = document.querySelector('#beginPicker');
                    const endPicker = document.querySelector('#endPicker');
                    
                    // 调用changeParams触发页面跳转
                    if (typeof changeParams === 'function') {{
                        changeParams();
                    }}
                }}
            """)
            
            # 等待页面重新加载
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # 检查新页面的状态
            info = await page.evaluate("""
                () => {
                    const deptVal = document.querySelector('#dept')?.value;
                    const table = document.querySelector('#worksummary');
                    const rows = table ? table.querySelectorAll('tbody tr').length : 0;
                    const firstUser = document.querySelector('.w-user')?.innerText?.trim();
                    return {dept: deptVal, rows: rows, firstUser: firstUser};
                }
            """)
            print(f"  After filter: dept={info['dept']}, rows={info['rows']}, firstUser={info['firstUser']}")
            
            if info['rows'] == 0:
                print(f"  No data for {dept_name}, skipping export")
                continue
            
            # 导出
            download_promise = page.wait_for_download(timeout=30000)
            await page.evaluate("() => { if (typeof exportData === 'function') exportData(); }")
            
            try:
                download = await download_promise
                filename = f"任务完成汇总表_{dept_name}.xlsx"
                filepath = os.path.join(OUTPUT_DIR, filename)
                await download.save_as(filepath)
                print(f"  Exported: {filepath}")
            except Exception as e:
                print(f"  Export error: {e}")
        
        await browser.close()

asyncio.run(main())
