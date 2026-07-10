import json, datetime, subprocess

now = datetime.datetime.now()
now_str = now.strftime('%Y-%m-%d %H:%M')
WEEKDAYS = ['周一','周二','周三','周四','周五','周六','周日']
weekday_str = WEEKDAYS[now.weekday()]
date_display = f'{now_str} {weekday_str}'

with open('/Users/crystal/WorkBuddy/禅道任务/authoritative_hours.json') as f: auth = json.load(f)
with open('/Users/crystal/WorkBuddy/禅道任务/effort_data.json') as f: effort = json.load(f)
with open('/Users/crystal/WorkBuddy/禅道任务/person_details.json') as f: pd = json.load(f)
with open('/Users/crystal/WorkBuddy/禅道任务/overdue_tasks.json') as f: od = json.load(f)
ot = od.get('total',0); obp = od.get('by_person',{}); oa = [t for ts in obp.values() for t in ts]
with open('/Users/crystal/WorkBuddy/禅道任务/quality_monitor_data.json') as f: qm = json.load(f)
qa1 = qm.get('analysis1',[]); qa2 = qm.get('analysis2',[]); qa3 = qm.get('analysis3',[]); qa4 = qm.get('analysis4',[])
qs = qm.get('summary',{})

TYPE_MAP = {
    'ab1_needs_research': '需求调研(#ab1_needs_research)',
    'ab2_request_des': '需求设计(#ab2_request_des)',
    'ab3_request_check': '需求验收(#ab3_request_check)',
    'a_dev4_control': '后端开发(#a_dev4_control)',
    'a_dev2_front': '前端开发(#a_dev2_front)',
    'ae2_test': '测试(#ae2_test)',
    'ad1_UI_des': 'UI设计(#ad1_UI_des)',
    'a_dev': '开发任务(#a_dev)',
}

EXCLUDE = {'苏方进', '黎思斯', '张旭', '余晨伟', '蔡能', '程迎娣', '胡丹'}
BASE_LOAD = 23 * 8  # 184h, 7月全月标准（23个工作日）
HOLIDAYS = set()
workdays = []
for m, end_d in [(7, 31)]:
    for d in range(1, end_d+1):
        dt = datetime.date(2026, m, d)
        ds = dt.strftime('%Y-%m-%d')
        if dt.weekday() < 5 and ds not in HOLIDAYS:
            workdays.append(ds)

today_str = now.strftime('%Y-%m-%d')
W_TODAY = len([d for d in workdays if d <= today_str])  # 工作日至今天
W_MONTH = len(workdays)  # 全月23天
W25, W26 = W_MONTH, W_MONTH
PAS, GOOD, OVER = 8*W25, 9*W25, 8*W25+30
PAS2, GOOD2, OVER2 = 8*W26, 9*W26, 8*W26+30  # 184, 207, 214

print(f"7月工作日: 月{W_MONTH}天, 至今天{W_TODAY}天")

ed, eu = effort['effort_daily'], effort['effort_update_days']

# Find last workday before today for "yesterday" reference
last_wd = [d for d in workdays if d < today_str][-1] if workdays else today_str
yday_label = last_wd[5:]  # MM-DD

pl = []
for n, a in auth.items():
    if n in EXCLUDE: continue
    u = set(eu.get(n,[]))
    w = [d for d in workdays if d <= today_str]
    up = [d for d in u if d <= today_str]
    ms = len([d for d in w if d not in u])
    th = a['total_hours']
    eh = a.get('estimated_hours', 0)
    est_load = round(eh / BASE_LOAD * 100, 1) if BASE_LOAD else 0
    cons_load = round(th / BASE_LOAD * 100, 1) if BASE_LOAD else 0
    av = round(th/max(len(up),1),1)
    pc = round(th/GOOD2*100,1)
    ip = 'GAS' if '海外售后' in a['project'] else ('FMS' if '销售财务' in a['project'] else 'OTHER')
    st = 'warning' if th<30 else ('good' if pc>=48 else 'ok')
    pl.append(dict(name=n,dept=a['dept'],project=ip,total=th,estimated=eh,est_load=est_load,cons_load=cons_load,
        progress=pc,avg_daily=av,
        yesterday=ed.get(n,{}).get(last_wd,0),update_days=len(up),missed_days=ms,status=st,
        biaobing=204<=th<=207))

pl.sort(key=lambda p:(0 if p['project']=='GAS' else 1 if p['project']=='FMS' else 2,p['total']))
ff=[p for p in pl if p['project'] in ('FMS','GAS')]
gf=[p for p in pl if p['project']=='GAS']; fm=[p for p in pl if p['project']=='FMS']
yc=len([p for p in ff if p['yesterday']>0]); wr=[p for p in ff if p['status']=='warning']
ym=[p for p in ff if p['yesterday']==0]; sp=[p for p in ff if p['update_days']<5]
for n in pd: pd[n].sort(key=lambda t:t['actual_finish'],reverse=True)

def tier_tag(th, pa, go, ov):
    if th < pa: return '#dc2626', '未达标', 'warn-tag'
    elif th < go: return '#d97706', '及格', 'pass-tag'
    elif th < ov: return '#059669', '良好', 'met-tag'
    return '#dc2626', '超标', 'exceed-tag'

