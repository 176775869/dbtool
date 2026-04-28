# coding=utf-8
"""
主线检测 v9.0 ：双锚点机制
"""
import os, json
from datetime import datetime
from config_loader import load_config

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

def get_sector_mid_trend(name, data):
    ma = data.get('sector_ma', {})
    if name in ma:
        info = ma[name]
        return info.get('ma5_status') == '已跌破', info.get('ma20_status') == '已跌破'
    for k, v in ma.items():
        if name in k or k in name:
            return v.get('ma5_status') == '已跌破', v.get('ma20_status') == '已跌破'
    return False, False

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

    # 资金（集群涨幅均值）
    cps = [c['pct'] for c in concepts if any(kw in c['name'] for kw in kw_list)]
    avg = sum(cps) / len(cps) if cps else 0
    money = 5 if avg > 5 else (3 if avg > 2 else 1)

    # 涨停数
    total = sum(cnt for sn, cnt in data.get('limit_by_sector', {}).items() if any(kw in sn for kw in kw_list))
    limit_score = 5 if total >= 15 else (4 if total >= 10 else (3 if total >= 5 else 1))

    # 封单
    max_seal = max((st.get('seal_amount', 0) for st in limit_stocks), default=0)
    seal_score = 5 if max_seal > 5 else (3 if max_seal > 2 else 1)

    # 中军表现（role_identifier 提供，这里给中等底分）
    mid_score = 3

    total_score = round(policy * 0.2 + money * 0.3 + limit_score * 0.2 + seal_score * 0.15 + mid_score * 0.15, 2)
    return total_score

def update_anchor_file(anchor):
    save_json(GLOBAL_ANCHOR_FILE, anchor)

def find_new_challenger(concepts, data):
    """寻找新的C日挑战者"""
    cfg = load_config()
    old_main = cfg.get('old_main_names', [])
    cluster_kw = cfg.get('cluster_keywords', {})

    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])
    all_mid = top20 + mid_caps

    # 最强非退潮中军
    cands = [obj for obj in all_mid
             if obj['pct'] >= 5 and obj.get('market_cap', 0) > 200
             and not obj['name'].startswith(('N', 'C'))
             and obj['name'] not in old_main]
    if not cands:
        return None

    cands.sort(key=lambda x: x['pct'], reverse=True)
    top_stock = cands[0]

    # 判断方向
    direction = None
    for dir_name, kw_list in cluster_kw.items():
        if any(kw in top_stock['name'] for kw in kw_list):
            direction = dir_name
            break
    if not direction:
        return None

    # 集群验证
    concepts_sorted = sorted(concepts, key=lambda x: x.get('pct', 0), reverse=True)
    related = [c for c in concepts_sorted[:10] if any(kw in c['name'] for kw in cluster_kw.get(direction, [])) and c['pct'] > 1]
    if len(related) < 2:
        return None

    score = calc_full_score(direction, data)
    return {'main_line': direction, 'stage': 'C', 'last_score': score, 't_day': data['date']}

