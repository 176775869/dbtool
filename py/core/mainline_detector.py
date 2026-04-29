# coding=utf-8
"""
主线检测 v10.2：市场周期识别 + 候选池机制 + 动态节奏模型 + 评分修复
"""
import os, json
from datetime import datetime, timedelta
from config_loader import load_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, '..', 'config')
GLOBAL_ANCHOR_FILE = os.path.join(CONFIG_DIR, 'global_anchor.json')
CANDIDATE_SCORES_FILE = os.path.join(CONFIG_DIR, 'candidate_scores.json')

MIN_SCORE_MAIN_LINE = 4.5
CONFIRM_DAYS = 3
SWITCH_DAYS = 3
DECLINE_DAYS = 2
DECLINE_WINDOW_DAYS = 2

def load_json(fp):
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(fp, data):
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 市场周期识别 ====================
def detect_market_phase(data, anchor=None):
    cfg = load_config()
    thresholds = cfg.get('environment_thresholds', {})
    sh = data.get('sh_index', 0)
    ma20 = data.get('ma20', 0)
    total_amt = data.get('sh_amount', 0) + data.get('sz_amount', 0)
    sid_max_amt = thresholds.get('sideways_max_amount', 22000)

    if sh < ma20 and total_amt < sid_max_amt:
        return 'decline'
    if total_amt < sid_max_amt:
        return 'sideways'
    return 'uptrend'

def get_rhythm_model(phase):
    cfg = load_config()
    models = cfg.get('rhythm_models', {
        'uptrend': [0, 2, 4, 9, 11],
        'sideways': [0, 2, 4, 6, 8],
        'retreat': None,
        'decline': None
    })
    return models.get(phase)

def is_in_decline_window(c_day, old_main_e_day):
    if not old_main_e_day:
        return False
    try:
        diff = (datetime.strptime(c_day, '%Y%m%d') - datetime.strptime(old_main_e_day, '%Y%m%d')).days
        return diff <= DECLINE_WINDOW_DAYS
    except:
        return False

# ==================== 评分与承载力 ====================
def calc_full_score(direction_name, data):
    cfg = load_config()
    policy_hints = cfg.get('policy_hints', {})
    cluster_kw = cfg.get('cluster_keywords', {})
    concepts = data.get('concepts', [])
    limit_stocks = data.get('limit_stocks', [])
    kw_list = cluster_kw.get(direction_name, [direction_name])

    # 政策
    policy = 3
    for k, v in policy_hints.items():
        if k in direction_name:
            policy = v
            break

    # 资金（集群涨幅均值，放宽过滤：pct < 1000）
    cps = []
    for c in concepts:
        if any(kw in c['name'] for kw in kw_list) or any(kw in c.get('leader', '') for kw in kw_list):
            pct = c.get('pct', 0)
            if 0 < pct < 1000:
                cps.append(pct)
    avg = sum(cps) / len(cps) if cps else 0
    money = 5 if avg > 5 else (3 if avg > 2 else 1)

    # 涨停数
    total = sum(cnt for sn, cnt in data.get('limit_by_sector', {}).items() if any(kw in sn for kw in kw_list))
    limit_score = 5 if total >= 15 else (4 if total >= 10 else (3 if total >= 5 else 1))

    # 封单（取方向相关涨停股的最大封单额）
    max_seal = 0
    for st in limit_stocks:
        if any(kw in st['name'] for kw in kw_list):
            if st.get('seal_amount', 0) > max_seal:
                max_seal = st['seal_amount']
    seal_score = 5 if max_seal > 5 else (3 if max_seal > 2 else 1)

    # 中军表现（role_identifier 负责，这里给中等底分）
    mid_score = 3

    total_score = round(policy * 0.2 + money * 0.3 + limit_score * 0.2 + seal_score * 0.15 + mid_score * 0.15, 2)
    return total_score

def calc_capacity(direction_name, data):
    cluster_kw = load_config().get('cluster_keywords', {})
    kw_list = cluster_kw.get(direction_name, [direction_name])
    concepts = data.get('concepts', [])
    total_amt = data.get('sh_amount', 0) + data.get('sz_amount', 0)
    if total_amt == 0:
        return 0
    dir_amt = 0
    for c in concepts:
        if any(kw in c['name'] for kw in kw_list):
            amt = c.get('amount', 0)
            if amt > 0:
                dir_amt += amt
    return dir_amt / total_amt

def get_sector_mid_trend(name, data):
    ma = data.get('sector_ma', {})
    if name in ma:
        info = ma[name]
        return info.get('ma5_status') == '已跌破', info.get('ma20_status') == '已跌破'
    for k, v in ma.items():
        if name in k or k in name:
            return v.get('ma5_status') == '已跌破', v.get('ma20_status') == '已跌破'
    return False, False