def render_row(p, show_project):
    tc = '#059669' if p['progress']>=48 else '#d97706' if p['progress']>=30 else '#dc2626'
    mc = '#dc2626' if p['missed_days']>=3 else '#6b7280'
    st = p['status']
    c1, t1, g1 = tier_tag(p['total'], PAS2, GOOD2, OVER2)
    c2, t2, g2 = tier_tag(p['total'], PAS2, GOOD2, OVER2)
    
    h = '<tr class="data-row" onclick="toggleDetail(this,\'' + p['name'] + '\')"><td>'
    if show_project:
        pb = 'gas' if p['project']=='GAS' else 'fms' if p['project']=='FMS' else 'ok'
        h += '<span class="badge ' + pb + '">' + p['project'] + '</span></td><td>'
    bb = ' <span style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff;font-size:10px;padding:1px 6px;border-radius:8px;font-weight:700;margin-left:4px;vertical-align:2px">标兵</span>' if p.get('biaobing') else ''
    h += '<div class="name-cell"><span class="arrow">▶</span> ' + p['name'] + bb + '</div></td>'
    h += '<td>' + p['dept'] + '</td>'
    h += '<td><b style="color:' + tc + '">' + "{:.1f}".format(p['total']) + 'h</b> / ' + str(GOOD2) + 'h</td>'
    h += '<td><div style="display:flex;align-items:center;gap:6px;"><span style="font-weight:600;font-size:13px;min-width:35px">' + str(p['progress']) + '%</span><div class="progress-bar" style="flex:1;min-width:40px"><div class="progress-fill ' + st + '" style="width:' + str(min(p['progress'],100)) + '%"></div></div></div></td>'
    h += '<td style="color:' + c1 + ';font-weight:600">' + "{:.1f}".format(p['total']) + 'h <span class="' + g1 + '">' + t1 + '</span></td>'
    h += '<td>' + str(p['update_days']) + '天 / ' + str(W26) + '天</td>'
    h += '<td style="color:' + mc + ';font-size:13px">' + str(p['missed_days']) + '天</td>'
    elr = p['est_load']
    clr = p['cons_load']
    # 负载率颜色: <100%正常, 100-150%警戒橙, >=150%超载红
    def load_color(rate):
        if rate >= 150: return '#dc2626'  # 红-超载
        if rate >= 100: return '#d97706'  # 橙-警戒
        return '#1d4ed8'  # 蓝-正常
    elc = load_color(elr)
    clc = load_color(clr)
    h += '<td style="color:' + elc + ';font-weight:600">' + str(elr) + '%</td>'
    h += '<td style="color:' + clc + ';font-weight:600">' + str(clr) + '%</td></tr>\n'
    
    dc = '11' if show_project else '10'
    h += '<tr class="detail-row" id="detail-' + p['name'] + '"><td colspan="' + dc + '"><div class="detail-wrap" id="detail-wrap-' + p['name'] + '"></div></td></tr>\n'
    return h

def render_panel(pid, pp, show_project=False):
    active = ' active' if pid=='fms' else ''
    h = '<div class="panel' + active + '" id="panel-' + pid + '"><div class="table-wrap">'
    h += '<div class="legend">'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#dc2626"></div> 超标（&ge;' + str(OVER2) + 'h）</div>'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#059669"></div> 良好（' + str(GOOD2) + '-' + str(OVER2-1) + 'h）</div>'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#d97706"></div> 及格（' + str(PAS2) + '-' + str(GOOD2-1) + 'h）</div>'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#dc2626"></div> 未达标（&lt;' + str(PAS2) + 'h）</div>'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#dc2626"></div> 超载 ≥150%</div>'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#d97706"></div> 警戒 100-150%</div>'
    h += '<div class="legend-item"><div class="legend-dot" style="background:#1d4ed8"></div> 正常 &lt;100%</div></div>'
    h += '<table><thead><tr>'
    if show_project: h += '<th>项目</th>'
    h += '<th>人员</th><th>部门</th><th>累计工时</th><th>进度</th>'
    h += '<th>累计至' + now.strftime('%-m/%-d') + '<br>及格' + str(PAS2) + 'h 良好' + str(GOOD2) + 'h</th>'
    h += '<th>更新天数</th><th>缺失工作日</th><th>预计负载率</th><th>消耗负载率</th></tr></thead><tbody>'
    for p in pp:
        h += render_row(p, show_project)
    h += '</tbody></table></div></div>\n'
    return h

dj = json.dumps(pd, ensure_ascii=False)

