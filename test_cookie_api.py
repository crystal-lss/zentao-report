import subprocess, json

COOKIE_FILE = '/tmp/zentao_cookies.txt'
BASE = "https://ztpm.gree.com:8888"

# 用cookie方式调用API
def api_get(path):
    cmd = ['curl', '-s', '-b', COOKIE_FILE, f'{BASE}/api.php/v2{path}']
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return json.loads(result.stdout)
    except:
        return result.stdout[:300]

# 测试
print("=== User list (cookie) ===")
r = api_get('/users?recPerPage=1000')
if isinstance(r, dict):
    print(f"Status: {r.get('status')}, Users count: {len(r.get('users', []))}")
    if r.get('users'):
        # 只显示带部门信息的用户
        for u in r['users'][:5]:
            print(f"  {u.get('account')}: {u.get('realname')} (dept={u.get('dept')})")

print("\n=== User 180152 (cookie) ===")
r = api_get('/users/180152')
print(json.dumps(r, indent=2, ensure_ascii=False)[:500])

print("\n=== User A80514 (cookie) ===")  
r = api_get('/users/A80514')
print(json.dumps(r, indent=2, ensure_ascii=False)[:500])
