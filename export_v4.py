"""
Playwright v4: 直接用curl的cookie登录
"""
import asyncio
import json
import os
import base64
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

DEPTS = [
    ("开发七室", 124),
    ("软件测试室", 129),
    ("视觉设计室", 31),
]

async def main():
    # 读取curl的cookie
    with open('/tmp/zentao_cookies.txt') as f:
        cookie_text = f.read()
    
    # 解析Netscape格式cookie
    cookies = []
    for line in cookie_text.strip().split('\n'):
        if line.startswith('#') or not line.strip():
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            cookies.append({
                'name': parts[5],
                'value': parts[6],
                'domain': parts[0],
                'path': parts[2],
                'httpOnly': False,
                'secure': parts[3] == 'TRUE',
            })
    
    print(f"Loaded {len(cookies)} cookies")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        await context.add_cookies(cookies)
        page = await context.new_page()
        
        # 导航到透视表 (直接用cookie，不需要额外登录)
        print("Navigating to pivot table...")
        await page.goto(f"{BASE}/pivot-preview-1-16441-worksummary.html", 
                       timeout=60000, wait_until='networkidle')
        await page.wait_for_timeout(5000)
        
        # 诊断
        info = await page.evaluate("""
            () => {
                const deptEl = document.querySelector('#dept');
                const tableEl = document.querySelector('#worksummary');
                return {
                    hasDept: !!deptEl,
                    deptVal: deptEl?.value,
                    hasTable: !!tableEl,
                    trCount: tableEl?.querySelectorAll('tbody tr').length || 0,
                    title: document.title,
                    hasExportBtn: !!document.querySelector('[data-target="#export"]'),
                };
            }
        """)
        print(f"Page info: {info}")
        
        if not info['hasTable']:
            await page.screenshot(path=os.path.join(OUTPUT_DIR, "debug_v4.png"), full_page=True)
            print("ERROR: Table not found")
            await browser.close()
            return
        
        for dept_name, dept_id in DEPTS:
            print(f"\n=== {dept_name} (dept={dept_id}) ===")
            
            # 用JS改变筛选并触发changeParams
            await page.evaluate(f"""
                () => {{
                    document.querySelector('#dept').value = '{dept_id}';
                    if (typeof changeParams === 'function') changeParams();
                }}
            """)
            
            # 等待页面跳转后的新页面
            await page.wait_for_load_state('networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # 检查
            rows = await page.evaluate("""
                () => {
                    const table = document.querySelector('#worksummary');
                    if (!table) return 0;
                    const rows = table.querySelectorAll('tbody tr');
                    const firstUser = document.querySelector('.w-user')?.innerText?.trim();
                    return rows.length;
                }
            """)
            
            dept_val = await page.evaluate("() => document.querySelector('#dept')?.value")
            print(f"  dept={dept_val}, rows={rows}")
            
            if rows == 0:
                print(f"  SKIP: no data")
                continue
            
            # 导出
            await page.evaluate("() => { exportData(); }")
            
            # 等待下载
            try:
                async with page.expect_download(timeout=30000) as download_info:
                    await page.evaluate("() => { exportData(); }")
                download = await download_info.value
                filename = f"任务完成汇总表_{dept_name}.xlsx"
                filepath = os.path.join(OUTPUT_DIR, filename)
                await download.save_as(filepath)
                print(f"  SAVED: {filepath}")
            except Exception as e:
                print(f"  Export error: {e}")
        
        await browser.close()

asyncio.run(main())
