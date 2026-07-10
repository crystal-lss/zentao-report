#!/usr/bin/env python3
"""
禅道需求和任务规范检查脚本 - FMS + GAS 项目
"""
import json, csv, re, subprocess, sys, os
from datetime import datetime, date
from collections import defaultdict

ZENTAO_URL = "https://ztpm.gree.com:8888"
TOKEN = "0a9a31b84da0c5f1b19f13b0e183e8f8"
DATA_DIR = "/Users/crystal/WorkBuddy/禅道任务/禅道问题检查/data_cache"
CACHE_FILE = os.path.join(DATA_DIR, "zentao_fms_gas_data.json")

TARGET_PROJECT_IDS = [962, 977]  # FMS, GAS
TARGET_PRODUCT_IDS = [122, 55]

def api_get(path, params=None):
    url = f"{ZENTAO_URL}/api.php/v2{path}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k,v in params.items())
    cmd = ["curl", "-s", url, "-H", f"token: {TOKEN}"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except:
        return None

def fetch_all_data():
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            data = json.load(f)
        print(f"从缓存加载: {len(data.get('products',[]))}产品 {len(data.get('projects',[]))}项目 {len(data.get('executions',[]))}执行 {len(data.get('stories',[]))}需求 {len(data.get('tasks',[]))}任务")
        return data
    
    data = {"products": [], "projects": [], "executions": [], "stories": [], "tasks": [], "users": []}
    
    # Products (from list, then filter)
    print("拉取产品...")
    resp = api_get("/products", {"recPerPage": 200})
    if resp and resp.get("status") == "success":
        for p in resp.get("products", []):
            if p["id"] in TARGET_PRODUCT_IDS:
                data["products"].append(p)
    
    # Projects (from list, then filter)
    print("拉取项目...")
    for btype in ["all", "doing", "undone", "done"]:
        resp = api_get("/projects", {"browseType": btype, "recPerPage": 200})
        if resp and resp.get("status") == "success":
            for p in resp.get("projects", []):
                if p["id"] in TARGET_PROJECT_IDS and p["id"] not in {x["id"] for x in data["projects"]}:
                    data["projects"].append(p)
    
    # Executions
    print("拉取执行(迭代)...")
    for pid in TARGET_PROJECT_IDS:
        for btype in ["all", "undone", "done"]:
            resp = api_get(f"/projects/{pid}/executions", {"browseType": btype, "recPerPage": 200})
            if resp and resp.get("status") == "success":
                for e in resp.get("executions", []):
                    if e["id"] not in {x["id"] for x in data["executions"]}:
                        data["executions"].append(e)
    print(f"  执行: {len(data['executions'])}")
    
    # Stories from products
    print("拉取需求(stories)...")
    all_ids = set()
    story_exec_map = {}
    for pid in TARGET_PRODUCT_IDS:
        for page in range(1, 5):
            resp = api_get(f"/products/{pid}/stories", {"recPerPage": 500, "pageID": page, "browseType": "all"})
            if resp and resp.get("status") == "success":
                stories = resp.get("stories", [])
                for s in stories:
                    sid = s["id"]
                    sproj = s.get("project", 0)
                    # Convert project to int if it's a string
                    try: sproj = int(sproj)
                    except: pass
                    if sproj in TARGET_PROJECT_IDS:
                        s["_proj"] = sproj
                        if sid not in all_ids:
                            data["stories"].append(s)
                            all_ids.add(sid)
                if len(stories) < 500:
                    break
    
    # Stories from executions (cross-reference)
    print("拉取执行关联需求...")
    for e in data["executions"]:
        eid = e["id"]
        for page in range(1, 5):
            resp = api_get(f"/executions/{eid}/stories", {"recPerPage": 500, "pageID": page})
            if resp and resp.get("status") == "success":
                for s in resp.get("stories", []):
                    sid = s["id"]
                    if sid not in story_exec_map:
                        story_exec_map[sid] = eid
                    sproj = s.get("project", 0) or e.get("project", 0)
                    if sproj in TARGET_PROJECT_IDS:
                        s["_proj"] = sproj
                        if sid not in all_ids:
                            data["stories"].append(s)
                            all_ids.add(sid)
                if len(resp.get("stories",[])) < 500:
                    break
    
    data["_story_exec_map"] = story_exec_map
    print(f"  需求: {len(data['stories'])}")
    
    # Tasks
    print("拉取任务...")
    task_ids = set()
    for e in data["executions"]:
        eid = e["id"]
        for page in range(1, 10):
            resp = api_get(f"/executions/{eid}/tasks", {"recPerPage": 500, "pageID": page})
            if resp and resp.get("status") == "success":
                for t in resp.get("tasks", []):
                    tid = t["id"]
                    if tid not in task_ids:
                        t["_exec"] = eid
                        t["_proj"] = e.get("project")
                        data["tasks"].append(t)
                        task_ids.add(tid)
                if len(resp.get("tasks",[])) < 500:
                    break
    print(f"  任务: {len(data['tasks'])}")
    
    # Users
    print("拉取用户...")
    resp = api_get("/users", {"recPerPage": 500})
    if resp and resp.get("status") == "success":
        data["users"] = resp.get("users", [])
    
    # Story details (tasks list)
    print("拉取需求详情...")
    for s in data["stories"]:
        sid = s["id"]
        resp = api_get(f"/stories/{sid}")
        if resp and resp.get("status") == "success":
            detail = resp.get("data", resp)
            if "tasks" in detail:
                s["_tasks"] = detail["tasks"]
    
    # Task details
    print("拉取任务详情...")
    for t in data["tasks"]:
        tid = t["id"]
        resp = api_get(f"/tasks/{tid}")
        if resp and resp.get("status") == "success":
            detail = resp.get("data", resp)
            for key in ["desc", "mode", "story", "consumed", "left", "estimate", "deadline",
                       "realStarted", "finishedDate", "type", "status", "assignedTo", "openedBy",
                       "openedDate", "finishedBy", "finishedDate", "pri", "progress"]:
                if key in detail:
                    t[key] = detail[key]
    
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, default=str)
    print(f"数据已缓存")
    return data