def determine_main_lines(anchor, data):
    from role_identifier import identify_roles
    today = data['date']
    concepts = data.get('concepts', [])

    # 确保基本结构
    if 'primary_anchor' not in anchor:
        anchor['primary_anchor'] = None
    if 'challenger_anchor' not in anchor:
        anchor['challenger_anchor'] = None

    primary = anchor.get('primary_anchor')
    challenger = anchor.get('challenger_anchor')

    # ---- 无主锚点且无挑战者：尝试寻找新挑战者 ----
    if not primary and not challenger:
        new_ch = find_new_challenger(concepts, data)
        if new_ch:
            anchor['challenger_anchor'] = new_ch
            update_anchor_file(anchor)
            roles = identify_roles(new_ch['main_line'], data)
            return [{'name': new_ch['main_line'], 'score': new_ch['last_score'], 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                   f"预置锚点：{new_ch['main_line']}（C日启动）", new_ch['main_line'], 'C'
        return [], "无确认主线", None, None

    # ---- 有挑战者：检查是否满足切换条件 ----
    if challenger:
        challenger_name = challenger['main_line']
        challenger_score_today = calc_full_score(challenger_name, data)

        # 更新挑战者评分
        challenger['last_score'] = challenger_score_today

        # 检查切换：连续3日评分>=4.5 且 中军未破5日线
        # 简化：这里需要从candidate_scores中获取连续评分，但当前逻辑直接判定为：若今日评分>=4.5且中军未破5日线，且主锚点阶段为E或即将E。
        # 真实切换需要三日验证，这里为了快速实现，满足以下条件即切换：
        # 1. 挑战者评分 >= 4.5
        # 2. 主锚点不存在 或 主锚点阶段为E 或 主锚点评分低于挑战者
        primary_stage = primary.get('stage') if primary else 'E'
        can_switch = False
        if challenger_score_today >= 4.5:
            if not primary or primary_stage == 'E' or (primary.get('last_score', 0) < challenger_score_today):
                # 三日验证简化：从candidate_scores读取最近3天评分
                scores = load_json(CANDIDATE_SCORES_FILE).get(challenger_name, [])
                if len(scores) >= 3 and all(s['score'] >= 4.5 for s in scores[-3:]):
                    can_switch = True

        if can_switch:
            # 切换：挑战者升级为主锚点，原主锚点标记为E并入历史（暂存）
            old_primary = primary
            anchor['primary_anchor'] = challenger
            anchor['challenger_anchor'] = None
            # 保存旧主锚点退潮信息，可记录在history中（忽略）
            update_anchor_file(anchor)

            roles = identify_roles(challenger_name, data)
            return [{'name': challenger_name, 'score': challenger_score_today, 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                   f"主线切换：{challenger_name}（确认）", challenger_name, 'C'
        else:
            # 挑战者保持，但更新阶段
            # 阶段递推（简化）
            new_stage = 'C'
            if challenger_score_today >= 4.0:
                new_stage = 'C'  # 实际应根据规则递推，此处略
            challenger['stage'] = new_stage
            update_anchor_file(anchor)
            roles = identify_roles(challenger_name, data)
            return [{'name': challenger_name, 'score': challenger_score_today, 'stage': new_stage, 'roles': roles, 'type': 'main'}], \
                   f"挑战者：{challenger_name}（{new_stage}）", challenger_name, new_stage

    # ---- 无挑战者，但存在主锚点 ----
    if primary:
        main_name = primary['main_line']
        main_score_today = calc_full_score(main_name, data)
        b5, b20 = get_sector_mid_trend(main_name, data)

        # 阶段递推逻辑（完整规则请参考设计文档，此处简化为示例）
        stage = primary.get('stage', 'C')
        if stage == 'E':
            # 尝试寻找挑战者
            new_ch = find_new_challenger(concepts, data)
            if new_ch:
                anchor['challenger_anchor'] = new_ch
                update_anchor_file(anchor)
                roles = identify_roles(new_ch['main_line'], data)
                return [{'name': new_ch['main_line'], 'score': new_ch['last_score'], 'stage': 'C', 'roles': roles, 'type': 'main'}], \
                       f"预置锚点：{new_ch['main_line']}（C日启动）", new_ch['main_line'], 'C'
            else:
                roles = identify_roles(main_name, data)
                return [{'name': main_name, 'score': main_score_today, 'stage': 'E', 'roles': roles, 'type': 'main'}], \
                       f"主线：{main_name}（E退潮）", main_name, 'E'

        # 递推阶段
        new_stage = stage
        if stage == 'C':
            new_stage = '1G-1' if main_score_today >= 4.0 else 'C'
        elif 'G' in stage:
            if b5:
                num = int(stage.split('-')[0][0])
                new_stage = f'{num}D-1'
            else:
                parts = stage.split('-')
                nd = int(parts[1]) + 1 if len(parts) > 1 else 1
                new_stage = f"{parts[0]}-{nd}"
        # 退潮检测
        if main_score_today < 2.5 and b20:
            new_stage = 'E'

        primary['stage'] = new_stage
        primary['last_score'] = main_score_today
        update_anchor_file(anchor)

        roles = identify_roles(main_name, data)
        return [{'name': main_name, 'score': main_score_today, 'stage': new_stage, 'roles': roles, 'type': 'main'}], \
               f"主线：{main_name}（{new_stage}）", main_name, new_stage

    return [], "无确认主线", None, None