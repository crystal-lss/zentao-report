#!/usr/bin/env python3
"""
工时预警分析脚本
统计 2026-07-01 ~ 今天，有完成者和完成时间的任务
按需求维度聚合，生成预警卡片数据
"""
import json
import sys
from datetime import datetime, date
from collections import defaultdict, Counter

# ─── 任务类型标准映射（来自 任务类型.xlsx） ───
# account → (姓名, 岗位, 标准任务类型)
PERSON_STANDARD = {
    # 产品 - 按任务名称匹配（不需要标准类型）
    'A80514': ('徐中然', '产品', None),      # 按名称匹配
    '180747': ('何曦宇', '产品', None),      # 按名称匹配
    '180748': ('连朔',  '产品', None),      # 按名称匹配
    'A80789': ('蔡泽平', '产品', None),      # 按名称匹配
    # 后端
    'A80520': ('李少君', '后端', 'a_dev4_control'),
    'A80715': ('苏若豪', '后端', 'a_dev4_control'),
    'A80740': ('肖永龙', '后端', 'a_dev4_control'),
    'A80735': ('毛慧敏', '后端', 'a_dev4_control'),
    '180152': ('全秋霞', '后端', 'a_dev4_control'),
    '180167': ('关珊',   '后端', 'a_dev4_control'),
    'A80556': ('梁彬彬', '后端', 'a_dev4_control'),
    'A80597': ('黎国威', '后端', 'a_dev4_control'),
    'heyang': ('何阳',   '后端', 'a_dev4_control'),
    'A80602': ('卢家朝', '后端', 'a_dev4_control'),
    'A80704': ('魏小兵', '后端', 'a_dev4_control'),
    'A80922': ('肖翰',   '后端', 'a_dev4_control'),
    'A80915': ('刘津',   '后端', 'a_dev4_control'),
    'A80714': ('贺桢',   '后端', 'a_dev4_control'),
    # 架构
    'A80569': ('冼泽华', '架构', 'a_dev'),
    'a80837': ('徐伟',   '架构', 'a_dev'),
    # 前端
    'A80575': ('袁世豪', '前端', 'a_dev2_front'),
    'A80521': ('姚彦',   '前端', 'a_dev2_front'),
    'A80773': ('刘钊志', '前端', 'a_dev2_front'),
    'A80223': ('舒恺',   '前端', 'a_dev2_front'),
    'A80264': ('陈国团', '前端', 'a_dev2_front'),
    'A80675': ('张兴龙', '前端', 'a_dev2_front'),
    # 测试
    'A80542': ('温碧玉', '测试', 'ae2_test'),
    'A80723': ('杜冬',   '测试', 'ae2_test'),
    '550388': ('蒋欣生', '测试', 'ae2_test'),
    'A80284': ('唐远辉', '测试', 'ae2_test'),
    'A80716': ('吴志强', '测试', 'ae2_test'),
    'wangyue': ('汪越', '测试', 'ae2_test'),
    'a80681': ('胡捷轩', '测试', 'ae2_test'),
    # UI/UX
    'A80507': ('李德文', 'UX', 'ad1_UI_des'),
    'a80549': ('许瑶',   'UI', 'ad1_UI_des'),
    'A80033': ('杨琳',   'UI', 'ad1_UI_des'),
}

# 按名称匹配的产品人员 account 集合
PRODUCT_NAME_MATCH = {'A80514', '180747', '180748', 'A80789'}

# 岗位 → 大类映射（用于产品/开发/测试/UI工时检查）
ROLE_TO_CATEGORY = {
    '产品': '产品', '后端': '开发', '架构': '开发', '前端': '开发',
    '测试': '测试', 'UX': 'UI', 'UI': 'UI',
}

# 任务名称关键词 → 标准类型（产品人员）
NAME_KEYWORDS = [
    ('需求调研', 'ab1_needs_research'),
    ('需求设计', 'ab2_request_des'),
    ('需求验收', 'ab3_request_check'),
]

