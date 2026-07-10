import subprocess, re, base64, hashlib

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

def fetch_and_analyze(params_encoded, label):
    url = f"{BASE}/pivot-preview-1-16441-worksummary.html?params={params_encoded}"
    cmd = ['curl', '-s', '-b', COOKIE_FILE, url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    content_hash = hashlib.md5(result.stdout.encode()).hexdigest()[:8]
    
    table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', result.stdout, re.DOTALL)
    tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_match.group(0), re.DOTALL) if table_match else None
    trs = re.findall(r'<tr[^>]*>', tbody_match.group(1)) if tbody_match else []
    
    # 提取所有完成者
    users = set()
    if tbody_match:
        for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_match.group(1), re.DOTALL):
            user_td = re.search(r'class="[^"]*w-user[^"]*"[^>]*rowspan="\d+"[^>]*>([^<]*)</td>', tr)
            if user_td:
                name = user_td.group(1).strip()
                if name and not name.replace('.', '').isdigit():
                    users.add(name)
    
    rec_match = re.search(r'recTotal[:\s]*(\d+)', result.stdout)
    rec_total = rec_match.group(1) if rec_match else '?'
    
    print(f"{label}: hash={content_hash}, total={rec_total}, trs={len(trs)}, users={len(users)} -> {sorted(users)}")
    return content_hash, users

# 完整参数版本 - 包含所有必要参数
for page in [1, 2, 3, 10, 34]:
    params = f'begin=20260501&end=&dept=0&recTotal=677&recPerPage=20&pageID={page}'
    encoded = base64.b64encode(params.encode()).decode()
    h, users = fetch_and_analyze(encoded, f"page={page}")

# 尝试不限制时间
params = f'begin=20260101&end=20260630&dept=0&recTotal=677&recPerPage=1000&pageID=1'
encoded = base64.b64encode(params.encode()).decode()
h, users = fetch_and_analyze(encoded, "rpp=1000")
