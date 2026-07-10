#!/usr/bin/env python3
"""禅道任务报告中心 - 自动生成器"""
import json, os, sys
from datetime import datetime, date
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(PROJECT_DIR, 'build')
TODAY = datetime.now()
TODAY_STR = TODAY.strftime('%Y-%m-%d')
TODAY_DATETIME = TODAY.strftime('%Y-%m-%d %H:%M')

# Task type → category mapping
CAT_MAP = {
    '需求设计': '产品', '需求调研': '产品',
    'ab1_needs_research': '产品', 'ab2_request_des': '产品', 'ab3_request_check': '产品',
    'a_dev': '后端', 'a_dev4_control': '后端', 'Dev_Ops': '后端',
    'a_dev2_front': '前端',
    'ad1_UI_des': 'uiux',
    'ae2_test': '测试',
}

CAT_NAMES = {'产品': '产品', '后端': '后端', '前端': '前端', '测试': '测试', 'uiux': 'UI_UX'}
CAT_DISPLAY = {'产品': '产品', '后端': '后端', '前端': '前端', '测试': '测试', 'uiux': 'UI/UX'}
CAT_ICONS = {'产品': '📋', '后端': '⚙️', '前端': '🎨', '测试': '🧪', 'uiux': '🖌️'}
CAT_COLORS = {'产品': '#a78bfa', '后端': '#4ade80', '前端': '#f472b6', '测试': '#fbbf24', 'uiux': '#38bdf8'}

# Execution data
EXEC_MAP = {
    4519: ('【2026】FMS-0630', 'FMS', '2026-04-30', '2026-06-30'),
    4562: ('【2026】FMS-0615', 'FMS', '2026-05-14', '2026-06-15'),
    4651: ('【2026】FMS-0715', 'FMS', '2026-06-15', '2026-07-15'),
    4527: ('【2026】海外售后服务器迁移-0630', 'GAS', '2026-04-20', '2026-06-30'),
    4639: ('【2026】海外售后v4.5-0630', 'GAS', '2026-06-11', '2026-06-30'),
}

def load_tasks():
    """加载所有任务数据"""
    all_tasks = []
    for eid in EXEC_MAP:
        fp = f'/tmp/tasks_{eid}.json'
        if os.path.exists(fp):
            with open(fp) as f:
                data = json.load(f)
            tasks = data.get('tasks', [])
            for t in tasks:
                t['_exec_name'] = EXEC_MAP[eid][0]
                t['_project'] = EXEC_MAP[eid][1]
                t['_exec_begin'] = EXEC_MAP[eid][2]
                t['_exec_end'] = EXEC_MAP[eid][3]
                # Category
                tp = t.get('type', '')
                cat = CAT_MAP.get(tp, '其他')
                t['_category'] = cat
            all_tasks.extend(tasks)
    return all_tasks

def categorize(tasks):
    """按类别分组 (只取未完成的)"""
    undone = [t for t in tasks if t.get('status') not in ('done', 'closed', 'cancel')]
    groups = defaultdict(list)
    for t in undone:
        groups[t['_category']].append(t)
    return dict(groups), undone

def fmt_hours(val):
    """格式化工时"""
    try:
        v = float(val)
        return f'{v:.1f}h' if v != int(v) else f'{int(v)}h'
    except:
        return '-'

def status_badge(status, deadline=None):
    """status: wait/doing/done/closed"""
    if status == 'wait':
        return '待处理', 'status-wait'
    elif status == 'doing':
        return '进行中', 'status-doing'
    return status, ''

def pri_label(pri):
    m = {'1': '最高', '2': '高', '3': '中', '4': '低'}
    return m.get(str(pri), str(pri))

def html_escape(s):
    if s is None: return ''
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

