import subprocess, re

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

# 获取包含JavaScript的完整页面
cmd = ['curl', '-s', '-b', COOKIE_FILE, f'{BASE}/pivot-preview-1-16441-worksummary.html']
result = subprocess.run(cmd, capture_output=True, text=True)
html = result.stdout

# 找changeParams函数
idx = html.find('changeParams')
if idx >= 0:
    print("=== changeParams function ===")
    print(html[idx:idx+2000])

# 找ajaxGetData
idx = html.find('ajaxGetData')
if idx >= 0:
    print("\n=== ajaxGetData references ===")
    print(html[max(0,idx-200):idx+500])

# 找loadTable 或 renderTable
for func_name in ['loadTable', 'renderTable', 'loadPage', '$.get', 'fetch(', 'axios']:
    idx = html.find(func_name)
    if idx >= 0:
        context = html[max(0,idx-100):idx+300]
        # Only show if it looks like data loading
        if 'pivot' in context.lower() or 'table' in context.lower() or 'url' in context.lower():
            print(f"\n=== {func_name} ===")
            print(context)

# 直接尝试AJAX数据接口
ajax_urls = [
    f'{BASE}/pivot-ajaxGetData-16441-1.json',
    f'{BASE}/pivot-ajaxGetData-16441.json?dimension=1&dept=124&begin=2026-06-01&end=2026-06-30',
    f'{BASE}/index.php?m=pivot&f=ajaxGetData&groupID=16441&dimensionID=1',
]
for url in ajax_urls:
    cmd = ['curl', '-s', '-b', COOKIE_FILE, url,
           '-H', 'X-Requested-With: XMLHttpRequest',
           '-H', 'Accept: application/json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"\n=== {url.split('?')[-1] if '?' in url else url.split('/')[-1]} ===")
    if result.stdout.strip():
        print(result.stdout[:500])
    else:
        print("(empty)")
