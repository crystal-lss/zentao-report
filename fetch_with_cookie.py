import subprocess, json

BASE = "https://ztpm.gree.com:8888"

# Step 1: 用密码登录, 获取session cookie
login_cmd = [
    'curl', '-s', '-c', '/tmp/zentao_cookies.txt',
    '-X', 'POST',
    f'{BASE}/api.php/v2/users/login',
    '-H', 'Content-Type: application/json',
    '-d', '{"account":"260298","password":"Lss@530720"}'
]
result = subprocess.run(login_cmd, capture_output=True, text=True)
print("Login response:", result.stdout[:200])

# Step 2: 用cookie获取透视表页面, 可能页面里有嵌入数据
fetch_cmd = [
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/pivot-preview-1-16441-worksummary.html'
]
result = subprocess.run(fetch_cmd, capture_output=True, text=True)
print("\nPage length:", len(result.stdout))
print("First 1000 chars:", result.stdout[:1000])

# Step 3: 尝试AJAX数据接口 (带cookie)
ajax_paths = [
    '/pivot-ajaxGetData-16441.json',
    '/index.php?m=pivot&f=ajaxGetData&pivotID=16441',
    '/pivot-ajaxGetPivot-16441.json',
]
for path in ajax_paths:
    cmd = ['curl', '-s', '-b', '/tmp/zentao_cookies.txt', f'{BASE}{path}']
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"\n=== {path} ===")
    print(result.stdout[:500])
