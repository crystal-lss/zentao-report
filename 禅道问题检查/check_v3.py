#!/usr/bin/env python3
"""
禅道需求任务规范检查 - FMS + GAS (仅用缓存数据)
"""
import json, csv, re, os
from datetime import datetime, date
from collections import defaultdict

DATA_DIR = "/Users/crystal/WorkBuddy/禅道任务/禅道问题检查/data_cache"
CACHE_FILE = os.path.join(DATA_DIR, "zentao_full_data.json")
TARGET_PROJECT_IDS = {962, 977}

FORBIDDEN = ["优化", "迭代", "对接"]
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


def main():
    print("加载缓存数据...")
    with open(CACHE_FILE) as f:
        raw = json.load(f)
    
    # === Filter: FMS(962) + GAS(977) ===
    target_exec_ids = {e["id"] for e in raw["executions"] if e.get("project") in TARGET_PROJECT_IDS}
    
    proj_name = {p["id"]: p.get("name","") for p in raw["projects"]}
    
    executions = [e for e in raw["executions"] if e["id"] in target_exec_ids]
    exec_map = {e["id"]: e for e in executions}
    exec_to_proj = {e["id"]: e.get("project") for e in executions}
    
    # Tasks in target executions
    tasks = [t for t in raw["tasks"] if t.get("execution") in target_exec_ids]
    task_map = {t["id"]: t for t in tasks}
    
    # Stories: linked from tasks OR story.project (which is actually exec ID) is in target
    target_sids = set()
    for t in tasks:
        sid = t.get("story", 0)
        if sid:
            target_sids.add(int(sid) if isinstance(sid, str) and sid.isdigit() else sid)
    for s in raw["stories"]:
        sproj = s.get("project", 0)  # This is actually execution ID in ZenTao data
        try: sproj = int(sproj)
        except: sproj = 0
        if sproj in target_exec_ids:
            target_sids.add(s["id"])
    
    stories = [s for s in raw["stories"] if s["id"] in target_sids]
    story_map = {s["id"]: s for s in stories}
    
    # Story -> execution mapping
    story_to_exec = {}
    for s in stories:
        sproj = s.get("project", 0)
        try: sproj = int(sproj)
        except: sproj = 0
        if sproj in exec_to_proj:
            story_to_exec[s["id"]] = sproj
    # Also from tasks
    for t in tasks:
        sid = t.get("story")
        eid = t.get("execution")
        if sid and eid and sid not in story_to_exec:
            story_to_exec[sid] = eid
    
    # Task -> project
    task_proj = {t["id"]: exec_to_proj.get(t.get("execution")) for t in tasks}
    
    # User name mapping
    user_name = {}
    # Load from file-based map
    import os as _os
    map_file = '/Users/crystal/WorkBuddy/禅道任务/禅道问题检查/data_cache/user_name_map.json'
    if _os.path.exists(map_file):
        with open(map_file) as f:
            user_name = json.load(f)
    for u in raw.get("users", []):
        uid = u.get("id")
        name = u.get("realname", "") or u.get("account", "")
        if uid:
            user_name[str(uid)] = name
            user_name[uid] = name
    
    print(f"FMS+GAS: {len(stories)} 需求, {len(tasks)} 任务, {len(executions)} 执行")
    
    # === CHECKS ===
    issues = []
    today = date.today()
    
    def pn(pid):
        return proj_name.get(pid,"") if pid else ""
    
    def en(eid):
        if not eid: return ""
        e = exec_map.get(eid, {})
        return e.get("name", f"执行{eid}")
    
    def sn(sid):
        if not sid: return ""
        s = story_map.get(sid, {})
        return f"{sid} {s.get('title','')}"
    
    def uname(uid):
        if not uid: return ""
        u = str(uid)
        name = user_name.get(u, user_name.get(u.lower(), ""))
        if name and name != u:
            return f"{name}({u})"
        return u
    
    def mk(pri, rule, cat, pid, eid, req, tname, t_or_s, detail):
        t = t_or_s if isinstance(t_or_s, dict) and 'execution' in (t_or_s or {}) else None
        s = t_or_s if isinstance(t_or_s, dict) and 'execution' not in (t_or_s or {}) else None
        return {
            "优先级":pri,"不符合规则":rule,"问题分类":cat,
            "所属项目":pn(pid),"所属执行":en(eid),
            "相关研发需求":req,"任务名称":tname or "",
            "任务描述":str(t.get("desc",""))[:200].replace("\n"," ") if t else "",
            "任务类型":t.get("type","") if t else "",
            "截止日期":str(t.get("deadline","")) if t else "",
            "任务状态":t.get("status","") if t else "",
            "最初预计":str(t.get("estimate","")) if t else "",
            "总计消耗":str(t.get("consumed","")) if t else "",
            "预计剩余":str(t.get("left","")) if t else "",
            "进度":str(t.get("progress","")) if t else "",
            "由谁创建":uname(t.get("openedBy")) if t else (uname(s.get("openedBy")) if s else ""),
            "创建日期":str(t.get("openedDate","")) if t else (str(s.get("openedDate","")) if s else ""),
            "由谁完成":uname(t.get("finishedBy")) if t else "",
            "实际完成":str(t.get("finishedDate","")) if t else "",
            "问题详情":detail
        }
    
    # Story->tasks mapping from task.story field
    story_tasks = defaultdict(list)
    for t in tasks:
        sid = t.get("story")
        if sid:
            story_tasks[sid].append(t)
    
    # R1: 编号前缀
    print("R1...")
    for s in stories:
        title = s.get("title","")
        if not POOL_RE.match(title):
            eid = story_to_exec.get(s["id"], s.get("project"))
            pid = exec_to_proj.get(eid)
            issues.append(mk("P1","规则1","需求问题",
                pid, eid, f"{s['id']} {title}", "", s,
                "需求标题未见需求池编号前缀"))
    
    # R2: 岗位覆盖
    print("R2...")
    for s in stories:
        sid = s["id"]
        s_tasks = story_tasks.get(sid, [])
        covered = set()
        for t in s_tasks:
            name = (t.get("name") or "").lower()
            ttype = t.get("type", "")
            if "【产品】" in name or "产品" in name[:8] or ttype in ["需求调研","需求设计","需求验收"]:
                covered.add("product")
            if "【ui】" in name or "【ux" in name or ("ui" in name[:8] and "ui" not in name[8:20]) or "ux" in name[:8] or ttype == "UI设计":
                covered.add("ui")
            if "后端" in name[:10] or ttype == "后端开发": covered.add("dev")
            if "前端" in name[:10] or ttype == "前端开发": covered.add("dev")
            if "架构" in name[:10] or ttype in ["开发任务","技术任务"]: covered.add("dev")
            if "【开发" in name: covered.add("dev")
            if "测试" in name[:10] or ttype == "测试": covered.add("test")
        missing = [r for r in ["product","ui","dev","test"] if r not in covered]
        if missing:
            eid = story_to_exec.get(sid, s.get("project"))
            pid = exec_to_proj.get(eid)
            issues.append(mk("P0","规则2","需求问题",
                pid, eid, f"{sid} {s.get('title','')}", "", s,
                f"缺少岗位任务：{'/'.join(missing)}"))
    
    # R4: 任务未关联需求
    print("R4...")
    for t in tasks:
        sid = t.get("story", 0)
        if not sid or sid == 0:
            eid = t.get("execution")
            issues.append(mk("P0","规则4","任务问题",
                exec_to_proj.get(eid), eid,
                "", t.get("name",""), t, "任务未关联需求"))
    
    # R5: 工时/截止日期/多人
    print("R5...")
    for t in tasks:
        est = float(t.get("estimate", 0) or 0)
        dl = t.get("deadline", "")
        name = t.get("name", "")
        mode = t.get("mode", "")
        dets = []
        if est <= 0: dets.append("预计工时为0或未填")
        if not dl: dets.append("截止日期未填")
        if est > 20: dets.append(f"预计工时>{est}h")
        if mode == "multi" and not any(kw in name for kw in MEETING_KW):
            dets.append("多人任务 mode=multi，但任务名未见会议类关键词")
        if dets:
            eid = t.get("execution")
            issues.append(mk("P1","规则5","任务问题",
                exec_to_proj.get(eid), eid,
                sn(t.get("story")), name, t, "；".join(dets)))
    
    # R6: 工时过大
    print("R6...")
    for t in tasks:
        est = float(t.get("estimate", 0) or 0)
        if est > 24:
            eid = t.get("execution")
            issues.append(mk("P0","规则6","任务问题",
                exec_to_proj.get(eid), eid,
                sn(t.get("story")), t.get("name",""), t, f"预计工时>{est}h"))
    
    # R9/11: 禁用词
    print("R9/11...")
    for s in stories:
        title = s.get("title","")
        for w in FORBIDDEN:
            if w in title:
                eid = story_to_exec.get(s["id"], s.get("project"))
                pid = exec_to_proj.get(eid)
                issues.append(mk("P1","规则11","需求问题",
                    pid, eid, f"{s['id']} {title}", "", s,
                    f"需求标题包含禁用词：{w}"))
    for t in tasks:
        name = t.get("name","")
        for w in FORBIDDEN:
            if w in name:
                eid = t.get("execution")
                issues.append(mk("P1","规则11","任务问题",
                    exec_to_proj.get(eid), eid,
                    sn(t.get("story")), name, t, f"任务名称包含禁用词：{w}"))
    
    # R10: 通用需求任务描述为空
    print("R10...")
    for s in stories:
        title = s.get("title","")
        if not any(kw in title for kw in GENERIC_KW):
            continue
        s_tasks = story_tasks.get(s["id"], [])
        for t in s_tasks:
            desc = str(t.get("desc","")).strip()
            if not desc or desc in ("<p></p>","&nbsp;","<br>","None",""):
                eid = story_to_exec.get(s["id"], s.get("project"))
                pid = exec_to_proj.get(eid)
                issues.append(mk("P1","规则10","任务问题",
                    pid, eid,
                    f"{s['id']} {title}", t.get("name",""), t,
                    "通用业务功能需求下任务描述为空"))
    
    # R15/19: 截止日期
    print("R15/19...")
    for t in tasks:
        dl_str = t.get("deadline","")
        status = t.get("status","")
        fd = parse_date(t.get("finishedDate"))
        dd = parse_date(dl_str)
        if not dd: continue
        eid = t.get("execution")
        if status not in ("done","closed","finished"):
            if dd < today:
                issues.append(mk("P0","规则15/19","任务问题",
                    exec_to_proj.get(eid), eid,
                    sn(t.get("story")), t.get("name",""), t,
                    f"任务未完成且已过截止日：{dl_str}"))
        else:
            if fd and fd > dd:
                delta = (fd - dd).days
                if delta > 3:  # 超期3天以内不算
                    issues.append(mk("P0","规则15/19","任务问题",
                        exec_to_proj.get(eid), eid,
                        sn(t.get("story")), t.get("name",""), t,
                        f"任务完成日晚于截止日：{fd} > {dl_str}"))
    
    # R17: 同名任务
    print("R17...")
    ename_grp = defaultdict(list)
    for t in tasks:
        eid = t.get("execution")
        name = (t.get("name","")).strip()
        ename_grp[(eid, name)].append(t)
    for (eid, name), tlist in ename_grp.items():
        if len(tlist) > 1:
            for t in tlist:
                issues.append(mk("P1","规则17","任务问题",
                    exec_to_proj.get(eid), eid,
                    sn(t.get("story")), name, t,
                    f"同迭代任务名称重复，共{len(tlist)}条"))
    
    # Sort
    def sk(i):
        pri = 0 if i["优先级"]=="P0" else 1
        cat = 0 if "需求" in i["问题分类"] else 1
        nums = [int(n) for n in re.findall(r'\d+', i["不符合规则"])]
        rn = nums[0] if nums else 99
        return (pri, cat, rn)
    issues.sort(key=sk)
    
    # Output
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
    si = sum(1 for i in issues if "需求" in i["问题分类"])
    ti = sum(1 for i in issues if "任务" in i["问题分类"])
    
    print(f"\n共 {len(issues)} 条: P0={p0}, P1={p1}, 需求={si}, 任务={ti}")
    print(f"报告: {output_csv}")


if __name__ == "__main__":
    main()