def parse_date(d):
    if not d: return None
    if isinstance(d, date): return d
    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]:
        try: return datetime.strptime(str(d)[:19], fmt).date()
        except: pass
    return None

FORBIDDEN_WORDS = ["优化", "迭代", "对接"]
GENERIC_REQ_KEYWORDS = [
    "发版技术支持", "运维专项需求", "未确定板块的需求", "项目管理协同合作支持",
    "支付功能板块优化升级", "账户功能板块优化升级", "清结算功能板块优化升级",
    "认款功能板块优化升级", "发票功能板块优化升级", "FMS和钱包架构升级",
    "AI应用销售财务项目需求"
]
MEETING_KEYWORDS = ["会议", "培训", "复盘", "评审", "分享", "总结", "例会", "讨论", "沟通", "交流", "澄清"]
POOL_NUMBER_PATTERN = re.compile(r'^\d{4,6}\s')

def _idmap(items): return {i["id"]: i for i in items}


def run_checks(data):
    issues = []
    
    smap = _idmap(data["stories"])
    tmap = _idmap(data["tasks"])
    emap = _idmap(data["executions"])
    pmap = _idmap(data["projects"])
    
    story_exec = data.get("_story_exec_map", {})
    today = date.today()
    
    def pname(pid):
        if not pid: return ""
        p = pmap.get(pid, {})
        # Also fallback via exec
        return p.get("name", "")

    def ename(eid):
        if not eid: return ""
        e = emap.get(eid, {})
        return e.get("name", f"执行{eid}")

    def sname(sid):
        if not sid: return ""
        s = smap.get(sid, {})
        return f"{sid} {s.get('title','')}"

    def exec_for_task(t):
        return t.get("_exec")

    def proj_for_task(t):
        return t.get("_proj")

    def exec_for_story(sid):
        return story_exec.get(sid)

    def proj_for_story(s):
        return s.get("_proj")

    # --- 规则1: 需求标题编号前缀 ---
    print("规则1: 编号前缀...")
    for s in data["stories"]:
        title = s.get("title", "")
        if not POOL_NUMBER_PATTERN.match(title):
            eid = exec_for_story(s["id"])
            issues.append(_issue("P1","规则1","需求问题",
                pname(proj_for_story(s)), ename(eid),
                f"{s['id']} {title}", "", s, None,
                "需求标题未见需求池编号前缀"))

    # --- 规则2: 岗位任务覆盖 ---
    print("规则2: 岗位覆盖...")
    for s in data["stories"]:
        sid = s["id"]
        tasks = s.get("_tasks", [])
        if not tasks:
            tasks = [t for t in data["tasks"] if t.get("story") == sid]
        covered = set()
        for t in tasks:
            name = (t.get("name") or "").lower()
            ttype = t.get("type", "")
            if "【产品】" in name or "产品" in name[:10] or ttype in ["需求调研","需求设计","需求验收"]:
                covered.add("product")
            if "【ui】" in name or "【ux" in name or "ui" in name[:5] or "ux" in name[:5] or ttype == "UI设计":
                covered.add("ui")
            if "【后端" in name or "后端" in name[:10] or ttype == "后端开发":
                covered.add("dev")
            if "【前端" in name or "前端" in name[:10] or ttype == "前端开发":
                covered.add("dev")
            if "【架构" in name or "架构" in name[:10] or ttype in ["开发任务","技术任务"]:
                covered.add("dev")
            if "【开发" in name and "后端" not in name and "前端" not in name:
                covered.add("dev")
            if "【测试" in name or "测试" in name[:10] or ttype == "测试":
                covered.add("test")
        missing = [r for r in ["product","ui","dev","test"] if r not in covered]
        if missing:
            eid = exec_for_story(sid)
            issues.append(_issue("P0","规则2","需求问题",
                pname(proj_for_story(s)), ename(eid),
                f"{sid} {s.get('title','')}", "", s, None,
                f"缺少岗位任务：{'/'.join(missing)}"))

    # --- 规则5: 工时/截止日期/多人任务 ---
    print("规则5: 工时/截止日期...")
    for t in data["tasks"]:
        est = t.get("estimate", 0) or 0
        dl = t.get("deadline", "")
        name = t.get("name", "")
        mode = t.get("mode", "")
        story_id = t.get("story")
        dets = []
        if est <= 0: dets.append("预计工时为0或未填")
        if not dl: dets.append("截止日期未填")
        if est > 20: dets.append(f"预计工时>{est}h")
        if mode == "multi" and not any(kw in name for kw in MEETING_KEYWORDS):
            dets.append("多人任务 mode=multi，但任务名未见会议类关键词")
        if dets:
            issues.append(_issue("P1","规则5","任务问题",
                pname(proj_for_task(t)), ename(exec_for_task(t)),
                sname(story_id), name, None, t,
                "；".join(dets)))

    # --- 规则6: 预计工时过大 ---
    print("规则6: 工时过大...")
    for t in data["tasks"]:
        est = t.get("estimate", 0) or 0
        if est > 24:
            issues.append(_issue("P0","规则6","任务问题",
                pname(proj_for_task(t)), ename(exec_for_task(t)),
                sname(t.get("story")), t.get("name",""), None, t,
                f"预计工时>{est}h"))

    # --- 规则9/11: 禁用词 ---
    print("规则9/11: 禁用词...")
    for s in data["stories"]:
        title = s.get("title","")
        for w in FORBIDDEN_WORDS:
            if w in title:
                eid = exec_for_story(s["id"])
                issues.append(_issue("P1","规则11","需求问题",
                    pname(proj_for_story(s)), ename(eid),
                    f"{s['id']} {title}", "", s, None,
                    f"需求标题包含禁用词：{w}"))
    for t in data["tasks"]:
        name = t.get("name","")
        for w in FORBIDDEN_WORDS:
            if w in name:
                issues.append(_issue("P1","规则11","任务问题",
                    pname(proj_for_task(t)), ename(exec_for_task(t)),
                    sname(t.get("story")), name, None, t,
                    f"任务名称包含禁用词：{w}"))

    # --- 规则15/19: 截止日期 ---
    print("规则15/19: 截止日期...")
    for t in data["tasks"]:
        dl_str = t.get("deadline","")
        status = t.get("status","")
        fd = parse_date(t.get("finishedDate"))
        dd = parse_date(dl_str)
        if not dd: continue
        if status not in ("done","closed","finished"):
            if dd < today:
                issues.append(_issue("P0","规则15/19","任务问题",
                    pname(proj_for_task(t)), ename(exec_for_task(t)),
                    sname(t.get("story")), t.get("name",""), None, t,
                    f"任务未完成且已过截止日：{dl_str}"))
        else:
            if fd and fd > dd:
                issues.append(_issue("P0","规则15/19","任务问题",
                    pname(proj_for_task(t)), ename(exec_for_task(t)),
                    sname(t.get("story")), t.get("name",""), None, t,
                    f"任务完成日晚于截止日：{fd} > {dl_str}"))

    # --- 规则17: 同名任务 ---
    print("规则17: 同名任务...")
    ename_grp = defaultdict(list)
    for t in data["tasks"]:
        eid = exec_for_task(t)
        name = (t.get("name","")).strip()
        ename_grp[(eid, name)].append(t)
    for (eid, name), tlist in ename_grp.items():
        if len(tlist) > 1:
            for t in tlist:
                issues.append(_issue("P1","规则17","任务问题",
                    pname(proj_for_task(t)), ename(eid),
                    sname(t.get("story")), name, None, t,
                    f"同迭代任务名称重复，共{len(tlist)}条"))

    # --- 规则4: 任务关联需求 ---
    print("规则4: 任务关联需求...")
    for t in data["tasks"]:
        sid = t.get("story", 0)
        if not sid or sid == 0:
            issues.append(_issue("P0","规则4","任务问题",
                pname(proj_for_task(t)), ename(exec_for_task(t)),
                "", t.get("name",""), None, t,
                "任务未关联需求"))

    # --- 规则10: 通用需求任务描述为空 ---
    print("规则10: 通用需求描述...")
    for s in data["stories"]:
        title = s.get("title","")
        if not any(kw in title for kw in GENERIC_REQ_KEYWORDS):
            continue
        tasks = s.get("_tasks", [])
        if not tasks:
            tasks = [t for t in data["tasks"] if t.get("story") == s["id"]]
        for t in tasks:
            desc = str(t.get("desc","")).strip()
            if not desc or desc in ("<p></p>","&nbsp;","<br>","None",""):
                issues.append(_issue("P1","规则10","任务问题",
                    pname(proj_for_story(s)), ename(exec_for_story(s["id"])),
                    f"{s['id']} {title}", t.get("name",""), None, t,
                    "通用业务功能需求下任务描述为空"))

    # 排序
    def sortkey(i):
        pri = 0 if i["优先级"]=="P0" else 1
        cat = 0 if "需求" in i["问题分类"] else 1
        nums = [int(n) for n in re.findall(r'\d+', i["不符合规则"])]
        rn = nums[0] if nums else 99
        return (pri, cat, rn)
    issues.sort(key=sortkey)
    
    return issues


