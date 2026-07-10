import subprocess, json

TOKEN = "0fa661149dcc428d6737e292785c9e39"
BASE = "https://ztpm.gree.com:8888"

# 尝试查看透视表HTML页面
print("=== Pivot HTML Page ===")
cmd = f'curl -s "{BASE}/pivot-preview-1-16441-worksummary.html" -H "token: {TOKEN}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout[:2000])

# 尝试获取单个用户
print("\n=== User 180152 ===")
cmd = f'curl -s "{BASE}/api.php/v2/users/180152" -H "token: {TOKEN}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout[:500])

print("\n=== User A80514 ===")
cmd = f'curl -s "{BASE}/api.php/v2/users/A80514" -H "token: {TOKEN}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout[:500])

# 尝试获取部门列表
print("\n=== Depts ===")
cmd = f'curl -s "{BASE}/api.php/v2/depts" -H "token: {TOKEN}"'
result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print(result.stdout[:500])
