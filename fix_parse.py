import re, json

with open('/Users/crystal/WorkBuddy/禅道任务/pivot_page.html') as f:
    html = f.read()

# 提取表格
table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', html, re.DOTALL)
table_html = table_match.group(0)

# 提取所有tr
trs = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
print(f"Total tr elements: {len(trs)}")

# 第一个tr是表头
for i, tr in enumerate(trs[:5]):
    tds = re.findall(r'<td[^>]*>(.*?)</td>', tr, re.DOTALL)
    if tds:
        # 清理
        clean = []
        for td in tds:
            text = re.sub(r'<[^>]+>', ' ', td)
            text = re.sub(r'\s+', ' ', text).strip()
            clean.append(text)
        print(f"Row {i}: {len(clean)} cells -> {clean[:5]}...")

# 正确提取完成者 - 只取第一列有w-user的
users_in_table = set()
# 解析带rowspan的完成者
for tr in trs:
    # 匹配第一列是完成者(w-user)的td
    user_td = re.search(r'<td[^>]*class="[^"]*w-user[^"]*"[^>]*rowspan="(\d+)"[^>]*>([^<]*)</td>', tr)
    if user_td:
        name = user_td.group(2).strip()
        count = user_td.group(1)
        if name and not name.replace('.', '').isdigit():
            users_in_table.add(name)
            # 不打印count因为这会让输出太长

# 也检查header确认第一列是"完成者"  
headers = re.findall(r'<th[^>]*>([^<]*)</th>', trs[0])
print(f"\nHeaders: {headers}")
print(f"\nUsers in table (non-numeric): {sorted(users_in_table)}")
print(f"Count: {len(users_in_table)}")
