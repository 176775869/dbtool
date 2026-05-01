"""
session_manager.py - 解析 AI 复盘的 JSON，更新 session_snapshot.json
用法：
    python session_manager.py py/data/ai_response.txt
"""
import json
import os
import re
from datetime import datetime

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def repair_truncated_json(raw):
    """尝试修复截断的 JSON：补全缺失的闭合括号"""
    open_braces = raw.count('{') - raw.count('}')
    open_brackets = raw.count('[') - raw.count(']')

    # 如果最后是未闭合的字符串，截断到最后一个完整逗号
    stripped = raw.rstrip()
    if not stripped.endswith('}') and not stripped.endswith(']'):
        last_comma = raw.rfind(',')
        if last_comma > 0:
            raw = raw[:last_comma]
            open_braces = raw.count('{') - raw.count('}')
            open_brackets = raw.count('[') - raw.count(']')

    raw += ']' * open_brackets
    raw += '}' * open_braces
    return raw

def extract_json_from_response(text):
    """从 AI 返回的大段文本中提取第一个有效 JSON 对象。支持自动修复截断。"""
    # 方式1：匹配 ```json ``` 代码块
    match = re.search(r'```json\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 方式2：匹配最外层 {}
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        raw = match.group()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            repaired = repair_truncated_json(raw)
            if repaired:
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass

    raise ValueError("无法从 AI 回复中提取有效 JSON")

def update_snapshot(snapshot, ai_json, new_date=None):
    """根据 AI 输出的 JSON 更新快照"""
    if new_date is None:
        new_date = datetime.now().strftime('%Y%m%d')

    snapshot['date'] = new_date

    # 市场阶段与节奏
    phase = ai_json.get('market_phase', snapshot.get('market_phase', 'sideways'))
    snapshot['market_phase'] = phase

    rhythm = ai_json.get('rhythm')
    if rhythm:
        snapshot['rhythm'] = rhythm

    if phase in ('decline', 'retreat'):
        snapshot['rhythm_day'] = 0
    else:
        snapshot['rhythm_day'] = snapshot.get('rhythm_day', 0) + 1

    # 环境等级
    grade_map = {'uptrend': 'S', 'sideways': 'A', 'decline': 'C', 'retreat': 'C'}
    snapshot['environment_grade'] = ai_json.get('environment_grade', grade_map.get(phase, 'B'))

    # 更新主锚点
    old_anchor = snapshot.get('primary_anchor', {})
    new_anchor = ai_json.get('primary_anchor', {})
    if new_anchor:
        name_changed = new_anchor.get('name') != old_anchor.get('name')
        score_now = new_anchor.get('score', 0)
        if name_changed:
            new_anchor['consecutive_qualify_days'] = 1
        else:
            if score_now >= 4.5:
                new_anchor['consecutive_qualify_days'] = old_anchor.get('consecutive_qualify_days', 0) + 1
            else:
                new_anchor['consecutive_qualify_days'] = 0
        snapshot['primary_anchor'] = {**old_anchor, **new_anchor}

    # 更新候选池
    old_pool = {c['name']: c for c in snapshot.get('candidate_pool', [])}
    new_pool = ai_json.get('candidate_pool', [])
    updated_pool = []

    for cand in new_pool:
        name = cand['name']
        old = old_pool.get(name, {})
        merged = {**old, **cand}
        score = merged.get('score', 0)
        if score >= 4.5:
            merged['consecutive_qualify_days'] = old.get('consecutive_qualify_days', 0) + 1
        elif score < 3.0:
            merged['consecutive_qualify_days'] = old.get('consecutive_qualify_days', 0) - 1
        else:
            merged['consecutive_qualify_days'] = max(0, old.get('consecutive_qualify_days', 0))

        if merged.get('consecutive_qualify_days', 0) <= -2:
            print(f'[淘汰] {name} 连续2日评分<3.0，移出候选池')
            continue

        updated_pool.append(merged)

    for old_name, old_cand in old_pool.items():
        if old_name not in [c['name'] for c in updated_pool]:
            if old_cand.get('consecutive_qualify_days', 0) > -2:
                updated_pool.append(old_cand)

    snapshot['candidate_pool'] = updated_pool

    # 持仓建议
    snapshot['holdings_advice'] = ai_json.get('holdings_advice', snapshot.get('holdings_advice', ''))
    snapshot['last_action'] = ai_json.get('next_day_plan', ai_json.get('last_action', ''))

    # 历史全景表追加
    history = snapshot.get('history', [])
    last_hist = history[-1] if history else {}
    if last_hist.get('date') != new_date:
        history.append({
            'date': new_date,
            't_plus': last_hist.get('t_plus', -1) + 1,
            'index': '',
            'volume': '',
            'emotion': '',
            'action': snapshot.get('last_action', '')
        })
    snapshot['history'] = history

    return snapshot

def update_from_ai_response(ai_response_text, snapshot_path):
    """主入口：传入 AI 完整回复文本和快照文件路径，更新并保存快照"""
    ai_json = extract_json_from_response(ai_response_text)
    snapshot = load_json(snapshot_path)
    updated = update_snapshot(snapshot, ai_json)
    save_json(updated, snapshot_path)
    print(f'[OK] 快照已更新，日期: {updated["date"]}')
    return updated

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('用法: python session_manager.py <ai_response.txt>')
        sys.exit(1)

    resp_file = sys.argv[1]
    base = os.path.dirname(os.path.abspath(__file__))
    snapshot_path = os.path.join(base, '..', 'config', 'session_snapshot.json')

    with open(resp_file, 'r', encoding='utf-8') as f:
        resp_text = f.read()

    updated = update_from_ai_response(resp_text, snapshot_path)
    print(json.dumps(updated, ensure_ascii=False, indent=2))