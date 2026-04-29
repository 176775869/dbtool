# coding=utf-8
"""
买点检测引擎 + 主跌妖股模式
"""
from config_loader import load_config

def detect_buy_signals(main_lines, data, anchor):
    signals = []
    for ml in main_lines:
        stage = ml.get('stage', '')
        roles = ml.get('roles', {})
        direction_name = ml.get('name', '')
        if ml.get('main_type') != 'candidate':
            continue

        if stage == 'C':
            sig = detect_c_type_a(direction_name, roles, data)
            if sig: signals.append(sig)
        elif stage in ('1G-1', '2G-1', '3G-1'):
            sig = detect_c_type_b(direction_name, roles, data)
            if sig: signals.append(sig)
        elif stage in ('1D-1', '2D-1'):
            sig = detect_d1(direction_name, roles, data)
            if sig: signals.append(sig)
        elif stage in ('1D-2', '2D-2'):
            sig = detect_d2(direction_name, roles, data)
            if sig: signals.append(sig)
        elif 'D' in stage:
            sig = detect_d3(direction_name, roles, data)
            if sig: signals.append(sig)
        
        # 主升期：已有仓位处理
        if 'G' in stage and int(stage.split('G')[0].split('-')[0]) >= 2:
            sig = detect_hold(direction_name, roles, data)
            if sig: signals.append(sig)

    return signals


def detect_c_type_a(direction_name, roles, data):
    lianban = roles.get('lianban_pioneer')
    elastic = roles.get('elastic_pioneer')
    stocks = []
    if lianban: stocks.append(f"{lianban['name']}({lianban.get('code','')})")
    if elastic: stocks.append(f"{elastic['name']}({elastic.get('code','')})")
    if not stocks: return None
    return {
        'type': 'C-A（启动）',
        'name': direction_name,
        'stocks': stocks,
        'condition': '板块涨停≥10家且中军大涨，打板最先换手板',
        'cangwei': '仓3-仓4',
        'timing': '早盘10:30前'
    }

def detect_c_type_b(direction_name, roles, data):
    lianban = roles.get('lianban_pioneer')
    elastic = roles.get('elastic_pioneer')
    stocks = []
    if lianban: stocks.append(f"{lianban['name']}({lianban.get('code','')})")
    if elastic: stocks.append(f"{elastic['name']}({elastic.get('code','')})")
    if not stocks: return None
    return {
        'type': 'C-B（确认）',
        'name': direction_name,
        'stocks': stocks,
        'condition': '隔日封单加大≥50%且>3亿，新增涨停≥2家，板块>2%',
        'cangwei': '仓3-仓4',
        'timing': '早盘10:30前'
    }

def detect_d1(direction_name, roles, data):
    lianban = roles.get('lianban_pioneer')
    if not lianban: return None
    return {
        'type': 'D1（开板回封）',
        'name': direction_name,
        'stocks': [f"{lianban['name']}({lianban.get('code','')})"],
        'condition': '开板后午盘前回封，封单额/成交>1.5→打板',
        'cangwei': '仓4',
        'timing': '午盘前'
    }

def detect_d2(direction_name, roles, data):
    lianban = roles.get('lianban_pioneer')
    trend = roles.get('trend_pioneer')
    stocks = []
    if lianban: stocks.append(f"{lianban['name']}({lianban.get('code','')})")
    if trend: stocks.append(f"{trend['name']}({trend.get('code','')})")
    if not stocks: return None
    return {
        'type': 'D2（活口弱转强）',
        'name': direction_name,
        'stocks': stocks,
        'condition': '竞价高开3-7%且放量>30%，开盘15分钟拉升翻红',
        'cangwei': '仓2-仓3',
        'timing': '次日早盘'
    }

def detect_d3(direction_name, roles, data):
    mid_cap = roles.get('mid_cap', [])
    if not mid_cap: return None
    stocks = [f"{m['name']}({m.get('code','')})" for m in mid_cap[:2]]
    return {
        'type': 'D3（中军低吸）',
        'name': direction_name,
        'stocks': stocks,
        'condition': '回踩5日线缩量企稳，次日不创新低→尾盘或次日早盘低吸',
        'cangwei': '仓2-仓3',
        'timing': '尾盘14:50或次日早盘'
    }

def detect_hold(direction_name, roles, data):
    mid_cap = roles.get('mid_cap', [])
    if not mid_cap: return None
    stocks = [f"{m['name']}({m.get('code','')})" for m in mid_cap[:1]]
    return {
        'type': 'HOLD（持有）',
        'name': direction_name,
        'stocks': stocks,
        'condition': '主升加速期，沿5日线持有，不加仓',
        'cangwei': '仓2-仓3',
        'timing': '—'
    }


def detect_demon_stocks(data, anchor):
    from mainline_detector import detect_market_phase
    phase = detect_market_phase(data)
    if phase != 'decline':
        return []

    cfg = load_config()
    thresholds = cfg.get('decline_demon_thresholds', {})
    min_lb = thresholds.get('min_lianban', 3)

    limit_stocks = data.get('limit_stocks', [])
    demons = []
    for st in limit_stocks:
        if st.get('lianban', 0) >= min_lb:
            demons.append({
                'name': st['name'],
                'code': st['code'],
                'lianban': st['lianban'],
                'pct': st['pct'],
                'turnover': st.get('turnover', 0),
                'seal_amount': st.get('seal_amount', 0),
                'cangwei': f"仓{thresholds.get('max_position', 1)}"
            })
    return demons[:3]