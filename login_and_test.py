import subprocess, json, sys

BASE = "https://ztpm.gree.com:8888"

# Step 1: Login
login_result = subprocess.run([
    'curl', '-s', '-c', '/tmp/zentao_cookies.txt',
    '-X', 'POST', f'{BASE}/api.php/v2/users/login',
    '-H', 'Content-Type: application/json',
    '-d', '{"account":"260298","password":"Lss@530720"}'
], capture_output=True, text=True)
print("Login:", login_result.stdout[:200])

# Step 2: Test projects
r = subprocess.run([
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/api.php/v2/projects?browseType=doing&recPerPage=20'
], capture_output=True, text=True)
data = json.loads(r.stdout)
if 'projects' in data:
    for p in data['projects']:
        print(f"Project {p['id']}: {p['name']} (model={p.get('model','?')})")
else:
    print("Projects:", json.dumps(data, ensure_ascii=False)[:500])

# Step 3: Test products
r2 = subprocess.run([
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/api.php/v2/products?browseType=all&recPerPage=20'
], capture_output=True, text=True)
data2 = json.loads(r2.stdout)
if 'products' in data2:
    for p in data2['products']:
        print(f"Product {p['id']}: {p['name']}")
else:
    print("Products:", json.dumps(data2, ensure_ascii=False)[:500])

# Step 4: Test task list
r3 = subprocess.run([
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/api.php/v2/tasks?status=all&recPerPage=5'
], capture_output=True, text=True)
data3 = json.loads(r3.stdout)
if 'tasks' in data3:
    for t in data3['tasks'][:5]:
        print(f"Task {t['id']}: {t['name'][:50]} (project={t.get('project')})")
else:
    print("Tasks:", json.dumps(data3, ensure_ascii=False)[:500])
