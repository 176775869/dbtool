# coding=utf-8
"""
主线检测 v7.0：完整评分卡 + 三日确认机制
"""
import os
import json
from datetime import datetime
from config_loader import load_config

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(SCRIPT_DIR, '..', 'config')
GLOBAL_ANCHOR_FILE = os.path.join(CONFIG_DIR, 'global_anchor.json')
CANDIDATE_SCORES_FILE = os.path.join(CONFIG_DIR, 'candidate_scores.json')

MIN_SCORE_MAIN_LINE = 4.5        # 主线确认最低评分
CONFIRM_DAYS = 3                  # 连续达标天数
SWITCH_DAYS = 3                   # 切换缓冲天数
DECLINE_DAYS = 2                  # 退潮低分天数

def load_json(fp):
    if os.path.exists(fp):
        with open(fp, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_json(fp, data):
    with open(fp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== 完整评分卡 ====================

def calc_full_score(direction_name, data):
    """
    完整五项加权评分：
    - 政策强度 20%
    - 资金流入 30%（基于概念板块集群涨幅）
    - 涨停数量 20%
    - 先锋封单 15%
    - 中军表现 15%
    返回 (总分, 各项得分字典)
    """
    cfg = load_config()
    policy_hints = cfg.get('policy_hints', {})
    concepts = data.get('concepts', [])
    limit_stocks = data.get('limit_stocks', [])
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])

    # 1. 政策强度
    policy = 3  # 默认
    for kw, score in policy_hints.items():
        if kw in direction_name:
            policy = score
            break

    # 2. 资金流入（集群涨幅代理）
    cluster_kw = {
        '半导体/芯片产业链': ['半导体', '芯片', 'PCB', '封测', '集成电路', 'MicroLED', '高带宽内存', '存储芯片', 'AI芯片', '汽车芯片', '先进封装', '中芯概念'],
        '锂矿/能源金属': ['锂矿', '能源金属', '盐湖'],
    }
    kw_list = cluster_kw.get(direction_name, [direction_name[:4]])
    cluster_pct = 0
    cluster_cnt = 0
    for c in concepts:
        if any(kw in c['name'] for kw in kw_list):
            cluster_pct += c['pct']
            cluster_cnt += 1
    avg_pct = cluster_pct / cluster_cnt if cluster_cnt > 0 else 0
    if avg_pct > 5:
        money_score = 5
    elif avg_pct > 2:
        money_score = 3
    else:
        money_score = 1

    # 3. 涨停数量
    limit_by_sector = data.get('limit_by_sector', {})
    total_limit = 0
    for sn, cnt in limit_by_sector.items():
        if any(kw in sn for kw in kw_list):
            total_limit += cnt
    if total_limit >= 15:
        limit_score = 5
    elif total_limit >= 10:
        limit_score = 4
    elif total_limit >= 5:
        limit_score = 3
    else:
        limit_score = 1

    # 4. 先锋封单（取涨停池中相关个股的最大封单额）
    max_seal = 0
    for st in limit_stocks:
        if st.get('seal_amount', 0) > max_seal:
            max_seal = st['seal_amount']
    if max_seal > 5:
        seal_score = 5
    elif max_seal > 2:
        seal_score = 3
    else:
        seal_score = 1

    # 5. 中军表现
    mid_names = {
        '半导体/芯片产业链': ['立讯精密', '北方华创', '中芯国际', '海光信息', '澜起科技', '长川科技', '寒武纪'],
        '锂矿/能源金属': ['宁德时代', '天齐锂业', '赣锋锂业', '永兴材料'],
    }
    target_names = mid_names.get(direction_name, [])
    mids = []
    for obj in top20 + mid_caps:
        if obj['name'] in target_names and obj.get('market_cap', 0) > 200:
            mids.append(obj)
    if mids:
        avg_mid_pct = sum(m['pct'] for m in mids) / len(mids)
        if avg_mid_pct >= 9.8:
            mid_score = 5
        elif avg_mid_pct > 5:
            mid_score = 3
        else:
            mid_score = 2
    else:
        mid_score = 1

    total = round(policy * 0.2 + money_score * 0.3 + limit_score * 0.2 +
                  seal_score * 0.15 + mid_score * 0.15, 2)

    return total, {
        'policy': policy,
        'money_score': money_score,
        'limit_score': limit_score,
        'limit_cnt': total_limit,
        'seal_score': seal_score,
        'max_seal': max_seal,
        'mid_score': mid_score,
        'mid_names': [m['name'] for m in mids]
    }

# ==================== C日检测 ====================

