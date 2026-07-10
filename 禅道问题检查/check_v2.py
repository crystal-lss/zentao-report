#!/usr/bin/env python3
"""
禅道需求任务规范检查 - FMS + GAS (从缓存数据筛选)
"""
import json, csv, re, os
from datetime import datetime, date
from collections import defaultdict

DATA_DIR = "/Users/crystal/WorkBuddy/禅道任务/禅道问题检查/data_cache"
CACHE_FILE = os.path.join(DATA_DIR, "zentao_full_data.json")
TARGET_PROJECT_IDS = {962, 977}
TARGET_PROJECT_NAMES = {"销售财务中台管理系统", "海外售后GAS项目"}

FORBIDDEN_WORDS = ["优化", "迭代", "对接"]
GENERIC_KW = [
    "发版技术支持", "运维专项需求", "未确定板块的需求", "项目管理协同合作支持",
    "支付功能板块优化升级", "账户功能板块优化升级", "清结算功能板块优化升级",
    "认款功能板块优化升级", "发票功能板块优化升级", "FMS和钱包架构升级",
    "AI应用销售财务项目需求"
]
MEETING_KW = ["会议", "培训", "复盘", "评审", "分享", "总结", "例会", "讨论", "沟通", "交流", "澄清"]
POOL_RE = re.compile(r'^\d{4,6}\s')

def parse_date(d):
    if not d: return None
    if isinstance(d, date): return d
    for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d"]:
        try: return datetime.strptime(str(d)[:19], fmt).date()
        except: pass
    return None

def _idmap(items): return {i["id"]: i for i in items}


