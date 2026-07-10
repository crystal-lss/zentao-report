import subprocess, re, base64, hashlib

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

def fetch_and_analyze(url, label):
    cmd = ['curl', '-s', '-b', COOKIE_FILE, url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    content_hash = hashlib.md5(result.stdout.encode()).hexdigest()[:8]
    
    # 检查table
    table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', result.stdout, re.DOTALL)
    tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_match.group(0), re.DOTALL) if table_match else None
    trs = re.findall(r'<tr[^>]*>', tbody_match.group(1)) if tbody_match else []
    
    # 找recTotal
    rec_match = re.search(r'recTotal[:\s]*(\d+)', result.stdout)
    rec_total = rec_match.group(1) if rec_match else '?'
    
    # 找第一个完成者
    first = re.search(r'class="[^"]*w-user[^"]*"[^>]*>([^<]+)</td>', result.stdout)
    first_user = first.group(1).strip() if first else 'N/A'
    
    print(f"{label}: hash={content_hash}, recTotal={rec_total}, trs={len(trs)}, first={first_user}")
    return content_hash

# 测试不同的URL格式
dept_id = 124
param_str = f'begin=20260601&end=20260630&dept={dept_id}'
encoded = base64.b64encode(param_str.encode()).decode()

urls = [
    (f"{BASE}/pivot-preview-1-16441-worksummary.html", "base (no params)"),
    (f"{BASE}/pivot-preview-1-16441-worksummary.html?params={encoded}", "with params"),
    (f"{BASE}/pivot-preview-1-16441-worksummary.html?dimension=1&group=16441&method=worksummary&params={encoded}", "full query string"),
    (f"{BASE}/index.php?m=pivot&f=preview&dimension=1&group=16441&method=worksummary&params={encoded}", "index.php format"),
]

hashes = set()
for url, label in urls:
    h = fetch_and_analyze(url, label)
    hashes.add(h)

print(f"\nUnique hashes: {len(hashes)} (should be >1 if params work)")
