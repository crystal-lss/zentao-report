#!/usr/bin/env python3
"""批量确认FMS-0715的研发需求变更任务"""
import asyncio
from playwright.async_api import async_playwright

ZENTAO_URL = "https://ztpm.gree.com:8888"

# 已指派给黎思斯(260298) - confirmStoryChange可用
LS_TASKS = [
    300210, 300209, 300207, 300206, 300204, 300203, 300201, 300200,
    300198, 300197, 300195, 300194, 300191, 300190, 300188, 300187,
    294036, 294006, 293760, 293759,
]

# 指派给A80556/A80789 - 需要先改指派
OTHER_TASKS = {
    'A80556': [301685, 301276, 301272, 301271, 301266, 301265, 301264],
    'A80789': [300211, 300208, 300205, 300202, 300199, 300196, 300192, 300189],
}

async def confirm_tasks(page, task_ids):
    """确认研发需求变更"""
    success = 0
    fail = 0
    for tid in task_ids:
        try:
            url = f"{ZENTAO_URL}/task-confirmStoryChange-{tid}.html?confirm=yes"
            await page.goto(url, timeout=10000)
            await asyncio.sleep(0.5)
            # 判断是否成功（不包含error/失败等）
            content = await page.content()
            if "错误" in content or "失败" in content:
                print(f"  Task {tid}: 失败")
                fail += 1
            else:
                print(f"  Task {tid}: 确认成功")
                success += 1
        except Exception as e:
            print(f"  Task {tid}: 异常 - {e}")
            fail += 1
    return success, fail

async def reassign_task(page, task_id, from_user, to_user="260298"):
    """重新指派任务"""
    try:
        # ZenTao 指派页面
        url = f"{ZENTAO_URL}/task-assignTo-{task_id}.html?onlybody=yes"
        await page.goto(url, timeout=10000)
        await asyncio.sleep(1)
        
        # 查找指派表单
        # 尝试选择用户
        assigned_input = page.locator('input[name="assignedTo"], #assignedTo')
        if await assigned_input.count() > 0:
            # 如果能直接输入，填入260298
            await assigned_input.first.fill(to_user)
        
        # 查找提交按钮
        submit_btn = page.locator('button[type="submit"], input[type="submit"], #submit').first
        if await submit_btn.count() > 0:
            await submit_btn.click()
            await asyncio.sleep(1)
            print(f"  Task {task_id}: 指派成功 ({from_user} -> {to_user})")
            return True
        
        # 尝试直接编辑任务URL
        edit_url = f"{ZENTAO_URL}/task-edit-{task_id}.html?onlybody=yes"
        await page.goto(edit_url, timeout=10000)
        await asyncio.sleep(1)
        
        assigned_select = page.locator('select[name="assignedTo"], #assignedTo')
        if await assigned_select.count() > 0:
            await assigned_select.first.select_option(to_user)
            submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
            if await submit_btn.count() > 0:
                await submit_btn.click()
                await asyncio.sleep(1)
                return True
        
        print(f"  Task {task_id}: 无法指派，跳过")
        return False
    except Exception as e:
        print(f"  Task {task_id}: 指派异常 - {e}")
        return False

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
        
        print("登录...")
        await page.goto(f"{ZENTAO_URL}/?m=user&f=login")
        await page.fill('input[name="account"]', '260298')
        await page.fill('input[name="password"]', 'Lss@530720')
        await page.click('button[type="submit"]')
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(2)
        print("登录成功\n")
        
        # Phase 1: 确认黎思斯名下的任务
        print(f"Phase 1: 确认黎思斯名下 {len(LS_TASKS)} 个任务...")
        s, f = await confirm_tasks(page, LS_TASKS)
        print(f"  结果: {s} 成功, {f} 失败\n")
        
        # Phase 2: 重新指派 + 确认
        for user, task_ids in OTHER_TASKS.items():
            print(f"Phase 2: 处理 {user} 的 {len(task_ids)} 个任务...")
            for tid in task_ids:
                # 改指派
                reassigned = await reassign_task(page, tid, user)
                if reassigned:
                    # 确认
                    s, f = await confirm_tasks(page, [tid])
                else:
                    print(f"  Task {tid}: 跳过（指派失败）")
        
        await browser.close()
        print("\n完成。")

if __name__ == "__main__":
    asyncio.run(main())