def build_detail_page(project, category, tasks, base_path):
    """生成分类详情页"""
    cat_name = CAT_NAMES.get(category, category)
    display_name = CAT_DISPLAY.get(category, cat_name)
    icon = CAT_ICONS.get(category, '📄')
    color = CAT_COLORS.get(category, '#94a3b8')
    
    # Stats
    total = len(tasks)
    wait_n = sum(1 for t in tasks if t.get('status') == 'wait')
    doing_n = sum(1 for t in tasks if t.get('status') == 'doing')
    people = sorted(set(t.get('assignedToRealName', '') or '' for t in tasks if t.get('assignedToRealName')))
    
    # Build table rows
    rows = []
    for t in sorted(tasks, key=lambda x: (x.get('status','') != 'doing', x.get('deadline','') or '9999')):
        name = t.get('name', '')
        exec_name = t.get('_exec_name', '')
        owner = t.get('assignedToRealName', '') or ''
        status = t.get('status', '')
        s_text, s_cls = status_badge(status)
        pri = t.get('pri', '')
        deadline = t.get('deadline', '') or ''
        estimate = fmt_hours(t.get('estimate', 0))
        consumed = fmt_hours(t.get('consumed', 0))
        
        # Highlight overdue
        is_overdue = False
        if deadline and status in ('wait', 'doing'):
            try:
                dl = datetime.strptime(deadline, '%Y-%m-%d').date()
                if dl < TODAY.date():
                    is_overdue = True
            except: pass
        
        row_cls = ' class="urgent"' if is_overdue else ''
        dl_cls = ' class="deadline"' if is_overdue else ''
        
        rows.append(f'''<tr{row_cls}>
            <td class="task-name" title="{html_escape(name)}">{html_escape(name[:60])}{'...' if len(name)>60 else ''}</td>
            <td>{exec_name}</td>
            <td>{owner}</td>
            <td><span class="status-badge {s_cls}">{s_text}</span></td>
            <td>{pri_label(pri)}</td>
            <td{dl_cls}>{deadline}</td>
            <td class="num">{estimate}</td>
            <td class="num">{consumed}</td>
        </tr>''')
    
    people_str = '、'.join(people) if people else '无'
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>未完成{cat_name}任务明细 - {project}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:#f5f7fa;color:#1a1f36;padding:20px}}
.header{{text-align:center;padding:24px 0 16px}}
.header h1{{font-size:24px;font-weight:800}}
.header .meta{{color:#6b7280;font-size:13px;margin-top:6px}}
.breadcrumb{{margin-bottom:16px;font-size:13px}}
.breadcrumb a{{color:#3b82f6;text-decoration:none}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}}
.card{{background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card .num{{font-size:28px;font-weight:800;color:{color}}}
.card .label{{font-size:12px;color:#9ca3af;margin-top:4px}}
.summary-bar{{background:#fff;border-radius:12px;padding:16px 20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06);font-size:14px}}
.summary-bar span{{color:#6b7280}}
.summary-bar strong{{color:#1a1f36}}
table{{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);border-collapse:collapse}}
th{{background:#f8fafc;color:#475569;font-weight:600;font-size:12px;padding:12px 10px;text-align:left;border-bottom:1px solid #e5e7eb}}
td{{padding:10px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#334155}}
tr:hover td{{background:#f8fafc}}
tr.urgent td{{background:#fee2e2}}
.task-name{{max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.status-badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600}}
.status-wait{{background:#fef3c7;color:#92400e}}
.status-doing{{background:#dbeafe;color:#1e40af}}
.deadline{{color:#dc2626;font-weight:600}}
.num{{text-align:right}}
.footer{{text-align:center;padding:24px;color:#9ca3af;font-size:12px}}
@media(max-width:768px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="breadcrumb"><a href="../../index.html">← 返回报告中心</a> | <a href="../index.html">{project} 总览</a></div>
<div class="header">
    <h1>{icon} 未完成{display_name}任务明细</h1>
    <p class="meta">{project} | 数据更新：{TODAY_DATETIME} | {len(people)}人参与 | 共{total}个未完成任务</p>
</div>
<div class="cards">
    <div class="card"><div class="num">{total}</div><div class="label">未完成总计</div></div>
    <div class="card"><div class="num">{wait_n}</div><div class="label">待处理</div></div>
    <div class="card"><div class="num">{doing_n}</div><div class="label">进行中</div></div>
    <div class="card"><div class="num">{len(people)}</div><div class="label">参与人数</div></div>
</div>
<div class="summary-bar"><span>👥 参与人员：<strong>{people_str}</strong></span></div>
<table>
<thead><tr><th>任务名称</th><th>所属迭代</th><th>负责人</th><th>状态</th><th>优先级</th><th>截止日期</th><th>预估</th><th>已耗</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME}</div>
</body>
</html>'''
    return html

def build_overdue_page(project, all_tasks):
    """生成延期任务页面"""
    overdue = []
    for t in all_tasks:
        deadline = t.get('deadline', '') or ''
        status = t.get('status', '')
        if deadline and status in ('wait', 'doing'):
            try:
                dl = datetime.strptime(deadline, '%Y-%m-%d').date()
                if dl < TODAY.date():
                    days = (TODAY.date() - dl).days
                    t['_overdue_days'] = days
                    overdue.append(t)
            except: pass
    
    overdue.sort(key=lambda x: -x['_overdue_days'])
    
    rows = []
    for t in overdue:
        name = t.get('name', '')
        exec_name = t.get('_exec_name', '')
        cat = CAT_DISPLAY.get(t['_category'], t['_category'])
        owner = t.get('assignedToRealName', '') or ''
        deadline = t.get('deadline', '')
        days = t['_overdue_days']
        day_text = f'{days}天' if days >= 2 else '今天到期' if days == 0 else '1天'
        row_cls = 'urgent' if days >= 3 else 'warn' if days >= 1 else ''
        days_cls = 'urgent' if days >= 3 else 'warn' if days >= 1 else ''
        
        rows.append(f'''<tr class="{row_cls}">
            <td class="task-name" title="{html_escape(name)}">{html_escape(name[:60])}{'...' if len(name)>60 else ''}</td>
            <td>{exec_name}</td>
            <td>{cat}</td>
            <td>{owner}</td>
            <td class="deadline">{deadline}</td>
            <td class="days {days_cls}">{day_text}</td>
        </tr>''')
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>延期任务 - {project}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:#fef2f2;color:#1a1f36;padding:20px}}
.header{{text-align:center;padding:24px 0 16px}}
.header h1{{font-size:24px;font-weight:800;color:#dc2626}}
.header .meta{{color:#6b7280;font-size:13px;margin-top:6px}}
.breadcrumb{{margin-bottom:16px;font-size:13px}}
.breadcrumb a{{color:#3b82f6;text-decoration:none}}
.alert{{background:#fff;border:1px solid #fecaca;border-radius:12px;padding:16px 20px;margin-bottom:20px;color:#991b1b;font-size:14px}}
.alert strong{{font-size:18px}}
table{{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);border-collapse:collapse}}
th{{background:#fef2f2;color:#991b1b;font-weight:600;font-size:12px;padding:12px 10px;text-align:left;border-bottom:1px solid #fecaca}}
td{{padding:10px;border-bottom:1px solid #fef2f2;font-size:13px;color:#334155}}
tr:hover td{{background:#fff5f5}}
tr.urgent td{{background:#fee2e2}}
tr.warn td{{background:#fffbeb}}
.task-name{{max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.deadline{{color:#dc2626;font-weight:600}}
.days{{font-weight:700}}
.urgent .days{{color:#dc2626}}
.warn .days{{color:#d97706}}
.footer{{text-align:center;padding:24px;color:#9ca3af;font-size:12px}}
</style>
</head>
<body>
<div class="breadcrumb"><a href="index.html">← 返回项目总览</a> | <a href="../index.html">报告中心</a></div>
<div class="header"><h1>🚨 延期任务</h1><p class="meta">{project} | 数据更新：{TODAY_DATETIME}</p></div>
<div class="alert">⚠️ 共有 <strong>{len(overdue)}</strong> 个任务已超过截止日期！</div>
<table>
<thead><tr><th>任务名称</th><th>所属迭代</th><th>类别</th><th>负责人</th><th>截止日期</th><th>超期天数</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table>
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME}</div>
</body>
</html>'''
    return html, len(overdue)

def build_workload_page(project, groups, all_tasks):
    """生成员工负载分析页面"""
    # Per-category load
    cat_rows = []
    total_undone = 0
    for cat in ['产品', '后端', '前端', '测试', 'uiux']:
        cat_tasks = groups.get(cat, [])
        people = set(t.get('assignedToRealName','') for t in cat_tasks if t.get('assignedToRealName'))
        n = len(cat_tasks)
        p = len(people) or 1
        avg = n / p
        total_undone += n
        cat_name = CAT_DISPLAY.get(cat, cat)
        icon = CAT_ICONS.get(cat, '')
        cat_rows.append(f'''<tr><td>{icon} {cat_name}</td><td class="num">{n}</td><td class="num">{len(people)}</td><td class="num">{avg:.1f}</td></tr>''')
    
    # Per person load
    person_tasks = defaultdict(list)
    for t in all_tasks:
        if t.get('status') not in ('done', 'closed', 'cancel'):
            p = t.get('assignedToRealName', '') or '未分配'
            person_tasks[p].append(t)
    
    person_rows = []
    for name in sorted(person_tasks, key=lambda n: -len(person_tasks[n])):
        tasks = person_tasks[name]
        waiting = sum(1 for t in tasks if t.get('status') == 'wait')
        doing = sum(1 for t in tasks if t.get('status') == 'doing')
        total_est = sum(float(t.get('estimate',0) or 0) for t in tasks)
        total_cons = sum(float(t.get('consumed',0) or 0) for t in tasks)
        cats = set(CAT_DISPLAY.get(t['_category'], t['_category']) for t in tasks)
        person_rows.append(f'''<tr>
            <td>{html_escape(name)}</td>
            <td>{'、'.join(cats)}</td>
            <td class="num">{len(tasks)}</td>
            <td class="num">{waiting}</td>
            <td class="num">{doing}</td>
            <td class="num">{total_est:.0f}h</td>
            <td class="num">{total_cons:.0f}h</td>
        </tr>''')
    
    total_count = len(all_tasks)
    overdue_count = sum(1 for t in all_tasks if t.get('_overdue_days', False))
    n_exec = len(set(t['_exec_name'] for t in all_tasks))
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>员工负载分析 - {project}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:#f5f7fa;color:#1a1f36;padding:20px}}
.header{{text-align:center;padding:24px 0 16px}}
.header h1{{font-size:24px;font-weight:800}}
.header .meta{{color:#6b7280;font-size:13px;margin-top:6px}}
.breadcrumb{{margin-bottom:16px;font-size:13px}}
.breadcrumb a{{color:#3b82f6;text-decoration:none}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}}
.card{{background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card .num{{font-size:28px;font-weight:800}}
.card .label{{font-size:12px;color:#9ca3af;margin-top:4px}}
table{{width:100%;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06);border-collapse:collapse;margin-bottom:24px}}
th{{background:#f8fafc;color:#475569;font-weight:600;font-size:12px;padding:12px 10px;text-align:left;border-bottom:1px solid #e5e7eb}}
td{{padding:10px;border-bottom:1px solid #f1f5f9;font-size:13px;color:#334155}}
tr:hover td{{background:#f8fafc}}
.num{{text-align:right}}
.section-title{{font-size:16px;font-weight:700;margin:24px 0 12px;color:#1a1f36}}
.footer{{text-align:center;padding:24px;color:#9ca3af;font-size:12px}}
@media(max-width:768px){{.cards{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<div class="breadcrumb"><a href="index.html">← 返回项目总览</a> | <a href="../index.html">报告中心</a></div>
<div class="header"><h1>💪 员工负载分析</h1><p class="meta">{project} | 数据更新：{TODAY_DATETIME}</p></div>
<div class="cards">
    <div class="card"><div class="num" style="color:#f59e0b">{total_undone}</div><div class="label">未完成任务</div></div>
    <div class="card"><div class="num" style="color:#3b82f6">{total_count}</div><div class="label">总任务数</div></div>
    <div class="card"><div class="num" style="color:#dc2626">{overdue_count}</div><div class="label">延期任务</div></div>
    <div class="card"><div class="num" style="color:#10b981">{n_exec}</div><div class="label">进行中迭代</div></div>
</div>
<div class="section-title">📊 按角色分组负载</div>
<table>
<thead><tr><th>角色</th><th>未完成数</th><th>人数</th><th>人均负载</th></tr></thead>
<tbody>{''.join(cat_rows)}</tbody>
</table>
<div class="section-title">👤 个人负载明细</div>
<table>
<thead><tr><th>姓名</th><th>角色</th><th>任务数</th><th>待处理</th><th>进行中</th><th>预估工时</th><th>已耗工时</th></tr></thead>
<tbody>{''.join(person_rows)}</tbody>
</table>
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME}</div>
</body>
</html>'''
    return html

def build_project_page(project, groups, all_tasks, date_dir):
    """生成项目总览页面 fms/index.html 或 gas/index.html"""
    # Stats
    execs = sorted(set(t['_exec_name'] for t in all_tasks))
    exec_intros = []
    for ename in execs:
        for eid, info in EXEC_MAP.items():
            if info[0] == ename and info[1] == project:
                exec_intros.append({'name': ename, 'begin': info[2], 'end': info[3]})
                break
    
    cat_stats = {}
    for cat in ['产品', '后端', '前端', '测试', 'uiux']:
        cat_tasks = groups.get(cat, [])
        wait_n = sum(1 for t in cat_tasks if t.get('status') == 'wait')
        doing_n = sum(1 for t in cat_tasks if t.get('status') == 'doing')
        people = len(set(t.get('assignedToRealName','') for t in cat_tasks if t.get('assignedToRealName')))
        cat_stats[cat] = {'total': len(cat_tasks), 'wait': wait_n, 'doing': doing_n, 'people': people}
    
    # Overdue count
    overdue_count = sum(1 for t in all_tasks if t.get('_overdue_days', False))
    total_count = len(all_tasks)
    
    overdue_pills = []
    for cat in ['产品', '后端', '前端', '测试', 'uiux']:
        s = cat_stats[cat]
        cat_display = CAT_DISPLAY[cat]
        color_cls = f'c-{cat}' if cat != 'uiux' else 'c-uiux'
        overdue_pills.append(f'''<div class="stat-pill-small {color_cls}">
        <div class="num">{s['total']}</div>
        <div class="meta"><span class="meta-icon">{CAT_ICONS[cat]}</span> {cat_display} <span style="color:#94a3b8">待{s['wait']}/做{s['doing']}</span></div>
    </div>''')
    
    overdue_pills.append(f'''<div class="stat-pill-small c-overdue">
        <div class="num">{overdue_count}</div>
        <div class="meta"><span class="meta-icon">🚨</span> 延期任务 <span style="color:#94a3b8">共{total_count}个</span></div>
    </div>''')
    
    feat_cards = []
    for cat in ['产品', '后端', '前端', 'uiux']:
        cs = cat_stats[cat]
        cat_display = CAT_DISPLAY[cat]
        cat_safe = CAT_NAMES[cat]
        subtitles = {'产品': '需求 / AB 类型', '后端': '开发任务', '前端': '开发任务', 'uiux': '设计任务'}
        feat_cards.append(f'''<a class="feature-card" href="{date_dir}/{cat_safe}_详细任务.html">
            <div class="card-icon-large">{CAT_ICONS[cat]}</div>
            <div class="card-title">{cat_display}任务</div>
            <div class="card-subtitle">{subtitles.get(cat, '')}</div>
            <div class="card-count"><strong>{cs['total']}</strong> 个未完成 · <strong>{cs['people']}</strong> 人</div>
        </a>''')
    
    test_cs = cat_stats['测试']
    exec_rows = ''.join(f'<tr><td>{e["name"]}</td><td>doing</td><td>{e["begin"]} ~ {e["end"]}</td></tr>' for e in exec_intros)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{project} - 项目总览</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:radial-gradient(ellipse at center,#2d3561 0%,#1a1f3a 50%,#0f1429 100%);color:#e2e8f0;min-height:100vh;padding:20px}}
.container{{max-width:1000px;margin:0 auto}}
.header{{text-align:center;padding:24px 0 16px}}
.header h1{{font-size:24px;font-weight:700;color:#f8fafc}}
.header .date-badge{{display:inline-block;background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:5px 18px;font-size:13px;margin-top:8px}}
.breadcrumb{{margin-bottom:20px;font-size:13px;text-align:center}}
.breadcrumb a{{color:#60a5fa;text-decoration:none}}
.stat-pills-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px}}
.stat-pill-small{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:16px 8px;text-align:center}}
.stat-pill-small .num{{font-size:26px;font-weight:700;margin-bottom:8px}}
.stat-pill-small .meta{{font-size:11px;color:#94a3b8}}
.stat-pill-small.c-产品 .num{{color:#a78bfa}}
.stat-pill-small.c-后端 .num{{color:#4ade80}}
.stat-pill-small.c-前端 .num{{color:#f472b6}}
.stat-pill-small.c-测试 .num{{color:#fbbf24}}
.stat-pill-small.c-uiux .num{{color:#38bdf8}}
.stat-pill-small.c-overdue .num{{color:#f87171}}
.feature-cards-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.feature-card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:28px 16px 24px;text-align:center;display:block;text-decoration:none;color:#e2e8f0;transition:all .2s}}
.feature-card:hover{{background:rgba(255,255,255,.06);transform:translateY(-3px)}}
.feature-card .card-icon-large{{font-size:28px;margin-bottom:12px}}
.feature-card .card-title{{font-size:15px;font-weight:700;margin-bottom:4px}}
.feature-card .card-subtitle{{font-size:12px;color:#64748b;margin-bottom:8px}}
.feature-card .card-count{{font-size:13px;color:#94a3b8}}
.feature-card .card-count strong{{color:#cbd5e1}}
.func-cards-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:24px}}
.func-card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:24px 16px;text-align:center;display:block;text-decoration:none;color:#e2e8f0;transition:all .2s}}
.func-card:hover{{background:rgba(255,255,255,.06);transform:translateY(-3px)}}
.func-card .card-icon-large{{font-size:24px;margin-bottom:8px}}
.func-card .card-title{{font-size:14px;font-weight:700;margin-bottom:4px}}
.func-card .card-desc{{font-size:12px;color:#64748b}}
.exec-section{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:24px;margin-bottom:24px}}
.exec-section h3{{font-size:16px;color:#f8fafc;margin-bottom:14px}}
.exec-table{{width:100%;border-collapse:collapse;font-size:13px;color:#cbd5e1}}
.exec-table th{{color:#94a3b8;text-align:left;padding:8px;border-bottom:1px solid rgba(255,255,255,.08)}}
.exec-table td{{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.04)}}
.footer{{text-align:center;padding:24px;color:#475569;font-size:12px}}
@media(max-width:768px){{.stat-pills-row{{grid-template-columns:repeat(3,1fr)}}.feature-cards-row{{grid-template-columns:repeat(2,1fr)}}.func-cards-row{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<div class="container">
<div class="breadcrumb"><a href="../index.html">← 返回报告中心</a></div>
<div class="header"><h1>{project}</h1><div class="date-badge">数据更新：{TODAY_DATETIME}</div></div>
<div class="stat-pills-row">{''.join(overdue_pills)}</div>
<div class="feature-cards-row">{''.join(feat_cards)}</div>
<div class="func-cards-row">
    <a class="func-card" href="{date_dir}/测试_详细任务.html">
        <div class="card-icon-large">🧪</div><div class="card-title">测试任务</div>
        <div class="card-desc">测试执行 + 测试设计<br><strong>{test_cs['total']}</strong> 个未完成 · <strong>{test_cs['people']}</strong> 人</div>
    </a>
    <a class="func-card" href="#executions">
        <div class="card-icon-large">📊</div><div class="card-title">迭代执行进展</div>
        <div class="card-desc"><strong>{len(exec_intros)}</strong> 个进行中迭代<br>报告总览</div>
    </a>
    <a class="func-card" href="延期任务.html">
        <div class="card-icon-large">🚨</div><div class="card-title">延期任务</div>
        <div class="card-desc"><strong>{overdue_count}</strong> 个延期任务<br>全平台超期追踪</div>
    </a>
</div>
<div class="exec-section" id="executions">
    <h3>📊 进行中的迭代</h3>
    <table class="exec-table">
        <thead><tr><th>迭代名称</th><th>状态</th><th>时间</th></tr></thead>
        <tbody>{exec_rows}</tbody>
    </table>
</div>
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME}</div>
</div>
</body>
</html>'''
    return html

def build_main_index(fms_groups, gas_groups, fms_all, gas_all, date_dir):
    """生成主报告中心页面"""
    fms_overdue = sum(1 for t in fms_all if t.get('_overdue_days', False))
    gas_overdue = sum(1 for t in gas_all if t.get('_overdue_days', False))
    fms_total = len(fms_all)
    gas_total = len(gas_all)
    
    # FMS executions
    fms_execs = [e for eid, e in EXEC_MAP.items() if e[1] == 'FMS']
    fms_exec_rows = ''.join(f'<tr><td>{e[0]}</td><td>doing</td><td>{e[2]} ~ {e[3]}</td></tr>' for e in fms_execs)
    gas_execs = [e for eid, e in EXEC_MAP.items() if e[1] == 'GAS']
    gas_exec_rows = ''.join(f'<tr><td>{e[0]}</td><td>doing</td><td>{e[2]} ~ {e[3]}</td></tr>' for e in gas_execs)
    
    def tab_content(project, groups, all_tasks, overdue_n, total_n, exec_rows, active):
        proj_lower = project.lower()
        cat_pills = []
        for cat in ['产品', '后端', '前端', '测试', 'uiux']:
            cat_tasks = groups.get(cat, [])
            wait_n = sum(1 for t in cat_tasks if t.get('status') == 'wait')
            doing_n = sum(1 for t in cat_tasks if t.get('status') == 'doing')
            cat_display = CAT_DISPLAY[cat]
            color_cls = f'c-{cat}' if cat != 'uiux' else 'c-uiux'
            cat_pills.append(f'''<div class="stat-pill-small {color_cls}">
            <div class="num">{len(cat_tasks)}</div>
            <div class="meta"><span class="meta-icon">{CAT_ICONS[cat]}</span> {cat_display} <span style="color:#94a3b8">待{wait_n}/做{doing_n}</span></div>
        </div>''')
        
        cat_pills.append(f'''<div class="stat-pill-small c-overdue">
            <div class="num">{overdue_n}</div>
            <div class="meta"><span class="meta-icon">🚨</span> 延期任务 <span style="color:#94a3b8">共{total_n}个</span></div>
        </div>''')
        
        feat_cards = []
        for cat in ['产品', '后端', '前端', 'uiux']:
            cat_tasks = groups.get(cat, [])
            wait_n = sum(1 for t in cat_tasks if t.get('status') == 'wait')
            doing_n = sum(1 for t in cat_tasks if t.get('status') == 'doing')
            people = len(set(t.get('assignedToRealName','') for t in cat_tasks if t.get('assignedToRealName')))
            cat_display = CAT_DISPLAY[cat]
            cat_safe = CAT_NAMES[cat]
            subtitles = {'产品': '需求 / AB 类型', '后端': '开发任务', '前端': '开发任务', 'uiux': '设计任务'}
            feat_cards.append(f'''<a class="feature-card" href="{proj_lower}/{date_dir}/{cat_safe}_详细任务.html">
            <div class="card-icon-large">{CAT_ICONS[cat]}</div>
            <div class="card-title">{cat_display}任务</div>
            <div class="card-subtitle">{subtitles.get(cat, '')}</div>
            <div class="card-count"><strong>{len(cat_tasks)}</strong> 个未完成 · <strong>{people}</strong> 人</div>
        </a>''')
        
        test_tasks = groups.get('测试', [])
        test_people = len(set(t.get('assignedToRealName','') for t in test_tasks if t.get('assignedToRealName')))
        proj_lower = project.lower()
        
        # Count executions for this project
        proj_exec_count = sum(1 for eid, e in EXEC_MAP.items() if e[1] == project)
        
        return f'''<div class="tab-content {'active' if active else ''}" id="tab-{project}">
<div class="header" style="margin-bottom:24px"><h1 style="font-size:24px">{project}</h1></div>
<div class="stat-pills-row">{''.join(cat_pills)}</div>
<div class="feature-cards-row">{''.join(feat_cards)}</div>
<div class="func-cards-row">
    <a class="func-card c-test" href="{proj_lower}/{date_dir}/测试_详细任务.html">
        <div class="card-icon-large">🧪</div><div class="card-title">测试任务</div>
        <div class="card-desc">测试执行 + 测试设计<br><strong>{len(test_tasks)}</strong> 个未完成 · <strong>{test_people}</strong> 人</div>
    </a>
    <a class="func-card c-progress" href="{proj_lower}/index.html#executions">
        <div class="card-icon-large">📊</div><div class="card-title">迭代执行进展</div>
        <div class="card-desc"><strong>{len(exec_rows.split('<tr>'))-1}</strong> 个进行中迭代<br>报告总览</div>
    </a>
    <a class="func-card c-overdue" href="{proj_lower}/延期任务.html">
        <div class="card-icon-large">🚨</div><div class="card-title">延期任务</div>
        <div class="card-desc"><strong>{overdue_n}</strong> 个延期任务<br>全平台超期追踪</div>
    </a>
    <a class="func-card c-load" href="{proj_lower}/效率分析.html">
        <div class="card-icon-large">💪</div><div class="card-title">员工负载</div>
        <div class="card-desc">按角色分组工时分析<br>完成/进行中负载对比</div>
    </a>
</div>
<div class="exec-section" id="executions-{project}">
    <h3>📊 进行中的迭代</h3>
    <table class="exec-table">
        <thead><tr><th>迭代名称</th><th>状态</th><th>时间</th></tr></thead>
        <tbody>{exec_rows}</tbody>
    </table>
</div>
</div>'''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>禅道任务报告中心</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Noto Sans SC',sans-serif;background:radial-gradient(ellipse at center,#2d3561 0%,#1a1f3a 50%,#0f1429 100%);color:#e2e8f0;min-height:100vh}}
.container{{max-width:1000px;margin:0 auto;padding:48px 24px}}
.header{{text-align:center;margin-bottom:32px}}
.logo{{width:48px;height:48px;margin:0 auto 16px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:28px}}
.header h1{{font-size:28px;font-weight:700;color:#f8fafc;margin-bottom:6px}}
.header .subtitle{{font-size:13px;color:#94a3b8;margin-bottom:16px}}
.date-badge{{display:inline-block;background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:5px 18px;font-size:13px;font-weight:500}}
.tab-bar{{display:flex;justify-content:center;gap:8px;margin-bottom:40px}}
.tab-btn{{padding:10px 36px;border-radius:24px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:#94a3b8;cursor:pointer;font-size:15px;font-weight:600;transition:all .2s}}
.tab-btn:hover{{background:rgba(255,255,255,.08);color:#cbd5e1}}
.tab-btn.active{{background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border-color:transparent;box-shadow:0 4px 15px rgba(59,130,246,.3)}}
.tab-content{{display:none}}
.tab-content.active{{display:block}}
.stat-pills-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:40px}}
.stat-pill-small{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:16px 8px;text-align:center;backdrop-filter:blur(10px);transition:all .2s}}
.stat-pill-small:hover{{background:rgba(255,255,255,.07)}}
.stat-pill-small .num{{font-size:26px;font-weight:700;margin-bottom:8px}}
.stat-pill-small .meta{{font-size:11px;color:#94a3b8;display:flex;align-items:center;justify-content:center;gap:4px}}
.stat-pill-small.c-产品 .num{{color:#a78bfa}}
.stat-pill-small.c-后端 .num{{color:#4ade80}}
.stat-pill-small.c-前端 .num{{color:#f472b6}}
.stat-pill-small.c-uiux .num{{color:#38bdf8}}
.stat-pill-small.c-测试 .num{{color:#fbbf24}}
.stat-pill-small.c-overdue .num{{color:#f87171}}
.feature-cards-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.feature-card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:32px 20px 28px;text-align:center;transition:all .2s ease;backdrop-filter:blur(10px);display:block;text-decoration:none;color:#e2e8f0}}
.feature-card:hover{{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.15);transform:translateY(-3px)}}
.feature-card .card-icon-large{{width:56px;height:56px;margin:0 auto 16px;background:rgba(255,255,255,.05);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:32px}}
.feature-card .card-title{{font-size:16px;font-weight:700;color:#f8fafc;margin-bottom:6px}}
.feature-card .card-subtitle{{font-size:12px;color:#64748b;margin-bottom:12px}}
.feature-card .card-count{{font-size:13px;color:#94a3b8}}
.feature-card .card-count strong{{color:#cbd5e1;font-weight:600}}
.func-cards-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:40px}}
.func-card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:28px 16px 24px;text-align:center;transition:all .2s ease;backdrop-filter:blur(10px);display:block;text-decoration:none;color:#e2e8f0}}
.func-card:hover{{background:rgba(255,255,255,.06);border-color:rgba(255,255,255,.15);transform:translateY(-3px)}}
.func-card .card-icon-large{{width:48px;height:48px;margin:0 auto 14px;background:rgba(255,255,255,.05);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:28px}}
.func-card .card-title{{font-size:15px;font-weight:700;margin-bottom:6px}}
.func-card .card-desc{{font-size:12px;color:#64748b;line-height:1.5}}
.exec-section{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:24px;margin-bottom:40px;backdrop-filter:blur(10px)}}
.exec-section h3{{font-size:16px;color:#f8fafc;margin-bottom:16px}}
.exec-table{{width:100%;border-collapse:collapse;font-size:13px;color:#cbd5e1}}
.exec-table th{{color:#94a3b8;text-align:left;padding:8px;border-bottom:1px solid rgba(255,255,255,.08)}}
.exec-table td{{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.04)}}
.exec-table tr:hover td{{background:rgba(255,255,255,.03)}}
.history-section{{text-align:center;margin:40px 0 20px}}
.history-section h3{{font-size:15px;color:#94a3b8;margin-bottom:14px}}
.history-dates{{display:flex;flex-wrap:wrap;justify-content:center;gap:10px}}
.date-tag{{background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);color:#60a5fa;border-radius:20px;padding:6px 16px;font-size:12px;text-decoration:none}}
.date-tag:hover{{background:rgba(59,130,246,.18)}}
.date-tag.current{{background:rgba(59,130,246,.22);border-color:rgba(59,130,246,.4);color:#93c5fd}}
.footer{{text-align:center;padding:20px 0}}
.footer-text{{color:#475569;font-size:12px}}
.footer-text a{{color:#60a5fa;text-decoration:none}}
@keyframes pulse {{ 0%,100% {{opacity:1}} 50% {{opacity:0.6}} }}
.pulse {{ animation: pulse 2s infinite }}
@media(max-width:1000px){{.stat-pills-row{{grid-template-columns:repeat(3,1fr)}}.feature-cards-row{{grid-template-columns:repeat(2,1fr)}}.func-cards-row{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:600px){{.stat-pills-row{{grid-template-columns:repeat(2,1fr)}}.feature-cards-row{{grid-template-columns:1fr}}.func-cards-row{{grid-template-columns:1fr}}}}
.stale-warning{{text-align:center;margin-bottom:8px;font-size:12px;color:#f87171}}
</style>
<script>
function switchTab(key){{document.querySelectorAll(".tab-btn").forEach(b=>b.classList.remove("active"));document.querySelectorAll(".tab-content").forEach(c=>c.classList.remove("active"));event.target.classList.add("active");document.getElementById("tab-"+key).classList.add("active")}}
</script>
</head>
<body>
<div class="container">
<div class="header"><div class="logo">📊</div><h1>禅道任务报告中心</h1><p class="subtitle">Zentao Task Dashboard</p><div class="date-badge">数据更新：{TODAY_DATETIME}</div></div>

<div class="tab-bar">
    <button class="tab-btn active" onclick="switchTab('FMS')">FMS - 销售财务中台 FMS</button>
    <button class="tab-btn" onclick="switchTab('GAS')">GAS - 格力海外售后 GAS</button>
</div>

{tab_content('FMS', fms_groups, fms_all, fms_overdue, fms_total, fms_exec_rows, True)}
{tab_content('GAS', gas_groups, gas_all, gas_overdue, gas_total, gas_exec_rows, False)}

<div class="history-section">
    <h3>📅 历史报告</h3>
    <div class="history-dates">
        <a class="date-tag current" href="fms/{date_dir}/产品_详细任务.html">{date_dir}</a>
    </div>
</div>

<div class="footer">
    <div class="footer-text">数据来源：禅道管理系统 | 自动生成于 {TODAY_DATETIME}</div>
</div>
</div>
</body>
</html>'''
    return html

def main():
    print("加载任务数据...")
    all_tasks = load_tasks()
    print(f"共加载 {len(all_tasks)} 个任务")
    
    # Split by project
    fms_tasks = [t for t in all_tasks if t['_project'] == 'FMS']
    gas_tasks = [t for t in all_tasks if t['_project'] == 'GAS']
    
    # Get today's date dir
    date_dir = TODAY_STR
    
    for project, tasks in [('FMS', fms_tasks), ('GAS', gas_tasks)]:
        groups, undone = categorize(tasks)
        
        # Count overdue first to set on tasks
        for t in undone:
            deadline = t.get('deadline', '') or ''
            status = t.get('status', '')
            if deadline and status in ('wait', 'doing'):
                try:
                    dl = datetime.strptime(deadline, '%Y-%m-%d').date()
                    if dl < TODAY.date():
                        t['_overdue_days'] = (TODAY.date() - dl).days
                except: pass
        
        proj_lower = project.lower()
        detail_dir = os.path.join(BUILD_DIR, proj_lower, date_dir)
        os.makedirs(detail_dir, exist_ok=True)
        
        print(f"\n=== {project} ===")
        for cat in ['产品', '后端', '前端', '测试', 'uiux']:
            cat_tasks = sorted(groups.get(cat, []), key=lambda x: (x.get('status','') != 'doing', x.get('deadline','') or '9999'))
            cat_name = CAT_NAMES[cat]
            html = build_detail_page(project, cat, cat_tasks, f'../../{proj_lower}/{date_dir}')
            fp = os.path.join(detail_dir, f'{cat_name}_详细任务.html')
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(html)
            print(f"  {cat_name}: {len(cat_tasks)} 个未完成 → {fp}")
        
        # Overdue page
        overdue_html, overdue_n = build_overdue_page(project, undone)
        fp = os.path.join(BUILD_DIR, proj_lower, '延期任务.html')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(overdue_html)
        print(f"  延期任务: {overdue_n} → {fp}")
        
        # Workload page
        wl_html = build_workload_page(project, groups, tasks)
        fp = os.path.join(BUILD_DIR, proj_lower, '效率分析.html')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(wl_html)
        print(f"  效率分析 → {fp}")
        
        # Project overview
        proj_html = build_project_page(project, groups, undone, date_dir)
        fp = os.path.join(BUILD_DIR, proj_lower, 'index.html')
        with open(fp, 'w', encoding='utf-8') as f:
            f.write(proj_html)
        print(f"  项目总览 → {fp}")
    
    # Main index
    fms_groups, fms_undone = categorize(fms_tasks)
    gas_groups, gas_undone = categorize(gas_tasks)
    for t in fms_undone + gas_undone:
        deadline = t.get('deadline', '') or ''
        if deadline and t.get('status') in ('wait', 'doing'):
            try:
                dl = datetime.strptime(deadline, '%Y-%m-%d').date()
                if dl < TODAY.date():
                    t['_overdue_days'] = (TODAY.date() - dl).days
            except: pass
    
    main_html = build_main_index(fms_groups, gas_groups, fms_undone, gas_undone, date_dir)
    fp = os.path.join(BUILD_DIR, 'index.html')
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(main_html)
    print(f"\n主报告中心 → {fp}")
    print("\n完成！")

if __name__ == '__main__':
    main()
