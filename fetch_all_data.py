"""Fetch all ZenTao data needed for the dashboard report."""
import subprocess, json, sys, os
from datetime import datetime, date

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = "/tmp/zentao_cookies.txt"
OUTDIR = "/Users/crystal/WorkBuddy/禅道任务/report_data"

os.makedirs(OUTDIR, exist_ok=True)

def api_get(path, params=""):
    url = f"{BASE}/api.php/v2/{path}"
    if params:
        url += "?" + params
    r = subprocess.run([
        'curl', '-s', '-b', COOKIE_FILE, url
    ], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except:
        print(f"ERROR parsing {path}: {r.stdout[:200]}")
        return {}

def login():
    r = subprocess.run([
        'curl', '-s', '-c', COOKIE_FILE,
        '-X', 'POST', f'{BASE}/api.php/v2/users/login',
        '-H', 'Content-Type: application/json',
        '-d', '{"account":"260298","password":"Lss@530720"}'
    ], capture_output=True, text=True)
    data = json.loads(r.stdout)
    print(f"Login: {data.get('status')} as {data.get('user',{}).get('realname','?')}")
    return data.get('status') == 'success'

def fetch_all_pages(path, params=""):
    """Fetch all pages of a list endpoint."""
    all_items = []
    page = 1
    while True:
        p = params + (f"&pageID={page}" if params else f"pageID={page}")
        if "recPerPage" not in p:
            p += "&recPerPage=100"
        data = api_get(path, p)
        # Find the array key
        items = None
        for key in ['tasks', 'executions', 'stories', 'bugs', 'users', 'projects', 'products']:
            if key in data:
                items = data[key]
                break
        if not items:
            break
        all_items.extend(items)
        if len(items) < 100:
            break
        page += 1
        if page > 50:  # safety
            break
    return all_items

# ====== MAIN ======
if not login():
    print("LOGIN FAILED")
    sys.exit(1)

# Step 1: Get projects info
print("\n=== Projects ===")
projects_data = api_get("projects", "browseType=doing&recPerPage=20")
projects = projects_data.get('projects', [])
fms_id = gas_id = None
for p in projects:
    print(f"  {p['id']}: {p['name']}")
    if '销售财务中台' in p['name']:
        fms_id = p['id']
    if '海外售后GAS' in p['name'] or 'GAS' in p['name']:
        gas_id = p['id']

print(f"\nFMS project ID: {fms_id}, GAS project ID: {gas_id}")

# Step 2: Get executions for both projects
print("\n=== Executions ===")
all_executions = []
for pid, pname in [(fms_id, "FMS"), (gas_id, "GAS")]:
    if not pid:
        continue
    execs = api_get(f"projects/{pid}/executions", "browseType=all&recPerPage=200")
    for e in execs.get('executions', []):
        e['_project'] = pname
        e['_pid'] = pid
        all_executions.append(e)
    print(f"  {pname}: {len(execs.get('executions',[]))} executions")

# Save executions
with open(f"{OUTDIR}/executions.json", 'w') as f:
    json.dump(all_executions, f, ensure_ascii=False, indent=2)
print(f"Saved {len(all_executions)} executions")

# Step 3: Get tasks for each execution
print("\n=== Fetching tasks ===")
all_tasks = []
for ex in all_executions:
    tasks = fetch_all_pages(f"executions/{ex['id']}/tasks", "status=all&recPerPage=100")
    for t in tasks:
        t['_project'] = ex['_project']
        t['_pid'] = ex['_pid']
        t['_execution_name'] = ex.get('name', '')
    all_tasks.extend(tasks)
    if len(tasks) > 0:
        print(f"  {ex['_project']}/{ex.get('name','?')}: {len(tasks)} tasks")

print(f"\nTotal tasks: {len(all_tasks)}")

# Save tasks
with open(f"{OUTDIR}/all_tasks.json", 'w') as f:
    json.dump(all_tasks, f, ensure_ascii=False, indent=2)

# Step 4: Get stories for both projects
print("\n=== Fetching stories ===")
all_stories = []
for pid, pname in [(fms_id, "FMS"), (gas_id, "GAS")]:
    if not pid:
        continue
    stories = fetch_all_pages(f"projects/{pid}/stories", "browseType=all&recPerPage=100")
    for s in stories:
        s['_project'] = pname
        s['_pid'] = pid
    all_stories.extend(stories)
    print(f"  {pname}: {len(stories)} stories")

with open(f"{OUTDIR}/all_stories.json", 'w') as f:
    json.dump(all_stories, f, ensure_ascii=False, indent=2)

# Step 5: Get users
print("\n=== Fetching users ===")
users = fetch_all_pages("users", "recPerPage=100")
with open(f"{OUTDIR}/users.json", 'w') as f:
    json.dump(users, f, ensure_ascii=False, indent=2)
print(f"Users: {len(users)}")

# Summary
print(f"\n{'='*50}")
print(f"DONE. Data saved to {OUTDIR}/")
print(f"  Projects: FMS={fms_id}, GAS={gas_id}")
print(f"  Executions: {len(all_executions)}")
print(f"  Tasks: {len(all_tasks)}")
print(f"  Stories: {len(all_stories)}")
print(f"  Users: {len(users)}")
