# coding=utf-8
"""
主线检测（最终稳定版）：包含锚点管理、预置C日、阶段递推、候选方向
已加入同一天防重复递推机制
"""
import os
import json
from datetime import datetime
from config_loader import load_config

# 路径：当前文件在 core/ 下，配置文件在 ../config/ 下
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, '..', 'config')
GLOBAL_ANCHOR_FILE = os.path.join(CONFIG_DIR, 'global_anchor.json')
CANDIDATE_SCORES_FILE = os.path.join(CONFIG_DIR, 'candidate_scores.json')

MIN_SCORE_MAIN_LINE = 4.5
CONFIRM_DAYS = 3
SWITCH_DAYS = 3
DECLINE_DAYS = 2

def load_json(fp):
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(fp, data):
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calc_sector_score(concept, data):
    """基础评分（简化版，用于候选板块）"""
    cfg = load_config()
    policy_hints = cfg.get('policy_hints', {})
    mid_cap_map = cfg.get('mid_cap_map', {})
    name = concept.get('name', '')
    if not name:
        return 0
    policy = 3
    for k, v in policy_hints.items():
        if k in name:
            policy = v
            break
    pct = concept.get('pct', 0)
    money = 5 if pct > 5 else (3 if pct > 2 else 1)
    limit_cnt = data.get('limit_by_sector', {}).get(name, 0)
    if not limit_cnt:
        for sn, c in data.get('limit_by_sector', {}).items():
            if name in sn or sn in name:
                limit_cnt = c
                break
    limit_score = 5 if limit_cnt >= 10 else (3 if limit_cnt >= 5 else 1)
    seal = 0
    leader = concept.get('leader', '')
    for st in data.get('limit_stocks', []):
        if st['name'] == leader:
            seal = st.get('seal_amount', 0)
            break
    seal_score = 5 if seal > 5 else (3 if seal > 1 else 1)
    mids = []
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])
    for key, names in mid_cap_map.items():
        if key in name:
            for n in names:
                for obj in top20 + mid_caps:
                    if obj['name'] == n:
                        mids.append(obj)
    if mids:
        avg_pct = sum(obj['pct'] for obj in mids) / len(mids)
        mid_score = 5 if avg_pct >= 9.8 else (3 if avg_pct > 5 else 2)
    else:
        mid_score = 1
    total = policy * 0.2 + money * 0.3 + limit_score * 0.2 + seal_score * 0.15 + mid_score * 0.15
    return round(total, 2)

def get_sector_mid_trend(name, data):
    ma = data.get('sector_ma', {})
    if name in ma:
        info = ma[name]
        return info.get('ma5_status') == '已跌破', info.get('ma20_status') == '已跌破'
    for k, v in ma.items():
        if name in k or k in name:
            return v.get('ma5_status') == '已跌破', v.get('ma20_status') == '已跌破'
    return False, False

def update_anchor(anchor, name, stage, score, t_day=None):
    if 'main_line' not in anchor:
        anchor['main_line'] = {}
    anchor['main_line'] = {'name': name, 'stage': stage, 'last_score': score}
    if t_day:
        anchor['t_day'] = t_day
    if 'history' not in anchor:
        anchor['history'] = []
    today = t_day or anchor.get('t_day')
    # 防止同一天重复记录同一阶段
    if not any(h.get('date') == today and h.get('stage') == stage for h in anchor['history']):
        anchor['history'].append({'date': today, 'main_line': name, 'stage': stage, 'score': score})
    save_json(GLOBAL_ANCHOR_FILE, anchor)

def update_candidate_scores(concepts, data):
    scores = load_json(CANDIDATE_SCORES_FILE)
    today = data['date']
    for cand in concepts:
        name = cand['name']
        sc = calc_sector_score(cand, data)
        if name not in scores:
            scores[name] = []
        if not any(s['date'] == today for s in scores[name]):
            scores[name].append({'date': today, 'score': sc})
        scores[name] = scores[name][-10:]
    save_json(CANDIDATE_SCORES_FILE, scores)
    return scores

