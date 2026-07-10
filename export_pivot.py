"""
Playwright脚本：从禅道透视表导出三个部门的任务完成数据
"""
import asyncio
import base64
import os
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

# 三个部门的配置
DEPTS = [
    ("开发七室", 124),
    ("软件测试室", 129),
    ("视觉设计室", 31),
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            storage_state=None,
        )
        
        # 先登录获取cookie
        page = await context.new_page()
        await page.goto(f"{BASE}/api.php/v2/users/login", timeout=30000)
        
        # 使用账号密码登录，然后获取session
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
        
        for dept_name, dept_id in DEPTS:
            print(f"\n=== Processing {dept_name} (dept={dept_id}) ===")
            
            # 构建params
            param_str = f'begin=20260601&end=20260630&dept={dept_id}'
            encoded = base64.b64encode(param_str.encode()).decode()
            url = f"{BASE}/pivot-preview-1-16441-worksummary.html?params={encoded}"
            
            print(f"Navigating to: {url}")
            await page.goto(url, timeout=60000, wait_until='networkidle')
            
            # 检查页面加载情况
            rec_total = await page.evaluate("""
                () => {
                    const text = document.body.innerText;
                    // 检查是否有完成者数据
                    const table = document.querySelector('#worksummary');
                    const rows = table ? table.querySelectorAll('tbody tr').length : 0;
                    return {rows: rows, title: document.title};
                }
            """)
            print(f"  Rows: {rec_total['rows']}, Title: {rec_total['title']}")
            
            # 尝试通过触发changeParams来改变筛选
            # 先设置dept值
            await page.evaluate(f"""
                () => {{
                    const deptSelect = document.querySelector('#dept');
                    if (deptSelect) {{
                        deptSelect.value = '{dept_id}';
                        // 也尝试设置日期
                        const beginPicker = document.querySelector('#beginPicker');
                        const endPicker = document.querySelector('#endPicker');
                    }}
                }}
            """)
            
            # 直接调用exportData导出
            download_promise = page.wait_for_download(timeout=30000)
            
            await page.evaluate("""
                () => {
                    exportData();
                }
            """)
            
            try:
                download = await download_promise
                filename = f"任务完成汇总表_{dept_name}.xlsx"
                filepath = os.path.join(OUTPUT_DIR, filename)
                await download.save_as(filepath)
                print(f"  Saved: {filepath}")
            except Exception as e:
                print(f"  Download error: {e}")
                # 尝试另一种导出方式
                await page.screenshot(path=os.path.join(OUTPUT_DIR, f"debug_{dept_name}.png"))
        
        await browser.close()

asyncio.run(main())