EXECUTIONS = [4519, 4651, 4697, 4665, 4672, 4671]
DATE_FROM = '2026-07-01'
DATE_TO = '2026-07-09'

def load_all_tasks():
    """加载6个执行的所有任务"""
    all_tasks = []
    for exec_id in EXECUTIONS:
        try:
            with open(f'/tmp/tasks_{exec_id}.json') as f:
                data = json.load(f)
            for t in data.get('tasks', []):
                t['_exec_id'] = exec_id
            all_tasks.extend(data.get('tasks', []))
        except FileNotFoundError:
            print(f"Warning: /tmp/tasks_{exec_id}.json not found")
    return all_tasks

def filter_valid_tasks(tasks):
    """筛选7/1至今有完成者和完成时间的任务"""
    valid = []
    from_dt = datetime.strptime(f"{DATE_FROM} 00:00:00", '%Y-%m-%d %H:%M:%S')
    to_dt = datetime.strptime(f"{DATE_TO} 23:59:59", '%Y-%m-%d %H:%M:%S')
    
    for t in tasks:
        finished_by = (t.get('finishedBy') or '').strip()
        finished_date = (t.get('finishedDate') or '').strip()
        
        if not finished_by or not finished_date:
            continue
        
        try:
            fd = datetime.strptime(finished_date, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                fd = datetime.strptime(finished_date, '%Y-%m-%d')
            except ValueError:
                continue
        
        if from_dt <= fd <= to_dt:
            t['_finished_date'] = fd
            t['_finished_by'] = finished_by
            valid.append(t)
    
    return valid

def get_person_info(account):
    """获取人员姓名和标准岗位"""
    if account in PERSON_STANDARD:
        name, role, std_type = PERSON_STANDARD[account]
        return name, role, std_type
    return account, '未知', None

def determine_correct_type(task):
    """判断任务的标准类型"""
    account = task.get('finishedBy') or task.get('assignedTo') or ''
    
    if account in PRODUCT_NAME_MATCH:
        # 按任务名称匹配
        name = task.get('name', '')
        for kw, std_type in NAME_KEYWORDS:
            if kw in name:
                return std_type
        return None  # 无法从名称判断
    
    # 其他人员：按标准类型表
    _, _, std_type = get_person_info(account)
    return std_type

def story_key(task):
    """获取需求的唯一标识"""
    sid = task.get('storyID') or task.get('story') or 0
    stitle = task.get('storyTitle') or ''
    return (sid, stitle)

def analyze():
    all_tasks = load_all_tasks()
    print(f"Loaded {len(all_tasks)} tasks total")
    
    valid = filter_valid_tasks(all_tasks)
    print(f"Valid tasks (7/1-7/9, with finishedBy + finishedDate): {len(valid)}")
    
    # 按需求聚合
    stories = defaultdict(list)
    for t in valid:
        sk = story_key(t)
        stories[sk].append(t)
    
    print(f"Unique stories: {len(stories)}")
    
    results = []
    for (sid, stitle), stasks in stories.items():
        total_hours = sum(float(t.get('consumed', 0) or 0) for t in stasks)
        
        # 按角色分类统计工时
        role_hours = defaultdict(float)
        person_details = []  # 每个人的任务明细
        
        for t in stasks:
            account = t.get('finishedBy') or t.get('assignedTo') or ''
            name, role, _ = get_person_info(account)
            consumed = float(t.get('consumed', 0) or 0)
            category = ROLE_TO_CATEGORY.get(role, '其他')
            role_hours[category] += consumed
            
            # 任务类型校验
            actual_type = t.get('type', '')
            correct_type = determine_correct_type(t)
            is_correct = True
            type_detail = ''
            
            if account in PRODUCT_NAME_MATCH:
                # 按名称匹配的产品人员
                if correct_type is None:
                    is_correct = None  # 无法判断
                    type_detail = f'无法从名称判断标准类型(当前:{actual_type})'
                elif actual_type != correct_type:
                    is_correct = False
                    type_detail = f'应:{correct_type},实际:{actual_type}'
                else:
                    type_detail = f'{actual_type} 正确'
            elif account in PERSON_STANDARD:
                # 有标准类型的人员
                _, _, std_type = PERSON_STANDARD[account]
                if actual_type != std_type:
                    is_correct = False
                    type_detail = f'应:{std_type},实际:{actual_type}'
                else:
                    type_detail = f'{actual_type} 正确'
            else:
                type_detail = f'{actual_type} (无标准)'
            
            person_details.append({
                'task_id': t.get('id'),
                'task_name': t.get('name', ''),
                'person_name': name,
                'account': account,
                'role': role,
                'consumed': consumed,
                'actual_type': actual_type,
                'correct_type': correct_type,
                'is_correct': is_correct,
                'type_detail': type_detail,
                'exec_id': t.get('_exec_id'),
            })
        
        # 预警判断
        warnings = []
        
        # 1. 总工时 > 450h 预警, 最低 40h
        if total_hours > 450:
            warnings.append({'type': 'total_high', 'msg': f'总工时{total_hours:.0f}h超450h上限', 'severity': 'high'})
        if total_hours < 40:
            warnings.append({'type': 'total_low', 'msg': f'总工时{total_hours:.0f}h低于40h下限', 'severity': 'medium'})
        
        # 2. 后端开发最高工时 > 245h
        back_hours = role_hours.get('开发', 0)
        if back_hours > 245:
            warnings.append({'type': 'backend_high', 'msg': f'后端开发工时{back_hours:.0f}h超245h上限', 'severity': 'high'})
        
        # 3. 产品/开发/测试 是否为0
        for cat in ['产品', '开发', '测试']:
            if role_hours.get(cat, 0) == 0:
                warnings.append({'type': f'role_missing', 'msg': f'{cat}工时为0', 'severity': 'medium'})
        
        # 4. 任务类型错误统计
        type_errors = [p for p in person_details if p['is_correct'] is False]
        
        results.append({
            'story_id': sid,
            'story_title': stitle,
            'task_count': len(stasks),
            'total_hours': total_hours,
            'role_hours': dict(role_hours),
            'warnings': warnings,
            'warning_count': len(warnings),
            'has_high': any(w['severity'] == 'high' for w in warnings),
            'type_errors': type_errors,
            'type_error_count': len(type_errors),
            'person_details': person_details,
        })
    
    # 按预警严重度排序
    results.sort(key=lambda x: (-x['has_high'], -x['warning_count'], -x['total_hours']))
    
    # 统计汇总
    total_stories = len(results)
    high_warn_stories = sum(1 for r in results if r['has_high'])
    total_warnings = sum(r['warning_count'] for r in results)
    total_type_errors = sum(r['type_error_count'] for r in results)
    stories_with_type_errors = sum(1 for r in results if r['type_error_count'] > 0)
    
    summary = {
        'total_stories': total_stories,
        'total_tasks': len(valid),
        'high_warn_stories': high_warn_stories,
        'total_warnings': total_warnings,
        'total_type_errors': total_type_errors,
        'stories_with_type_errors': stories_with_type_errors,
        'date_range': f'{DATE_FROM} ~ {DATE_TO}',
    }
    
    output = {
        'summary': summary,
        'stories': [r for r in results if r['warning_count'] > 0 or r['type_error_count'] > 0],
        'stories_ok': len([r for r in results if r['warning_count'] == 0 and r['type_error_count'] == 0]),
    }
    
    print(f"\n=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"  stories_with_warnings: {len(output['stories'])}")
    print(f"  stories_ok: {output['stories_ok']}")
    
    return output

if __name__ == '__main__':
    result = analyze()
    output_path = '/Users/crystal/WorkBuddy/禅道任务/hours_alert_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\nSaved to {output_path}")
