#!/usr/bin/env python3
"""禅道任务报告中心 - 完整版生成器（含趋势、项目汇报、历史记录、Chart.js图表）"""
import json, os, hashlib
from datetime import datetime, date
from collections import defaultdict, Counter

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BUILD_DIR = os.path.join(PROJECT_DIR, 'build')
TODAY = datetime.now()
TODAY_STR = TODAY.strftime('%Y-%m-%d')
TODAY_DATETIME = TODAY.strftime('%Y-%m-%d %H:%M')

CAT_MAP = {
    '需求设计': '产品', '需求调研': '产品',
    'ab1_needs_research': '产品', 'ab2_request_des': '产品', 'ab3_request_check': '产品',
    'a_dev': '后端', 'a_dev4_control': '后端', 'Dev_Ops': '后端',
    'a_dev2_front': '前端',
    'ad1_UI_des': 'uiux',
    'ae2_test': '测试',
}

CAT_SAFE = {'产品': '产品', '后端': '后端', '前端': '前端', '测试': '测试', 'uiux': 'UI_UX'}
CAT_DISPLAY = {'产品': '产品', '后端': '后端', '前端': '前端', '测试': '测试', 'uiux': 'UI/UX'}
CAT_ICONS = {'产品': '📋', '后端': '⚙️', '前端': '🎨', '测试': '🧪', 'uiux': '🖌️'}

EXEC_MAP = {
    4519: ('【2026】FMS-0630', 'FMS', '2026-04-30', '2026-06-30'),
    4562: ('【2026】FMS-0615', 'FMS', '2026-05-14', '2026-06-15'),
    4651: ('【2026】FMS-0715', 'FMS', '2026-06-15', '2026-07-15'),
    4527: ('【2026】海外售后服务器迁移-0630', 'GAS', '2026-04-20', '2026-06-30'),
    4639: ('【2026】海外售后v4.5-0630', 'GAS', '2026-06-11', '2026-06-30'),
}

# 颜色调色板
AVATAR_COLORS = ['#667eea','#f093fb','#4facfe','#43e97b','#ffa726','#f5576c','#7c3aed','#ec4899','#06b6d4','#84cc16','#f59e0b','#ef4444','#8b5cf6','#d946ef','#0891b2','#a3e635','#d97706','#dc2626']

HIST_TOTALS = {
    'FMS': {
        '2026-06-18': {'产品':168,'后端':309,'前端':69,'测试':125,'uiux':89,'total':760},
        '2026-06-17': {'产品':168,'后端':310,'前端':65,'测试':126,'uiux':91,'total':760},
        '2026-06-12': {'产品':167,'后端':288,'前端':62,'测试':107,'uiux':85,'total':709},
        '2026-06-11': {'产品':187,'后端':736,'前端':215,'测试':367,'uiux':208,'total':1713},
        '2026-06-05': {'产品':143,'后端':634,'前端':195,'测试':325,'uiux':187,'total':1484},
    },
    'GAS': {
        '2026-06-18': {'产品':0,'后端':5,'前端':31,'测试':35,'uiux':28,'total':126},
        '2026-06-17': {'产品':0,'后端':53,'前端':13,'测试':52,'uiux':8,'total':126},
        '2026-06-12': {'产品':0,'后端':54,'前端':13,'测试':50,'uiux':6,'total':123},
        '2026-06-11': {'产品':3,'后端':78,'前端':24,'测试':55,'uiux':42,'total':233},
        '2026-06-05': {'产品':3,'后端':78,'前端':50,'测试':56,'uiux':42,'total':220},
    },
}

def load_tasks():
    all_tasks = []
    for eid in EXEC_MAP:
        fp = f'/tmp/tasks_{eid}.json'
        if os.path.exists(fp):
            with open(fp) as f: data = json.load(f)
            for t in data.get('tasks', []):
                t['_exec_name'] = EXEC_MAP[eid][0]
                t['_project'] = EXEC_MAP[eid][1]
                t['_exec_begin'] = EXEC_MAP[eid][2]
                t['_exec_end'] = EXEC_MAP[eid][3]
                t['_category'] = CAT_MAP.get(t.get('type',''), '其他')
            all_tasks.extend(data.get('tasks', []))
    return all_tasks

def categorize_undone(tasks):
    undone = [t for t in tasks if t.get('status') not in ('done','closed','cancel')]
    groups = defaultdict(list)
    for t in undone: groups[t['_category']].append(t)
    return dict(groups), undone

def count_overdue(tasks):
    n = 0
    for t in tasks:
        dl = t.get('deadline','') or ''
        if dl and t.get('status') in ('wait','doing'):
            try:
                if datetime.strptime(dl,'%Y-%m-%d').date() < TODAY.date():
                    t['_overdue_days'] = (TODAY.date() - datetime.strptime(dl,'%Y-%m-%d').date()).days
                    n += 1
            except: pass
    return n

def esc(s):
    if s is None: return ''
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;').replace("'","&#39;")

def fmt_h(val):
    try:
        v = float(val); return f'{v:.0f}h'
    except: return '0h'

def pri_cls(pri):
    return {'1':'pri-urgent','2':'pri-high','3':'pri-medium','4':'pri-low'}.get(str(pri),'pri-medium')

def pri_text(pri):
    return {'1':'1-紧急','2':'2-高','3':'3-中','4':'4-低'}.get(str(pri), str(pri))

# ─── 详情页（完全匹配6/18旧版样式） ──────────────────────────────────