def detect_c_day_candidates(concepts, data):
    """基于最强中军 + 集群验证识别C日方向"""
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])

    # 最强中军
    old_main = ['新易盛', '中际旭创', '天孚通信', '工业富联']
    cands = []
    for obj in top20 + mid_caps:
        name = obj['name']
        if name.startswith('N') or name.startswith('C'):
            continue
        if name in old_main:
            continue
        if obj['pct'] >= 5 and obj.get('market_cap', 0) > 200:
            cands.append(obj)
    if not cands:
        return None

    cands.sort(key=lambda x: x['pct'], reverse=True)
    top_stock = cands[0]

    # 方向判定
    semi_names = ['立讯精密', '北方华创', '中芯国际', '海光信息', '长川科技', '澜起科技', '寒武纪']
    lithium_names = ['宁德时代', '天齐锂业', '赣锋锂业', '永兴材料']

    direction = None
    if top_stock['name'] in semi_names:
        direction = '半导体/芯片产业链'
    elif top_stock['name'] in lithium_names:
        direction = '锂矿/能源金属'

    if not direction:
        return None

    # 集群验证
    cluster_kw = {
        '半导体/芯片产业链': ['半导体', '芯片', 'PCB', '封测', '集成电路', 'MicroLED', '高带宽内存'],
        '锂矿/能源金属': ['锂矿', '能源金属', '盐湖'],
    }
    kw_list = cluster_kw.get(direction, [direction[:4]])
    concepts_sorted = sorted(concepts, key=lambda x: x.get('pct', 0), reverse=True)
    related = [c for c in concepts_sorted[:10] if any(kw in c['name'] for kw in kw_list) and c['pct'] > 1]

    if len(related) >= 2:
        score, _ = calc_full_score(direction, data)
        return {'name': direction, 'score': score, 'concept': concepts_sorted[0]}

    return None

# ==================== 锚点管理 ====================

def update_anchor(anchor, name, stage, score, t_day=None):
    if 'main_line' not in anchor:
        anchor['main_line'] = {}
    anchor['main_line'] = {'name': name, 'stage': stage, 'last_score': score}
    if t_day:
        anchor['t_day'] = t_day
    if 'history' not in anchor:
        anchor['history'] = []
    today = t_day or anchor.get('t_day')
    if not any(h.get('date') == today and h.get('stage') == stage for h in anchor['history']):
        anchor['history'].append({'date': today, 'main_line': name, 'stage': stage, 'score': score})
    save_json(GLOBAL_ANCHOR_FILE, anchor)

def update_candidate_scores(concepts, data):
    scores = load_json(CANDIDATE_SCORES_FILE)
    today = data['date']
    for cand in concepts:
        name = cand['name']
        sc, _ = calc_full_score(name, data)  # 尝试完整评分
        if sc == 0:
            sc = 2.0  # 兜底
        if name not in scores:
            scores[name] = []
        if not any(s['date'] == today for s in scores[name]):
            scores[name].append({'date': today, 'score': sc})
        scores[name] = scores[name][-10:]
    save_json(CANDIDATE_SCORES_FILE, scores)
    return scores

def get_sector_mid_trend(name, data):
    ma = data.get('sector_ma', {})
    if name in ma:
        info = ma[name]
        return info.get('ma5_status') == '已跌破', info.get('ma20_status') == '已跌破'
    for k, v in ma.items():
        if name in k or k in name:
            return v.get('ma5_status') == '已跌破', v.get('ma20_status') == '已跌破'
    return False, False

# ==================== 主线判定 ====================

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

    # 检查今天是否已递推
    already_advanced_today = False
    if anchor and 'history' in anchor:
        for h in anchor['history']:
            if h.get('date') == today and h.get('stage') != mstage:
                already_advanced_today = True
                break

    # ---- 情况1：无主线或已退潮 ----
    if not mname or mstage == 'E':
        # 先检查是否有满足三日确认的方向
        for c in concepts_filtered:
            hist = scores.get(c['name'], [])
            if len(hist) >= CONFIRM_DAYS and all(s['score'] >= MIN_SCORE_MAIN_LINE for s in hist[-CONFIRM_DAYS:]):
                b5, _ = get_sector_mid_trend(c['name'], data)
                if not b5:
                    new_score, _ = calc_full_score(c['name'], data)
                    update_anchor(anchor, c['name'], 'C', new_score, today)
                    roles = identify_roles(c['name'], data)
                    return [{'name': c['name'], 'score': new_score, 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                           f"主线确认：{c['name']}（连续3日评分达标）", c['name'], 'C'

        # 寻找C日预置锚点
        c_cand = detect_c_day_candidates(concepts_filtered, data)
        if c_cand:
            cname = c_cand['name']
            cscore = c_cand['score']
            update_anchor(anchor, cname, 'C', cscore, today)
            roles = identify_roles(cname, data)
            main_lines = [{'name': cname, 'score': cscore, 'stage': 'C', 'roles': roles, 'type': 'main'}]
            return main_lines, f"预置锚点：{cname}（C日启动，{cscore}分）", cname, 'C'

        # 无C日，显示候选
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
        return [], "无确认主线", None, None

    # ---- 情况2：有主线且未退潮 ----
    main_today_score, score_detail = calc_full_score(mname, data)
    b5, b20 = get_sector_mid_trend(mname, data)

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

    # 退潮
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
                ns2, _ = calc_full_score(c['name'], data)
                update_anchor(anchor, c['name'], 'C', ns2, today)
                roles = identify_roles(c['name'], data)
                return [{'name': c['name'], 'score': ns2, 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                       f"主线切换：{c['name']}（C）", c['name'], 'C'

    roles = identify_roles(mname, data)
    return [{'name': mname, 'score': main_today_score, 'stage': ns, 'roles': roles, 'type': 'main'}], \
           f"主线：{mname}（{ns}，{main_today_score}分）", mname, ns