#!/usr/bin/env python3
"""静态文件服务器 + 禅道数据刷新接口"""
import json, subprocess, re, datetime
from flask import Flask, send_from_directory, jsonify, request

app = Flask(__name__)
BUILD_DIR = 'build'

@app.route('/')
def index():
    return send_from_directory(BUILD_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(BUILD_DIR, path)

@app.route('/api/refresh', methods=['POST'])
def refresh():
    try:
        TOKEN = subprocess.run(['curl', '-sk', '-X', 'POST',
            'https://ztpm.gree.com:8888/api.php/v2/users/login',
            '-H', 'Content-Type: application/json',
            '-d', '{"account":"260298","password":"Lss@530720"}'],
            capture_output=True, text=True, timeout=10).stdout
        TOKEN = json.loads(TOKEN).get('token', '')

        EXECS = {
            4519: '【2026】FMS-0630', 4651: '【2026】FMS-0715', 4697: '【2026】FMS-0725',
            4665: '【2026】FMS-0730', 4672: '【2026】FMS-0815', 4671: '【2026】FMS-0830',
            4527: '【2026】海外售后服务器迁移-0630', 4639: '【2026】海外售后v4.5-0630',
            4698: '【2026】海外售后v4.6.1', 4699: '【2026】海外售后v4.6.2'
        }
        GAS_IDS = {4527, 4639, 4698, 4699}
        EXCLUDE = {'苏方进', '黎思斯', '张旭', '余晨伟', '蔡能', '程迎娣', '胡丹'}

        # Collect all tasks
        all_tasks = []
        for eid, ename in EXECS.items():
            r = subprocess.run(['curl', '-sk',
                f'https://ztpm.gree.com:8888/api.php/v1/executions/{eid}/tasks?limit=2000',
                '-H', f'token: {TOKEN}'], capture_output=True, text=True, timeout=15)
            try: tasks = json.loads(r.stdout).get('tasks', [])
            except: continue
            is_gas = eid in GAS_IDS
            for t in tasks:
                fb = t.get('finishedBy', {}) or {}
                at = t.get('assignedTo', {}) or {}
                fname = fb.get('realname', '') if isinstance(fb, dict) else str(fb)
                aname = at.get('realname', '') if isinstance(at, dict) else str(at)
                all_tasks.append({
                    'name': t.get('name', ''), 'assignedTo': aname, 'finishedBy': fname,
                    'status': t.get('status', ''), 'consumed': t.get('consumed', 0) or 0,
                    'estimate': t.get('estimate', 0) or 0, 'left': t.get('left', 0) or 0,
                    'deadline': (t.get('deadline', '') or '')[:10],
                    'finishedDate': (t.get('finishedDate', '') or '')[:10],
                    'type': t.get('type', ''), 'execution': ename,
                    'story': str(t.get('story', 0)) if t.get('story') else '',
                    'project': 'GAS' if is_gas else 'FMS'
                })

        # Build authoritative_hours.json
        person_hours = {}
        known_depts = {}  # preserve existing dept
        try:
            with open('authoritative_hours.json') as f:
                for n, i in json.load(f).items():
                    if i.get('dept'): known_depts[n] = i['dept']
        except: pass

        for t in all_tasks:
            person = t['finishedBy']
            fd = t['finishedDate']
            if person and person not in EXCLUDE and fd >= '2026-07-01' and t['status'] in ('done', 'closed'):
                if person not in person_hours:
                    person_hours[person] = {'total_hours': 0, 'task_count': 0, 'estimated_hours': 0, 'dept': '', 'project': ''}
                person_hours[person]['total_hours'] += t['consumed']
                person_hours[person]['estimated_hours'] += t['estimate']
                person_hours[person]['task_count'] += 1
                if not person_hours[person]['project']:
                    person_hours[person]['project'] = '海外售后 GAS' if t['project'] == 'GAS' else '销售财务中台管理系统 FMS'

        # Add people with only incomplete tasks
        person_all = {}
        for t in all_tasks:
            done = t['status'] in ('done', 'closed')
            fd = t['finishedDate']
            person = t['finishedBy'] if (done and fd >= '2026-07-01' and t['finishedBy']) else t['assignedTo']
            if not person or person in EXCLUDE: continue
            if person not in person_all: person_all[person] = []
            if done and fd >= '2026-07-01':
                person_all[person].append({'execution': t['execution'], 'task_name': t['name'],
                    'status': '已完成', 'actual_finish': fd, 'deadline': '', 'consumed': t['consumed'],
                    'estimate': t['estimate'], 'left': t['left'], 'done': True})
            elif not done:
                person_all[person].append({'execution': t['execution'], 'task_name': t['name'],
                    'status': '进行中' if t['status'] == 'doing' else '待处理', 'actual_finish': '',
                    'deadline': t['deadline'], 'consumed': t['consumed'], 'estimate': t['estimate'],
                    'left': t['left'], 'done': False})

        for name in person_all:
            if name not in person_hours:
                person_hours[name] = {'total_hours': 0, 'task_count': 0, 'estimated_hours': 0, 'dept': known_depts.get(name, ''), 'project': ''}
                for t in person_all[name]:
                    if '海外售后' in t.get('execution', ''):
                        person_hours[name]['project'] = '海外售后 GAS'
                        break
                if not person_hours[name]['project']:
                    person_hours[name]['project'] = '销售财务中台管理系统 FMS'

        # Restore dept
        for n in person_hours:
            if not person_hours[n].get('dept') and n in known_depts:
                person_hours[n]['dept'] = known_depts[n]
            person_hours[n]['total_hours'] = round(person_hours[n]['total_hours'], 1)
            person_hours[n]['estimated_hours'] = round(person_hours[n]['estimated_hours'], 1)

        # Fix 全秋霞 space
        for k in list(person_hours.keys()):
            if k.rstrip() != k:
                person_hours[k.strip()] = person_hours.pop(k)

        with open('authoritative_hours.json', 'w') as f:
            json.dump(person_hours, f, ensure_ascii=False, indent=2)
        with open('person_all_tasks.json', 'w') as f:
            json.dump(person_all, f, ensure_ascii=False, indent=2)

        # Build quality_monitor_data
        story_tasks = {}
        for t in all_tasks:
            sid = t['story']
            if not sid or sid == '0': continue
            if sid not in story_tasks: story_tasks[sid] = []
            done = t['status'] in ('done', 'closed')
            fd = t['finishedDate']
            if done and fd >= '2026-07-01':
                story_tasks[sid].append({'name': t['name'], 'person': t['finishedBy'],
                    'type': t['type'], 'consumed': t['consumed'], 'estimate': t['estimate'],
                    'left': t['left'], 'finishedDate': fd, 'deadline': '', 'status': '已完成',
                    'execution': t['execution'], 'done': True})
            elif not done and t['assignedTo']:
                story_tasks[sid].append({'name': t['name'], 'person': t['assignedTo'],
                    'type': t['type'], 'consumed': t['consumed'], 'estimate': t['estimate'],
                    'left': t['left'], 'finishedDate': '', 'deadline': t['deadline'],
                    'status': '进行中' if t['status'] == 'doing' else '待处理',
                    'execution': t['execution'], 'done': False})

        # Fetch story names (first 20 most important)
        story_ids = list(story_tasks.keys())[:80]
        story_names = {}
        for sid in story_ids:
            try:
                r = subprocess.run(['curl', '-sk', f'https://ztpm.gree.com:8888/api.php/v1/stories/{sid}',
                    '-H', f'token: {TOKEN}'], capture_output=True, text=True, timeout=5)
                resp = json.loads(r.stdout)
                sd = resp.get('story', resp) if isinstance(resp, dict) else {}
                title = (sd or {}).get('title', '') if isinstance(sd, dict) else ''
                story_names[sid] = title or f'需求#{sid}'
            except: story_names[sid] = f'需求#{sid}'

        BACKEND_TYPES = {'devel', 'dev', 'devel:backend', 'a_dev4_control', 'a_dev2_front', 'devel:frontend'}
        analysis1, analysis2, analysis3 = [], [], []

        for sid, tasks in story_tasks.items():
            consumed = sum(t['consumed'] for t in tasks if t['done'])
            estimated = sum(t['estimate'] for t in tasks)
            undone = sum(1 for t in tasks if not t['done'])
            done_count = sum(1 for t in tasks if t['done'])
            if consumed >= 40:
                analysis1.append({'story_id': sid, 'story_name': story_names.get(sid, f'需求#{sid}'),
                    'total_hours': round(consumed, 1), 'consumed_total': round(consumed, 1),
                    'estimated_total': round(estimated, 1), 'task_count': done_count,
                    'undone_count': undone, 'tasks': tasks,
                    'warning': 'red' if estimated > 450 else ('yellow' if estimated > 350 else 'green')})

            be_tasks = [t for t in tasks if t.get('type') in BACKEND_TYPES]
            be_consumed = sum(t['consumed'] for t in be_tasks if t['done'])
            be_estimated = sum(t['estimate'] for t in be_tasks)
            if be_consumed >= 20:
                max_be = max(be_tasks, key=lambda t: t['consumed'], default={})
                analysis2.append({'story_id': sid, 'story_name': story_names.get(sid, f'需求#{sid}'),
                    'max_backend_hours': max_be.get('consumed', 0),
                    'max_task_person': max_be.get('person', ''), 'max_task_name': max_be.get('name', ''),
                    'be_consumed_total': round(be_consumed, 1), 'be_estimated_total': round(be_estimated, 1),
                    'undone_count': undone, 'tasks': tasks,
                    'warning': 'red' if be_consumed > 245 else 'green'})

        for sid, tasks in story_tasks.items():
            role_hours = {}
            for t in tasks:
                tp = t.get('type', '')
                if tp in ('devel:research', 'research'): role_hours['需求调研'] = role_hours.get('需求调研', 0) + (t['consumed'] if t['done'] else 0)
                elif tp in ('devel:design', 'design'): role_hours['需求设计'] = role_hours.get('需求设计', 0) + (t['consumed'] if t['done'] else 0)
                elif tp in ('devel:check', 'check'): role_hours['需求验收'] = role_hours.get('需求验收', 0) + (t['consumed'] if t['done'] else 0)
                elif tp in BACKEND_TYPES: role_hours['后端开发'] = role_hours.get('后端开发', 0) + (t['consumed'] if t['done'] else 0)
                elif tp == 'devel:frontend': role_hours['前端开发'] = role_hours.get('前端开发', 0) + (t['consumed'] if t['done'] else 0)
                elif tp in ('devel', 'dev'): role_hours['开发任务'] = role_hours.get('开发任务', 0) + (t['consumed'] if t['done'] else 0)
            test_h = sum(t['consumed'] for t in tasks if t.get('type') in ('test', 'testing') and t['done'])
            ui_h = sum(t['consumed'] for t in tasks if t.get('type') in ('ui', 'ui/ux') and t['done'])
            missing = []
            if role_hours.get('需求调研', 0) == 0: missing.append('需求调研')
            if role_hours.get('需求设计', 0) == 0: missing.append('需求设计')
            if role_hours.get('需求验收', 0) == 0: missing.append('需求验收')
            if role_hours.get('后端开发', 0) == 0: missing.append('后端开发')
            if role_hours.get('前端开发', 0) == 0: missing.append('前端开发')
            if test_h == 0: missing.append('测试')
            if missing:
                consumed = sum(t['consumed'] for t in tasks if t['done'])
                analysis3.append({'story_id': sid, 'story_name': story_names.get(sid, f'需求#{sid}'),
                    'missing_roles': missing, 'total_hours': round(consumed, 1),
                    'consumed_total': round(consumed, 1), 'undone_count': undone, 'tasks': tasks,
                    'research_hours': role_hours.get('需求调研', 0), 'design_hours': role_hours.get('需求设计', 0),
                    'check_hours': role_hours.get('需求验收', 0), 'backend_hours': role_hours.get('后端开发', 0),
                    'frontend_hours': role_hours.get('前端开发', 0), 'arch_hours': role_hours.get('开发任务', 0),
                    'test_hours': test_h, 'ui_hours': ui_h})

        analysis1.sort(key=lambda a: a['consumed_total'], reverse=True)
        analysis2.sort(key=lambda a: a['be_consumed_total'], reverse=True)
        analysis3.sort(key=lambda a: a['consumed_total'], reverse=True)

        qm = {'summary': {'total_stories': len(story_tasks),
            'analysis1_warnings': len(analysis1), 'analysis2_warnings': len(analysis2),
            'analysis3_warnings': len(analysis3)},
            'analysis1': analysis1, 'analysis2': analysis2, 'analysis3': analysis3, 'analysis4': []}

        with open('quality_monitor_data.json', 'w') as f:
            json.dump(qm, f, ensure_ascii=False, indent=2)

        # Run gen_report
        subprocess.run(['/Users/crystal/.workbuddy/binaries/python/envs/default/bin/python3', 'gen_report.py'],
            capture_output=True, timeout=30)
        subprocess.run(['cp', '/tmp/fms-gas-monitor/index.html', 'build/dailymonitor.html'])

        # Regenerate sub-pages
        with open('build/dailymonitor.html') as f: html = f.read()
        css = re.search(r'<style>(.*?)</style>', html, re.DOTALL).group(1)
        js = re.search(r'<script>(.*?)</script>', html, re.DOTALL).group(1)
        css_wide = css.replace('max-width:1400px;margin:0 auto;padding:24px', 'max-width:100%;margin:0;padding:12px 20px')

        od = re.search(r'<div id="overdue-detail".*?</div>\s*(?=<div id="quality-detail")', html, re.DOTALL)
        if od:
            b = od.group(0).replace('display:none', 'display:block')
            h = '<div style="background:linear-gradient(135deg,#1a56db,#1e40af);color:#fff;padding:28px 36px;border-radius:16px;margin-bottom:20px"><h1 style="font-size:24px;font-weight:700">延期任务统计</h1><p style="font-size:13px;opacity:.75;margin-top:6px">全平台超期追踪 · 按人聚合展示</p></div>'
            with open('build/overdue.html', 'w') as f:
                f.write(f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>延期任务统计 - FMS & GAS</title><style>{css_wide}</style></head><body><div class="container"><a href="index.html" style="display:inline-block;margin-bottom:20px;color:#3b82f6;text-decoration:none;font-size:13px">← 返回首页</a>{h}{b}</div><script>{js}</script></body></html>')

        qd = re.search(r'<div id="quality-detail".*?</div>\s*(?=<div class="note")', html, re.DOTALL)
        if qd:
            b = qd.group(0).replace('display:none', 'display:block')
            h = '<div style="background:linear-gradient(135deg,#1a56db,#1e40af);color:#fff;padding:28px 36px;border-radius:16px;margin-bottom:20px"><h1 style="font-size:24px;font-weight:700">工时质量监控</h1><p style="font-size:13px;opacity:.75;margin-top:6px">需求工时预警 · 角色覆盖检查 · 任务类型校验</p></div>'
            with open('build/quality.html', 'w') as f:
                f.write(f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>工时质量监控 - FMS & GAS</title><style>{css_wide}</style></head><body><div class="container"><a href="index.html" style="display:inline-block;margin-bottom:20px;color:#3b82f6;text-decoration:none;font-size:13px">← 返回首页</a>{h}{b}</div><script>{js}</script></body></html>')

        # Regenerate monitor.html
        GAS_N = {n for n, i in person_hours.items() if '海外售后' in i.get('project', '') or 'GAS' in i.get('project', '')}
        ppl = []
        for n, i in person_hours.items():
            if n in EXCLUDE: continue
            t, e, c = i.get('total_hours', 0), i.get('estimated_hours', 0), i.get('task_count', 0)
            pj = 'GAS' if n in GAS_N else 'FMS'
            ppl.append({'n': n, 't': round(t, 1), 'e': round(e, 1), 'c': c, 'pj': pj,
                'dp': i.get('dept', ''), 'pg': round(t / 72 * 100, 1) if t else 0,
                'el': round(e / 184 * 100, 1), 'cl': round(t / 184 * 100, 1)})
        ppl.sort(key=lambda p: (0 if p['pj'] == 'GAS' else 1, p['t']))
        fm = [p for p in ppl if p['pj'] == 'FMS']
        gs = [p for p in ppl if p['pj'] == 'GAS']

        # Write simplified monitor (same as existing but with fresh data)
        # For brevity, just update the JS task data in the existing monitor
        with open('build/monitor.html') as f: mon = f.read()
        task_data_json = json.dumps(person_all, ensure_ascii=False)
        mon = re.sub(r'var td=\[.*?\];', f'var td={task_data_json};', mon)
        with open('build/monitor.html', 'w') as f: f.write(mon)

        return jsonify({'ok': True, 'message': f'数据刷新完成 ({len(ppl)}人)', 'people': len(ppl)})
    except Exception as e:
        return jsonify({'ok': False, 'message': str(e)}), 500

if __name__ == '__main__':
    import os
    os.chdir('/Users/crystal/WorkBuddy/禅道任务')
    print('Server running at http://localhost:9876')
    app.run(host='0.0.0.0', port=9876, debug=False)
