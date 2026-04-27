# coding=utf-8
"""识别主线方向的中军、连板先锋（10cm）、弹性先锋（20cm）、趋势先锋"""
from config_loader import load_config

def identify_roles(concept_name, data):
    cfg = load_config()
    mid_cap_map = cfg.get('mid_cap_map', {})
    limit_stocks = data.get('limit_stocks', [])
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])
    qs = data.get('qs_stocks', [])

    # ---- 根据主线名称定义关键词 ----
    if '半导体' in concept_name or '芯片' in concept_name:
        related_ks = ['半导体', '芯片', 'PCB', '封测', '电子', '立讯精密', '北方华创', '中芯国际',
                      '长川科技', '澜起科技', '寒武纪', '海光信息', '韦尔股份', '兆易创新', '北京君正']
    elif '锂矿' in concept_name or '能源金属' in concept_name:
        related_ks = ['锂', '钴', '镍', '宁德时代', '天齐', '赣锋', '永兴材料', '江特电机']
    elif '算力' in concept_name or 'CPO' in concept_name:
        related_ks = ['算力', 'CPO', '光模块', '工业富联', '中际旭创', '新易盛']
    else:
        related_ks = concept_name.replace('概念', '').replace('产业链', '').split('/')

    def is_related(n):
        return any(k in n for k in related_ks)

    rel_limit = [s for s in limit_stocks if is_related(s['name'])]
    rel_qs = [s for s in qs if is_related(s['name'])]

    # ---- 中军 ----
    mid_targets = []
    if '半导体' in concept_name:
        mid_targets = ['立讯精密', '北方华创', '中芯国际', '海光信息', '澜起科技', '长川科技']
    elif '锂矿' in concept_name:
        mid_targets = ['宁德时代', '天齐锂业', '赣锋锂业', '永兴材料']
    elif '算力' in concept_name:
        mid_targets = ['工业富联', '中际旭创', '新易盛']

    seen_codes = set()
    mids = []
    for obj in top20 + mid_caps:
        if obj['name'] in mid_targets and obj.get('market_cap', 0) > 200 and obj.get('code', '') not in seen_codes:
            mids.append(obj)
            seen_codes.add(obj.get('code', ''))
    if not mids and mid_cap_map:
        for key, names in mid_cap_map.items():
            if key in concept_name or concept_name in key:
                for n in names:
                    for obj in top20 + mid_caps:
                        if obj['name'] == n and obj.get('code', '') not in seen_codes:
                            mids.append(obj)
                            seen_codes.add(obj.get('code', ''))
    mids = mids[:2]

    # ---- 连板先锋（10cm）与弹性先锋（20cm） ----
    def score_lb(st):
        t = st['turnover']
        ts = 10 if 3 <= t <= 7 else (7 if 7 < t <= 15 else (3 if t < 3 else 2))
        try:
            h, m = map(int, st['first_time'].split(':'))
            mins = h * 60 + m
        except:
            mins = 999
        if mins <= 570: ti = 10
        elif mins <= 600: ti = 9
        elif mins <= 630: ti = 7
        elif mins <= 690: ti = 5
        else: ti = 2
        if st['amount'] > 0:
            sr = st['seal_amount'] / st['amount']
        else:
            sr = 0
        se = 9 if sr > 3 else (7 if sr > 2 else (5 if sr > 1 else 3))
        is_10cm = not (st['code'].startswith('300') or st['code'].startswith('688') or st['code'].startswith('301'))
        cm_score = 5 if is_10cm else -5
        return ts * 0.3 + ti * 0.3 + se * 0.2 + cm_score * 0.2, st

    lianban, elastic = None, None
    if rel_limit:
        scored = [score_lb(s) for s in rel_limit]
        scored.sort(key=lambda x: x[0], reverse=True)
        top1 = scored[0][1]
        if top1['code'].startswith(('300', '688', '301')):
            elastic = top1
            for sc, st in scored:
                if not st['code'].startswith(('300', '688', '301')):
                    lianban = st
                    break
        else:
            lianban = top1
            for sc, st in scored:
                if st['code'].startswith(('300', '688', '301')):
                    elastic = st
                    break

    # ---- 趋势先锋 ----
    trend = None
    cands = [q for q in rel_qs if q.get('lb', 0) >= 1.5]
    valid = [q for q in cands if not any(ls['code'] == q['code'] and ls['lianban'] > 2 for ls in limit_stocks)]
    if valid:
        valid.sort(key=lambda x: x.get('trend_score', 0), reverse=True)
        trend = valid[0]

    return {
        'mid_cap': mids,
        'lianban_pioneer': lianban,
        'elastic_pioneer': elastic,
        'trend_pioneer': trend
    }