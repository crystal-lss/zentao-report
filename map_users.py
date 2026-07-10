import subprocess, re, json

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

# 从初始页面提取所有完成者
with open('/Users/crystal/WorkBuddy/禅道任务/pivot_page.html') as f:
    html = f.read()

# 提取所有完成者名字
users = set()
user_matches = re.findall(r'rowspan="\d+">([^<]+)</td>', html)
for u in user_matches:
    u = u.strip()
    if u:
        users.add(u)
print(f"Found {len(users)} unique users in pivot table")
for u in sorted(users):
    print(f"  {u}")

# 尝试用cookie获取用户详情
# 基于task数据中的assignedTo账号，尝试逐个查用户
user_accounts = set()
with open('/Users/crystal/WorkBuddy/禅道任务/temp_filtered_tasks.json') as f:
    tasks = json.load(f)
    for t in tasks:
        acc = t.get('assignedTo', '')
        if acc and acc != 'closed':
            user_accounts.add(acc)

print(f"\n{len(user_accounts)} unique user accounts from tasks with finishedDate in June")

# 把完成者姓名映射到账号
# 从task数据中建立映射
name_to_account = {}
for t in tasks:
    name = t.get('assignedToRealName', '').strip()
    acc = t.get('assignedTo', '').strip()
    if name and acc and acc != 'closed':
        if name not in name_to_account:
            name_to_account[name] = set()
        name_to_account[name].add(acc)

print(f"\n{len(name_to_account)} name→account mappings")
for name in sorted(users):
    accs = name_to_account.get(name, set())
    print(f"  {name}: {accs}")

# 保存映射
with open('/Users/crystal/WorkBuddy/禅道任务/user_mapping.json', 'w') as f:
    # Convert sets to lists for JSON
    serializable = {k: list(v) for k, v in name_to_account.items()}
    json.dump({'users': list(users), 'mapping': serializable}, f, ensure_ascii=False, indent=2)