CSS = """*{margin:0;padding:0;box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;background:#f0f2f5;color:#1a1a2e;line-height:1.6}.container{max-width:1400px;margin:0 auto;padding:24px}.header{background:linear-gradient(135deg,#1a56db 0%,#1e40af 100%);color:#fff;padding:32px 40px;border-radius:16px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center}.header h1{font-size:28px;font-weight:700}.header .date{font-size:16px;opacity:.85}.header .subtitle{font-size:14px;opacity:.7;margin-top:4px}.cards{display:grid;grid-template-columns:repeat(6,1fr);gap:16px;margin-bottom:24px}.card{background:#fff;border-radius:12px;padding:20px 24px;box-shadow:0 1px 3px rgba(0,0,0,.06);display:flex;flex-direction:column}.card .label{font-size:13px;color:#6b7280;margin-bottom:6px}.card .value{font-size:32px;font-weight:700}.card .sub{font-size:13px;color:#9ca3af;margin-top:4px}.card.green .value{color:#059669}.card.red .value{color:#dc2626}.card.blue .value{color:#1d4ed8}.card.orange .value{color:#d97706}.card.red .value{color:#dc2626}.overdue-card{cursor:pointer;border:2px solid #fecaca;box-shadow:0 0 12px rgba(220,38,38,0.15);transition:all .2s}.overdue-card:hover{box-shadow:0 0 20px rgba(220,38,38,0.3);transform:translateY(-2px)}.tabs{display:flex;margin-bottom:24px;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06)}.tab{flex:1;text-align:center;padding:14px 24px;font-size:15px;font-weight:600;cursor:pointer;border:none;background:#fff;color:#6b7280;transition:all .2s;position:relative}.tab:hover{color:#1d4ed8}.tab.active{color:#1d4ed8;background:#eff6ff}.tab.active::after{content:'';position:absolute;bottom:0;left:0;right:0;height:3px;background:#1d4ed8;border-radius:3px 3px 0 0}.tab .badge{display:inline-block;margin-left:6px;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:500;background:#d1fae5;color:#065f46}.panel{display:none}.panel.active{display:block}.table-wrap{background:#fff;border-radius:12px;overflow:auto;max-height:85vh;box-shadow:0 1px 3px rgba(0,0,0,.06)}table{width:100%;border-collapse:collapse;font-size:14px}thead{background:#f8fafc;position:sticky;top:0;z-index:10}th{padding:12px 14px;text-align:left;font-weight:600;font-size:13px;color:#6b7280;white-space:nowrap}td{padding:10px 14px;border-top:1px solid #f1f5f9}tr.data-row{cursor:pointer;transition:background .15s}tr.data-row:hover{background:#eff6ff!important}tr.data-row.expanded{background:#eff6ff!important}tr.data-row .name-cell{color:#1d4ed8;font-weight:600;display:flex;align-items:center;gap:6px}tr.data-row .name-cell .arrow{font-size:11px;transition:transform .2s;display:inline-block;color:#93c5fd}tr.data-row.expanded .name-cell .arrow{transform:rotate(90deg)}tr.detail-row{display:none;background:#f8fafc}tr.detail-row.show{display:table-row}tr.detail-row td{padding:0;border-top:none}.detail-wrap{padding:12px 20px 16px;border-top:1px solid #e5e7eb;max-height:300px;overflow-y:auto}.detail-wrap h4{font-size:14px;color:#1e40af;margin-bottom:8px}.detail-table{width:100%;font-size:13px}.detail-table thead{background:#eff6ff;position:sticky;top:0;z-index:10}.detail-table th{font-size:12px;padding:8px 10px;color:#475569}.detail-table td{font-size:12px;padding:6px 10px}.detail-table .st-done{color:#059669}.detail-table .st-closed{color:#6b7280}.badge{display:inline-block;padding:3px 10px;border-radius:10px;font-size:12px;font-weight:600}.badge.good{background:#d1fae5;color:#065f46}.badge.gas{background:#ede9fe;color:#5b21b6}.badge.fms{background:#e0e7ff;color:#3730a3}.badge.ok{background:#dbeafe;color:#1e40af}.progress-bar{width:100%;height:6px;background:#e5e7eb;border-radius:3px;margin-top:4px}.progress-fill{height:100%;border-radius:3px}.progress-fill.good{background:#10b981}.progress-fill.ok{background:#3b82f6}.progress-fill.warning{background:#f59e0b}.progress-fill.critical{background:#ef4444}.alerts{margin-bottom:24px}.alert{background:#fef2f2;border:1px solid #fecaca;border-left:4px solid #dc2626;padding:14px 20px;border-radius:8px;margin-bottom:8px;font-size:14px}.alert.warn{background:#fffbeb;border-color:#fde68a;border-left-color:#f59e0b}.exceed-tag{display:inline-block;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700;background:#fee2e2;color:#dc2626;margin-left:4px}.met-tag{display:inline-block;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700;background:#d1fae5;color:#065f46;margin-left:4px}.warn-tag{display:inline-block;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700;background:#fef3c7;color:#92400e;margin-left:4px}.pass-tag{display:inline-block;padding:2px 6px;border-radius:4px;font-size:11px;font-weight:700;background:#fef9c3;color:#a16207;margin-left:4px}.today-section{background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);border:1px solid #bfdbfe;border-radius:12px;padding:20px 24px;margin-top:24px}.today-section h3{font-size:16px;color:#1e40af;margin-bottom:12px}.summary-stats{display:flex;gap:24px;margin-top:8px;font-size:13px;flex-wrap:wrap}.summary-stats span{color:#6b7280}.summary-stats b{color:#1a1a2e}.legend{display:flex;gap:16px;margin-bottom:12px;font-size:12px;color:#6b7280;flex-wrap:wrap;padding:10px 14px}.legend-item{display:flex;align-items:center;gap:4px}.legend-dot{width:10px;height:10px;border-radius:2px}.note{background:#e0f2fe;border:1px solid #bae6fd;border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:13px;color:#0369a1}@media(max-width:768px){.cards{grid-template-columns:repeat(2,1fr)}.header{flex-direction:column;text-align:center;gap:12px}}.history-section{background:#fff;border-radius:12px;padding:20px 24px;margin-top:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)}.history-section h3{font-size:16px;font-weight:600;color:#1a1a2e;margin-bottom:12px}.history-links{display:flex;flex-wrap:wrap;gap:8px}.history-link{display:inline-block;padding:6px 14px;background:#eff6ff;color:#1d4ed8;border-radius:6px;font-size:13px;font-weight:500;text-decoration:none;transition:all .2s}.history-link:hover{background:#1d4ed8;color:#fff}.audit-section{background:#fff;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)}.audit-table{width:100%;border-collapse:collapse;font-size:13px}.audit-table th{background:#f8fafc;color:#6b7280;font-weight:600;text-align:left;padding:8px 12px;border-bottom:2px solid #e5e7eb;white-space:nowrap}.audit-table td{padding:8px 12px;border-bottom:1px solid #f3f4f6;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.audit-table tr:hover{background:#f9fafb}.audit-badge{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}.badge-ok{background:#d1fae5;color:#065f46}.badge-warn{background:#fecaca;color:#991b1b}.quality-card{transition:all .2s}.quality-card:hover{box-shadow:0 0 20px rgba(0,0,0,0.15);transform:translateY(-2px)}.qm-panel{animation:fadeIn .2s ease}@keyframes fadeIn{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:translateY(0)}}.qm-story-row{cursor:pointer;transition:background .15s}.qm-story-row:hover{background:#eff6ff}.qm-arrow{display:inline-block;transition:transform .2s;font-size:11px;margin-right:2px;color:#9ca3af}.qm-story-row.expanded .qm-arrow{transform:rotate(90deg)}.qm-detail-row{background:#fafbfc}.qm-detail-row td{padding:0!important}.qm-detail-wrap{padding:12px 20px}.qm-task-table{width:100%;border-collapse:collapse;font-size:12px}.qm-task-table th{background:#f1f5f9;color:#64748b;font-weight:600;padding:6px 10px;text-align:left;border-bottom:1px solid #e2e8f0;font-size:11px}.qm-task-table td{padding:5px 10px;border-bottom:1px solid #f1f5f9;color:#374151;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.qm-task-table tr:hover td{background:#f8fafc}"""

