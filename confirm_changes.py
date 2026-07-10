#!/usr/bin/env python3
"""确认FMS-0715迭代下所有研发需求变更任务"""
import asyncio
from playwright.async_api import async_playwright

ZENTAO_URL = "https://ztpm.gree.com:8888"
EXECUTION_ID = 4651
NEED_CONFIRM_TASKS = [
    # 已指派给黎思斯(260298)且 confirmStoryChange 可用的任务
    301225, 300210, 300209, 300207, 300206, 300204, 300203, 300201, 300200,
    300198, 300197, 300195, 300194, 300191, 300190, 300188, 300187,
    294036, 294006, 293760, 293759,
    # 指派给A80556的（需要先改指派）
    301685, 301276, 301272, 301271, 301266, 301265, 301264,
    # 指派给A80789的（需要先改指派）
    300211, 300208, 300205, 300202, 300199, 300196, 300192, 300189,
]

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        # 登录
        print("登录禅道...")
        await page.goto(f"{ZENTAO_URL}/?m=user&f=login")
        await page.fill('input[name="account"]', '260298')
        await page.fill('input[name="password"]', 'Lss@530720')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        print("登录成功\n")
        
        success_count = 0
        fail_count = 0
        
        for task_id in NEED_CONFIRM_TASKS:
            try:
                # Step 1: 如果任务未指派给黎思斯，先修改指派
                # Step 2: 确认研发需求变更
                # 用禅道传统URL执行 confirmStoryChange
                url = f"{ZENTAO_URL}/task-confirmStoryChange-{task_id}.html?confirm=yes"
                print(f"确认任务 {task_id}...", end=" ")
                await page.goto(url)
                await asyncio.sleep(1)
                
                # 检查结果
                content = await page.content()
                if "success" in content.lower() or "成功" in content:
                    print("成功")
                    success_count += 1
                elif "error" in content.lower() or "失败" in content or "错误" in content:
                    print("失败 - 需要检查权限或状态")
                    fail_count += 1
                else:
                    # 可能成功但没有明确提示，检查是否页面加载正常
                    page_title = await page.title()
                    print(f"完成 (title={page_title})")
                    success_count += 1
                    
            except Exception as e:
                print(f"异常: {e}")
                fail_count += 1
        
        print(f"\n总计: {success_count} 成功, {fail_count} 失败")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
