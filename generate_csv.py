"""
终极方案：从API任务数据+透视表结构，直接生成Excel
"""
import json
import re
from datetime import datetime
from collections import defaultdict

# ====== 第1步：加载API任务数据 ======
with open('/Users/crystal/WorkBuddy/禅道任务/temp_filtered_tasks.json') as f:
    all_tasks = json.load(f)

# 排除assignedTo=closed的任务
valid_tasks = [t for t in all_tasks if t.get('assignedTo') != 'closed']

# ====== 第2步：获取项目名称映射 ======
import subprocess
TOKEN = "0fa661149dcc428d6737e292785c9e39"
BASE = "https://ztpm.gree.com:8888/api.php/v2"

# 获取项目名称
project_names = {}
cmd = f'curl -s "{BASE}/projects?browseType=all&recPerPage=100" -H "token: {TOKEN}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
try:
    projects_data = json.loads(result.stdout)
    for p in projects_data.get('projects', []):
        project_names[p['id']] = p['name']
except:
    pass

# ====== 第3步：按完成者分组 ======
user_data = defaultdict(lambda: {
    'tasks': [],
    'total_consumed': 0.0,
    'total_estimate': 0.0,
})

for t in valid_tasks:
    name = t.get('assignedToRealName', '').strip()
    if not name:
        name = t.get('assignedTo', 'Unknown').strip()
    
    # 计算延期天数
    finished_date = t.get('finishedDate', '')
    deadline = t.get('deadline', '')
    delay_days = ''
    if finished_date and deadline:
        try:
            fd = datetime.strptime(finished_date[:10], '%Y-%m-%d')
            dl = datetime.strptime(deadline[:10], '%Y-%m-%d')
            delay = (fd - dl).days
            delay_days = str(delay) if delay > 0 else ''
        except:
            pass
    
    user_data[name]['tasks'].append({
        'project_name': project_names.get(t.get('project'), str(t.get('project', ''))),
        'exec_name': t.get('_exec_name', ''),
        'id': t.get('id'),
        'name': t.get('name'),
        'pri': t.get('pri', ''),
        'est_started': t.get('estStarted', ''),
        'real_started': t.get('realStarted', '')[:10] if t.get('realStarted') else '',
        'deadline': t.get('deadline', ''),
        'finished_date': finished_date[:10] if finished_date else '',
        'delay_days': delay_days,
        'estimate': float(t.get('estimate', 0) or 0),
        'consumed': float(t.get('consumed', 0) or 0),
    })
    
    user_data[name]['total_consumed'] += float(t.get('consumed', 0) or 0)
    user_data[name]['total_estimate'] += float(t.get('estimate', 0) or 0)

# ====== 第4步：生成CSV(Excel源数据) ======
import csv

csv_rows = []
headers = ['完成者', '所属项目', '所属执行', '编号', '任务名称', 'P', '预计开始', 
           '实际开始', '截止日期', '实际完成', '延期(天)', '最初预计', '任务消耗工时']

for user_name in sorted(user_data.keys()):
    stats = user_data[user_name]
    total_tasks = len(stats['tasks'])
    
    for i, task in enumerate(stats['tasks']):
        row = [
            user_name,
            task['project_name'],
            task['exec_name'],
            task['id'],
            task['name'],
            task['pri'],
            task['est_started'],
            task['real_started'],
            task['deadline'],
            task['finished_date'],
            task['delay_days'],
            task['estimate'],
            task['consumed'],
        ]
        csv_rows.append(row)

output_path = '/Users/crystal/WorkBuddy/禅道任务/任务完成汇总_6月_全部.csv'
with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    writer.writerow([])  # 空行
    for row in csv_rows:
        writer.writerow(row)

print(f"Generated CSV: {output_path}")
print(f"Total users: {len(user_data)}")
print(f"Total tasks: {len(csv_rows)}")

# 用户汇总
print("\n=== User Summary ===")
for user_name in sorted(user_data.keys()):
    stats = user_data[user_name]
    print(f"  {user_name}: {len(stats['tasks'])} tasks, consumed={stats['total_consumed']}h, estimate={stats['total_estimate']}h")