JS = """<script>
var taskData = """ + dj + """;
function switchTab(n){
  document.querySelectorAll('.panel').forEach(function(p){p.classList.remove('active')});
  document.querySelectorAll('.tab').forEach(function(t){t.classList.remove('active')});
  document.getElementById('panel-'+n).classList.add('active');
  event.target.classList.add('active');
}
function toggleDetail(r,n){
  var dr=document.getElementById('detail-'+n);
  var io=dr.classList.contains('show');
  document.querySelectorAll('.detail-row.show').forEach(function(x){x.classList.remove('show')});
  document.querySelectorAll('.data-row.expanded').forEach(function(x){x.classList.remove('expanded')});
  if(!io){
    var w=document.getElementById('detail-wrap-'+n);
    if(!w.dataset.loaded){
      var ts=taskData[n]||[];
      var h='<h4>'+n+' - 任务明细（'+ts.length+'条）</h4>';
      h+='<table class="detail-table"><thead><tr><th>执行</th><th>任务名称</th><th>状态</th><th>完成日期</th><th>工时(h)</th></tr></thead><tbody>';
      ts.forEach(function(t){
        var sc=t.status==='已完成'?'st-done':'st-closed';
        h+='<tr><td>'+(t.execution||'')+'</td><td>'+t.task_name+'</td><td class="'+sc+'">'+t.status+'</td><td>'+t.actual_finish+'</td><td style="font-weight:600">'+t.consumed+'</td></tr>';
      });
      h+='</tbody></table>';
      w.innerHTML=h;
      w.dataset.loaded='1';
    }
    dr.classList.add('show');
    r.classList.add('expanded');
  }
}
function toggleOverdue(){
  var d=document.getElementById('overdue-detail');
  if(d.style.display==='none'){d.style.display='block'}
  else{d.style.display='none'}
}
function toggleQuality(){
  var d=document.getElementById('quality-detail');
  if(d.style.display==='none'){d.style.display='block'}
  else{d.style.display='none'}
}
function switchQMTab(tabId,btn){
  document.querySelectorAll('.qm-panel').forEach(function(p){p.style.display='none'});
  document.querySelectorAll('.qm-tab').forEach(function(t){t.style.color='#6b7280';t.style.borderBottomColor='transparent'});
  document.getElementById('qm-tab-'+tabId).style.display='block';
  btn.style.color='#1d4ed8';
  btn.style.borderBottomColor='#1d4ed8';
}
function toggleQMTaskRow(row,sid){
  var detail=document.getElementById('qm-detail-'+sid);
  if(!detail) return;
  var isOpen=detail.style.display!=='none';
  // Close all others first
  document.querySelectorAll('.qm-detail-row').forEach(function(d){d.style.display='none'});
  document.querySelectorAll('.qm-story-row.expanded').forEach(function(r){r.classList.remove('expanded')});
  if(!isOpen){
    detail.style.display='';
    row.classList.add('expanded');
  }
}
</script>
"""

# Count stats
b1=len([p for p in ff if p['total']<PAS2]); p1=len([p for p in ff if PAS2<=p['total']<GOOD2])
g1=len([p for p in ff if GOOD2<=p['total']<OVER2]); o1=len([p for p in ff if p['total']>=OVER2])

