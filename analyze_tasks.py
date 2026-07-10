"""
最终方案：从API任务数据直接生成Excel汇总表
由于无法获取透视表的完整数据和部门筛选，使用API数据作为替代
"""
import json
import csv
from datetime import datetime

# 加载6月完成的任务
with open('/Users/crystal/WorkBuddy/禅道任务/temp_filtered_tasks.json') as f:
    tasks = json.load(f)

# 排除 assignedTo=closed 的任务（这些是系统自动关闭的）
valid_tasks = [t for t in tasks if t.get('assignedTo') != 'closed']
print(f"Valid June tasks: {len(valid_tasks)} (excluded {len(tasks) - len(valid_tasks)} closed tasks)")

# 按所属项目和用户分组统计
from collections import defaultdict

user_stats = defaultdict(lambda: {
    'tasks': [],
    'total_consumed': 0.0,
    'total_estimate': 0.0,
    'projects': set(),
    'executions': set(),
})

for t in valid_tasks:
    user = t.get('assignedToRealName', t.get('assignedTo', 'Unknown')).strip()
    user_stats[user]['tasks'].append(t)
    user_stats[user]['total_consumed'] += float(t.get('consumed', 0) or 0)
    user_stats[user]['total_estimate'] += float(t.get('estimate', 0) or 0)
    user_stats[user]['projects'].add(t.get('project'))
    user_stats[user]['executions'].add(t.get('_exec_name', ''))

print(f"\nUsers with June-completed tasks: {len(user_stats)}")
for user, stats in sorted(user_stats.items()):
    print(f"  {user}: {len(stats['tasks'])} tasks, consumed={stats['total_consumed']}h, projects={stats['projects']}")

# 建立用户账号→部门映射
# 从任务数据中提取用户名和真实姓名
account_to_name = {}
for t in valid_tasks:
    acc = t.get('assignedTo', '').strip()
    name = t.get('assignedToRealName', '').strip()
    if acc and acc != 'closed':
        account_to_name[acc] = name

print(f"\nUnique accounts with tasks: {len(account_to_name)}")
for acc, name in sorted(account_to_name.items()):
    print(f"  {acc}: {name}")

# 将任务数据按用户分组保存
with open('/Users/crystal/WorkBuddy/禅道任务/user_task_stats.json', 'w') as f:
    # 转化sets为lists
    serializable = {}
    for user, stats in user_stats.items():
        serializable[user] = {
            'task_count': len(stats['tasks']),
            'total_consumed': stats['total_consumed'],
            'total_estimate': stats['total_estimate'],
            'projects': list(stats['projects']),
            'executions': list(stats['executions']),
        }
    json.dump(serializable, f, ensure_ascii=False, indent=2)

print("\nSaved user_task_stats.json")