def _issue(pri, rule, cat, proj, exec_name, req, tname, story, task, detail):
    """构建一条问题记录"""
    out = {
        "优先级": pri, "不符合规则": rule, "问题分类": cat,
        "所属项目": proj or "", "所属执行": exec_name or "",
        "相关研发需求": req or "", "任务名称": tname or "",
        "任务描述": (str(task.get("desc",""))[:200] if task else ""),
        "任务类型": (task.get("type","") if task else ""),
        "截止日期": str(task.get("deadline","")) if task else "",
        "任务状态": (task.get("status","") if task else ""),
        "最初预计": str(task.get("estimate","")) if task else "",
        "总计消耗": str(task.get("consumed","")) if task else "",
        "预计剩余": str(task.get("left","")) if task else "",
        "进度": str(task.get("progress","")) if task else "",
        "由谁创建": (task.get("openedBy","") if task else (story.get("openedBy","") if story else "")),
        "创建日期": str(task.get("openedDate","")) if task else (str(story.get("openedDate","")) if story else ""),
        "由谁完成": (task.get("finishedBy","") if task else ""),
        "实际完成": str(task.get("finishedDate","")) if task else "",
        "问题详情": detail
    }
    return out


def main():
    print("=" * 60)
    print("禅道需求任务规范检查 (FMS + GAS)")
    print("=" * 60)
    
    data = fetch_all_data()
    issues = run_checks(data)
    
    output_csv = "/Users/crystal/WorkBuddy/禅道任务/禅道问题检查/禅道不符合项整改报告_2026-06-08.csv"
    fields = ["优先级","不符合规则","问题分类","所属项目","所属执行",
              "相关研发需求","任务名称","任务描述","任务类型","截止日期",
              "任务状态","最初预计","总计消耗","预计剩余","进度",
              "由谁创建","创建日期","由谁完成","实际完成","问题详情"]
    
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in issues:
            w.writerow(i)
    
    p0 = sum(1 for i in issues if i["优先级"]=="P0")
    p1 = sum(1 for i in issues if i["优先级"]=="P1")
    s_iss = sum(1 for i in issues if "需求" in i["问题分类"])
    t_iss = sum(1 for i in issues if "任务" in i["问题分类"])
    
    print(f"\n共 {len(issues)} 条: P0={p0}, P1={p1}, 需求={s_iss}, 任务={t_iss}")
    print(f"报告: {output_csv}")


if __name__ == "__main__":
    main()
