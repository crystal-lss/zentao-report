import subprocess, re, csv, json

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

# 先查看页面中透视表的默认参数
with open('/Users/crystal/WorkBuddy/禅道任务/pivot_page.html') as f:
    html = f.read()

# 搜索pivot ID和参数
for pat in ['pivotID', 'pivot-id', 'groupID', '16441', 'changeParams']:
    idxs = [m.start() for m in re.finditer(pat, html)]
    print(f"'{pat}': {len(idxs)} matches")
    for idx in idxs[:2]:
        print(f"  ...{html[max(0,idx-50):idx+len(pat)+100]}...")

# 尝试带dept参数获取
dept_ids = {
    '开发七室': 124,
    '软件测试室': 129,
    '视觉设计室': 31
}

for dept_name, dept_id in dept_ids.items():
    urls_to_try = [
        f'{BASE}/pivot-preview-1-16441-worksummary.html?dept={dept_id}',
        f'{BASE}/pivot-preview-1-16441-worksummary-{dept_id}.html',
    ]
    for url in urls_to_try:
        cmd = ['curl', '-s', '-b', COOKIE_FILE, url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', result.stdout, re.DOTALL)
        if table_match:
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_match.group(0), re.DOTALL)
            row_count = len(re.findall(r'<tr[^>]*>', tbody_match.group(1), re.DOTALL)) if tbody_match else 0
            print(f"\n{dept_name} ({url.split('?')[-1] if '?' in url else url}): {row_count} rows, page_len={len(result.stdout)}")
        else:
            print(f"\n{dept_name} ({url.split('?')[-1] if '?' in url else url}): NO TABLE, len={len(result.stdout)}")
