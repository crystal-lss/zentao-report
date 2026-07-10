import subprocess, json

TOKEN = "0fa661149dcc428d6737e292785c9e39"
BASE = "https://ztpm.gree.com:8888"

paths = [
    "/pivot-ajaxGetData-16441.json",
    "/pivot-ajaxGetPivot-16441.json",
    "/report-ajaxGetData-16441.json",
    "/api.php/v2/report/pivot-16441",
    "/pivot-ajaxGetGroup-16441.json",
]

for path in paths:
    cmd = f'curl -s "{BASE}{path}" -H "token: {TOKEN}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(f"\n=== {path} ===")
    print(result.stdout[:500])
