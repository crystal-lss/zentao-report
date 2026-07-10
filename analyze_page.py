import subprocess, json, re

BASE = "https://ztpm.gree.com:8888"

# 获取完整页面内容
fetch_cmd = [
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/pivot-preview-1-16441-worksummary.html'
]
result = subprocess.run(fetch_cmd, capture_output=True, text=True)
html = result.stdout

# 搜索可能嵌入数据的script标签
scripts = re.findall(r'<script[^>]*>([^<]+)</script>', html, re.DOTALL)
print(f"Found {len(scripts)} script blocks")

# 搜索JSON数据
for i, s in enumerate(scripts):
    if 'data' in s.lower() or 'pivot' in s.lower() or 'rows' in s.lower() or 'cols' in s.lower():
        print(f"\n=== Script block {i} (len={len(s)}) ===")
        print(s[:1000])

# 搜索表格数据
if '<table' in html:
    print("\n=== Found tables ===")
    tables = re.findall(r'<table[^>]*>.*?</table>', html, re.DOTALL)
    print(f"Table count: {len(tables)}")
    for i, t in enumerate(tables[:2]):
        print(f"\nTable {i}: {t[:500]}")

# 查找可能的数据容器
for pattern in ['data-rows', 'pivotData', 'pivot-data', 'zin.pivot', 'groupData']:
    matches = re.findall(f'{pattern}[^;]*', html)
    if matches:
        print(f"\n=== {pattern} ===")
        for m in matches[:3]:
            print(m[:300])