def detect_c_day_candidates(concepts, data):
    """
    极简C日检测：最强中军 + 概念板块集群验证
    """
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])
    all_mid = top20 + mid_caps

    # 1. 找最强中军（涨幅>5%，市值>200亿，排除新股和旧主线）
    old_main = ['新易盛', '中际旭创', '天孚通信', '工业富联']
    candidates = []
    for s in all_mid:
        name = s['name']
        if name.startswith('N') or name.startswith('C'):
            continue
        if name in old_main:
            continue
        if s['pct'] >= 5 and s.get('market_cap', 0) > 200:
            candidates.append(s)
    if not candidates:
        return []

    candidates.sort(key=lambda x: x['pct'], reverse=True)
    top_stock = candidates[0]
    print(f"[DEBUG] 最强中军: {top_stock['name']} (涨幅 {top_stock['pct']}%)")

    # 2. 判断方向
    direction = None
    if top_stock['name'] in ['立讯精密', '北方华创', '中芯国际', '海光信息', '长川科技', '澜起科技', '寒武纪']:
        direction = '半导体/芯片产业链'
    elif top_stock['name'] in ['宁德时代', '天齐锂业', '赣锋锂业', '永兴材料']:
        direction = '锂矿/能源金属'

    if not direction:
        print(f"[DEBUG] 最强中军 '{top_stock['name']}' 不属于已知主线方向")
        return []

    # 3. 集群验证：涨幅前10的概念板块中，至少有2个与该方向相关，且板块涨幅>2%
    concepts_sorted = sorted(concepts, key=lambda x: x.get('pct', 0), reverse=True)
    related_concepts = []
    if '半导体' in direction:
        semi_kw = ['半导体', '芯片', 'PCB', '封测', '集成电路', '电子', 'MicroLED', '高带宽内存']
        for c in concepts_sorted[:10]:
            if any(kw in c['name'] for kw in semi_kw) and c['pct'] > 2:
                related_concepts.append(c['name'])
    elif '锂矿' in direction:
        lithium_kw = ['锂矿', '能源金属', '盐湖']
        for c in concepts_sorted[:10]:
            if any(kw in c['name'] for kw in lithium_kw) and c['pct'] > 2:
                related_concepts.append(c['name'])

    if len(related_concepts) >= 2:
        print(f"[DEBUG] 集群验证通过，确认C日方向: {direction}")
        return [{'name': direction, 'score': 4.5, 'concept': concepts_sorted[0]}]
    else:
        print(f"[DEBUG] 集群验证失败，相关概念数: {len(related_concepts)}")
        return []