# ==================== 候选池管理 ====================
def detect_c_day_candidates(concepts, data):
    cfg = load_config()
    old_main = cfg.get('old_main_names', [])
    cluster_kw = cfg.get('cluster_keywords', {})
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])
    all_mid = top20 + mid_caps

    cands = [obj for obj in all_mid
             if obj['pct'] >= 5 and obj.get('market_cap', 0) > 200
             and not obj['name'].startswith(('N', 'C'))
             and obj['name'] not in old_main]
    if not cands:
        return []

    cands.sort(key=lambda x: x['pct'], reverse=True)
    detected = []
    seen_dirs = set()
    for stock in cands:
        for dir_name, kw_list in cluster_kw.items():
            if dir_name in seen_dirs:
                continue
            if any(kw in stock['name'] for kw in kw_list):
                concepts_sorted = sorted(concepts, key=lambda x: x.get('pct', 0), reverse=True)
                related = [c for c in concepts_sorted[:10] if any(kw in c['name'] for kw in kw_list) and c['pct'] > 1]
                if len(related) >= 2:
                    score = calc_full_score(dir_name, data)
                    detected.append({'name': dir_name, 'score': score})
                    seen_dirs.add(dir_name)
                break
    return detected

def update_candidate_pool(anchor, data):
    today = data['date']
    
    if anchor.get('last_update_date') == today:
        return
    
    if 'candidate_pool' not in anchor:
        anchor['candidate_pool'] = []

    pool = anchor['candidate_pool']
    old_main_e_day = None
    if anchor.get('primary_anchor', {}).get('stage') == 'E':
        old_main_e_day = anchor['primary_anchor'].get('t_day')

    for cand in pool:
        score = calc_full_score(cand['name'], data)
        cand['last_score'] = score
        cand['capacity'] = calc_capacity(cand['name'], data)
        stage = cand.get('stage', 'C')
        b5, b20 = get_sector_mid_trend(cand['name'], data)
        if stage == 'C':
            cand['stage'] = '1G-1' if score >= 4.5 and not b5 else 'C'
        elif 'G' in stage:
            if b5:
                num = int(stage.split('-')[0][0])
                cand['stage'] = f'{num}D-1'
            else:
                parts = stage.split('-')
                nd = int(parts[1]) + 1 if len(parts) > 1 else 1
                cand['stage'] = f"{parts[0]}-{nd}"
        elif 'D' in stage:
            if not b5 and score >= 4.0:
                num = int(stage.split('-')[0][0]) + 1
                cand['stage'] = f'{num}G-1'
            else:
                parts = stage.split('-')
                nd = int(parts[1]) + 1
                cand['stage'] = f"{parts[0]}-{nd}"

    concepts = data.get('concepts', [])
    new_dirs = detect_c_day_candidates(concepts, data)
    for nd in new_dirs:
        if not any(c['name'] == nd['name'] for c in pool):
            pool.append({
                'name': nd['name'],
                't_day': today,
                'type': '窗口期候选' if is_in_decline_window(today, old_main_e_day) else '普通候选',
                'stage': 'C',
                'last_score': nd['score'],
                'capacity': calc_capacity(nd['name'], data),
                'mid_cap': [],
                'lianban_pioneer': None,
                'trend_pioneer': None
            })

    pool[:] = [c for c in pool if not (c.get('last_score', 0) < 3.0 and get_sector_mid_trend(c['name'], data)[1])]
    pool.sort(key=lambda x: (is_in_decline_window(x.get('t_day', ''), old_main_e_day), x.get('last_score', 0)), reverse=True)
    anchor['candidate_pool'] = pool
    anchor['last_update_date'] = today
    save_json(GLOBAL_ANCHOR_FILE, anchor)

# ==================== 主线判定 ====================
def determine_main_lines(anchor, data):
    from role_identifier import identify_roles
    today = data['date']

    update_candidate_pool(anchor, data)
    pool = anchor.get('candidate_pool', [])

    scores = load_json(CANDIDATE_SCORES_FILE)
    for cand in pool:
        name = cand['name']
        sc = cand.get('last_score', 0)
        if name not in scores:
            scores[name] = []
        if not any(s['date'] == today for s in scores[name]):
            scores[name].append({'date': today, 'score': sc})
        scores[name] = scores[name][-10:]
    save_json(CANDIDATE_SCORES_FILE, scores)

    for cand in pool:
        roles = identify_roles(cand['name'], data)
        cand['mid_cap'] = [m['name'] for m in roles.get('mid_cap', [])]
        cand['lianban_pioneer'] = roles['lianban_pioneer']['name'] if roles.get('lianban_pioneer') else None
        cand['trend_pioneer'] = roles['trend_pioneer']['name'] if roles.get('trend_pioneer') else None

    phase = detect_market_phase(data, anchor)
    rhythm = get_rhythm_model(phase)

    main_lines = []
    for cand in pool[:5]:
        roles = identify_roles(cand['name'], data)
        main_lines.append({
            'name': cand['name'],
            'score': cand.get('last_score', 0),
            'stage': cand.get('stage', 'C'),
            'capacity': cand.get('capacity', 0),
            'type': cand.get('type', '候选'),
            'roles': roles,
            'main_type': 'candidate'
        })

    primary = anchor.get('primary_anchor', {})
    if primary.get('main_line'):
        primary_roles = identify_roles(primary['main_line'], data)
        main_lines.insert(0, {
            'name': primary['main_line'],
            'score': primary.get('last_score', 0),
            'stage': primary.get('stage', 'E'),
            'capacity': 0,
            'type': '主锚点（退潮）',
            'roles': primary_roles,
            'main_type': 'primary'
        })

    phase_msg = f"市场阶段：{phase} | 节奏：{rhythm if rhythm else '无（空仓等待）'}"
    return main_lines, phase_msg, phase, rhythm