import subprocess, re, json, base64, time

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

def fetch_pivot_page(params_encoded, label):
    ts = int(time.time() * 1000)
    url = f'{BASE}/pivot-preview-1-16441-worksummary.html?params={params_encoded}&_t={ts}'
    cmd = ['curl', '-s', '-b', COOKIE_FILE, url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 找分页信息
    rec_match = re.search(r'recTotal[:\s]*(\d+)', result.stdout)
    pp_match = re.search(r'recPerPage[:\s]*(\d+)', result.stdout)
    page_match = re.search(r"page[:\s]*(\d+)", result.stdout)
    
    rec_total = rec_match.group(1) if rec_match else '?'
    rec_per_page = pp_match.group(1) if pp_match else '?'
    page = page_match.group(1) if page_match else '?'
    
    # 提取用户
    table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', result.stdout, re.DOTALL)
    users = set()
    if table_match:
        trs = re.findall(r'<tr[^>]*>(.*?)</tr>', table_match.group(0), re.DOTALL)
        for tr in trs:
            user_td = re.search(r'<td[^>]*class="[^"]*w-user[^"]*"[^>]*rowspan="\d+"[^>]*>([^<]*)</td>', tr)
            if user_td:
                name = user_td.group(1).strip()
                if name and not name.replace('.', '').isdigit():
                    users.add(name)
    
    print(f"{label}: total={rec_total}, perPage={rec_per_page}, page={page}, users={len(users)} -> {sorted(users)}")
    return users

# 测试1: 尝试不同的recPerPage
print("=== Testing recPerPage ===")
for rpp in [20, 50, 100, 500, 1000]:
    params = base64.b64encode(f'begin=20260501&end=&dept=0&recTotal=677&recPerPage={rpp}&pageID=1'.encode()).decode()
    fetch_pivot_page(params, f"rpp={rpp}")

# 测试2: 尝试不同页
print("\n=== Testing pages ===")
for p in [1, 2, 3, 34]:
    params = base64.b64encode(f'begin=20260501&end=&dept=0&recTotal=677&recPerPage=20&pageID={p}'.encode()).decode()
    fetch_pivot_page(params, f"page={p}")