def determine_main_lines(anchor, data):
    from role_identifier import identify_roles
    today = data['date']
    concepts = data.get('concepts', [])
    exclude = load_config().get('exclude_concepts', [])

    concepts_filtered = [c for c in concepts if not any(e in c['name'] for e in exclude)]
    scores = update_candidate_scores(concepts_filtered, data)

    mname = mstage = mscore = None
    if anchor and 'main_line' in anchor:
        m = anchor['main_line']
        mname = m.get('name')
        mstage = m.get('stage')
        mscore = m.get('last_score')

    # 检查今天是否已经递推过阶段（防止重复运行导致阶段跳跃）
    already_advanced_today = False
    if anchor and 'history' in anchor:
        for h in anchor['history']:
            if h.get('date') == today and h.get('stage') != mstage:  # 今天已经改过阶段
                already_advanced_today = True
                break

    if not mname or mstage == 'E':
        # 严格主线确认
        for c in concepts_filtered:
            hist = scores.get(c['name'], [])
            if len(hist) >= CONFIRM_DAYS and all(s['score'] >= MIN_SCORE_MAIN_LINE for s in hist[-CONFIRM_DAYS:]):
                b5, _ = get_sector_mid_trend(c['name'], data)
                if not b5:
                    ns = calc_sector_score(c, data)
                    update_anchor(anchor, c['name'], 'C', ns, today)
                    roles = identify_roles(c['name'], data)
                    return [{'name': c['name'], 'score': ns, 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                           f"主线确认：{c['name']}（C，连续3日达标）", c['name'], 'C'

        c_cands = detect_c_day_candidates(concepts_filtered, data)
        if c_cands:
            best = c_cands[0]
            cname = best['name']
            cscore = best['score']
            update_anchor(anchor, cname, 'C', cscore, today)
            roles = identify_roles(cname, data)
            main_lines = [{'name': cname, 'score': cscore, 'stage': 'C', 'roles': roles, 'type': 'main'}]
            candidates = []
            for c in concepts_filtered:
                if c['name'] == cname: continue
                hist = scores.get(c['name'], [])
                if hist and hist[-1]['score'] >= 2.0:
                    stage = '候选'
                    if len(hist) >= 2 and hist[-1]['score'] < hist[-2]['score']:
                        stage = '1D-1'
                    roles = identify_roles(c['name'], data)
                    candidates.append({'name': c['name'], 'score': hist[-1]['score'], 'stage': stage, 'roles': roles, 'type': 'candidate'})
            candidates.sort(key=lambda x: x['score'], reverse=True)
            main_lines.extend(candidates[:3])
            return main_lines, f"预置锚点：{cname}（C日启动）", cname, 'C'

        candidates = []
        for c in concepts_filtered:
            hist = scores.get(c['name'], [])
            if hist and hist[-1]['score'] >= 2.0:
                stage = '候选'
                if len(hist) >= 2 and hist[-1]['score'] < hist[-2]['score']:
                    stage = '1D-1'
                roles = identify_roles(c['name'], data)
                candidates.append({'name': c['name'], 'score': hist[-1]['score'], 'stage': stage, 'roles': roles, 'type': 'candidate'})
        candidates.sort(key=lambda x: x['score'], reverse=True)
        if candidates:
            return candidates[:5], "无预置锚点，候选方向观察中", None, None
        return [], "无确认主线，无候选方向", None, None

    # 已有主线
    main_today_score = next((calc_sector_score(c, data) for c in concepts_filtered if c['name'] == mname), mscore)
    b5, b20 = get_sector_mid_trend(mname, data)

    # 如果今天已经递推过了，则保持现有阶段，不再更改
    if already_advanced_today:
        roles = identify_roles(mname, data)
        return [{'name': mname, 'score': main_today_score, 'stage': mstage, 'roles': roles, 'type': 'main'}], \
               f"主线：{mname}（{mstage}）", mname, mstage

    # 阶段递推
    if mstage == 'C':
        ns = '1G-1' if main_today_score >= 4.5 and not b5 else 'C'
    elif 'G' in mstage:
        if b5:
            num = int(mstage.split('-')[0][0])
            ns = f'{num}D-1'
        else:
            parts = mstage.split('-')
            nd = int(parts[1]) + 1 if len(parts) > 1 else 1
            ns = f"{parts[0]}-{nd}"
    elif 'D' in mstage:
        if not b5 and main_today_score >= 4.0:
            num = int(mstage.split('-')[0][0]) + 1
            ns = f'{num}G-1'
        else:
            parts = mstage.split('-')
            nd = int(parts[1]) + 1
            ns = f"{parts[0]}-{nd}"
    else:
        ns = mstage

    # 退潮检查
    hist = scores.get(mname, [])
    if len(hist) >= DECLINE_DAYS and all(s['score'] < 3.0 for s in hist[-DECLINE_DAYS:]) and b20:
        ns = 'E'
    update_anchor(anchor, mname, ns, main_today_score)

    # 切换检查
    for c in concepts_filtered:
        if c['name'] == mname: continue
        hist_c = scores.get(c['name'], [])
        if len(hist_c) >= SWITCH_DAYS and all(s['score'] > mscore for s in hist_c[-SWITCH_DAYS:]):
            cb, _ = get_sector_mid_trend(c['name'], data)
            if not cb and b5:
                ns2 = calc_sector_score(c, data)
                update_anchor(anchor, c['name'], 'C', ns2, today)
                roles = identify_roles(c['name'], data)
                return [{'name': c['name'], 'score': ns2, 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                       f"主线切换：{c['name']}（C）", c['name'], 'C'

    roles = identify_roles(mname, data)
    return [{'name': mname, 'score': main_today_score, 'stage': ns, 'roles': roles, 'type': 'main'}], \
           f"主线：{mname}（{ns}）", mname, ns