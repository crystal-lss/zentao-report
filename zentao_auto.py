#!/usr/bin/env python3
"""禅道自动化：在FMS-0715迭代下处理研发需求变更确认"""
import asyncio
import sys
from playwright.async_api import async_playwright

ZENTAO_URL = "https://ztpm.gree.com:8888"
ACCOUNT = "260298"
PASSWORD = "Lss@530720"

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Step 1: 登录
        print("正在登录禅道...")
        await page.goto(f"{ZENTAO_URL}/?m=user&f=login")
        await page.fill('input[name="account"]', ACCOUNT)
        await page.fill('input[name="password"]', PASSWORD)
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        
        # 检查登录状态
        current_url = page.url
        if "login" in current_url:
            # 可能登录失败，截图看看
            await page.screenshot(path="/Users/crystal/WorkBuddy/禅道任务/login_error.png")
            print(f"登录可能失败，当前URL: {current_url}")
            content = await page.content()
            print(f"页面标题: {await page.title()}")
        else:
            print(f"登录成功，当前URL: {current_url}")
        
        # Step 2: 搜索FMS-0715迭代
        # 先到执行列表
        print("\n搜索FMS-0715迭代...")
        await page.goto(f"{ZENTAO_URL}/?m=execution&f=all")
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        
        # 在搜索框中搜索
        try:
            search_input = page.locator('input[placeholder*="搜索"], input[name="name"], #executionName')
            if await search_input.count() > 0:
                await search_input.first.fill("FMS-0715")
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
        except Exception as e:
            print(f"搜索时出错: {e}")
        
        # 截图看看当前页面
        await page.screenshot(path="/Users/crystal/WorkBuddy/禅道任务/execution_list.png", full_page=True)
        print(f"页面标题: {await page.title()}")
        print(f"当前URL: {page.url}")
        
        # 查找FMS-0715链接
        links = await page.locator('a:has-text("FMS-0715")').all()
        print(f"找到 {len(links)} 个FMS-0715链接")
        
        for link in links:
            href = await link.get_attribute("href")
            text = await link.inner_text()
            print(f"  链接: {text} -> {href}")
        
        # Step 3: 如果有FMS-0715链接，点击进入
        if len(links) > 0:
            # 优先找执行链接
            execution_link = None
            for link in links:
                href = await link.get_attribute("href") or ""
                text = await link.inner_text()
                if "execution" in href:
                    execution_link = link
                    break
            
            if execution_link:
                print(f"\n点击进入: {await execution_link.inner_text()}")
                await execution_link.click()
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(2)
                print(f"进入后URL: {page.url}")
                await page.screenshot(path="/Users/crystal/WorkBuddy/禅道任务/execution_detail.png", full_page=True)
                
                # 找到需求列表
                print("\n查找需求Tab...")
                story_tab = page.locator('a:has-text("需求"), li:has-text("需求")').first
                if await story_tab.count() > 0:
                    await story_tab.click()
                    await page.wait_for_load_state("networkidle")
                    await asyncio.sleep(2)
                    print(f"需求页面URL: {page.url}")
                    await page.screenshot(path="/Users/crystal/WorkBuddy/禅道任务/story_list.png", full_page=True)
                    
                    # 查看页面内容，搜索"研发需求变更"
                    page_content = await page.content()
                    if "研发需求变更" in page_content or "需求变更" in page_content:
                        print("页面中包含'研发需求变更'相关文字")
                    
                    # 获取所有需求行
                    story_rows = await page.locator('table tr, .table tr, [class*="story"]').all()
                    print(f"找到 {len(story_rows)} 行/元素")
                    
                    # 找所有链接文字
                    all_links = await page.locator('a').all()
                    story_links = []
                    for a in all_links:
                        text = await a.inner_text()
                        href = await a.get_attribute("href") or ""
                        if "story" in href.lower() or "需求" in text:
                            story_links.append((text.strip(), href))
                    
                    print(f"\n需求相关链接 ({len(story_links)}个):")
                    for text, href in story_links[:30]:
                        print(f"  [{text}] -> {href}")
        
        await browser.close()
        print("\n完成。截图已保存。")

if __name__ == "__main__":
    asyncio.run(main())
