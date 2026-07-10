#!/usr/bin/env python3
"""批量确认FMS-0715和FMS-0730迭代的研发需求变更"""
import requests
import time
import json

TOKEN = "b2dd540252514fb6d2983ddbbba7fa97"
BASE = "https://ztpm.gree.com:8888"
COOKIE = {"zentaosid": TOKEN, "lang": "zh-cn"}
HEADERS = {
    "token": TOKEN,
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json"
}
HEADERS_NOJSON = {
    "token": TOKEN,
    "X-Requested-With": "XMLHttpRequest",
}

def get_needconfirm_tasks(exec_id):
    """获取执行的needconfirm任务列表"""
    url = f"{BASE}/execution-task-{exec_id}-needconfirm-0-status,id_desc-143-100-1-execution-0.html?zin=1"
    r = requests.get(url, headers=HEADERS_NOJSON, cookies=COOKIE, verify=False)
    html = r.text

    # Parse dtable JSON
    start = html.find('zui-create-dtable="') + len('zui-create-dtable="')
    # Find end by brace counting
    brace = 0
    in_str = False
    esc = False
    end = start
    for i in range(start, len(html)):
        ch = html[i]
        if esc:
            esc = False
            continue
        if ch == '\\':
            esc = True
            continue
        if ch == '&':
            sc = html.find(';', i)
            if sc > 0 and sc - i < 6:
                i = sc
                continue
        if ch == '"':
            in_str = not in_str
        elif not in_str:
            if ch in '{[':
                brace += 1
            elif ch in '}]':
                brace -= 1
                if brace == 0:
                    end = i + 1
                    break

    js_str = html[start:end]
    js_str = js_str.replace('&quot;', '"').replace('&amp;', '&')

    # Extract data array manually
    data_start = js_str.find('"data":[') + len('"data":')
    arr_str = js_str[data_start:]
    # Find matching ]
    brace2 = 0
    in_str2 = False
    esc2 = False
    end2 = 0
    for i in range(len(arr_str)):
        ch = arr_str[i]
        if esc2:
            esc2 = False
            continue
        if ch == '\\':
            esc2 = True
            continue
        if ch == '"':
            in_str2 = not in_str2
        elif not in_str2:
            if ch == '[':
                brace2 += 1
            elif ch == ']':
                brace2 -= 1
                if brace2 == 0:
                    end2 = i + 1
                    break

    tasks = json.loads(arr_str[:end2])
    return tasks

def assign_task(task_id):
    """通过API指派任务给260298"""
    r = requests.put(
        f"{BASE}/api.php/v2/tasks/{task_id}",
        json={"assignedTo": "260298"},
        headers=HEADERS,
        cookies=COOKIE,
        verify=False
    )
    result = r.json()
    return result.get("status") == "success"

def confirm_task(task_id):
    """确认研发需求变更"""
    r = requests.get(
        f"{BASE}/task-confirmStoryChange-{task_id}.html?confirm=yes",
        headers=HEADERS_NOJSON,
        cookies=COOKIE,
        verify=False,
        allow_redirects=True
    )
    return r.status_code == 200

# ========== FMS-0715 剩余任务 ==========
print("=" * 60)
print("FMS-0715 (exec=4651) - A80789剩余任务")
print("=" * 60)

A80789_tasks = [300211, 300208, 300205, 300202, 300199, 300196, 300192, 300189]

# 尝试直接确认（不改指派）
print("\n尝试直接确认(不改指派)...")
for tid in A80789_tasks:
    ok = confirm_task(tid)
    print(f"  Task {tid}: {'成功' if ok else '失败'}")
    time.sleep(0.3)

# 检查还是否在needconfirm中
print("\n检查FMS-0715剩余任务...")
remaining_0715 = get_needconfirm_tasks(4651)
print(f"  剩余: {len(remaining_0715)} 个")
for t in remaining_0715:
    acts = []
    for a in (t.get("actions") or []):
        name = a.get("name", "?")
        if name == "dropdown" and a.get("items"):
            acts.extend([i.get("name", "?") for i in a["items"]])
        else:
            acts.append(name)
    print(f"  Task {t['id']}: {t['name'][:50]} | assignedTo={t.get('assignedTo','none')} | actions={acts}")

# ========== FMS-0730 ==========
print("\n" + "=" * 60)
print("FMS-0730 (exec=4665)")
print("=" * 60)

tasks_0730 = get_needconfirm_tasks(4665)
print(f"研发需求变更任务: {len(tasks_0730)} 个\n")

# Group by assignedTo
by_assignee = {}
for t in tasks_0730:
    at = t.get("assignedTo", "none")
    by_assignee.setdefault(at, []).append(t)

for at, tasks in by_assignee.items():
    acts = []
    for a in (tasks[0].get("actions") or []) if tasks else []:
        name = a.get("name", "?")
        if name == "dropdown" and a.get("items"):
            acts.extend([f"{i.get('name','?')}{'(D)' if i.get('disabled') else ''}" for i in a["items"]])
        else:
            acts.append(f"{name}{'(D)' if a.get('disabled') else ''}")
    print(f"  {at}: {len(tasks)} 个, actions={acts}")

# Process FMS-0730 tasks
all_tasks_0730 = [t["id"] for t in tasks_0730]
non_ls = [t for t in tasks_0730 if t.get("assignedTo") != "260298" and t.get("assignedTo") != "260298"]
ls_tasks = [t for t in tasks_0730 if t.get("assignedTo") == "260298"]

print(f"\n黎思斯名下: {len(ls_tasks)} 个")
print(f"其他人名下: {len(non_ls)} 个")

# Phase 1: Assign non-LS tasks
if non_ls:
    print("\nPhase 1: 改指派...")
    for t in non_ls:
        tid = t["id"]
        ok = assign_task(tid)
        print(f"  Task {tid}: {'指派成功' if ok else '指派失败'}")
        time.sleep(0.3)

# Phase 2: Confirm all
# Get fresh list
tasks_0730 = get_needconfirm_tasks(4665)
all_tasks_0730 = [t["id"] for t in tasks_0730]
print(f"\nPhase 2: 确认 {len(all_tasks_0730)} 个任务...")
success = 0
for tid in all_tasks_0730:
    ok = confirm_task(tid)
    if ok:
        success += 1
    print(f"  Task {tid}: {'成功' if ok else '失败'}")
    time.sleep(0.3)

# Final check for FMS-0730
tasks_0730_final = get_needconfirm_tasks(4665)
print(f"\nFMS-0730 最终剩余: {len(tasks_0730_final)} 个")
for t in tasks_0730_final:
    print(f"  Task {t['id']}: {t.get('name','?')[:60]}")

# Final check for FMS-0715
remaining_0715_final = get_needconfirm_tasks(4651)
print(f"\nFMS-0715 最终剩余: {len(remaining_0715_final)} 个")
for t in remaining_0715_final:
    print(f"  Task {t['id']}: {t.get('name','?')[:60]}")

print("\n全部完成!")