def build_detail_page(project, cat, tasks, date_dir):
    """按6/18旧版格式生成详情页：5 KPI卡片 + Chart.js 3图表 + 人员卡片折叠"""
    cat_safe = CAT_SAFE[cat]; cat_display = CAT_DISPLAY[cat]; icon = CAT_ICONS[cat]
    
    # Stats
    total = len(tasks)
    wait_n = sum(1 for t in tasks if t.get('status')=='wait')
    doing_n = sum(1 for t in tasks if t.get('status')=='doing')
    overdue_n = sum(1 for t in tasks if t.get('_overdue_days', False))
    people = sorted(set(t.get('assignedToRealName','') or '' for t in tasks if t.get('assignedToRealName')))
    n_people = len(people)
    
    # Type breakdown for meta tag
    type_counts = Counter(t.get('type','') for t in tasks)
    type_parts = ' · '.join(f'{k}({v})' for k,v in sorted(type_counts.items(), key=lambda x:-x[1]))
    
    # Chart data: top10 by person
    person_counts = Counter(t.get('assignedToRealName','') or '未分配' for t in tasks)
    top10 = person_counts.most_common(10)
    bar_labels = json.dumps([p[0] for p in top10])
    bar_data = json.dumps([p[1] for p in top10])
    
    # Status pie
    pie_status = json.dumps({'待处理': wait_n, '进行中': doing_n})
    
    # Priority pie
    pri_counts = Counter(t.get('pri','') for t in tasks)
    pri_labels_map = {'1':'紧急','2':'高','3':'中','4':'低'}
    pri_pie_labels = json.dumps([pri_labels_map.get(k,k) for k in ['1','2','3','4'] if pri_counts.get(k)])
    pri_pie_data = json.dumps([pri_counts.get(k,0) for k in ['1','2','3','4'] if pri_counts.get(k)])
    
    # Person cards
    person_groups = defaultdict(list)
    for t in tasks:
        name = t.get('assignedToRealName','') or '未分配'
        person_groups[name].append(t)
    
    person_cards = []
    for idx, (name, ptasks) in enumerate(sorted(person_groups.items(), key=lambda x: -len(x[1]))):
        pwait = sum(1 for t in ptasks if t.get('status')=='wait')
        pdoing = sum(1 for t in ptasks if t.get('status')=='doing')
        poverdue = sum(1 for t in ptasks if t.get('_overdue_days', False))
        pest = sum(float(t.get('estimate',0) or 0) for t in ptasks)
        pleft = sum(float(t.get('left',0) or 0) for t in ptasks)
        pcons = sum(float(t.get('consumed',0) or 0) for t in ptasks)
        ptotal_pct = pwait+pdoing
        wait_pct = (pwait/max(ptotal_pct,1))*100
        doing_pct = (pdoing/max(ptotal_pct,1))*100
        
        avatar_color = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        surname = name[0] if name != '未分配' else '?'
        
        subtext = f'共{len(ptasks)}个任务'
        subtext += f'<span class="mini-bar"><span class="mb-wait" style="width:{wait_pct:.0f}%"></span><span class="mb-doing" style="width:{doing_pct:.0f}%"></span></span>待{pwait} 做{pdoing}'
        if poverdue: subtext += f' 延期{poverdue}'
        
        # Table rows
        trows = []
        for t in sorted(ptasks, key=lambda x: (x.get('status','')!='doing', x.get('deadline','') or '9999')):
            tid = t.get('id',''); tname = t.get('name','')
            status = t.get('status',''); ddl = t.get('deadline','') or ''
            ttype = t.get('type',''); exec_name = t.get('_exec_name','')
            is_overdue = bool(t.get('_overdue_days', False))
            overdue_days = t.get('_overdue_days', 0)
            
            if status == 'wait':
                sbadge = f'<span class="badge-wait"><span class="status-dot wait"></span>待处理</span>'
            elif status == 'doing':
                sbadge = f'<span class="badge-doing"><span class="status-dot doing"></span>进行中</span>'
            else:
                sbadge = f'<span class="badge-pause">{status}</span>'
            
            pri = t.get('pri',''); pcls = pri_cls(pri); ptxt = pri_text(pri)
            est = fmt_h(t.get('estimate',0)); cons = fmt_h(t.get('consumed',0)); left = fmt_h(t.get('left',0))
            
            row_cls = ' class="row-overdue"' if is_overdue else ''
            od_text = f'{overdue_days}天' if overdue_days > 0 else ''
            
            trows.append(f'<tr{row_cls}><td class="col-id">{tid}</td><td class="col-name" title="{esc(tname)}">{esc(tname[:50])}{"…" if len(tname)>50 else ""}</td><td>{sbadge}</td><td><span class="pri-tag {pcls}">{ptxt}</span></td><td>{ttype}</td><td class="col-name" title="{esc(exec_name)}">{esc(exec_name[:20])}</td><td class="col-date">{ddl}</td><td class="col-overdue">{od_text}</td><td class="col-num">{est}</td><td class="col-num">{cons}</td><td class="col-num">{left}</td></tr>')
        
        person_cards.append(f'''<details class="person-card" open>
<summary><div class="person-avatar" style="background:{avatar_color}">{surname}</div>
<div class="person-info"><span class="person-name">{esc(name)}</span><span class="person-subtitle">{subtext}</span></div>
<div class="person-stats-right"><div class="person-stat ps-wait"><div class="ps-num">{pwait}</div><div class="ps-label">待处理</div></div><div class="person-stat ps-doing"><div class="ps-num">{pdoing}</div><div class="ps-label">进行中</div></div><div class="person-stat ps-est"><div class="ps-num">{pest:.0f}h</div><div class="ps-label">预估</div></div><div class="person-stat"><div class="ps-num" style="color:#9ca3af">{pleft:.0f}h</div><div class="ps-label">剩余</div></div><div class="expand-arrow"><svg viewBox="0 0 24 24"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6z"/></svg></div></div>
</summary><div class="table-wrapper"><table><thead><tr><th class="col-id">ID</th><th class="col-name">任务名称</th><th>状态</th><th>优先级</th><th>类型</th><th class="col-name">执行</th><th class="col-date">截止日期</th><th class="col-overdue">延期</th><th class="col-num">预估h</th><th class="col-num">消耗h</th><th class="col-num">剩余h</th></tr></thead><tbody>{"".join(trows)}</tbody></table></div></details>''')
    
    proj_full = '销售财务中台 FMS' if project=='FMS' else '格力海外售后 GAS'
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>未完成{cat_display}任务明细 - {proj_full}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:'Inter','SF Pro Display','PingFang SC','Microsoft YaHei',-apple-system,sans-serif;background:linear-gradient(135deg,#f5f7fa 0%,#e8ecf1 100%);color:#1a1f36;padding:24px;min-height:100vh}}
.header{{text-align:center;padding:32px 0 24px}}.header h1{{font-size:26px;font-weight:800;color:#1a1f36;letter-spacing:-0.5px}}.header h1 .icon{{font-size:28px;margin-right:8px}}.header p{{color:#6b7280;margin-top:6px;font-size:13px;letter-spacing:0.1px}}
.header .meta-tags{{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-top:10px}}.header .meta-tag{{display:inline-flex;align-items:center;gap:4px;font-size:12px;padding:4px 12px;border-radius:20px;background:#fff;color:#6b7280;border:1px solid #e5e7eb}}
.kpi-section{{margin-bottom:28px}}.kpi-section .section-label{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#9ca3af;margin-bottom:12px;font-weight:600}}
.cards{{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}}.card{{background:#fff;border-radius:14px;padding:20px 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03);transition:transform .2s,box-shadow .2s;position:relative;overflow:hidden}}.card::before{{content:"";position:absolute;top:0;left:0;right:0;height:3px}}.card:hover{{transform:translateY(-2px);box-shadow:0 4px 16px rgba(0,0,0,.08)}}.card .card-icon{{font-size:24px;margin-bottom:6px;display:block}}.card .num{{font-size:32px;font-weight:800;letter-spacing:-1px;line-height:1.1}}.card .label{{font-size:12px;color:#9ca3af;margin-top:4px;font-weight:500}}
.card-total::before{{background:linear-gradient(90deg,#667eea,#764ba2)}}.card-total .num{{color:#667eea}}
.card-wait::before{{background:linear-gradient(90deg,#f5576c,#f093fb)}}.card-wait .num{{color:#f5576c}}
.card-doing::before{{background:linear-gradient(90deg,#43e97b,#38f9d7)}}.card-doing .num{{color:#2e7d32}}
.card-overdue::before{{background:linear-gradient(90deg,#ffa726,#ff7043)}}.card-overdue .num{{color:#e65100}}
.card-people::before{{background:linear-gradient(90deg,#4facfe,#00f2fe)}}.card-people .num{{color:#1565c0}}
.charts-section{{margin-bottom:32px}}.charts-section .section-label{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#9ca3af;margin-bottom:12px;font-weight:600}}
.charts{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}}.chart-box{{background:#fff;border-radius:14px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03)}}.chart-box h3{{font-size:13px;font-weight:700;color:#374151;margin-bottom:14px;text-align:center}}.chart-container{{position:relative;height:280px}}.chart-container canvas{{max-height:280px}}
.detail-section{{margin-bottom:24px}}.detail-section .section-label{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:#9ca3af;margin-bottom:14px;font-weight:600}}
.person-card{{background:#fff;border-radius:14px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03);overflow:hidden;transition:box-shadow .25s}}.person-card:hover{{box-shadow:0 4px 20px rgba(0,0,0,.08)}}.person-card summary{{display:flex;align-items:center;gap:14px;padding:16px 20px;cursor:pointer;font-weight:600;user-select:none;list-style:none;transition:background .2s}}.person-card summary::-webkit-details-marker,.person-card summary::marker{{display:none;content:""}}.person-card summary:hover{{background:#f9fafb}}
.person-avatar{{width:42px;height:42px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:#fff;flex-shrink:0;letter-spacing:0.5px}}
.person-info{{flex:1;min-width:0}}.person-name{{font-size:15px;font-weight:700;color:#1a1f36;display:block}}.person-subtitle{{font-size:11px;color:#9ca3af;margin-top:1px;display:flex;align-items:center;gap:6px}}
.mini-bar{{display:inline-flex;height:4px;border-radius:2px;overflow:hidden;background:#f3f4f6;width:80px;vertical-align:middle;margin:0 4px}}.mini-bar .mb-wait{{background:#f5576c}}.mini-bar .mb-doing{{background:#43e97b}}
.person-stats-right{{display:flex;align-items:center;gap:16px;flex-shrink:0}}.person-stat{{text-align:center}}.person-stat .ps-num{{font-size:18px;font-weight:800;line-height:1;letter-spacing:-0.5px}}.person-stat .ps-label{{font-size:10px;color:#9ca3af;margin-top:2px;text-transform:uppercase;letter-spacing:0.5px}}
.person-stat.ps-wait .ps-num{{color:#f5576c}}.person-stat.ps-doing .ps-num{{color:#2e7d32}}.person-stat.ps-est .ps-num{{color:#6366f1}}
.expand-arrow{{width:28px;height:28px;border-radius:50%;background:#f3f4f6;display:flex;align-items:center;justify-content:center;transition:transform .3s;flex-shrink:0}}.person-card[open] .expand-arrow{{transform:rotate(180deg);background:#e0e7ff}}.expand-arrow svg{{width:14px;height:14px;fill:#6b7280;transition:fill .3s}}.person-card[open] .expand-arrow svg{{fill:#6366f1}}
.table-wrapper{{overflow-x:auto;padding:0 20px 20px;border-top:1px solid #f3f4f6;margin-top:8px;padding-top:14px}}table{{width:100%;border-collapse:collapse;font-size:12px}}thead th{{background:#f9fafb;padding:10px 8px;text-align:left;font-weight:700;white-space:nowrap;color:#4b5563;font-size:11px;text-transform:uppercase;letter-spacing:0.3px;border-bottom:2px solid #e5e7eb}}thead th:first-child{{border-radius:8px 0 0 0}}thead th:last-child{{border-radius:0 8px 0 0}}
tbody td{{padding:10px 8px;border-bottom:1px solid #f3f4f6;white-space:nowrap;color:#374151}}tbody tr:nth-child(even){{background:#fafbfc}}tbody tr:hover{{background:#f0f4ff}}
.status-dot{{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:5px;vertical-align:middle}}.status-dot.wait{{background:#f5576c;box-shadow:0 0 0 2px rgba(245,87,108,.2)}}.status-dot.doing{{background:#43e97b;box-shadow:0 0 0 2px rgba(67,233,123,.2)}}
.badge-wait{{display:inline-flex;align-items:center;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:600;background:#fef2f2;color:#dc2626}}.badge-doing{{display:inline-flex;align-items:center;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:600;background:#f0fdf4;color:#16a34a}}.badge-pause{{display:inline-flex;align-items:center;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:600;background:#f5f5f5;color:#737373}}
tr.row-overdue{{background:#fef2f2!important}}tr.row-overdue td:first-child{{border-left:3px solid #ef4444}}tr.row-overdue:hover{{background:#fee2e2!important}}tr.row-overdue:nth-child(even){{background:#fff5f5!important}}
.pri-tag{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:11px;font-weight:600;letter-spacing:0.3px}}.pri-urgent{{background:#fef2f2;color:#dc2626}}.pri-high{{background:#fff7ed;color:#ea580c}}.pri-medium{{background:#eff6ff;color:#2563eb}}.pri-low{{background:#f9fafb;color:#9ca3af}}
.col-id{{width:62px;font-family:"SF Mono","Consolas",monospace;font-size:11px;color:#9ca3af}}.col-name{{max-width:320px;overflow:hidden;text-overflow:ellipsis}}.col-date{{width:95px}}.col-num{{width:62px;text-align:right}}.col-overdue{{color:#ef4444;font-weight:700;width:60px;text-align:center}}
.back-link{{text-align:center;margin-bottom:20px}}.back-link a{{color:#6366f1;text-decoration:none;font-size:13px;font-weight:500;padding:7px 18px;border-radius:20px;background:#fff;border:1px solid #e5e7eb;display:inline-flex;align-items:center;gap:4px;transition:all .2s}}.back-link a:hover{{background:#6366f1;color:#fff;border-color:#6366f1}}
.empty-msg{{text-align:center;padding:80px 0;color:#9ca3af;font-size:15px}}
.footer{{text-align:center;color:#9ca3af;font-size:12px;padding:28px 0 8px}}
@media(max-width:900px){{.cards{{grid-template-columns:repeat(3,1fr)}}.charts{{grid-template-columns:1fr 1fr}}}}
@media(max-width:768px){{body{{padding:14px}}.header h1{{font-size:20px}}.cards{{grid-template-columns:repeat(2,1fr);gap:8px}}.card{{padding:14px 10px}}.card .num{{font-size:24px}}.charts{{grid-template-columns:1fr}}.chart-container{{height:220px}}.person-card summary{{padding:12px 14px;gap:10px}}.person-avatar{{width:34px;height:34px;font-size:14px}}.person-name{{font-size:14px}}.person-stats-right{{gap:10px}}.person-stat .ps-num{{font-size:15px}}table{{font-size:10px}}thead th{{padding:7px 5px;font-size:10px}}tbody td{{padding:7px 5px}}.badge-wait,.badge-doing,.badge-pause{{font-size:10px;padding:1px 6px}}.pri-tag{{font-size:10px;padding:1px 6px}}.col-id{{width:48px}}.col-date{{width:78px}}.col-num{{width:48px}}.col-overdue{{width:50px}}.col-name{{max-width:180px}}}}
@media(max-width:480px){{body{{padding:8px}}.header h1{{font-size:18px}}.header p{{font-size:11px}}.cards{{grid-template-columns:repeat(2,1fr);gap:6px}}.card{{padding:10px 6px;border-radius:10px}}.card .num{{font-size:20px}}.card .label{{font-size:10px}}.card .card-icon{{font-size:18px}}.charts{{gap:10px}}.chart-box{{padding:12px}}.chart-box h3{{font-size:12px}}.chart-container{{height:180px}}.person-card summary{{padding:10px 12px;gap:8px}}.person-avatar{{width:28px;height:28px;font-size:12px}}.person-name{{font-size:13px}}.person-stats-right{{gap:6px}}.person-stat .ps-num{{font-size:13px}}.ps-label{{font-size:9px}}.expand-arrow{{width:22px;height:22px}}.expand-arrow svg{{width:11px;height:11px}}.table-wrapper{{padding:0 10px 10px;margin-top:4px;padding-top:8px}}table{{font-size:9px}}thead th{{padding:5px 3px;font-size:9px}}tbody td{{padding:5px 3px}}.badge-wait,.badge-doing,.badge-pause{{font-size:9px;padding:0 4px}}.pri-tag{{font-size:9px;padding:0 5px}}.col-id{{width:36px}}.col-date{{width:62px}}.col-num{{width:38px}}.col-overdue{{width:40px}}.col-name{{max-width:110px}}}}</style></head><body>
<div class="header"><h1><span class="icon">{icon}</span>未完成{cat_display}任务明细</h1><p>统计日期: {TODAY_STR}</p><div class="meta-tags"><span class="meta-tag">📊 总计 {total} 个未完成任务</span><span class="meta-tag">👥 涉及 {n_people} 人</span><span class="meta-tag">📁 {type_parts}</span></div></div>
<div class="back-link"><a href="../index.html">← 返回报告中心</a></div>
<div class="kpi-section"><div class="section-label">📈 数据概览</div><div class="cards"><div class="card card-total"><span class="card-icon">📊</span><div class="num">{total}</div><div class="label">任务总数</div></div><div class="card card-wait"><span class="card-icon">⏳</span><div class="num">{wait_n}</div><div class="label">待处理</div></div><div class="card card-doing"><span class="card-icon">🔄</span><div class="num">{doing_n}</div><div class="label">进行中</div></div><div class="card card-overdue"><span class="card-icon">⚠️</span><div class="num">{overdue_n}</div><div class="label">延期</div></div><div class="card card-people"><span class="card-icon">👤</span><div class="num">{n_people}</div><div class="label">负责人</div></div></div></div>
<div class="charts-section"><div class="section-label">📊 可视化分析</div><div class="charts"><div class="chart-box"><h3>📋 负责人任务分布 (Top10)</h3><div class="chart-container"><canvas id="barChart"></canvas></div></div><div class="chart-box"><h3>🔄 任务状态分布</h3><div class="chart-container"><canvas id="statusPie"></canvas></div></div><div class="chart-box"><h3>🎯 优先级分布</h3><div class="chart-container"><canvas id="priPie"></canvas></div></div></div></div>
<div class="detail-section"><div class="section-label">👥 按负责人明细（点击展开/折叠）</div>
{"".join(person_cards)}</div>
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME} | 仅显示未完成任务</div>
<script>
new Chart(document.getElementById('barChart'),{{type:'bar',data:{{labels:{bar_labels},datasets:[{{label:'任务数',data:{bar_data},backgroundColor:'rgba(99,102,241,.7)',borderRadius:6}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}}}}}});
new Chart(document.getElementById('statusPie'),{{type:'doughnut',data:{{labels:['待处理','进行中'],datasets:[{{data:[{wait_n},{doing_n}],backgroundColor:['#f5576c','#43e97b'],borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}}}}}});
new Chart(document.getElementById('priPie'),{{type:'doughnut',data:{{labels:{pri_pie_labels},datasets:[{{data:{pri_pie_data},backgroundColor:['#ef4444','#f59e0b','#3b82f6','#9ca3af'],borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}}}}}});
</script></body></html>'''

# ─── 其他页面 ──────────────────────────────────────────────────────

# ─── 延期任务（6/18旧版样式） ─────────────────────────────────────

def build_overdue_page(project, tasks):
    overdue = [t for t in tasks if t.get('_overdue_days', False)]
    overdue.sort(key=lambda x: -x['_overdue_days'])
    proj_full = '销售财务中台 FMS' if project=='FMS' else '格力海外售后 GAS'
    total = len(overdue); wait_n = sum(1 for t in overdue if t.get('status')=='wait')
    doing_n = sum(1 for t in overdue if t.get('status')=='doing')
    people = len(set(t.get('assignedToRealName','') for t in overdue if t.get('assignedToRealName')))
    
    # Chart data
    pcounts = Counter(t.get('assignedToRealName','') or '未分配' for t in overdue)
    pnames = json.dumps([n for n,_ in pcounts.most_common(10)])
    pdata = json.dumps([c for _,c in pcounts.most_common(10)])
    pcolors = json.dumps([AVATAR_COLORS[i%len(AVATAR_COLORS)]+'80' for i in range(min(len(pcounts),10))])
    
    # Person groups
    pgroups = defaultdict(list)
    for t in overdue: pgroups[t.get('assignedToRealName','') or '未分配'].append(t)
    
    person_cards = []
    for idx, (name, pt) in enumerate(sorted(pgroups.items(), key=lambda x: -len(x[1]))):
        pwait = sum(1 for t in pt if t.get('status')=='wait')
        pdoing = sum(1 for t in pt if t.get('status')=='doing')
        max_days = max((t.get('_overdue_days',0) or 0) for t in pt)
        pest = sum(float(t.get('estimate',0) or 0) for t in pt)
        pcons = sum(float(t.get('consumed',0) or 0) for t in pt)
        pleft = sum(float(t.get('left',0) or 0) for t in pt)
        color = AVATAR_COLORS[idx % len(AVATAR_COLORS)]
        trows = []
        for t in sorted(pt, key=lambda x: -x['_overdue_days']):
            tid = t.get('id',''); tn = t.get('name',''); st = t.get('status','')
            dd = t.get('deadline','') or ''; ovd = t.get('_overdue_days',0)
            typ = t.get('type',''); exn = t.get('_exec_name','')
            pr = t.get('pri',''); pcls = pri_cls(pr); ptxt = pri_text(pr)
            est_h = fmt_h(t.get('estimate',0)); con_h = fmt_h(t.get('consumed',0)); left_h = fmt_h(t.get('left',0))
            sbadge = f'<span class="badge-wait">待处理</span>' if st=='wait' else f'<span class="badge-doing">进行中</span>'
            trows.append(f'<tr class="row-overdue"><td class="col-id">{tid}</td><td class="col-name" title="{esc(tn)}">{esc(tn[:50])}{"…" if len(tn)>50 else ""}</td><td class="col-status">{sbadge}</td><td><span class="pri-tag {pcls}">{ptxt}</span></td><td>{typ}</td><td class="col-name" title="{esc(exn)}">{esc(exn[:20])}</td><td class="col-date">{dd}</td><td class="col-overdue">{ovd}天</td><td class="col-num">{est_h}</td><td class="col-num">{con_h}</td><td class="col-num">{left_h}</td></tr>')
        person_cards.append(f'<details class="person-details" open><summary style="background:{color}15;border-left:4px solid {color}"><span class="assignee-name">{esc(name)}</span><span class="assignee-stats"><span class="stat-badge">共{len(pt)}个</span><span class="stat-badge stat-wait">待处理{pwait}</span><span class="stat-badge stat-doing">进行中{pdoing}</span><span class="stat-badge stat-overdue">最长{max_days}天</span><span class="stat-badge stat-h">预估{pest:.0f}h</span><span class="stat-badge stat-h">消耗{pcons:.0f}h</span><span class="stat-badge stat-h">剩余{pleft:.0f}h</span></span></summary><div class="table-wrapper"><table class="data-table"><thead><tr><th class="col-id">ID</th><th class="col-name">任务名称</th><th class="col-status">状态</th><th>优先级</th><th>类型</th><th class="col-name">所属迭代</th><th class="col-date">截止日期</th><th class="col-overdue">超期天数</th><th class="col-num">预估h</th><th class="col-num">消耗h</th><th class="col-num">剩余h</th></tr></thead><tbody>{"".join(trows)}</tbody></table></div></details>')
    
    pri_counts = Counter(t.get('pri','') for t in overdue)
    pri_map = {'1':'1-紧急','2':'2-高','3':'3-中','4':'4-低'}
    pri_lbl = json.dumps([pri_map.get(k,k) for k in ['1','2','3','4'] if pri_counts.get(k)])
    pri_d = json.dumps([pri_counts.get(k,0) for k in ['1','2','3','4'] if pri_counts.get(k)])
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>延期任务统计报告 - {proj_full}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:"Microsoft YaHei","PingFang SC",-apple-system,BlinkMacSystemFont,sans-serif;background:#f0f2f5;color:#333;padding:20px}}.container{{max-width:1100px;margin:0 auto}}
.header{{text-align:center;padding:20px 0}}.header h1{{font-size:24px;color:#c62828}}.header .subtitle{{color:#888;margin-top:4px;font-size:13px}}.header .date-badge{{display:inline-block;margin-top:8px;font-size:12px;color:#888}}
.back-link{{text-align:center;margin-bottom:16px}}.back-link a{{color:#667eea;text-decoration:none;font-size:13px;padding:6px 16px;border-radius:16px;background:#e8ecf4;border:1px solid #d0d5e0;display:inline-block;transition:background .2s}}.back-link a:hover{{background:#d0d5e0}}
.kpi-row{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}}.kpi-card{{flex:1;min-width:120px;background:#fff;border-radius:10px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.06)}}.kpi-card .kpi-num{{font-size:28px;font-weight:700}}.kpi-card .kpi-label{{font-size:12px;color:#888;margin-top:4px}}
.kpi-card.c-total .kpi-num{{color:#ef4444}}.kpi-card.c-wait .kpi-num{{color:#f5576c}}.kpi-card.c-doing .kpi-num{{color:#43e97b}}.kpi-card.c-overdue .kpi-num{{color:#ffa726}}.kpi-card.c-people .kpi-num{{color:#4facfe}}
.charts-row{{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:20px}}.chart-box{{flex:1;min-width:320px;background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,.06)}}.chart-box h3{{font-size:14px;color:#555;margin-bottom:10px;text-align:center}}.chart-container{{position:relative;height:300px}}.chart-container canvas{{max-height:300px}}
.details-title{{font-size:14px;color:#555;margin-bottom:10px;font-weight:600}}
details.person-details{{background:#fff;border-radius:10px;margin-bottom:10px;box-shadow:0 2px 8px rgba(0,0,0,.06);overflow:hidden}}details.person-details summary{{padding:12px 16px;cursor:pointer;font-weight:600;display:flex;align-items:center;gap:8px;flex-wrap:nowrap;user-select:none;overflow-x:auto}}details.person-details summary::-webkit-details-marker{{display:none}}.assignee-name{{font-size:15px;flex-shrink:0}}.assignee-stats{{display:flex;gap:6px;flex-wrap:nowrap;margin-left:auto;flex-shrink:0}}
.stat-badge{{font-size:11px;padding:2px 8px;border-radius:10px;background:#eee;color:#555;font-weight:normal;white-space:nowrap}}.stat-badge.stat-wait{{background:#fde8e8;color:#c62828}}.stat-badge.stat-doing{{background:#e8f5e9;color:#2e7d32}}.stat-badge.stat-overdue{{background:#fff3e0;color:#e65100}}.stat-badge.stat-h{{background:#e3f2fd;color:#1565c0}}
.table-wrapper{{overflow-x:auto;padding:0 16px 16px}}table.data-table{{width:100%;border-collapse:collapse;font-size:12px}}table.data-table th{{background:#f5f6f8;padding:8px 6px;text-align:left;font-weight:600;white-space:nowrap}}table.data-table td{{padding:6px;border-bottom:1px solid #f0f0f0;white-space:nowrap}}table.data-table tr:hover td{{background:#fafbfc}}table.data-table tr.row-overdue{{background:#fff5f5}}table.data-table tr.row-overdue td:first-child{{border-left:3px solid #ef4444}}table.data-table tr.row-overdue:hover td{{background:#fee2e2}}
.badge-wait{{display:inline-block;padding:1px 6px;border-radius:8px;font-size:11px;background:#fde8e8;color:#c62828}}.badge-doing{{display:inline-block;padding:1px 6px;border-radius:8px;font-size:11px;background:#e8f5e9;color:#2e7d32}}
.pri-tag{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:11px;font-weight:500}}.pri-urgent{{background:#ffebee;color:#c62828}}.pri-high{{background:#fff3e0;color:#e65100}}.pri-medium{{background:#e3f2fd;color:#1565c0}}.pri-low{{background:#f5f5f5;color:#888}}
.col-id{{width:55px}}.col-name{{max-width:280px;overflow:hidden;text-overflow:ellipsis}}.col-date{{width:90px}}.col-num{{width:60px;text-align:right}}.col-overdue{{color:#ef4444;font-weight:700;width:75px}}.col-status{{width:60px}}
.footer{{text-align:center;color:#aaa;font-size:12px;padding:20px}}
@media(max-width:768px){{body{{padding:12px}}.header h1{{font-size:20px}}.kpi-card{{min-width:90px;padding:12px 8px}}.kpi-card .kpi-num{{font-size:22px}}.chart-box{{min-width:100%;padding:12px}}.chart-container{{height:240px}}table.data-table{{font-size:11px}}th{{padding:6px 4px}}td{{padding:5px 4px}}.badge-wait,.badge-doing{{font-size:10px;padding:1px 5px}}.stat-badge{{font-size:10px;padding:2px 6px}}.pri-tag{{font-size:10px}}summary{{padding:10px 14px;gap:6px}}.assignee-name{{font-size:14px}}.col-id{{width:48px}}.col-date{{width:80px}}.col-num{{width:50px}}.col-overdue{{width:60px}}.col-name{{max-width:180px}}}}
@media(max-width:480px){{body{{padding:8px}}.header h1{{font-size:18px}}.kpi-card{{min-width:70px;padding:10px 6px}}.kpi-card .kpi-num{{font-size:20px}}.chart-box h3{{font-size:12px}}.chart-container{{height:200px}}table.data-table{{font-size:10px}}th{{padding:5px 3px}}td{{padding:4px 3px}}.badge-wait,.badge-doing{{font-size:9px;padding:0 4px}}.stat-badge{{font-size:9px;padding:1px 4px}}.pri-tag{{font-size:9px}}summary{{padding:8px 10px;gap:5px}}.assignee-name{{font-size:13px}}.col-id{{width:40px}}.col-date{{width:70px}}.col-num{{width:40px}}.col-overdue{{width:50px}}.col-name{{max-width:120px}}}}</style>
<script>window.onload=function(){{new Chart(document.getElementById("personChart"),{{type:"bar",data:{{labels:{pnames},datasets:[{{label:"延期任务数",data:{pdata},backgroundColor:{pcolors},borderRadius:6}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},scales:{{y:{{beginAtZero:true,ticks:{{stepSize:1}}}}}}}}}});
new Chart(document.getElementById("statusChart"),{{type:"pie",data:{{labels:["待处理","进行中"],datasets:[{{data:[{wait_n},{doing_n}],backgroundColor:["#f5576c","#43e97b"]}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:"bottom"}}}}}}}});
new Chart(document.getElementById("priChart"),{{type:"pie",data:{{labels:{pri_lbl},datasets:[{{data:{pri_d},backgroundColor:["#ef4444","#ffa726","#4facfe","#94a3b8"]}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:"bottom"}}}}}}}});}}</script></head>
<body><div class="container"><div class="back-link"><a href="index.html">← 返回 {proj_full} 报告</a></div>
<div class="header"><h1>🚨 延期任务统计报告</h1><p class="subtitle">数据截止：{TODAY_STR} | 全平台延期任务追踪 | 共 {total} 个延期任务</p><div class="date-badge">更新于 {TODAY_DATETIME}</div></div>
<div class="kpi-row"><div class="kpi-card c-total"><div class="kpi-num">{total}</div><div class="kpi-label">延期任务总数</div></div><div class="kpi-card c-wait"><div class="kpi-num">{wait_n}</div><div class="kpi-label">待处理</div></div><div class="kpi-card c-doing"><div class="kpi-num">{doing_n}</div><div class="kpi-label">进行中</div></div><div class="kpi-card c-overdue"><div class="kpi-num">{total}</div><div class="kpi-label">延期</div></div><div class="kpi-card c-people"><div class="kpi-num">{people}</div><div class="kpi-label">涉及人员</div></div></div>
<div class="charts-row"><div class="chart-box"><h3>延期任务按人员分布</h3><div class="chart-container"><canvas id="personChart"></canvas></div></div><div class="chart-box"><h3>任务状态分布</h3><div class="chart-container"><canvas id="statusChart"></canvas></div></div><div class="chart-box"><h3>优先级分布</h3><div class="chart-container"><canvas id="priChart"></canvas></div></div></div>
<div class="details-title">按负责人明细（点击展开）</div>{"".join(person_cards)}
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME} | 仅显示已延期任务</div></div></body></html>'''

# ─── 效率分析（6/18旧版样式） ─────────────────────────────────────

def build_workload_page(project, groups, all_tasks):
    proj_full = '销售财务中台 FMS' if project=='FMS' else '格力海外售后 GAS'
    # Overall stats
    total_done = sum(1 for t in all_tasks if t.get('status') in ('done','closed'))
    total_undone = sum(1 for t in all_tasks if t.get('status') not in ('done','closed','cancel'))
    total_cons = sum(float(t.get('consumed',0) or 0) for t in all_tasks)
    total_left = sum(float(t.get('left',0) or 0) for t in all_tasks)
    total_est = sum(float(t.get('estimate',0) or 0) for t in all_tasks)
    overdue_n = sum(1 for t in all_tasks if t.get('_overdue_days',False))
    n_people = len(set(t.get('assignedToRealName','') for t in all_tasks if t.get('assignedToRealName')))
    
    # Role summary
    role_bars = []
    all_cat_people = set()
    for cat in ['产品','后端','前端','测试','uiux']:
        ct = [t for t in all_tasks if t['_category']==cat]
        ct_done = [t for t in ct if t.get('status') in ('done','closed')]
        ct_doing = [t for t in ct if t.get('status') not in ('done','closed','cancel')]
        ct_ppl = set(t.get('assignedToRealName','') for t in ct if t.get('assignedToRealName'))
        all_cat_people.update(ct_ppl)
        role_bars.append(f'<div class="role-bar"><div class="rb-title">{CAT_DISPLAY[cat]}</div><div class="rb-stat"><strong>{len(ct_ppl)}人</strong></div><div class="rb-stat">完成 <strong>{len(ct_done)}个</strong></div><div class="rb-stat">进行中 <strong>{len(ct_doing)}个</strong></div></div>')
    
    # Chart data: per-person consumed (top 30)
    pstats = defaultdict(lambda: [0,0])  # [done_cons, undone_cons]
    for t in all_tasks:
        pn = t.get('assignedToRealName','') or ''
        if t.get('status') in ('done','closed'):
            pstats[pn][0] += float(t.get('consumed',0) or 0)
        elif t.get('status') not in ('done','closed','cancel'):
            pstats[pn][1] += float(t.get('consumed',0) or 0)
    top_ppl = sorted(pstats.items(), key=lambda x: sum(x[1]), reverse=True)[:30]
    ch_names = json.dumps([n for n,_ in top_ppl])
    ch_done = json.dumps([v[0] for _,v in top_ppl])
    ch_udone = json.dumps([v[1] for _,v in top_ppl])
    
    # Chart: role stats
    role_labels = json.dumps([CAT_DISPLAY[c] for c in ['产品','后端','前端','测试','uiux']])
    role_done_data = json.dumps([sum(1 for t in all_tasks if t['_category']==c and t.get('status') in ('done','closed')) for c in ['产品','后端','前端','测试','uiux']])
    role_doing_data = json.dumps([sum(1 for t in all_tasks if t['_category']==c and t.get('status') not in ('done','closed','cancel')) for c in ['产品','后端','前端','测试','uiux']])
    
    # Per-role person tables with expandable detail
    role_sections = []
    for cat in ['产品','后端','前端','测试','uiux']:
        cat_tasks = [t for t in all_tasks if t['_category']==cat]
        cat_done = [t for t in cat_tasks if t.get('status') in ('done','closed')]
        cat_undone = [t for t in cat_tasks if t.get('status') not in ('done','closed','cancel')]
        # Group by person
        pt_map = defaultdict(lambda: {'all':[],'done':[],'undone':[]})
        for t in cat_tasks:
            pn = t.get('assignedToRealName','') or '未分配'
            pt_map[pn]['all'].append(t)
            if t.get('status') in ('done','closed'): pt_map[pn]['done'].append(t)
            else: pt_map[pn]['undone'].append(t)
        
        cat_ppl = len(set(t.get('assignedToRealName','') for t in cat_tasks if t.get('assignedToRealName')))
        cat_cons = sum(float(t.get('consumed',0) or 0) for t in cat_tasks)
        
        person_rows = []
        detail_rows = []
        for pi, (name, pd) in enumerate(sorted(pt_map.items(), key=lambda x: -len(x[1]['all']))):
            total_ts = len(pd['all']); done_ts = len(pd['done']); undone_ts = len(pd['undone'])
            done_pct = done_ts/max(total_ts,1)*100
            p_cons = sum(float(t.get('consumed',0) or 0) for t in pd['done'])
            p_ucons = sum(float(t.get('consumed',0) or 0) for t in pd['undone'])
            p_uest = sum(float(t.get('estimate',0) or 0) for t in pd['undone'])
            p_uleft = sum(float(t.get('left',0) or 0) for t in pd['undone'])
            eff = 'eff-high' if done_pct>=80 else 'eff-normal' if done_pct>=40 else 'eff-slow'
            eff_text = '高效' if done_pct>=80 else '正常' if done_pct>=40 else '缓慢'
            detail_id = f'p{project}_{cat}_{pi}'
            person_rows.append(f'<tr><td>{pi+1}</td><td class="name-cell" onclick="toggleDetail(\'{detail_id}\')">{esc(name)}</td><td>{total_ts}</td><td><span class="rate-bar-bg"><span class="rate-bar-fg" style="width:{done_pct:.0f}%;background:#60a5fa"></span></span>{done_pct:.0f}%</td><td>{p_cons+p_ucons:.1f}h</td><td>{p_cons:.1f}h</td><td>{p_uest:.0f}h</td><td>{p_ucons:.1f}h</td><td>{p_uleft:.0f}h</td><td><span class="{eff}">{eff_text}</span></td></tr>')
            # Detail rows
            d_done_rows = ''.join(f'<tr><td>{t.get("id","")}</td><td>{esc(t.get("name","")[:40])}</td><td>{float(t.get("consumed",0) or 0):.1f}h</td><td>{t.get("finishedDate","") or ""}</td><td>{esc((t.get("_exec_name","") or "")[:20])}</td></tr>' for t in sorted(pd['done'], key=lambda x: x.get('finishedDate','') or '', reverse=True))
            d_undone_rows = ''.join(f'<tr><td>{t.get("id","")}</td><td>{esc(t.get("name","")[:40])}</td><td>{t.get("status","")}</td><td>{t.get("deadline","") or ""}</td><td>{fmt_h(t.get("estimate",0))}</td><td>{fmt_h(t.get("consumed",0))}</td><td>{fmt_h(t.get("left",0))}</td><td>{esc((t.get("_exec_name","") or "")[:20])}</td></tr>' for t in pd['undone'])
            detail_rows.append(f'<tr class="detail-row" id="{detail_id}"><td colspan="10"><div class="detail-inner"><div class="detail-col"><h4>已完成任务 ({done_ts}个)</h4><table class="detail-table"><thead><tr><th>ID</th><th>任务</th><th>消耗</th><th>完成日期</th><th>执行</th></tr></thead><tbody>{d_done_rows}</tbody></table></div><div class="detail-col"><h4>未完成任务 ({undone_ts}个)</h4><table class="detail-table"><thead><tr><th>ID</th><th>任务</th><th>状态</th><th>截止</th><th>预估</th><th>已耗</th><th>剩余</th><th>执行</th></tr></thead><tbody>{d_undone_rows}</tbody></table></div></div></td></tr>')
        
        role_sections.append(f'''<div class="team-section"><div class="team-header"><h2>{CAT_DISPLAY[cat]}</h2><span class="team-meta"><strong>{cat_ppl}人</strong> · 当月完成 <strong>{len(cat_done)}</strong> 任务 · 消耗 <strong>{cat_cons:.1f}h</strong> · 进行中 <strong>{len(cat_undone)}个</strong></span></div>
<table class="person-table"><thead><tr><th>#</th><th>人员</th><th>总任务</th><th>完成率</th><th>总工时</th><th>已完成消耗</th><th>未完成预估</th><th>未完成已耗</th><th>未完成剩余</th><th>效率</th></tr></thead><tbody>{"".join(person_rows)}{"".join(detail_rows)}</tbody></table></div>''')
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>团队产出效率分析 - {proj_full}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script><style>
*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:"Microsoft YaHei","PingFang SC",-apple-system,BlinkMacSystemFont,sans-serif;background:#f0f2f5;color:#333;padding:20px;min-height:100vh}}
.header{{text-align:center;padding:24px 0 20px}}.header h1{{font-size:22px;font-weight:700;color:#1a1f36;margin-bottom:6px}}.header .subtitle{{font-size:12px;color:#6b7280}}
.date-badge{{display:inline-block;background:#e8ecf4;color:#6366f1;border:1px solid #d0d5e0;border-radius:16px;padding:4px 14px;font-size:11px;font-weight:500;margin-top:10px}}
.back-link{{display:inline-flex;align-items:center;gap:4px;color:#6366f1;text-decoration:none;font-size:12px;margin-bottom:16px;padding:6px 14px;border-radius:14px;background:#e8ecf4;border:1px solid #d0d5e0;transition:all .2s}}.back-link:hover{{background:#6366f1;color:#fff;border-color:#6366f1}}
.kpi-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px}}.kpi-card{{background:#fff;border-radius:12px;padding:18px 12px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03);position:relative;overflow:hidden}}.kpi-card::before{{content:"";position:absolute;top:0;left:0;right:0;height:3px}}.kpi-card .kpi-num{{font-size:26px;font-weight:800;margin-bottom:3px;letter-spacing:-0.5px}}.kpi-card .kpi-label{{font-size:11px;color:#9ca3af;font-weight:500}}
.kpi-card.c-done::before{{background:linear-gradient(90deg,#43e97b,#38f9d7)}}.kpi-card.c-done .kpi-num{{color:#2e7d32}}.kpi-card.c-doing::before{{background:linear-gradient(90deg,#4facfe,#00f2fe)}}.kpi-card.c-doing .kpi-num{{color:#2563eb}}.kpi-card.c-people::before{{background:linear-gradient(90deg,#667eea,#764ba2)}}.kpi-card.c-people .kpi-num{{color:#667eea}}.kpi-card.c-consumed::before{{background:linear-gradient(90deg,#fbbf24,#f59e0b)}}.kpi-card.c-consumed .kpi-num{{color:#d97706}}.kpi-card.c-left::before{{background:linear-gradient(90deg,#38bdf8,#0ea5e9)}}.kpi-card.c-left .kpi-num{{color:#0284c7}}.kpi-card.c-overdue::before{{background:linear-gradient(90deg,#f87171,#ef4444)}}.kpi-card.c-overdue .kpi-num{{color:#dc2626}}
.role-summary{{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:24px}}.role-bar{{background:#fff;border-radius:10px;padding:14px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.04)}}.role-bar .rb-title{{font-size:12px;font-weight:700;color:#1a1f36;margin-bottom:5px}}.role-bar .rb-stat{{font-size:10px;color:#6b7280;line-height:1.5}}.role-bar .rb-stat strong{{color:#374151}}
.team-section{{margin-bottom:28px}}.team-header{{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding-bottom:10px;border-bottom:2px solid #e5e7eb}}.team-header h2{{font-size:16px;font-weight:700;color:#1a1f36}}.team-header .team-meta{{font-size:11px;color:#9ca3af}}.team-header .team-meta strong{{color:#374151}}
.person-table{{width:100%;border-collapse:collapse;font-size:11px;margin-bottom:20px;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.04)}}.person-table th{{background:#f9fafb;color:#6b7280;font-weight:700;padding:10px 8px;text-align:center;border-bottom:2px solid #e5e7eb;white-space:nowrap;font-size:11px}}.person-table td{{padding:8px 6px;text-align:center;border-bottom:1px solid #f3f4f6;color:#374151}}.person-table tr:nth-child(even){{background:#fafbfc}}.person-table tr:hover td{{background:#f0f4ff}}.person-table .name-cell{{text-align:left;cursor:pointer;color:#6366f1;font-weight:600}}.person-table .name-cell:hover{{color:#4f46e5;text-decoration:underline}}
.eff-high{{display:inline-block;background:#f0fdf4;color:#16a34a;border-radius:6px;padding:1px 8px;font-size:10px;font-weight:600}}.eff-normal{{display:inline-block;background:#eff6ff;color:#2563eb;border-radius:6px;padding:1px 8px;font-size:10px;font-weight:600}}.eff-slow{{display:inline-block;background:#fef2f2;color:#dc2626;border-radius:6px;padding:1px 8px;font-size:10px;font-weight:600}}
.rate-bar-bg{{display:inline-block;width:50px;height:5px;background:#f3f4f6;border-radius:3px;vertical-align:middle;margin-right:3px}}.rate-bar-fg{{display:inline-block;height:5px;border-radius:3px}}
.detail-row{{display:none}}.detail-row.open{{display:table-row}}.detail-row td{{background:#fafbfc;padding:0;border-bottom:2px solid #e5e7eb}}.detail-inner{{padding:14px 16px;display:flex;flex-wrap:wrap;gap:16px}}.detail-col{{flex:1;min-width:300px}}.detail-col h4{{font-size:12px;font-weight:700;color:#374151;margin-bottom:8px;padding-bottom:6px;border-bottom:2px solid #e5e7eb}}
.detail-table{{width:100%;border-collapse:collapse;font-size:10px}}.detail-table th{{background:#f3f4f6;color:#6b7280;font-weight:600;padding:6px 5px;text-align:left;border-bottom:1px solid #e5e7eb;white-space:nowrap;font-size:10px}}.detail-table td{{padding:5px;border-bottom:1px solid #f3f4f6;color:#374151}}.detail-table tr:nth-child(even){{background:#fff}}.detail-table tr:hover td{{background:#f0f4ff}}
.charts-section{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:28px}}.chart-box{{background:#fff;border-radius:12px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}.chart-box h3{{font-size:13px;font-weight:600;color:#374151;margin-bottom:12px;text-align:center}}.chart-box canvas{{max-height:260px}}
.footer{{text-align:center;padding:16px 0;color:#9ca3af;font-size:11px}}@media(max-width:768px){{body{{padding:14px}}.kpi-row{{grid-template-columns:repeat(3,1fr);gap:8px}}.kpi-card{{padding:14px 8px}}.kpi-card .kpi-num{{font-size:22px}}.role-summary{{grid-template-columns:repeat(3,1fr);gap:8px}}.charts-section{{grid-template-columns:1fr}}.header h1{{font-size:18px}}.person-table{{font-size:10px}}.detail-table{{font-size:9px}}.eff-high,.eff-normal,.eff-slow{{font-size:9px;padding:1px 6px}}}}@media(max-width:480px){{body{{padding:8px}}.kpi-row{{grid-template-columns:repeat(2,1fr);gap:6px}}.kpi-card{{padding:10px 6px;border-radius:10px}}.kpi-card .kpi-num{{font-size:18px}}.role-summary{{grid-template-columns:repeat(2,1fr);gap:6px}}.header h1{{font-size:16px}}.person-table{{font-size:9px}}.detail-table{{font-size:8px}}}}</style>
<script>function toggleDetail(id){{var el=document.getElementById(id);if(el)el.classList.toggle("open")}}
window.onload=function(){{new Chart(document.getElementById("consumedChart"),{{type:"bar",data:{{labels:{ch_names},datasets:[{{label:"已完成消耗",data:{ch_done},backgroundColor:"#4ade80"}},{{label:"未完成已耗",data:{ch_udone},backgroundColor:"#f87171"}}]}},options:{{indexAxis:"y",responsive:true,scales:{{x:{{stacked:true}}}},plugins:{{legend:{{position:"bottom"}}}}}}}});
new Chart(document.getElementById("roleChart"),{{type:"bar",data:{{labels:{role_labels},datasets:[{{label:"已完成",data:{role_done_data},backgroundColor:"#4ade80"}},{{label:"进行中",data:{role_doing_data},backgroundColor:"#60a5fa"}}]}},options:{{responsive:true,scales:{{x:{{grid:{{color:"rgba(255,255,255,.06)"}}}}}},plugins:{{legend:{{position:"bottom"}}}}}}}});}}</script></head>
<body><a class="back-link" href="index.html">← 返回 {proj_full} 报告</a>
<div class="header"><h1>团队产出效率分析</h1><p class="subtitle">{proj_full} · 2026年06月</p><div class="date-badge">数据更新：{TODAY_DATETIME}</div></div>
<div class="kpi-row"><div class="kpi-card c-done"><div class="kpi-num">{total_done}</div><div class="kpi-label">当月已完成</div></div><div class="kpi-card c-doing"><div class="kpi-num">{total_undone}</div><div class="kpi-label">进行中+待处理</div></div><div class="kpi-card c-people"><div class="kpi-num">{n_people}</div><div class="kpi-label">参与人员</div></div><div class="kpi-card c-consumed"><div class="kpi-num">{total_cons:.1f}h</div><div class="kpi-label">总消耗工时</div></div><div class="kpi-card c-left"><div class="kpi-num">{total_left:.1f}h</div><div class="kpi-label">剩余工时</div></div><div class="kpi-card c-overdue"><div class="kpi-num">{overdue_n}</div><div class="kpi-label">延期任务</div></div></div>
<div class="role-summary">{"".join(role_bars)}</div>
<div class="charts-section"><div class="chart-box"><h3>成员已完成/进行中消耗工时对比</h3><canvas id="consumedChart"></canvas></div><div class="chart-box"><h3>各角色已完成/进行中任务对比</h3><canvas id="roleChart"></canvas></div></div>
{"".join(role_sections)}
<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME} | 团队产出效率自动统计</div></body></html>'''

# ─── 项目汇报（完整版：动态数据 + 富内容跟踪） ────────────────────

# 6月核心需求跟踪数据（静态项目规划内容，手工维护）
CORE_REQUIREMENTS_FMS = [
    # (优先级, 业务线, 需求编号, 总结描述, 版本, 状态)
    ('P0', '分销/发票', '1212', '京东订单开票增加字段长度', '0615', '已上线'),
    ('P0', '售后/账户', '1184', 'FMS侧查看收付通用户进件资料审核状态和审核驳回内容', '0615', '已上线'),
    ('P0', '售后/账户', '1185', '售后收付通用户进件调整附件上传功能和文案修改', '0615', '已上线'),
    ('P0', '分销/报表', '1195', '销售订单与扣款报表多维分析扩展', '0615', '已上线'),
    ('P1', '通用/认款', '1158', 'FMS系统增加已签收票据邮件收件人配置功能', '0615', '已上线'),
    ('P1', '售后/清结算', '1214', '售后分账查账单调整为从钱包侧查询账单数据', '0615', '已上线'),
    ('P2', '网批/发票', '1173', 'ERP订单开票记录功能优化', '0615', '已上线'),
    ('P2', '通用/平台技术', '1192', 'AI 插件与大模型之间增加一层代理', '0615', '已上线'),
    ('P0', '商用/账户', '1191', '商用机电公司额度账户自动还款能力', '0630', '开发中'),
    ('P0', '售后/账户', '1208', '售后收付通企业和个人进件流程简化', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '信用账户钱包侧和FMS管理后台侧功能升级', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '商用项目合同模式现汇和汇票到账管理和预收款管理', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '商用项目合同模式订单退款单建设及单据冲销处理', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '商用项目合同模式核销逻辑体系建设', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '商用项目合同模式应收单详情管理', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '商用项目合同模式应收单管理', '0630', '开发中'),
    ('P0', '商用/账务', '1155', '商用订单和合同信息和商用系统对接', '0630', '开发中'),
    ('P0', '出口/清结算', '1167', '新增出口报价测算报批机制', '0630', '开发中'),
    ('P0', '网批/认款', '1224', 'FMS系统承兑汇票流水增加备注', '0630', '开发中'),
    ('P1', '分销/发票', '1213', '大贲数电发票回调到FMS的提效处理', '0630', '开发中'),
    ('P1', '网批/认款', '1211', '民生银行实现网批票据直联', '0630', '开发中'),
    ('P2', '网批/发票', '1210', 'ERP 下单校验异常分析', '0630', '开发中'),
    ('P2', '网批/账户', '1142', 'FMS从网批系统获取ERP伙伴编码', '0630', '待联调'),
    ('P2', '售后/支付', '1189', '售后好收银历史未分账数据处理', '0630', '开发中'),
    ('P2', '售后/清结算', '1146', '售后批量付款性能提升', '0630', '开发中'),
    ('P2', '通用/平台技术', '1156', '6月AI应用销售财务项目需求', '0630', '开发中'),
    ('P2', '通用/平台技术', '1215', '实现代码提交时的自动检查能力', '0630', '开发中'),
]

# 业务与系统对接支持
BUSINESS_INTEGRATION_FMS = [
    ('收付通进件审核', '外部平台', '已完成', '对接微信收付通审核状态查询接口'),
    ('商用订单及合同系统', '业务系统', '进行中', '商用订单/合同信息拉取'),
    ('网批ERP伙伴编码', '业务系统', '待联调', '现有接口和网批联调(1142)'),
    ('民生银行票据直联', '银行对接', '开发中', '网批票据直联(1211)'),
    ('银企直联ETL', '平台技术', '开发中', 'AI应用项目，630上MVP'),
    ('大贲数电发票回调', '外部平台', '开发中', '提效处理(1213)'),
]

# 风险与问题跟踪
RISK_TRACKING_FMS = [
    ('🔴 高', '商用项目业务紧急需求',
     '商经部临时通知直签项目正常上线，财务未明确需求，还款和开票功能还未提需求开发',
     '需财务确认需求，拉通商用系统同步排期'),
    ('🔴 高', '网批工程保证金紧急需求',
     '销司反馈圈2次货资金占用多一倍，需紧急支持，与当前多个重点项目排期冲突',
     '组内紧急讨论评估，确认是否保持一致上线节点'),
    ('🟡 中', '0630版本需求密集',
     'P0需求集中在0630，开发资源紧张，6月20日全量提测节点压力大',
     '持续跟进开发进度，必要时协调资源'),
    ('🟡 中', '数据权限方案复杂',
     '技术复杂度高，关联功能多，实现方案待评估',
     '技术方案评审中'),
    ('🟢 低', 'AI应用MVP版本',
     '630上MVP版本，用于研发导任务，无需测试',
     '按计划推进'),
]


def build_report_page(project, groups, all_tasks):
    proj_full = '销售财务中台 FMS' if project=='FMS' else '格力海外售后 GAS'
    execs = defaultdict(lambda: {'tasks':0,'done':0})
    for t in all_tasks:
        execs[t.get('_exec_name','')]['tasks'] += 1
        if t.get('status') in ('done','closed'): execs[t.get('_exec_name','')]['done'] += 1
    
    # Stats
    total_all = len(all_tasks)
    total_done = sum(1 for t in all_tasks if t.get('status') in ('done','closed'))
    total_undone = total_all - total_done
    
    # Requirement count: estimate based on executed tasks across iterations
    # Count unique story IDs if available, else use task count
    n_requirements = len(set(t.get('story','') for t in all_tasks if t.get('story'))) or 27  # fallback to 27
    
    n_exec = sum(1 for e in EXEC_MAP.values() if e[1]==project)
    
    # Version details
    ver0615_tasks = [t for t in all_tasks if '0615' in t.get('_exec_name','')]
    ver0630_tasks = [t for t in all_tasks if '0630' in t.get('_exec_name','')]
    ver0615_done = sum(1 for t in ver0615_tasks if t.get('status') in ('done','closed'))
    ver0630_done = sum(1 for t in ver0630_tasks if t.get('status') in ('done','closed'))
    
    ver0615_total = len(ver0615_tasks)
    ver0630_total = len(ver0630_tasks)
    
    # ─── 0615 version card ───
    ver0615_html = f'''<div class="ver-card ver-done"><div class="ver-header"><div class="ver-status-icon">✅</div><div class="ver-info"><h3>0615版本</h3><span class="ver-badge done">已上线 (6月15日)</span></div></div><div class="ver-timeline">6月8日全量提测 → 6月11日投产方案评审 → 6月15日发布UAT及发版</div><div class="ver-stats"><div class="vs-item"><div class="vs-num">8</div><div class="vs-label">需求数</div></div><div class="vs-item"><div class="vs-num">{ver0615_total}</div><div class="vs-label">总任务</div></div><div class="vs-item"><div class="vs-num">{ver0615_done}</div><div class="vs-label">已完成</div></div></div></div>'''
    
    # ─── 0630 version card ───
    ver0630_html = f'''<div class="ver-card ver-active"><div class="ver-header"><div class="ver-status-icon">🔄</div><div class="ver-info"><h3>0630版本</h3><span class="ver-badge active">开发中</span></div></div><div class="ver-timeline">6月20日全量提测 → 6月28日投产方案评审 → 6月30日发布UAT及发版</div><div class="ver-stats"><div class="vs-item"><div class="vs-num">19</div><div class="vs-label">需求数</div></div><div class="vs-item"><div class="vs-num">{ver0630_total}</div><div class="vs-label">总任务</div></div><div class="vs-item"><div class="vs-num">{ver0630_total - ver0630_done}</div><div class="vs-label">未完成</div></div><div class="vs-item"><div class="vs-num">{ver0630_done}</div><div class="vs-label">已完成</div></div></div></div>'''
    
    # ─── Core requirements table ───
    req_rows = []
    for pri, biz, rid, summary, ver, status in CORE_REQUIREMENTS_FMS:
        pri_cls = 'pri-p0' if pri == 'P0' else 'pri-p1' if pri == 'P1' else 'pri-p2'
        st_cls = 'st-done' if status == '已上线' else 'st-active' if '开发' in status else 'st-pending'
        req_rows.append(f'<tr><td><span class="pri-badge {pri_cls}">{pri}</span></td><td>{biz}</td><td>{rid} - {summary}</td><td>{ver}</td><td><span class="st-badge {st_cls}">{status}</span></td></tr>')
    
    # ─── Business integration table ───
    biz_rows = []
    for item, itype, istatus, desc in BUSINESS_INTEGRATION_FMS:
        si_cls = 'st-done' if istatus == '已完成' else 'st-active'
        biz_rows.append(f'<tr><td>{item}</td><td>{itype}</td><td><span class="st-badge {si_cls}">{istatus}</span></td><td>{desc}</td></tr>')
    
    # ─── Risk tracking table ───
    risk_rows = []
    for level, item, problem, measure in RISK_TRACKING_FMS:
        rl_cls = 'rl-high' if '高' in level else 'rl-mid' if '中' in level else 'rl-low'
        risk_rows.append(f'<tr class="{rl_cls}"><td><strong>{level}</strong></td><td><strong>{item}</strong></td><td>{problem}</td><td>{measure}</td></tr>')
    
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>6月项目汇报 - {project}</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:"Inter","SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1a1f36;padding:24px;min-height:100vh}}.container{{max-width:1100px;margin:0 auto}}
.header{{text-align:center;padding:32px 0 16px}}.header h1{{font-size:28px;font-weight:800;letter-spacing:-0.5px}}.header .meta{{color:#6b7280;font-size:13px;margin-top:8px;display:flex;align-items:center;justify-content:center;gap:12px}}.header .meta span{{background:#fff;padding:4px 14px;border-radius:14px;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
.breadcrumb{{margin-bottom:16px;font-size:13px}}.breadcrumb a{{color:#6366f1;text-decoration:none;padding:5px 14px;border-radius:14px;background:#fff;border:1px solid #e5e7eb;display:inline-flex;align-items:center;gap:4px;transition:all .2s}}.breadcrumb a:hover{{background:#6366f1;color:#fff;border-color:#6366f1}}

/* Overview cards */
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:28px}}
.card{{background:#fff;border-radius:14px;padding:22px 16px;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03);position:relative;overflow:hidden;transition:transform .2s}}.card:hover{{transform:translateY(-2px);box-shadow:0 4px 20px rgba(0,0,0,.08)}}.card::before{{content:"";position:absolute;top:0;left:0;right:0;height:3px}}.card .card-icon{{font-size:28px;display:block;margin-bottom:6px}}.card .num{{font-size:34px;font-weight:800;letter-spacing:-1px;line-height:1.1}}.card .label{{font-size:12px;color:#9ca3af;margin-top:6px;font-weight:500}}
.card-v::before{{background:linear-gradient(90deg,#667eea,#764ba2)}}.card-v .num{{color:#667eea}}
.card-r::before{{background:linear-gradient(90deg,#f59e0b,#fbbf24)}}.card-r .num{{color:#d97706}}
.card-t::before{{background:linear-gradient(90deg,#3b82f6,#6366f1)}}.card-t .num{{color:#3b82f6}}
.card-d::before{{background:linear-gradient(90deg,#43e97b,#38f9d7)}}.card-d .num{{color:#2e7d32}}

/* Version cards */
.ver-section{{margin-bottom:28px}}.ver-section h2{{font-size:18px;font-weight:700;margin-bottom:14px;color:#1a1f36}}
.ver-cards{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.ver-card{{background:#fff;border-radius:14px;padding:24px;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03)}}
.ver-header{{display:flex;align-items:center;gap:12px;margin-bottom:10px}}.ver-status-icon{{font-size:30px}}.ver-info h3{{font-size:18px;font-weight:700;color:#1a1f36}}.ver-badge{{display:inline-block;font-size:11px;padding:2px 12px;border-radius:12px;font-weight:600;margin-top:2px}}.ver-badge.done{{background:#f0fdf4;color:#16a34a}}.ver-badge.active{{background:#eff6ff;color:#3b82f6}}
.ver-timeline{{font-size:12px;color:#9ca3af;margin-bottom:14px;padding:8px 12px;background:#f9fafb;border-radius:8px;line-height:1.5}}
.ver-stats{{display:flex;gap:16px}}.vs-item{{flex:1;text-align:center;padding:12px 8px;background:#f9fafb;border-radius:10px}}.vs-num{{font-size:26px;font-weight:800}}.vs-item:nth-child(1) .vs-num{{color:#667eea}}.vs-item:nth-child(2) .vs-num{{color:#3b82f6}}.vs-item:nth-child(3) .vs-num{{color:#f59e0b}}.vs-item:nth-child(4) .vs-num{{color:#10b981}}.vs-label{{font-size:11px;color:#9ca3af;margin-top:3px}}

/* Content sections */
.section{{background:#fff;border-radius:14px;padding:24px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.03)}}.section h2{{font-size:18px;font-weight:700;margin-bottom:16px;color:#1a1f36}}

/* Tables */
table{{width:100%;border-collapse:collapse;font-size:13px}}th{{background:#f8fafc;color:#475569;font-weight:700;font-size:12px;padding:12px 10px;text-align:left;border-bottom:2px solid #e5e7eb;white-space:nowrap}}
td{{padding:11px 10px;border-bottom:1px solid #f1f5f9;color:#334155;line-height:1.5}}tr:hover td{{background:#f8fafc}}
td:last-child{{text-align:center}}

/* Priority badges */
.pri-badge{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:4px;font-weight:700}}.pri-p0{{background:#fef2f2;color:#dc2626}}.pri-p1{{background:#fff7ed;color:#ea580c}}.pri-p2{{background:#eff6ff;color:#2563eb}}

/* Status badges */
.st-badge{{display:inline-block;font-size:11px;padding:3px 10px;border-radius:12px;font-weight:600}}.st-done{{background:#f0fdf4;color:#16a34a}}.st-active{{background:#eff6ff;color:#2563eb}}.st-pending{{background:#fef9c3;color:#ca8a04}}

/* Risk rows */
tr.rl-high{{background:#fef2f2}}tr.rl-high:hover td{{background:#fee2e2}}tr.rl-mid{{background:#fff7ed}}tr.rl-mid:hover td{{background:#ffedd5}}tr.rl-low{{background:#f0fdf4}}tr.rl-low:hover td{{background:#dcfce7}}

/* Toggle details */
summary{{cursor:pointer;user-select:none;padding:4px 0;font-weight:600}}summary:hover{{color:#6366f1}}

.footer{{text-align:center;padding:28px;color:#9ca3af;font-size:12px}}

@media(max-width:900px){{.cards{{grid-template-columns:repeat(2,1fr)}}.ver-cards{{grid-template-columns:1fr}}}}
@media(max-width:600px){{body{{padding:12px}}.header h1{{font-size:22px}}.cards{{gap:8px}}.card{{padding:14px 8px}}.card .num{{font-size:26px}}.ver-stats{{flex-wrap:wrap}}.section{{padding:16px}}table{{font-size:11px}}th,td{{padding:8px 6px}}}}</style></head>
<body><div class="container">
<div class="breadcrumb"><a href="index.html">← 返回 {proj_full} 报告</a></div>
<div class="header"><h1>📊 6月项目汇报</h1><p class="meta"><span>{proj_full}</span><span>部门领导汇报</span></p></div>

<div class="cards">
<div class="card card-v"><span class="card-icon">📦</span><div class="num">{n_exec}</div><div class="label">上线版本</div></div>
<div class="card card-r"><span class="card-icon">📋</span><div class="num">{n_requirements}</div><div class="label">月度需求</div></div>
<div class="card card-t"><span class="card-icon">📊</span><div class="num">{total_all}</div><div class="label">月总任务</div></div>
<div class="card card-d"><span class="card-icon">✅</span><div class="num">{total_done}</div><div class="label">已完成</div></div>
</div>

<div class="ver-section"><h2>📦 6月版本情况</h2><div class="ver-cards">{ver0615_html}{ver0630_html}</div></div>

<div class="section"><h2>🎯 核心需求跟踪</h2>
<div style="overflow-x:auto"><table><thead><tr><th>优先级</th><th>业务线</th><th>需求总结描述</th><th>版本</th><th>状态</th></tr></thead><tbody>{"".join(req_rows)}</tbody></table></div></div>

<div class="section"><h2>🔗 业务与系统对接支持</h2>
<div style="overflow-x:auto"><table><thead><tr><th>对接项</th><th>类型</th><th>状态</th><th>说明</th></tr></thead><tbody>{"".join(biz_rows)}</tbody></table></div></div>

<div class="section"><h2>⚠️ 风险与问题跟踪</h2>
<div style="overflow-x:auto"><table><thead><tr><th>级别</th><th>风险项</th><th>问题描述</th><th>应对措施</th></tr></thead><tbody>{"".join(risk_rows)}</tbody></table></div></div>

<div class="footer">数据来源：禅道管理系统 | 生成时间：{TODAY_DATETIME}</div></div></body></html>'''

# ─── 主报告中心 ────────────────────────────────────────────────────

def build_main_index(fms_groups, gas_groups, fms_all, gas_all, date_dir):
    def proj_stats(project, groups, all_tasks):
        today_total = {c:0 for c in ['产品','后端','前端','测试','uiux']}
        for t in all_tasks:
            if t['_category'] in today_total: today_total[t['_category']] += 1
        undone = {}
        for cat in ['产品','后端','前端','测试','uiux']:
            ct = groups.get(cat,[])
            undone[cat] = {'total':len(ct),'wait':sum(1 for t in ct if t.get('status')=='wait'),'doing':sum(1 for t in ct if t.get('status')=='doing'),'people':len(set(t.get('assignedToRealName','') for t in ct if t.get('assignedToRealName')))}
        overdue_n = count_overdue(all_tasks)
        return today_total, undone, overdue_n, len(all_tasks)
    
    fms_totals, fms_undone, fms_overdue, fms_total = proj_stats('FMS', fms_groups, fms_all)
    gas_totals, gas_undone, gas_overdue, gas_total = proj_stats('GAS', gas_groups, gas_all)
    
    def trend_table(project, hist_data, today_totals):
        dates = ['2026-06-05','2026-06-11','2026-06-12','2026-06-17','2026-06-18']
        rows = []
        for i, d in enumerate(dates):
            if d in hist_data:
                prev_key = dates[i-1] if i>0 else None
                row = hist_data[d]; cols = [f'<td style="font-size:13px">{d}</td>']
                for cat in ['产品','后端','前端','测试','uiux']:
                    v = row[cat]; diff = ''
                    if prev_key and prev_key in hist_data:
                        delta = v-hist_data[prev_key][cat]
                        diff = f'<span style="color:#10b981">+{delta}</span>' if delta>0 else f'<span style="color:#ef4444">{delta}</span>' if delta<0 else '<span style="color:#64748b">--</span>'
                    cols.append(f'<td style="font-size:13px;text-align:center">{v} {diff}</td>')
                dt = row['total']-(hist_data[prev_key]['total'] if prev_key and prev_key in hist_data else row['total'])
                dts = f'<span style="color:#10b981">+{dt}</span>' if dt>0 else f'<span style="color:#ef4444">{dt}</span>' if dt<0 else '<span style="color:#64748b">--</span>'
                cols.append(f'<td style="font-size:13px;text-align:center;font-weight:600">{row["total"]} {dts}</td>')
                rows.append('<tr>'+''.join(cols)+'</tr>')
        today_val = sum(today_totals.get(c,0) for c in ['产品','后端','前端','测试','uiux'])
        prev_tot = hist_data.get('2026-06-18',{})
        today_cols = [f'<td style="font-size:13px;background:rgba(59,130,246,.08)"><strong>{TODAY_STR}</strong></td>']
        for cat in ['产品','后端','前端','测试','uiux']:
            v = today_totals.get(cat,0)
            delta = v-prev_tot.get(cat,0) if prev_tot else 0
            diff = f'<span style="color:#10b981">+{delta}</span>' if delta>0 else f'<span style="color:#ef4444">{delta}</span>' if delta<0 else '<span style="color:#64748b">--</span>'
            today_cols.append(f'<td style="font-size:13px;text-align:center;background:rgba(59,130,246,.08)">{v} {diff}</td>')
        dt = today_val-(prev_tot['total'] if prev_tot else 0)
        dts = f'<span style="color:#10b981">+{dt}</span>' if dt>0 else f'<span style="color:#ef4444">{dt}</span>' if dt<0 else '<span style="color:#64748b">--</span>'
        today_cols.append(f'<td style="font-size:13px;text-align:center;font-weight:600;background:rgba(59,130,246,.08)">{today_val} {dts}</td>')
        rows.append('<tr>'+''.join(today_cols)+'</tr>')
        return f'''<table style="width:100%;border-collapse:collapse;font-size:13px;color:#e2e8f0"><thead><tr style="color:#94a3b8;font-weight:600"><th style="padding:8px;border-bottom:1px solid rgba(255,255,255,.08)">日期</th><th style="padding:8px;text-align:center">📋 产品</th><th style="padding:8px;text-align:center">⚙️ 后端</th><th style="padding:8px;text-align:center">🎨 前端</th><th style="padding:8px;text-align:center">🧪 测试</th><th style="padding:8px;text-align:center">🖌️ UI/UX</th><th style="padding:8px;text-align:center;color:#f8fafc">合计</th></tr></thead><tbody>{"".join(rows)}</tbody></table>'''
    
    def tab_content(project, groups, all_tasks, today_totals, hist_data, active):
        proj_l = project.lower(); undone = fms_undone if project=='FMS' else gas_undone
        ov_n = fms_overdue if project=='FMS' else gas_overdue; tot_n = fms_total if project=='FMS' else gas_total
        pills = []
        for cat in ['产品','后端','前端','测试','uiux']:
            s = undone[cat]; cd = CAT_DISPLAY[cat]; cls = f'c-{cat}' if cat!='uiux' else 'c-uiux'
            pills.append(f'<div class="stat-pill-small {cls}"><div class="num">{s["total"]}</div><div class="meta"><span class="meta-icon">{CAT_ICONS[cat]}</span> {cd} <span style="color:#94a3b8">待{s["wait"]}/做{s["doing"]}</span></div></div>')
        pills.append(f'<div class="stat-pill-small c-overdue"><div class="num">{ov_n}</div><div class="meta"><span class="meta-icon">🚨</span> 延期任务 <span style="color:#94a3b8">共{tot_n}个</span></div></div>')
        
        feats = []
        for cat in ['产品','后端','前端','uiux']:
            s = undone[cat]; cs = CAT_SAFE[cat]; cd = CAT_DISPLAY[cat]; subt = {'产品':'需求 / AB 类型','后端':'开发任务','前端':'开发任务','uiux':'设计任务'}
            feats.append(f'<a class="feature-card" href="{proj_l}/{date_dir}/{cs}_详细任务.html"><div class="card-icon-large">{CAT_ICONS[cat]}</div><div class="card-title">{cd}任务</div><div class="card-subtitle">{subt.get(cat,"")}</div><div class="card-count"><strong>{s["total"]}</strong> 个未完成 · <strong>{s["people"]}</strong> 人</div></a>')
        
        ts = undone['测试']; n_exec = sum(1 for e in EXEC_MAP.values() if e[1]==project)
        exec_rows = ''.join(f'<tr><td>{e[0]}</td><td>doing</td><td>{e[2]} ~ {e[3]}</td></tr>' for eid,e in EXEC_MAP.items() if e[1]==project)
        
        return f'''<div class="tab-content {"active" if active else ""}" id="tab-{project}">
<div class="project-header">{'销售财务中台 FMS' if project=="FMS" else "格力海外售后 GAS"}</div>
<div class="stat-pills-row">{"".join(pills)}</div>
<div class="feature-cards-row">{"".join(feats)}</div>
<div class="func-cards-row">
<a class="func-card" href="{proj_l}/{date_dir}/测试_详细任务.html"><div class="card-icon-large">🧪</div><div class="card-title">测试任务</div><div class="card-desc">测试执行 + 测试设计<br><strong>{ts["total"]}</strong> 个未完成 · <strong>{ts["people"]}</strong> 人</div></a>
<a class="func-card" href="{proj_l}/项目汇报.html"><div class="card-icon-large">📊</div><div class="card-title">6月项目汇报</div><div class="card-desc">版本进度 · P0需求跟踪<br>业务对接 · 风险预警</div></a>
<a class="func-card" href="{proj_l}/延期任务.html"><div class="card-icon-large">🚨</div><div class="card-title">延期任务</div><div class="card-desc"><strong>{ov_n}</strong> 个延期任务<br>全平台超期追踪</div></a>
<a class="func-card" href="{proj_l}/效率分析.html"><div class="card-icon-large">💪</div><div class="card-title">员工负载</div><div class="card-desc">按角色分组工时分析<br>完成/进行中负载对比</div></a>
</div>
<div class="exec-section"><h3>📊 进行中的迭代</h3><table class="exec-table"><thead><tr><th>迭代名称</th><th>状态</th><th>时间</th></tr></thead><tbody>{exec_rows}</tbody></table></div>
<div class="trend-section"><h3>📈 任务数量趋势（近5天）</h3>{trend_table(project, hist_data, today_totals)}</div></div>'''
    
    hist_dates = ['2026-06-18','2026-06-17','2026-06-12','2026-06-11','2026-06-05','2026-05-28','2026-05-27']
    hist_links = ''.join(f'<a class="date-tag{" current" if d==TODAY_STR else ""}" href="fms/{d}/产品_详细任务.html">{d}</a>' for d in [TODAY_STR]+hist_dates)
    
    html = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>禅道任务报告中心</title>
<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Noto Sans SC",sans-serif;background:radial-gradient(ellipse at center,#2d3561 0%,#1a1f3a 50%,#0f1429 100%);color:#e2e8f0;min-height:100vh}}
.container{{max-width:1000px;margin:0 auto;padding:48px 24px}}
.header{{text-align:center;margin-bottom:32px}}.logo{{width:48px;height:48px;margin:0 auto 16px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:28px}}
.header h1{{font-size:28px;font-weight:700;color:#f8fafc;margin-bottom:6px}}.header .subtitle{{font-size:13px;color:#94a3b8;margin-bottom:16px}}
.date-badge{{display:inline-block;background:rgba(59,130,246,.15);color:#60a5fa;border:1px solid rgba(59,130,246,.3);border-radius:20px;padding:5px 18px;font-size:13px;font-weight:500}}
.tab-bar{{display:flex;justify-content:center;gap:8px;margin-bottom:40px}}.tab-btn{{padding:10px 36px;border-radius:24px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:#94a3b8;cursor:pointer;font-size:15px;font-weight:600;transition:all .2s}}.tab-btn:hover{{background:rgba(255,255,255,.08);color:#cbd5e1}}.tab-btn.active{{background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border-color:transparent;box-shadow:0 4px 15px rgba(59,130,246,.3)}}
.tab-content{{display:none}}.tab-content.active{{display:block}}.project-header{{text-align:center;margin-bottom:24px;font-size:24px;font-weight:700;color:#f8fafc}}
.stat-pills-row{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin-bottom:24px}}
.stat-pill-small{{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px;padding:16px 8px;text-align:center;backdrop-filter:blur(10px);transition:all .2s}}.stat-pill-small:hover{{background:rgba(255,255,255,.07)}}
.stat-pill-small .num{{font-size:26px;font-weight:700;margin-bottom:8px}}.stat-pill-small .meta{{font-size:11px;color:#94a3b8;display:flex;align-items:center;justify-content:center;gap:4px}}
.stat-pill-small.c-产品 .num{{color:#a78bfa}}.stat-pill-small.c-后端 .num{{color:#4ade80}}.stat-pill-small.c-前端 .num{{color:#f472b6}}.stat-pill-small.c-uiux .num{{color:#38bdf8}}.stat-pill-small.c-测试 .num{{color:#fbbf24}}.stat-pill-small.c-overdue .num{{color:#f87171}}
.feature-cards-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.feature-card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:28px 16px 24px;text-align:center;transition:all .2s ease;backdrop-filter:blur(10px);display:block;text-decoration:none;color:#e2e8f0}}.feature-card:hover{{background:rgba(255,255,255,.06);transform:translateY(-3px)}}
.feature-card .card-icon-large{{width:56px;height:56px;margin:0 auto 12px;background:rgba(255,255,255,.05);border-radius:14px;display:flex;align-items:center;justify-content:center;font-size:32px}}
.feature-card .card-title{{font-size:16px;font-weight:700;color:#f8fafc;margin-bottom:6px}}.feature-card .card-subtitle{{font-size:12px;color:#64748b;margin-bottom:10px}}.feature-card .card-count{{font-size:13px;color:#94a3b8}}.feature-card .card-count strong{{color:#cbd5e1;font-weight:600}}
.func-cards-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}}
.func-card{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:24px 16px 20px;text-align:center;transition:all .2s ease;backdrop-filter:blur(10px);display:block;text-decoration:none;color:#e2e8f0}}.func-card:hover{{background:rgba(255,255,255,.06);transform:translateY(-3px)}}
.func-card .card-icon-large{{width:48px;height:48px;margin:0 auto 10px;background:rgba(255,255,255,.05);border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:28px}}
.func-card .card-title{{font-size:14px;font-weight:700;margin-bottom:4px}}.func-card .card-desc{{font-size:11px;color:#64748b;line-height:1.5}}
.exec-section,.trend-section{{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:16px;padding:24px;margin-bottom:24px;backdrop-filter:blur(10px)}}.exec-section h3,.trend-section h3{{font-size:16px;color:#f8fafc;margin-bottom:14px}}
.exec-table{{width:100%;border-collapse:collapse;font-size:13px;color:#cbd5e1}}.exec-table th{{color:#94a3b8;text-align:left;padding:8px;border-bottom:1px solid rgba(255,255,255,.08)}}.exec-table td{{padding:10px 8px;border-bottom:1px solid rgba(255,255,255,.04)}}
.history-section{{text-align:center;margin:40px 0 20px}}.history-section h3{{font-size:15px;color:#94a3b8;margin-bottom:14px}}.history-dates{{display:flex;flex-wrap:wrap;justify-content:center;gap:10px}}
.date-tag{{background:rgba(59,130,246,.1);border:1px solid rgba(59,130,246,.2);color:#60a5fa;border-radius:20px;padding:6px 16px;font-size:12px;text-decoration:none}}.date-tag:hover{{background:rgba(59,130,246,.18)}}.date-tag.current{{background:rgba(59,130,246,.22);border-color:rgba(59,130,246,.4);color:#93c5fd}}
.footer{{text-align:center;padding:20px 0}}.footer-text{{color:#475569;font-size:12px}}
@media(max-width:1000px){{.stat-pills-row{{grid-template-columns:repeat(3,1fr)}}.feature-cards-row{{grid-template-columns:repeat(2,1fr)}}.func-cards-row{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:600px){{.stat-pills-row{{grid-template-columns:repeat(2,1fr)}}.feature-cards-row{{grid-template-columns:1fr}}.func-cards-row{{grid-template-columns:1fr}}}}</style>
<script>function switchTab(key){{document.querySelectorAll(".tab-btn").forEach(b=>b.classList.remove("active"));document.querySelectorAll(".tab-content").forEach(c=>c.classList.remove("active"));event.target.classList.add("active");document.getElementById("tab-"+key).classList.add("active")}}</script></head>
<body><div class="container">
<div class="header"><div class="logo">📊</div><h1>禅道任务报告中心</h1><p class="subtitle">Zentao Task Dashboard</p><div class="date-badge">数据更新：{TODAY_DATETIME}</div></div>
<div class="tab-bar"><button class="tab-btn active" onclick="switchTab('FMS')">FMS - 销售财务中台 FMS</button><button class="tab-btn" onclick="switchTab('GAS')">GAS - 格力海外售后 GAS</button></div>
{tab_content('FMS', fms_groups, fms_all, fms_totals, HIST_TOTALS['FMS'], True)}
{tab_content('GAS', gas_groups, gas_all, gas_totals, HIST_TOTALS['GAS'], False)}
<div class="history-section"><h3>📅 历史报告</h3><div class="history-dates">{hist_links}</div></div>
<div class="footer"><div class="footer-text">数据来源：禅道管理系统 | 自动生成于 {TODAY_DATETIME}</div></div></div></body></html>'''
    return html

def main():
    print("加载数据...")
    all_tasks = load_tasks(); print(f"共 {len(all_tasks)} 个任务")
    date_dir = TODAY_STR
    
    for project in ['FMS','GAS']:
        tasks = [t for t in all_tasks if t['_project']==project]
        groups, undone = categorize_undone(tasks); count_overdue(undone)
        proj_l = project.lower(); detail_dir = os.path.join(BUILD_DIR, proj_l, date_dir); os.makedirs(detail_dir, exist_ok=True)
        print(f"\n=== {project} ===")
        for cat in ['产品','后端','前端','测试','uiux']:
            ct = sorted(groups.get(cat,[]), key=lambda x: (x.get('status','')!='doing', x.get('deadline','') or '9999'))
            count_overdue(ct)
            html = build_detail_page(project, cat, ct, date_dir)
            fp = os.path.join(detail_dir, f'{CAT_SAFE[cat]}_详细任务.html')
            with open(fp,'w',encoding='utf-8') as f: f.write(html)
            print(f"  {CAT_DISPLAY[cat]}: {len(ct)} → {fp}")
        # Overdue page
        html = build_overdue_page(project, undone)
        fp = os.path.join(BUILD_DIR, proj_l, '延期任务.html')
        with open(fp,'w',encoding='utf-8') as f: f.write(html)
        print(f"  延期 → {fp}")
        # Workload page
        html = build_workload_page(project, groups, tasks)
        fp = os.path.join(BUILD_DIR, proj_l, '效率分析.html')
        with open(fp,'w',encoding='utf-8') as f: f.write(html)
        print(f"  效率分析 → {fp}")
        # Report page
        html = build_report_page(project, groups, tasks)
        fp = os.path.join(BUILD_DIR, proj_l, '项目汇报.html')
        with open(fp,'w',encoding='utf-8') as f: f.write(html)
        print(f"  项目汇报 → {fp}")
    
    fms_tasks = [t for t in all_tasks if t['_project']=='FMS']; gas_tasks = [t for t in all_tasks if t['_project']=='GAS']
    fms_groups, fms_undone = categorize_undone(fms_tasks); gas_groups, gas_undone = categorize_undone(gas_tasks)
    count_overdue(fms_undone); count_overdue(gas_undone)
    
    html = build_main_index(fms_groups, gas_groups, fms_tasks, gas_tasks, date_dir)
    fp = os.path.join(BUILD_DIR, 'index.html')
    with open(fp,'w',encoding='utf-8') as f: f.write(html)
    print(f"\n主报告中心 → {fp}\n完成！")

if __name__ == '__main__': main()
