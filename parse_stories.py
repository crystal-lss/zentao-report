#!/usr/bin/env python3
import re, json, html as html_mod

with open('/tmp/zentao_stories.html', 'r') as f:
    content = f.read()

# Find zui-create-dtable attribute
match = re.search(r'zui-create-dtable=["\'](.+?)["\']\s+zui-create', content)
if not match:
    # Try without the following attribute
    match = re.search(r'zui-create-dtable=["\'](.+?)["\']', content)

if match:
    json_str = match.group(1)
    json_str = html_mod.unescape(json_str)
    
    data = json.loads(json_str)
    stories = data.get('data', [])
    print(f'Total stories: {len(stories)}')
    print()
    
    # Show toolbar actions
    toolbar_items = data.get('footToolbar', {}).get('items', [])
    if not toolbar_items:
        toolbar_items = data.get('toolbar', [])
    if toolbar_items:
        print('=== Toolbar actions ===')
        for t in toolbar_items:
            if isinstance(t, dict):
                hint = t.get('hint', '')
                name = t.get('name', '?')
                print(f'  {name}: {hint}')
    
    for s in stories:
        sid = s.get('story', '?')
        title = s.get('title', '?')
        status = s.get('status', '?')
        changed_by = s.get('changedBy', '')
        changed_date = s.get('changedDate', '')
        ur_changed = s.get('URChanged', '0')
        story_changed = s.get('storyChanged', '0')
        assigned_to = s.get('assignedTo', '')
        plan = s.get('planTitle', '')
        
        has_change = bool(changed_by) or ur_changed != '0' or story_changed != '0'
        
        marker = ' <<< HAS CHANGE' if has_change else ''
        print(f'Story {sid}: {title} [{status}]{marker}')
        print(f'  plan={plan} assignedTo={assigned_to}')
        if changed_by:
            print(f'  changedBy={changed_by} changedDate={changed_date}')
        if ur_changed != '0':
            print(f'  URChanged={ur_changed}')
        if story_changed != '0':
            print(f'  storyChanged={story_changed}')
        
        actions = s.get('actions', [])
        action_names = []
        for a in actions:
            if isinstance(a, dict):
                nm = a.get('name', '')
                disabled = a.get('disabled', False)
                hint = a.get('hint', '')
                if nm == 'dropdown' and 'items' in a:
                    for item in a['items']:
                        d = ' (disabled)' if item.get('disabled') else ''
                        action_names.append(f'{item.get("name","?")}{d}')
                else:
                    d = ' (disabled)' if disabled else ''
                    if hint:
                        action_names.append(f'{nm}{d}({hint[:25]})')
                    else:
                        action_names.append(f'{nm}{d}')
        if action_names:
            print(f'  actions: {" | ".join(action_names)}')
        print()
else:
    print('No match found')
    idx = content.find('zui-create-dtable')
    if idx >= 0:
        print(content[idx:idx+500])