with open(f'/Users/crystal/WorkBuddy/禅道任务/工时监控周报_{now.strftime("%Y-%m-%d")}.html', 'w', encoding='utf-8') as f:
    f.write('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>FMS & GAS 工时监控周报 | ' + now.strftime('%Y-%m-%d') + '</title><style>' + CSS + '</style></head><body><div class="container">')
    f.write('<div class="header"><div><h1>FMS & GAS 工时监控周报</h1></div><div class="date">' + date_display + '</div></div>')
    f.write('<div class="cards">')
    f.write('<div class="card blue"><div class="label">FMS+GAS 总人数</div><div class="value">' + str(len(ff)) + '</div><div class="sub">FMS ' + str(len(fm)) + '人 / GAS ' + str(len(gf)) + '人</div></div>')
    bb_count = len([p for p in ff if p.get('biaobing')])
    bb_names = '、'.join(p['name'] for p in ff if p.get('biaobing'))
    f.write('<div class="card green"><div class="label">累计至' + now.strftime('%-m/%-d') + '（'+str(W_TODAY)+'天）</div><div class="value">良好' + str(GOOD2) + 'h</div><div class="sub">及格' + str(PAS2) + 'h | 超标' + str(OVER2) + 'h</div></div>')
    if bb_count:
        f.write('<div class="card orange"><div class="label">标兵 204-207h</div><div class="value">' + str(bb_count) + '人</div><div class="sub">' + bb_names + '</div></div>')
    # Quality monitoring stats
    qm_warn_hours = qs.get('analysis1_warnings',0) + qs.get('analysis2_warnings',0)
    qm_warn_role = qs.get('analysis3_warnings',0)
    qm_warn_type = qs.get('analysis4_warnings',0)
    qm_time_range = qs.get('time_range','7/1-至今')
    qm_warn_level = 'red' if (qm_warn_hours + qm_warn_role + qm_warn_type) > 0 else 'green'

    o_ps = {}
    for t in oa: o_ps[t['assignedTo']] = o_ps.get(t['assignedTo'],0) + 1
    o_sub = '、'.join(f'{p}×{c}' for p,c in sorted(o_ps.items(),key=lambda x:-x[1])[:4])
    f.write('<div class="card red overdue-card" onclick="toggleOverdue()"><div class="label">延期任务统计 <span style="font-size:11px">点击展开</span></div><div class="value">' + str(ot) + '个</div><div class="sub">' + o_sub + '</div></div>')
    qm_label_color = '#059669' if qm_warn_level == 'green' else '#dc2626'
    f.write('<div class="card quality-card ' + qm_warn_level + '" onclick="toggleQuality()" style="cursor:pointer;border:2px solid ' + ('#bbf7d0' if qm_warn_level=='green' else '#fecaca') + '"><div class="label">工时质量监控 <span style="font-size:12px;color:#6b7280">点击展开</span></div><div style="display:flex;gap:20px;margin-top:8px">')
    f.write('<div style="flex:1"><div class="value" style="font-size:22px;color:' + qm_label_color + '">' + str(qm_warn_hours) + '</div><div class="sub">工时超标</div></div>')
    f.write('<div style="flex:1"><div class="value" style="font-size:22px;color:' + ('#dc2626' if qm_warn_role>0 else '#059669') + '">' + str(qm_warn_role) + '</div><div class="sub">角色缺失</div></div>')
    f.write('<div style="flex:1"><div class="value" style="font-size:22px;color:' + ('#dc2626' if qm_warn_type>0 else '#059669') + '">' + str(qm_warn_type) + '</div><div class="sub">类型异常</div></div>')
    f.write('</div></div>')
    f.write('<div class="card green"><div class="label">' + yday_label + ' ' + str(yc) + '人有日志</div><div class="value">' + str(len(ym)) + '人需关注</div><div class="sub">工作日统计</div></div>')
    # Yesterday summary card
    y_hours = sum(ed.get(p['name'],{}).get(last_wd,0) for p in ff if p['yesterday']>0)
    f.write('<div class="card blue"><div class="label">' + yday_label + ' 昨日概况</div><div class="value">' + "{:.1f}".format(y_hours) + 'h</div><div class="sub">' + str(yc) + '人共' + str(len(ff)) + '人</div></div>')
    f.write('</div>')
    # Overdue detail
    o_w = sum(1 for t in oa if t['status']=='wait'); o_d = sum(1 for t in oa if t['status']=='doing')
    o_pc = len(obp); o_mx = max((t['overdue_days'] for t in oa),default=0)
    f.write('<div id="overdue-detail" style="display:none;background:#fff;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)">')
    f.write('<h3 style="margin:0 0 16px;font-size:18px;color:#1a1a2e">🚨 延期任务统计报告</h3>')
    f.write('<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:20px">')
    f.write('<div style="background:#fef2f2;border-radius:8px;padding:14px;text-align:center"><div style="font-size:24px;font-weight:700;color:#dc2626">'+str(ot)+'</div><div style="font-size:12px;color:#6b7280;margin-top:4px">延期任务总数</div></div>')
    f.write('<div style="background:#fff7ed;border-radius:8px;padding:14px;text-align:center"><div style="font-size:24px;font-weight:700;color:#d97706">'+str(o_w)+'</div><div style="font-size:12px;color:#6b7280;margin-top:4px">待处理</div></div>')
    f.write('<div style="background:#eff6ff;border-radius:8px;padding:14px;text-align:center"><div style="font-size:24px;font-weight:700;color:#1d4ed8">'+str(o_d)+'</div><div style="font-size:12px;color:#6b7280;margin-top:4px">进行中</div></div>')
    f.write('<div style="background:#f0fdf4;border-radius:8px;padding:14px;text-align:center"><div style="font-size:24px;font-weight:700;color:#059669">'+str(o_mx)+'天</div><div style="font-size:12px;color:#6b7280;margin-top:4px">最长超期</div></div>')
    f.write('<div style="background:#f8fafc;border-radius:8px;padding:14px;text-align:center"><div style="font-size:24px;font-weight:700;color:#6b7280">'+str(o_pc)+'</div><div style="font-size:12px;color:#6b7280;margin-top:4px">涉及人员</div></div></div>')
    for pn,ts in sorted(obp.items(),key=lambda x:-len(x[1])):
        tw=sum(1 for t in ts if t['status']=='wait'); td=sum(1 for t in ts if t['status']=='doing')
        es=sum(t['estimate'] for t in ts); cs=sum(t['consumed'] for t in ts); ls=sum(t['left'] for t in ts); mx=max(t['overdue_days'] for t in ts)
        f.write('<details open style="margin-bottom:16px"><summary style="cursor:pointer;font-weight:600;font-size:15px;padding:10px 14px;background:#f8fafc;border-radius:8px;margin-bottom:8px">'+pn+' — 共'+str(len(ts))+'个 <span style="color:#d97706">待处理'+str(tw)+'</span> <span style="color:#1d4ed8">进行中'+str(td)+'</span> <span style="color:#9ca3af;font-weight:400">最长'+str(mx)+'天 预估'+str(int(es))+'h/消耗'+str(int(cs))+'h/剩余'+str(int(ls))+'h</span></summary>')
        f.write('<div class="table-wrap"><table><thead><tr><th>ID</th><th>任务名称</th><th>状态</th><th>优先级</th><th>类型</th><th>所属迭代</th><th>截止日期</th><th>超期天数</th><th>预估h</th><th>消耗h</th><th>剩余h</th></tr></thead><tbody>')
        for t in ts:
            sx='进行中' if t['status']=='doing' else '待处理'; sc='color:#1d4ed8;font-weight:600' if t['status']=='doing' else 'color:#d97706;font-weight:600'
            f.write('<tr><td>'+str(t['id'])+'</td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+str(t['name'])+'</td><td style="'+sc+'">'+sx+'</td><td>'+str(t['priority'])+'</td><td>'+str(t['type'])+'</td><td>'+str(t['execution'])+'</td><td>'+str(t['deadline'])+'</td><td style="color:#dc2626;font-weight:600">'+str(t['overdue_days'])+'天</td><td>'+str(int(t['estimate']))+'h</td><td>'+str(int(t['consumed']))+'h</td><td>'+str(int(t['left']))+'h</td></tr>')
        f.write('</tbody></table></div></details>')
    f.write('</div>')
    # Quality monitoring detail section
    f.write('<div id="quality-detail" style="display:none;background:#fff;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 1px 3px rgba(0,0,0,.06)">')
    f.write('<h3 style="margin:0 0 16px;font-size:18px;color:#1a1a2e">工时质量监控报告 <span style="font-size:13px;color:#9ca3af;font-weight:400">统计范围：已完成且有完成者的任务 | ' + qm_time_range + '</span></h3>')
    f.write('<div style="display:flex;gap:0;margin-bottom:20px;border-bottom:2px solid #e5e7eb">')
    f.write('<button onclick="switchQMTab(\'qm1\',this)" class="qm-tab active" style="padding:10px 18px;border:none;background:none;font-size:14px;font-weight:600;color:#1d4ed8;cursor:pointer;border-bottom:2px solid #1d4ed8;margin-bottom:-2px">需求总工时预警 <span style="font-size:11px;background:#fef2f2;color:#dc2626;padding:1px 6px;border-radius:8px;margin-left:4px">' + str(len([a for a in qa1 if a["warning"]=="red"])) + '红 ' + str(len([a for a in qa1 if a["warning"]=="yellow"])) + '黄</span></button>')
    f.write('<button onclick="switchQMTab(\'qm2\',this)" class="qm-tab" style="padding:10px 18px;border:none;background:none;font-size:14px;font-weight:600;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px">后端开发工时 <span style="font-size:11px;background:#fef2f2;color:#dc2626;padding:1px 6px;border-radius:8px;margin-left:4px">阈值245h</span></button>')
    f.write('<button onclick="switchQMTab(\'qm3\',this)" class="qm-tab" style="padding:10px 18px;border:none;background:none;font-size:14px;font-weight:600;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px">角色工时缺失 <span style="font-size:11px;background:#fef2f2;color:#dc2626;padding:1px 6px;border-radius:8px;margin-left:4px">' + str(len(qa3)) + '个</span></button>')
    f.write('<button onclick="switchQMTab(\'qm4\',this)" class="qm-tab" style="padding:10px 18px;border:none;background:none;font-size:14px;font-weight:600;color:#6b7280;cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-2px">任务类型校验 <span style="font-size:11px;background:' + ('#fef2f2;color:#dc2626' if qa4 else '#f0fdf4;color:#059669') + ';padding:1px 6px;border-radius:8px;margin-left:4px">' + (str(len(qa4))+'个异常' if qa4 else '全部正确') + '</span></button>')
    f.write('</div>')
    # Tab 1: 需求总工时
    f.write('<div id="qm-tab-qm1" class="qm-panel" style="display:block">')
    if qa1:
        si = 0
        f.write('<div class="table-wrap"><table><thead><tr><th>需求名称</th><th>已完成工时</th><th>预计总工时</th><th>已完成任务数</th><th>状态</th></tr></thead><tbody>')
        for a in qa1:
            sid = str(a.get('story_id', f'q1_{si}')); si += 1; wc = '#dc2626' if a['warning']=='red' else ('#d97706' if a['warning']=='yellow' else '#059669'); wt = '超标>450h' if a['warning']=='red' else ('偏高350-450h' if a['warning']=='yellow' else '正常')
            uc = a.get('undone_count', 0)
            u_badge = ' <span style="font-size:11px;color:#f59e0b">+' + str(uc) + '未完成</span>' if uc > 0 else ''
            ct = a.get('consumed_total', a.get('total_hours', 0))
            et = a.get('estimated_total', a.get('estimated_hours', 0))
            f.write('<tr class="qm-story-row" onclick="toggleQMTaskRow(this,\'' + sid + '\')"><td style="max-width:400px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer" title="' + a['story_name'] + '"><span class="qm-arrow">▶</span> ' + a['story_name'] + u_badge + '</td><td style="font-weight:600;color:' + wc + '">' + str(ct) + 'h</td><td style="font-weight:600">' + str(et) + 'h</td><td>' + str(a['task_count']) + '</td><td style="color:' + wc + ';font-weight:600">' + wt + '</td></tr>')
            tasks = sorted(a.get('tasks', []), key=lambda x: x.get('person',''))
            dc = [t for t in tasks if t.get('done')]; ic = [t for t in tasks if not t.get('done')]
            h = '<tr class="qm-detail-row" id="qm-detail-' + sid + '" style="display:none"><td colspan="4"><div class="qm-detail-wrap">'
            if dc:
                h += '<div style="font-size:12px;font-weight:600;color:#64748b;margin:8px 0 4px;padding:4px 8px;background:#f1f5f9;border-radius:4px;display:inline-block">已完成 <b>' + str(len(dc)) + '</b> 个</div>'
                h += '<table class="qm-task-table"><thead><tr><th>任务名称</th><th>负责人</th><th>类型</th><th>工时</th><th>版本</th><th>完成日期</th></tr></thead><tbody>'
                for t in dc:
                    h += '<tr><td title="' + t.get('name','') + '">' + t.get('name','') + '</td><td>' + t.get('person','') + '</td><td>' + TYPE_MAP.get(t.get('type',''), t.get('type','')) + '</td><td style="font-weight:600">' + str(t.get('consumed',0)) + 'h</td><td>' + t.get('execution','') + '</td><td style="color:#059669;font-weight:600">' + t.get('finishedDate','') + '</td></tr>'
                h += '</tbody></table>'
            if ic:
                h += '<div style="font-size:12px;font-weight:600;color:#64748b;margin:8px 0 4px;padding:4px 8px;background:#f1f5f9;border-radius:4px;display:inline-block">未完成 <b>' + str(len(ic)) + '</b> 个</div>'
                h += '<table class="qm-task-table"><thead><tr><th>任务名称</th><th>负责人</th><th>类型</th><th>状态</th><th>截止日期</th><th>预估</th><th>剩余</th></tr></thead><tbody>'
                for t in ic:
                    sc = 'color:#3b82f6' if t.get('status')=='进行中' else 'color:#f59e0b'
                    h += '<tr><td title="' + t.get('name','') + '">' + t.get('name','') + '</td><td>' + t.get('person','') + '</td><td>' + TYPE_MAP.get(t.get('type',''), t.get('type','')) + '</td><td style="' + sc + ';font-weight:600">' + t.get('status','') + '</td><td>' + t.get('deadline','') + '</td><td>' + str(t.get('estimate',0)) + 'h</td><td style="font-weight:600">' + str(t.get('left',0)) + 'h</td></tr>'
                h += '</tbody></table>'
            h += '</div></td></tr>'
            f.write(h)
        f.write('</tbody></table></div>')
    else:
        f.write('<p style="color:#9ca3af;text-align:center;padding:20px">暂无已完成工时≥40h的需求</p>')
    f.write('</div>')
    # Tab 2: 后端开发工时
    f.write('<div id="qm-tab-qm2" class="qm-panel" style="display:none">')
    if qa2:
        si = 0
        f.write('<div class="table-wrap"><table><thead><tr><th>需求名称</th><th>已完成工时</th><th>预计总工时</th><th>负责人</th><th>状态</th></tr></thead><tbody>')
        for a in qa2:
            sid = str(a.get('story_id', f'q2_{si}')); si += 1; wc = '#dc2626' if a['warning']=='red' else '#059669'; wt = '超标>245h' if a['warning']=='red' else '正常'
            uc = a.get('undone_count', 0)
            u_badge = ' <span style="font-size:11px;color:#f59e0b">+' + str(uc) + '未完成</span>' if uc > 0 else ''
            bc = a.get('be_consumed_total', 0)
            be = a.get('be_estimated_total', 0)
            f.write('<tr class="qm-story-row" onclick="toggleQMTaskRow(this,\'' + sid + '\')"><td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer" title="' + a['story_name'] + '"><span class="qm-arrow">▶</span> ' + a['story_name'] + u_badge + '</td><td style="font-weight:600;color:' + wc + '">' + str(bc) + 'h</td><td style="font-weight:600">' + str(be) + 'h</td><td>' + a['max_task_person'] + '</td><td style="color:' + wc + ';font-weight:600">' + wt + '</td></tr>')
            tasks = sorted(a.get('tasks', []), key=lambda x: x.get('person',''))
            dc = [t for t in tasks if t.get('done')]; ic = [t for t in tasks if not t.get('done')]
            h = '<tr class="qm-detail-row" id="qm-detail-' + sid + '" style="display:none"><td colspan="4"><div class="qm-detail-wrap">'
            if dc:
                h += '<div style="font-size:12px;font-weight:600;color:#64748b;margin:8px 0 4px;padding:4px 8px;background:#f1f5f9;border-radius:4px;display:inline-block">已完成 <b>' + str(len(dc)) + '</b> 个</div>'
                h += '<table class="qm-task-table"><thead><tr><th>任务名称</th><th>负责人</th><th>类型</th><th>工时</th><th>版本</th><th>完成日期</th></tr></thead><tbody>'
                for t in dc:
                    h += '<tr><td title="' + t.get('name','') + '">' + t.get('name','') + '</td><td>' + t.get('person','') + '</td><td>' + TYPE_MAP.get(t.get('type',''), t.get('type','')) + '</td><td style="font-weight:600">' + str(t.get('consumed',0)) + 'h</td><td>' + t.get('execution','') + '</td><td style="color:#059669;font-weight:600">' + t.get('finishedDate','') + '</td></tr>'
                h += '</tbody></table>'
            if ic:
                h += '<div style="font-size:12px;font-weight:600;color:#64748b;margin:8px 0 4px;padding:4px 8px;background:#f1f5f9;border-radius:4px;display:inline-block">未完成 <b>' + str(len(ic)) + '</b> 个</div>'
                h += '<table class="qm-task-table"><thead><tr><th>任务名称</th><th>负责人</th><th>类型</th><th>状态</th><th>截止日期</th><th>预估</th><th>剩余</th></tr></thead><tbody>'
                for t in ic:
                    sc = 'color:#3b82f6' if t.get('status')=='进行中' else 'color:#f59e0b'
                    h += '<tr><td title="' + t.get('name','') + '">' + t.get('name','') + '</td><td>' + t.get('person','') + '</td><td>' + TYPE_MAP.get(t.get('type',''), t.get('type','')) + '</td><td style="' + sc + ';font-weight:600">' + t.get('status','') + '</td><td>' + t.get('deadline','') + '</td><td>' + str(t.get('estimate',0)) + 'h</td><td style="font-weight:600">' + str(t.get('left',0)) + 'h</td></tr>'
                h += '</tbody></table>'
            h += '</div></td></tr>'
            f.write(h)
        f.write('</tbody></table></div>')
    else:
        f.write('<p style="color:#9ca3af;text-align:center;padding:20px">暂无后端开发任务数据</p>')
    f.write('</div>')
    # Tab 3: 角色工时缺失
    f.write('<div id="qm-tab-qm3" class="qm-panel" style="display:none">')
    if qa3:
        si = 0
        f.write('<div class="table-wrap"><table><thead><tr><th style="min-width:250px">需求名称</th><th colspan="3" style="text-align:center;background:#eff6ff;font-size:11px">产品工时</th><th colspan="3" style="text-align:center;background:#f0fdf4;font-size:11px">开发工时</th><th style="font-size:11px">测试</th><th style="font-size:11px">UI</th><th style="font-size:11px">总计</th><th style="min-width:80px;max-width:130px;font-size:11px">缺失角色</th></tr>')
        f.write('<tr style="font-size:10px"><th></th><th style="min-width:35px">调研</th><th style="min-width:35px">设计</th><th style="min-width:35px">验收</th><th style="min-width:35px">后端</th><th style="min-width:35px">前端</th><th style="min-width:35px">架构</th><th style="min-width:35px"></th><th style="min-width:32px"></th><th style="min-width:35px"></th><th style="min-width:80px;max-width:130px"></th></tr></thead><tbody>')
        for a in qa3:
            sid = str(a.get('story_id', f'q3_{si}')); si += 1; ms = '、'.join(a['missing_roles'])
            uc = a.get('undone_count', 0)
            u_badge = ' <span style="font-size:10px;color:#f59e0b">+' + str(uc) + '</span>' if uc > 0 else ''
            f.write('<tr class="qm-story-row" onclick="toggleQMTaskRow(this,\'' + sid + '\')"><td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer" title="' + a['story_name'] + '"><span class="qm-arrow">▶</span> ' + a['story_name'] + u_badge + '</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['research_hours']==0 and '需求调研' in a['missing_roles'] else '#059669') + '">' + str(a['research_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['design_hours']==0 and '需求设计' in a['missing_roles'] else '#059669') + '">' + str(a['design_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['check_hours']==0 and '需求验收' in a['missing_roles'] else '#059669') + '">' + str(a['check_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['backend_hours']==0 and '后端开发' in a['missing_roles'] else '#059669') + '">' + str(a['backend_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['frontend_hours']==0 and '前端开发' in a['missing_roles'] else '#059669') + '">' + str(a['frontend_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['arch_hours']==0 and '开发任务' in a['missing_roles'] else '#059669') + '">' + str(a['arch_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;color:' + ('#dc2626;font-weight:600' if a['test_hours']==0 else '#059669') + '">' + str(a['test_hours']) + 'h</td>')
            f.write('<td style="font-size:12px">' + str(a['ui_hours']) + 'h</td>')
            f.write('<td style="font-size:12px;font-weight:600">' + str(a['total_hours']) + 'h</td>')
            f.write('<td style="color:#dc2626;font-weight:600;font-size:10px;max-width:130px;line-height:1.4;word-break:keep-all" title="缺 ' + ms + '">' + ms + '</td></tr>')
            tasks = sorted(a.get('tasks', []), key=lambda x: x.get('person',''))
            dc = [t for t in tasks if t.get('done')]; ic = [t for t in tasks if not t.get('done')]
            h = '<tr class="qm-detail-row" id="qm-detail-' + sid + '" style="display:none"><td colspan="11"><div class="qm-detail-wrap">'
            if dc:
                h += '<div style="font-size:12px;font-weight:600;color:#64748b;margin:8px 0 4px;padding:4px 8px;background:#f1f5f9;border-radius:4px;display:inline-block">已完成 <b>' + str(len(dc)) + '</b> 个</div>'
                h += '<table class="qm-task-table"><thead><tr><th>任务名称</th><th>负责人</th><th>类型</th><th>工时</th><th>版本</th><th>完成日期</th></tr></thead><tbody>'
                for t in dc:
                    h += '<tr><td title="' + t.get('name','') + '">' + t.get('name','') + '</td><td>' + t.get('person','') + '</td><td>' + TYPE_MAP.get(t.get('type',''), t.get('type','')) + '</td><td style="font-weight:600">' + str(t.get('consumed',0)) + 'h</td><td>' + t.get('execution','') + '</td><td style="color:#059669;font-weight:600">' + t.get('finishedDate','') + '</td></tr>'
                h += '</tbody></table>'
            if ic:
                h += '<div style="font-size:12px;font-weight:600;color:#64748b;margin:8px 0 4px;padding:4px 8px;background:#f1f5f9;border-radius:4px;display:inline-block">未完成 <b>' + str(len(ic)) + '</b> 个</div>'
                h += '<table class="qm-task-table"><thead><tr><th>任务名称</th><th>负责人</th><th>类型</th><th>状态</th><th>截止日期</th><th>预估</th><th>剩余</th></tr></thead><tbody>'
                for t in ic:
                    sc = 'color:#3b82f6' if t.get('status')=='进行中' else 'color:#f59e0b'
                    h += '<tr><td title="' + t.get('name','') + '">' + t.get('name','') + '</td><td>' + t.get('person','') + '</td><td>' + TYPE_MAP.get(t.get('type',''), t.get('type','')) + '</td><td style="' + sc + ';font-weight:600">' + t.get('status','') + '</td><td>' + t.get('deadline','') + '</td><td>' + str(t.get('estimate',0)) + 'h</td><td style="font-weight:600">' + str(t.get('left',0)) + 'h</td></tr>'
                h += '</tbody></table>'
            h += '</div></td></tr>'
            f.write(h)
        f.write('</tbody></table></div>')
    else:
        f.write('<p style="color:#059669;text-align:center;padding:20px">所有需求岗位工时覆盖完整</p>')
    f.write('</div>')
    # Tab 4: 任务类型校验
    f.write('<div id="qm-tab-qm4" class="qm-panel" style="display:none">')
    if qa4:
        f.write('<div class="table-wrap"><table><thead><tr><th>人员</th><th>任务名称</th><th>实际类型</th><th>期望类型</th><th>所属需求</th><th>版本</th><th>工时</th></tr></thead><tbody>')
        for a in qa4:
            f.write('<tr><td>' + a['person'] + '</td><td style="max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + a['task_name'] + '">' + a['task_name'] + '</td><td style="color:#dc2626;font-weight:600">' + a['actual_type'] + '</td><td style="color:#059669">' + a['expected_type'] + '</td><td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + a['story_name'] + '">' + a['story_name'] + '</td><td>' + a['execution'] + '</td><td>' + str(a['hours']) + 'h</td></tr>')
        f.write('</tbody></table></div>')
    else:
        f.write('<p style="color:#059669;text-align:center;padding:20px">所有人员任务类型填写正确</p>')
    f.write('</div>')
    f.write('<div style="margin-top:16px;padding:12px;background:#f8fafc;border-radius:8px;font-size:13px;color:#6b7280">')
    f.write('<b>预警规则：</b> 需求已完成总工时&gt;450h红色预警，350-450h黄色预警（最低统计40h）| 需求下后端开发类型单任务最高&gt;245h预警 | 需求下产品/开发/测试任一角色工时为0则预警 | 按任务类型.xlsx标准校验（徐中然/何曦宇/连朔/蔡泽平按任务名匹配）')
    f.write('</div></div>')
    f.write('<div class="note">工时来源：禅道任务API（6个执行） | 负载率=工时÷(' + str(BASE_LOAD) + 'h)</div>')
    f.write('<div class="alerts">')
    if wr:
        for p in wr:
            f.write('<div class="alert"><strong>需关注</strong> — ' + p['name'] + '（' + p['dept'] + ' | ' + p['project'] + '）：累计仅 ' + "{:.1f}".format(p['total']) + 'h，更新 ' + str(p['update_days']) + ' 天，缺失 ' + str(p['missed_days']) + '个工作日</div>\n')
    if ym:
        f.write('<div class="alert warn"><strong>' + yday_label + '无日志</strong> — ' + '、'.join(p['name'] for p in ym) + '</div>\n')
    if sp:
        f.write('<div class="alert warn"><strong>更新频次偏低</strong> — ' + '、'.join(p['name'] + '(' + str(p['update_days']) + '天)' for p in sp) + '</div>\n')
    f.write('</div>\n')
    f.write('<div class="tabs"><button class="tab active" onclick="switchTab(\'fms\')">销售财务中台 FMS <span class="badge">' + str(len(fm)) + '人</span></button><button class="tab" onclick="switchTab(\'gas\')">海外售后 GAS <span class="badge">' + str(len(gf)) + '人</span></button><button class="tab" onclick="switchTab(\'summary\')">全量汇总 <span class="badge">' + str(len(pl)) + '人</span></button></div>\n')
    f.write(render_panel('fms', fm))
    f.write(render_panel('gas', gf))
    f.write(render_panel('summary', pl, True))
    f.write('<div class="today-section"><h3>评级统计</h3><div class="summary-stats">')
    f.write('<div><span>' + yday_label + '：</span><b style="color:#dc2626">未达标 ' + str(b1) + '人</b> | <b style="color:#d97706">及格 ' + str(p1) + '人</b> | <b style="color:#059669">良好 ' + str(g1) + '人</b> | <b style="color:#dc2626">超标 ' + str(o1) + '人</b></div>')
    f.write('<div><span>全月及格线' + str(PAS2) + 'h | 良好线' + str(GOOD2) + 'h | 超标线' + str(OVER2) + 'h</span></div>')
    f.write('</div></div>\n')
    # History card
    history_dates = ['07-03','07-02','06-30','06-29']
    history_html = '<div class="history-section"><h3>历史报告</h3><div class="history-links">'
    for d in history_dates:
        history_html += '<a href="history/2026-' + d + '.html" class="history-link">2026-' + d + '</a>'
    history_html += '</div></div>'
    f.write(history_html)
    f.write(JS)
    f.write('</div></body></html>')

subprocess.run(['cp', f'/Users/crystal/WorkBuddy/禅道任务/工时监控周报_{now.strftime("%Y-%m-%d")}.html', '/tmp/fms-gas-monitor/index.html'])

print(f"\nOK - {yday_label}({W26}天): 及格{PAS2}h 良好{GOOD2}h 超标{OVER2}h")
print(f"监控{len(ff)}人, {yc}人{yday_label}有日志, {len(ym)}人需关注")
print(f"{yday_label}评级: 未达标{b1} 及格{p1} 良好{g1} 超标{o1}")
