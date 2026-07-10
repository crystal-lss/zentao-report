import subprocess, re, csv, json, base64

BASE = "https://ztpm.gree.com:8888"
COOKIE_FILE = '/tmp/zentao_cookies.txt'

dept_configs = [
    ('开发七室', 124),
    ('软件测试室', 129),
    ('视觉设计室', 31),
]

# 构建参数：begin=20260601&end=20260630&dept={dept_id}
# URL模式: /pivot-preview-1-16441-worksummary.html?params={base64_encoded}
# $.createLink 生成的URL可能是: /index.php?m=pivot&f=preview&dimension=1&group=16441&method=worksummary&params={base64}

all_dept_data = {}

for dept_name, dept_id in dept_configs:
    param_str = f'begin=20260601&end=20260630&dept={dept_id}'
    encoded = base64.b64encode(param_str.encode()).decode()
    
    urls_to_try = [
        f'{BASE}/pivot-preview-1-16441-worksummary.html?params={encoded}',
        f'{BASE}/index.php?m=pivot&f=preview&dimension=1&group=16441&method=worksummary&params={encoded}',
        f'{BASE}/index.php?m=pivot&f=preview&dimensionID=1&groupID=16441&method=worksummary&params={encoded}',
    ]
    
    for url in urls_to_try:
        cmd = ['curl', '-s', '-b', COOKIE_FILE, '-L', url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # 查找表格
        table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', result.stdout, re.DOTALL)
        if table_match:
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_match.group(0), re.DOTALL)
            rows = re.findall(r'<tr[^>]*>', tbody_match.group(1), re.DOTALL) if tbody_match else []
            
            # 查找分页信息
            rec_match = re.search(r'recTotal[:\s]*(\d+)', result.stdout)
            page_match = re.search(r"text: '([^']*页[^']*)'", result.stdout)
            rec_total = rec_match.group(1) if rec_match else '?'
            
            print(f"{dept_name} dept={dept_id}: {len(rows)} rows, recTotal={rec_total}, page_len={len(result.stdout)}")
            
            if len(rows) > 0:
                # 解析数据行
                tbody_html = tbody_match.group(1)
                trs = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_html, re.DOTALL)
                
                parsed_rows = []
                for tr in trs:
                    cells = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
                    clean = []
                    for cell in cells:
                        text = re.sub(r'<[^>]+>', ' ', cell)
                        text = re.sub(r'\s+', ' ', text).strip()
                        clean.append(text)
                    if clean:
                        parsed_rows.append(clean)
                
                all_dept_data[dept_name] = {
                    'rows': parsed_rows,
                    'recTotal': rec_total,
                    'page_len': len(result.stdout),
                    'success_url': url
                }
                break  # 找到一个有效的URL就跳出
        else:
            pass  # 这个URL没返回表格

# 汇总
print("\n=== Summary ===")
for dept_name, data in all_dept_data.items():
    print(f"{dept_name}: {len(data['rows'])} parsed rows, recTotal={data['recTotal']}")

# 如果有数据，保存
if all_dept_data:
    with open('/Users/crystal/WorkBuddy/禅道任务/dept_data.json', 'w') as f:
        json.dump(all_dept_data, f, ensure_ascii=False, indent=2)
    print("Saved to dept_data.json")
