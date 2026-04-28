# coding=utf-8
"""识别主线方向的中军、连板先锋、弹性先锋、趋势先锋（最终稳定版）"""
from config_loader import load_config

def identify_roles(direction_name, data):
    limit_stocks = data.get('limit_stocks', [])
    top20 = data.get('top20', [])
    mid_caps = data.get('mid_caps', [])
    qs = data.get('qs_stocks', [])
    cfg = load_config()
    cluster_kw = cfg.get('cluster_keywords', {})
    kw_list = cluster_kw.get(direction_name, [])

    if not kw_list:
        kw_list = [direction_name[:4]]

    def is_related(name):
        return any(kw in name for kw in kw_list)

    # ---- 中军：方向相关，市值>200亿，涨幅>3% ----
    all_mid = top20 + mid_caps
    seen = set()
    mids = []
    for obj in all_mid:
        code = obj.get('code', '')
        if code in seen:
            continue
        if obj.get('market_cap', 0) >= 200 and obj['pct'] >= 3 and is_related(obj['name']):
            mids.append(obj)
            seen.add(code)

    # 兜底：放宽至市值>100亿，涨幅>=1%
    if not mids:
        for obj in all_mid:
            code = obj.get('code', '')
            if code in seen:
                continue
            if obj.get('market_cap', 0) >= 100 and obj['pct'] >= 1 and is_related(obj['name']):
                mids.append(obj)
                seen.add(code)

    mids.sort(key=lambda x: x.get('market_cap', 0), reverse=True)
    mids = mids[:3]

    # ---- 方向相关的涨停股 ----
    rel_limit = [s for s in limit_stocks if is_related(s['name'])]
    rel_qs = [s for s in qs if is_related(s['name'])]

    # ---- 连板先锋（10cm）与弹性先锋（20cm）----
    def score_lb(st):
        t = st['turnover']
        ts = 10 if 3 <= t <= 7 else (7 if 7 < t <= 15 else (3 if t < 3 else 2))
        try:
            h, m = map(int, st['first_time'].split(':'))
            mins = h * 60 + m
        except:
            mins = 999
        ti = (10 if mins <= 570 else 9 if mins <= 600 else 7 if mins <= 630 else 5 if mins <= 690 else 2)
        sr = st['seal_amount'] / st['amount'] if st['amount'] > 0 else 0
        se = 9 if sr > 3 else (7 if sr > 2 else (5 if sr > 1 else 3))
        is_10cm = not st['code'].startswith(('300', '688', '301'))
        return ts * 0.3 + ti * 0.3 + se * 0.2 + (5 if is_10cm else -5) * 0.2, st

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

    # ---- 趋势先锋：方向相关的强势池个股 ----
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