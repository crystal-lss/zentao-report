import subprocess, base64

COOKIE_FILE = '/tmp/zentao_cookies.txt'
BASE = "https://ztpm.gree.com:8888"

# 尝试直接导出URL
export_urls = [
    f"{BASE}/pivot-export-16441-1-worksummary.xlsx",
    f"{BASE}/pivot-export-1-16441-worksummary.xlsx",
    f"{BASE}/pivot-export-16441.xlsx",
    f"{BASE}/pivot-export-16441-1.xlsx",
    f"{BASE}/pivot-ajaxExport-16441-1.json",
]

dept_id = 124
param_str = f'begin=20260601&end=20260630&dept={dept_id}'
encoded = base64.b64encode(param_str.encode()).decode()

for url in export_urls:
    cmd = ['curl', '-s', '-b', COOKIE_FILE, '-o', '/tmp/test_export.xlsx', '-w', '%{http_code} %{size_download}', url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"{url.split('/')[-1]}: HTTP {result.stdout.strip()}")

# 也尝试带params
for url in export_urls:
    full_url = f"{url}?params={encoded}"
    cmd = ['curl', '-s', '-b', COOKIE_FILE, '-o', '/tmp/test_export.xlsx', '-w', '%{http_code} %{size_download}', full_url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(f"{url.split('/')[-1]}?params=...: HTTP {result.stdout.strip()}")
