import subprocess, re, json, csv

BASE = "https://ztpm.gree.com:8888"

fetch_cmd = [
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/pivot-preview-1-16441-worksummary.html'
]
result = subprocess.run(fetch_cmd, capture_output=True, text=True)
html = result.stdout

# 保存完整页面
with open('/Users/crystal/WorkBuddy/禅道任务/pivot_page.html', 'w') as f:
    f.write(html)

# 搜索筛选条件 - 部门相关
dept_patterns = [
    r'开发七室', r'软件测试室', r'视觉设计室',
    r'营销数智化中心', r'技术部',
    r'dept', r'部门',
]
for pat in dept_patterns:
    matches = re.findall(pat, html, re.IGNORECASE)
    if matches:
        print(f"Found '{pat}': {len(matches)} occurrences")
        # Show context around first match
        idx = html.lower().find(pat.lower())
        if idx >= 0:
            print(f"  Context: ...{html[max(0,idx-50):idx+len(pat)+100]}...")

print("\n=== Extracting table data ===")

# Parse table
table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', html, re.DOTALL)
table_html = table_match.group(0)

# Extract header
headers = re.findall(r'<th[^>]*>([^<]*)</th>', table_html)
print("Headers:", headers)

# Extract rows
tbody_match = re.search(r'<tbody>(.*?)</tbody>', table_html, re.DOTALL)
tbody = tbody_match.group(1)

# Parse each tr
rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody, re.DOTALL)
print(f"Total rows: {len(rows)}")

# Extract cell data from each row
all_data = []
for row in rows:
    cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    # Clean HTML from cells
    clean_cells = []
    for cell in cells:
        # Remove HTML tags but keep text
        text = re.sub(r'<[^>]+>', ' ', cell)
        text = re.sub(r'\s+', ' ', text).strip()
        clean_cells.append(text)
    all_data.append(clean_cells)

print(f"Sample row: {all_data[0] if all_data else 'none'}")
print(f"Sample row 100: {all_data[100] if len(all_data) > 100 else 'none'}")

# Save CSV
with open('/Users/crystal/WorkBuddy/禅道任务/pivot_raw.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    for row in all_data:
        writer.writerow(row)
print(f"\nSaved {len(all_data)} rows to pivot_raw.csv")
