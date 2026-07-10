import subprocess, re

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

cmd = ['curl', '-s', '-b', COOKIE_FILE, f'{BASE}/pivot-preview-1-16441-worksummary.html']
result = subprocess.run(cmd, capture_output=True, text=True)
html = result.stdout

# 找到loadProductSummary和changeParams函数
for func in ['loadProductSummary', 'function changeParams', 'loadPage', 'loadWorksummary', 'worksummary']:
    idx = html.find(func)
    if idx >= 0:
        print(f"=== {func} ===")
        print(html[max(0,idx-20):idx+800])
        print()

# 找所有script内容
scripts = re.findall(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
for i, s in enumerate(scripts):
    if len(s) > 100 and ('changeParams' in s or 'loadPage' in s or 'worksummary' in s):
        print(f"\n=== Script {i} (len={len(s)}) ===")
        print(s[:3000])
