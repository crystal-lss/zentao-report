"""
Playwright v6: 用fetch API获取页面（模仿curl行为）
"""
import asyncio
import os
import re
import json
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
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
        print(f"Login URL: {page.url}")
        
        # 用fetch API获取透视表页面 (类似curl的方式)
        print("Fetching pivot page via fetch API...")
        html = await page.evaluate("""
            async () => {
                const resp = await fetch('/pivot-preview-1-16441-worksummary.html');
                return await resp.text();
            }
        """)
        
        print(f"HTML length: {len(html)}")
        
        # 检查是否有表格
        has_table = '<table' in html and 'worksummary' in html
        print(f"Has table: {has_table}")
        
        if has_table:
            # 提取表格
            table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', html, re.DOTALL)
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_match.group(0), re.DOTALL)
            tr_count = len(re.findall(r'<tr[^>]*>', tbody_match.group(1)))
            
            # 提取用户
            users = set()
            for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_match.group(1), re.DOTALL):
                user_td = re.search(r'class="[^"]*w-user[^"]*"[^>]*rowspan="\d+"[^>]*>([^<]*)</td>', tr)
                if user_td:
                    name = user_td.group(1).strip()
                    if name and not name.replace('.', '').isdigit():
                        users.add(name)
            
            print(f"Rows: {tr_count}, Users: {sorted(users)}")
            
            # 获取总记录数
            rec_match = re.search(r'recTotal[:\s]*(\d+)', html)
            print(f"recTotal: {rec_match.group(1) if rec_match else 'N/A'}")
            
            # 保存HTML
            with open(os.path.join(OUTPUT_DIR, "pivot_fetched.html"), 'w') as f:
                f.write(html)
            print("Saved to pivot_fetched.html")
            
            # 尝试导出 - 设置innerHTML并导出
            print("\nAttempting export via JS...")
            await page.evaluate(f"""
                () => {{
                    // 创建一个隐藏的div来接收表格HTML
                    const div = document.createElement('div');
                    div.id = 'export-container';
                    div.style.display = 'none';
                    div.innerHTML = `{table_match.group(0)}`;
                    document.body.appendChild(div);
                    
                    // 触发导出
                    const table = div.querySelector('#worksummary');
                    if (table && typeof exportFile === 'function') {{
                        // We need to set up the export context
                    }}
                }}
            """)
            
            # 检查是否加载了导出所需的库
            has_xlsx = await page.evaluate("() => typeof XLSX !== 'undefined'")
            print(f"XLSX library loaded: {has_xlsx}")
            
            if not has_xlsx:
                print("XLSX not loaded, loading page normally to get JS libraries...")
                await page.goto(f"{BASE}/pivot-preview-1-16441-worksummary.html", 
                               timeout=60000, wait_until='networkidle')
                await page.wait_for_timeout(5000)
                has_xlsx = await page.evaluate("() => typeof XLSX !== 'undefined'")
                print(f"After page load, XLSX: {has_xlsx}")
        
        await browser.close()

asyncio.run(main())
