"""
用Playwright的fetch API获取所有34页透视表数据 - 模拟JS执行
"""
import asyncio
import os
import base64
import re
import json
from playwright.async_api import async_playwright

BASE = "https://ztpm.gree.com:8888"
OUTPUT_DIR = "/Users/crystal/WorkBuddy/禅道任务"

def parse_users_from_html(html):
    """从HTML中提取完成者名称"""
    table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', html, re.DOTALL)
    if not table_match:
        return set()
    
    users = set()
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(0), re.DOTALL):
        user_td = re.search(r'class="[^"]*w-user[^"]*"[^>]*rowspan="\d+"[^>]*>([^<]*)</td>', tr)
        if user_td:
            name = user_td.group(1).strip()
            if name and not name.replace('.', '').isdigit():
                users.add(name)
    return users

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        # 登录 - 用fetch API
        print("Logging in...")
        
        # 先访问登录页获取初始cookie
        await page.goto(f"{BASE}/user-login.html", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # 用fetch登录
        login_resp = await page.evaluate("""
            async () => {
                const resp = await fetch('/api.php/v2/users/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({account: '260298', password: 'Lss@530720'})
                });
                return await resp.json();
            }
        """)
        token = login_resp.get('token', '')
        print(f"Login: {login_resp.get('status')}, token={token[:10]}...")
        
        # 用fetch获取透视表数据（就像curl一样）
        all_users = set()
        
        for page_num in range(1, 35):  # 34页
            # 构建params
            param_str = f'begin=20260501&end=&dept=0&recTotal=677&recPerPage=20&pageID={page_num}'
            encoded = base64.b64encode(param_str.encode()).decode()
            
            html = await page.evaluate(f"""
                async () => {{
                    const resp = await fetch('/pivot-preview-1-16441-worksummary.html?params={encoded}');
                    return await resp.text();
                }}
            """)
            
            users = parse_users_from_html(html)
            all_users.update(users)
            
            if users:
                print(f"Page {page_num}: {len(users)} users -> {sorted(users)}")
            
            # 如果连续3页没有新用户，可能说明参数不生效
            if page_num > 2 and len(users) == 0:
                print(f"Page {page_num}: no users found, params might not work")
        
        print(f"\nTotal unique users across all pages: {len(all_users)}")
        for u in sorted(all_users):
            print(f"  {u}")
        
        await browser.close()

asyncio.run(main())
