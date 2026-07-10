#!/usr/bin/env python3
"""禅道：在FMS-0715迭代下处理研发需求变更确认"""
import asyncio
from playwright.async_api import async_playwright

ZENTAO_URL = "https://ztpm.gree.com:8888"
ACCOUNT = "260298"
PASSWORD = "Lss@530720"
EXECUTION_ID = 4651

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 登录
        print("1. 登录禅道...")
        await page.goto(f"{ZENTAO_URL}/?m=user&f=login")
        await page.fill('input[name="account"]', ACCOUNT)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        print(f"   登录成功: {page.url}")
        
        # 直接导航到执行需求页面
        print(f"\n2. 进入FMS-0715迭代需求页面...")
        await page.goto(f"{ZENTAO_URL}/execution-story-{EXECUTION_ID}.html?browseType=all")
        await asyncio.sleep(5)
        
        # 截图看看
        await page.screenshot(path="/Users/crystal/WorkBuddy/禅道任务/story_page.png", full_page=True)
        print(f"   页面标题: {await page.title()}")
        
        # 在页面上搜索所有按钮
        all_buttons = await page.locator('button, a.btn, .btn, [role="button"]').all()
        print(f"\n3. 找出所有按钮...")
        found_buttons = []
        for btn in all_buttons:
            try:
                text = (await btn.inner_text()).strip()
                href = await btn.get_attribute('href') or ''
                cls = await btn.get_attribute('class') or ''
                if text and ('变更' in text or '确认' in text or '研发' in text or '指派' in text or 'assign' in text.lower()):
                    found_buttons.append((text, href, cls))
            except:
                pass
        
        if found_buttons:
            print("   找到相关按钮:")
            for text, href, cls in found_buttons:
                print(f"   [{text}] class={cls[:50]} href={href[:80]}")
        else:
            print("   没有找到直接相关的按钮")
        
        # 在页面上搜索所有链接和文本
        print(f"\n4. 搜索页面中的关键文本...")
        body_text = await page.locator('body').inner_text()
        lines = body_text.split('\n')
        key_lines = []
        for line in lines:
            line = line.strip()
            if line and any(kw in line for kw in ['变更', '确认', '研发需求', '指派', '黎思斯', 'processStoryChange']):
                key_lines.append(line)
        for line in key_lines[:30]:
            print(f"   {line[:120]}")
        
        # 查找表格中的操作列
        print(f"\n5. 查找表格操作列...")
        table_cells = await page.locator('td, th').all()
        action_cells = []
        for cell in table_cells:
            try:
                text = (await cell.inner_text()).strip()
                if '变更' in text:
                    action_cells.append(text)
            except:
                pass
        for text in action_cells[:20]:
            print(f"   {text[:100]}")
        
        # 也看看toolbar
        print(f"\n6. 查找toolbar...")
        toolbars = await page.locator('.toolbar, #toolbar, [class*="toolbar"]').all()
        for tb in toolbars:
            text = (await tb.inner_text()).strip()
            if text:
                print(f"   Toolbar: {text[:200]}")
        
        # 查找所有下拉菜单
        print(f"\n7. 查找下拉菜单项...")
        dropdown_items = await page.locator('.dropdown-menu a, .dropdown-item, [role="menuitem"]').all()
        for item in dropdown_items:
            try:
                text = (await item.inner_text()).strip()
                if text and ('变更' in text or '确认' in text):
                    print(f"   菜单项: {text[:100]}")
            except:
                pass
        
        await browser.close()
        print("\n完成。")

if __name__ == "__main__":
    asyncio.run(main())
