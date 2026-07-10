import subprocess, re, base64, time, hashlib

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

# 测试不同dept参数
test_params = [
    # (dept_id, begin, end)
    (124, '20260601', '20260630'),  # 开发七室 6月
    (129, '20260601', '20260630'),  # 软件测试室 6月
    (31, '20260601', '20260630'),   # 视觉设计室 6月
    (0, '20260501', '20260630'),    # 全部 5-6月
]

for dept_id, begin, end in test_params:
    param_str = f'begin={begin}&end={end}&dept={dept_id}'
    encoded = base64.b64encode(param_str.encode()).decode()
    
    # 加上时间戳防止缓存
    ts = int(time.time() * 1000)
    
    url = f'{BASE}/pivot-preview-1-16441-worksummary.html?params={encoded}&_t={ts}'
    cmd = ['curl', '-s', '-b', COOKIE_FILE, url,
           '-H', 'Cache-Control: no-cache',
           '-H', 'Pragma: no-cache']
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # 检查页面内容哈希
    content_hash = hashlib.md5(result.stdout.encode()).hexdigest()[:8]
    
    # 查找分页信息
    rec_match = re.search(r'recTotal[:\s]*(\d+)', result.stdout)
    rec_total = rec_match.group(1) if rec_match else '?'
    
    # 找表格
    table_match = re.search(r'<tbody>(.*?)</tbody>', result.stdout, re.DOTALL)
    tr_count = len(re.findall(r'<tr[^>]*>', table_match.group(1))) if table_match else 0
    
    # 查找第一个完成者
    first_user_match = re.search(r'rowspan="(\d+)">([^<]+)</td>', result.stdout)
    first_user = f"{first_user_match.group(2).strip()}({first_user_match.group(1)})" if first_user_match else 'N/A'
    
    print(f"dept={dept_id}, begin={begin}, end={end}: hash={content_hash}, recTotal={rec_total}, trs={tr_count}, first={first_user}")