def main():
    # Load cached data
    print("加载缓存数据...")
    with open(CACHE_FILE) as f:
        raw = json.load(f)
    
    # Filter data to FMS(962) + GAS(977)
    target_exec_ids = {e["id"] for e in raw["executions"] if e.get("project") in TARGET_PROJECT_IDS}
    
    # Get project name map
    proj_name = {}
    for p in raw["projects"]:
        proj_name[p["id"]] = p.get("name", "")
    
    # Filter executions
    executions = [e for e in raw["executions"] if e["id"] in target_exec_ids]
    exec_map = {e["id"]: e for e in executions}
    
    # Filter tasks: those in target executions
    tasks = [t for t in raw["tasks"] if t.get("execution") in target_exec_ids]
    task_map = {t["id"]: t for t in tasks}
    print(f"任务: {len(tasks)} (共 {len(raw['tasks'])} 条)")
    
    # Filter stories: those with project in target, OR linked from target tasks
    target_story_ids = set()
    for t in tasks:
        sid = t.get("story", 0)
        if sid:
            target_story_ids.add(sid)
    # Also add stories whose project is in target
    for s in raw["stories"]:
        sproj = s.get("project", 0)
        if isinstance(sproj, str):
            try: sproj = int(sproj)
            except: sproj = 0
        if sproj in TARGET_PROJECT_IDS:
            target_story_ids.add(s["id"])
    
    stories = [s for s in raw["stories"] if s["id"] in target_story_ids]
    story_map = {s["id"]: s for s in stories}
    print(f"需求: {len(stories)}")
    
    # Get story details (need API for tasks list per story)
    # Use a script to batch-fetch story details
    story_details_file = os.path.join(DATA_DIR, "story_details.json")
    if os.path.exists(story_details_file):
        with open(story_details_file) as f:
            story_details = json.load(f)
    else:
        story_details = {}
    
    # Use subprocess to batch-fetch missing story details
    import subprocess
    missing_sids = [sid for sid in target_story_ids if str(sid) not in story_details]
    if missing_sids:
        print(f"拉取 {len(missing_sids)} 条需求详情...")
        TOKEN = "0a9a31b84da0c5f1b19f13b0e183e8f8"
        # Login fresh
        resp = subprocess.run(["curl", "-s", "-X", "POST",
            "https://ztpm.gree.com:8888/api.php/v2/users/login",
            "-H", "Content-Type: application/json",
            "-d", '{"account":"260298","password":"Lss@530720"}'],
            capture_output=True, text=True, timeout=30)
        try:
            login_data = json.loads(resp.stdout)
            TOKEN = login_data.get("token", TOKEN)
        except:
            pass
        
        for i, sid in enumerate(missing_sids):
            if i % 5 == 0:
                print(f"  {i+1}/{len(missing_sids)}...")
            resp = subprocess.run(["curl", "-s",
                f"https://ztpm.gree.com:8888/api.php/v2/stories/{sid}",
                "-H", f"token: {TOKEN}"],
                capture_output=True, text=True, timeout=30)
            try:
                d = json.loads(resp.stdout)
                if d.get("status") == "success":
                    story_details[str(sid)] = d.get("data", d)
            except:
                pass
        with open(story_details_file, "w") as f:
            json.dump(story_details, f, ensure_ascii=False, default=str)
    
    # Also fetch task details for all tasks
    task_details_file = os.path.join(DATA_DIR, "task_details_fms_gas.json")
    if os.path.exists(task_details_file):
        with open(task_details_file) as f:
            task_details = json.load(f)
    else:
        task_details = {}
    
    missing_tids = [tid for tid in task_map if str(tid) not in task_details]
    if missing_tids:
        print(f"拉取 {len(missing_tids)} 条任务详情...")
        TOKEN = "0a9a31b84da0c5f1b19f13b0e183e8f8"
        resp = subprocess.run(["curl", "-s", "-X", "POST",
            "https://ztpm.gree.com:8888/api.php/v2/users/login",
            "-H", "Content-Type: application/json",
            "-d", '{"account":"260298","password":"Lss@530720"}'],
            capture_output=True, text=True, timeout=30)
        try:
            login_data = json.loads(resp.stdout)
            TOKEN = login_data.get("token", TOKEN)
        except:
            pass
        
        for i, tid in enumerate(missing_tids):
            if i % 5 == 0:
                print(f"  {i+1}/{len(missing_tids)}...")
            resp = subprocess.run(["curl", "-s",
                f"https://ztpm.gree.com:8888/api.php/v2/tasks/{tid}",
                "-H", f"token: {TOKEN}"],
                capture_output=True, text=True, timeout=30)
            try:
                d = json.loads(resp.stdout)
                if d.get("status") == "success":
                    task_details[str(tid)] = d.get("data", d)
            except:
                pass
        with open(task_details_file, "w") as f:
            json.dump(task_details, f, ensure_ascii=False, default=str)
    
    # Merge task details into task objects
    for t in tasks:
        tid = str(t["id"])
        if tid in task_details:
            td = task_details[tid]
            for key in ["desc","mode","story","consumed","left","estimate","deadline",
                       "realStarted","finishedDate","type","status","assignedTo","openedBy",
                       "openedDate","finishedBy","finishedDate","pri","progress"]:
                if key in td:
                    t[key] = td[key]
    
    # ==================== CHECKS ====================
    issues = []
    today = date.today()
    
    def pname(pid):
        return proj_name.get(pid, "") if pid else ""
    
    def ename(eid):
        if not eid: return ""
        e = exec_map.get(eid, {})
        return e.get("name", f"执行{eid}")
    
    def sname(sid):
        if not sid: return ""
        s = story_map.get(sid, {})
        return f"{sid} {s.get('title','')}"
    
    def _issue(pri, rule, cat, pid, eid, req, tname, t, detail):
        return {
            "优先级": pri, "不符合规则": rule, "问题分类": cat,
            "所属项目": pname(pid), "所属执行": ename(eid),
            "相关研发需求": req, "任务名称": tname or "",
            "任务描述": str(t.get("desc",""))[:200] if t else "",
            "任务类型": t.get("type","") if t else "",
            "截止日期": str(t.get("deadline","")) if t else "",
            "任务状态": t.get("status","") if t else "",
            "最初预计": str(t.get("estimate","")) if t else "",
            "总计消耗": str(t.get("consumed","")) if t else "",
            "预计剩余": str(t.get("left","")) if t else "",
            "进度": str(t.get("progress","")) if t else "",
            "由谁创建": t.get("openedBy","") if t else "",
            "创建日期": str(t.get("openedDate","")) if t else "",
            "由谁完成": t.get("finishedBy","") if t else "",
            "实际完成": str(t.get("finishedDate","")) if t else "",
            "问题详情": detail
        }
    
    # R1: 标题编号前缀
    print("规则1: 编号前缀...")
    for s in stories:
        title = s.get("title","")
        if not POOL_RE.match(title):
            eid = s.get("execution")
            issues.append(_issue("P1","规则1","需求问题",
                s.get("project"), eid, f"{s['id']} {title}", "", None,
                "需求标题未见需求池编号前缀"))
    
    # R2: 岗位任务覆盖
    print("规则2: 岗位覆盖...")
    for s in stories:
        sid = s["id"]
        sd = story_details.get(str(sid), {})
        s_tasks_raw = sd.get("tasks", [])
        s_tasks = []
        for st in s_tasks_raw:
            # st might be just an ID or an object
            if isinstance(st, (int, str)):
                tid = int(st) if isinstance(st, str) and st.isdigit() else st
                st_obj = task_map.get(tid)
                if st_obj:
                    s_tasks.append(st_obj)
            elif isinstance(st, dict):
                s_tasks.append(st)
        if not s_tasks:
            # Fallback: tasks whose story field == sid
            s_tasks = [t for t in tasks if t.get("story") == sid]
        
        covered = set()
        for t in s_tasks:
            name = (t.get("name") or "").lower()
            ttype = t.get("type", "")
            if "【产品】" in name or "产品" in name[:10] or ttype in ["需求调研","需求设计","需求验收"]:
                covered.add("product")
            if "【ui】" in name or "【ux" in name or "ui" in name[:5] or "ux" in name[:5] or ttype == "UI设计":
                covered.add("ui")
            if "后端" in name[:10] or ttype == "后端开发": covered.add("dev")
            if "前端" in name[:10] or ttype == "前端开发": covered.add("dev")
            if "架构" in name[:10] or ttype in ["开发任务","技术任务"]: covered.add("dev")
            if "【开发" in name: covered.add("dev")
            if "测试" in name[:10] or ttype == "测试": covered.add("test")
        
        missing = [r for r in ["product","ui","dev","test"] if r not in covered]
        if missing:
            eid = s.get("execution")
            issues.append(_issue("P0","规则2","需求问题",
                s.get("project"), eid, f"{sid} {s.get('title','')}", "", None,
                f"缺少岗位任务：{'/'.join(missing)}"))
    
    # R5: 工时/截止日期/多人
    print("规则5: 工时/截止日期...")
    for t in tasks:
        est = t.get("estimate", 0) or 0
        dl = t.get("deadline", "")
        name = t.get("name", "")
        mode = t.get("mode", "")
        sid = t.get("story")
        dets = []
        if est <= 0: dets.append("预计工时为0或未填")
        if not dl: dets.append("截止日期未填")
        if est > 20: dets.append(f"预计工时>{est}h")
        if mode == "multi" and not any(kw in name for kw in MEETING_KW):
            dets.append("多人任务 mode=multi，但任务名未见会议类关键词")
        if dets:
            issues.append(_issue("P1","规则5","任务问题",
                exec_map.get(t.get("execution"),{}).get("project"), t.get("execution"),
                sname(sid), name, t, "；".join(dets)))
    
    # R6: 工时过大
    print("规则6: 工时过大...")
    for t in tasks:
        est = t.get("estimate", 0) or 0
        if est > 24:
            issues.append(_issue("P0","规则6","任务问题",
                exec_map.get(t.get("execution"),{}).get("project"), t.get("execution"),
                sname(t.get("story")), t.get("name",""), t, f"预计工时>{est}h"))
    
    # R9/11: 禁用词
    print("规则9/11: 禁用词...")
    for s in stories:
        title = s.get("title","")
        for w in FORBIDDEN_WORDS:
            if w in title:
                eid = s.get("execution")
                issues.append(_issue("P1","规则11","需求问题",
                    s.get("project"), eid, f"{s['id']} {title}", "", None,
                    f"需求标题包含禁用词：{w}"))
    for t in tasks:
        name = t.get("name","")
        for w in FORBIDDEN_WORDS:
            if w in name:
                issues.append(_issue("P1","规则11","任务问题",
                    exec_map.get(t.get("execution"),{}).get("project"), t.get("execution"),
                    sname(t.get("story")), name, t, f"任务名称包含禁用词：{w}"))
    
    # R15/19: 截止日期
    print("规则15/19: 截止日期...")
    for t in tasks:
        dl_str = t.get("deadline","")
        status = t.get("status","")
        fd = parse_date(t.get("finishedDate"))
        dd = parse_date(dl_str)
        if not dd: continue
        if status not in ("done","closed","finished"):
            if dd < today:
                issues.append(_issue("P0","规则15/19","任务问题",
                    exec_map.get(t.get("execution"),{}).get("project"), t.get("execution"),
                    sname(t.get("story")), t.get("name",""), t,
                    f"任务未完成且已过截止日：{dl_str}"))
        else:
            if fd and fd > dd:
                issues.append(_issue("P0","规则15/19","任务问题",
                    exec_map.get(t.get("execution"),{}).get("project"), t.get("execution"),
                    sname(t.get("story")), t.get("name",""), t,
                    f"任务完成日晚于截止日：{fd} > {dl_str}"))
    
    # R17: 同名任务
    print("规则17: 同名任务...")
    ename_grp = defaultdict(list)
    for t in tasks:
        eid = t.get("execution")
        name = (t.get("name","")).strip()
        ename_grp[(eid, name)].append(t)
    for (eid, name), tlist in ename_grp.items():
        if len(tlist) > 1:
            for t in tlist:
                issues.append(_issue("P1","规则17","任务问题",
                    exec_map.get(eid,{}).get("project"), eid,
                    sname(t.get("story")), name, t,
                    f"同迭代任务名称重复，共{len(tlist)}条"))
    
    # R4: 任务关联需求
    print("规则4: 任务关联需求...")
    for t in tasks:
        sid = t.get("story", 0)
        if not sid or sid == 0:
            issues.append(_issue("P0","规则4","任务问题",
                exec_map.get(t.get("execution"),{}).get("project"), t.get("execution"),
                "", t.get("name",""), t, "任务未关联需求"))
    
    # R10: 通用需求任务描述为空
    print("规则10: 通用需求描述...")
    for s in stories:
        title = s.get("title","")
        if not any(kw in title for kw in GENERIC_KW):
            continue
        sd = story_details.get(str(s["id"]), {})
        s_tasks_raw = sd.get("tasks", [])
        s_tasks = []
        for st in s_tasks_raw:
            if isinstance(st, (int, str)):
                tid = int(st) if isinstance(st, str) and st.isdigit() else st
                st_obj = task_map.get(tid)
                if st_obj: s_tasks.append(st_obj)
            elif isinstance(st, dict):
                s_tasks.append(st)
        if not s_tasks:
            s_tasks = [t for t in tasks if t.get("story") == s["id"]]
        for t in s_tasks:
            desc = str(t.get("desc","")).strip()
            if not desc or desc in ("<p></p>","&nbsp;","<br>","None",""):
                issues.append(_issue("P1","规则10","任务问题",
                    s.get("project"), s.get("execution"),
                    f"{s['id']} {title}", t.get("name",""), t,
                    "通用业务功能需求下任务描述为空"))
    
    # Sort
    def sortkey(i):
        pri = 0 if i["优先级"]=="P0" else 1
        cat = 0 if "需求" in i["问题分类"] else 1
        nums = [int(n) for n in re.findall(r'\d+', i["不符合规则"])]
        rn = nums[0] if nums else 99
        return (pri, cat, rn)
    issues.sort(key=sortkey)
    
    # Output CSV
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
