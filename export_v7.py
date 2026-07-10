"""
Playwright v7: 匹配curl的user-agent和headers
"""
import asyncio
import os
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

async def main():
    async with async_playwright() as p:
        # 使用与curl相同的User-Agent
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            accept_downloads=True,
            user_agent='curl/8.7.1',
            viewport={'width': 1920, 'height': 1080},
        )
        page = await context.new_page()
        
        # 登录
        print("Login via form...")
        await page.goto(f"{BASE}/user-login-lax.html", timeout=30000, wait_until='networkidle')
        await page.wait_for_timeout(2000)
        
        # 看看有哪些登录相关页面
        content = await page.content()
        if 'account' in content:
            await page.fill('input[name="account"]', '260298')
            await page.fill('input[name="password"]', 'Lss@530720')
            await page.click('button[type="submit"]')
            await page.wait_for_timeout(5000)
            print(f"Logged in: {page.url}")
        
        # 直接fetch透视表
        print("Fetching pivot via fetch API...")
        resp = await page.evaluate("""
            async () => {
                const resp = await fetch('/pivot-preview-1-16441-worksummary.html');
                const html = await resp.text();
                return {
                    status: resp.status,
                    length: html.length,
                    hasTable: html.includes('worksummary'),
                };
            }
        """)
        print(f"Fetch result: {resp}")
        
        # 保存HTML
        html = await page.evaluate("""
            async () => {
                const resp = await fetch('/pivot-preview-1-16441-worksummary.html');
                return await resp.text();
            }
        """)
        
        if resp['hasTable']:
            with open(os.path.join(OUTPUT_DIR, "pivot_fetched_v7.html"), 'w') as f:
                f.write(html)
            print(f"Saved HTML ({len(html)} chars)")
            
            # 尝试在页面中渲染
            await page.evaluate(f"""
                () => {{
                    document.body.innerHTML = `{html}`;
                }}
            """)
            await page.wait_for_timeout(3000)
            
            # 检查渲染后的状态
            has_table = await page.evaluate("() => !!document.querySelector('#worksummary')")
            print(f"After render: has #worksummary = {has_table}")
            
            if has_table:
                # 尝试导出 - 需要加载XLSX库
                await page.evaluate("""
                    () => {
                        const script1 = document.createElement('script');
                        script1.src = '/js/sheetjs/xlsx.full.min.js';
                        document.head.appendChild(script1);
                    }
                """)
                await page.wait_for_timeout(2000)
                
                xlsx_loaded = await page.evaluate("() => typeof XLSX !== 'undefined'")
                print(f"XLSX loaded: {xlsx_loaded}")
                
                if xlsx_loaded:
                    # 直接从DOM导出
                    result = await page.evaluate("""
                        () => {
                            try {
                                const table = document.querySelector('#worksummary');
                                const wb = XLSX.utils.table_to_book(table, {raw: true});
                                const data = XLSX.write(wb, {type: 'array', bookType: 'xlsx'});
                                // Convert to base64 for download
                                const blob = new Blob([new Uint8Array(data)], {type: 'application/octet-stream'});
                                const url = URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.href = url;
                                a.download = 'export.xlsx';
                                a.click();
                                return 'done';
                            } catch(e) {
                                return 'error: ' + e.message;
                            }
                        }
                    """)
                    print(f"Export result: {result}")
        
        await browser.close()

asyncio.run(main())
