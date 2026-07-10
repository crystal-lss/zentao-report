import subprocess, re

BASE = "https://ztpm.gree.com:8888"

fetch_cmd = [
    'curl', '-s', '-b', '/tmp/zentao_cookies.txt',
    f'{BASE}/pivot-preview-1-16441-worksummary.html'
]
result = subprocess.run(fetch_cmd, capture_output=True, text=True)
html = result.stdout

# 提取整个表格
table_match = re.search(r'<table[^>]*id="worksummary"[^>]*>(.*?)</table>', html, re.DOTALL)
if table_match:
    table_html = table_match.group(0)
    print(f"Table length: {len(table_html)}")
    print(table_html[:3000])
    print("\n...MIDDLE...")
    print(table_html[len(table_html)//2-500:len(table_html)//2+500])
    print("\n...END...")
    print(table_html[-2000:])
else:
    print("Table not found - checking what's after the thead...")
    # Find the table start
    idx = html.find('<table class')
    if idx >= 0:
        print(html[idx:idx+5000])
    else:
        # Maybe data is loaded via AJAX - look for any embedded JSON
        print("Looking for embedded data...")
        # Save full page for analysis
        with open('/Users/crystal/WorkBuddy/禅道任务/page_full.html', 'w') as f:
            f.write(html)
        print("Saved full page to page_full.html")
